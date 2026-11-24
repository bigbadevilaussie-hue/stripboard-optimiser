#!/usr/bin/env python3
"""WR Audio + Moto: seeds 1..2000 at 5k,10k,20k; save EVERY strict pass only.

Desktop/WR_Audio/{5k,10k,20k}/seed_0001.json ...
Desktop/WR_Moto/{5k,10k,20k}/seed_0001.json ...

Run: python3 scripts/run_wr_audio_moto.py --jobs 3
Rerun safely: python3 scripts/run_wr_audio_moto.py --jobs 3 --resume

Uses the existing native CLI + independent saved-board auditor. No new solver.
No top-10/top-20 filtering, no rejected JSONs or per-seed log archives.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import run_audioex_native_ladder as core
from scripts.run_audio_net_drill_on_debug50_20k import verify_netlist
from scripts.run_audioex_10k_2000_quality import score_quality

BUDGETS = (5_000, 10_000, 20_000)
SEEDS = range(1, 2001)
CIRCUITS = {
    "Audio": ROOT / "test-fixtures/masters/audio/audio.json",
    "Moto": ROOT / "test-fixtures/masters/moto/moto.json",
}
REQUIRED = (core.CLI, core.AUDITOR, core.EDGE_DECODE, core.NATIVE_ROUTE,
            core.NATIVE_ADDON, core.SOLVER_JS)
FIELDS = ("seed", "moves", "pass", "quality100", "wires", "cuts", "wireLengthMm",
          "price", "layoutSig", "file", "elapsedWallMs")


def identity(source: Path):
    required = (source, source.with_suffix(".net"), *REQUIRED)
    for p in required:
        if not p.is_file():
            raise FileNotFoundError(f"Missing required file: {p}")
    return {str(p.relative_to(ROOT)): core.digest(p.read_bytes()) for p in required}


def save_index(folder: Path, completed: set[int], passed: dict[int, dict]) -> None:
    """Store only completed seed IDs and independently audited passes."""
    folder.mkdir(parents=True, exist_ok=True)
    core.write_json(folder / "completed_seeds.json", sorted(completed))
    index = folder / "passes.jsonl"
    tmp = folder / "passes.jsonl.tmp"
    with tmp.open("w", encoding="utf8") as f:
        for row in sorted(passed.values(), key=lambda r: r["seed"]):
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    tmp.replace(index)
    tmp_csv = folder / "passes.csv.tmp"
    with tmp_csv.open("w", newline="", encoding="utf8") as f:
        writer = csv.DictWriter(f, FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in sorted(passed.values(), key=lambda r: r["seed"]):
            writer.writerow(row)
    tmp_csv.replace(folder / "passes.csv")

def run_seed(prepared: dict, moves: int, seed: int, folder: Path, timeout: int):
    # Core checks CLI strict + independent saved-board audit and board bounds.
    # Its scratch logs and rejected JSONs are deleted with the temp directory.
    with tempfile.TemporaryDirectory(prefix=f"wr_{moves}_{seed}_") as tmp:
        scratch = Path(tmp)
        try:
            r = core.run_one(scratch, prepared, moves, seed, timeout=timeout,
                             drilled=False, drill_domain=False,
                             forensic=False, enforce_bms_anchor=False)
            passed = r.get("strictPass") is True
            result = {
                "seed": seed, "moves": moves, "pass": passed,
                "quality100": None, "wires": r.get("wires"), "cuts": r.get("cuts"),
                "wireLengthMm": None, "price": r.get("price"),
                "layoutSig": r.get("layoutSig"), "file": None,
                "elapsedWallMs": r.get("elapsedWallMs"),
                "reason": None
            }
            if passed:
                source = scratch / r["savedJson"]
                data = json.loads(source.read_text(encoding="utf8"))
                quality, length, _penalties = score_quality(data)
                target = folder / f"seed_{seed:04d}.json"
                if target.exists():
                    raise FileExistsError(f"Refusing to overwrite saved pass: {target}")
                staged = target.with_suffix(".json.tmp")
                shutil.copyfile(source, staged)
                os.replace(staged, target)
                result.update(quality100=quality, wireLengthMm=length,
                              file=target.name)
            return result
        except Exception as exc:
            return {"seed": seed, "moves": moves, "pass": False,
                    "quality100": None, "wires": None, "cuts": None,
                    "wireLengthMm": None, "price": None, "layoutSig": None,
                    "file": None, "elapsedWallMs": None,
                    "reason": None}


def load_existing(folder: Path) -> tuple[set[int], dict[int, dict]]:
    """Migrate previous all-result checkpoints without retaining failure details."""
    old = folder / "results.jsonl"
    completed_file = folder / "completed_seeds.json"
    new = folder / "passes.jsonl"
    completed = set(json.loads(completed_file.read_text(encoding="utf8"))) if completed_file.exists() else set()
    passed = {}
    if new.exists():
        for line in new.read_text(encoding="utf8").splitlines():
            if line.strip():
                row = json.loads(line)
                passed[row["seed"]] = row
                completed.add(row["seed"])
    if old.exists():
        for line in old.read_text(encoding="utf8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            completed.add(row["seed"])
            if row.get("pass"):
                passed[row["seed"]] = row
        save_index(folder, completed, passed)
        old.unlink()
    for row in passed.values():
        if not (folder / row["file"]).is_file():
            raise FileNotFoundError(f"Passing JSON missing: {folder / row['file']}")
    return completed, passed



def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--desktop", type=Path, default=Path.home() / "Desktop")
    ap.add_argument("--seed-start", type=int, default=1,
                    help="Diagnostic subset starting seed (default 1)")
    ap.add_argument("--seed-end", type=int, default=2000,
                    help="Diagnostic subset ending seed (default 2000)")
    args = ap.parse_args()
    if args.jobs < 1 or args.timeout < 1:
        ap.error("jobs and timeout must be positive")
    if not (1 <= args.seed_start <= args.seed_end <= 2000):
        ap.error("seed range must be within 1..2000")
    # Default runs full 2000. Partial runs need explicit --resume to finish.
    wanted = set(range(args.seed_start, args.seed_end + 1))
    prepared_cases = []
    for name, source in CIRCUITS.items():
        data = json.loads(source.read_text(encoding="utf8"))
        if (data["board"].get("rows"), data["board"].get("cols"),
            data["board"].get("lockedRows"), data["board"].get("lockedCols")) != (24, 56, True, True):
            ap.error(f"Expected locked 24×56: {source}")
        if any(c.get("locked") and c.get("boardPos") for c in data["components"]):
            ap.error(f"Expected unlocked component placements in {source}")
        verify_netlist(data, source.with_suffix(".net").read_text(encoding="utf8"))
        prepared_cases.append((name, data, identity(source)))

    for name, data, fingerprints in prepared_cases:
        for moves in BUDGETS:
            folder = args.desktop.expanduser() / f"WR_{name}" / f"{moves//1000}k"
            manifest_file = folder / "manifest.json"
            expected = {
                "schema": "WR-audio-moto-passes-only/v1",
                "circuit": name, "moves": moves, "seedRange": [1, 2000],
                "drilled": False, "drillRotationDomain": False,
                "wireStacking": True, "strict": True, "independentAudit": True,
                "routingPreference": "wires", "wirePolish": False,
                "identity": fingerprints,
                "qualityFormula": "max(0,100-15*unplaced-10*nonvertical-0.4*cuts-0.6*wires-0.02*wireLengthMm)",
                "note": "Only independently strict-passing candidate JSONs retained; all seeds in results.jsonl",
            }
            if manifest_file.exists():
                if not args.resume:
                    ap.error(f"Already exists: {folder}. Use --resume.")
                if json.loads(manifest_file.read_text(encoding="utf8")) != expected:
                    ap.error(f"Identity or config differs; refusing to resume: {folder}")
            else:
                if args.resume and any((folder / file).exists() for file in ("results.jsonl", "passes.jsonl", "completed_seeds.json")):
                    ap.error(f"Cannot resume without manifest: {folder}")
                core.write_json(manifest_file, expected)
            # Allow a small smoke run without changing default 1..2000.
            sweep_subset(name, data, moves, folder, args.jobs, args.timeout,
                         args.resume, wanted)
    print("\n🏆 FINISHED | WR_Audio + WR_Moto | 5k / 10k / 20k | ALL passes saved", flush=True)
    return 0


def sweep_subset(name, prepared, moves, folder, jobs, timeout, resume, wanted):
    """Save every pass; failed seeds are only a number in the resume checkpoint."""
    completed, passed = load_existing(folder) if resume else (set(), {})
    todo = [seed for seed in SEEDS if seed in wanted and seed not in completed]
    print(f"\n🚀 {name.upper()} {moves//1000}k | {len(todo)} seeds | {jobs} workers", flush=True)
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = {pool.submit(run_seed, prepared, moves, seed, folder, timeout): seed
                   for seed in todo}
        try:
            for fut in as_completed(futures):
                row = fut.result()
                seed = row["seed"]
                if seed in completed:
                    raise RuntimeError(f"Duplicate seed {seed}")
                if row["pass"]:
                    row.pop("reason", None)
                    passed[seed] = row
                completed.add(seed)
                save_index(folder, completed, passed)
                if row["pass"]:
                    print(f"✅ {name} {moves//1000}k seed {seed:04d}/2000 "
                          f"| ⭐ {row['quality100']:.2f}/100 "
                          f"| {row['wires']}W/{row['cuts']}C "
                          f"| 💾 {row['file']} | passes {len(passed)}", flush=True)
        except KeyboardInterrupt:
            for f in futures:
                f.cancel()
            print("\n⏸️ Interrupted. Re-run with --resume.", flush=True)
            raise
    print(f"🏁 {name} {moves//1000}k | ✅ {len(passed)}/{len(completed)} "
          f"| 📁 {folder}", flush=True)

if __name__ == "__main__":
    sys.exit(main())
