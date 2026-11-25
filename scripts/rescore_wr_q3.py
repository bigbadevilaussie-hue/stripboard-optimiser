#!/usr/bin/env python3
"""Read-only rescoring of the archived WR Audio/Moto boards using live Q3 code.

No optimiser, native binaries or GUI dependencies. Optional CSV is new output;
the saved boards, campaigns and historical reports are never modified.
"""
import argparse
import csv
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from gui.quality import construction_metrics, QUALITY_VERSION

EXPECTED = {
    "Audio": {5: 113, 10: 170, 15: 201, 20: 215, 25: 207},
    "Moto": {5: 3, 10: 15, 15: 29, 20: 37, 25: 63},
}


def collect(repo):
    rows = []
    for circuit, budgets in EXPECTED.items():
        for budget, count in budgets.items():
            directory = repo / "analysis" / f"WR_{circuit}" / f"{budget}k"
            paths = sorted(directory.glob("seed_*.json"))
            if len(paths) != count:
                raise ValueError(f"{directory}: expected {count} boards, got {len(paths)}")
            for path in paths:
                saved = json.loads(path.read_text(encoding="utf-8"))
                old = construction_metrics(saved, quality_version="Q2")
                new = construction_metrics(saved, quality_version="Q3")
                rows.append({"circuit": circuit, "budget": budget,
                             "seed": int(path.stem.split("_")[-1]),
                             "w": new["w"], "cut": new["cut"], "s": new["s"],
                             "wire_length_mm": new["wire_length_mm"],
                             "q2": old["q"], "q3": new["q"],
                             "path": str(path.relative_to(repo))})
    return rows


def winner(rows, score):
    return min(rows, key=lambda r: (-r[score], r["w"], r["cut"], r["seed"], r["budget"]))


def report(label, rows):
    a, b = winner(rows, "q2"), winner(rows, "q3")
    values = [r["q3"] for r in rows]
    changed = (a["budget"], a["seed"]) != (b["budget"], b["seed"])
    return (f"{label:12} {len(rows):5}  {a['budget']:2}k/{a['seed']:04} {a['q2']:6.2f}  "
            f"{b['budget']:2}k/{b['seed']:04} {b['q3']:6.2f}  "
            f"{min(values):6.2f} {statistics.median(values):6.2f}  "
            f"{sum(v >= 85 for v in values):5} {sum(v >= 90 for v in values):5} "
            f"{sum(v >= 95 for v in values):5}   {'YES' if changed else 'no'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--csv", type=Path, help="Optional new CSV output file; refuses overwrite")
    args = parser.parse_args()
    if QUALITY_VERSION != "Q3":
        raise RuntimeError("This comparison is pinned to the Q3 release")
    rows = collect(args.repo.resolve())
    print("Set          Count   Q2 champion         Q3 champion         Q3 min median   >=85  >=90  >=95  Changed")
    for circuit, budgets in EXPECTED.items():
        for budget in budgets:
            report_rows = [r for r in rows if r["circuit"] == circuit and r["budget"] == budget]
            print(report(f"{circuit} {budget}k", report_rows))
        print(report(f"{circuit} ALL", [r for r in rows if r["circuit"] == circuit]))
    print(f"Rescored {len(rows):,} saved boards. No optimisation or electrical re-audit performed.")
    if args.csv:
        out = args.csv.expanduser().resolve()
        archive = args.repo.resolve() / "analysis"
        if out.is_relative_to(archive):
            raise ValueError("Write CSV outside the historical analysis directory")
        with out.open("x", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        print(f"Saved {out}")


if __name__ == "__main__":
    main()
