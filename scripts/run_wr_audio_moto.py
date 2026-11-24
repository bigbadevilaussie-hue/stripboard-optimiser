#!/usr/bin/env python3
"""Audio + Moto, seeds 1..2000 at 5k/10k/20k. Print and save STRICT PASSES ONLY."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import argparse
import json
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import run_audioex_native_ladder as core
from scripts.run_audio_net_drill_on_debug50_20k import verify_netlist
from scripts.run_audioex_10k_2000_quality import score_quality

CIRCUITS = {
    "Audio": ROOT / "test-fixtures/masters/audio/audio.json",
    "Moto": ROOT / "test-fixtures/masters/moto/moto.json",
}
BUDGETS = (5000, 10000, 20000)

def trial(project, moves, seed, folder, timeout):
    with tempfile.TemporaryDirectory(prefix="wr_trial_") as tmp:
        try:
            row = core.run_one(Path(tmp), project, moves, seed, timeout=timeout,
                               drilled=False, drill_domain=False,
                               forensic=False, enforce_bms_anchor=False)
            if row.get("strictPass") is not True:
                return None
            saved = Path(tmp) / row["savedJson"]
            score, _, _ = score_quality(json.loads(saved.read_text(encoding="utf8")))
            destination = folder / f"seed_{seed:04d}.json"
            if destination.exists():
                raise FileExistsError(f"Refusing to overwrite: {destination}")
            shutil.copy2(saved, destination)
            return seed, score, row["wires"], row["cuts"], destination.name
        except Exception:
            return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=1800)
    args = ap.parse_args()
    if args.jobs < 1 or args.timeout < 1:
        ap.error("--jobs and --timeout must be positive")
    for name, source in CIRCUITS.items():
        project = json.loads(source.read_text(encoding="utf8"))
        verify_netlist(project, source.with_suffix(".net").read_text(encoding="utf8"))
        for moves in BUDGETS:
            folder = Path.home() / "Desktop" / f"WR_{name}" / f"{moves//1000}k"
            # Fresh WR run: clear only this circuit/budget output directory.
            if folder.exists():
                shutil.rmtree(folder)
            folder.mkdir(parents=True, exist_ok=True)
            print(f"🧹 Cleared {folder}", flush=True)
            print(f"🚀 {name} {moves//1000}k | seeds 1–2000", flush=True)
            count = 0
            with ThreadPoolExecutor(max_workers=args.jobs) as pool:
                futures = [pool.submit(trial, project, moves, seed, folder, args.timeout)
                           for seed in range(1, 2001)]
                for fut in as_completed(futures):
                    result = fut.result()
                    if result is not None:
                        seed, score, wires, cuts, filename = result
                        count += 1
                        print(f"✅ {name} {moves//1000}k seed {seed:04d} "
                              f"| ⭐ {score:.2f}/100 | {wires}W/{cuts}C "
                              f"| 💾 {filename}", flush=True)
            print(f"🏁 {name} {moves//1000}k | ✅ {count} passes", flush=True)

if __name__ == "__main__":
    main()
