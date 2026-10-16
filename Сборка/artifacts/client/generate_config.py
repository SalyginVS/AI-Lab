#!/usr/bin/env python3
"""Generate the RB-08 baseline from the byte-preserving live templates."""
import argparse
import json
import re
from pathlib import Path

Q6 = "qwen3.8-flash-next:125b-a6b-q6_K-ab-262k"
RVN = "ailab-gateway/qwen38-rvn-sandbox-native:256k"
REMOVED = {
    "ailab-ollama/qwen3.8-flash-next:125b-a6b-q5_K_M-ab-262k",
    "ailab-gateway/kat-coder-v2.5-dev:256k",
}


def generate(package, output, host, with_rvn=False):
    if not re.fullmatch(r"[A-Za-z0-9.-]+", host):
        raise ValueError("LAB_SERVER_HOST must be a hostname or IPv4 address")
    output.mkdir(parents=True, exist_ok=True)
    texts = {n: (package / (n + ".json.in")).read_text() for n in ("settings", "models")}
    texts["models"] = texts["models"].replace("@LAB_SERVER_HOST@", host)
    settings, models = (json.loads(texts[n]) for n in ("settings", "models"))
    settings["defaultModel"] = Q6
    for obj in (settings["modelThinkingLevels"], settings["compaction"]["modelOverrides"]):
        for key in REMOVED:
            obj.pop(key)
    optional = {
        "settings": {
            "modelThinkingLevels": {RVN: settings["modelThinkingLevels"].pop(RVN)},
            "compaction": {"modelOverrides": {RVN: settings["compaction"]["modelOverrides"].pop(RVN)}},
        },
        "models": {"providers": {"ailab-gateway": models["providers"].pop("ailab-gateway")}},
    }
    if with_rvn:
        settings["modelThinkingLevels"].update(optional["settings"]["modelThinkingLevels"])
        settings["compaction"]["modelOverrides"].update(optional["settings"]["compaction"]["modelOverrides"])
        models["providers"].update(optional["models"]["providers"])
    for name, value in (("settings", settings), ("models", models)):
        # Preserve the source's key order and indentation width.
        indent = len(re.search(r"\n( +)"+chr(34), texts[name]).group(1))
        (output / (name + ".json")).write_text(json.dumps(value, ensure_ascii=False, indent=indent)+"\n")
    (output / "rvn.optional.json").write_text(json.dumps(optional, ensure_ascii=False, indent=4)+"\n")
    return settings, models, optional


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--with-rvn", action="store_true")
    args = parser.parse_args()
    generate(args.package, args.output, args.host, args.with_rvn)
