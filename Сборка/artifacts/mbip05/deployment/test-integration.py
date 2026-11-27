import json, pathlib, unittest, tempfile, urllib.error
from unittest.mock import patch
from importlib.machinery import SourceFileLoader
from importlib.util import spec_from_loader,module_from_spec
ROOT=pathlib.Path(__file__).resolve().parent
def load(n,p):
    l=SourceFileLoader(n,str(p));s=spec_from_loader(n,l);m=module_from_spec(s);l.exec_module(m);return m
b=load("switcher",ROOT.parent/"mbip-backend")
p=load("postboot",ROOT/"stage/mbip05-postboot-readiness")
class Sim:
    def __init__(self):
        self.states={u:"active" for u in b.OLD};self.states[b.STRATA]="inactive";self.loaded=False
        self.events=[];self.fail_load=False;self.busy=False;self.unreleased=False;self.wrong_model=False;self.ollama_version="0.35.1"
    def unit(self,u):
        return {"LoadState":"loaded","ActiveState":self.states.get(u,"inactive"),"MainPID":"71" if self.states.get(u)=="active" else "0"}
    def listeners(self,*ports):
        return "\n".join(str(x) for u,x in b.PORTS.items() if x in ports and self.states[u]=="active")
    def resources(self):
        return {"compute_pids":["99"] if self.loaded or self.unreleased else [],"used_mib":21228 if self.loaded or self.unreleased else 1,"free_mib":2898 if self.loaded or self.unreleased else 24124,"mem_available_kib":64000000,"power_w":300.0}
    def run(self,*args,**kwargs):
        if args[:2]==("systemctl","list-units") or args[:2]==("systemctl","list-jobs"):return ""
        assert args[0]=="systemctl",args
        op=args[1];assert op in ("start","stop"),args
        for u in args[2:]:
            self.events.append((op,u))
            if op=="start":self.states[u]="active"
            else:
                self.states[u]="inactive"
                if u==b.STRATA:self.loaded=False
        return ""
    def api(self,port,route,body=None,timeout=3):
        self.events.append((port,route))
        if port==11434:return {"version":self.ollama_version}
        if port==8000:return {"ollama":"ok"}
        if route=="/v1/status":return {"loaded":self.loaded}
        if route=="/v1/models":return {"data":[{"id":"wrong" if self.wrong_model else b.selected_profile()[1]}]}
        if route=="/v1/load":
            if self.fail_load:
                self.fail_load=False;raise OSError("injected load failure")
            self.loaded=True;return {"loaded":True}
        if route=="/v1/unload":
            if self.busy:raise urllib.error.HTTPError("mock",409,"busy",{},None)
            self.loaded=False;return {"loaded":False}
        raise AssertionError(route)
class Transition(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        root=pathlib.Path(self.tmp.name)
        for n in ("flash","inkling"):
            (root/f"strata-mbip-{n}.json").write_bytes((ROOT/"stage/profiles"/f"strata-mbip-{n}.json").read_bytes())
        self.sim=Sim();self.clock=0
        def tick():self.clock+=1;return self.clock
        for obj,k,v in [(b,"PROFILE_DIR",root),(b,"ACTIVE_POINTER",root/"active.json"),(b,"unit",self.sim.unit),(b,"run",self.sim.run),(b,"api",self.sim.api),(b,"listeners",self.sim.listeners),(b,"sockets",lambda ports:[]),(b,"resources",self.sim.resources),(b,"engine_pids",lambda: [99] if self.sim.loaded or self.sim.unreleased else []),(b.time,"monotonic",tick),(b.time,"sleep",lambda _:None)]:
            q=patch.object(obj,k,v);q.start();self.addCleanup(q.stop)
        b.ACTIVE_POINTER.symlink_to(root/"strata-mbip-inkling.json")
    def test_full_mode_cycle(self):
        b.switch("strata",True);self.assertTrue(b.healthy("strata"))
        b.switch_profile("flash",True);self.assertEqual(b.selected_profile()[0],"flash")
        b.switch("ollama",True);self.assertTrue(b.healthy("ollama"))
        b.switch_profile("inkling",True);self.assertTrue(b.healthy("strata"));self.assertEqual(b.selected_profile()[0],"inkling")
        ev=self.sim.events;self.assertLess(ev.index(("stop",b.OLLAMA)),ev.index(("start",b.STRATA)))
        self.assertLess(ev.index(("start",b.OLLAMA)),ev.index(("start",b.GATEWAY)))
    def test_load_error_recovers_previous_mode(self):
        self.sim.fail_load=True
        with self.assertRaises(OSError):b.switch("strata",True)
        self.assertTrue(b.healthy("ollama"))
    def test_profile_load_error_restores_original_profile(self):
        b.switch("strata",True);self.sim.fail_load=True
        with self.assertRaises(OSError):b.switch_profile("flash",True)
        self.assertEqual(b.selected_profile()[0],"inkling");self.assertTrue(b.healthy("strata"))
    def test_wrong_model_times_out_and_recovers(self):
        self.sim.wrong_model=True
        with self.assertRaisesRegex(b.Refused,"Readiness timeout"):b.switch("strata",True)
        self.assertTrue(b.healthy("ollama"))
    def test_unreleased_resources_no_new_start(self):
        self.sim.unreleased=True
        with self.assertRaisesRegex(b.Refused,"Recovery withheld"):b.switch("strata",True)
        self.assertFalse(any(x[0]=="start" for x in self.sim.events))
    def test_busy_preserves_engine_and_pointer(self):
        b.switch("strata",True);self.sim.busy=True
        with self.assertRaisesRegex(b.Refused,"busy"):b.switch_profile("flash",True)
        self.assertTrue(self.sim.loaded);self.assertEqual(b.selected_profile()[0],"inkling")
    def test_ollama_readiness_wrong_version(self):
        b.switch("strata",True);self.sim.ollama_version="0.0.0"
        with self.assertRaisesRegex(b.Refused,"Ollama HTTP"):b.switch("ollama",True)
        self.assertNotIn(("start",b.GATEWAY),self.sim.events)
class FakeHost:
    def __init__(self):
        self.states={u:"inactive" for u in p.OLD};self.states.update({p.STRATA:"active","ailab-gpu-power.service":"active"})
        self.enables={u:"disabled" for u in p.OLD};self.enables.update({p.STRATA:"enabled","ailab-gpu-power.service":"enabled","ailab-postboot-check.service":"enabled"})
        self.st={"loaded":False,"model":p.MODEL,"context":{"native":262144,"max_positions":262144},"activity":{"in_flight":0},"concurrency":{"serving":1}}
        self.raw=(ROOT/"stage/profiles/strata-mbip-inkling.json").read_bytes();self.ptr=p.PROFILE
        self.ids=[{"id":p.MODEL}];self.gpu="300.00, 36, Not Active, Not Active";self.socket="LISTEN 0 256 127.0.0.1:18081 0.0.0.0:*";self.competing="";self.gets=[]
    def enabled(self,u):return self.enables[u]
    def state(self,u):return self.states[u]
    def link(self,x):return self.ptr
    def read(self,x):return self.raw
    def run(self,*a):
        assert a[0]=="nvidia-smi",a
        return self.gpu
    def listeners(self,*ports):return self.socket if ports==(18081,) else self.competing
    def get(self,route):
        self.gets.append(route);return self.st if route=="/v1/status" else {"data":self.ids}
class Postboot(unittest.TestCase):
    def setUp(self):self.h=FakeHost()
    def check_refuse(self,match):
        with self.assertRaisesRegex(p.Refused,match):p.inspect(self.h)
    def test_lazy_readiness_never_claims_functional(self):
        r=p.inspect(self.h);self.assertEqual(r["result"],"READY_PENDING_FUNCTIONAL");self.assertFalse(r["loaded"]);self.assertEqual(r["functional"],"NOT_RUN");self.assertEqual(self.h.gets,["/v1/status","/v1/models"])
    def test_loaded_readiness(self):
        self.h.st["loaded"]=True;self.assertTrue(p.inspect(self.h)["loaded"])
    def test_mixed_mode(self):
        self.h.states[p.OLD[0]]="active";self.check_refuse("Mixed")
    def test_boot_enablement(self):
        self.h.enables[p.OLD[0]]="enabled";self.check_refuse("enablement")
    def test_wrong_pointer(self):
        self.h.ptr="/etc/mbip05/profiles/strata-mbip-flash.json";self.check_refuse("pointer")
    def test_fingerprint(self):
        self.h.raw+=b" ";self.check_refuse("fingerprint")
    def test_wrong_model(self):
        self.h.ids=[{"id":"wrong"}];self.check_refuse("model mismatch")
    def test_wrong_effective_window(self):
        self.h.st["loaded"]=True;self.h.st["context"]["max_positions"]=32768;self.check_refuse("Effective context")
    def test_wrong_power(self):
        self.h.gpu="350, 36, Not Active, Not Active";self.check_refuse("Power/thermal")
    def test_thermal_flag(self):
        self.h.gpu="300, 65, Not Active, Active";self.check_refuse("Power/thermal")
    def test_competing_listener(self):
        self.h.competing="stale";self.check_refuse("Competing")
    def test_nonloopback(self):
        self.h.socket=self.h.socket.replace("127.0.0.1","0.0.0.0");self.check_refuse("loopback")
    def test_inference_active(self):
        self.h.st["activity"]["in_flight"]=1;self.check_refuse("active inference")
if __name__=="__main__":unittest.main(verbosity=2)
