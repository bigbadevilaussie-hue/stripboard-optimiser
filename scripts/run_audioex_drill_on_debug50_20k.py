#!/usr/bin/env python3
"""Forensic Drill ON only: AUDIOEX seeds 1..50, 20k moves, preserve EVERYTHING.

Bypasses the known impossible locked BMS drilled-only preflight ONLY for
diagnostics; strict electrical + geometry validation remains enabled.
Preserves all candidates, native logs, auditor output, finish traces, timings,
and full manifest. No Pass 2 or deletion. Three concurrent workers by default.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import run_audioex_native_ladder as core

MOVES = 20_000
SEEDS = tuple(range(1, 51))
OUT = (Path.home() / "Documents" / "Stripboard-Experiment-Archive" /
       "audioex_drill_on_20k_debug50")
FIELDS = ("seed", "moves", "strictPass", "cliValid", "auditValid",
          "wires", "cuts", "knife", "incomplete", "conflicts", "crossings",
          "geometry", "nonvertical", "unsolvedReason", "strictFailures",
          "auditFailures", "errors", "elapsedWallMs", "solveMs",
          "firstFeasibleMove", "firstFeasibleMs", "savedJson", "savedSha256",
          "stdoutLog", "stderrLog", "preparedInput", "layoutSig", "exit")

def identity(prepared):
    prerequisites = (core.CLI, core.AUDITOR, core.EDGE_DECODE,
                     core.NATIVE_ROUTE, core.NATIVE_ADDON, core.SOLVER_JS)
    for item in prerequisites:
        if not item.is_file():
            raise FileNotFoundError(f"Missing built prerequisite {item}")
    return {
        "schema": "audioex-drillon-20k-debug50/v1",
        "sourceSha256": core.digest(core.SOURCE.read_bytes()),
        "preparedSha256": core.digest(core.json_bytes(prepared)),
        "nativeArtifacts": {str(p.relative_to(ROOT)): core.digest(p.read_bytes())
                            for p in prerequisites},
        "seeds": list(SEEDS), "moves": MOVES, "drilledOnly": True,
        "drilledRotationDomain": True, "stackingAllowed": True,
        "strict": True, "debugBypassKnownImpossibleLockedBms": True,
        "finishTrace": True, "moveSummary": True, "wirePolish": False,
    }

def failure_counts(rows):
    return dict(Counter(
        reason for r in rows if not r.get("strictPass")
        for reason in (r.get("strictFailures") or r.get("auditFailures") or
                       r.get("errors") or [r.get("unsolvedReason") or "UNCLASSIFIED"])
    ))

def publish(out, rows):
    with (out / "results.csv").open("w", newline="", encoding="utf8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        for row in sorted(rows, key=lambda r: r["seed"]):
            x = {field: row.get(field) for field in FIELDS}
            for field in ("strictFailures", "auditFailures", "errors"):
                x[field] = json.dumps(x[field] or [])
            writer.writerow(x)
    summary = {
        "completed": len(rows), "target": len(SEEDS),
        "strictPasses": sum(r.get("strictPass") is True for r in rows),
        "failureCounts": failure_counts(rows),
        "unsolvedReasons": dict(Counter(str(r.get("unsolvedReason") or "none")
                                        for r in rows if not r.get("strictPass"))),
        "solveSecondsSum": round(sum((r.get("solveMs") or 0) for r in rows)/1000, 3),
        "trialWallSecondsSum": round(sum((r.get("elapsedWallMs") or 0) for r in rows)/1000, 3),
        "diagnostic": "Forced bypass of physically necessary drill-only preflight for DEBUG ONLY",
        "strictVerificationRequired": True,
    }
    core.write_json(out/"summary.json", summary)
    return summary

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()
    if args.jobs <= 0 or args.timeout <= 0:
        ap.error("--jobs and --timeout must be positive")
    out = args.out.expanduser().resolve()
    if out == ROOT or ROOT in out.parents:
        ap.error("Output must be outside the repository")
    prepared = core.prepare_audioex(json.loads(core.SOURCE.read_text(encoding="utf8")))
    ident = identity(prepared)
    manifest = out/"manifest.json"
    if args.resume:
        if not manifest.is_file() or json.loads(manifest.read_text()).get("identity") != ident:
            ap.error("Refusing resume: fixture or compiled binaries have changed")
        rows = core.read_checkpoint(out, (MOVES,), SEEDS)
    else:
        if out.exists() and any(out.iterdir()):
            ap.error("Output exists and is nonempty; use --resume")
        out.mkdir(parents=True, exist_ok=True)
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                capture_output=True, text=True, check=True).stdout.strip()
        core.write_json(manifest, {"identity": ident, "gitCommit": commit,
                                   "createdUTC": datetime.now(timezone.utc).isoformat()})
        rows = []
    remaining = [seed for seed in SEEDS if seed not in {r["seed"] for r in rows}]
    start = time.perf_counter()
    print("🔩 AUDIOEX DRILL ON | 🛡️ strict | 🧵 stacking ON | 24×56 LOCKED", flush=True)
    print("⚠️ FORENSIC: bypass known BMS impossibility precheck; NOT a claim drilled routing is feasible", flush=True)
    print(f"🔬 Seeds 1–50 | 20k moves | ⚙️ {args.jobs} workers | {len(remaining)} remaining", flush=True)
    print("🧪 Native drill rotation domain ON | full finish-trace + move-summary", flush=True)
    print(f"💾 ALL boards, failures, CLI stdout/stderr, audit traces kept at {out}", flush=True)
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(core.run_one, out, prepared, MOVES, seed,
                               args.timeout, drilled=True, drill_domain=True,
                               forensic=True): seed for seed in remaining}
        for f in as_completed(futures):
            seed = futures[f]
            try:
                row = f.result()
            except Exception as exc:
                row = {"seed": seed, "moves": MOVES, "strictPass": False,
                       "errors": ["WORKER_EXCEPTION: " + repr(exc)]}
            core.append_checkpoint(out, row)
            rows.append(row)
            summary = publish(out, rows)
            status = "✅ STRICT PASS" if row.get("strictPass") else "❌ NOT STRICT"
            print(f"{status} seed {seed:02d} ({len(rows)}/50) | "
                  f"{row.get('wires','?')}W/{row.get('cuts','?')}C | "
                  f"reason {row.get('unsolvedReason') or row.get('strictFailures') or row.get('errors') or 'none'} | "
                  f"incomplete {row.get('incomplete','?')} conflicts {row.get('conflicts','?')} "
                  f"knife {row.get('knife','?')} | "
                  f"⏱️ solve {(row.get('solveMs') or 0)/1000:.2f}s "
                  f"trial {(row.get('elapsedWallMs') or 0)/1000:.2f}s "
                  f"total {time.perf_counter()-start:.1f}s", flush=True)
    print(f"🏁 DONE {len(rows)}/50 | {summary['strictPasses']} strict passes | "
          f"⏱️ total wall {time.perf_counter()-start:.1f}s", flush=True)
    print(f"🧾 Failure reasons: {summary['failureCounts']}", flush=True)
    print(f"📁 {out} | 💾 ALL EVIDENCE RETAINED | 🛑 NO PASS 2", flush=True)

if __name__ == "__main__":
    main()
