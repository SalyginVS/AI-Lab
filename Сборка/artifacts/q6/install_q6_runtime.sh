#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 -I - "$SCRIPT_DIR" "$@" <<'PY'
"""Q6 runtime package. Reads GGUF metadata; never reads tensor data."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import subprocess
import sys
import tempfile
import urllib.request

PACKAGE = Path(sys.argv[1])
ORIGINAL = "c3cf9e34abf4f9e36c2d72165aa9c132d3e2a725b6c2586aaa3a8af9d7a81041"
REPAIRED = "051e7fd833cbe38640057f6d9870cf59c118d939071fae4c3cf24714c516c3d0"
LIVE = "a20b9923b872faba2fb56fb0148cd60547a3e7516869cd0a9ad56773802fc1c6"
TEMPLATE_HASH = "f07f08baf630b0bfa92b52f26972c035add89aa0b5babf5dbdd245ccd65d9819"
PREFIX_HASH = "e565bf70130bbc5a2b93bd682436f7ffd8656de0295980146917d6aae110022c"
LIB = "/usr/local/lib/ollama/"
RUNNER = LIB + "llama-server"
STATE = "/var/lib/ai-lab/q6-runtime.json"
SIZES = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def template_path(qid):
    require(re.fullmatch(r"[0-9a-f]{12}", qid), "Invalid Q6 ID")
    return "/usr/local/share/ollama/templates/q6-" + qid + "-reasoning-compat.jinja"


def render(real, qid):
    require(re.fullmatch(r"/usr/local/lib/ollama/llama-server\.real-[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.-]+)?", real),
            "Unsafe or unexpected real runner path")
    template_path(qid)
    return WRAPPER.replace(b"@REAL@", real.encode()).replace(b"@Q6_ID@", qid.encode())


def package_check():
    global WRAPPER, PREFIX
    WRAPPER = (PACKAGE / "llama-server.wrapper.in").read_bytes()
    PREFIX = (PACKAGE / "reasoning-alias.prefix").read_bytes()
    require(sha(WRAPPER) == TEMPLATE_HASH, "Wrapper template SHA256 mismatch")
    require(sha(PREFIX) == PREFIX_HASH and len(PREFIX) == 147, "Prefix SHA256/size mismatch")
    require(WRAPPER.count(b"@REAL@") == 1 and WRAPPER.count(b"@Q6_ID@") == 2,
            "Unexpected placeholder count")
    require(sha(render(LIB + "llama-server.real-0.35.1", "09b8aff72a79")) == LIVE,
            "Wrapper fidelity mismatch")
    sums = {}
    for line in (PACKAGE / "SHA256SUMS").read_text().splitlines():
        if line and not line.startswith("#"):
            digest, name = line.split("  ", 1)
            require(re.fullmatch(r"[0-9a-f]{64}", digest) and "/" not in name and name not in sums,
                    "Invalid package SHA256SUMS")
            sums[name] = digest
    require(set(sums) == {"llama-server.wrapper.in", "reasoning-alias.prefix",
                         "install_q6_runtime.sh", "uninstall_q6_runtime.sh", "verify_q6_runtime.sh"},
            "Incomplete package SHA256SUMS")
    for name, digest in sums.items():
        require(file_sha(PACKAGE / name) == digest, "Package SHA256 mismatch: " + name)


def exact_read(f, n):
    require(0 <= n <= 64 * 1024 * 1024, "Unexpected GGUF length")
    data = f.read(n)
    require(len(data) == n, "Truncated GGUF metadata")
    return data


def u32(f):
    return struct.unpack("<I", exact_read(f, 4))[0]


def u64(f):
    return struct.unpack("<Q", exact_read(f, 8))[0]


def gguf_string(f):
    return exact_read(f, u64(f))


def skip_value(f, kind, depth=0):
    require(depth <= 4, "Unexpected GGUF metadata nesting")
    if kind in SIZES:
        n = SIZES[kind]
    elif kind == 8:
        n = u64(f)
        require(n <= 64 * 1024 * 1024, "Unexpected GGUF string length")
    elif kind == 9:
        element, count = u32(f), u64(f)
        require(count <= 10_000_000, "Unexpected GGUF array length")
        if element in SIZES:
            n = SIZES[element] * count
        else:
            for _ in range(count):
                skip_value(f, element, depth + 1)
            return
    else:
        raise ValueError("Unknown GGUF metadata type: " + str(kind))
    require(f.tell() + n <= os.fstat(f.fileno()).st_size, "Truncated GGUF value")
    f.seek(n, os.SEEK_CUR)


def read_gguf_template(path):
    with path.open("rb") as f:
        require(exact_read(f, 4) == b"GGUF" and u32(f) in (2, 3), "Unsupported GGUF")
        _tensors, count = u64(f), u64(f)
        require(count <= 100_000, "Unexpected GGUF metadata count")
        for _ in range(count):
            key, kind = gguf_string(f), u32(f)
            if key == b"tokenizer.chat_template":
                require(kind == 8, "Chat template is not a string")
                return gguf_string(f)
            skip_value(f, kind)
    raise ValueError("GGUF has no tokenizer.chat_template")


def parse_args():
    p = argparse.ArgumentParser(description="Install, verify or remove Q6 runtime; Python 3.11+ required")
    p.add_argument("--action", choices=("install", "verify", "uninstall"), default="install")
    p.add_argument("--root", default="/", help="Existing target root; all target paths are rooted here")
    p.add_argument("--model", default=os.environ.get("Q6_MODEL"))
    p.add_argument("--gguf-first", default=os.environ.get("Q6_GGUF_FIRST"), help="Absolute target path of first Q6 shard")
    p.add_argument("--ollama-url", default=os.environ.get("LAB_OLLAMA_URL", "http://127.0.0.1:11434"))
    p.add_argument("--ollama-bin", default=os.environ.get("LAB_OLLAMA_BIN", "/usr/local/bin/ollama"))
    p.add_argument("--tags-file", help="Offline /api/tags JSON; allowed only with --root other than /")
    p.add_argument("--q6-id", help="Optional assertion only; always checked against /api/tags")
    return p.parse_args(sys.argv[2:])


def target(name):
    p = Path(name)
    require(p.is_absolute() and ".." not in p.parts, "Target path must be absolute without ..")
    path = ROOT / str(p).lstrip("/")
    require(path.resolve().is_relative_to(ROOT), "Target path escapes root")
    # Do not replace symlinks or follow directory symlinks, even within the root.
    for item in [path, *path.parents]:
        if item == ROOT:
            break
        require(not item.is_symlink(), "Symlink in target path: " + str(item))
    return path


def elf(path):
    require(path.is_file(), "Runner not found: " + str(path))
    with path.open("rb") as f:
        return f.read(4) == b"\x7fELF"


def version(args):
    binary = target(args.ollama_bin)
    result = subprocess.run([str(binary), "--version"], capture_output=True, text=True, timeout=15, check=True)
    found = re.findall(r"ollama version (?:is )?([0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.-]+)?)",
                       result.stdout + result.stderr)
    require(len(set(found)) == 1, "Cannot unambiguously determine ollama --version")
    return found[0]


def model_identity(args):
    require(args.model, "--model or Q6_MODEL is required")
    if args.tags_file:
        require(ROOT != Path("/"), "--tags-file is for offline rooted tests only")
        data = json.loads(Path(args.tags_file).read_bytes())
    else:
        require(args.ollama_url.startswith(("http://", "https://")), "Invalid Ollama URL")
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(args.ollama_url.rstrip("/") + "/api/tags", timeout=15) as response:
            require(response.status == 200, "Cannot read /api/tags")
            data = json.load(response)
    require(isinstance(data, dict) and isinstance(data.get("models"), list), "Invalid /api/tags")
    rows = [m for m in data["models"] if isinstance(m, dict)]
    found = [m for m in rows if args.model in (m.get("name"), m.get("model"))]
    require(len(found) == 1, "Q6 model missing or ambiguous in /api/tags")
    digest = found[0].get("digest", "")
    require(isinstance(digest, str), "Invalid digest type")
    digest = digest.removeprefix("sha256:")
    require(re.fullmatch(r"[0-9a-f]{64}", digest), "Invalid model digest")
    qid = digest[:12]
    for m in rows:
        other = str(m.get("digest", "")).removeprefix("sha256:")
        require(not (other.startswith(qid) and other != digest), "Ambiguous 12-character model ID")
    require(args.q6_id is None or args.q6_id == qid, "Requested Q6 ID disagrees with /api/tags")
    return qid, digest


def load_state():
    p = target(STATE)
    if not p.exists():
        return None
    s = json.loads(p.read_bytes())
    require(isinstance(s, dict) and s.get("format") == 1, "Unknown runtime state")
    require(re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.-]+)?", s.get("version", "")),
            "Invalid state version")
    require(s.get("real") == LIB + "llama-server.real-" + s["version"], "Invalid state runner path")
    require(s.get("template") == template_path(s.get("q6_id", "")), "Invalid state template path")
    require(s.get("wrapper_sha256") == sha(render(s["real"], s["q6_id"])), "Invalid state wrapper hash")
    require(s.get("template_sha256") == REPAIRED, "Invalid state template hash")
    require(re.fullmatch(r"[0-9a-f]{64}", s.get("real_sha256", "")), "Invalid state ELF hash")
    return s


def check_installed(s):
    require(s is not None, "No Q6 runtime installation state")
    runner, real, chat = target(RUNNER), target(s["real"]), target(s["template"])
    require(runner.read_bytes() == render(s["real"], s["q6_id"]), "Installed wrapper mismatch")
    require(file_sha(chat) == REPAIRED, "Installed chat template mismatch")
    require(elf(real) and os.access(real, os.X_OK), "Real runner is not executable ELF")
    require(file_sha(real) == s["real_sha256"], "Real runner SHA256 mismatch")
    return runner, real, chat


def atomic_write(path, data, mode):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".q6-runtime-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fchmod(f.fileno(), mode)
            os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def snapshot_small(paths):
    return {p: (p.read_bytes(), stat.S_IMODE(p.stat().st_mode)) if p.exists() else None for p in paths}


def restore_small(saved):
    for p, value in saved.items():
        if value is None:
            p.unlink(missing_ok=True)
        else:
            atomic_write(p, *value)


def install(args):
    qid, digest = model_identity(args)
    ver = version(args)
    require(args.gguf_first, "--gguf-first or Q6_GGUF_FIRST is required")
    original = read_gguf_template(target(args.gguf_first))
    require(len(original) == 8952 and sha(original) == ORIGINAL, "Original chat template SHA256/size mismatch")
    chat_bytes = PREFIX + original
    require(len(chat_bytes) == 9099 and sha(chat_bytes) == REPAIRED, "Generated template SHA256 mismatch")
    real_name = LIB + "llama-server.real-" + ver
    wrapper_bytes = render(real_name, qid)
    runner, real, chat, state_file = target(RUNNER), target(real_name), target(template_path(qid)), target(STATE)
    state = load_state()
    old_chat = target(state["template"]) if state else None
    if old_chat and old_chat.exists():
        require(file_sha(old_chat) == REPAIRED, "Previous template SHA256 mismatch")
    is_elf = elf(runner)
    if is_elf:
        require(os.access(runner, os.X_OK), "ELF runner is not executable")
        require(not real.exists(), "Real runner backup already exists; refusing to overwrite it")
        real_hash = file_sha(runner)
    else:
        data = runner.read_bytes()
        found_real = re.search(rb"^REAL='([^']+)'$", data, re.M)
        found_id = re.search(rb"^Q6_ID='([0-9a-f]{12})'$", data, re.M)
        require(found_real and found_id, "Unknown wrapper")
        previous_real, previous_id = found_real[1].decode(), found_id[1].decode()
        require(data == render(previous_real, previous_id), "Existing wrapper differs from accepted template")
        require(previous_real == real_name, "Wrapper runner version differs from ollama --version")
        require(elf(real) and os.access(real, os.X_OK), "Missing executable real runner")
        previous_chat = target(template_path(previous_id))
        require(file_sha(previous_chat) == REPAIRED, "Existing template SHA256 mismatch")
        if state:
            check_installed(state)
        else:
            old_chat = previous_chat
        real_hash = file_sha(real)
    if chat.exists():
        require(file_sha(chat) == REPAIRED, "Target chat template SHA256 mismatch")
    new_state = dict(format=1, model=args.model, digest=digest, q6_id=qid, version=ver, real=real_name,
                     real_sha256=real_hash, template=template_path(qid),
                     template_sha256=REPAIRED, wrapper_sha256=sha(wrapper_bytes))
    state_bytes = (json.dumps(new_state, sort_keys=True, indent=2) + "\n").encode()
    if (not is_elf and runner.read_bytes() == wrapper_bytes and chat.exists()
            and chat.read_bytes() == chat_bytes and state_file.exists() and state_file.read_bytes() == state_bytes):
        print("INSTALL=UNCHANGED Q6_ID=" + qid + " VERSION=" + ver)
        return
    # All SHA256, identity, version and path checks above are read-only.
    saved = snapshot_small(set([chat, state_file] + ([old_chat] if old_chat else [])
                               + ([] if is_elf else [runner])))
    renamed = False
    try:
        if is_elf:
            runner.rename(real)
            renamed = True
        atomic_write(chat, chat_bytes, 0o644)
        atomic_write(runner, wrapper_bytes, 0o755)
        atomic_write(state_file, state_bytes, 0o644)
        if old_chat and old_chat != chat:
            old_chat.unlink(missing_ok=True)
    except BaseException:
        restore_small(saved)
        if renamed:
            runner.unlink(missing_ok=True)
            real.rename(runner)
        raise
    print("INSTALL=PASS Q6_ID=" + qid + " VERSION=" + ver)
    print("REAL=" + real_name + " SHA256=" + real_hash + (" RENAMED_FROM_ELF" if is_elf else " PRESERVED"))
    print("WRAPPER_SHA256=" + sha(wrapper_bytes))
    print("TEMPLATE_SHA256=" + sha(chat_bytes))


def verify(args):
    s = load_state()
    check_installed(s)
    qid, digest = model_identity(args)
    require(s["model"] == args.model and s["q6_id"] == qid and s["digest"] == digest, "Installed Q6 identity mismatch")
    require(s["version"] == version(args), "Installed runner differs from ollama --version")
    print("VERIFY=PASS Q6_ID=" + qid + " VERSION=" + s["version"])
    print("WRAPPER_SHA256=" + s["wrapper_sha256"])
    print("TEMPLATE_SHA256=" + s["template_sha256"])
    print("REAL_SHA256=" + s["real_sha256"])


def uninstall():
    s = load_state()
    runner, real, chat = check_installed(s)
    state_file = target(STATE)
    saved = snapshot_small([runner, chat, state_file])
    restored = False
    try:
        os.replace(real, runner)
        restored = True
        chat.unlink()
        state_file.unlink()
    except BaseException:
        if restored:
            runner.rename(real)
        restore_small(saved)
        raise
    print("UNINSTALL=PASS RESTORED_ELF_SHA256=" + file_sha(runner))


try:
    args = parse_args()
    ROOT = Path(args.root).resolve()
    require(ROOT.is_dir(), "--root must be an existing directory")
    package_check()
    if args.action == "install":
        install(args)
    elif args.action == "verify":
        verify(args)
    else:
        uninstall()
except (OSError, ValueError, KeyError, TypeError, AttributeError, subprocess.SubprocessError,
        struct.error) as exc:
    print("Q6_RUNTIME=FAIL " + str(exc), file=sys.stderr)
    sys.exit(1)
PY
