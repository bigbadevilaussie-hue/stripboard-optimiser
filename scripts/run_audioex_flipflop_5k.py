#!/usr/bin/env python3
"""AUDIOEX flip-flop: each seed 1..2000 at 5k in drill ON and drill OFF.

Three concurrent native workers by default. Strict passes only printed; every
passing layout kept. Historical Route-Mate 100-point breakdown, full ranked
CSV, per-seed paired comparison, and timing. No second-pass optimisation.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import run_audioex_native_ladder as core

MOVES = 5_000
SEEDS = range(1, 2001)
MODES = (True, False)  # ON then OFF for each seed, 4,000 total solves
SCHEMA = "audioex-flipflop-5k-2000-v1"
OUT = Path.home() / "Documents" / "Stripboard-Experiment-Archive" / "audioex_flipflop_5k_2000"
FIELD_NAMES = ("seed", "drillOn", "strictPass", "wires", "cuts", "quality100",
               "wireLengthMm", "penaltyWires", "penaltyCuts", "penaltyWireLength",
               "penaltyDiagonals", "penaltyInvalid", "penaltyUnplaced",
               "elapsedWallMs", "solveMs", "layoutSig", "strictFailures",
               "auditFailures", "errors", "unsolvedReason", "savedBoard")
RANK_FIELDS = ("rank", "seed", "mode", "quality100", "wires", "cuts", "wireLengthMm",
               "penaltyWires", "penaltyCuts", "penaltyWireLength",
               "penaltyDiagonals", "penaltyInvalid", "penaltyUnplaced",
               "elapsedWallMs", "solveMs", "savedBoard")

def score_quality(project):
    wires = project["board"]["wires"]
    cuts = project["board"]["cuts"]
    mm = sum(math.hypot(w["from"]["row"] - w["to"]["row"],
                        w["from"]["col"] - w["to"]["col"]) for w in wires) * 2.54
    missing = sum(not isinstance(c.get("boardPos"), dict)
                  for c in project["components"]
                  if not (c.get("offBoard") or c.get("boardExcluded")))
    diagonal = sum(w["from"]["col"] != w["to"]["col"] for w in wires)
    penalties = dict(
        penaltyWires=round(.6 * len(wires), 3),
        penaltyCuts=round(.4 * len(cuts), 3),
        penaltyWireLength=round(.02 * mm, 3),
        penaltyDiagonals=round(10 * diagonal, 3),
        penaltyInvalid=0.0,  # strict saved-board audit is mandatory before scoring
        penaltyUnplaced=round(15 * missing, 3),
    )
    return round(max(0., 100. - sum(penalties.values())), 2), round(mm, 2), penalties

def key(row):
    return (-row["quality100"], row["wires"], row["cuts"],
            row["wireLengthMm"], row["seed"], row["drillOn"])

def encode(row):
    return {k: row.get(k) for k in FIELD_NAMES}

def mode_name(drilled):
    return "drill_on" if drilled else "drill_off"

def source_identity():
    source = core.SOURCE.read_bytes()
    prepared = core.prepare_audioex(json.loads(source))
    binaries = (core.CLI, core.AUDITOR, core.EDGE_DECODE, core.NATIVE_ROUTE,
                core.NATIVE_ADDON, core.SOLVER_JS)
    for path in binaries:
        if not path.is_file():
            raise FileNotFoundError(f"Missing compiled prerequisite: {path}")
    identity = dict(schema=SCHEMA, moves=MOVES, seeds=[1, 2000],
                    modeOrder=["ON", "OFF"], strict=True,
                    drillDomain=False, stackingAllowed=True, wirePolish=False,
                    sourceSha256=core.digest(source),
                    preparedSha256=core.digest(core.json_bytes(prepared)),
                    binaries={str(p.relative_to(ROOT)): core.digest(p.read_bytes())
                              for p in binaries})
    return prepared, identity

def make_task(out, prepared, seed, drilled, timeout):
    work = out / "temp" / mode_name(drilled)
    result = core.run_one(work, prepared, MOVES, seed, timeout, drilled=drilled)
    return result, work

def process_result(out, result, work, seed, drilled):
    record = encode({**result, "seed": seed, "drillOn": drilled})
    src = work / result["savedJson"] if result.get("savedJson") else None
    if result.get("strictPass") is True:
        if not src or not src.is_file():
            record["strictPass"] = False
            record["errors"] = list(record.get("errors") or []) + ["PASS_BOARD_MISSING"]
        else:
            project = json.loads(src.read_text(encoding="utf8"))
            if core.signature(project) != result.get("layoutSig"):
                raise RuntimeError(f"Signature mismatch on seed {seed}, drill {drilled}")
            q, mm, penalties = score_quality(project)
            record.update(quality100=q, wireLengthMm=mm, **penalties)
            dest = (out / "qualified_all" / mode_name(drilled) /
                    f"seed_{seed:04d}_W{record['wires']}_C{record['cuts']}.json")
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            record["savedBoard"] = str(dest.relative_to(out))
    # Delete temporary candidate, rejects, logs, only after verified pass is copied.
    job = work / "jobs" / f"moves_{MOVES:06d}_seed_{seed:03d}"
    if job.is_dir():
        shutil.rmtree(job)
    if src and src.is_file():
        src.unlink()
    return record

def freeze_previous(out):
    old = Path.home() / "Desktop" / "audioex_pass1_2000_25k_top20"
    candidates = (old, Path.home() / "Documents" /
                  "Stripboard-Experiment-Archive" / old.name)
    source = next((p / "results.jsonl" for p in candidates
                   if (p / "results.jsonl").is_file()), None)
    if not source:
        print("⚠️ Previous 25k seed file not found; no old data modified", flush=True)
        return
    old_rows = [json.loads(line) for line in source.read_text().splitlines()
                if line.strip()]
    passed = sorted(int(row["seed"]) for row in old_rows
                    if row.get("strictPass") is True)
    core.write_json(out / "previous_25k_passing_seeds.json",
                    {"source": str(source), "trialCount": len(old_rows),
                     "strictPassCount": len(passed), "seeds": passed,
                     "previousTop20": str(source.parent / "top20")})
    print(f"📌 FROZEN 25k baseline: {len(passed)} passing seed IDs", flush=True)

def publish(out, rows):
    strict = [r for r in rows if r.get("strictPass") is True]
    leaderboard = sorted(strict, key=key)
    with (out / "quality_leaderboard_all.csv").open("w", newline="", encoding="utf8") as stream:
        writer = csv.DictWriter(stream, fieldnames=RANK_FIELDS)
        writer.writeheader()
        for index, r in enumerate(leaderboard, 1):
            writer.writerow({"rank": index, "seed": r["seed"],
                             "mode": "ON" if r["drillOn"] else "OFF",
                             **{k: r.get(k) for k in RANK_FIELDS if k not in ("rank", "seed", "mode")}})
    ranks = leaderboard[:20]
    top = out / "top20"
    top.mkdir(parents=True, exist_ok=True)
    wanted = set()
    for index, r in enumerate(ranks, 1):
        src = out / r["savedBoard"]
        dest = top / f"rank_{index:02d}_{mode_name(r['drillOn'])}_seed_{r['seed']:04d}.json"
        wanted.add(dest.name)
        shutil.copy2(src, dest)
    for file in top.glob("rank_*.json"):
        if file.name not in wanted:
            file.unlink()
    mode_stats = {}
    for flag in MODES:
        subset = [r for r in rows if r["drillOn"] == flag]
        passed = [r for r in subset if r.get("strictPass") is True]
        mode_stats[mode_name(flag)] = {
            "attempts": len(subset), "strictPasses": len(passed),
            "bestScore": max((r["quality100"] for r in passed), default=None),
            "sumSolveSeconds": round(sum((r.get("solveMs") or 0) for r in subset) / 1000, 3),
            "sumTrialWallSeconds": round(sum((r.get("elapsedWallMs") or 0) for r in subset) / 1000, 3),
        }
    paired = {seed: {} for seed in SEEDS}
    for r in rows:
        paired[r["seed"]][mode_name(r["drillOn"])] = r
    with (out / "paired_comparison.csv").open("w", newline="", encoding="utf8") as stream:
        names = ["seed", "onPass", "offPass", "onQuality", "offQuality",
                 "onWires", "offWires", "onCuts", "offCuts",
                 "onSolveMs", "offSolveMs"]
        writer = csv.DictWriter(stream, fieldnames=names)
        writer.writeheader()
        for seed in SEEDS:
            on = paired[seed].get("drill_on", {})
            off = paired[seed].get("drill_off", {})
            writer.writerow(dict(seed=seed, onPass=on.get("strictPass"),
                offPass=off.get("strictPass"), onQuality=on.get("quality100"),
                offQuality=off.get("quality100"), onWires=on.get("wires"),
                offWires=off.get("wires"), onCuts=on.get("cuts"),
                offCuts=off.get("cuts"), onSolveMs=on.get("solveMs"),
                offSolveMs=off.get("solveMs")))
    core.write_json(out / "summary.json",
                    {"completed": len(rows), "target": 4000,
                     "strictPasses": len(strict), "modes": mode_stats,
                     "sumSolveSeconds": round(sum((r.get("solveMs") or 0) for r in rows) / 1000, 3),
                     "sumTrialWallSeconds": round(sum((r.get("elapsedWallMs") or 0) for r in rows) / 1000, 3),
                     "drillOnImpossiblePrechecks": sum(r.get("drillOn") is True and r.get("unsolvedReason") == "IMPOSSIBLE_DRILLED_ONLY_LOCKED_PADS" for r in rows),
                     "qualityFormula": "100 - (.6*wires + .4*cuts + .02*wireLengthMm + 10*diagonal + 15*unplaced), clamped at zero",
                     "pass2Started": False})

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()
    if args.jobs < 1 or args.timeout < 1:
        ap.error("--jobs and --timeout must be positive")
    out = args.out.expanduser().resolve()
    if out == ROOT or ROOT in out.parents:
        ap.error("Output must be outside repository")
    prepared, identity = source_identity()
    manifest = out / "manifest.json"
    if args.resume:
        if not manifest.is_file() or json.loads(manifest.read_text()).get("identity") != identity:
            ap.error("Resume refused: fixture, source, settings or binaries changed")
        rows = [json.loads(line) for line in (out / "results.jsonl").read_text().splitlines()
                if line.strip()]
        if len({(r["seed"], r["drillOn"]) for r in rows}) != len(rows):
            ap.error("Duplicate checkpoint trial")
        for r in rows:
            if r.get("strictPass"):
                file = out / r["savedBoard"]
                if not file.is_file() or core.signature(json.loads(file.read_text())) != r["layoutSig"]:
                    ap.error(f"Missing/changed strict pass: {file}")
    else:
        if out.exists() and any(out.iterdir()):
            ap.error("Output exists and is nonempty; choose new --out or --resume")
        out.mkdir(parents=True, exist_ok=True)
        rows = []
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                text=True, capture_output=True, check=True).stdout.strip()
        core.write_json(manifest, {"createdUtc": datetime.now(timezone.utc).isoformat(),
                                  "gitCommit": commit, "identity": identity})
        freeze_previous(out)
    seen = {(r["seed"], r["drillOn"]) for r in rows}
    tasks = [(seed, drilled) for seed in SEEDS for drilled in MODES
             if (seed, drilled) not in seen]
    session_start = time.perf_counter()
    print("🔋 AUDIOEX | 24×56 LOCKED | BMS -2,24 | STACK ON | STRICT", flush=True)
    print(f"🔁 DRILL ON → OFF per seed | 5k | 2000 seeds | 4000 solves | ⚙️ {args.jobs} workers", flush=True)
    print("🏅 EVERY PASS: quality /100, penalties, wire length, solve + total wall time", flush=True)
    print("⚠️ Drill ON may be rejected instantly: locked BMS has adjacent pads that require knife cuts", flush=True)
    print(f"📁 {out} | {len(tasks)} remaining | 🛑 NO PASS 2", flush=True)
    # Submit in seed-paired order. Each variant has a separate temporary directory.
    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        futures = {executor.submit(make_task, out, prepared, seed, drilled, args.timeout): (seed, drilled)
                   for seed, drilled in tasks}
        for future in as_completed(futures):
            seed, drilled = futures[future]
            try:
                result, work = future.result()
                row = process_result(out, result, work, seed, drilled)
            except Exception as exc:
                row = {k: None for k in FIELD_NAMES}
                row.update(seed=seed, drillOn=drilled, strictPass=False,
                           errors=["WORKER_EXCEPTION: " + repr(exc)])
            row = encode(row)
            with (out / "results.jsonl").open("a", encoding="utf8") as stream:
                stream.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
                stream.flush()
            rows.append(row)
            if row.get("strictPass"):
                print(f"✅ PASS seed {seed:04d} {('🔩 DRILL ON' if drilled else '🔪 DRILL OFF')} "
                      f"({len(rows)}/4000) | {row['wires']}W/{row['cuts']}C | "
                      f"🏅 {row['quality100']:.2f}/100 | length {row['wireLengthMm']:.1f}mm | "
                      f"-W {row['penaltyWires']:.2f} -C {row['penaltyCuts']:.2f} "
                      f"-L {row['penaltyWireLength']:.2f} "
                      f"-diag {row['penaltyDiagonals']:.2f} "
                      f"-invalid {row['penaltyInvalid']:.2f} "
                      f"-unplaced {row['penaltyUnplaced']:.2f} | "
                      f"⏱️ solve {(row.get('solveMs') or 0)/1000:.2f}s "
                      f"trial {(row.get('elapsedWallMs') or 0)/1000:.2f}s "
                      f"total {time.perf_counter()-session_start:.1f}s", flush=True)
    publish(out, rows)
    session_wall = round(time.perf_counter() - session_start, 3)
    print(f"🏁 DONE {len(rows)}/4000 | strict passes "
          f"{sum(r.get('strictPass') is True for r in rows)} | "
          f"⏱️ current session total wall {session_wall:.1f}s", flush=True)
    print("📊 FULL QUALITY RANKING: " + str(out / "quality_leaderboard_all.csv"), flush=True)
    print("🔁 PAIRED ON/OFF: " + str(out / "paired_comparison.csv"), flush=True)
    print("💾 ALL STRICT BOARDS: " + str(out / "qualified_all"), flush=True)
    print("🏆 TOP 20: " + str(out / "top20"), flush=True)
    print("🛑 STOPPED BEFORE PASS 2", flush=True)

if __name__ == "__main__":
    main()
