#!/usr/bin/env python3
"""RB-06 offline verification. All installers use temporary --root."""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import stat
import struct
import subprocess
import tarfile
import tempfile

BIN = "usr/local/bin/ollama"
LIB = "usr/local/lib/ollama"
UNIT = "etc/systemd/system/ollama.service"
OVERRIDE = "etc/systemd/system/ollama.service.d/override.conf"
KEEP = "etc/systemd/system/ollama.service.d/90-fn3090-keepalive.conf"
REAL_SHA = "234b05b2138264f8fb263c3205e85f4c290e8afe5067e280a4f6f90cdac5696b"
BIN_SHA = "8fd655c8fde7b524dc3a64ae1006f9e8d0344dec93b1796fc9f87b7c5179fbb9"
ARCHIVE_SHA = "9fcd79ac4575b2bd31b992eee18b1000c8ad126b451627c8f8cd091714cfbb10"
MODEL = "qwen3.8-flash-next:125b-a6b-q6_K-ab-262k"


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def write(path, data, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    path.chmod(mode)


def tree(root):
    result = {}
    for p in [root, *sorted(root.rglob("*"))]:
        s = p.lstat()
        content = os.readlink(p) if p.is_symlink() else ("dir" if p.is_dir() else sha(p))
        result[str(p.relative_to(root))] = (content, stat.S_IMODE(s.st_mode), s.st_mtime_ns)
    return result


def call(args, ok=True):
    result = subprocess.run(args, capture_output=True, text=True, timeout=300)
    print("COMMAND " + json.dumps(args) + " RC=" + str(result.returncode), flush=True)
    print(result.stdout + result.stderr, end="", flush=True)
    assert (result.returncode == 0) == ok, result
    return result


def install(root, archive, backup, package=None, ok=True):
    return call(["bash", str((package or pkg) / "install_ollama_runtime.sh"),
                 "--root", str(root), "--archive", str(archive), "--backup-dir", backup,
                 "--service-path", live_path, "--bind", live_bind], ok=ok)


def q6(root, action, ok=True):
    args = ["bash", str(q6pkg / (action + "_q6_runtime.sh")), "--root", str(root),
            "--model", MODEL, "--tags-file", str(root / "fixtures/tags.json"),
            "--ollama-bin", "/fixtures/ollama"]
    if action == "install":
        args += ["--gguf-first", "/fixtures/first.gguf"]
    return call(args, ok)


def fixtures(root, version):
    original = (extract / "home/vladimir/llama-cpp-test/repairs/q6-reasoning-2hicz6e0/chat-template.original.jinja").read_bytes()
    key = b"tokenizer.chat_template"
    gs = lambda b: struct.pack("<Q", len(b)) + b
    gguf = b"GGUF" + struct.pack("<IQQ", 3, 0, 1) + gs(key) + struct.pack("<I", 8) + gs(original)
    write(root / "fixtures/first.gguf", gguf)
    write(root / "fixtures/tags.json", json.dumps({"models": [{"name": MODEL, "digest": "09b8aff72a79" + "0" * 52}]}).encode())
    write(root / "fixtures/ollama", ('#!/usr/bin/env bash\nprintf "ollama version is ' + version + '\\n"\n').encode(), 0o755)


def receipt(package, archive):
    lines = [l for l in (package / "SHA256SUMS").read_text().splitlines()
             if not l.startswith("# archive-size ") and not l.endswith("  ollama-linux-amd64.tar.zst")]
    lines += ["# archive-size " + archive.name + " " + str(archive.stat().st_size),
              sha(archive) + "  " + archive.name]
    (package / "SHA256SUMS").write_text("\n".join(lines) + "\n")


parser = argparse.ArgumentParser()
parser.add_argument("--extract", type=Path, required=True)
parser.add_argument("--archive", type=Path, required=True)
parser.add_argument("--evidence", type=Path, required=True)
opt = parser.parse_args()
extract = opt.extract
pkg = Path(__file__).resolve().parents[2] / "artifacts/ollama"
q6pkg = pkg.parent / "q6"
live_unit = (extract / UNIT).read_bytes()
live_override = (extract / OVERRIDE).read_bytes()
live_path = re.search(rb'Environment="PATH=([^"]+)"', live_unit)[1].decode()
live_bind = re.search(rb'Environment="OLLAMA_HOST=([^"]+)"', live_override)[1].decode()
for name, expected, value, marker in [
    ("ollama.service.in", live_unit, live_path, b"@OLLAMA_SERVICE_PATH@"),
    ("override.conf.in", live_override, live_bind, b"@LAB_OLLAMA_BIND@"),
]:
    source = (pkg / name).read_bytes()
    assert source.count(marker) == 1
    assert source.replace(marker, value.encode()) == expected
    assert source == expected.replace(value.encode(), marker)
assert (pkg / "90-fn3090-keepalive.conf").read_bytes() == (extract / KEEP).read_bytes()
print("T1=PASS two exact substitutions; all three captured files byte-identical", flush=True)
assert opt.archive.stat().st_size == 1439658961 and sha(opt.archive) == ARCHIVE_SHA
archive_tree = json.loads((opt.evidence / "rb06_ollama_tree.json").read_text())
assert archive_tree["binaries"]["bin/ollama"]["sha256"] == BIN_SHA
assert archive_tree["binaries"]["lib/ollama/llama-server"]["sha256"] == REAL_SHA
assert not archive_tree["mismatches"] and not archive_tree["archive_only"]
print("T2=PARTIAL_RECORDED archive digest and both ELF hashes MATCH; all captured regular-file sizes MATCH; source symlink targets were not captured", flush=True)

with tempfile.TemporaryDirectory(prefix="rb06-tests-") as name:
    tmp = Path(name)
    root = tmp / "root"
    root.mkdir()
    print("TEMP_ROOT=" + str(root), flush=True)
    install(root, opt.archive, "/backups/initial")
    assert sha(root / BIN) == BIN_SHA and sha(root / LIB / "llama-server") == REAL_SHA
    assert (root / UNIT).read_bytes() == live_unit and (root / OVERRIDE).read_bytes() == live_override
    before = tree(root)
    result = install(root, opt.archive, "/backups/initial")
    assert "INSTALL=UNCHANGED" in result.stdout and tree(root) == before
    fixtures(root, "0.35.1")
    q6(root, "install")
    q6(root, "verify")
    print("T3=PASS real archive installation; repeat preserves entire root bytes/modes/mtimes; Q6 installation and verify PASS", flush=True)

    bad = tmp / "bad"
    bad.mkdir()
    write(bad / LIB / "keep", b"existing-runtime")
    write(bad / BIN, b"existing-binary", 0o755)
    short = tmp / "ollama-linux-amd64.tar.zst"
    with opt.archive.open("rb") as stream:
        write(short, stream.read(4096))
    before = tree(bad)
    install(bad, short, "/backup", ok=False)
    assert tree(bad) == before
    # Same-size checksum corruption in a small, separately receipted fixture archive.
    fake_tar = tmp / "fixture.tar"
    with tarfile.open(fake_tar, "w") as tar:
        for n, source in [("bin/ollama", "/bin/true"), ("lib/ollama/llama-server", "/bin/false")]:
            b = Path(source).read_bytes()
            info = tarfile.TarInfo(n)
            info.size, info.mode = len(b), 0o755
            tar.addfile(info, io.BytesIO(b))
    fake = tmp / "fixture.tar.zst"
    call(["zstd", "-q", "-f", str(fake_tar), "-o", str(fake)])
    fakepkg = tmp / "fixture-package"
    shutil.copytree(pkg, fakepkg)
    receipt(fakepkg, fake)
    saved = fake.read_bytes()
    write(fake, saved[:-1] + bytes([saved[-1] ^ 1]))
    install(bad, fake, "/backup", package=fakepkg, ok=False)
    assert tree(bad) == before
    write(fake, saved)
    # A receipted but truncated frame must fail during complete extraction.
    brokenpkg = tmp / "broken-package"
    shutil.copytree(pkg, brokenpkg)
    broken = tmp / "broken.tar.zst"
    write(broken, saved[:len(saved)//2])
    receipt(brokenpkg, broken)
    install(bad, broken, "/backup", package=brokenpkg, ok=False)
    assert tree(bad) == before
    print("T4=PASS wrong size, wrong SHA256, receipted truncated frame; entire target unchanged", flush=True)

    old_wrapper = (root / LIB / "llama-server").read_bytes()
    install(root, fake, "/backups/update", package=fakepkg)
    assert (root / LIB / "llama-server").read_bytes() == Path("/bin/false").read_bytes()
    assert not (root / LIB / "llama-server.real-0.35.1").exists()
    assert (root / "backups/update" / LIB / "llama-server").read_bytes() == old_wrapper
    assert sha(root / "backups/update" / BIN) == BIN_SHA
    assert (root / "backups/update/backup.json").is_file()
    fixtures(root, "0.35.2")
    q6(root, "verify", ok=False)
    q6(root, "install")
    q6(root, "verify")
    # Restore the updater's backup, including Q6 metadata, then verify it.
    backup = root / "backups/update"
    saved = json.loads((backup / "backup.json").read_text())
    import importlib.util, sys
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("runtime", pkg / "runtime.py")
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    actual = {str(q.relative_to(backup)): runtime.fingerprint(q) for q in backup.iterdir() if q.name != "backup.json"}
    assert json.dumps(actual, sort_keys=True) == json.dumps(saved, sort_keys=True)
    state = json.loads((backup / "var/lib/ai-lab/q6-runtime.json").read_text())
    for logical in (BIN, LIB, UNIT, OVERRIDE, KEEP, "var/lib/ai-lab/q6-runtime.json", state["template"].lstrip("/")):
        dest = root / logical
        runtime.remove(dest)
        runtime.copy(backup / logical, dest)
    fixtures(root, "0.35.1")
    q6(root, "verify")
    print("T5_BACKUP_RESTORE=PASS binary, library tree, units and Q6 metadata restored", flush=True)
    install(root, opt.archive, "/backups/rollback")
    assert sha(root / BIN) == BIN_SHA and sha(root / LIB / "llama-server") == REAL_SHA
    fixtures(root, "0.35.1")
    q6(root, "verify", ok=False)
    q6(root, "install")
    q6(root, "verify")
    print("T5=PASS replacement removes Q6; backup preserves prior binary/tree; Q6 reapplied; real archive rollback restores both hashes and Q6 verify PASS", flush=True)

summary = json.loads((opt.evidence / "rb06_snapshot_summary.json").read_text())
with (opt.evidence / "rb06_snapshot_table.tsv").open() as f:
    rows = list(csv.DictReader(f, delimiter="\t"))
assert len(rows) == summary["installed_count"]
keys = [r for r in rows if r["key"] == "yes"]
assert len(keys) == summary["key_count"]
status = "PASS" if all(r["result"] == "MATCH" for r in keys) else "MISMATCH_RECORDED"
print("T6=" + status + " " + json.dumps(summary, sort_keys=True), flush=True)
ctk = (opt.evidence / "rb06_ctk_index.txt").read_text()
for name in ("nvidia-container-toolkit", "nvidia-container-toolkit-base", "libnvidia-container-tools", "libnvidia-container1"):
    block = next(b for b in ctk.split("\n\n") if "Package: " + name + "\n" in b + "\n")
    assert "Version: 1.20.1-1\n" in block + "\n" and re.search(r"^SHA256: [0-9a-f]{64}$", block, re.M)
for name in ("libc6", "libcap2", "libseccomp2"):
    assert any(r["package"] == name and r["result"] == "MATCH" for r in rows)
print("T7=PASS four NVIDIA packages 1.20.1-1 with SHA256; system dependencies match signed Ubuntu snapshot", flush=True)
print("OFFLINE_EXECUTION=COMPLETE T1,T3,T4,T5,T7=PASS; T2 retains disclosed symlink-evidence limitation; T6 result shown above", flush=True)
