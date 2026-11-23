#!/usr/bin/env python3
"""Read-only, solver-independent post-run geometry audit for the 80-run matrix.

Reads saved project JSON and comparison.csv; imports no solver/helper code.
Independent stack = a wire overlaps an earlier collinear wire by positive length.
Does NOT independently verify net connectivity or component footprint clearances.
"""
import argparse
import ast
import csv
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path


def as_bool(value):
    return str(value).lower() in ("true", "1", "yes")


def no_issues(value):
    if not value or value in ("[]", "None", "null"):
        return True
    try:
        parsed = json.loads(value)
    except (ValueError, TypeError):
        return False
    return not parsed


def nonzero(value):
    try:
        return float(value or 0) != 0
    except (ValueError, TypeError):
        return True


def cross(ax, ay, bx, by):
    return ax * by - ay * bx


def stacked_count(wires):
    """Count each wire overlapping an earlier wire on its geometric line.

    A shared endpoint alone is NOT stacking. Positive-length overlap is.
    The order agrees with the harness' 'joining an existing wire' definition,
    but the algorithm here is independent of TypeScript helper imports.
    """
    count = 0
    prior = []
    for wire in wires:
        a = wire["from"]
        b = wire["to"]
        dx, dy = b["col"] - a["col"], b["row"] - a["row"]
        overlapping = False
        if dx or dy:
            for other in prior:
                c, d = other["from"], other["to"]
                ex, ey = d["col"] - c["col"], d["row"] - c["row"]
                if cross(dx, dy, ex, ey) or cross(dx, dy, c["col"] - a["col"], c["row"] - a["row"]):
                    continue
                # Project both segments onto the first one's direction;
                # positive overlap, not a single shared endpoint.
                def dot(p):
                    return (p["col"] - a["col"]) * dx + (p["row"] - a["row"]) * dy
                left = max(min(dot(a), dot(b)), min(dot(c), dot(d)))
                right = min(max(dot(a), dot(b)), max(dot(c), dot(d)))
                if right > left:
                    overlapping = True
                    break
        if overlapping:
            count += 1
        prior.append(wire)
    return count


def independently_count(saved):
    board = saved["board"]
    wires = board.get("wires", [])
    cuts = board.get("cuts", [])
    return {
        "diagonals_actual": sum(w["from"]["col"] != w["to"]["col"] for w in wires),
        "knife": sum(c.get("kind") != "hole" for c in cuts),
        "stacked": stacked_count(wires),
        "wires": len(wires),
        "cuts": len(cuts),
        "board_24x56": (board.get("rows") == 24 and board.get("cols") == 56
                         and board.get("lockedRows") is True and board.get("lockedCols") is True),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, default=Path("/tmp/stripboard_drill_stack_80"))
    args = parser.parse_args()
    root = args.dir.expanduser().resolve()
    source = root / "comparison.csv"
    if not source.is_file():
        raise SystemExit("❌ Missing " + str(source))
    with source.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise SystemExit("❌ No rows in CSV")

    mismatch = Counter()
    checks = Counter()
    failures = Counter()
    by_config = defaultdict(Counter)
    raw = []
    for row in rows:
        project, config = row["project"], row["configuration"]
        seed = int(row["seed"])
        group = (project, config)
        path = root / project / config / "seed_{:04d}.json".format(seed)
        if not path.is_file():
            failures["missing_file"] += 1
            print("⚠️ MISSING {} / {} / #{}".format(project, config, seed))
            continue
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
            counts = independently_count(saved)
        except (ValueError, TypeError, KeyError) as exc:
            failures["parse_error"] += 1
            print("⚠️ PARSE {} / {} / #{}: {}".format(project, config, seed, exc))
            continue
        checks["loaded"] += 1
        group_stats = by_config[group]
        group_stats["n"] += 1
        for field in ("diagonals_actual", "knife", "stacked", "wires", "cuts"):
            try:
                reported = int(float(row[field]))
            except (TypeError, ValueError, KeyError):
                failures["missing_" + field] += 1
                continue
            if reported != counts[field]:
                mismatch[field] += 1
                print("🔎 MISMATCH {} / {} / #{}: {} CSV={} JSON={}".format(
                    project, config, seed, field, reported, counts[field]))
        if counts["board_24x56"] != as_bool(row.get("board_24x56")):
            mismatch["board_24x56"] += 1
            print("🔎 BOARD MISMATCH {} / {} / #{}".format(project, config, seed))

        criteria = {
            "Q0": not nonzero(row.get("quality")),
            "geo0": not nonzero(row.get("geo")),
            "diag0": counts["diagonals_actual"] == 0,
            "offAxis0": not nonzero(row.get("offAxis")),
            "electrical0": not nonzero(row.get("conflicts")) and not nonzero(row.get("incomplete")),
            "issues0": no_issues(row.get("issues")),
            "board24x56": counts["board_24x56"],
            "F1_kept": as_bool(row.get("f1_kept")),
            "knife0": counts["knife"] == 0,
            "stack0": counts["stacked"] == 0,
        }
        for name, passed in criteria.items():
            if passed:
                group_stats[name] += 1
        for a, b in (("Q0", "diag0"), ("Q0", "knife0"), ("Q0", "stack0"),
                     ("diag0", "stack0"), ("Q0", "geo0"), ("diag0", "offAxis0")):
            if criteria[a] and criteria[b]:
                group_stats[a + "_AND_" + b] += 1
        drilled = as_bool(row.get("drilled_required"))
        stack_allowed = as_bool(row.get("stack_allowed"))
        reasons = [name for name in ("Q0", "geo0", "diag0", "offAxis0", "electrical0", "issues0", "board24x56", "F1_kept") if not criteria[name]]
        if drilled and not criteria["knife0"]:
            reasons.append("knife0")
        if not stack_allowed and not criteria["stack0"]:
            reasons.append("stack0")
        predicted = not reasons
        if predicted != as_bool(row.get("clean")):
            mismatch["clean"] += 1
            print("🔎 CLEAN MISMATCH {} / {} / #{}".format(project, config, seed))
        if predicted:
            group_stats["clean"] += 1
        raw.append({
            "project": project, "configuration": config, "seed": seed,
            **counts,
            "fail_reasons": ",".join(reasons),
            "clean_recomputed": predicted,
        })

    print("\n🏆 INDEPENDENT GEOMETRY AUDIT — {} layouts loaded / {} CSV rows".format(checks["loaded"], len(rows)))
    print("🔎 DIFFERENCES: " + (", ".join("{}={}".format(k, v) for k, v in sorted(mismatch.items())) if mismatch else "NONE"))
    if failures:
        print("⚠️ MISSING/UNREADABLE: " + ", ".join("{}={}".format(k, v) for k, v in failures.items()))
    print("\nCRITERION PASS COUNTS (each denominator = loaded files in that group)")
    print("{:<9} {:<22} {:>3} {:>4} {:>4} {:>5} {:>5} {:>5} {:>5} {:>5} {:>5} {:>6}".format(
        "PROJECT", "CONFIG", "N", "Q0", "GEO", "DIAG", "OFFAX", "ELEC", "KNIFE", "STACK", "F1", "CLEAN"
    ))
    for (project, config), stats in sorted(by_config.items()):
        print("{:<9} {:<22} {:>3} {:>4} {:>4} {:>5} {:>5} {:>5} {:>5} {:>5} {:>6} {:>6}".format(
            project, config, stats["n"], stats["Q0"], stats["geo0"], stats["diag0"],
            stats["offAxis0"], stats["electrical0"],
            stats["knife0"] if "DRILL_ON" in config else "-",
            stats["stack0"] if "STACK_OFF" in config else "-",
            stats["F1_kept"], stats["clean"]
        ))
    print("\n🔗 JOINT CRITERION PASS COUNTS (recomputed geometry + original CSV Q0/geo/offAxis)")
    print("{:<9} {:<22} {:>7} {:>8} {:>8} {:>10} {:>8}".format(
        "PROJECT", "CONFIG", "Q0+DIAG", "Q0+KNIFE", "Q0+STACK", "DIAG+STACK", "Q0+GEO"))
    for (project, config), stats in sorted(by_config.items()):
        print("{:<9} {:<22} {:>7} {:>8} {:>8} {:>10} {:>8}".format(
            project, config, stats["Q0_AND_diag0"],
            stats["Q0_AND_knife0"], stats["Q0_AND_stack0"],
            stats["diag0_AND_stack0"], stats["Q0_AND_geo0"]))
    print("\n⏱ CLI PHASE TIMINGS (mean ms; from original benchmark CSV, not independent)")
    print("{:<9} {:<22} {:>7} {:>7} {:>7} {:>7} {:>7} {:>9}".format(
        "PROJECT", "CONFIG", "SOLVE", "ANNEAL", "ROUTE", "REPAIR", "EXTRACT", "ANNEAL %"))
    for (project, config), stats in sorted(by_config.items()):
        group = [r for r in rows if r["project"] == project and r["configuration"] == config]
        def avg(key):
            vals = []
            for r in group:
                try:
                    vals.append(float(r[key]))
                except (KeyError, TypeError, ValueError):
                    pass
            return statistics.mean(vals) if vals else 0.0
        solve = avg("solveMs")
        print("{:<9} {:<22} {:>7.0f} {:>7.0f} {:>7.0f} {:>7.0f} {:>7.0f} {:>8.1f}%".format(
            project, config, solve, avg("annealMs"), avg("routeMs"),
            avg("repairMs"), avg("extractMs"), 100 * avg("annealMs") / solve if solve else 0))
    try:
        route_outlier = max((r for r in rows if r.get("routeMs") not in (None, "")),
                            key=lambda r: float(r["routeMs"]))
        print("🧭 Slowest route: {} / {} / seed #{} · {:.0f}ms".format(
            route_outlier["project"], route_outlier["configuration"],
            route_outlier["seed"], float(route_outlier["routeMs"])))
    except (ValueError, KeyError, TypeError):
        pass
    print("\n🔒 NOTE: Electrical/geometry/F1 entries above use existing CSV claims, NOT independent validation.")
    print("🔪 Knife from cut.kind; 🧵 stack from positive-length collinear wire overlaps; ↘ diagonal from endpoint columns.")
    print("Cut-kind audit is a label check, not a physical cut classification independent of stored labels.")

    output = root / "independent_geometry_audit.csv"
    fields = ["project", "configuration", "seed", "diagonals_actual", "knife",
              "stacked", "wires", "cuts", "board_24x56", "fail_reasons", "clean_recomputed"]
    with output.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(raw)
    print("📁 Independent audit: " + str(output))


if __name__ == "__main__":
    main()
