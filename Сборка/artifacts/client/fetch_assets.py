#!/usr/bin/env python3
"""Download the pinned client assets and verify their recorded source digests."""
import argparse
import gzip
import hashlib
import json
import urllib.request
from pathlib import Path

ASSET_NAMES = {"vscode": "vscode.tar.gz", "vsix": "pi-vscode-openvsx.vsix",
               "fd": "fd.tar.gz", "rg": "rg.tar.gz"}


def verify_assets(package, assets):
    sources = json.loads((package / "sources.json").read_text())
    pi = json.loads((package / "pi-source.json").read_text())
    expected = {name: sources[key]["source_sha256"] for key, name in ASSET_NAMES.items()}
    expected["pi.tgz"] = pi["sha256"]
    for name, digest in expected.items():
        if hashlib.sha256((assets / name).read_bytes()).hexdigest() != digest:
            raise ValueError("SHA256 mismatch: " + name)


def fetch(package, assets):
    sources = json.loads((package / "sources.json").read_text())
    pi = json.loads((package / "pi-source.json").read_text())
    urls = {name: sources[key]["url"] for key, name in ASSET_NAMES.items()}
    urls["pi.tgz"] = pi["dist"]["tarball"]
    assets.mkdir(parents=True, exist_ok=True)
    for name, url in urls.items():
        path = assets / name
        if not path.exists():
            req = urllib.request.Request(url, headers={"User-Agent": "AI-Lab-RB08", "Accept-Encoding": "identity"})
            with urllib.request.urlopen(req, timeout=120) as response:
                body = response.read()
                if response.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
            path.write_bytes(body)
    verify_assets(package, assets)
    print("ASSETS_VERIFIED=5")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--package", type=Path, default=Path(__file__).resolve().parent)
    p.add_argument("--assets", type=Path, required=True)
    p.add_argument("--verify-only", action="store_true")
    args = p.parse_args()
    if args.verify_only:
        verify_assets(args.package, args.assets)
        print("ASSETS_VERIFIED=5")
    else:
        fetch(args.package, args.assets)
