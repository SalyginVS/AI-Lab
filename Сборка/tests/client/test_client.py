#!/usr/bin/env python3
"""RB-08 offline verification. Never runs npm, Pi, or Code on a live HOME."""
import argparse
import base64
import csv
import hashlib
import http.server
import importlib.util
import json
import lzma
import os
import shutil
import sys

sys.dont_write_bytecode = True
import subprocess
import tarfile
import tempfile
import threading
import zipfile
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(path.read_text())


def isolated_env(home):
    return {"PATH": "/usr/bin:/bin", "HOME": str(home), "LANG": "C.UTF-8",
            "XDG_CONFIG_HOME": str(home / ".config"), "XDG_CACHE_HOME": str(home / ".cache"),
            "PI_OFFLINE": "1", "PI_TELEMETRY": "0"}


def run_tests(args):
    package, evidence = args.package.resolve(), args.evidence.resolve()
    downloads = args.downloads.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    results = {}
    spec = importlib.util.spec_from_file_location("rb08_config", package / "generate_config.py")
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    capture = args.capture.resolve()
    live_s, live_m = load(capture / "settings.json"), load(capture / "models.json")
    host = live_m["providers"]["ailab-ollama"]["baseUrl"].split("//", 1)[1].split(":")[0]
    with tempfile.TemporaryDirectory(prefix="rb08-tests-") as tmp:
        root = Path(tmp)
        for name in ("settings", "models"):
            rendered = (package / (name + ".json.in")).read_bytes().replace(b"@LAB_SERVER_HOST@", host.encode())
            assert rendered == (capture / (name + ".json")).read_bytes(), "T1 " + name
        results["T1"] = "PASS"

        s, m, optional = gen.generate(package, root / "baseline", "127.0.0.1")
        expected = json.loads(json.dumps(live_s))
        expected["defaultModel"] = gen.Q6
        for obj in (expected["modelThinkingLevels"], expected["compaction"]["modelOverrides"]):
            for key in gen.REMOVED | {gen.RVN}:
                obj.pop(key)
        assert s == expected
        expected_m = json.loads(json.dumps(live_m))
        expected_m["providers"].pop("ailab-gateway")
        expected_m["providers"]["ailab-ollama"]["baseUrl"] = "http://127.0.0.1:11434/v1"
        assert m == expected_m
        comp = s["compaction"]
        assert [comp["enabled"], comp["reserveTokens"], comp["keepRecentTokens"]] == [True, 32768, 20000]
        assert s["httpIdleTimeoutMs"] == 0
        assert s["retry"]["enabled"] is False and s["retry"]["maxRetries"] == 0
        assert s["retry"]["provider"]["maxRetries"] == 0 and "timeoutMs" not in s["retry"]["provider"]
        model = m["providers"]["ailab-ollama"]["models"][0]
        override = m["providers"]["ailab-ollama"]["modelOverrides"][gen.Q6]
        thinking = {"off": None, "minimal": "low", "low": "low", "medium": "medium",
                    "high": "xhigh", "xhigh": "xhigh", "max": "xhigh"}
        assert model["thinkingLevelMap"] == thinking and override["thinkingLevelMap"] == thinking
        for obj in (model, override):
            assert obj["contextWindow"] == 262144 and obj["maxTokens"] == 32768
        assert model["input"] == ["text", "image"]
        assert override["samplingParams"]["reasoning_effort"] == "xhigh"
        full_s, full_m, _ = gen.generate(package, root / "with-rvn", host, True)
        expected = json.loads(json.dumps(live_s)); expected["defaultModel"] = gen.Q6
        for obj in (expected["modelThinkingLevels"], expected["compaction"]["modelOverrides"]):
            for key in gen.REMOVED:
                obj.pop(key)
        assert full_s == expected and full_m == live_m
        gen.generate(package, root / "published-baseline", "LAB-SERVER-HOST")
        for name in ("settings", "models", "rvn.optional"):
            expected_file = root / "published-baseline" / (name + ".json")
            assert expected_file.read_bytes() == (package / "baseline" / (name + ".json")).read_bytes()
        results["T2"] = "PASS"

        meta = load(evidence / "rb08_pi_registry.json")
        blob = (downloads / "pi.tgz").read_bytes()
        assert "sha512-" + base64.b64encode(hashlib.sha512(blob).digest()).decode() == meta["dist"]["integrity"]
        assert hashlib.sha1(blob).hexdigest() == meta["dist"]["shasum"]
        recorded = load(evidence / "rb08_pi_live_hashes.json")
        count = 0
        with tarfile.open(downloads / "pi.tgz") as archive:
            for member in archive.getmembers():
                if member.isfile():
                    rel = member.name.removeprefix("package/")
                    assert sha(archive.extractfile(member).read()) == recorded[rel], rel
                    count += 1
        assert count == 1248
        results["T3"] = "PASS"

        prefix = args.prefix.resolve()
        assert prefix.is_relative_to(Path(tempfile.gettempdir())), "prefix must be temporary"
        tree = {}
        for p in (prefix / "node_modules").rglob("package.json"):
            parts = p.parent.relative_to(prefix).parts
            if ((len(parts) >= 2 and parts[-2] == "node_modules") or
                    (len(parts) >= 3 and parts[-3] == "node_modules" and parts[-2].startswith("@"))):
                tree[str(p.parent.relative_to(prefix))] = load(p)["version"]
        assert tree == load(evidence / "rb08_npm_tree_live.json")
        lock = load(package / "package-lock.json")
        assert tree == {k: v["version"] for k, v in lock["packages"].items() if k}
        (evidence / "rb08_npm_tree_test.json").write_text(json.dumps(tree, indent=2) + "\n")
        home = root / "home"; home.mkdir()
        version = subprocess.run([str(prefix / "node_modules/.bin/pi"), "--version"],
                                 cwd=root, env=isolated_env(home), capture_output=True, text=True, timeout=30)
        assert version.returncode == 0 and version.stdout.strip() == "1.0.3", version.stderr
        assert "EXIT=0" in (evidence / "rb08_npm_ci.log").read_text()
        results["T4"] = "PASS"

        sources = load(package / "sources.json")
        for name, file in (("vscode", "vscode.tar.gz"), ("vsix", "pi-vscode-openvsx.vsix"),
                           ("fd", "fd.tar.gz"), ("rg", "rg.tar.gz")):
            assert sources[name]["source_sha256"] == sha((downloads / file).read_bytes())
        assert sources["vsix"]["package_json_without_installer_metadata_match"]
        for name in ("fd", "rg"):
            with tarfile.open(downloads / (name + ".tar.gz")) as archive:
                member = next(p for p in archive.getmembers() if p.isfile() and p.name.endswith("/" + name))
                assert sha(archive.extractfile(member).read()) == sources[name]["live_sha256"]
        # Byte differences are evidence, not silently normalized into PASS.
        results["T5"] = "PASS_WITH_RECORDED_DIFFERENCES" if not sources["vsix"]["files_match_raw"] else "PASS"

        snapshot = load(package / "ubuntu-snapshot.json")
        for suite in ("resolute", "resolute-updates", "resolute-security"):
            release = args.snapshot / (suite + ".InRelease")
            checked = subprocess.run(["gpgv", "--keyring", "/usr/share/keyrings/ubuntu-archive-keyring.gpg", str(release)],
                                     cwd=root, env=isolated_env(home), capture_output=True, text=True)
            assert checked.returncode == 0, checked.stderr
        table = list(csv.DictReader((package / "key-packages.tsv").open(), delimiter="\t"))
        found = set()
        wanted = {(v["PACKAGE"].split(":")[0], v["INSTALLED"], v["ARCH"]) for v in table}
        for index in snapshot["indexes"]:
            file = args.snapshot / (index["suite"] + "-" + index["path"].replace("/", "_"))
            assert sha(file.read_bytes()) == index["sha256"]
            # Bind the index digest to its signed InRelease, not just the receipt.
            assert (" " + index["sha256"] + " ") in (args.snapshot / (index["suite"] + ".InRelease")).read_text()
            paragraph = {}
            with lzma.open(file, "rt") as stream:
                for line in stream:
                    if line == "\n":
                        key = (paragraph.get("Package"), paragraph.get("Version"), paragraph.get("Architecture"))
                        if key in wanted:
                            found.add(key)
                        paragraph = {}
                    elif ": " in line and not line[0].isspace():
                        key, value = line.rstrip("\n").split(": ", 1)
                        if key in ("Package", "Version", "Architecture"):
                            paragraph[key] = value
        assert found == wanted and len(table) == snapshot["selected"] == snapshot["matched"]
        checked = subprocess.run(["gpgv", "--keyring", "/usr/share/keyrings/ubuntu-archive-keyring.gpg",
                                  str(package / "ubuntu-SHA256SUMS.gpg"), str(package / "ubuntu-SHA256SUMS")],
                                 cwd=root, env=isolated_env(home), capture_output=True, text=True)
        assert checked.returncode == 0, checked.stderr
        results["T6"] = "PASS"

        requests = []
        class Stub(http.server.BaseHTTPRequestHandler):
            def log_message(self, *unused):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                requests.append({"path": self.path, "body": body})
                self.send_response(200); self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                for delta, finish in (({"role": "assistant", "content": "OK"}, None), ({}, "stop")):
                    chunk = {"id": "rb08-stub", "object": "chat.completion.chunk", "created": 1,
                             "model": body["model"], "choices": [{"index": 0, "delta": delta, "finish_reason": finish}]}
                    self.wfile.write(("data: " + json.dumps(chunk) + "\n\n").encode())
                self.wfile.write(b"data: [DONE]\n\n")

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 11434), Stub)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        runs = []
        try:
            for label, thinking_args in (("default", []), ("low", ["--thinking", "low"])):
                run_home = root / ("home-" + label)
                config = run_home / ".pi/agent"
                gen.generate(package, config, "127.0.0.1")
                for n in ("AGENTS.md", "models-store.json"):
                    shutil.copyfile(package / n, config / n)
                # New dummy credential for the local stub; never read or copy the live auth.json.
                (config / "auth.json").write_text(json.dumps({"ailab-ollama": {"type": "api_key", "key": "rb08-local-stub"}}))
                (config / "auth.json").chmod(0o600)
                before = len(requests)
                proc = subprocess.run([str(prefix / "node_modules/.bin/pi"), "--offline", "--print", "--no-session",
                                       "--no-tools", "--no-extensions", "--no-skills", "--no-prompt-templates",
                                       "--no-themes", "--no-context-files",
                                       *thinking_args, "Reply only OK"],
                                      cwd=root, env=isolated_env(run_home), capture_output=True, text=True, timeout=60)
                runs.append({"thinking": label, "returncode": proc.returncode, "stdout": proc.stdout,
                             "stderr": proc.stderr, "requests": requests[before:]})
                (evidence / "rb08_pi_requests.json").write_text(json.dumps(runs, ensure_ascii=False, indent=2) + "\n")
                assert proc.returncode == 0 and len(requests) == before + 1, runs[-1]
                assert requests[-1]["body"]["model"] == gen.Q6
                assert requests[-1]["path"] == "/v1/chat/completions"
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=5)
        results["T7"] = "PASS"
        for run in runs:
            body = run["requests"][0]["body"]
            print("T7_REQUEST", run["thinking"], json.dumps({k: v for k, v in body.items() if k != "messages"}), flush=True)
    (evidence / "rb08_test_results.json").write_text(json.dumps(results, indent=2) + "\n")
    for key, value in results.items():
        print(key + "=" + value, flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--package", type=Path, required=True)
    p.add_argument("--capture", type=Path, required=True)
    p.add_argument("--evidence", type=Path, required=True)
    p.add_argument("--downloads", type=Path, required=True)
    p.add_argument("--prefix", type=Path, required=True, help="existing npm ci prefix under /tmp")
    p.add_argument("--snapshot", type=Path, required=True)
    run_tests(p.parse_args())
