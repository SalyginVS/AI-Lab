#!/usr/bin/env python3
"""Offline RB-05 T1-T7. No Ollama daemon, network requests or real installation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import struct
import subprocess
import tempfile

LIVE = "a20b9923b872faba2fb56fb0148cd60547a3e7516869cd0a9ad56773802fc1c6"
ORIGINAL = "c3cf9e34abf4f9e36c2d72165aa9c132d3e2a725b6c2586aaa3a8af9d7a81041"
REPAIRED = "051e7fd833cbe38640057f6d9870cf59c118d939071fae4c3cf24714c516c3d0"
MODEL = "qwen3.8-flash-next:125b-a6b-q6_K-ab-262k"
QID = "09b8aff72a79"
PROFILE = dict(LLAMA_ARG_N_CPU_MOE="43", LLAMA_ARG_OVERRIDE_TENSOR="per_layer_token_embd=CPU",
               LLAMA_ARG_LAZY_MODE="on", LLAMA_ARG_LOAD_MODE="mmap")
RUNNER = "usr/local/lib/ollama/llama-server"
CHAT = "usr/local/share/ollama/templates/q6-" + QID + "-reasoning-compat.jinja"
STATE = "var/lib/ai-lab/q6-runtime.json"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def tree(path):
    """Snapshot all directories and file bytes/mode/mtime, including unexpected files."""
    return {str(p.relative_to(path)): (("dir" if p.is_dir() else sha(p.read_bytes())),
                                      stat.S_IMODE(p.stat().st_mode), p.stat().st_mtime_ns)
            for p in [path, *sorted(path.rglob("*"))]}


def write(path, data, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    path.chmod(mode)


def gs(data):
    return struct.pack("<Q", len(data)) + data


def gguf(data):
    # Several metadata types before the template exercise the skip logic.
    values = [(b"test.uint", 4, struct.pack("<I", 7)),
              (b"test.string", 8, gs(b"ignored")),
              (b"test.array", 9, struct.pack("<IQii", 5, 2, -1, 2)),
              (b"tokenizer.chat_template", 8, gs(data))]
    return b"GGUF" + struct.pack("<IQQ", 3, 0, len(values)) + b"".join(gs(k) + struct.pack("<I", t) + v for k, t, v in values)


def fixture(root):
    root.mkdir()
    write(root / RUNNER, Path("/bin/true").read_bytes(), 0o755)
    write(root / "usr/local/bin/ollama", b'#!/usr/bin/env bash\nprintf "ollama version is 0.35.1\\n"\n', 0o755)
    write(root / "models/first.gguf", gguf(original))
    write(root / "tags.json", json.dumps({"models": [{"name": MODEL, "digest": QID + "0" * 52}]}).encode())
    return root


def command(root, action="install", extra=(), package=None, ok=True):
    script = (package or pkg) / (action + "_q6_runtime.sh")
    args = ["bash", str(script), "--root", str(root)]
    if action != "uninstall":
        args += ["--model", MODEL, "--tags-file", str(root / "tags.json")]
    if action == "install":
        args += ["--gguf-first", "/models/first.gguf"]
    result = subprocess.run(args + list(extra), capture_output=True, text=True, timeout=30)
    print("COMMAND " + action + " root=" + str(root) + " rc=" + str(result.returncode), flush=True)
    print(result.stdout + result.stderr, end="", flush=True)
    assert (result.returncode == 0) == ok, result
    return result


def refusal(root, extra=(), package=None):
    before = tree(root)
    command(root, extra=extra, package=package, ok=False)
    assert tree(root) == before, "Refused install changed target"
    print("NO_WRITES=PASS", flush=True)


def t3(tmp):
    fake = tmp / "fake-real"
    write(fake, b'#!/usr/bin/env python3\nimport json,os,sys\nprint(json.dumps({"args":sys.argv[1:],"env":{k:v for k,v in os.environ.items() if k.startswith("LLAMA_ARG_")}}))\n', 0o755)
    logger = tmp / "bin/logger"
    write(logger, b"#!/usr/bin/env bash\nexit 0\n", 0o755)
    wrapper = tmp / "wrapper"
    write(wrapper, wrapper_in.replace(b"@REAL@", str(fake).encode()).replace(b"@Q6_ID@", QID.encode()), 0o755)
    env = dict(os.environ, PATH=str(logger.parent) + ":" + os.environ["PATH"], **{k: "external" for k in PROFILE})
    cases = [(["--model", "/tmp/.ollama-split-" + QID + "-x/model-00001-of-00005.gguf", "--test", "with space"], True),
             (["--model", "/tmp/.ollama-split-abcdef012345-x/model-00001-of-00005.gguf"], False),
             (["--model", "/tmp/other.gguf"], False),
             ([], False), (["--model"], False)]
    for args, selected in cases:
        p = subprocess.run(["bash", str(wrapper)] + args, capture_output=True, text=True, env=env, check=True)
        result = json.loads(p.stdout)
        assert result["env"] == (PROFILE if selected else {}), result
        assert result["args"] == args + (["--chat-template-file", "/" + CHAT] if selected else []), result
    print("T3=PASS Q6 profile, exact argument preservation, other-model external-environment isolation", flush=True)


parser = argparse.ArgumentParser()
parser.add_argument("--extract", type=Path, required=True)
options = parser.parse_args()
pkg = Path(__file__).resolve().parents[2] / "artifacts/q6"
extract = options.extract
original = (extract / "home/vladimir/llama-cpp-test/repairs/q6-reasoning-2hicz6e0/chat-template.original.jinja").read_bytes()
assert sha(original) == ORIGINAL
wrapper_in = (pkg / "llama-server.wrapper.in").read_bytes()
rendered = wrapper_in.replace(b"@REAL@", b"/usr/local/lib/ollama/llama-server.real-0.35.1").replace(b"@Q6_ID@", QID.encode())
assert sha(rendered) == LIVE and rendered == (extract / RUNNER).read_bytes()
assert wrapper_in == (extract / RUNNER).read_bytes().replace(b"/usr/local/lib/ollama/llama-server.real-0.35.1", b"@REAL@").replace(QID.encode(), b"@Q6_ID@")
print("T1=PASS SHA256=" + sha(rendered) + " SIZE=" + str(len(rendered)), flush=True)
repaired = (pkg / "reasoning-alias.prefix").read_bytes() + original
assert sha(repaired) == REPAIRED and repaired == (extract / CHAT).read_bytes()
print("T2=PASS SHA256=" + sha(repaired) + " SIZE=" + str(len(repaired)), flush=True)

with tempfile.TemporaryDirectory(prefix="rb05-tests-") as name:
    tmp = Path(name)
    print("TEMP_ROOT=" + name, flush=True)
    t3(tmp)
    root = fixture(tmp / "install")
    original_elf = (root / RUNNER).read_bytes()
    command(root)
    real = root / (RUNNER + ".real-0.35.1")
    assert real.read_bytes() == original_elf
    assert sha((root / RUNNER).read_bytes()) == LIVE
    assert sha((root / CHAT).read_bytes()) == REPAIRED
    before = tree(root)
    result = command(root)
    assert "INSTALL=UNCHANGED" in result.stdout and before == tree(root)
    print("T4=PASS initial ELF rename, expected hashes, repeat preserves bytes/modes/mtimes/directories", flush=True)

    bad = fixture(tmp / "bad-template")
    write(bad / "models/first.gguf", gguf(original[:-1] + bytes([original[-1] ^ 1])))
    refusal(bad)
    bad_id = fixture(tmp / "bad-id")
    refusal(bad_id, extra=("--q6-id", "abcdef012345"))
    malformed = fixture(tmp / "bad-digest")
    write(malformed / "tags.json", json.dumps({"models": [{"name": MODEL, "digest": "bad"}]}).encode())
    refusal(malformed)
    unknown = fixture(tmp / "missing-model")
    write(unknown / "tags.json", b'{"models":[]}')
    refusal(unknown)
    corrupt_pkg = tmp / "corrupt-package"
    shutil.copytree(pkg, corrupt_pkg)
    write(corrupt_pkg / "reasoning-alias.prefix", b"corrupt")
    refusal(fixture(tmp / "bad-prefix"), package=corrupt_pkg)
    damaged = fixture(tmp / "truncated-gguf")
    write(damaged / "models/first.gguf", b"GGUF")
    refusal(damaged)
    print("T5=PASS template SHA256, asserted ID, digest, missing model, package prefix, truncated GGUF; zero target writes", flush=True)

    before = tree(root)
    command(root, action="verify")
    assert tree(root) == before
    for relative, change in [
        (RUNNER, lambda b: b + b"# damaged\n"),
        (CHAT, lambda b: b + b"\n"),
        (RUNNER + ".real-0.35.1", lambda b: b + b"damaged"),
        ("tags.json", lambda b: b.replace(QID.encode(), b"abcdef012345")),
        ("usr/local/bin/ollama", lambda b: b.replace(b"0.35.1", b"0.35.2")),
    ]:
        path = root / relative
        saved, mode = path.read_bytes(), stat.S_IMODE(path.stat().st_mode)
        write(path, change(saved), mode)
        before = tree(root)
        command(root, action="verify", ok=False)
        assert tree(root) == before, "verify performed writes"
        write(path, saved, mode)
    print("T7=PASS intact state, wrapper/template/ELF/API-ID/version corruption; verify read-only", flush=True)
    command(root, action="uninstall")
    assert (root / RUNNER).read_bytes() == original_elf
    assert not real.exists() and not (root / CHAT).exists() and not (root / STATE).exists()
    command(root, action="verify", ok=False)
    print("T6=PASS restored ELF SHA256=" + sha((root / RUNNER).read_bytes()), flush=True)

    # Adopt a captured-style installation without installer metadata.
    adopted = fixture(tmp / "adoption")
    (adopted / RUNNER).rename(adopted / (RUNNER + ".real-0.35.1"))
    write(adopted / RUNNER, rendered, 0o755)
    write(adopted / CHAT, repaired)
    real_before = (adopted / (RUNNER + ".real-0.35.1")).stat().st_mtime_ns
    command(adopted)
    assert (adopted / (RUNNER + ".real-0.35.1")).stat().st_mtime_ns == real_before
    command(adopted, action="verify")
    # Model reimport changes the ID but not the wrapper logic.
    new_id = "abcdef012345"
    write(adopted / "tags.json", (adopted / "tags.json").read_bytes().replace(QID.encode(), new_id.encode()))
    command(adopted)
    assert not (adopted / CHAT).exists()
    assert (adopted / RUNNER).read_bytes() == rendered.replace(QID.encode(), new_id.encode())
    command(adopted, action="verify")
    # Ollama update replaces the wrapper with a new ELF and changes its version.
    previous_real = adopted / (RUNNER + ".real-0.35.1")
    old_snapshot = (previous_real.read_bytes(), previous_real.stat().st_mtime_ns)
    write(adopted / RUNNER, original_elf, 0o755)
    write(adopted / "usr/local/bin/ollama", b'#!/usr/bin/env bash\nprintf "ollama version is 0.35.2\\n"\n', 0o755)
    command(adopted)
    assert (previous_real.read_bytes(), previous_real.stat().st_mtime_ns) == old_snapshot
    assert (adopted / (RUNNER + ".real-0.35.2")).read_bytes() == original_elf
    command(adopted, action="verify")
    command(adopted, action="uninstall")
    assert (adopted / RUNNER).read_bytes() == original_elf and previous_real.exists()
    print("T4_EXTENSION=PASS captured wrapper adoption, changed model digest, Ollama update, previous real preserved", flush=True)
print("TESTS=7/7 PASS", flush=True)
