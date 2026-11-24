#!/usr/bin/env python3
"""Track 10k drill ON/OFF pass-seed repeats against the frozen 25k baseline.

Read-only. Run while the main sweep continues, optionally --watch.
"""
from __future__ import annotations
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
import time

DEFAULT_OUT = (Path.home() / "Documents" / "Stripboard-Experiment-Archive"
               / "audioex_flipflop_10k_2000")

def load_jsonl(path: Path):
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf8") as f:
        for line in f:
            try:
                row = json.loads(line)
                if isinstance(row, dict):
                    rows.append(row)
            except json.JSONDecodeError:
                # The sweep may be appending a line during this read.
                continue
    return rows

def inspect(out: Path):
    baseline_path = out / "previous_25k_passing_seeds.json"
    if not baseline_path.is_file():
        raise FileNotFoundError(f"Missing frozen 25k baseline: {baseline_path}")
    baseline = json.loads(baseline_path.read_text(encoding="utf8"))
    old_seeds = set(map(int, baseline["seeds"]))
    rows = load_jsonl(out / "results.jsonl")
    strict = [r for r in rows if r.get("strictPass") is True]
    by_seed = defaultdict(dict)
    for r in strict:
        mode = "ON" if r.get("drillOn") else "OFF"
        by_seed[int(r["seed"])][mode] = r
    repeated = sorted(set(by_seed) & old_seeds)
    dual = sorted(seed for seed, modes in by_seed.items() if "ON" in modes and "OFF" in modes)
    on_count = sum("ON" in m for m in by_seed.values())
    off_count = sum("OFF" in m for m in by_seed.values())
    print(f"🔁 25k baseline: {len(old_seeds)} unique passing seed IDs | "
          f"10k trials: {len(rows)}/4000", flush=True)
    print(f"✅ 10k strict passes: {len(strict)} | 🔩 ON {on_count} | "
          f"🔪 OFF {off_count} | 25k↔10k repeat seeds {len(repeated)} | "
          f"ON↔OFF dual passes {len(dual)}", flush=True)
    for seed in repeated:
        modes = by_seed[seed]
        details = " | ".join(
            f"{mode} {modes[mode].get('wires','?')}W/"
            f"{modes[mode].get('cuts','?')}C "
            f"Q={modes[mode].get('quality100','?')}"
            for mode in ("ON", "OFF") if mode in modes)
        print(f"🎯 REPEAT seed {seed:04d} | 25k PASS | 10k {details}", flush=True)
    for seed in dual:
        modes = by_seed[seed]
        print(f"🔃 BOTH MODES seed {seed:04d} | "
              f"ON Q={modes['ON'].get('quality100','?')} | "
              f"OFF Q={modes['OFF'].get('quality100','?')}", flush=True)
    if not repeated:
        print("🎯 No 25k↔10k repeated passing seeds yet", flush=True)
    if not dual:
        print("🔃 No same-seed ON↔OFF dual pass yet", flush=True)
    return len(rows), len(repeated), len(dual)

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--watch", action="store_true",
                    help="refresh while sweep runs; Ctrl+C to stop")
    ap.add_argument("--interval", type=float, default=15.0)
    args = ap.parse_args()
    if args.interval < 1:
        ap.error("--interval must be >= 1 second")
    last = None
    try:
        while True:
            now = inspect(args.out.expanduser())
            if not args.watch:
                break
            if now != last:
                print("─" * 55, flush=True)
            last = now
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n🛑 Tracker stopped; solver unaffected.", flush=True)

if __name__ == "__main__":
    main()
