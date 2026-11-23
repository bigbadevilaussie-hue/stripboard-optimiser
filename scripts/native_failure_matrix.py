#!/usr/bin/env python3
"""v1.61 native CLI failure-matrix analysis, no solver runs and no GUI imports.

Input is the existing v1.60 full80 finish_matrix.csv. "Closest" prioritises
electrical correctness first, then the number of failed validation categories.
Also report the *minimum* failures across either finish, and the intersection
of failures in both, to avoid mistaking a ranking convention for proof.
"""
import argparse
from collections import Counter, defaultdict
import csv
from pathlib import Path

DEFAULT = Path("/tmp/stripboard_drill_stack_80/cli_profile_v160_full80/finish_matrix.csv")
CRITERIA = ("COLUMN_SHIFT", "CROSSINGS", "STACKED", "KNIFE", "GEOMETRY")
ELECTRICAL = frozenset(("QUALITY", "CONFLICTS", "INCOMPLETE"))
REQUIRED = ("project", "configuration", "seed", "selected",
            "repair_failed", "router_failed",
            "repair_verified_compliant", "router_verified_compliant")
REASONS = ("QUALITY", "CONFLICTS", "INCOMPLETE", "GEOMETRY",
           "COLUMN_SHIFT", "CROSSINGS", "ISSUES", "LOCKED_PART",
           "LOCKED_BOARD", "KNIFE", "STACKED")


def as_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in ("true", "1"):
        return True
    if isinstance(value, str) and value.strip().lower() in ("false", "0"):
        return False
    raise ValueError("Expected explicit boolean, got {!r}".format(value))


def reasons(value):
    return frozenset(x.strip() for x in (value or "").split(",") if x.strip())


def classify_row(row):
    """Classify two audited candidates without changing their selection."""
    for key in REQUIRED:
        if key not in row:
            raise ValueError("Missing finish-matrix field: " + key)
    if row.get("error"):
        raise ValueError("Profile has failed case: " + str(row["error"]))
    failures = {name: reasons(row[name + "_failed"]) for name in ("repair", "router")}
    verified = {name: as_bool(row[name + "_verified_compliant"]) for name in ("repair", "router")}
    for name in ("repair", "router"):
        if verified[name] != (len(failures[name]) == 0):
            raise ValueError("Candidate validator/reasons disagree: " + name)
    if row["selected"] not in failures:
        raise ValueError("Unknown finish selected: " + str(row["selected"]))
    # Hard priority: never call an electrically incomplete result preferable
    # just because it has fewer purely geometric faults.
    closest = min(("repair", "router"), key=lambda name: (
        len(failures[name] & ELECTRICAL),
        len(failures[name]),
        0 if name == row["selected"] else 1,
    ))
    common = failures["repair"] & failures["router"]
    clean_any = any(verified.values())
    clean_selected = verified[row["selected"]]
    if "eitherCompliant" in row and row["eitherCompliant"] not in (None, ""):
        if as_bool(row["eitherCompliant"]) != clean_any:
            raise ValueError("Either-compliant flag disagrees with validators")
    if "selectedCompliant" in row and row["selectedCompliant"] not in (None, ""):
        if as_bool(row["selectedCompliant"]) != clean_selected:
            raise ValueError("Selected-compliant flag disagrees with validators")
    return {
        "project": row["project"], "configuration": row["configuration"],
        "seed": int(row["seed"]), "selected": row["selected"], "closest": closest,
        "selectedCompliant": clean_selected, "eitherCompliant": clean_any,
        "repairCompliant": verified["repair"], "routerCompliant": verified["router"],
        "repairFailures": ",".join(sorted(failures["repair"])),
        "routerFailures": ",".join(sorted(failures["router"])),
        "closestFailures": ",".join(sorted(failures[closest])),
        "commonFailures": ",".join(sorted(common)),
        "closestCount": len(failures[closest]),
        "minimumFailures": min(len(failures["repair"]), len(failures["router"])),
        "commonCount": len(common),
        "_closest": failures[closest], "_common": common,
        "_repair": failures["repair"], "_router": failures["router"],
    }


def print_breakdown(records, title="NATIVE CLI FINISH FAILURES"):
    if not records:
        raise ValueError("No finish-matrix cases to analyse")
    print("\n🔬 {} — {} cases".format(title, len(records)), flush=True)
    group = defaultdict(list)
    for rec in records:
        group[(rec["project"], rec["configuration"])].append(rec)
    print("{:<9} {:<22} {:>3} {:>5} {:>6} {:>7} {:>7} {:>7} {:>7}".format(
        "PROJECT", "CONFIG", "N", "CLEAN", "EITHER", "MIN=0", "MIN<=1", "MIN<=2", "BOTH"))
    for (project, config), rows in sorted(group.items()):
        print("{:<9} {:<22} {:>3} {:>5} {:>6} {:>7} {:>7} {:>7} {:>7}".format(
            project, config, len(rows), sum(r["selectedCompliant"] for r in rows),
            sum(r["eitherCompliant"] for r in rows),
            sum(r["minimumFailures"] == 0 for r in rows),
            sum(r["minimumFailures"] <= 1 for r in rows),
            sum(r["minimumFailures"] <= 2 for r in rows),
            sum(r["commonCount"] > 0 for r in rows)))
    print("\nHard-rule failure frequencies; closest = electrical-first, then fewest categories.")
    print("{:<16} {:>10} {:>10} {:>10} {:>11}".format(
        "RULE", "REPAIR", "ROUTER", "CLOSEST", "BOTH"))
    for rule in CRITERIA:
        print("{:<16} {:>10} {:>10} {:>10} {:>11}".format(
            rule,
            sum(rule in r["_repair"] for r in records),
            sum(rule in r["_router"] for r in records),
            sum(rule in r["_closest"] for r in records),
            sum(rule in r["_common"] for r in records)))
    print("\nElectrical gate (Q/conflicts/incomplete) failures: repair {}, router {}, closest {}.".format(
        sum(bool(r["_repair"] & ELECTRICAL) for r in records),
        sum(bool(r["_router"] & ELECTRICAL) for r in records),
        sum(bool(r["_closest"] & ELECTRICAL) for r in records)))
    print("🏁 Selected valid: {}/{}; either finish valid: {}/{}; selected lost a valid alternative: {}.".format(
        sum(r["selectedCompliant"] for r in records), len(records),
        sum(r["eitherCompliant"] for r in records), len(records),
        sum(r["eitherCompliant"] and not r["selectedCompliant"] for r in records)))
    print("⚠️ BOTH means both candidates failed that criterion, not proof that no legal placement exists.")
    print("⚠️ Counts use the existing harness validators; column-shift is the historical vertical-only rule.")


def load_matrix(path):
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return [classify_row(r) for r in rows]


def write_breakdown(records, out):
    fields = [k for k in records[0] if not k.startswith("_")]
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: r[k] for k in fields} for r in records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=DEFAULT)
    parser.add_argument("--out", type=Path, help="Default: failure_breakdown.csv next to input")
    args = parser.parse_args()
    path = args.matrix.expanduser().resolve()
    if not path.is_file():
        parser.error("Missing full-matrix CSV: {}".format(path))
    records = load_matrix(path)
    print_breakdown(records, "v1.61 NATIVE FINISH FAILURE MATRIX")
    out = (args.out or path.with_name("failure_breakdown.csv")).expanduser().resolve()
    if out == path:
        parser.error("output cannot overwrite the source finish matrix")
    out.parent.mkdir(parents=True, exist_ok=True)
    write_breakdown(records, out)
    print("📁 Detailed per-run failure breakdown:", out)


if __name__ == "__main__":
    main()
