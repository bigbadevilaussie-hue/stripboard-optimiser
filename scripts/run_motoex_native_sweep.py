#!/usr/bin/env python3
"""Reproducible MOTOEX native Edge 200-seed tournament with full archive.

This is a benchmark controller, NOT solver logic. The actual solver remains
general-purpose. 200 seeds means 200 solver invocations TOTAL: distribute
the USB anchor among the selected legal slide columns, one column per seed.
No early stop: archive every strict pass and every rejected result.

Default policy: knives allowed (drilled-only OFF), wire stacking allowed,
but strict electrical/physical board, vertical jumper and crossing rules ON.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import time

from run_motoex_native_edge_slide import (
    EDGE_LIB, FRONTEND, ROOT, bool_option, check_trial, contract,
    prepare_trial, slide_positions,
)

DEFAULT_OUT = Path.home() / "Desktop" / "motoex_native_sweep_200x25k_knife_stack"
ROUTE_LIB = FRONTEND / "tests/solver/native/build/libv5route.so"
NATIVE_ADDON = FRONTEND / "tests/solver/native/build/v5native.node"

def jdump(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)

def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    temporary.replace(path)

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def timing_from_stderr(stderr):
    for line in reversed(stderr.splitlines()):
        if line.startswith("timing "):
            try:
                return json.loads(line[7:])
            except ValueError:
                return {"parseError": line[:200]}
    return {}

def wire_length(saved):
    return round(sum(((w["from"]["row"] - w["to"]["row"]) ** 2 +
                      (w["from"]["col"] - w["to"]["col"]) ** 2) ** 0.5
                     for w in saved["board"]["wires"]), 3)

def key_of(entry, preference):
    if preference == "cuts":
        return (entry.get("cuts", 1e9), entry.get("wires", 1e9),
                entry.get("wireLength", 1e9), entry.get("price", 1e9),
                entry["seed"], entry["column"])
    return (entry.get("wires", 1e9), entry.get("cuts", 1e9),
            entry.get("wireLength", 1e9), entry.get("price", 1e9),
            entry["seed"], entry["column"])

def percentile(values, percentage):
    if not values:
        return None
    values = sorted(values)
    index = (len(values) - 1) * percentage / 100
    lo = int(index)
    hi = min(len(values) - 1, lo + 1)
    return round(values[lo] * (hi - index) + values[hi] * (index - lo), 2) if hi != lo else round(values[lo], 2)

def stats_of(values):
    values = [float(x) for x in values if isinstance(x, (float, int))]
    return {"n": len(values), "min": round(min(values), 2) if values else None,
            "mean": round(statistics.mean(values), 2) if values else None,
            "median": percentile(values, 50), "p95": percentile(values, 95),
            "max": round(max(values), 2) if values else None}

def columns_from_arg(arg, all_columns):
    if arg == "all":
        return list(all_columns)
    try:
        selected = [int(item.strip()) for item in arg.split(",")]
    except ValueError as e:
        raise ValueError("--columns must be all or comma-separated integers") from e
    if not selected or len(selected) != len(set(selected)):
        raise ValueError("--columns cannot be empty or contain duplicates")
    illegal = [n for n in selected if n not in all_columns]
    if illegal:
        raise ValueError("USB columns outside legal Edge slide: " + str(illegal))
    return selected

def capture_one(args, master, seed, column, output, source_sha):
    """All per-seed files have disjoint paths: thread workers share no input."""
    tag = "seed_{:04d}_col_{:02d}".format(seed, column)
    job = output / "jobs" / tag
    project = job / "input" / "projects" / "1.json"
    project.parent.mkdir(parents=True, exist_ok=True)
    prepared = prepare_trial(master, True, True, column)
    write_json(project, prepared)
    candidate = job / "candidate.json"
    stdout_path = job / "stdout.log"
    stderr_path = job / "stderr.log"
    env = os.environ.copy()
    env["V5_NATIVE_LIB_DIR"] = str(EDGE_LIB)
    env.pop("V5_NATIVE_ROUTE_LIB_DIR", None)
    env["STRIPBOARD_TIMING"] = "1"
    cmd = [
        "node", str(contract.CLI), "--data", str(job / "input"),
        "--id", "1", "--seed", str(seed), "--moves", str(args.moves),
        "--native", "1", "--strict", "1",
        "--drilled", "0", "--nostack", "0", "--drill-domain", "0",
        "--wire-polish", "1" if args.wire_polish else "0",
        "--routing-preference", args.rank,
        "--move-summary", "1", "--finish-trace", "1",
        "--save", str(candidate),
    ]
    begin = time.perf_counter()
    try:
        proc = subprocess.run(cmd, cwd=FRONTEND, env=env, capture_output=True,
                              text=True, timeout=args.timeout)
        stdout, stderr, code = proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout or b""
        stderr = error.stderr or b""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", "replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", "replace")
        stderr += "\nTIMEOUT after {}s\n".format(args.timeout)
        code = 124
    except OSError as error:
        stdout, stderr, code = "", repr(error), 127
    elapsed = round((time.perf_counter() - begin) * 1000, 2)
    stdout_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr, encoding="utf-8")
    entry = {
        "seed": seed, "column": column, "sourceSha256": source_sha,
        "exit": code, "strictPass": False, "elapsedWallMs": elapsed,
        "time": timing_from_stderr(stderr),
        "input": str(project.relative_to(output)),
        "stdoutLog": str(stdout_path.relative_to(output)),
        "stderrLog": str(stderr_path.relative_to(output)),
        "cmd": cmd, "errors": [], "diagnostics": {},
    }
    try:
        result = contract.cli_result(stdout)
        entry.update({
            "sig": result.get("sig"), "price": result.get("price"),
            "wires": result.get("wires"), "cuts": result.get("cuts"),
            "knife": result.get("knife"), "stacked": result.get("stacked"),
            "nonvertical": result.get("diagonalsActual"), "crossings": result.get("crossings"),
            "conflicts": result.get("conflicts"), "incomplete": result.get("incomplete"),
            "geometry": result.get("geo"), "quality": result.get("quality"),
            "rows": result.get("rows"), "cols": result.get("cols"),
            "strictValid": result.get("strictValid", False),
            "strictFailures": result.get("strictFailures", []),
            "firstFeasibleMove": result.get("firstFeasibleMove"),
            "firstFeasibleMs": result.get("firstFeasibleMs"),
            "unsolvedReason": result.get("unsolvedReason"),
            "moveSummary": result.get("moveSummary"),
        })
        # Diagnostics remain available for rejected candidates as well.
        entry["diagnostics"] = {
            "incompleteNets": result.get("incompleteNets", []),
            "knifeCuts": result.get("knifeCuts", []),
            "wireViolations": result.get("wireViolations", []),
            "wirePolish": result.get("wirePolish"),
            "issues": result.get("issues", []),
        }
        if not candidate.is_file():
            entry["errors"].append("SAVED_JSON_MISSING")
        else:
            saved = json.loads(candidate.read_text(encoding="utf-8"))
            entry["errors"].extend(check_trial(master, prepared, saved, result, code))
            entry["wireLength"] = wire_length(saved)
        if code not in (0, 2):
            entry["errors"].append("CLI_EXIT_" + str(code))
        if code == 0 and result.get("strictValid") is not True:
            entry["errors"].append("EXIT_0_BUT_STRICT_FALSE")
        if entry["errors"] == [] and code == 0 and result.get("strictValid") is True:
            entry["strictPass"] = True
    except (ValueError, TypeError, KeyError, OSError) as error:
        entry["errors"].append("RESULT_PARSE_OR_VERIFY_ERROR: " + str(error))
    if candidate.is_file():
        dest = output / ("solved" if entry["strictPass"] else "rejected") / (tag + ".json")
        dest.parent.mkdir(parents=True, exist_ok=True)
        candidate.replace(dest)
        entry["savedJson"] = str(dest.relative_to(output))
        entry["savedSha256"] = sha256(dest)
    return entry

def write_csv(path, rows):
    fields = ["seed", "column", "strictPass", "exit", "wires", "cuts", "wireLength",
              "knife", "stacked", "nonvertical", "crossings", "conflicts", "incomplete",
              "geometry", "quality", "price", "elapsedWallMs", "solveMs", "totalMs",
              "cpuMs", "rssMb", "firstFeasibleMove", "firstFeasibleMs", "sig",
              "strictFailures", "errors", "savedJson"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        out = csv.DictWriter(handle, fieldnames=fields)
        out.writeheader()
        for item in rows:
            row = {f: item.get(f) for f in fields}
            row.update({f: item.get("time", {}).get(f) for f in
                        ("solveMs", "totalMs", "cpuMs", "rssMb")})
            for f in ("strictFailures", "errors"):
                row[f] = jdump(row[f] or [])
            out.writerow(row)

def summarize(args, output, entries, source_hash, columns, started):
    entries.sort(key=lambda x: x["seed"])
    solved = sorted((e for e in entries if e.get("strictPass")), key=lambda e: key_of(e, args.rank))
    used = set()
    distinct = []
    for e in solved:
        signature = e.get("sig") or e.get("savedSha256")
        if signature not in used:
            used.add(signature)
            distinct.append(e)
    top = distinct[:5]
    errors = Counter(f for e in entries if not e.get("strictPass")
                     for f in (e.get("strictFailures") or e.get("errors") or ["NO_REASON"]))
    by_column = {str(c): {"attempts": sum(e["column"] == c for e in entries),
                          "strictPasses": sum(e["column"] == c and e.get("strictPass") for e in entries)}
                 for c in columns}
    timing = {field: stats_of([e.get("time", {}).get(field) for e in entries])
              for field in ("solveMs", "totalMs", "cpuMs", "annealMs", "rssMb")}
    timing["elapsedWallMs"] = stats_of([e.get("elapsedWallMs") for e in entries])
    timing["firstFeasibleMs"] = stats_of([e.get("firstFeasibleMs") for e in entries])
    summary = {
        "sourceSha256": source_hash, "totalRequested": args.seeds,
        "completed": len(entries), "strictSolved": len(solved),
        "distinctSolvedSignatures": len(distinct), "rejected": len(entries) - len(solved),
        "movesPerSeed": args.moves, "totalMovesRequested": args.seeds * args.moves,
        "policy": {"drilledCutsOnly": False, "noWireStacking": False,
                   "strictElectricalGeometryAndVerticalWires": True,
                   "rotationDomain": False, "wirePolish": args.wire_polish,
                   "ranking": [args.rank, "cuts" if args.rank == "wires" else "wires",
                               "wireLength", "price"], "columns": columns},
        "durationWallS": round(time.perf_counter() - started, 2),
        "timing": timing,
        "failureHistogram": dict(errors.most_common()),
        "byColumn": by_column, "top5": top,
        "allSolved": [{"seed": e["seed"], "column": e["column"],
                       "wires": e["wires"], "cuts": e["cuts"],
                       "sig": e.get("sig"), "savedJson": e.get("savedJson")}
                      for e in solved],
    }
    write_json(output / "summary.json", summary)
    write_csv(output / "results.csv", entries)
    write_json(output / "results.json", {"summary": {k: v for k, v in summary.items() if k != "top5" and k != "allSolved"},
                                         "results": entries})
    (output / "solved_index.jsonl").write_text(
        "".join(jdump(e) + "\n" for e in solved), encoding="utf-8")
    top_dir = output / "top5"
    top_dir.mkdir(exist_ok=True)
    for rank, e in enumerate(top, 1):
        src = output / e["savedJson"]
        dst = top_dir / ("rank_{:02d}_seed_{:04d}_col_{:02d}_W{}_C{}.json".format(
            rank, e["seed"], e["column"], e["wires"], e["cuts"]))
        shutil.copy2(src, dst)
    lines = [
        "# Native Edge sweep: {} seeds × {} moves".format(args.seeds, args.moves),
        "", "Drilled-only OFF (knife cuts permitted); stacking ALLOWED;",
        "independent strict connectivity, locked 24×56 geometry, vertical",
        "jumper and body-crossing checks are still mandatory.",
        "", "- Strict passes: **{} / {}**".format(len(solved), len(entries)),
        "- Distinct signatures: **{}**".format(len(distinct)),
        "- Wall time: **{} s**".format(summary["durationWallS"]),
        "- Mean solveMs: **{}**; p95: **{}**".format(timing["solveMs"]["mean"], timing["solveMs"]["p95"]),
        "", "## Top five distinct strictly solved boards", "",
        "| Rank | Seed | USB col | Wires | Cuts | Knife | Stacked | Length | Solver ms | JSON |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for rank, e in enumerate(top, 1):
        lines.append("| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            rank, e["seed"], e["column"], e["wires"], e["cuts"],
            e.get("knife"), e.get("stacked"), e.get("wireLength"),
            e.get("time", {}).get("solveMs"),
            e["savedJson"]))
    if not top:
        lines.append("| — | — | — | — | — | — | — | — | — | **NO STRICT SOLVES** |")
    lines.extend(["", "## Strict failure codes", ""])
    lines.extend("- {}: {}".format(k, v) for k, v in errors.most_common())
    lines.extend(["", "## Files", "",
        "- Every strict-solved JSON: solved/",
        "- Every rejected JSON (for post-analysis): rejected/",
        "- Per-seed input, stdout, stderr and raw finisher traces: jobs/",
        "- Every attempt with timing and move summary: results.json, results.csv, results.jsonl",
        "- All qualifying candidates in ranking order: solved_index.jsonl",
        "- Top-five copies: top5/",
        "- Full settings, source and binary hashes: manifest.json",
        ""])
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")
    return summary

def run(args):
    started = time.perf_counter()
    source_bytes = contract.MASTER.read_bytes()
    original = json.loads(source_bytes)
    usb, definition, overhang = contract.usb_source(original)
    allowed = slide_positions(usb, definition, 24, 56, True)
    columns = columns_from_arg(args.columns, allowed)
    if args.seeds > 1 and args.seed_start + args.seeds != len(set(range(args.seed_start, args.seed_start + args.seeds))) + args.seed_start:
        raise ValueError("Invalid seed range")
    for needed in (EDGE_LIB / "libv5decode.so", ROUTE_LIB, NATIVE_ADDON,
                   contract.CLI, FRONTEND / "tests/solver/out/components/stripboard/autoLayout5.js"):
        if not needed.is_file():
            raise ValueError("Build prerequisite missing: " + str(needed))
    output = args.out.expanduser().resolve()
    if output.exists() and any(output.iterdir()) and not args.resume:
        raise ValueError("Output directory is not empty; use a fresh --out, or --resume")
    output.mkdir(parents=True, exist_ok=True)
    checksum = hashlib.sha256(source_bytes).hexdigest()
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                            text=True, check=True).stdout.strip()
    manifest = {
        "createdUTC": datetime.now(timezone.utc).isoformat(), "repo": str(ROOT),
        "gitCommit": commit, "sourcePath": str(contract.MASTER),
        "sourceSha256": checksum, "board": {"rows": 24, "cols": 56,
                                          "lockedRows": True, "lockedCols": True},
        "usb": {"sourceColumn": usb["boardPos"]["col"], "row": usb["boardPos"]["row"],
                "overhangRows": overhang, "selectedColumns": columns},
        "seeds": args.seeds, "seedStart": args.seed_start,
        "moves": args.moves, "workers": args.workers, "timeout": args.timeout,
        "drilled": False, "nostack": False, "drillDomain": False,
        "wirePolish": args.wire_polish, "rank": args.rank,
        "binarySha256": {str(p.relative_to(ROOT)): sha256(p)
                         for p in (EDGE_LIB / "libv5decode.so", ROUTE_LIB, NATIVE_ADDON)},
    }
    manifest_path = output / "manifest.json"
    if args.resume and manifest_path.is_file():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        for field in ("sourceSha256", "seeds", "seedStart", "moves", "drilled",
                      "nostack", "drillDomain", "wirePolish", "rank", "usb", "binarySha256"):
            if manifest.get(field) != previous.get(field):
                raise ValueError("Resume manifest mismatch in " + field)
        manifest = previous
    else:
        write_json(manifest_path, manifest)

    log_file = output / "progress.log"
    def log(line):
        print(line, flush=True)
        with log_file.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    checkpoint = output / "results.jsonl"
    entries = {}
    if args.resume and checkpoint.is_file():
        for line in checkpoint.read_text(encoding="utf-8").splitlines():
            e = json.loads(line)
            if e.get("seed") in entries:
                raise ValueError("Duplicate seed in checkpoint: " + str(e["seed"]))
            if e.get("sourceSha256") != checksum:
                raise ValueError("Source checksum changed during resume")
            if e.get("savedJson") and not (output / e["savedJson"]).is_file():
                raise ValueError("Saved candidate missing during resume: " + str(e["savedJson"]))
            entries[e["seed"]] = e

    schedule = [(seed, columns[i % len(columns)])
                for i, seed in enumerate(range(args.seed_start, args.seed_start + args.seeds))]
    pending = [(seed, col) for seed, col in schedule if seed not in entries]
    log("🏁 NATIVE SWEEP | {} TOTAL seeds × {} moves | {} workers | {} legal USB columns".format(
        args.seeds, args.moves, args.workers, len(columns)))
    log("🛡️ STRICT ELECTRICAL + GEOMETRY + VERTICAL + 24×56 | 🔪 DRILLED OFF (KNIVES OK) | 🧷 STACKS ON")
    log("🔬 independent result checks; timing + move histograms + finish trace; no early stop")
    log("💾 ALL strict passes -> solved/ | all rejected -> rejected/ | top 5 unique -> top5/")
    if entries:
        log("🔁 Resuming {} finished, {} remaining".format(len(entries), len(pending)))

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(capture_one, args, original, seed, col, output, checksum): (seed, col)
                   for seed, col in pending}
        for future in as_completed(futures):
            seed, col = futures[future]
            try:
                item = future.result()
            except Exception as exc:
                # A bookkeeping failure is a failed attempt, not a fake pass.
                item = {"seed": seed, "column": col, "sourceSha256": checksum,
                        "strictPass": False, "exit": 127, "errors": ["SWEEP_WORKER_EXCEPTION: " + repr(exc)],
                        "time": {}, "elapsedWallMs": None}
            entries[seed] = item
            with checkpoint.open("a", encoding="utf-8") as file:
                file.write(jdump(item) + "\n")
                file.flush()
                os.fsync(file.fileno())
            solved = sum(e.get("strictPass", False) for e in entries.values())
            if item.get("strictPass"):
                status = "✅ STRICT PASS"
            elif item.get("unsolvedReason"):
                status = "🛑 UNSOLVED " + str(item["unsolvedReason"])
            else:
                status = "❌ " + ",".join(item.get("strictFailures") or item.get("errors") or ["UNCLASSIFIED"])[:92]
            log("{} | seed {:4d} USB col {:2d} | {}W/{}C knife={} stack={} | {:.2f}s | completed {}/{} | solved {}".format(
                status, seed, col, item.get("wires", "?"), item.get("cuts", "?"),
                item.get("knife", "?"), item.get("stacked", "?"),
                (item.get("elapsedWallMs") or 0) / 1000,
                len(entries), args.seeds, solved))

    summary = summarize(args, output, list(entries.values()), checksum, columns, started)
    log("🏆 TOP FIVE DISTINCT STRICT SOLVES (wires → cuts → length → price)")
    for rank, e in enumerate(summary["top5"], 1):
        log("🏅 #{} seed {} col {} | {} wires / {} cuts | knife={} stacked={} | {} | {}".format(
            rank, e["seed"], e["column"], e["wires"], e["cuts"],
            e.get("knife"), e.get("stacked"), e.get("time", {}).get("solveMs"),
            e["savedJson"]))
    if not summary["top5"]:
        log("🛑 No strict passes at this budget. All rejected boards + diagnostics still saved.")
    log("🏁 {}/{} strictly solved, {} unique | time {}s | {}".format(
        summary["strictSolved"], args.seeds, summary["distinctSolvedSignatures"],
        summary["durationWallS"], output / "report.md"))
    if contract.MASTER.read_bytes() != source_bytes:
        raise AssertionError("Canonical master changed during sweep")
    return 0 if summary["completed"] == args.seeds else 2

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seeds", type=int, default=200)
    p.add_argument("--seed-start", type=int, default=1)
    p.add_argument("--moves", type=int, default=25000)
    p.add_argument("--columns", default="all",
                   help="all legal USB slide columns (default) or e.g. 25,41; one column per seed")
    p.add_argument("--workers", type=int, default=min(6, max(1, (os.cpu_count() or 4) // 2)))
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--rank", choices=("wires", "cuts"), default="wires")
    p.add_argument("--wire-polish", type=bool_option, default=False, metavar="yes/no")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--resume", action="store_true")
    args = p.parse_args()
    if args.seeds < 1 or args.moves < 1 or args.workers < 1 or args.timeout < 1 or args.seed_start < 0:
        p.error("seeds/moves/workers/timeout must be positive and seed-start nonnegative")
    try:
        return run(args)
    except (ValueError, OSError, AssertionError, subprocess.CalledProcessError) as error:
        print("🛑 SWEEP SETUP/ARCHIVE ERROR: " + str(error), file=sys.stderr)
        return 64

if __name__ == "__main__":
    sys.exit(main())
