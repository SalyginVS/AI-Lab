#!/usr/bin/env python3
"""Compare captured dpkg versions with signed, downloaded Ubuntu snapshot indexes."""
import argparse
import csv
import hashlib
import json
import lzma
from pathlib import Path
import re
import subprocess

def deb(text):
    for block in text.split("\n\n"):
        row, key = {}, None
        for line in block.splitlines():
            if line.startswith((" ", "\t")) and key:
                row[key] += "\n" + line
            elif ": " in line:
                key, value = line.split(": ", 1)
                row[key] = value
        if "Package" in row:
            yield row

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--evidence", type=Path, required=True)
parser.add_argument("--sources", type=Path, required=True)
parser.add_argument("--snapshot", required=True)
args = parser.parse_args()
p, src = args.evidence, args.sources
assert re.fullmatch(r"\d{8}T\d{6}Z", args.snapshot)
idx, signatures = {}, []
for suite in ("noble", "noble-updates", "noble-security", "noble-backports"):
    release = (src / (suite + "-InRelease")).read_text()
    sha_lines = release.split("SHA256:\n", 1)[1]
    hashes = {m[3]: (m[1], int(m[2])) for m in re.finditer(r"^ ([0-9a-f]{64})\s+(\d+)\s+(\S+)$", sha_lines, re.M)}
    result = subprocess.run(["gpgv", "--keyring", "/usr/share/keyrings/ubuntu-archive-keyring.gpg",
                             str(src / (suite + "-InRelease"))], capture_output=True, text=True)
    signatures.append(suite + " rc=" + str(result.returncode) + "\n" + result.stdout + result.stderr)
    assert result.returncode == 0, result
    for component in ("main", "restricted", "universe", "multiverse"):
        data = (src / (suite + "-" + component + ".xz")).read_bytes()
        assert (hashlib.sha256(data).hexdigest(), len(data)) == hashes[component + "/binary-amd64/Packages.xz"]
        for d in deb(lzma.decompress(data).decode()):
            idx.setdefault((d["Package"], d["Version"], d["Architecture"]), []).append((suite, component, d))
(p / "rb06_snapshot_signatures.txt").write_text("\n".join(signatures))
text = (p / "rb06_server_p1.out").read_text()
installed, residual = [], []
for line in text.split("=== P1.2 MANUAL")[0].splitlines():
    fields = line.split("\t")
    if len(fields) == 4:
        (installed if fields[3].startswith("ii") else residual).append(fields)
manual = set(text.split("=== P1.2 MANUAL ===\n")[1].split("=== P1.2 HOLD")[0].splitlines())
ctk = list(deb((p / "sources/ctk-Packages").read_text()))
ctki = {(d["Package"], d["Version"], d["Architecture"]): d for d in ctk}
rows, keys, manualrows, locks, ctkrows = [], [], [], [], []
for name, version, arch, status in installed:
    key = bool(re.search(r"^linux-(image|modules|headers).*6\.8\.0-146|^linux-(generic|image-generic|headers-generic)$|595|^docker.io$|^containerd$|^python3$|^python3-(venv|pip)$|^zstd$|^curl$|^git$", name))
    entries, external = idx.get((name, version, arch), []), ctki.get((name, version, arch))
    if entries:
        suite, component, d = entries[0]
        match, source, digest, filename = "MATCH", ",".join(a + "/" + b for a, b, _ in entries), d["SHA256"], d["Filename"]
        locks.append(name + "=" + version)
    elif external:
        match, source, digest, filename = "EXTERNAL_CTK_MATCH", "NVIDIA", external["SHA256"], external["Filename"]
        ctkrows.append(external)
    else:
        match, source, digest, filename = "MISMATCH", "", "", ""
    versions = sorted({v for n, v, a in idx if n == name and a == arch})
    row = [name, arch, version, "yes" if name in manual else "no", "yes" if key else "no",
           match, source, ";".join(versions), digest, filename]
    rows.append(row)
    if key:
        keys.append(row)
    if name in manual:
        manualrows.append(row)
header = ["package", "architecture", "installed", "manual", "key", "result", "source", "snapshot_versions", "sha256", "filename"]
for name, data in (("rb06_snapshot_table.tsv", rows), ("rb06_key_packages.tsv", keys),
                   ("rb06_manual_packages.tsv", manualrows),
                   ("rb06_mismatches.tsv", [r for r in rows if r[5] == "MISMATCH"])):
    with (p / name).open("w") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(header)
        writer.writerows(data)
(p / "rb06_ctk_index.txt").write_text("\n\n".join("\n".join(k + ": " + v for k, v in d.items()) for d in ctkrows) + "\n")
(p / "rb06_ubuntu_packages.lock").write_text("\n".join(locks) + "\n")
summary = {
    "snapshot_T": args.snapshot, "installed_count": len(rows), "residual_config_count": len(residual),
    "ubuntu_exact_matches": sum(r[5] == "MATCH" for r in rows), "ctk_exact_matches": len(ctkrows),
    "mismatches": sum(r[5] == "MISMATCH" for r in rows), "manual_count": len(manualrows),
    "manual_unmatched": [r[:6] for r in manualrows if r[5] == "MISMATCH"],
    "key_count": len(keys), "key_matches": sum(r[5] == "MATCH" for r in keys),
    "key_unmatched": [r[:6] for r in keys if r[5] != "MATCH"],
}
summary["all_packages_match_percent"] = 100 * summary["ubuntu_exact_matches"] / len(rows)
summary["combined_match_percent"] = 100 * (summary["ubuntu_exact_matches"] + len(ctkrows)) / len(rows)
(p / "rb06_snapshot_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
