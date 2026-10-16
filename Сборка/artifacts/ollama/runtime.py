#!/usr/bin/env python3
"""Verified archive installation. No users, services, downloads or Q6 installation."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile

PACKAGE = Path(__file__).resolve().parent
BIN = "usr/local/bin/ollama"
LIB = "usr/local/lib/ollama"
UNIT = "etc/systemd/system/ollama.service"
OVERRIDE = "etc/systemd/system/ollama.service.d/override.conf"
KEEPALIVE = "etc/systemd/system/ollama.service.d/90-fn3090-keepalive.conf"


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def target(root, logical):
    p = PurePosixPath(logical)
    require(p.is_absolute() and ".." not in p.parts, "Target paths must be absolute, without ..")
    result = root
    for part in p.parts[1:]:
        result /= part
        require(not result.is_symlink(), "Symlink in target path: " + str(result))
    return result


def fingerprint(path):
    """Content and mode; symlink targets are compared without dereferencing."""
    if path.is_symlink():
        return ("symlink", os.readlink(path))
    if path.is_file():
        return ("file", stat.S_IMODE(path.stat().st_mode), digest(path))
    if path.is_dir():
        return ("dir", stat.S_IMODE(path.stat().st_mode),
                tuple((p.name, fingerprint(p)) for p in sorted(path.iterdir())))
    require(not path.exists(), "Unsupported target object: " + str(path))
    return None


def remove(path):
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)


def copy(source, destination):
    if source.is_dir():
        shutil.copytree(source, destination, symlinks=True)
    else:
        shutil.copy2(source, destination)


def receipt(archive):
    sums, sizes = {}, {}
    for line in (PACKAGE / "SHA256SUMS").read_text().splitlines():
        if line.startswith("# archive-size "):
            _, _, name, size = line.split()
            sizes[name] = int(size)
        elif line and not line.startswith("#"):
            sha, name = line.split(None, 1)
            name = name.lstrip("*")
            require(re.fullmatch(r"[0-9a-f]{64}", sha), "Invalid checksum")
            require("/" not in name and name not in (".", ".."), "Invalid receipt filename")
            sums[name] = sha
    for name in ("runtime.py", "install_ollama_runtime.sh", "ollama.service.in",
                 "override.conf.in", "90-fn3090-keepalive.conf"):
        require(name in sums and digest(PACKAGE / name) == sums[name], "Package SHA256 mismatch: " + name)
    require(archive.name in sums and archive.name in sizes, "Archive absent from package SHA256SUMS")
    require(archive.stat().st_size == sizes[archive.name], "Archive size mismatch")
    require(digest(archive) == sums[archive.name], "Archive SHA256 mismatch")


def unpack(archive, destination):
    with subprocess.Popen(["zstd", "-dc", "--", str(archive)], stdout=subprocess.PIPE) as proc:
        try:
            with tarfile.open(fileobj=proc.stdout, mode="r|") as stream:
                for member in stream:
                    path = PurePosixPath(member.name)
                    require(not path.is_absolute() and ".." not in path.parts, "Unsafe archive path")
                    name = str(path)
                    allowed = name in (".", "bin", "lib", "lib/ollama", "bin/ollama") or name.startswith("lib/ollama/")
                    require(allowed, "Unexpected archive path: " + name)
                    require(member.isdir() or member.isreg() or member.issym(), "Unsupported archive member")
                    if member.issym():
                        link = PurePosixPath(member.linkname)
                        require(not link.is_absolute(), "Absolute archive symlink")
                        joined = os.path.normpath(str(path.parent / link))
                        require(joined.startswith("lib/ollama/"), "Escaping archive symlink")
                    stream.extract(member, destination, filter="data")
            while proc.stdout.read(1024 * 1024):
                pass
            require(proc.wait() == 0, "zstd decompression failed")
        finally:
            proc.stdout.close()
            if proc.poll() is None:
                proc.kill()
                proc.wait()
    for name in ("bin/ollama", "lib/ollama/llama-server"):
        f = destination / name
        require(f.is_file() and not f.is_symlink() and os.access(f, os.X_OK), "Missing executable: " + name)
        with f.open("rb") as stream:
            require(stream.read(4) == b"\x7fELF", "Not ELF: " + name)


def install(args):
    require(args.root.is_dir() and not args.root.is_symlink(), "--root must be an existing real directory")
    root = args.root.resolve()
    require(re.fullmatch(r"[A-Za-z0-9_./:-]+", args.service_path), "Invalid service PATH")
    require(re.fullmatch(r"[A-Za-z0-9_.:\[\]-]+", args.bind), "Invalid bind value")
    archive = args.archive.resolve(strict=True)
    receipt(archive)
    backup = target(root, args.backup_dir)
    paths = [target(root, "/" + n) for n in (BIN, LIB, UNIT, OVERRIDE, KEEPALIVE)]
    require(not any(backup == q or backup.is_relative_to(q) or q.is_relative_to(backup) for q in paths),
            "Backup overlaps installed paths")
    require(not archive.is_relative_to(backup), "Archive is inside backup path")
    for q in paths:
        if q.exists():
            require(q.is_dir() if q == paths[1] else q.is_file(), "Unexpected target type")
    extra_backups = []
    q6_state = target(root, "/var/lib/ai-lab/q6-runtime.json")
    if q6_state.exists():
        require(q6_state.is_file(), "Invalid Q6 state type")
        state = json.loads(q6_state.read_bytes())
        template = state.get("template", "")
        require(re.fullmatch(r"/usr/local/share/ollama/templates/q6-[0-9a-f]{12}-reasoning-compat\.jinja", template),
                "Invalid Q6 template path in existing state")
        chat = target(root, template)
        require(chat.is_file(), "Existing Q6 template is missing")
        extra_backups = [q6_state, chat]
    with tempfile.TemporaryDirectory(prefix="rb06-ollama-stage-") as name:
        stage = Path(name)
        unpack(archive, stage)
        units = {
            UNIT: (PACKAGE / "ollama.service.in").read_bytes().replace(b"@OLLAMA_SERVICE_PATH@", args.service_path.encode()),
            OVERRIDE: (PACKAGE / "override.conf.in").read_bytes().replace(b"@LAB_OLLAMA_BIND@", args.bind.encode()),
            KEEPALIVE: (PACKAGE / "90-fn3090-keepalive.conf").read_bytes(),
        }
        for logical, data in units.items():
            require(b"@OLLAMA_SERVICE_PATH@" not in data and b"@LAB_OLLAMA_BIND@" not in data, "Unfilled template")
            f = stage / logical
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(data)
            f.chmod(0o644)
        sources = [stage / "bin/ollama", stage / "lib/ollama"] + [stage / n for n in units]
        if all(fingerprint(a) == fingerprint(b) for a, b in zip(sources, paths)):
            print("INSTALL=UNCHANGED")
            return
        require(not backup.exists(), "Backup directory already exists; choose a new one")
        # All source, checksum, extraction and target path checks above are read-only.
        existing_dirs = {}
        for q in paths + [backup]:
            for parent in q.parents:
                if parent == root or parent.is_relative_to(root):
                    if parent.is_dir():
                        st = parent.stat()
                        existing_dirs[parent] = (st.st_atime_ns, st.st_mtime_ns)
        created_dirs, moved, installed = [], [], []
        def mkdir(path):
            absent = []
            q = path
            while not q.exists():
                absent.append(q)
                q = q.parent
            for q in reversed(absent):
                q.mkdir()
                created_dirs.append(q)
        try:
            mkdir(backup)
            for original in extra_backups:
                saved = backup / original.relative_to(root)
                mkdir(saved.parent)
                copy(original, saved)
            for source, dest in zip(sources, paths):
                mkdir(dest.parent)
                saved = backup / dest.relative_to(root)
                if dest.exists():
                    mkdir(saved.parent)
                    shutil.move(str(dest), str(saved))
                    moved.append((saved, dest))
                installed.append(dest)
                copy(source, dest)
            manifest = {str(q.relative_to(backup)): fingerprint(q) for q in backup.iterdir()}
            (backup / "backup.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
        except BaseException:
            for dest in reversed(installed):
                remove(dest)
            for saved, dest in reversed(moved):
                shutil.move(str(saved), str(dest))
            remove(backup)
            for q in reversed(created_dirs):
                if q.exists() and q.is_dir() and not any(q.iterdir()):
                    q.rmdir()
            for q, times in existing_dirs.items():
                os.utime(q, ns=times)
            raise
        print("INSTALL=PASS ARCHIVE_SHA256=" + digest(archive))
        print("BACKUP=" + str(backup))
        print("BIN_SHA256=" + digest(paths[0]))
        print("RUNNER_SHA256=" + digest(paths[1] / "llama-server"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--backup-dir", required=True, help="Absolute logical path under --root")
    parser.add_argument("--service-path", required=True)
    parser.add_argument("--bind", required=True)
    install(parser.parse_args())


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, tarfile.TarError, subprocess.SubprocessError) as exc:
        print("INSTALL=FAIL " + str(exc), file=sys.stderr)
        sys.exit(1)
