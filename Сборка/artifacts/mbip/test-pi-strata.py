#!/usr/bin/python3
"""Functional MBIP-03 checks over the owner's local SSH forward."""
from datetime import datetime, timezone
import json
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import urllib.request

MODEL = "qwen3.6-35b-a3b-ud-q4_k_xl"
PROVIDER = "ailab-strata"
BASE = "http://127.0.0.1:18081/v1"
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def request(route, body=None):
    req = urllib.request.Request(BASE+route, None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type":"application/json"})
    return HTTP.open(req,timeout=120)


def emit(case, **fields):
    print(datetime.now(timezone.utc).isoformat(),case,json.dumps(fields, ensure_ascii=False),flush=True)


def chat_args(stream=False, effort="none"):
    return {"model":MODEL, "messages":[{"role":"user","content":"Reply exactly OK."}],
            "reasoning_effort":effort,"max_tokens":128 if effort != "none" else 20,"stream":stream}


def api_tests():
    with request("/models") as reply:
        models=json.load(reply)["data"]
    with request("/status") as reply:
        status=json.load(reply)
    assert MODEL in {m["id"] for m in models} and status["loaded"] is True
    emit("STRATA_TUNNEL_MODEL_PASS", model=MODEL, loaded=True)
    with request("/chat/completions",chat_args()) as reply:
        choice=json.load(reply)["choices"][0]
    assert choice["message"]["content"].strip().strip(".!")=="OK"
    emit("API_NONSTREAM_PASS", answer=choice["message"]["content"].strip(), finish=choice["finish_reason"])
    with request("/chat/completions",chat_args(stream=True)) as reply:
        events=[line.decode().strip()[6:] for line in reply if line.startswith(b"data: ")]
    assert events[-1]=="[DONE]"
    choices=[c for event in events[:-1] for c in json.loads(event).get("choices",[])]
    text="".join(c.get("delta",{}).get("content") or "" for c in choices)
    assert text.strip().strip(".!")=="OK" and any(c.get("finish_reason") in ("stop","length") for c in choices)
    emit("API_SSE_PASS",text=text.strip(),done=True,finish=[c["finish_reason"] for c in choices if c.get("finish_reason")])
    with request("/chat/completions",chat_args(effort="low")) as reply:
        choice=json.load(reply)["choices"][0]
    message=choice["message"]
    emit("API_REASONING_OBSERVED", effort="low", fields=sorted(message.keys()),
         reasoning_nonempty=bool(message.get("reasoning_content")), answer_nonempty=bool(message.get("content")))


def pi_events(work, prompt, tools):
    args=["pi","--no-extensions","--no-skills","--no-context-files","--no-session","--mode","json",
          "--print","--thinking","low","--model",f"{PROVIDER}/{MODEL}",*tools,prompt]
    p=subprocess.run(args,cwd=work,text=True,stdin=subprocess.DEVNULL,capture_output=True,timeout=190)
    rows=[]
    for line in p.stdout.splitlines():
        try:
            row=json.loads(line)
        except ValueError:
            continue
        if isinstance(row,dict):
            rows.append(row)
    messages=[row["message"] for row in rows if row.get("type")=="message_end" and isinstance(row.get("message"),dict)]
    assistants=[m for m in messages if m.get("role")=="assistant"]
    if p.returncode or not assistants:
        emit("PI_CAPTURE_FAILURE", returncode=p.returncode, event_types=sorted({r.get("type","") for r in rows}),
             last=[{k:m.get(k) for k in ("api","provider","model","stopReason")} for m in assistants[-2:]])
        raise AssertionError("Pi did not produce a completed assistant message")
    assert all(m.get("provider")==PROVIDER and m.get("model")==MODEL for m in assistants)
    return rows,messages,assistants


def text(msg):
    return "".join(c.get("text","") for c in msg.get("content",[]) if c.get("type")=="text")


def pi_tests():
    with tempfile.TemporaryDirectory(prefix="mbip03-pi-") as temp:
        work=Path(temp)
        _,_,assistants=pi_events(work,"Reply exactly OK.",["--no-tools"])
        last=assistants[-1]
        assert text(last).strip().strip(".!")=="OK"
        emit("PI_STRATA_SHORT_PASS",provider=last["provider"],model=last["model"],finish=last.get("stopReason"),
             thinking_seen=any(c.get("type")=="thinking" and c.get("thinking") for c in last["content"]))
        marker="MBIP03_"+secrets.token_hex(8).upper()
        (work/"probe.txt").write_text(marker+"\n")
        rows,messages,assistants=pi_events(work,
            'Use the read tool exactly once to read ./probe.txt. Then, after the tool result, reply with exactly the single line from that file.',
            ["--tools","read"])
        calls=[c for m in assistants for c in m.get("content",[]) if c.get("type")=="toolCall"]
        results=[m for m in messages if m.get("role")=="toolResult"]
        ends=[r for r in rows if r.get("type")=="tool_execution_end"]
        emit("PI_TOOL_OBSERVATION", call_names=[c.get("name") for c in calls], result_count=len(results),
             result_has_marker=any(marker in text(m) for m in results), last_answer_matches=marker==text(assistants[-1]).strip(),
             end_events=len(ends), finishes=[m.get("stopReason") for m in assistants])
        assert len(calls)==1 and calls[0]["name"]=="read"
        assert calls[0]["arguments"].get("path") in ("./probe.txt","probe.txt",str(work/"probe.txt"))
        assert len(results)==1 and results[0].get("toolCallId")==calls[0]["id"] and marker in text(results[0])
        assert not results[0].get("isError") and len(assistants)>=2 and marker==text(assistants[-1]).strip()
        emit("PI_TOOL_CONTINUATION_PASS",provider=PROVIDER,model=MODEL,tool="read", correlated_id=True)


if __name__=="__main__":
    try:
        api_tests()
        pi_tests()
    except (AssertionError, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        emit("MBIP_PI_TEST_FAIL",error_type=type(error).__name__,detail=str(error)[:200])
        sys.exit(1)
