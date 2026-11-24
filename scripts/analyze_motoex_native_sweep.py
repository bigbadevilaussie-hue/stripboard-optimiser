#!/usr/bin/env python3
"""Read an existing native sweep and archive top near-misses (NOT solved)."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import shutil
import statistics
import sys


def load(root):
    checkpoint = root / "results.jsonl"
    if checkpoint.is_file():
        records = [json.loads(line) for line in checkpoint.read_text(encoding="utf8").splitlines() if line.strip()]
    else:
        records = json.loads((root / "results.json").read_text(encoding="utf8"))["results"]
    if len({r["seed"] for r in records}) != len(records):
        raise ValueError("duplicate seeds in checkpoint")
    return sorted(records, key=lambda r: r["seed"])


def eligible(r):
    return (not r.get("strictPass") and not r.get("unsolvedReason")
            and bool(r.get("savedJson")) and r.get("rows") == 24 and r.get("cols") == 56
            and r.get("quality") == 0 and r.get("conflicts") == 0
            and r.get("incomplete") == 0 and r.get("geometry") == 0
            and r.get("wires", 0) > 0
            and isinstance(r.get("nonvertical"), int)
            and isinstance(r.get("crossings"), int))


def rank(r):
    # Prefer electrical and geometric validity, then fewest remaining
    # strict violations. KNIVES and STACKING were explicitly permitted.
    return (r["nonvertical"] + r["crossings"], r["nonvertical"],
            r["crossings"], r["wires"], r.get("cuts", 10**9),
            r.get("wireLength") or float("inf"), r["seed"])


def stats(data):
    numbers = [float(n) for n in data if isinstance(n, (int, float))]
    return {"n": len(numbers),
            "mean": round(statistics.mean(numbers), 2) if numbers else None,
            "median": round(statistics.median(numbers), 2) if numbers else None,
            "min": round(min(numbers), 2) if numbers else None,
            "max": round(max(numbers), 2) if numbers else None}


def inspect(root, top=5):
    records = load(root)
    bad = [r for r in records if not r.get("strictPass")]
    routed = [r for r in records if not r.get("unsolvedReason")]
    complete = [r for r in routed if r.get("conflicts") == 0 and r.get("incomplete") == 0]
    near = sorted((r for r in records if eligible(r)), key=rank)
    failure_counts = Counter(code.split("_")[0] for r in bad for code in r.get("strictFailures", []))
    polish = [r.get("diagnostics", {}).get("wirePolish") for r in records]
    polish = [p for p in polish if isinstance(p, dict)]
    summary = {
        "attempts": len(records),
        "strictSolved": len(records) - len(bad),
        "noFeasiblePlacement": sum(bool(r.get("unsolvedReason")) for r in records),
        "electricallyCompleteRouted": len(complete),
        "completeAndNonverticalZero": sum(r.get("nonvertical") == 0 for r in complete),
        "completeAndCrossingsZero": sum(r.get("crossings") == 0 for r in complete),
        "completeAndBothZero": sum(r.get("nonvertical") == 0 and r.get("crossings") == 0 for r in complete),
        "nearMissPool": len(near),
        "failureHistogram": dict(failure_counts.most_common()),
        "timing": {k: stats([r.get("time", {}).get(k) for r in records])
                   for k in ("solveMs", "totalMs", "cpuMs", "rssMb")},
        "elapsedWallMs": stats([r.get("elapsedWallMs") for r in records]),
        "polish": {"recorded": len(polish),
                   "tried": sum(int(p.get("tried", 0)) for p in polish),
                   "accepted": sum(int(p.get("accepted", 0)) for p in polish),
                   "drillsRecovered": sum(int(p.get("drillsRecovered", 0)) for p in polish)},
    }
    output = root / "analysis"
    copy_dir = output / "near_misses"
    copy_dir.mkdir(parents=True, exist_ok=True)
    chosen = []
    for i, r in enumerate(near[:top], 1):
        source = root / r["savedJson"]
        if not source.is_file():
            raise FileNotFoundError("missing saved board: " + str(source))
        target = copy_dir / "rank_{:02d}_seed_{:04d}_W{}_C{}.json".format(
            i, r["seed"], r["wires"], r["cuts"])
        shutil.copy2(source, target)
        chosen.append({
            "rank": i, "seed": r["seed"], "wires": r["wires"], "cuts": r["cuts"],
            "nonvertical": r["nonvertical"], "crossings": r["crossings"],
            "incomplete": r["incomplete"], "knife": r.get("knife"),
            "stacked": r.get("stacked"), "strictFailures": r.get("strictFailures", []),
            "elapsedWallMs": r.get("elapsedWallMs"), "time": r.get("time", {}),
            "savedJson": str(target.relative_to(root)),
            "originalJson": r["savedJson"],
            "wireViolations": r.get("diagnostics", {}).get("wireViolations", []),
            "issues": r.get("diagnostics", {}).get("issues", []),
        })
    (output / "near_miss_summary.json").write_text(
        json.dumps({"summary": summary, "topNearMissesNotSolved": chosen}, indent=2) + "\n", encoding="utf8")
    with (output / "near_misses.csv").open("w", newline="", encoding="utf8") as fh:
        fields = ["rank", "seed", "wires", "cuts", "incomplete", "nonvertical",
                  "crossings", "stacked", "knife", "elapsedWallMs", "savedJson"]
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for r in chosen:
            writer.writerow({key: r.get(key) for key in fields})
    lines = [
        "# Strictly invalid near-misses, NOT solved boards", "",
        "This sweep permitted between-hole knife cuts and stacked wires.",
        "Electrical completeness, physical geometry, vertical wires and",
        "component crossings remained strict checks.", "",
        "Completed {} / strict solved {} / electrically complete routed {} / no feasible placement {}.".format(
            summary["attempts"], summary["strictSolved"], summary["electricallyCompleteRouted"],
            summary["noFeasiblePlacement"]),
        "", "## Five closest NOT-SOLVED layouts", "",
        "| Rank | Seed | Wires | Cuts | Opens | Nonvertical | Crossings | Stacks | Knives |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in chosen:
        lines.append("| {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            r["rank"], r["seed"], r["wires"], r["cuts"], r["incomplete"],
            r["nonvertical"], r["crossings"], r["stacked"], r["knife"]))
    for r in chosen:
        lines.extend(["", "## Seed {} (NOT SOLVED)".format(r["seed"]),
                      "Saved copy: " + r["savedJson"],
                      "Strict failures: " + ", ".join(r["strictFailures"])])
        for w in r["wireViolations"]:
            lines.append("- Wire {} {} -> {} | {} | crosses {} | stacks with {}".format(
                w.get("wire"), w.get("from"), w.get("to"),
                ",".join(w.get("violations") or []),
                ",".join(w.get("crossingComponents") or []),
                ",".join(str(x) for x in w.get("stackedWith") or [])))
        for issue in r["issues"]:
            lines.append("- Solver issue: " + str(issue))
    lines.extend(["", "## Timing, memory, and move statistics", "",
                  json.dumps({"timing": summary["timing"], "wall": summary["elapsedWallMs"],
                              "polish": summary["polish"]}, indent=2),
                  "", "## Strict failure histogram", ""])
    lines.extend("- {}: {}".format(k, v) for k, v in summary["failureHistogram"].items())
    (output / "near_miss_report.md").write_text("\n".join(lines) + "\n", encoding="utf8")
    return summary, chosen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="existing sweep root")
    parser.add_argument("--top", type=int, default=5)
    args = parser.parse_args()
    if args.top < 1:
        parser.error("--top must be positive")
    root = args.out.expanduser().resolve()
    try:
        summary, chosen = inspect(root, args.top)
    except (OSError, KeyError, ValueError, TypeError) as error:
        print("❌ SWEEP ANALYSIS ERROR: " + str(error), file=sys.stderr)
        return 2
    print("🏁 {} runs | ✅ {} strict solved | 🔌 {} electrically complete | 🛑 {} no-fit".format(
        summary["attempts"], summary["strictSolved"],
        summary["electricallyCompleteRouted"], summary["noFeasiblePlacement"]))
    for r in chosen:
        print("🔬 NEAR MISS (NOT SOLVED) #{} seed {} | {}W/{}C | NV={} X={} | {}".format(
            r["rank"], r["seed"], r["wires"], r["cuts"],
            r["nonvertical"], r["crossings"], r["savedJson"]))
    print("💾 " + str(root / "analysis/near_miss_report.md"))
    return 0

if __name__ == "__main__":
    sys.exit(main())
