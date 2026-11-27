"""Isolated tests for refusal, idempotence and Pi config preservation."""
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import urllib.error
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent


def load(path):
    loader = importlib.machinery.SourceFileLoader(path.name, str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


b = load(ROOT / "mbip-backend")
p = load(ROOT.parent / "mbip" / "configure-pi.py")


class Guards(unittest.TestCase):
    def test_guards_refuse_other_mode_and_activation(self):
        for service, conflict in [(b.STRATA,b.OLLAMA),(b.OLLAMA,b.STRATA),(b.GATEWAY,b.STRATA),(b.RAG,b.STRATA)]:
            for state in ("active", "activating", "deactivating"):
                def row(u):
                    return {"LoadState":"loaded","ActiveState":state if u==conflict else "inactive","MainPID":"0"}
                with patch.object(b,"unit",side_effect=row), patch.object(b,"listeners",return_value=""):
                    with self.assertRaises(b.Refused):
                        b.gate(service)

    def test_inactive_other_mode_with_leftover_listener_refused(self):
        with patch.object(b,"stopped",return_value=True), patch.object(b,"listeners",return_value="stale"):
            with self.assertRaises(b.Refused):
                b.gate(b.STRATA)

    def test_direct_guards_allow_clean_opposite_state(self):
        with patch.object(b,"stopped",return_value=True), patch.object(b,"listeners",return_value=""):
            b.gate(b.STRATA)
            b.gate(b.OLLAMA)

    def test_busy_unload_does_not_stop(self):
        busy=urllib.error.HTTPError("loopback",409,"busy",{},None)
        with patch.object(b,"active",return_value=True), patch.object(b,"confirm_connections"), patch.object(b,"api",side_effect=busy), patch.object(b,"run") as run:
            with self.assertRaisesRegex(b.Refused,"busy"):
                b.stop_strata()
            run.assert_not_called()

    def test_idempotent_and_missing_confirmation(self):
        with patch.object(b,"healthy",return_value=True), patch.object(b,"run") as run:
            for mode in ("ollama","strata"):
                b.switch(mode,False)
            run.assert_not_called()
        with patch.object(b,"healthy",return_value=False), patch.object(b,"run") as run:
            with self.assertRaisesRegex(b.Refused,"--drained"):
                b.switch("strata",False)
            run.assert_not_called()

    def test_open_client_connection_refused(self):
        row=((0,0),("127.0.0.1",11434),("198.51.100.1",45123),"",{"lastsnd":70_000,"lastrcv":70_000})
        with patch.object(b,"sockets",return_value=[row]), patch.object(b,"unit",return_value={"MainPID":"71"}):
            with self.assertRaisesRegex(b.Refused,"connection"):
                b.confirm_connections(11434)

    def test_only_tagged_idle_gateway_socket_accepted(self):
        gateway={"lastsnd":70_000,"lastrcv":71_000}
        server=((0,0),("127.0.0.1",11434),("127.0.0.1",45123),"",gateway)
        reverse=((0,0),server[2],server[1],'users:(("python",pid=71,fd=9))',gateway)
        with patch.object(b,"sockets",return_value=[server,reverse]),patch.object(b,"unit",return_value={"MainPID":"71"}):
            b.confirm_connections(11434)
            gateway["lastsnd"]=1
            with self.assertRaises(b.Refused):
                b.confirm_connections(11434)

    def test_transition_lock_rejects_second_operator(self):
        with tempfile.TemporaryDirectory() as work, b.locked(Path(work) / "switch.lock"):
            with self.assertRaises(b.Refused), b.locked(Path(work) / "switch.lock"):
                self.fail("Second lock was acquired")

    def test_recovery_with_resources_uncertain(self):
        with patch.object(b,"healthy",return_value=False), patch.object(b,"no_activation"), patch.object(b,"active",return_value=False), patch.object(b,"stopped",return_value=True), patch.object(b,"listeners",return_value=""), patch.object(b,"confirm_connections"), patch.object(b,"run") as run, patch.object(b,"released",side_effect=b.Refused("unreleased")):
            with self.assertRaisesRegex(b.Refused,"Recovery withheld"):
                b.switch("strata",True)
            self.assertFalse(any(c.args[:2] == ("systemctl","start") for c in run.call_args_list))


class Pi(unittest.TestCase):
    def test_addition_only_and_second_run_noop(self):
        base=b'{\n    "providers": {\n        "ailab-ollama": {"keep":"exact"}\n    }\n}\n'
        template=json.loads((ROOT.parent/"mbip"/"pi-provider.json").read_text())
        out=p.add_provider(base,template)
        self.assertIn(b'        "ailab-ollama": {"keep":"exact"}',out)
        self.assertEqual(p.add_provider(out,template),out)
        self.assertEqual(json.loads(out)["providers"]["ailab-ollama"],json.loads(base)["providers"]["ailab-ollama"])


if __name__=="__main__":
    unittest.main()
