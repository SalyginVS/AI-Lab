"""Candidate MBIP-05 profile transition tests; no services or GPUs used."""
from pathlib import Path
import json,tempfile,unittest,urllib.error
from unittest.mock import patch
from importlib.machinery import SourceFileLoader
from importlib.util import spec_from_loader,module_from_spec
loader=SourceFileLoader("candidate_backend",str(Path(__file__).with_name("mbip-backend")))
spec=spec_from_loader(loader.name,loader); b=module_from_spec(spec);loader.exec_module(b)

class Profiles(unittest.TestCase):
 def setUp(self):
    self.work=tempfile.TemporaryDirectory()
    self.root=Path(self.work.name)
    self.patch=patch.object(b,"PROFILE_DIR",self.root);self.patch.start()
    self.pointer=patch.object(b,"ACTIVE_POINTER",self.root/"active.json");self.pointer.start()
    for name,(filename,ids) in b.PROFILES.items():
        model=sorted(ids)[-1]
        (self.root/filename).write_text(json.dumps(dict(model_name=model,host="127.0.0.1",port=18081,parallel=1,lazy_load=True)))
    b.ACTIVE_POINTER.symlink_to(self.root/b.PROFILES["flash"][0])
 def tearDown(self):
    self.pointer.stop();self.patch.stop();self.work.cleanup()
 def test_atomic_selection(self):
    with patch.object(b,"stopped",return_value=True),patch.object(b,"listeners",return_value=""):
        b.select_profile("inkling")
    self.assertEqual(b.selected_profile()[0],"inkling")
 def test_disallow_running_change(self):
    with patch.object(b,"stopped",return_value=False):
        with self.assertRaises(b.Refused):b.select_profile("inkling")
    self.assertEqual(b.selected_profile()[0],"flash")
 def test_wrong_profile_id_refused(self):
    f=self.root/b.PROFILES["inkling"][0]
    d=json.loads(f.read_text());d["model_name"]="unapproved";f.write_text(json.dumps(d))
    with self.assertRaises(b.Refused):b.profile_for("inkling")
 def test_wrong_listener_config_refused(self):
    f=self.root/b.PROFILES["inkling"][0]
    d=json.loads(f.read_text());d["host"]="0.0.0.0";f.write_text(json.dumps(d))
    with self.assertRaises(b.Refused):b.profile_for("inkling")
 def test_api_id_mismatch(self):
    with patch.object(b,"api",side_effect=[{"loaded":True},{"data":[{"id":"wrong"}]}]):
        self.assertFalse(b.strata_ready())
 def test_drain_required_before_change(self):
    with patch.object(b,"stop_strata") as stop,patch.object(b,"switch") as switch:
        with self.assertRaisesRegex(b.Refused,"--drained"):b.switch_profile("inkling",False)
        stop.assert_not_called();switch.assert_not_called()
    self.assertEqual(b.selected_profile()[0],"flash")
 def test_busy_preserves_pointer(self):
    with patch.object(b,"active",return_value=True),patch.object(b,"stopped",return_value=True),patch.object(b,"listeners",return_value=""),patch.object(b,"no_activation"),patch.object(b,"stop_strata",side_effect=b.Refused("busy")),patch.object(b,"switch") as switch:
        with self.assertRaisesRegex(b.Refused,"busy"):b.switch_profile("inkling",True)
        switch.assert_not_called()
    self.assertEqual(b.selected_profile()[0],"flash")
 def test_failure_restores_previous_selection(self):
    with patch.object(b,"active",return_value=True),patch.object(b,"stopped",return_value=True),patch.object(b,"listeners",return_value=""),patch.object(b,"no_activation"),patch.object(b,"stop_strata"),patch.object(b,"switch",side_effect=[b.Refused("load failed"),None]) as switch:
        with self.assertRaisesRegex(b.Refused,"load failed"):b.switch_profile("inkling",True)
        self.assertEqual(switch.call_count,2)
    self.assertEqual(b.selected_profile()[0],"flash")
 def test_recovery_withheld_when_strata_uncertain(self):
    with patch.object(b,"active",return_value=True),patch.object(b,"stopped",side_effect=[True,True,True,True,False]),patch.object(b,"listeners",return_value=""),patch.object(b,"no_activation"),patch.object(b,"stop_strata"),patch.object(b,"switch",side_effect=b.Refused("load failed")):
        with self.assertRaisesRegex(b.Refused,"Recovery withheld"):b.switch_profile("inkling",True)
    self.assertEqual(b.selected_profile()[0],"inkling")

if __name__=="__main__":unittest.main()
