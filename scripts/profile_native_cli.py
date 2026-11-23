#!/usr/bin/env python3
"""Read-only baseline comparison: profile BOTH finishes across all 80 native runs.

Run after building the TypeScript test solver:
    cd src/frontend && npx tsc -p tests/solver/tsconfig.json && cd ../..
    python3 scripts/profile_native_cli.py --jobs 4
    python3 scripts/profile_native_cli.py --smoke --jobs 1 --verbose

By default reads the original 80-run CSV and 24x56 input snapshots. Writes
ONLY to a distinct cli_profile_v160_full80 folder, never overwrites any
original saved board. --jobs 1 is for timings; parallel timings are contended.
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
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "src" / "frontend"
HARNESS = FRONTEND / "tests" / "solver" / "v5Solve.js"
SOURCE_FILES = [
    FRONTEND / "components" / "stripboard" / "autoLayout5.ts",
    FRONTEND / "components" / "stripboard" / "layout2" / "finish.ts",
]
BUILT_JS = FRONTEND / "tests" / "solver" / "out" / "components" / "stripboard" / "autoLayout5.js"
BUILT_FINISH = FRONTEND / "tests" / "solver" / "out" / "components" / "stripboard" / "layout2" / "finish.js"
DEFAULT_BENCH = Path("/tmp/stripboard_drill_stack_80")
SMOKE = {("MOTO", "DRILL_ON_STACK_OFF", 639),
         ("MOTOMIX", "DRILL_OFF_STACK_ON", 897),
         ("MOTOMIX", "DRILL_ON_STACK_OFF", 1036),
         ("MOTOMIX", "DRILL_OFF_STACK_OFF", 1552)}
PROFILE_VERSION = "v1.60-cli-audit"


def parse_json_lines(text, prefix):
    result = []
    for line in text.splitlines():
        if line.startswith(prefix):
            try:
                result.append(json.loads(line if prefix == "{" else line[len(prefix):]))
            except json.JSONDecodeError:
                pass
    return result


def load_cases(baseline, smoke):
    with baseline.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    required = {"project", "configuration", "seed", "moves", "sig",
                "drilled_required", "stack_allowed", "clean"}
    if not rows or not required.issubset(rows[0]):
        raise SystemExit("❌ Missing benchmark columns: " + ", ".join(sorted(required - set(rows[0]) if rows else required)))
    if len(rows) != 80:
        raise SystemExit("❌ Expected all 80 baseline CSV rows, found {}".format(len(rows)))
    cases = []
    seen = set()
    for r in rows:
        key = (r["project"], r["configuration"], int(r["seed"]))
        if key in seen:
            raise SystemExit("❌ Duplicate baseline case " + repr(key))
        seen.add(key)
        if not smoke or key in SMOKE:
            cases.append(r)
    if smoke and len(cases) != len(SMOKE):
        raise SystemExit("❌ One or more smoke test seeds are missing from the CSV")
    return cases


def run_case(row, bench, out):
    project, config, seed = row["project"], row["configuration"], int(row["seed"])
    drilled = str(row["drilled_required"]).lower() in ("1", "true")
    stack_allowed = str(row["stack_allowed"]).lower() in ("1", "true")
    moves = int(row["moves"])
    base = "{}_{}_{}".format(project, config, seed)
    project_dir = bench / project
    saved = out / (base + ".json")
    logpath = out / (base + ".stderr.log")
    inp = project_dir / "projects" / "1.json"
    if not inp.is_file():
        return {"project": project, "configuration": config, "seed": seed, "error": "missing input " + str(inp)}
    src_board = json.loads(inp.read_text(encoding="utf-8")).get("board", {})
    if any((src_board.get("rows") != 24, src_board.get("cols") != 56,
            src_board.get("lockedRows") is not True, src_board.get("lockedCols") is not True)):
        return {"project": project, "configuration": config, "seed": seed, "error": "input is not locked 24x56"}
    cmd = [
        "node", str(HARNESS), "--data", str(project_dir), "--id", "1",
        "--seed", str(seed), "--moves", str(moves), "--native", "1",
        "--routing-preference", "wires", "--strict", "1", "--move-summary", "1",
        "--finish-trace", "1", "--save", str(saved),
    ]
    if drilled:
        cmd += ["--drilled", "1"]
    if not stack_allowed:
        cmd += ["--nostack", "1"]
    env = os.environ.copy()
    env["STRIPBOARD_TIMING"] = "1"
    try:
        proc = subprocess.run(cmd, cwd=FRONTEND, env=env, text=True, capture_output=True)
    except OSError as exc:
        return {"project": project, "configuration": config, "seed": seed, "error": str(exc)}
    logpath.write_text(proc.stderr, encoding="utf-8")
    result_lines = parse_json_lines(proc.stdout, "{")
    result = result_lines[-1] if result_lines else {}
    timings = parse_json_lines(proc.stderr, "timing ")
    finish = parse_json_lines(proc.stderr, "finishTrace ")
    err = None
    if proc.returncode not in (0, 2):
        err = "CLI exit " + str(proc.returncode)
    elif result.get("error"):
        err = str(result["error"])
    elif len(finish) != 1 or not result.get("moveSummary"):
        err = "missing one finish trace or move summary; check TypeScript rebuild"
    elif result.get("cliVersion") != PROFILE_VERSION:
        err = "stale CLI version: " + str(result.get("cliVersion"))
    elif result.get("strictValid") is not (proc.returncode == 0):
        err = "strictValid and CLI exit code disagree"
    elif not saved.is_file():
        err = "missing solved output"
    baseline_sig = row["sig"]
    match = result.get("sig") == baseline_sig if result and baseline_sig else None
    baseline_clean = str(row["clean"]).lower() in ("true", "1")
    strict_match = result.get("strictValid") == baseline_clean if result else None
    report = {
        "project": project, "configuration": config, "seed": seed,
        "baselineSig": baseline_sig, "signatureMatch": match,
        "baselineClean": baseline_clean, "strictMatch": strict_match,
        "exitCode": proc.returncode, "result": result,
        "timing": timings[-1] if timings else {},
        "finishTrace": finish, "saved": str(saved),
    }
    if err:
        report["error"] = err
    return report


def candidate_label(result, label):
    cand = result.get(label) or {}
    check = cand.get("verification") or {}
    terms = cand.get("scoreTerms") or {}
    return "{} Q{} colΔ{} slant{} horz{} stack{} knives{} (avoidable {}) crosses{}; score={} [Q={},mess={},price={}]; compliant={} errors={}".format(
        label, cand.get("quality"), cand.get("columnShiftWires"),
        cand.get("slantedWires"), cand.get("horizontalWires"),
        cand.get("stacked"), cand.get("knife"), cand.get("avoidableKnife"),
        cand.get("crossings"), cand.get("score"),
        terms.get("qualityCost"), terms.get("messCost"), terms.get("price"),
        check.get("compliant"), ",".join(check.get("failReasons", [])))


def report_summary(records, out, jobs):
    total = len(records)
    errors = [r for r in records if r.get("error")]
    mismatches = [r for r in records if r.get("signatureMatch") is False]
    clean_mismatches = [r for r in records if r.get("strictMatch") is False]
    counters = Counter()
    group_stats = defaultdict(Counter)
    phase_stats = defaultdict(list)
    for rec in records:
        if rec.get("error"):
            continue
        group = (rec["project"], rec["configuration"])
        stats = group_stats[group]
        stats["n"] += 1
        if rec.get("signatureMatch"):
            stats["sig"] += 1
        if rec["result"].get("strictValid"):
            stats["clean"] += 1
        moves = rec["result"].get("moveSummary", {})
        for k in ("attempted", "mutateFailed", "decodeFailed", "rejected", "accepted", "sameBoard"):
            counters[k] += int(moves.get(k, 0))
        for tr in rec.get("finishTrace", []):
            repair = tr.get("repair") or {}
            router = tr.get("router") or {}
            r_ok = bool(repair.get("eligible"))
            r_compliant = bool((repair.get("verification") or {}).get("compliant"))
            t_compliant = bool((router.get("verification") or {}).get("compliant"))
            stats["repair_eligible"] += int(r_ok)
            stats["repair_compliant"] += int(r_compliant)
            stats["router_compliant"] += int(t_compliant)
            stats["either_compliant"] += int(r_compliant or t_compliant)
            stats["selected_compliant"] += int(bool(tr.get("selectedCompliant")))
            stats["both_fail"] += int(not (r_compliant or t_compliant))
            stats["compliant_lost"] += int((r_compliant or t_compliant) and not tr.get("selectedCompliant"))
            stats["repair_q_bad"] += int(repair.get("quality", 1) != 0)
            stats["router_q_bad"] += int(router.get("quality", 1) != 0)
            for k, v in tr.get("routePhases", {}).items():
                if isinstance(v, (int, float)):
                    phase_stats[k].append(float(v))
    print("\n🏆 FULL NATIVE FINISH AUDIT — {} of {} cases | workers={}".format(total - len(errors), total, jobs))
    print("PROJECT   CONFIG                    N  SIG  CLEAN  REP_OK  REP_C  ROUT_C  EITHER  SELECT  BOTH_FAIL  LOST")
    for (project, config), c in sorted(group_stats.items()):
        print("{:<9} {:<23} {:>2} {:>4} {:>6} {:>7} {:>6} {:>7} {:>7} {:>7} {:>10} {:>5}".format(
            project, config, c["n"], c["sig"], c["clean"],
            c["repair_eligible"], c["repair_compliant"], c["router_compliant"],
            c["either_compliant"], c["selected_compliant"], c["both_fail"], c["compliant_lost"]))
    n = max(1, counters["attempted"])
    print("\n🔁 Annealing moves: {:,} attempted; reject {:,} ({:.1f}%), same {:,} ({:.1f}%), mutate failed {:,}, decode failed {:,}".format(
        counters["attempted"], counters["rejected"], 100 * counters["rejected"] / n,
        counters["sameBoard"], 100 * counters["sameBoard"] / n,
        counters["mutateFailed"], counters["decodeFailed"]))
    print("🧭 Route subphase times (mean ms, instrumented; parallel execution distorts timing):")
    for key, values in sorted(phase_stats.items(), key=lambda kv: -sum(kv[1]) / len(kv[1])):
        print("  {:<24} avg={:>7.1f} max={:>7.1f}".format(key, sum(values) / len(values), max(values)))
    print("🔏 Fingerprint mismatches: {} | clean mismatches: {} | failed cases: {}".format(
        len(mismatches), len(clean_mismatches), len(errors)))
    for rec in (errors + mismatches + clean_mismatches)[:25]:
        print("⚠️ {} / {} / #{}: {}".format(
            rec["project"], rec["configuration"], rec["seed"],
            rec.get("error") or "fingerprint/strict mismatch"))
    print("📁 Results:", out / "results.json")
    print("📁 Cases CSV:", out / "finish_matrix.csv")
    print("⚠️ The check uses existing harness electrical/geometry validators, not an independent netlist validator.")
    if jobs > 1:
        print("⚠️ Timings are contended: --jobs 1 for a sequential performance comparison.")
    return not errors and not mismatches and not clean_mismatches


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bench", type=Path, default=DEFAULT_BENCH, help="Original 80-run benchmark directory")
    parser.add_argument("--out", type=Path, default=None, help="Profile output; must be separate from baseline")
    parser.add_argument("--jobs", type=int, default=4, help="Parallel native processes (default 4; use 1 for timings)")
    parser.add_argument("--smoke", action="store_true", help="Four known seeds only instead of all 80")
    parser.add_argument("--verbose", action="store_true", help="Print per-candidate score details for every case")
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be >=1")
    bench = args.bench.expanduser().resolve()
    out = (args.out or (bench / ("cli_profile_v160_smoke" if args.smoke else "cli_profile_v160_full80"))).expanduser().resolve()
    baseline = bench / "comparison.csv"
    if not baseline.is_file():
        raise SystemExit("❌ Baseline CSV missing: " + str(baseline))
    if out == bench or out == bench.parent or out == ROOT:
        parser.error("--out must not overwrite benchmark or repository root")
    for built in (BUILT_JS, BUILT_FINISH):
        if not built.is_file():
            raise SystemExit("❌ Missing built TypeScript: {}. Run npx tsc -p tests/solver/tsconfig.json".format(built))
    for src, built in zip(SOURCE_FILES, (BUILT_JS, BUILT_FINISH)):
        if built.stat().st_mtime < src.stat().st_mtime:
            raise SystemExit("❌ Stale compiled solver: {}. Rebuild TypeScript.".format(built))
    cases = load_cases(baseline, args.smoke)
    out.mkdir(parents=True, exist_ok=True)
    snapshot = out / "baseline_snapshot.csv"
    baseline_bytes = baseline.read_bytes()
    if snapshot.exists() and snapshot.read_bytes() != baseline_bytes:
        raise SystemExit("❌ Baseline has changed since last profile; refusing to compare inconsistent fingerprints")
    if not snapshot.exists():
        shutil.copy2(baseline, snapshot)
    (out / "baseline_sha256.txt").write_text(
        hashlib.sha256(baseline_bytes).hexdigest() + "  comparison.csv\n", encoding="utf-8")
    print("🔒 Baseline CSV snapshotted (SHA256 checked); existing layouts untouched.")
    print("🚀 Profiling {} runs (jobs={}, moves from baseline).".format(len(cases), args.jobs), flush=True)
    results = []
    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        futures = {executor.submit(run_case, r, bench, out): r for r in cases}
        for f in as_completed(futures):
            rec = f.result()
            results.append(rec)
            trace = (rec.get("finishTrace") or [{}])[0]
            repair = trace.get("repair") or {}
            router = trace.get("router") or {}
            print("{} {} {} #{} | sig={} clean={} | selected={} repairQ={} routerQ={} either={} | {:.0f}ms".format(
                "❌" if rec.get("error") or rec.get("signatureMatch") is False else "✅",
                rec["project"], rec["configuration"], rec["seed"],
                "MATCH" if rec.get("signatureMatch") else "DIFF",
                rec.get("result", {}).get("strictValid"),
                trace.get("selected", "?"), repair.get("quality", "?"), router.get("quality", "?"),
                trace.get("anyCompliant"), rec.get("timing", {}).get("solveMs", 0)), flush=True)
            if args.verbose and trace:
                print("  🛠️ " + candidate_label(trace, "repair"))
                print("  🧭 " + candidate_label(trace, "router"))
                print("  ⏱️ route phases:", trace.get("routePhases"))
    order = {(r["project"], r["configuration"], int(r["seed"])): i for i, r in enumerate(cases)}
    results.sort(key=lambda r: order[(r["project"], r["configuration"], r["seed"])])
    (out / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    flat = []
    for rec in results:
        ft = (rec.get("finishTrace") or [{}])[0]
        x = {"project": rec["project"], "configuration": rec["configuration"], "seed": rec["seed"],
             "error": rec.get("error", ""), "baselineSig": rec.get("baselineSig", ""),
             "newSig": rec.get("result", {}).get("sig", ""),
             "sigMatch": rec.get("signatureMatch"), "strictMatch": rec.get("strictMatch"),
             "selected": ft.get("selected"), "selectedCompliant": ft.get("selectedCompliant"),
             "eitherCompliant": ft.get("anyCompliant"),
             "routeMs": rec.get("timing", {}).get("routeMs"),
             "solveMs": rec.get("timing", {}).get("solveMs")}
        for label in ("repair", "router"):
            c = ft.get(label) or {}
            v = c.get("verification") or {}
            terms = c.get("scoreTerms") or {}
            for key in ("quality", "columnShiftWires", "slantedWires", "horizontalWires",
                        "stacked", "knife", "avoidableKnife", "forcedKnife", "crossings", "score"):
                x[label + "_" + key] = c.get(key)
            for key in ("qualityCost", "messCost", "price", "offAxis", "crossings", "stacked", "mess"):
                x[label + "_score_" + key] = terms.get(key)
            for key in ("compliant", "conflicts", "incomplete", "geometry", "crossingsHarness"):
                x[label + "_verified_" + key] = v.get(key)
            x[label + "_failed"] = ",".join(v.get("failReasons", []))
        flat.append(x)
    if flat:
        with (out / "finish_matrix.csv").open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(flat[0]))
            writer.writeheader()
            writer.writerows(flat)
    if not report_summary(results, out, args.jobs):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
