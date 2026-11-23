#!/usr/bin/env python3
"""v1.63 native CLI audio.json ladder: 5k..50k by 5k; seeds 1..10.

100 independent native solves; same original audio input and board settings
for every run. A rung is a fresh anneal, not a continuation. No GUI.
Outputs are isolated and never overwrite prior ladder/benchmark data.

Run:
  python3 scripts/ladder_native_audio.py --jobs 4
  python3 scripts/ladder_native_audio.py --jobs 1 --out /tmp/audio_ladder_v163_serial

Default: routing preference=wires, existing 24x56 locked board, drilled
and no-stack OFF (matching the previous controlled ladder); use --drilled
and/or --nostack for a different experiment with a new --out directory.
"""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "src" / "frontend"
SOURCE = ROOT / "test-fixtures" / "masters" / "audio" / "audio.json"
HARNESS = FRONTEND / "tests" / "solver" / "v5Solve.js"
BUILT_SOLVER = FRONTEND / "tests" / "solver" / "out" / "components" / "stripboard" / "autoLayout5.js"
BUDGETS = tuple(range(5000, 50001, 5000))
VERSION = "v1.63-native-audio-ladder"
FIELDS = [
    "budget", "seed", "failed", "error", "exitCode", "strictValid", "historicalClean",
    "quality", "rows", "cols", "wires", "cuts", "knife", "stacked",
    "offAxis", "columnShift", "slanted", "horizontal", "crossings",
    "conflicts", "incomplete", "geo", "issues", "strictFailures",
    "price", "rate", "sig", "solveMs", "annealMs", "routeMs", "repairMs",
    "skeletonMs", "extractMs", "exactRepairMs", "totalMs", "saved",
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def physical_cores():
    try:
        return max(1, int(subprocess.check_output(
            ["sysctl", "-n", "hw.physicalcpu"], text=True,
            stderr=subprocess.DEVNULL).strip()))
    except (ValueError, OSError, subprocess.CalledProcessError):
        return max(1, os.cpu_count() or 1)


def parse_one_json(text, prefix):
    lines = [line[len(prefix):] if prefix != "{" else line
             for line in text.splitlines() if line.startswith(prefix)]
    try:
        return json.loads(lines[-1]) if lines else None
    except json.JSONDecodeError:
        return None


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".ladder-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(value, out, indent=2, ensure_ascii=False)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def emit_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run_one(out, budget, seed, drilled, nostack):
    rung = out / "runs" / ("moves_%05d" % budget)
    rung.mkdir(parents=True, exist_ok=True)
    saved = rung / ("seed_%02d.json" % seed)
    stderr_file = rung / ("seed_%02d.stderr.log" % seed)
    args = [
        "node", str(HARNESS), "--data", str(out / "input"), "--id", "1",
        "--seed", str(seed), "--moves", str(budget), "--native", "1",
        "--routing-preference", "wires", "--strict", "1", "--save", str(saved),
    ]
    if drilled:
        args.extend(["--drilled", "1"])
    if nostack:
        args.extend(["--nostack", "1"])
    env = os.environ.copy()
    env["STRIPBOARD_TIMING"] = "1"
    row = {"budget": budget, "seed": seed, "saved": str(saved), "failed": 1}
    try:
        proc = subprocess.run(args, cwd=FRONTEND, capture_output=True, text=True, env=env)
        stderr_file.write_text(proc.stderr, encoding="utf-8")
        result = parse_one_json(proc.stdout, "{")
        timing = parse_one_json(proc.stderr, "timing ")
        row["exitCode"] = proc.returncode
        if proc.returncode not in (0, 2) or not result or not timing or result.get("error"):
            raise RuntimeError("CLI exit {} / {}".format(proc.returncode, result.get("error") if result else "missing JSON"))
        if timing.get("error"):
            raise RuntimeError("Timing reports error: " + str(timing["error"]))
        if not saved.is_file():
            raise RuntimeError("CLI did not save layout")
        if result.get("strictValid") is not (proc.returncode == 0):
            raise RuntimeError("Strict verdict does not match exit code")
        if not isinstance(result.get("strictFailures"), list):
            raise RuntimeError("Missing CLI strict failure reasons")
        # Historical benchmark only rejected true slants and violations of
        # electrical/geometry/locked board, while strict CLI now also
        # prohibits horizontal jumpers. Report BOTH without conflating them.
        historical = (
            result.get("quality") == 0
            and result.get("offAxis") == 0
            and result.get("geo") == 0
            and result.get("conflicts") == 0
            and result.get("incomplete") == 0
            and not result.get("issues")
            and result.get("rows") == 24 and result.get("cols") == 56
        )
        row.update({
            "failed": 0, "error": "", "strictValid": bool(result["strictValid"]),
            "historicalClean": historical,
            "columnShift": result.get("diagonalsActual"),
            "slanted": result.get("slantedWires"),
            "horizontal": result.get("horizontalWires"),
            "issues": json.dumps(result.get("issues"), ensure_ascii=False),
            "strictFailures": ",".join(result.get("strictFailures") or []),
        })
        for key in ("quality", "rows", "cols", "wires", "cuts", "knife", "stacked",
                    "offAxis", "crossings", "conflicts", "incomplete", "geo",
                    "price", "rate", "sig"):
            row[key] = result.get(key)
        for key in ("solveMs", "annealMs", "routeMs", "repairMs",
                    "skeletonMs", "extractMs", "exactRepairMs", "totalMs"):
            row[key] = timing.get(key)
    except Exception as error:
        row["error"] = str(error)
        if saved.exists() and row.get("exitCode") not in (0, 2):
            # Leave the failed layout for diagnosis, but never qualify it.
            pass
    return row


def summarize(rows, budgets, seeds):
    summary = []
    for budget in budgets:
        group = [r for r in rows if r["budget"] == budget]
        if len(group) != len(seeds):
            raise RuntimeError("Incomplete rung: {} has {} of {} seeds".format(budget, len(group), len(seeds)))
        valid = [r for r in group if not r["failed"]]
        clean = [r for r in valid if r["strictValid"]]
        historical = [r for r in valid if r["historicalClean"]]
        def avg(field):
            nums = [float(r[field]) for r in valid if isinstance(r.get(field), (int, float))]
            return round(statistics.mean(nums), 1) if nums else None
        best = min(clean, key=lambda x: (
            int(x["wires"]), int(x["cuts"]), float(x["price"] or 1e12)
        )) if clean else None
        summary.append({
            "budget": budget, "runs": len(group), "completed": len(valid),
            "strictClean": len(clean), "historicalClean": len(historical),
            "avgWires": avg("wires"), "avgCuts": avg("cuts"),
            "avgSolveMs": avg("solveMs"), "avgAnnealMs": avg("annealMs"),
            "avgRouteMs": avg("routeMs"),
            "bestStrictSeed": best["seed"] if best else "",
            "bestStrictWires": best["wires"] if best else "",
            "bestStrictCuts": best["cuts"] if best else "",
            "bestStrictSig": best["sig"] if best else "",
        })
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=4, help="Native process concurrency; capped at physical cores")
    parser.add_argument("--out", type=Path, default=Path("/tmp/audio_native_ladder_v163"))
    parser.add_argument("--seeds", type=int, default=10, help="Use seeds 1..N (default 10)")
    parser.add_argument("--drilled", action="store_true", help="Require drilled cuts (changes experiment)")
    parser.add_argument("--nostack", action="store_true", help="Require no stacking (changes experiment)")
    args = parser.parse_args()
    if args.jobs < 1 or args.seeds < 1:
        parser.error("--jobs and --seeds must both be positive")
    out = args.out.expanduser().resolve()
    source = SOURCE.resolve()
    if out == source.parent or out == ROOT or source in out.parents or ROOT == out:
        parser.error("Refusing to write the ladder into the source repository/fixture directory")
    if not source.is_file():
        parser.error("Missing audio master: " + str(source))
    original = source.read_bytes()
    data = json.loads(original)
    board = data.get("board", {})
    if (board.get("rows"), board.get("cols"), board.get("lockedRows"), board.get("lockedCols")) != (24, 56, True, True):
        parser.error("Audio master is not a locked 24x56 input; refusing silent modification")
    if not HARNESS.is_file() or not BUILT_SOLVER.is_file() or BUILT_SOLVER.stat().st_mtime < (
            FRONTEND / "components" / "stripboard" / "autoLayout5.ts").stat().st_mtime:
        parser.error("Build TypeScript first: cd src/frontend && npx tsc -p tests/solver/tsconfig.json")
    seeds = tuple(range(1, args.seeds + 1))
    cfg = {"version": VERSION, "source": str(source), "source_sha256": sha(original),
           "budgets": BUDGETS, "seeds": seeds, "drilled": args.drilled,
           "nostack": args.nostack, "native": True, "routingPreference": "wires",
           "strict": True}
    input_copy = out / "input" / "projects" / "1.json"
    config_path = out / "ladder_config.json"
    if config_path.exists() and json.loads(config_path.read_text(encoding="utf-8")) != cfg:
        parser.error("Output belongs to a different source or settings; choose a new --out directory")
    if input_copy.exists() and input_copy.read_bytes() != original:
        parser.error("Output contains a different audio input snapshot")
    if (out / "ladder_results.csv").exists():
        parser.error("Ladder output already exists; choose another --out to preserve past results")
    input_copy.parent.mkdir(parents=True, exist_ok=True)
    if not input_copy.exists():
        shutil.copy2(source, input_copy)
    atomic_json(config_path, cfg)
    jobs = min(args.jobs, physical_cores())
    print("🎛️ {} | AUDIO locked 24x56 | SHA256 {}".format(VERSION, sha(original)), flush=True)
    print("🏁 {} seeds × {} rungs = {} native CLI solves | jobs {}".format(
        len(seeds), len(BUDGETS), len(seeds)*len(BUDGETS), jobs), flush=True)
    print("⚙️ drill={} noStack={} | historical and strict-clean reported separately".format(
        args.drilled, args.nostack), flush=True)
    print("📁 Output:", out, flush=True)
    rows = []
    for budget in BUDGETS:
        print("\n🔁 {:,} moves — {} seeds".format(budget, len(seeds)), flush=True)
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            future_map = {pool.submit(run_one, out, budget, seed, args.drilled, args.nostack): seed
                          for seed in seeds}
            for future in as_completed(future_map):
                row = future.result()
                rows.append(row)
                status = "❌ ERROR" if row["failed"] else ("✅ CLEAN" if row["strictValid"] else "⚠️ FAIL")
                print("{} #{} Q{} 🔌{} ✂️{} ↘{} 🔪{} 🧵{} ⏱{}ms".format(
                    status, row["seed"], row.get("quality", "?"), row.get("wires", "?"),
                    row.get("cuts", "?"), row.get("columnShift", "?"),
                    row.get("knife", "?"), row.get("stacked", "?"),
                    row.get("solveMs", "?")), flush=True)
        rows.sort(key=lambda x: (x["budget"], x["seed"]))
        emit_csv(out / "ladder_results.csv", rows, FIELDS)
        summary = summarize(rows, tuple(b for b in BUDGETS if b <= budget), seeds)
        emit_csv(out / "ladder_summary.csv", summary, list(summary[0]))
        latest = summary[-1]
        print("🏁 {:,}: STRICT {}/{} | historical {}/{} | best strict {} wires / {} cuts".format(
            budget, latest["strictClean"], len(seeds), latest["historicalClean"],
            len(seeds), latest["bestStrictWires"] or "—", latest["bestStrictCuts"] or "—"), flush=True)
        errors = [r for r in rows if r["failed"]]
        if errors:
            for row in errors:
                print("🛑 FAILED {} #{}: {}".format(row["budget"], row["seed"], row["error"]))
            raise SystemExit("Stopped after failing rung; original inputs and partial CSV preserved")
    print("\n✅ LADDER COMPLETE — {} solves".format(len(rows)), flush=True)
    print("📊 Results:", out / "ladder_results.csv")
    print("🏆 Summary:", out / "ladder_summary.csv")
    if jobs > 1:
        print("⚠️ Concurrent timing is contended; use --jobs 1 and a fresh --out for speed comparisons.")


if __name__ == "__main__":
    main()
