#!/usr/bin/python3
"""Live API and Pi CLI smoke through the real SSH tunnel."""
import argparse,json,urllib.request,secrets,tempfile,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
MODELS={"flash":"qwen3.8-flash-next-ud-q6_k_xl","inkling":"inkling-2-mini-sq-20"}
a=argparse.ArgumentParser();a.add_argument("profile",choices=MODELS);args=a.parse_args()
MODEL=MODELS[args.profile]; PROVIDER="ailab-strata"; BASE="http://127.0.0.1:18081/v1"
HTTP=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def emit(case,**fields):print(datetime.now(timezone.utc).isoformat(),case,json.dumps(fields,ensure_ascii=False),flush=True)
def request(route,body=None):
    return HTTP.open(urllib.request.Request(BASE+route,None if body is None else json.dumps(body).encode(),headers={"Content-Type":"application/json"}),timeout=600)
def chat(prompt,stream=False,effort="none",max_tokens=128):
    return {"model":MODEL,"messages":[{"role":"user","content":prompt}],"reasoning_effort":effort,"stream":stream,"max_tokens":max_tokens}
def exact(t,expected):return t.strip().strip(".!")==expected
def api_test():
    with request("/models") as r: ids={m["id"] for m in json.load(r)["data"]}
    with request("/status") as r: status=json.load(r)
    assert ids=={MODEL} and status["loaded"] is True,(ids,status.get("loaded"))
    emit("SERVER_MODEL_PASS",model=MODEL)
    with request("/chat/completions",chat("Reply exactly OK.")) as r: c=json.load(r)["choices"][0]
    assert exact(c["message"]["content"],"OK"),c.get("finish_reason")
    emit("API_NONSTREAM_PASS",finish=c.get("finish_reason"))
    with request("/chat/completions",chat("Reply exactly OK.",True)) as r:
        events=[l.decode().strip()[6:] for l in r if l.startswith(b"data: ")]
    assert events and events[-1]=="[DONE]"
    choices=[c for e in events[:-1] for c in json.loads(e).get("choices",[])]
    s="".join(c.get("delta",{}).get("content") or "" for c in choices)
    assert exact(s,"OK") and any(c.get("finish_reason") in ("stop","length") for c in choices)
    emit("API_SSE_PASS",done=True,finish=[c["finish_reason"] for c in choices if c.get("finish_reason")])
    with request("/chat/completions",chat("Compute 17 times 23. Reply with just the number.",effort="low",max_tokens=1024)) as r: c=json.load(r)["choices"][0]
    m=c["message"]; reason=m.get("reasoning_content") or m.get("reasoning") or ""
    emit("API_REASONING_OBSERVED",reasoning_chars=len(reason),answer_chars=len(m.get("content") or ""),finish=c.get("finish_reason"))
    assert reason and exact(m.get("content") or "","391")
    emit("API_REASONING_PASS")
def text(m):return "".join(c.get("text","") for c in m.get("content",[]) if c.get("type")=="text")
def pi_events(work,prompt,tools):
    cmd=["pi","--offline","--no-extensions","--no-skills","--no-context-files","--no-session","--mode","json","--print","--thinking","low","--model",f"{PROVIDER}/{MODEL}",*tools,prompt]
    p=subprocess.run(cmd,cwd=work,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=1200)
    rows=[]
    for line in p.stdout.splitlines():
        try:r=json.loads(line)
        except ValueError:continue
        if isinstance(r,dict):rows.append(r)
    ms=[r["message"] for r in rows if r.get("type")=="message_end" and isinstance(r.get("message"),dict)]
    ass=[m for m in ms if m.get("role")=="assistant"]
    emit("PI_CAPTURE",exit=p.returncode,assistants=len(ass),last=[{k:m.get(k) for k in ("provider","model","stopReason")} for m in ass[-2:]])
    assert not p.returncode and ass
    assert all(m.get("provider")==PROVIDER and m.get("model")==MODEL for m in ass)
    return ms,ass
def pi_test():
    with tempfile.TemporaryDirectory(prefix="mbip05-pi-") as d:
        work=Path(d)
        _,ass=pi_events(work,"Compute 17 times 23. Reply with just the number.",["--no-tools"])
        assert exact(text(ass[-1]),"391")
        reasoning=any(c.get("type")=="thinking" and c.get("thinking") for m in ass for c in m.get("content",[]))
        emit("PI_SHORT_PASS",thinking_seen=bool(reasoning))
        assert reasoning,"Pi did not preserve reasoning"
        marker="MBIP05_"+secrets.token_hex(8).upper()
        (work/"probe.txt").write_text(marker+"\n")
        ms,ass=pi_events(work,"Use the read tool to read ./probe.txt. After the result, reply with exactly the single line in the file.",["--tools","read"])
        calls=[c for m in ass for c in m.get("content",[]) if c.get("type")=="toolCall"]
        results=[m for m in ms if m.get("role")=="toolResult"]
        correlated=[r for r in results if any(c.get("id")==r.get("toolCallId") and c.get("name")=="read" for c in calls)]
        assert correlated and all(not r.get("isError") for r in correlated)
        assert any(marker in text(r) for r in correlated) and text(ass[-1]).strip()==marker and len(ass)>=2
        emit("PI_READ_CONTINUATION_PASS",calls=[c.get("name") for c in calls],correlated_id=True)
try:
    api_test();pi_test();emit("MBIP05_LIVE_PASS",profile=args.profile)
except (AssertionError,OSError,ValueError,KeyError,subprocess.SubprocessError) as e:
    emit("MBIP05_LIVE_FAIL",type=type(e).__name__,detail=str(e)[:300]);sys.exit(1)
