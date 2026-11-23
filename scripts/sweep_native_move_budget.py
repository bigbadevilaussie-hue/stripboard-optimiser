#!/usr/bin/env python3
"""v1.61 native CLI move-budget sweep — same projects/seeds/flags, zero solver changes.

Default: MOTOMIX x four drill/stack modes x three fixed seeds x
[20k,100k,500k] = 36 independent native processes.
Run as: python3 scripts/sweep_native_move_budget.py --jobs 4

The first 20k stage MUST reproduce the archived sig and clean fields, or the
script stops before the 100k/500k stages. It snapshots the baseline CSV with
SHA256 and writes all solved layouts under its OWN directory, never into the
historical 80-run benchmark. Progress is checkpointed per case and --resume
can reuse completed cases after interruptions. Timing under concurrency is
not a before/after performance measurement.
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

import native_failure_matrix as fm
import profile_native_cli as prof

VERSION = "v1.61-cli-budget-sweep"
DEFAULT_PROJECT = "MOTOMIX"
DEFAULT_SEEDS = (897, 1036, 1552)
DEFAULT_BUDGETS = (20000, 100000, 500000)
DEFAULT_OUT = "cli_budget_sweep_v161"
SUM_FIELDS = [
    "budget", "project", "configuration", "runs", "selected_clean",
    "either_clean", "repair_clean", "router_clean", "minimal_zero",
    "minimal_le1", "minimal_le2", "mean_min_failures", "mean_closest_failures",
    "mean_anneal_ms_contended", "mean_route_ms_contended",
]


def parse_positive_ints(raw, option):
    try:
        vals = tuple(int(t.strip()) for t in raw.split(","))
    except ValueError as exc:
        raise ValueError("{}: expected comma-separated integers".format(option)) from exc
    if not vals or any(v <= 0 for v in vals) or len(vals) != len(set(vals)):
        raise ValueError("{}: values must be positive and distinct".format(option))
    return vals


def safe_write(path, data):
    """Save a valid JSON record atomically, even on Ctrl-C or process failure."""
    tmp = path.with_name(path.name + ".partial")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def flatten(rec, budget):
    trace = (rec.get("finishTrace") or [{}])[0]
    selected = trace.get("selected")
    row = {
        "version": VERSION, "budget": budget,
        "project": rec["project"], "configuration": rec["configuration"],
        "seed": rec["seed"], "error": rec.get("error", ""),
        "selected": selected, "baselineSig": rec.get("baselineSig"),
        "newSig": rec.get("result", {}).get("sig"),
        "sigMatch20k": rec.get("signatureMatch") if budget == 20000 else "",
        "strictMatch20k": rec.get("strictMatch") if budget == 20000 else "",
        "strictValid": rec.get("result", {}).get("strictValid"),
        "quality": rec.get("result", {}).get("quality"),
        "wires": rec.get("result", {}).get("wires"),
        "cuts": rec.get("result", {}).get("cuts"),
        "knife": rec.get("result", {}).get("knife"),
        "stacked": rec.get("result", {}).get("stacked"),
        "columnShift": rec.get("result", {}).get("diagonalsActual"),
        "slanted": rec.get("result", {}).get("slantedWires"),
        "horizontal": rec.get("result", {}).get("horizontalWires"),
        "geo": rec.get("result", {}).get("geo"),
        "annealMs": rec.get("timing", {}).get("annealMs"),
        "routeMs": rec.get("timing", {}).get("routeMs"),
        "solveMs": rec.get("timing", {}).get("solveMs"),
        "eitherCompliant": trace.get("anyCompliant"),
        "selectedCompliant": trace.get("selectedCompliant"),
    }
    for name in ("repair", "router"):
        c = trace.get(name) or {}
        verified = c.get("verification") or {}
        terms = c.get("scoreTerms") or {}
        row[name + "_failed"] = ",".join(verified.get("failReasons", [])) if c else "UNAVAILABLE"
        row[name + "_verified_compliant"] = verified.get("compliant", False)
        row[name + "_eligible"] = c.get("eligible")
        for field in ("quality", "columnShiftWires", "slantedWires",
                      "horizontalWires", "stacked", "knife", "avoidableKnife",
                      "crossings", "score"):
            row[name + "_" + field] = c.get(field)
        for field in ("price", "qualityCost", "messCost", "mess"):
            row[name + "_score_" + field] = terms.get(field)
    for stage, elapsed in trace.get("routePhases", {}).items():
        row["phase_" + stage + "_ms"] = elapsed
    m = rec.get("result", {}).get("moveSummary") or {}
    for key in ("attempted", "rejected", "accepted", "sameBoard", "mutateFailed", "decodeFailed"):
        row["moves_" + key] = m.get(key)
        row["pct_" + key] = (m.get("percent") or {}).get(key)
    return row


def save_csv(rows, out, fields=None):
    if not rows:
        return
    names = fields or list(dict.fromkeys(k for row in rows for k in row))
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=names)
        writer.writeheader()
        writer.writerows(rows)


def summarize_budget(rows, budget):
    by_group = defaultdict(list)
    for r in rows:
        by_group[(r["project"], r["configuration"])].append(r)
    summaries = []
    for (project, config), group in sorted(by_group.items()):
        closest = [fm.classify_row(r) for r in group]
        def mean_number(field):
            vals = [float(r[field]) for r in group if r.get(field) not in (None, "")]
            return round(statistics.mean(vals), 1) if vals else None
        summaries.append({
            "budget": budget, "project": project, "configuration": config,
            "runs": len(group),
            "selected_clean": sum(r["selectedCompliant"] for r in closest),
            "either_clean": sum(r["eitherCompliant"] for r in closest),
            "repair_clean": sum(r["repairCompliant"] for r in closest),
            "router_clean": sum(r["routerCompliant"] for r in closest),
            "minimal_zero": sum(r["minimumFailures"] == 0 for r in closest),
            "minimal_le1": sum(r["minimumFailures"] <= 1 for r in closest),
            "minimal_le2": sum(r["minimumFailures"] <= 2 for r in closest),
            "mean_min_failures": round(statistics.mean(r["minimumFailures"] for r in closest), 2),
            "mean_closest_failures": round(statistics.mean(r["closestCount"] for r in closest), 2),
            "mean_anneal_ms_contended": mean_number("annealMs"),
            "mean_route_ms_contended": mean_number("routeMs"),
        })
    print("\n🏁 {} moves — {} runs".format(budget, len(rows)))
    print("{:<23} {:>6} {:>7} {:>8} {:>7} {:>8}".format(
        "CONFIG", "CLEAN", "EITHER", "MIN<=1", "MIN<=2", "AVG_MIN"))
    for r in summaries:
        print("{:<23} {:>6} {:>7} {:>8} {:>7} {:>8.2f}".format(
            r["configuration"], "{}/{}".format(r["selected_clean"], r["runs"]),
            "{}/{}".format(r["either_clean"], r["runs"]),
            r["minimal_le1"], r["minimal_le2"], r["mean_min_failures"]))
    fm.print_breakdown([fm.classify_row(r) for r in rows], "BUDGET {:,} HARD-RULE COUNTS".format(budget))
    return summaries


def run_stage(selected, bench, out, budget, jobs, resume, baseline_hash):
    stage_dir = out / "moves_{:07d}".format(budget)
    stage_dir.mkdir(parents=True, exist_ok=True)
    records = []
    pending = []
    for row in selected:
        key = "{}_{}_{}".format(row["project"], row["configuration"], row["seed"])
        checkpoint = stage_dir / (key + ".checkpoint.json")
        if resume and checkpoint.is_file():
            rec = json.loads(checkpoint.read_text(encoding="utf-8"))
            if rec.get("_budget") == budget and rec.get("_baselineSha256") == baseline_hash and not rec.get("error") and Path(rec.get("saved", "")).is_file():
                print("♻️  RESUME {} / {} / #{} @ {}".format(row["project"], row["configuration"], row["seed"], budget), flush=True)
                records.append(rec)
                continue
        pending.append((row, checkpoint))
    with ThreadPoolExecutor(max_workers=jobs) as executor:
        futures = {
            executor.submit(prof.run_case, {**row, "moves": str(budget)}, bench, stage_dir): (row, checkpoint)
            for row, checkpoint in pending
        }
        for future in as_completed(futures):
            row, checkpoint = futures[future]
            rec = future.result()
            rec["_budget"] = budget
            rec["_baselineSha256"] = baseline_hash
            records.append(rec)
            print("{} {:7,d} {} {} #{} | strict={} | originalSig={} | route={}ms".format(
                "❌" if rec.get("error") or (budget == 20000 and
                             (rec.get("signatureMatch") is not True or rec.get("strictMatch") is not True))
                else "✅",
                budget, row["project"], row["configuration"], row["seed"],
                rec.get("result", {}).get("strictValid"),
                "MATCH" if rec.get("signatureMatch") else "DIFF",
                rec.get("timing", {}).get("routeMs")), flush=True)
            safe_write(checkpoint, rec)
    idx = {(r["project"], r["configuration"], int(r["seed"])): i for i, r in enumerate(selected)}
    records.sort(key=lambda rec: idx[(rec["project"], rec["configuration"], rec["seed"])])
    safe_write(stage_dir / "results.json", records)
    bad = [r for r in records if r.get("error")]
    if budget == 20000:
        bad.extend(r for r in records if r.get("signatureMatch") is not True or r.get("strictMatch") is not True)
    if bad:
        for rec in bad:
            print("🛑 STAGE FAILED {} / {} / #{}: {}".format(
                rec["project"], rec["configuration"], rec["seed"],
                rec.get("error") or "original 20k signature/strict result changed"))
        raise RuntimeError("Native sweep stopped at {} moves: {} failures; refusing subsequent budgets".format(budget, len(bad)))
    return [flatten(r, budget) for r in records]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bench", type=Path, default=prof.DEFAULT_BENCH)
    parser.add_argument("--out", type=Path, default=None,
                        help="New output root, never the original benchmark root")
    parser.add_argument("--project", default=DEFAULT_PROJECT)
    parser.add_argument("--seeds", default=",".join(str(n) for n in DEFAULT_SEEDS))
    parser.add_argument("--budgets", default=",".join(str(n) for n in DEFAULT_BUDGETS))
    parser.add_argument("--jobs", type=int, default=4,
                        help="Parallel native processes; capped at physical CPU cores")
    parser.add_argument("--resume", action="store_true",
                        help="Reuse completed, saved case checkpoints from the same baseline")
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be at least 1")
    try:
        seeds = parse_positive_ints(args.seeds, "--seeds")
        budgets = tuple(sorted(parse_positive_ints(args.budgets, "--budgets")))
    except ValueError as exc:
        parser.error(str(exc))
    if not budgets or budgets[0] != 20000:
        parser.error("start budgets at 20000, with no smaller value, to gate higher budgets on baseline reproduction")
    bench = args.bench.expanduser().resolve()
    baseline = bench / "comparison.csv"
    if not baseline.is_file():
        parser.error("Missing original 80-run comparison.csv: " + str(baseline))
    out = (args.out or bench / DEFAULT_OUT).expanduser().resolve()
    protected = [bench, bench.parent, prof.ROOT, bench / "MOTO", bench / "MOTOMIX",
                 bench / "cli_profile_v160_full80", bench / "cli_profile_v160_smoke"]
    if out in protected or (out / "comparison.csv").exists() or (out / "projects" / "1.json").exists():
        parser.error("--out must not replace a benchmark, input project or existing full80 profile")
    for src, built in zip(prof.SOURCE_FILES, (prof.BUILT_JS, prof.BUILT_FINISH)):
        if not built.is_file() or built.stat().st_mtime < src.stat().st_mtime:
            parser.error("Build the current TypeScript solver first: cd src/frontend && npx tsc -p tests/solver/tsconfig.json")
    rows = prof.load_cases(baseline, smoke=False)
    selected = [r for r in rows if r["project"] == args.project and int(r["seed"]) in seeds]
    configs = sorted({r["configuration"] for r in selected})
    if len(selected) != len(seeds) * 4 or len(configs) != 4:
        parser.error("Expected four configs for each seed {}; found {} cases / {} configs".format(
            seeds, len(selected), len(configs)))
    cores = prof.physical_cpu_count()
    jobs = min(args.jobs, cores)
    if jobs != args.jobs:
        print("⚠️ Capping {} workers at {} physical cores".format(args.jobs, cores), flush=True)
    baseline_bytes = baseline.read_bytes()
    baseline_sha = hashlib.sha256(baseline_bytes).hexdigest()
    config = {"version": VERSION, "project": args.project, "seeds": seeds,
              "budgets": budgets, "baselineSha256": baseline_sha,
              "native": True, "routingPreference": "wires",
              "drillAndStack": "taken from baseline per config"}
    out.mkdir(parents=True, exist_ok=True)
    config_path = out / "sweep_config.json"
    if config_path.is_file() and json.loads(config_path.read_text(encoding="utf-8")) != config:
        parser.error("Existing output has different configuration or baseline; choose another --out")
    safe_write(config_path, config)
    snapshot = out / "baseline_snapshot.csv"
    if snapshot.is_file() and snapshot.read_bytes() != baseline_bytes:
        parser.error("Archived baseline snapshot has changed, refusing to continue")
    if not snapshot.is_file():
        shutil.copy2(baseline, snapshot)
    print("🔒 Protected original baseline SHA256={}".format(baseline_sha))
    print("🧪 {}: {} × {} configs × {} seeds = {} independent CLI runs; jobs={}".format(
        VERSION, len(budgets), len(configs), len(seeds), len(budgets) * len(selected), jobs))
    print("📁 Sweep output:", out, flush=True)
    all_rows = []
    summaries = []
    for budget in budgets:
        print("\n⚙️  Starting {:,}-move stage".format(budget), flush=True)
        current = run_stage(selected, bench, out, budget, jobs, args.resume, baseline_sha)
        all_rows.extend(current)
        summaries.extend(summarize_budget(current, budget))
        save_csv(all_rows, out / "budget_results.csv")
        save_csv(summaries, out / "budget_summary.csv", SUM_FIELDS)
        fm.write_breakdown([fm.classify_row(r) for r in all_rows],
                           out / "failure_breakdown.csv")
    print("\n✅ Move-budget sweep complete. No native solver weights or selection logic changed.")
    print("📁 Cases:", out / "budget_results.csv")
    print("📁 Summary:", out / "budget_summary.csv")
    print("📁 Failure reasons:", out / "failure_breakdown.csv")
    print("⚠️ More moves change the temperature/ramp schedule and can alter outcomes non-monotonically.")
    if jobs > 1:
        print("⚠️ Parallel timings are contended; repeat with --jobs 1 for performance comparisons.")


if __name__ == "__main__":
    main()
