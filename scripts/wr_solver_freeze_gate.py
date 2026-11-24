#!/usr/bin/env python3
"""Read-only-source WR freeze gate: replay four independent strict winners.

Never edits the solver, existing archives, or champion JSONs. Writes a new,
refuse-to-overwrite regression folder under Documents only. A freeze requires
every original board to pass the current independent saved-board audit.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import run_audioex_native_ladder as core

ARCHIVE = Path.home() / "Documents/Stripboard-Experiment-Archive"
AUDIO = ROOT / "test-fixtures/masters/audio/audio.json"
EXPECTED_AUDIO = {
    6: (12, 40, "29e75cc41615ffc74846b478b18ba88ed64494fa3ef03a90d24a6ce684e52548"),
    26: (13, 41, "60fc8082dadb8c3f08c69d88326cb3a38cb8c03662a451bca6f62e527ddedf09"),
    32: (19, 47, "f9e8e7ac5c185a117de4fc062fdabd3b0b710fc89f77d457b339220643715e6c"),
}
# The original AUDIOEX champion's complete layout signature is not in the
# repository. Preserve the witnessed counts, not an invented SHA.
EXPECTED_AUDIOEX = (13, 47)

def git(*args):
    result = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=True)
    return result.stdout.strip()

def fingerprint():
    # Hash the actual solver sources AND the compiled native artifacts used
    # by the CLI. A clean Git status by itself cannot detect stale binaries.
    roots = (ROOT / "src/frontend/components/stripboard",
             ROOT / "src/frontend/tests/solver")
    sources = []
    for folder in roots:
        for p in folder.rglob("*"):
            if p.is_file() and p.suffix in (".ts", ".tsx", ".js", ".c", ".h"):
                if not any(q in ("build", "out", "node_modules", "dist") for q in p.relative_to(ROOT).parts):
                    sources.append(p)
    binary_files = [core.EDGE_DECODE, core.NATIVE_ROUTE, core.NATIVE_ADDON, core.SOLVER_JS]
    files = sorted(set(sources + binary_files + [core.CLI, core.AUDITOR, AUDIO, core.SOURCE]))
    missing = [str(p) for p in binary_files if not p.is_file()]
    if missing:
        raise FileNotFoundError("Native build incomplete: " + ", ".join(missing))
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}

def run_case(out, label, prepared, moves, seed, drilled, drill_domain, expected):
    folder = out / label
    record = core.run_one(folder, prepared, moves, seed, timeout=1800,
                          drilled=drilled, drill_domain=drill_domain,
                          forensic=True, enforce_bms_anchor=(label == "audioex"))
    w, c = expected[:2]
    failures = []
    if record.get("strictPass") is not True:
        failures.append("NOT_STRICT: " + str(record.get("strictFailures") or record.get("errors")))
    if record.get("wires") != w or record.get("cuts") != c:
        failures.append("W_C_REGRESSION expected %sW/%sC, got %sW/%sC" %
                        (w, c, record.get("wires"), record.get("cuts")))
    if len(expected) > 2 and record.get("layoutSig") != expected[2]:
        failures.append("LAYOUT_SIGNATURE_CHANGED")
    return {"case": label, "seed": seed, "moves": moves, "drilled": drilled,
            "drillDomain": drill_domain, "record": record, "gateFailures": failures,
            "gatePass": not failures}

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--skip-audioex", action="store_true",
                    help="Isolate the original audio.net regression cases only")
    args = ap.parse_args()
    dirty = git("status", "--porcelain", "--untracked-files=no")
    if dirty:
        ap.error("Tracked repo files are modified. Commit/revert changes before WR freeze.")
    revision = git("rev-parse", "HEAD")
    out = (args.out or (ARCHIVE / ("wr_solver_freeze_gate_" + revision[:12]))).expanduser().resolve()
    if out.exists() and any(out.iterdir()):
        ap.error("Refusing to overwrite a prior freeze gate: " + str(out))
    out.mkdir(parents=True, exist_ok=True)
    audio = json.loads(AUDIO.read_text(encoding="utf8"))
    if any(c.get("locked") and c.get("boardPos") for c in audio["components"]):
        ap.error("Expected original audio.net's unlocked audio.json fixture")
    manifest = {"schema": "wr-solver-freeze-gate/v1", "gitCommit": revision,
                "sourceAndCompiledSha256": fingerprint(), "cases": [], "allPass": False}
    print("🔒 WR freeze gate | source + compiled binary hashes | independent strict audit", flush=True)
    cases = [("audio_net_drill_on", audio, 20000, seed, True, True, expected)
             for seed, expected in EXPECTED_AUDIO.items()]
    if not args.skip_audioex:
        ex = core.prepare_audioex(json.loads(core.SOURCE.read_text(encoding="utf8")))
        cases.append(("audioex_drill_off", ex, 25000, 1575, False, False, EXPECTED_AUDIOEX))
    for label, prepared, moves, seed, drilled, domain, expected in cases:
        # Dedicated per-case folders prevent 20k and 25k outputs clobbering.
        case_name = "%s_seed_%04d" % (label, seed)
        result = run_case(out, case_name if label != "audioex_drill_off" else "audioex",
                          prepared, moves, seed, drilled, domain, expected)
        manifest["cases"].append(result)
        status = "✅ PASS" if result["gatePass"] else "❌ REGRESSION"
        print("%s %s seed %04d %sW/%sC %s" %
              (status, label, seed,
               result["record"].get("wires"), result["record"].get("cuts"),
               result["gateFailures"]), flush=True)
    manifest["allPass"] = all(r["gatePass"] for r in manifest["cases"])
    core.write_json(out / "freeze_gate.json", manifest)
    print(("🔒 FREEZE GATE PASS" if manifest["allPass"] else "🛑 DO NOT FREEZE: REGRESSIONS") +
          " | manifest " + str(out / "freeze_gate.json"), flush=True)
    return 0 if manifest["allPass"] else 1

if __name__ == "__main__":
    sys.exit(main())
