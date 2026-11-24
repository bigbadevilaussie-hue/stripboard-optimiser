#!/usr/bin/env python3
"""200 independent seeds x up to 51 USB positions each (first strict pass wins).

Native Edge+Slide MOTOEX stress-test controller. Core solver remains generic.
4 workers DEFAULT, one seed per worker; each seed probes all 51 USB positions
in nearest-to-original order, stopping only after an independently validated
strict pass. Drilled-only OFF; stacking ALLOWED; exact 24x56 locked board;
electrical, geometry, vertical wires and no-body-crossing rules stay strict.

Archives EVERY attempted JSON + logs; EVERY STRICT SOLUTION in solved/,
top five distinct valid layouts in top5/. Crash-resumable per-attempt JSONL.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from threading import Lock
import time

from run_motoex_native_edge_slide import (
    EDGE_LIB, FRONTEND, ROOT, contract, slide_positions,
)
from run_motoex_native_sweep import (
    ROUTE_LIB, NATIVE_ADDON, capture_one, jdump, key_of,
    sha256, stats_of, write_csv, write_json,
)

DEFAULT_OUT = Path.home() / "Desktop" / "motoex_native_full_slide_200x25k_v1"


def seed_positions(columns, previous):
    """The next step resumes precisely where this seed last stopped."""
    if any(x.get("strictPass") for x in previous):
        return []
    completed = {x["column"] for x in previous}
    return [col for col in columns if col not in completed]


def analyse(entries, seeds, columns, moves, started, output):
    all_attempts = sorted(entries, key=lambda e: (e["seed"], columns.index(e["column"])))
    solved = sorted((e for e in all_attempts if e.get("strictPass")),
                    key=lambda e: key_of(e, "wires"))
    unique = []
    seen = set()
    for item in solved:
        sig = item.get("layoutSig") or item.get("savedSha256")
        if sig not in seen:
            unique.append(item)
            seen.add(sig)
    top = unique[:5]
    failed = Counter(code for e in all_attempts if not e.get("strictPass")
                     for code in (e.get("strictFailures") or e.get("errors") or ["UNKNOWN"]))
    grouped = {seed: [e for e in all_attempts if e["seed"] == seed] for seed in seeds}
    outcomes = []
    for seed in seeds:
        attempts = grouped[seed]
        winner = next((e for e in attempts if e.get("strictPass")), None)
        outcomes.append({
            "seed": seed, "positionsAttempted": len(attempts),
            "positionsAvailable": len(columns), "strictPass": winner is not None,
            "winnerColumn": winner["column"] if winner else None,
            "winningJson": winner.get("savedJson") if winner else None,
            "elapsedWallMs": round(sum((e.get("elapsedWallMs") or 0) for e in attempts), 2),
            "fullyExhausted": winner is None and len(attempts) == len(columns),
        })
    per_col = {str(col): {
        "attempts": sum(e["column"] == col for e in all_attempts),
        "strictPasses": sum(e["column"] == col and e.get("strictPass") for e in all_attempts),
    } for col in columns}
    summary = {
        "seedsRequested": len(seeds),
        "seedsFinished": sum(o["strictPass"] or o["fullyExhausted"] for o in outcomes),
        "strictSolvedSeeds": sum(o["strictPass"] for o in outcomes),
        "totalPositionsAttempted": len(all_attempts),
        "maximumPossiblePositions": len(seeds) * len(columns),
        "movesPerPosition": moves,
        "annealMovesBudgetAttempted": len(all_attempts) * moves,
        "distinctSolvedLayouts": len(unique),
        "drilledCutsOnly": False, "stackingForbidden": False,
        "usbSlide": True, "stopAtFirstStrictPerSeed": True,
        "strictBoard": "24x56", "columns": columns,
        "durationWallS": round(time.perf_counter() - started, 2),
        "timing": {field: stats_of([e.get("time", {}).get(field) for e in all_attempts])
                   for field in ("solveMs", "totalMs", "cpuMs", "rssMb")},
        "elapsedPositionWallMs": stats_of([e.get("elapsedWallMs") for e in all_attempts]),
        "firstFitMs": stats_of([e.get("firstFeasibleMs") for e in all_attempts]),
        "failureHistogram": dict(failed.most_common()),
        "byColumn": per_col,
        "top5": top,
        "allSolved": [{"seed": e["seed"], "column": e["column"],
                       "wires": e.get("wires"), "cuts": e.get("cuts"),
                       "knife": e.get("knife"), "stacked": e.get("stacked"),
                       "json": e.get("savedJson"), "layoutSig": e.get("layoutSig")}
                      for e in solved],
        "seedOutcomes": outcomes,
    }
    write_json(output / "summary.json", summary)
    write_json(output / "results.json", {"summary": {
        k: v for k, v in summary.items() if k not in ("top5", "allSolved", "seedOutcomes")
    }, "seeds": outcomes, "attempts": all_attempts})
    write_csv(output / "results.csv", all_attempts)
    (output / "solved_index.jsonl").write_text(
        "".join(jdump(e) + "\n" for e in solved), encoding="utf8")
    top_dir = output / "top5"
    top_dir.mkdir(parents=True, exist_ok=True)
    for rank, winner in enumerate(top, 1):
        shutil.copy2(output / winner["savedJson"],
            top_dir / ("rank_{:02d}_seed_{:04d}_col_{:02d}_W{}_C{}.json".format(
                rank, winner["seed"], winner["column"], winner["wires"], winner["cuts"])))
    lines = [
        "# Exhaustive native Edge USB Slide — 200 seeds x up to 51 positions", "",
        "**No false winners:** all saved JSONs under solved/ independently passed",
        "strict electrical and physical checking. Knives and stacks were permitted.",
        "", "- Seeds finished: **{} / {}**".format(summary["seedsFinished"], len(seeds)),
        "- Strict-solved seeds: **{}**".format(summary["strictSolvedSeeds"]),
        "- Total physical solver attempts: **{} / {} max**".format(
            len(all_attempts), len(seeds) * len(columns)),
        "- Distinct strict-solved layouts: **{}**".format(len(unique)),
        "- Wall seconds: **{}**".format(summary["durationWallS"]),
        "", "## Top five distinct strict solutions", "",
        "| Rank | Seed | USB col | Wires | Cuts | Knives | Stacks | Solve ms | JSON |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for i, e in enumerate(top, 1):
        lines.append("| {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            i, e["seed"], e["column"], e["wires"], e["cuts"], e["knife"],
            e["stacked"], e.get("time", {}).get("solveMs"), e["savedJson"]))
    if not top:
        lines.append("| — | — | — | — | — | — | — | — | NO STRICT SOLUTIONS |")
    lines.extend(["", "## Failure codes", ""])
    lines.extend("- {}: {}".format(code, n) for code, n in failed.most_common())
    lines.extend(["", "## Archive", "",
                  "- solved/: ALL strict-solved project JSONs",
                  "- rejected/: ALL rejected project JSONs",
                  "- jobs/: per-attempt inputs, stdout, stderr and finish traces",
                  "- results.jsonl: live, per-position checkpoint",
                  "- results.csv / results.json: per-position timings and diagnostics",
                  "- summary.json: winner index, per-column and per-seed timing",
                  "- manifest.json: code and binary hashes",
                  "- top5/: copies of best five distinct strict winners",
                  ""])
    (output / "report.md").write_text("\n".join(lines), encoding="utf8")
    return summary


def run(args):
    started = time.perf_counter()
    source = contract.MASTER.read_bytes()
    master = json.loads(source)
    usb, definition, overhang = contract.usb_source(master)
    columns = slide_positions(usb, definition, 24, 56, True)
    if len(columns) != 51:
        raise ValueError("Expected all 51 legal positions")
    for required in (EDGE_LIB / "libv5decode.so", ROUTE_LIB, NATIVE_ADDON,
                     contract.CLI, FRONTEND / "tests/solver/out/components/stripboard/autoLayout5.js"):
        if not required.is_file():
            raise ValueError("Missing build prerequisite: " + str(required))
    out = args.out.expanduser().resolve()
    if out.exists() and any(out.iterdir()) and not args.resume:
        raise ValueError("Nonempty output directory; use fresh --out or --resume")
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "manifest.json"
    source_hash = hashlib.sha256(source).hexdigest()
    manifest = {
        "createdUTC": datetime.now(timezone.utc).isoformat(),
        "sourceSha256": source_hash,
        "gitCommit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                   capture_output=True, text=True, check=True).stdout.strip(),
        "board": [24, 56], "USB": {"row": 13, "originCol": 47, "overhangRows": overhang,
                                     "slide": True, "columns": columns},
        "seeds": args.seeds, "seedStart": args.seed_start,
        "moves": args.moves, "workers": args.workers,
        "timeout": args.timeout, "wirePolish": args.wire_polish,
        "drilled": False, "noStack": False, "drillDomain": False,
        "libraries": {str(p.relative_to(ROOT)): sha256(p) for p in
                      (EDGE_LIB / "libv5decode.so", ROUTE_LIB, NATIVE_ADDON)},
    }
    if args.resume:
        if not manifest_path.is_file():
            raise ValueError("Missing manifest.json for resume")
        before = json.loads(manifest_path.read_text(encoding="utf8"))
        for field in ("sourceSha256", "USB", "seeds", "seedStart", "moves", "timeout",
                      "wirePolish", "drilled", "noStack", "drillDomain", "libraries"):
            if before.get(field) != manifest.get(field):
                raise ValueError("Resume mismatch: " + field)
    else:
        write_json(manifest_path, manifest)

    checkpoint = out / "results.jsonl"
    completed = {}
    if args.resume and checkpoint.is_file():
        for line in checkpoint.read_text(encoding="utf8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            pair = record["seed"], record["column"]
            if pair in completed:
                raise ValueError("Duplicate completed position: " + str(pair))
            if record.get("sourceSha256") != source_hash:
                raise ValueError("Source changed in checkpoint")
            if record.get("savedJson") and not (out / record["savedJson"]).is_file():
                raise ValueError("Missing archived JSON: " + record["savedJson"])
            completed[pair] = record
    guard = Lock()
    progress = out / "progress.log"
    seeds = list(range(args.seed_start, args.seed_start + args.seeds))

    def log(message):
        with guard:
            print(message, flush=True)
            with progress.open("a", encoding="utf8") as f:
                f.write(message + "\n")

    def worker(seed):
        existing = [completed[(seed, col)] for col in columns if (seed, col) in completed]
        if existing:
            positions = [e["column"] for e in existing]
            expected = columns[:len(positions)]
            if positions != expected:
                raise ValueError("Checkpoint has gaps in seed {}: {}".format(seed, positions))
        remaining = seed_positions(columns, existing)
        if not remaining:
            return {"seed": seed, "win": next((x for x in existing if x.get("strictPass")), None),
                    "attempts": len(existing)}
        for col in remaining:
            # capture_one writes each project/log to a unique job folder and
            # archives the candidate to solved/ or rejected/.
            entry = capture_one(args, master, seed, col, out, source_hash)
            pair = seed, col
            with guard:
                if pair in completed:
                    raise AssertionError("Repeated position: " + str(pair))
                with checkpoint.open("a", encoding="utf8") as f:
                    f.write(jdump(entry) + "\n")
                    f.flush()
                    os.fsync(f.fileno())
                completed[pair] = entry
                n = len([1 for p in completed if p[0] == seed])
                solved_so_far = len({e["seed"] for e in completed.values() if e.get("strictPass")})
                kind = "✅ STRICT PASS" if entry.get("strictPass") else (
                    "🛑 NO FIT" if entry.get("unsolvedReason") else "❌ NOT STRICT")
                message = "{} seed {} col {} ({}/51) | {}W/{}C | {:.2f}s | strict seeds {}".format(
                    kind, seed, col, n, entry.get("wires", "?"), entry.get("cuts", "?"),
                    (entry.get("elapsedWallMs") or 0) / 1000, solved_so_far)
                print(message, flush=True)
                with progress.open("a", encoding="utf8") as f:
                    f.write(message + "\n")
            if entry.get("strictPass"):
                return {"seed": seed, "win": entry, "attempts": n}
        return {"seed": seed, "win": None, "attempts": len(columns)}

    log("🏁 200-SEED EXHAUSTIVE SLIDE | {} seeds × 25k moves per position | 51 columns/seed MAX".format(args.seeds))
    log("🧵 {} workers | USB Edge + Slide YES | col order {}".format(args.workers, columns))
    log("🔪 DRILLED OFF (knives allowed) | 🧷 STACKS ON | 🛡️ strict 24×56 + electrical + vertical + geometry")
    log("💾 Solved JSONs, rejected JSONs, full timing/diagnostics, top five + per-position checkpoint")
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        tasks = {pool.submit(worker, seed): seed for seed in seeds}
        for task in as_completed(tasks):
            seed = tasks[task]
            try:
                state = task.result()
                log("{} SEED {} finished {} / 51 positions{}".format(
                    "🏆" if state["win"] else "🛑", seed, state["attempts"],
                    " | STRICT winner col {}".format(state["win"]["column"]) if state["win"] else " | no strict pass"))
            except Exception as error:
                log("❌ SEED {} CONTROLLER ERROR: {!r}".format(seed, error))
                raise

    report = analyse(list(completed.values()), seeds, columns, args.moves, started, out)
    log("🏆 TOP 5 DISTINCT STRICT SOLVED (fewest wires, then cuts)")
    for rank, entry in enumerate(report["top5"], 1):
        log("🏅 #{} SEED {} COL {} | {}W/{}C knife={} stack={} | {}".format(
            rank, entry["seed"], entry["column"], entry["wires"], entry["cuts"],
            entry.get("knife"), entry.get("stacked"), entry.get("savedJson")))
    if not report["top5"]:
        log("🛑 No strict PASS — all failed candidates retained")
    log("🏁 {} / {} SEEDS STRICTLY SOLVED | {} attempts | {} seconds | {}".format(
        report["strictSolvedSeeds"], args.seeds, report["totalPositionsAttempted"],
        report["durationWallS"], out / "report.md"))
    if contract.MASTER.read_bytes() != source:
        raise AssertionError("Master fixture changed during sweep")
    return 0 if report["seedsFinished"] == args.seeds else 2


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seeds", type=int, default=200)
    p.add_argument("--seed-start", type=int, default=1)
    p.add_argument("--moves", type=int, default=25000)
    p.add_argument("--workers", type=int, default=4, choices=(3, 4))
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--wire-polish", choices=("yes", "no"), default="yes")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--resume", action="store_true")
    args = p.parse_args()
    args.wire_polish = args.wire_polish == "yes"
    args.slide = True
    args.rank = "wires"
    if args.seeds < 1 or args.moves < 1 or args.timeout < 1 or args.seed_start < 0:
        p.error("seeds/moves/timeout positive, seed-start nonnegative")
    try:
        return run(args)
    except (OSError, ValueError, AssertionError, subprocess.CalledProcessError) as error:
        print("🛑 FULL-SLIDE SWEEP ERROR: " + str(error), file=sys.stderr)
        return 64


if __name__ == "__main__":
    sys.exit(main())
