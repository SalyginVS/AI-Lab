#!/usr/bin/python3
"""Controlled regression smoke on Lenovo after the accepted Ollama mode is restored."""
from datetime import datetime, timezone
import json, math, subprocess, sys, tempfile
from pathlib import Path
import urllib.request

Q6 = "qwen3.8-flash-next:125b-a6b-q6_K-ab-262k"
Q27 = "qwen3.8-27b-gsq-rco:iq3s-mtp-262k"
root=Path.home()/".pi"/"agent"
provider=json.loads((root/"models.json").read_bytes())["providers"]["ailab-ollama"]
base=provider["baseUrl"].removesuffix("/v1")
http=urllib.request.build_opener(urllib.request.ProxyHandler({}))


def say(*args):
    print(datetime.now(timezone.utc).isoformat(),*args,flush=True)


def api(path,data=None):
    req=urllib.request.Request(base+path,None if data is None else json.dumps(data).encode(),
                               headers={"Content-Type":"application/json"})
    with http.open(req,timeout=100) as r:
        return json.load(r)


def resident():
    return [m["name"] for m in api("/api/ps")["models"]]


def remove_test_runner(model):
    running=resident()
    if running==[model]:
        result=api("/api/generate",{"model":model,"keep_alive":0})
        assert result.get("done_reason")=="unload", "unload not acknowledged"
        say("OLLAMA_TEST_RUNNER_UNLOADED",model)
    elif running:
        raise AssertionError("Unexpected resident model; no runner was stopped")


def run_pi(work, model, launch, timeout):
    say("PI_OLLAMA_START",model)
    common=["--no-extensions","--no-skills","--no-context-files","--no-tools","--no-session","--mode","json","--print"]
    p=subprocess.run([*launch,*common,"Reply with exactly one word: OK."],cwd=work,text=True,
                     stdin=subprocess.DEVNULL,capture_output=True,timeout=timeout)
    events=[]
    for line in p.stdout.splitlines():
        try:
            item=json.loads(line)
        except ValueError:
            continue
        if item.get("type")=="message_end" and item.get("message",{}).get("role")=="assistant":
            events.append(item["message"])
    if not events or p.returncode:
        say("PI_OLLAMA_FAIL",model,p.returncode)
        raise AssertionError("No finished Pi response")
    last=events[-1]
    message="".join(c.get("text","") for c in last["content"] if c.get("type")=="text")
    assert last.get("provider")=="ailab-ollama" and last.get("model")==model and message.strip().strip(".!")=="OK"
    say("PI_OLLAMA_PASS",model,"provider",last.get("provider"),"answer=OK",
        "thinking_seen",any(c.get("type")=="thinking" and c.get("thinking") for c in last["content"]))


def main():
    assert api("/api/version")["version"]=="0.35.1" and not resident()
    assert provider["modelOverrides"][Q6]["samplingParams"]["reasoning_effort"]=="xhigh"
    with tempfile.TemporaryDirectory(prefix="mbip03-ollama-") as work:
        for model,launch,limit in ((Q6,["pi","--model",f"ailab-ollama/{Q6}","--thinking","xhigh"],480),
                                   (Q27,["pi-q27"],180)):
            try:
                run_pi(work,model,launch,limit)
            finally:
                remove_test_runner(model)
    vector=api("/api/embed",{"model":"qwen3-embedding:latest","input":"MBIP-03 connectivity smoke","keep_alive":0})["embeddings"]
    assert len(vector)==1 and len(vector[0])==4096 and all(math.isfinite(x) for x in vector[0])
    say("OLLAMA_EMBED_PASS dimension=4096")
    say("FINAL_OLLAMA_RESIDENT",json.dumps(resident()))


if __name__=="__main__":
    try:
        main()
    except (AssertionError,OSError,ValueError,KeyError,subprocess.SubprocessError) as error:
        say("OLLAMA_REGRESSION_SMOKE_FAIL",type(error).__name__,str(error)[:160])
        sys.exit(1)
