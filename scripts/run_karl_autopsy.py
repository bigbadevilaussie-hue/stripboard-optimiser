#!/usr/bin/env python3
"""Find the exact original input by manifest hash, then run one forensic process.
Default: six-case smoke. Explicit --all enables complete archive replay.
No rebuild, no annealing, no modification to original files.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime

REPO = Path(__file__).resolve().parents[1]
HOME = Path.home()
parser = argparse.ArgumentParser()
parser.add_argument("--arena", type=Path, default=REPO / "research/mortal-kombat")
parser.add_argument("--input", type=Path)
parser.add_argument("--all", action="store_true")
args = parser.parse_args()
arena = args.arena.expanduser().resolve()
manifest = json.loads((arena / "manifest.json").read_text())
expected = manifest["input"]

def fingerprint(p):
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    except (OSError, ValueError, UnicodeError):
        return None

if args.input:
    candidates = [args.input.expanduser().resolve()]
else:
    roots = [HOME / "ARM_C_ORIENTATION_20261126_211658",
             HOME / "MORTAL_KOMBAT_DAVE_STEVE",
             HOME / "PASS2_NEW_KARL",
             HOME / "Desktop/WR_Moto_V140_100k_STRICT_2000",
             REPO / "Work", REPO / "test-fixtures/masters/moto/V1.40"]
    candidates = []
    for root in roots:
        if not root.is_dir():
            continue
        for folder, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in {"candidates", "node_modules", ".git", "Elite", "jsons", "rejected", "solved"}]
            candidates.extend(Path(folder) / f for f in files
                              if f.endswith(".json") and ("prepared" in f.lower() or "input" in f.lower() or "v_1_40" in f.lower()))
input_path = next((p for p in candidates if fingerprint(p) == expected), None)
if input_path is None:
    sys.exit("🛑 Exact prepared input not found. Checked " + str(len(candidates)) +
             " candidates; required SHA-256 " + expected +
             ". Supply --input /path/to/original-prepared-input.json. No boards modified.")
print("✅ Matched input:", input_path, flush=True)
out = HOME / ("KARL_AUTOPSY_" + ("ALL_" if args.all else "SMOKE_") + datetime.now().strftime("%Y%m%d_%H%M%S"))
env = dict(os.environ, KARL_PYTHON=sys.executable)
cmd = ["node", str(REPO / "scripts/karl_autopsy.js"), str(REPO), str(arena), str(input_path), str(out)]
if not args.all:
    cmd.append("--smoke")
print("🔬", "100-board replay" if args.all else "Six-board smoke", "| one process | zero annealing", flush=True)
subprocess.run(cmd, env=env, check=True)
