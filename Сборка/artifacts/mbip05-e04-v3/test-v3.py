#!/usr/bin/env python3
"""E04 helper routing only: synthetic subprocesses, no real SSH, API or inference."""
import json,os,pathlib,shutil,socket,subprocess,tempfile,unittest
HERE=pathlib.Path(__file__).resolve().parent
INK="inkling-2-mini-sq-20";FLASH="qwen3.8-flash-next-ud-q6_k_xl"
Q27="qwen3.8-27b-gsq-rco:iq3s-mtp-262k";Q6="qwen3.8-flash-next:125b-a6b-q6_K-ab-262k"
FAKE=r'''#!/usr/bin/env python3
import json,os,pathlib,sys,socket
mode=os.environ["CASE"];cmd=pathlib.Path(sys.argv[0]).name;a=sys.argv[1:]
def status(which):
 return {"model":"inkling-2-mini-sq-20" if which=="inkling" else "qwen3.8-flash-next-ud-q6_k_xl","started":1,"loaded":True,"context":{"native":262144,"max_positions":262144}}
def tags():return {"models":[{"name":"qwen3.8-27b-gsq-rco:iq3s-mtp-262k","digest":"9842917e7505"+"0"*52},{"name":"qwen3.8-flash-next:125b-a6b-q6_K-ab-262k","digest":"09b8aff72a79"+"0"*52}]}
if cmd=="ss":
 if mode not in ("absent","fresh","authfail") or pathlib.Path(os.environ["HOME"],"fake-forward").exists():print('LISTEN 0 128 127.0.0.1:18081 0.0.0.0:* users:(("ssh",pid='+("111" if mode=="foreign" else "222")+',fd=6))')
elif cmd=="ssh":
 if "-O" in a and "check" in a:
  if mode in ("fresh","authfail") and not pathlib.Path(os.environ["HOME"],"fake-forward").exists():sys.exit(1)
  print("Master running (pid=222)",file=sys.stderr)
 elif "-M" in a:
  if mode=="authfail":sys.exit(255)
  assert mode=="fresh"
  sock=socket.socket(socket.AF_UNIX);sock.bind(a[a.index("-S")+1]);sock.close()
  pathlib.Path(os.environ["HOME"],"fake-forward").touch()
 elif a[-1]=="true":pass
 elif a[-1]=="/usr/local/sbin/mbip-backend status" or a[-1]=="status":
  old="active" if mode=="ollama" else "inactive";st="inactive" if mode=="ollama" else "active"
  if mode=="mixed":old="active"
  print("SERVICES "+json.dumps({k:{"ActiveState":old} for k in ["ollama.service","llm-gateway.service","rag-mcp.service"]}|{"mbip-strata.service":{"ActiveState":st}}))
  p="flash" if mode=="flash" else "inkling";print("SELECTED_PROFILE "+p+" "+status(p)["model"]);print("LOADED true")
 elif "/api/tags" in a[-1]:print(json.dumps(tags()))
 elif "/v1/status" in a[-1]:print(json.dumps(status("flash" if mode=="flash" else "inkling")))
 else:raise SystemExit("unexpected SSH operation")
elif cmd=="curl":
 if "/api/tags" in a[-1]:print(json.dumps(tags()))
 elif "/v1/status" in a[-1]:print(json.dumps(status("flash" if mode in ("flash","wrongapi") else "inkling")))
 else:raise SystemExit("unexpected HTTP operation")
elif cmd=="pi":print("PI_ARGS "+json.dumps(a))
'''
class Helper(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);r=pathlib.Path(self.tmp.name);self.home=r/"home";self.home.mkdir();self.bin=r/"bin";self.bin.mkdir();runtime=r/"runtime";runtime.mkdir(mode=0o700)
  for c in ("ssh","ss","curl"):
   p=self.bin/c;p.write_text(FAKE);p.chmod(0o700)
  b=self.home/".local/bin";b.mkdir(parents=True)
  for n in ("ailab-mode","ailab-pi","ailab-ide"):shutil.copy2(HERE/n,b/n);(b/n).chmod(0o700)
  p=b/"pi";p.write_text(FAKE);p.chmod(0o700);self.helper=b
  p=self.home/".pi/agent";p.mkdir(parents=True);(p/"models.json").write_text(json.dumps({"providers":{"ailab-ollama":{"baseUrl":"http://127.0.0.1:11434/v1"}}}))
  q=self.home/".config/ailab-mbip05";q.mkdir(parents=True,mode=0o700);self.sock=socket.socket(socket.AF_UNIX);self.addCleanup(self.sock.close);sock=r/"adopted.sock";self.sock.bind(str(sock));p=q/"master-path";p.write_text(str(sock)+"\n");p.chmod(0o600)
  self.env=dict(os.environ,HOME=str(self.home),XDG_RUNTIME_DIR=str(runtime),PATH=str(self.bin)+":"+os.environ["PATH"])
 def run_case(self,case,helper,*args,rc=0):
  r=subprocess.run([str(self.helper/helper),*args],env=dict(self.env,CASE=case),capture_output=True,text=True,timeout=10);self.assertEqual(r.returncode,rc,r.stdout+r.stderr);return r.stdout+r.stderr
 def test_inkling(self):
  s=self.run_case("inkling","ailab-pi","inkling");self.assertIn(json.dumps(["--offline","--provider","ailab-strata","--model",INK,"--thinking","low"]),s)
 def test_flash(self):
  s=self.run_case("flash","ailab-pi","flash");self.assertIn(json.dumps(["--offline","--provider","ailab-strata","--model",FLASH,"--thinking","low"]),s)
 def test_q27(self):
  s=self.run_case("ollama","ailab-pi","q27");self.assertIn(json.dumps(["--offline","--provider","ailab-ollama","--model",Q27,"--thinking","medium"]),s)
 def test_reserve_q6(self):
  s=self.run_case("ollama","ailab-pi","q6");self.assertIn(json.dumps(["--offline","--provider","ailab-ollama","--model",Q6,"--thinking","max"]),s)
 def test_block_switch(self):
  for m in ("flash","q27","q6"):
   s=self.run_case("inkling","ailab-pi",m,rc=3);self.assertNotIn("PI_ARGS",s);self.assertIn("G0 open",s)
 def test_foreign_listener(self):
  self.assertIn("owner mismatch",self.run_case("foreign","ailab-mode","status",rc=1))
 def test_absent_forward(self):
  self.assertIn("Forward absent",self.run_case("absent","ailab-mode","status",rc=1))
 def test_wrong_api(self):
  self.run_case("wrongapi","ailab-mode","status",rc=1)
 def test_mixed(self):
  self.assertIn("not ready",self.run_case("mixed","ailab-mode","status",rc=1))
 def test_selector_override(self):
  self.assertIn("Conflicting selector",self.run_case("inkling","ailab-pi","inkling","--model","other",rc=2))
 def test_current_exact(self):
  for mode,expected in (("inkling","ailab-strata/"+INK),("flash","ailab-strata/"+FLASH),("ollama","ailab-ollama/"+Q27)):
   r=subprocess.run([str(self.helper/"ailab-mode"),"current"],env=dict(self.env,CASE=mode),capture_output=True,text=True,timeout=10);self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(r.stdout.strip(),expected)
 def test_ide_args(self):
  for mode,expected,think in (("inkling","ailab-strata/"+INK,"low"),("flash","ailab-strata/"+FLASH,"low"),("ollama","ailab-ollama/"+Q27,"medium")):
   s=self.run_case(mode,"ailab-ide","--extension","fixture.js");self.assertIn(json.dumps(["--offline","--model",expected,"--thinking",think,"--extension","fixture.js"]),s)
 def test_ide_refuses_mixed(self):
  self.assertNotIn("PI_ARGS",self.run_case("mixed","ailab-ide",rc=1))
 def test_fresh_path_recovery(self):
  ref=self.home/".config/ailab-mbip05/master-path";old=ref.read_text();b=pathlib.Path(self.env["XDG_RUNTIME_DIR"])/"ailab-mbip05";b.mkdir(mode=0o700);stale=b/"llm.sock";stale.touch()
  self.run_case("fresh","ailab-mode","connect");new=pathlib.Path(ref.read_text().strip());self.assertNotEqual(ref.read_text(),old);self.assertTrue(new.is_socket());self.assertTrue(stale.is_file());self.assertEqual(new.parent.parent,b);self.assertEqual(ref.stat().st_mode&0o777,0o600)
 def test_auth_failure_preserves_reference(self):
  ref=self.home/".config/ailab-mbip05/master-path";before=ref.read_bytes();self.run_case("authfail","ailab-mode","connect",rc=1);self.assertEqual(ref.read_bytes(),before)
if __name__=="__main__":unittest.main(verbosity=2)
