#!/usr/bin/env python3
"""Isolated deployment transaction tests. No live mode, GPU, or service manager."""
import copy, hashlib, importlib.util, json, os, pathlib, shutil, subprocess, sys, tempfile, unittest
from unittest.mock import patch
P=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("deploy",P/"deploy.py");d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
def write(p,data):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes(data if isinstance(data,bytes) else data.encode())
def tree(root):
    return {str(p.relative_to(root)):d.state(p) for p in sorted(root.rglob("*"))}
class Deployment(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory(prefix="mbip05-transaction-");self.addCleanup(self.t.cleanup)
        self.work=pathlib.Path(self.t.name);self.root=self.work/"root";self.root.mkdir()
        write(self.root/".mbip05-fixture","MBIP05_ISOLATED_FIXTURE\n")
        self.b=self.work/"backups";self.b.mkdir(mode=0o700)
        self.ev=self.work/"evidence";self.ev.mkdir(mode=0o700)
        write(self.ev/"fixture.txt","SYNTHETIC TEST ONLY\n");(self.ev/"fixture.txt").chmod(0o600)
        for u in (*d.OLD,d.BOOT,*d.KEEP):
            text="[Unit]\nDescription=Isolated fixture "+u+"\n[Service]\nExecStart=/bin/true\n"
            if u!=d.BOOT:text+="[Install]\nWantedBy="+("default.target" if u==d.OLD[0] else "multi-user.target")+"\n"
            write(self.root/d.UNITS/u,text)
        for n in ("default.target","multi-user.target"):write(self.root/d.UNITS/n,"[Unit]\nDescription=Fixture\n")
        write(self.root/d.UNITS/"mbip-strata.service.d/96-mbip05-profiles.conf","[Service]\nEnvironment=FIXTURE=1\n")
        subprocess.run(["systemctl","--root="+str(self.root),"enable",*d.OLD,*d.KEEP],check=True,capture_output=True)
        for n in d.PROFILES:
            q="strata-mbip-"+n+".json";write(self.root/"etc/mbip05/profiles"/q,(P/"stage/profiles"/q).read_bytes())
        write(self.root/"usr/local/sbin/mbip-backend",(P.parent/"mbip-backend").read_bytes())
        intent=json.loads((P/"pi-config-intent.json").read_text())
        models={"providers":{"ailab-ollama":{"models":[{"id":"fixture-original"}],"baseUrl":"http://127.0.0.1:11434/v1"},"ailab-strata":{"api":"openai-completions","baseUrl":"http://127.0.0.1:18081/v1","models":[{"id":x["id"],"reasoning":True,"input":["text"],"thinkingLevelMap":x["thinkingLevelMap"],"contextWindow":32768,"maxTokens":2048,"extra":"preserve"} for x in intent["models"]]},"unrelated":{"models":[]}}}
        settings={"defaultProvider":"ailab-ollama","defaultModel":"fixture-original","defaultThinkingLevel":"max","compaction":{"enabled":True,"reserveTokens":32768,"keepRecentTokens":20000,"modelOverrides":{"ailab-ollama/fixture-original":{"reserveTokens":32768}}},"modelThinkingLevels":{"ailab-ollama/fixture-original":"max"},"other":{"keep":True}}
        for n,obj in [("models.json",models),("settings.json",settings)]:write(self.root/".pi/agent"/n,d.jsonbytes(obj));(self.root/".pi/agent"/n).chmod(0o600)
        self.original=tree(self.root)
    def receipt(self,scope,**kw):
        h,_=d.manifest();r=dict(kind="fixture",scope=scope,root=str(self.root),package_manifest_sha256=h,profiles=d.PROFILES,power_w=300,owner_approved=True,gates={k:dict(result="PASS",evidence="fixture.txt",sha256=d.sha((self.ev/"fixture.txt").read_bytes())) for k in d.GATES})
        if scope=="client":r["client_before"]={n:d.sha((self.root/".pi/agent"/n).read_bytes()) for n in ("models.json","settings.json")}
        r.update(kw);p=self.ev/(scope+".json");write(p,d.jsonbytes(r));p.chmod(0o600);return p
    def invoke(self,scope,op,name="tx",receipt=None,extra=(),ok=True):
        args=[sys.executable,"-IB",str(P/"deploy.py"),scope+"-"+op,"--root",str(self.root),"--backup",str(self.b/name)]
        if op=="install":args+=["--receipt",str(receipt or self.receipt(scope))]
        q=subprocess.run(args+list(extra),capture_output=True,text=True,timeout=30)
        self.assertEqual(q.returncode==0,ok,q.stdout+q.stderr)
        return q
    def journal(self,name="tx"):return json.loads((self.b/name/"transaction.json").read_text())
    def test_server_success_rollback_and_repeat(self):
        self.invoke("server","install");j=self.journal();self.assertEqual(j["status"],"INSTALLED")
        d.check_boot(self.root,True)
        self.assertTrue(all(d.state(self.root/e["path"])==e["after"] for e in j["entries"]))
        self.invoke("server","rollback");self.assertEqual(tree(self.root),self.original)
        self.invoke("server","rollback");self.assertEqual(tree(self.root),self.original)
    def test_server_fail_every_mutation(self):
        count=len(d.server_plan(self.root))
        for i in range(1,count+1):
            with self.subTest(step=i):
                name="fail-"+str(i)
                self.invoke("server","install",name,extra=("--fixture-fail-after",str(i)),ok=False)
                self.assertEqual(self.journal(name)["status"],"ROLLED_BACK")
                self.assertEqual(tree(self.root),self.original)
        print("FAULT_STEPS",count)
    def test_postcheck_failure_rolls_back(self):
        plan=d.server_plan(self.root);original=d.postcheck
        def fail(root,scope,installed,live):
            if installed:raise d.Refused("synthetic verify failure")
            return original(root,scope,installed,live)
        with patch.object(d,"postcheck",side_effect=fail):
            with self.assertRaises(d.Refused):d.transact(self.root,self.b/"tx","server",False,plan)
        self.assertEqual(tree(self.root),self.original)
    def test_wrong_profile_refused(self):
        p=self.root/"etc/mbip05/profiles/strata-mbip-inkling.json";p.write_bytes(p.read_bytes()+b" ")
        before=tree(self.root);self.invoke("server","install",ok=False);self.assertEqual(tree(self.root),before);self.assertFalse((self.b/"tx").exists())
    def test_missing_gate_refused(self):
        r=self.receipt("server");x=json.loads(r.read_text());x["gates"]["inkling_e01"]["result"]="BLOCKED";write(r,d.jsonbytes(x))
        self.invoke("server","install",receipt=r,ok=False);self.assertEqual(tree(self.root),self.original)
    def test_wrong_receipt_fingerprint_refused(self):
        r=self.receipt("server",package_manifest_sha256="0"*64)
        self.invoke("server","install",receipt=r,ok=False);self.assertEqual(tree(self.root),self.original)
    def test_fixture_receipt_live_refused(self):
        self.invoke("server","install",extra=("--live",),ok=False);self.assertEqual(tree(self.root),self.original)
    def test_existing_artifact_refused(self):
        p=self.root/next(iter(d.FILES.values()));write(p,"foreign")
        before=tree(self.root);self.invoke("server","install",ok=False);self.assertEqual(tree(self.root),before)
    def test_foreign_edit_rollback_refused_without_partial_restore(self):
        self.invoke("server","install");p=self.root/next(iter(d.FILES.values()));p.write_bytes(b"third-party")
        before=tree(self.root);self.invoke("server","rollback",ok=False);self.assertEqual(tree(self.root),before)
    def test_foreign_file_in_new_dir_refuses_rollback(self):
        self.invoke("server","install");write(self.root/"etc/tmpfiles.d/foreign.conf","foreign")
        before=tree(self.root);self.invoke("server","rollback",ok=False);self.assertEqual(tree(self.root),before)
    def test_interrupted_journal_recovery(self):
        plan=d.server_plan(self.root);entries=[dict(path=k,before=d.state(self.root/k),after=v) for k,v in plan.items()]
        b=self.b/"tx";b.mkdir(mode=0o700);d.writejournal(b/"transaction.json",dict(root=str(self.root),scope="server",live=False,status="PREPARED",entries=entries))
        for e in entries[:4]:d.put(self.root/e["path"],e["after"])
        self.invoke("server","rollback");self.assertEqual(tree(self.root),self.original)
    def test_client_preservation_and_rollback(self):
        self.invoke("client","install");mp=self.root/".pi/agent/models.json";sp=self.root/".pi/agent/settings.json"
        m=json.loads(mp.read_text());s=json.loads(sp.read_text())
        oldm=json.loads(d.base64.b64decode(self.original[".pi/agent/models.json"]["data"]))
        olds=json.loads(d.base64.b64decode(self.original[".pi/agent/settings.json"]["data"]))
        self.assertEqual({k:v for k,v in m["providers"].items() if k!=d.PROVIDER},{k:v for k,v in oldm["providers"].items() if k!=d.PROVIDER})
        self.assertEqual(s["defaultModel"],d.INK);self.assertEqual(s["defaultThinkingLevel"],olds["defaultThinkingLevel"])
        self.assertEqual(s["other"],olds["other"])
        for model in m["providers"][d.PROVIDER]["models"]:
            self.assertEqual(model["contextWindow"],262144);self.assertEqual(model["extra"],"preserve")
            self.assertEqual(model["maxTokens"],8192 if model["id"]==d.FLASH else 4096)
            self.assertEqual(s["modelThinkingLevels"][d.PROVIDER+"/"+model["id"]],"low")
        self.invoke("client","rollback");self.assertEqual(tree(self.root),self.original)
    def test_client_fail_each_file(self):
        for i in (1,2):
            name="fail-"+str(i);self.invoke("client","install",name,extra=("--fixture-fail-after",str(i)),ok=False)
            self.assertEqual(self.journal(name)["status"],"ROLLED_BACK");self.assertEqual(tree(self.root),self.original)
    def test_client_stale_receipt(self):
        r=self.receipt("client");p=self.root/".pi/agent/settings.json";p.write_bytes(p.read_bytes()+b" ")
        before=tree(self.root);self.invoke("client","install",receipt=r,ok=False);self.assertEqual(tree(self.root),before)
    def test_client_foreign_edit(self):
        self.invoke("client","install");p=self.root/".pi/agent/settings.json";p.write_bytes(p.read_bytes()+b" ")
        before=tree(self.root);self.invoke("client","rollback",ok=False);self.assertEqual(tree(self.root),before)
if __name__=="__main__":unittest.main(verbosity=2)
