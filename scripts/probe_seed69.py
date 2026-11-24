#!/usr/bin/env python3
"""SEED 69: five independent native V5 timing/quality probes, never a WR sweep.

Run on the iMac, from the repository root:
    python3 scripts/probe_seed69.py                # Moto (current circuit)
    python3 scripts/probe_seed69.py --circuit audio
    python3 scripts/probe_seed69.py --circuit both

Always creates a NEW Desktop/Seed69Calibrations/ folder. Never deletes, resumes,
writes to, or imports the destructive run_wr_audio_moto.py controller.
By default refuses to time the probe while that WR campaign is running because
CPU contention would spoil its timing estimates. --allow-concurrent overrides.
The exact same native CLI + independently audited strict-validation policy is
used as the existing WR campaign. Unqualified W/C is diagnostic ONLY.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import run_audioex_native_ladder as core
from scripts.run_audio_net_drill_on_debug50_20k import verify_netlist
from scripts.run_audioex_10k_2000_quality import score_quality

BUDGETS = (5_000, 10_000, 15_000, 20_000, 25_000)
SEED = 69
SOURCES = {
    "audio": ROOT / "test-fixtures/masters/audio/audio.json",
    "moto": ROOT / "test-fixtures/masters/moto/moto.json",
}
REQUIRED = (core.CLI, core.AUDITOR, core.EDGE_DECODE,
            core.NATIVE_ROUTE, core.NATIVE_ADDON, core.SOLVER_JS)
FIELDS = ("circuit", "moves", "seed", "strictPass", "wires", "cuts",
          "quality100", "solveMs", "elapsedWallMs", "firstFeasibleMove",
          "unsolvedReason", "errors", "strictFailures", "auditFailures",
          "savedJson")


def wr_campaign_running() -> bool:
    """Best-effort read-only process check; avoids contaminated timings."""
    try:
        proc = subprocess.run(["ps", "-axo", "pid=,command="],
                              capture_output=True, text=True, timeout=5)
        if proc.returncode != 0:
            return False
        for line in proc.stdout.splitlines():
            if "run_wr_audio_moto.py" not in line:
                continue
            parts = line.strip().split(None, 1)
            if parts and parts[0].isdigit() and int(parts[0]) != os.getpid():
                # Only actual Python invocations, not grep, editors or terminal
                # shells with the filename in a command buffer.
                cmd = parts[1] if len(parts) > 1 else ""
                if "python" in cmd.lower() and "run_wr_audio_moto.py" in cmd:
                    return True
    except (OSError, subprocess.TimeoutExpired):
        pass
    return False


def fit_speed(rows: list[dict]) -> dict:
    """Approximate per-move solve time; extrapolation is indicative only."""
    solve = all(isinstance(r.get("solveMs"), (int, float)) and
                math.isfinite(r["solveMs"]) and r["solveMs"] > 0 for r in rows)
    key = "solveMs" if solve else "elapsedWallMs"
    pairs = [(r["moves"], float(r[key])) for r in rows]
    x_mean = statistics.mean(x for x, _ in pairs)
    y_mean = statistics.mean(y for _, y in pairs)
    denom = sum((x - x_mean) ** 2 for x, _ in pairs)
    slope = sum((x - x_mean) * (y - y_mean) for x, y in pairs) / denom
    if slope <= 0:
        return {"metric": key, "reliable": False,
                "message": "Timings did not increase with move budget; do not extrapolate."}
    intercept = y_mean - slope * x_mean
    return {"metric": key, "reliable": True,
            "msPerMove": round(slope, 6),
            "estimatedMovesPerSecond": round(1000 / slope, 1),
            "overheadMs": round(intercept, 1),
            "estimated50kSeconds": round(max(0, intercept + slope * 50_000) / 1000, 2),
            "estimated100kSeconds": round(max(0, intercept + slope * 100_000) / 1000, 2),
            "warning": "Single seed, five independent solves, routing outliers possible; "
                       "timings under simultaneous WR load are not representative."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--circuit", choices=("moto", "audio", "both"), default="moto")
    parser.add_argument("--timeout", type=int, default=1800,
                        help="Per-run timeout in seconds (default: 1800)")
    parser.add_argument("--allow-concurrent", action="store_true",
                        help="Run even if the 2,000-seed WR campaign is active; estimates may be contaminated")
    args = parser.parse_args()
    if args.timeout < 1:
        parser.error("--timeout must be positive")

    if wr_campaign_running() and not args.allow_concurrent:
        print("🛡️ WR campaign is still running. Seed-69 timing would be skewed by CPU contention.", flush=True)
        print("No files touched. Run again after the WR sweep finishes.", flush=True)
        print("For a deliberate under-load test only, add --allow-concurrent.", flush=True)
        return 2

    circuits = ("audio", "moto") if args.circuit == "both" else (args.circuit,)
    for binary in REQUIRED:
        if not binary.is_file():
            parser.error(f"Missing native build prerequisite: {binary}")

    originals, inputs = {}, {}
    for circuit in circuits:
        source = SOURCES[circuit]
        original = source.read_bytes()
        project = json.loads(original)
        verify_netlist(project, source.with_suffix(".net").read_text(encoding="utf8"))
        board = project.get("board", {})
        if (board.get("rows"), board.get("cols"), board.get("lockedRows"),
            board.get("lockedCols")) != (24, 56, True, True):
            parser.error(f"{circuit}: expected both dimensions locked 24x56")
        originals[circuit] = hashlib.sha256(original).hexdigest()
        inputs[circuit] = project

    # Exclusive create: never overwrite or delete even an old probe folder.
    parent = Path.home() / "Desktop" / "Seed69Calibrations"
    parent.mkdir(parents=True, exist_ok=True)
    label = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = parent / f"{label}_pid{os.getpid()}"
    out.mkdir(exist_ok=False)
    print(f"🦂 SEED 69 — GET OVER HERE! | {args.circuit} | 5 native probes per circuit", flush=True)
    print("🔪 DRILL OFF | 🧷 STACK ON | 24x56 locked | native strict + saved-board auditor", flush=True)
    print(f"💾 Separate output, NO WR deletion: {out}", flush=True)
    if args.allow_concurrent:
        print("⚠️ Concurrent WR requested: timing estimates may be distorted.", flush=True)

    rows = []
    for circuit in circuits:
        print(f"\n🔬 {circuit.upper()} — 5k / 10k / 15k / 20k / 25k, seed 69", flush=True)
        for moves in BUDGETS:
            # Uses same native flags as WR trial; job paths are scoped to THIS run.
            row = core.run_one(out / circuit, inputs[circuit], moves, SEED,
                               timeout=args.timeout, drilled=False,
                               drill_domain=False, forensic=False,
                               enforce_bms_anchor=False)
            row["circuit"] = circuit
            row["quality100"] = None
            if row.get("strictPass") is True:
                saved = out / circuit / row["savedJson"]
                score, _, _ = score_quality(json.loads(saved.read_text(encoding="utf8")))
                row["quality100"] = score
            rows.append(row)
            ms = row.get("solveMs")
            solve = f"{ms/1000:.2f}s" if isinstance(ms, (int, float)) else "unavailable"
            wc = f"{row.get('wires', '?')}W/{row.get('cuts', '?')}C"
            status = "✅ STRICT" if row.get("strictPass") else "❌ NOT STRICT"
            detail = f"⭐ {row['quality100']:.2f}" if row["quality100"] is not None else (
                str(row.get("unsolvedReason") or row.get("strictFailures") or
                    row.get("auditFailures") or row.get("errors") or "no valid route")[:80])
            print(f"{status} {circuit.upper()} {moves//1000:2}k | ⏱ solve {solve} "
                  f"| {wc} | {detail}", flush=True)

        group = [r for r in rows if r["circuit"] == circuit]
        curve = fit_speed(group)
        passing = [r for r in group if r.get("strictPass")]
        print(f"🏁 {circuit.upper()} {len(passing)}/5 strict passes | speed fit: "
              f"{curve.get('estimatedMovesPerSecond', 'unreliable')} moves/s", flush=True)
        if curve.get("reliable"):
            print(f"📐 Approx. 50k {curve['estimated50kSeconds']}s | "
                  f"100k {curve['estimated100kSeconds']}s "
                  f"(same machine/load, indicative only)", flush=True)
        if len(passing) > 1:
            print("🧮 Strict-pass wire reductions versus previous valid budget:", flush=True)
            for before, after in zip(passing, passing[1:]):
                saved = before["wires"] - after["wires"]
                extra = (after.get("solveMs") or after["elapsedWallMs"]) - (
                    before.get("solveMs") or before["elapsedWallMs"])
                if saved > 0:
                    print(f"  {before['moves']//1000}k→{after['moves']//1000}k: "
                          f"{saved} fewer wires, {extra/1000/saved:.2f} extra seconds/wire "
                          "(single seed, noisy)", flush=True)
                else:
                    print(f"  {before['moves']//1000}k→{after['moves']//1000}k: "
                          f"no wire improvement ({-saved:+} additional wires)", flush=True)
        else:
            print("ℹ️ Not enough strict-valid samples to estimate wire improvement. "
                  "Time calibration is still useful.", flush=True)

    # Preserve full machine-readable diagnostics, trial logs and even rejected boards.
    core.write_json(out / "manifest.json", {
        "schema": "seed69-five-rung-native/v1", "seed": SEED, "budgets": BUDGETS,
        "circuits": circuits, "fixtureSha256": originals,
        "binarySha256": {str(p.relative_to(ROOT)): core.digest(p.read_bytes())
                         for p in REQUIRED},
        "drilled": False, "stacking": True, "wirePolish": False,
        "routingPreference": "wires", "native": True, "strict": True,
        "concurrentOverride": args.allow_concurrent})
    for circuit in circuits:
        group = [r for r in rows if r["circuit"] == circuit]
        core.write_json(out / f"{circuit}_summary.json", {
            "circuit": circuit, "speedFit": fit_speed(group),
            "rows": group, "strictPasses": sum(r["strictPass"] for r in group)})
    with (out / "results.csv").open("w", newline="", encoding="utf8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            compact = {k: row.get(k) for k in FIELDS}
            for field in ("errors", "strictFailures", "auditFailures"):
                compact[field] = json.dumps(compact[field] or [])
            writer.writerow(compact)
    for circuit in circuits:
        if hashlib.sha256(SOURCES[circuit].read_bytes()).hexdigest() != originals[circuit]:
            raise RuntimeError(f"Fixture was modified externally during probe: {circuit}")
    print(f"\n🏆 DONE | CSV + summary + all audits/logs: {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
