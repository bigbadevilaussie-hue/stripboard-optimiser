#!/usr/bin/env python3
"""Replay the MOTOEX winner's seed/USB anchor at increasing anneal budgets.

Default 43 independent trials: 5k, 10k, ... 200k, 300k, 400k, 500k.
This is a fresh solve from the canonical master for EACH budget; the existing
solver does NOT yet support a warm-start from the solved winner's placement.
The 44W/60C saved JSON is copied unchanged as a benchmark competitor.

Knives and wire stacks permitted; every net must be electrically complete,
there must be no copper conflicts, nonvertical jumpers or body crossings,
and pins/cuts/wire endpoints must stay on the locked 24x56 board.
Package-body overhang is reported as a nonfatal build warning.
All trials, including rejections, are archived and resume is checkpointed.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import os
import shutil
import subprocess
import sys
import time

from run_motoex_native_edge_slide import EDGE_LIB, FRONTEND, ROOT, contract
from run_motoex_native_sweep import (
    NATIVE_ADDON, ROUTE_LIB, capture_one, jdump, key_of, physical_layout_signature,
    sha256, wire_length, write_json,
)

MOVES = tuple(range(5_000, 200_001, 5_000)) + (300_000, 400_000, 500_000)
SEED, COLUMN = 37, 23
DEFAULT_OUT = Path.home() / "Desktop" / "motoex_seed37_col23_ladder"
DEFAULT_BASELINE = Path.home() / "Desktop" / "MOTOEX_STRICT_44W_60C.json"
REQUIRED = (
    EDGE_LIB / "libv5decode.so",
    ROUTE_LIB,
    NATIVE_ADDON,
    contract.CLI,
    FRONTEND / "tests/solver/out/components/stripboard/autoLayout5.js",
)


def parse_moves(text: str) -> tuple[int, ...]:
    try:
        moves = tuple(int(t.strip()) for t in text.split(","))
    except ValueError as error:
        raise argparse.ArgumentTypeError("moves must be comma-separated integers") from error
    if not moves or any(n <= 0 for n in moves) or list(moves) != sorted(set(moves)):
        raise argparse.ArgumentTypeError("moves must be positive, increasing and unique")
    return moves


def validate_baseline(saved: dict) -> None:
    board = saved.get("board") or {}
    if (board.get("rows"), board.get("cols")) != (24, 56):
        raise ValueError("Baseline must have locked board dimensions 24x56")
    if (len(board.get("wires", [])), len(board.get("cuts", []))) != (44, 60):
        raise ValueError("Baseline must be the 44-wire/60-cut saved winner")
    usb = [c for c in saved.get("components", []) if c.get("label") == "USB"]
    if len(usb) != 1 or usb[0].get("boardPos") != {"row": 13, "col": COLUMN}:
        raise ValueError("Baseline must be the saved seed-37 USB-column-23 board")


def rank_candidates(rows: list[dict]) -> list[dict]:
    qualified = [r for r in rows if r.get("strictPass")]
    qualified.sort(key=lambda r: key_of(r, "wires"))
    distinct, signatures = [], set()
    for row in qualified:
        signature = row.get("layoutSig") or row.get("savedSha256")
        if signature in signatures:
            continue
        signatures.add(signature)
        distinct.append(row)
    return distinct


def checkpoint_rows(folder: Path, allowed: tuple[int, ...], source_hash: str) -> list[dict]:
    checkpoint = folder / "results.jsonl"
    rows, seen = [], set()
    if checkpoint.is_file():
        for line in checkpoint.read_text(encoding="utf8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            moves = r["moves"]
            if moves not in allowed or moves in seen or r.get("sourceSha256") != source_hash:
                raise ValueError("Incompatible/duplicate ladder checkpoint: " + str(moves))
            seen.add(moves)
            if r.get("savedJson") and not (folder / r["savedJson"]).is_file():
                raise ValueError("Missing archived result: " + r["savedJson"])
            rows.append(r)
    return rows


def publish(folder: Path, rows: list[dict], baseline: dict, start: float, requested: tuple[int, ...]) -> dict:
    all_rows = [baseline, *rows]
    top = rank_candidates(all_rows)
    champion = top[0] if top else None
    strict_trials = [r for r in rows if r.get("strictPass")]
    summary = {
        "policy": "strict electrical/copper/vertical/crossing with package overhang warnings",
        "seed": SEED, "usbColumn": COLUMN, "movesRequested": list(requested),
        "completed": len(rows), "total": len(requested),
        "strictTrialPasses": len(strict_trials),
        "improvementsAgainstBaseline": sum(
            key_of(r, "wires") < key_of(baseline, "wires") for r in strict_trials
        ),
        "baseline": baseline,
        "champion": champion,
        "top5": top[:5],
        "elapsedWallS": round(time.perf_counter() - start, 2),
        "trials": rows,
    }
    write_json(folder / "summary.json", summary)
    cols = ["moves", "strictPass", "wires", "cuts", "wireLength", "price",
            "knife", "stacked", "nonvertical", "crossings", "conflicts", "incomplete",
            "geometry", "bodyOverhangWarnings", "elapsedWallMs", "savedJson",
            "strictFailures", "errors"]
    with (folder / "results.csv").open("w", newline="", encoding="utf8") as h:
        writer = csv.DictWriter(h, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        for row in sorted(rows, key=lambda r: r["moves"]):
            line = dict(row)
            for k in ("bodyOverhangWarnings", "strictFailures", "errors"):
                line[k] = jdump(line.get(k, []))
            writer.writerow(line)
    top_dir = folder / "top5"
    top_dir.mkdir(exist_ok=True)
    for old in top_dir.glob("rank_*.json"):
        old.unlink()
    for i, row in enumerate(top[:5], 1):
        original = folder / row["savedJson"]
        shutil.copy2(original, top_dir /
            f"rank_{i:02d}_{row.get('moves', 'baseline')}_W{row['wires']}_C{row['cuts']}.json")
    if champion:
        shutil.copy2(folder / champion["savedJson"], folder / "champion.json")
    return summary


def run(args: argparse.Namespace) -> int:
    started = time.perf_counter()
    master_bytes = contract.MASTER.read_bytes()
    master = json.loads(master_bytes)
    contract.usb_source(master)
    baseline_data = args.baseline.expanduser().resolve().read_bytes()
    baseline_project = json.loads(baseline_data)
    validate_baseline(baseline_project)
    for prerequisite in REQUIRED:
        if not prerequisite.is_file():
            raise ValueError("Missing build prerequisite: " + str(prerequisite))
    source_hash = hashlib.sha256(master_bytes).hexdigest()
    out = args.out.expanduser().resolve()
    manifest_path = out / "manifest.json"
    if out.exists() and any(out.iterdir()) and not args.resume:
        raise ValueError("Nonempty output directory: use --resume or a new --out")
    out.mkdir(parents=True, exist_ok=True)
    manifest = {
        "createdUTC": datetime.now(timezone.utc).isoformat(),
        "gitCommit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                    capture_output=True, check=True, text=True).stdout.strip(),
        "sourcePath": str(contract.MASTER),
        "sourceSha256": source_hash,
        "baselineSha256": hashlib.sha256(baseline_data).hexdigest(),
        "baselinePath": str(args.baseline.expanduser().resolve()),
        "seed": SEED, "usb": {"row": 13, "column": COLUMN, "edge": True, "slide": True},
        "moves": list(args.moves),
        "timeout": args.timeout, "wirePolish": True,
        "drilledOnly": False, "stackingAllowed": True, "drillDomain": False,
        "strictElectrical": True, "strictVerticalJumpers": True,
        "strictWireBodyCrossings": True, "bodyOverhangWarningsAllowed": True,
        "binaries": {str(p.relative_to(ROOT)): sha256(p) for p in REQUIRED},
    }
    if args.resume:
        if not manifest_path.is_file():
            raise ValueError("No manifest.json for resume")
        old = json.loads(manifest_path.read_text(encoding="utf8"))
        for key in ("sourceSha256", "baselineSha256", "seed", "usb", "moves",
                    "timeout", "wirePolish", "drilledOnly", "stackingAllowed",
                    "drillDomain", "binaries"):
            if manifest[key] != old.get(key):
                raise ValueError("Resume refused: " + key + " differs from manifest")
    else:
        write_json(manifest_path, manifest)
        shutil.copy2(args.baseline.expanduser().resolve(), out / "original_winner_44W_60C.json")

    baseline = {
        "source": "preserved seed-37 baseline", "seed": SEED, "column": COLUMN,
        "strictPass": True, "moves": None, "wires": 44, "cuts": 60,
        "wireLength": wire_length(baseline_project), "price": None,
        "layoutSig": physical_layout_signature(baseline_project),
        "savedJson": "original_winner_44W_60C.json",
        "bodyOverhangWarnings": ["Q1", "C6"],
    }
    if not (out / baseline["savedJson"]).is_file():
        raise ValueError("Original winner baseline copy missing")
    rows = checkpoint_rows(out, args.moves, source_hash)
    seen = {r["moves"] for r in rows}
    summary = publish(out, rows, baseline, started, args.moves)
    print(f"🏁 SEED {SEED} / USB COL {COLUMN} | {len(args.moves)} budgets | "
          "5k ladder to 200k + 300/400/500k", flush=True)
    print("💾 Original 44W/60C preserved; 10mm package overhangs are warnings", flush=True)
    for move_count in args.moves:
        if move_count in seen:
            print(f"⏭️ {move_count//1000}k already archived", flush=True)
            continue
        stage_folder = out / "runs" / f"moves_{move_count:06d}"
        stage_folder.mkdir(parents=True, exist_ok=True)
        trial_args = argparse.Namespace(**{**vars(args), "moves": move_count})
        result = capture_one(trial_args, master, SEED, COLUMN, stage_folder, source_hash)
        result["moves"] = move_count
        for field in ("input", "stdoutLog", "stderrLog", "savedJson"):
            if result.get(field):
                result[field] = str(Path("runs") / stage_folder.name / result[field])
        result["source"] = "fresh seed-37 solve at move budget"
        with (out / "results.jsonl").open("a", encoding="utf8") as h:
            h.write(jdump(result) + "\n")
            h.flush()
            os.fsync(h.fileno())
        rows.append(result)
        seen.add(move_count)
        summary = publish(out, rows, baseline, started, args.moves_schedule)
        champion = summary["champion"]
        status = "✅ STRICT" if result.get("strictPass") else "❌ REJECTED"
        if result.get("unsolvedReason"):
            status = "🛑 NO FIT"
        score = f"{result.get('wires', '?')}W/{result.get('cuts', '?')}C"
        leader = f"{champion['wires']}W/{champion['cuts']}C" if champion else "none"
        better = result.get("strictPass") and key_of(result, "wires") < key_of(baseline, "wires")
        line = (f"{'🏆' if better else status} {move_count//1000:>3}k | {score} | "
                f"best {leader} | {len(rows)}/{len(args.moves_schedule)} "
                f"| {(result.get('elapsedWallMs') or 0)/1000:.2f}s")
        print(line, flush=True)
        with (out / "progress.log").open("a", encoding="utf8") as log:
            log.write(line + "\n")
        if not result.get("strictPass"):
            reason = result.get("strictFailures") or result.get("errors") or []
            if reason:
                print("   ↳ " + ", ".join(map(str, reason[:5]))[:220], flush=True)
    if contract.MASTER.read_bytes() != master_bytes:
        raise AssertionError("Master JSON changed during ladder")
    summary = publish(out, rows, baseline, started, args.moves_schedule)
    winner = summary["champion"]
    print(f"🏁 DONE — {summary['strictTrialPasses']} strict ladder passes | "
          f"champion {winner['wires']}W/{winner['cuts']}C"
          f" | {out/'champion.json'}", flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--moves", type=parse_moves, default=MOVES,
                        help="optional smoke run: --moves 5000,10000; default full 43-level ladder")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.timeout < 1:
        parser.error("--timeout must be positive")
    args.moves_schedule = args.moves
    args.slide = True
    args.wire_polish = True
    args.rank = "wires"
    try:
        return run(args)
    except (ValueError, OSError, AssertionError, subprocess.CalledProcessError) as error:
        print("🛑 LADDER SETUP/ARCHIVE ERROR: " + str(error), file=sys.stderr)
        return 64


if __name__ == "__main__":
    sys.exit(main())
