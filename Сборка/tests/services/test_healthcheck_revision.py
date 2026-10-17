#!/usr/bin/env python3
"""RB-07.1 offline checks. Loopback stubs only, no lab server access."""
import argparse,ast,csv,hashlib,http.server,io,json,os,re,shutil,socket,subprocess,sys,tempfile,threading,time,urllib.request
from pathlib import Path
Q6="qwen3.8-flash-next:125b-a6b-q6_K-ab-262k"
EMBED="qwen3-embedding:latest"
BASE="e3269eefbc54cc0571992e7bbf007a997d26d31b"
def run(cmd,**kw):
    return subprocess.run(cmd,capture_output=True,text=True,timeout=60,**kw)
def check(p):
    assert p.returncode==0, p.stdout+p.stderr
    return p
def gateway_json(path,data=None,token=None):
    h={}
    if token:h["Authorization"]="Bearer "+token
    if data is not None:h["Content-Type"]="application/json"
    q=urllib.request.Request("http://127.0.0.1:8000"+path,data=None if data is None else json.dumps(data).encode(),headers=h)
    try:
        with urllib.request.urlopen(q,timeout=20) as resp:return json.load(resp)
    except urllib.error.HTTPError as exc:raise AssertionError("HTTP "+str(exc.code)+" "+exc.read().decode())
class Ollama(http.server.BaseHTTPRequestHandler):
    models=[Q6,EMBED];requests=[]
    def log_message(self,*args):pass
    def send(self,obj,status=200):
        b=json.dumps(obj).encode();self.send_response(status);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
    def do_GET(self):
        if self.path=="/api/tags":self.send({"models":[{"name":m,"model":m,"size":1,"digest":"0"*64,"modified_at":"2026-10-17T00:00:00Z","details":{}} for m in self.models]})
        else:self.send({},404)
    def do_POST(self):
        data=json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.requests.append({"path":self.path,"body":data})
        if self.path=="/api/embed":self.send({"model":data["model"],"embeddings":[[0.0]*4096],"prompt_eval_count":1})
        elif self.path=="/api/chat":self.send({"model":data["model"],"created_at":"2026-10-17T00:00:00Z","message":{"role":"assistant","content":"OK"},"done":True,"done_reason":"stop","total_duration":1,"load_duration":1,"prompt_eval_count":1,"prompt_eval_duration":1,"eval_count":1,"eval_duration":1})
        else:self.send({},404)
def expected_revision(source):
    """Explicit ordered edits, each required exactly once except all Python invocations."""
    edits=[
      ("#!/usr/bin/env bash\n","#!/usr/bin/env bash\n# Revision RB-07.1, 2026-10-17; owner decision H-6 (2026-10-16).\n"),
      ('CONTEXT_WINDOW=262144',''),
      ('  "qwen3.8-flash-next:125b-a6b-q5_K_M-ab-262k"\n  "kat-coder-v2.5-dev:256k"\n  "qwen38-rvn-sandbox-native:256k"','  "'+Q6+'"'),
      ('Three primary LLMs have num_ctx = 262144','Required LLMs have num_ctx = 262144'),
      ('and data["models_count"] >= 4','and data["models_count"] >= int(sys.argv[2])'),
      ('step.get("model") == "kat-coder-v2.5-dev:256k"','step.get("model") == "'+Q6+'"')]
    for old,new in edits:
        assert source.count(old)==1,(old,source.count(old))
        source=source.replace(old,new,1)
    first=source.index("check_gateway_health_contract()")
    last=source.index("check_gateway_version_matches_source()",first)
    frag=source[first:last];assert frag.count('python3 - "$payload"')==1
    dollar=chr(36)
    frag=frag.replace('python3 - "$payload"','python3 - "$payload" "'+dollar+'(('+dollar+'{#REQUIRED_LLM_MODELS[@]} + 1))"')
    source=source[:first]+frag+source[last:]
    assert source.count("python3 - ")==10 and source.count('"$ROOT/venv/bin/python" - ')==1
    return source.replace("python3 - ","python3 -I - ").replace('"$ROOT/venv/bin/python" - ','"$ROOT/venv/bin/python" -I - ')
def main():
    p=argparse.ArgumentParser()
    for n in ["repo","evidence","venv","shellcheck"]:p.add_argument("--"+n,type=Path,required=True)
    a=p.parse_args();r=a.repo;e=a.evidence;e.mkdir(parents=True,exist_ok=True)
    art=r/"Сборка/artifacts/services";src=art/"gateway/src";rev=art/"gateway/revisions/rb07.1";py=a.venv/"bin/python"
    log=[];results={}
    def say(s):print(s,flush=True);log.append(s)
    def passed(t,msg):results[t]="PASS";say(t+"=PASS "+msg)
    source=(src/"scripts/health-check.sh").read_text();actual=(rev/"scripts/health-check.sh").read_text()
    assert expected_revision(source).splitlines(keepends=True)==actual.splitlines(keepends=True)
    original=(src/"pipelines.yaml").read_text()
    assert original.count("kat-coder-v2.5-dev:256k")==1
    assert (rev/"pipelines.yaml").read_text()==original.replace("kat-coder-v2.5-dev:256k",Q6)
    before=check(run(["git","show",BASE+":Сборка/artifacts/services/render.py"],cwd=r)).stdout
    assert (art/"render.py").read_text()==before.replace("client:'client'","client:'roadwarrior'")
    passed("T1","line-for-line C1-C7, one pipeline model line, one render user literal")
    check(run(["bash","-n",str(rev/"scripts/health-check.sh")]))
    sc=run([str(a.shellcheck),"--severity=warning",str(rev/"scripts/health-check.sh")])
    (e/"rb071_shellcheck.txt").write_text("ShellCheck --severity=warning\n"+sc.stdout+sc.stderr+"exit="+str(sc.returncode)+"\n")
    check(sc)
    check(run([str(py),"-I","-c","import yaml,sys; d=yaml.safe_load(open(sys.argv[1])); assert d['pipelines']['smoke']['steps'][0]['model']==sys.argv[2]",str(rev/"pipelines.yaml"),Q6]))
    check(run([str(py),"-I","-m","pip","check"]))
    check(run([str(py),"-I","-c","import importlib.metadata as m,sys; from pathlib import Path; rows=[x for x in Path(sys.argv[1]).read_text().splitlines() if x and not x.startswith('#')]; assert all(m.version(x.split('==')[0])==x.split('==')[1].split()[0] for x in rows); print('LOCK=PASS')",str(art/"gateway/requirements.lock")]))
    passed("T2","bash -n; ShellCheck zero warnings; YAML; RB-07 lock exact versions; pip check")
    # Stop before starting either process when either mandatory port is occupied.
    sockets=[]
    try:
        for port in [8000,11434]:
            sock=socket.socket();sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);sockets.append(sock);sock.bind(("127.0.0.1",port))
    finally:
        for sock in sockets:sock.close()
    server=None;proc=None
    try:
      with tempfile.TemporaryDirectory(prefix="rb071-") as td:
        td=Path(td);home=td/"home";root=home/"llm-gateway";home.mkdir();shutil.copytree(src,root)
        shutil.copy2(rev/"scripts/health-check.sh",root/"scripts/health-check.sh");shutil.copy2(rev/"pipelines.yaml",root/"pipelines.yaml")
        (root/"venv").symlink_to(a.venv,target_is_directory=True)
        env=os.environ.copy();env.update(HOME=str(home),PYTHONDONTWRITEBYTECODE="1",NO_PROXY="127.0.0.1,localhost",no_proxy="127.0.0.1,localhost")
        check(run([sys.executable,"-I",str(art/"render.py"),"credentials","--output",str(root/".env"),"--operator","vladimir"],env=env))
        values={}
        for line in (root/".env").read_text().splitlines():
            k,v=line.split("=",1);values[k]=v.strip("'")
        tokens=json.loads(values["LLM_GATEWAY_TOKENS"]);assert set(tokens.values())=={"vladimir","roadwarrior","orchestrator"}
        token=next(k for k,v in tokens.items() if v=="vladimir")
        env.update(values)
        bin=td/"stub-bin";bin.mkdir()
        # Deny unexpected commands/arguments. All host results here are synthetic.
        commands={
          "systemctl":'case "$*" in "is-active --quiet ollama.service"|"is-enabled --quiet ollama.service"|"is-active --quiet llm-gateway.service"|"is-enabled --quiet llm-gateway.service"|"is-active --quiet rag-mcp.service"|"is-enabled --quiet rag-mcp.service"|"is-active --quiet docker-mcp.service"|"is-enabled --quiet docker-mcp.service") exit 0;; "show ollama.service --property=Environment --value") echo OLLAMA_CONTEXT_LENGTH=262144;; *) exit 97;; esac',
          "nvidia-smi":'[ "$*" = "-L" ] || exit 97\necho "GPU 0: NVIDIA GeForce RTX 3090 (UUID: offline-stub)"',
          "ollama":'[ "$1" = show ] && [ "$2" = --modelfile ] || exit 97\n[ "$3" = "'+Q6+'" ] || exit 1\necho "PARAMETER num_ctx 262144"',
          "sudo":'[ "$*" = "-n ufw status" ] || exit 97\nprintf "%s\\n" "Status: active" "22/tcp ALLOW 192.168.0.0/24" "8000/tcp ALLOW 192.168.0.0/24" "11434/tcp ALLOW 192.168.0.0/24"',
          "df":'[ "$*" = "-P /" ] || exit 97\nprintf "%s\\n" "Filesystem 1024-blocks Used Available Capacity Mounted on" "/dev/offline-stub 1000000 500000 500000 50% /"'}
        for name,body in commands.items():
            f=bin/name;f.write_text("#!/usr/bin/env bash\n# RB-07.1 OFFLINE STUB, NOT HOST EVIDENCE\n"+body+"\n");f.chmod(0o755)
        (e/"rb071_stub_commands.txt").write_text("Explicit offline PATH stubs. Match accepted live properties, not literal hardware identifiers or firewall inventory.\n"+json.dumps(commands,ensure_ascii=False,indent=2)+"\nStubbed checks: NVIDIA GPU available; four service active/enabled checks; Ollama global context; model num_ctx; UFW active/rule count; disk usage. API/auth/catalog/pipeline/embedding/metrics use real gateway with Ollama HTTP stub.\n")
        env["PATH"]=str(bin)+os.pathsep+env["PATH"]
        server=http.server.ThreadingHTTPServer(("127.0.0.1",11434),Ollama);threading.Thread(target=server.serve_forever,daemon=True).start()
        bootstrap="import sys;sys.path.insert(0,sys.argv[1]);import uvicorn;uvicorn.run('gateway.app:app',host='127.0.0.1',port=8000,log_level='error',access_log=False)"
        with tempfile.TemporaryFile(mode="w+") as err:
          proc=subprocess.Popen([str(py),"-I","-B","-c",bootstrap,str(root)],cwd=root,env=env,stdout=subprocess.DEVNULL,stderr=err)
          for _ in range(150):
            if proc.poll() is not None:
                err.seek(0);raise AssertionError("gateway startup: "+err.read().replace(token,"<TEST_TOKEN>"))
            try:health=gateway_json("/health");break
            except (OSError,ValueError):time.sleep(.1)
          else:raise AssertionError("gateway startup timeout")
          assert health["pipelines_count"]==1, "STOP: pipelines_count != 1"
          revision=run(["bash",str(root/"scripts/health-check.sh")],env=env)
          say("REVISION FULL OUTPUT:\n"+revision.stdout+revision.stderr)
          check(revision);assert revision.stdout.count("[OK]")==20 and "[FAIL]" not in revision.stdout
          passed("T3","20/20 exit 0, temporary HOME, real gateway from accepted source, locked venv")
          control=run(["bash",str(src/"scripts/health-check.sh")],env=env)
          say("CAPTURED FULL OUTPUT:\n"+control.stdout+control.stderr)
          failures={line[7:] for line in control.stdout.splitlines() if line.startswith("[FAIL] ")}
          wanted={"Required Ollama models present","Three primary LLMs have num_ctx = 262144","Gateway health contract","Required models published by Gateway","Smoke pipeline inherits 256k Gateway context"}
          assert control.returncode==1 and failures==wanted,(failures,wanted)
          assert control.stdout.count("[OK]")==15
          Ollama.models=[EMBED]
          missing=run(["bash",str(root/"scripts/health-check.sh")],env=env)
          say("REVISION WITHOUT Q6 FULL OUTPUT:\n"+missing.stdout+missing.stderr)
          assert missing.returncode==1 and "[FAIL] Required Ollama models present" in missing.stdout
          Ollama.models=[Q6,EMBED]
          assert "qwen2.5-coder:7b" not in Ollama.models and len(Ollama.models)==2
          passed("T4","captured 15 PASS / 5 model-dependent FAIL; missing Q6 rejected; optional models absent in successful T3")
          payload={"pipeline":"smoke","task":"Return OK"}
          answer=gateway_json("/v1/orchestrate",payload,token)
          assert any(x["path"]=="/api/chat" and x["body"].get("model")==Q6 for x in Ollama.requests), "Q6 chat not reached"
          assert "OK" in json.dumps(answer), "gateway did not return stub OK"
          assert gateway_json("/health")["pipelines_count"]==1
          captured=[x for x in Ollama.requests if x["path"]=="/api/chat"][-1]
          (e/"rb071_orchestrate_request.json").write_text(json.dumps({"gateway_request":payload,"ollama_request":captured,"gateway_response":answer},ensure_ascii=False,indent=2)+"\n")
          passed("T5","POST /v1/orchestrate -> Ollama /api/chat model Q6 -> gateway OK; pipelines_count=1")
          assert "[OK]   Gateway auth configuration + permissions" in revision.stdout
          assert "[OK]   Gateway auth configuration + permissions" in control.stdout
          runbook=(r/"Сборка/50_Сервисы_Gateway_MCP.md").read_text()
          guard=runbook.split("# RB071_OPERATOR_GUARD\n",1)[1].split("umask 077",1)[0]
          for operator,expected in [("another_operator",1),("vladimir",0)]:
            guardenv=env.copy();guardenv["LAB_OPERATOR"]=operator
            target=td/("guard-"+operator)
            trial=run(["bash","-c",guard+'\nprintf generated > "$1"',"_",str(target)],env=guardenv)
            assert trial.returncode==expected
            assert target.exists()==(expected==0)
          passed("T6","generated 0600 env passes auth in both scripts; exact runbook guard rejects other operator before generation")
          proc.terminate();proc.wait(timeout=10);proc=None
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            try:proc.wait(timeout=10)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
        if server:server.shutdown();server.server_close()
    # Run unmodified RB-07 T1 and T3 statements from its existing main function.
    oldtest=r/"Сборка/tests/services/test_services.py";tree=ast.parse(oldtest.read_text())
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="main")
    cut=None
    for i,n in enumerate(fn.body):
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Subscript) and isinstance(t.value,ast.Name) and t.value.id=="out" and isinstance(t.slice,ast.Constant) and t.slice.value=="T3" for t in n.targets):cut=i+1;break
    assert cut is not None
    fn.body=fn.body[:cut]+ast.parse("print('RB07_T1='+out['T1']['status']+'; RB07_T3='+out['T3']['status'])").body
    with tempfile.TemporaryDirectory(prefix="rb071-regress-") as td:
        f=Path(td)/"rb07_t1_t3.py";f.write_text(ast.unparse(tree))
        old=check(run([str(py),"-I",str(f),"--artifacts",str(art),"--evidence",str(Path.home()/"ailab-rebuild-evidence/RB-07"),"--capture",str(Path.home()/"ailab-rebuild-evidence/RB-02/extract"),"--venvs",str(a.venv.parent)]))
        say(old.stdout);assert "RB07_T1=PASS; RB07_T3=PASS" in old.stdout
    # Compare every gateway/src file to its recorded SOURCE_SET SHA256.
    rows=list(csv.DictReader(io.StringIO((art/"SOURCE_SET.tsv").read_text()),delimiter="\t"));verified=0
    for row in rows:
        vals=list(row.values());sha=next((v for v in vals if re.fullmatch("[a-f0-9]{64}",v or "")),None)
        if not sha:continue
        paths=[]
        for value in vals:
            if not value:continue
            if value.startswith("gateway/"):paths.append(art/value)
            if "home/vladimir/llm-gateway/" in value:paths.append(src/value.split("home/vladimir/llm-gateway/",1)[1])
        for path in paths:
            if path.is_file():
                assert hashlib.sha256(path.read_bytes()).hexdigest()==sha
                verified+=1;break
    assert verified==15,verified
    assert not check(run(["git","diff",BASE,"--","Сборка/artifacts/services/gateway/src"],cwd=r)).stdout
    passed("T7","gateway/src unchanged; recorded source hashes; RB07 original T1/T3 PASS; files="+str(verified))
    (e/"rb071_tests.json").write_text(json.dumps(results,indent=2)+"\n")
    (e/"rb071_tests.log").write_text("\n".join(log)+"\n")
if __name__=="__main__":main()
