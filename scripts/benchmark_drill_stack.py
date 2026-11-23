#!/usr/bin/env python3
"""Reproducible 80-run native v5 drill/stack matrix; never edits source JSON.

Run at repository root: python3 scripts/benchmark_drill_stack.py
10 fixed randomly selected seeds x 2 projects x 4 physical-rule combinations.
"""
import argparse
import csv
import json
import os
import statistics
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

SEEDS = [382, 639, 736, 820, 897, 1036, 1121, 1277, 1437, 1552]
CONFIGS = [
    ("DRILL_ON_STACK_OFF", True, False),
    ("DRILL_OFF_STACK_OFF", False, False),
    ("DRILL_OFF_STACK_ON", False, True),
    ("DRILL_ON_STACK_ON", True, True),
]
ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "src" / "frontend"
HARNESS = FRONTEND / "tests" / "solver" / "v5Solve.js"
SOURCES = {
    "MOTO": ROOT / "test-fixtures" / "masters" / "moto" / "moto.json",
    "MOTOMIX": ROOT / "motomix.json",
}
INPUT_REVISION = "v1.62-C1-1000uF"


def f1_components(data):
    return [c for c in data.get("components", []) if c.get("label") == "F1"]


def prepare(out):
    originals = {}
    for name, src in SOURCES.items():
        if not src.is_file():
            raise SystemExit("Missing source project: " + str(src))
        data = json.loads(src.read_text(encoding="utf-8"))
        c1 = [c for c in data.get("components", []) if c.get("label") == "C1"]
        if len(c1) != 1 or c1[0].get("value") != "1000µF":
            raise SystemExit(f"{name}: C1 must be corrected to 1000µF before this benchmark; "
                             f"found {[c.get(\'value\') for c in c1]} (run scripts/fix_moto_c1.py --apply)")
        if not isinstance(data.get("board"), dict):
            raise SystemExit("Missing board in " + str(src))
        f1s = f1_components(data)
        if len(f1s) != 1:
            raise SystemExit(name + ": expected exactly one F1 component, got " + str(len(f1s)))
        board = data["board"]
        board.update(rows=24, cols=56, lockedRows=True, lockedCols=True)
        # F1 stays exactly as it is in each source file. Only board-size locks
        # are forced. MOTO vs MOTOMIX is not a controlled F1-only comparison.
        f1 = f1s[0]
        originals[name] = {
            "locked": bool(f1.get("locked", False)),
            "pos": f1.get("boardPos"),
            "rotation": f1.get("rotation", 0),
            "id": f1["id"],
        }
        folder = out / name / "projects"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "1.json").write_text(json.dumps(data), encoding="utf-8")
        print("📁 {}: {} | F1 locked={} | F1 position={} | board LOCKED 24×56".format(
            name, src, originals[name]["locked"], originals[name]["pos"]
        ), flush=True)
    return originals


def average(rows, field):
    values = [float(x[field]) for x in rows if x.get(field) is not None]
    return statistics.mean(values) if values else None


def fmt(x, suffix=""):
    return ("—" if x is None else "{:.0f}{}".format(x, suffix))


def run_case(out, project, label, drilled, stack_on, moves, originals, jobs):
    rows = []
    location = out / project / label
    location.mkdir(parents=True, exist_ok=True)
    print("\n" + "=" * 86, flush=True)
    print("🏁 {} · {} · {} moves · 10 seeds".format(project, label, format(moves, ",")), flush=True)
    print("=" * 86, flush=True)
    def solve_seed(idx, seed):
        save = location / ("seed_{:04d}.json".format(seed))
        cmd = [
            "node", str(HARNESS), "--data", str(out / project),
            "--id", "1", "--seed", str(seed), "--moves", str(moves),
            "--native", "1", "--routing-preference", "wires",
            "--save", str(save),
        ]
        if drilled:
            cmd.extend(["--drilled", "1"])
        if not stack_on:
            cmd.extend(["--nostack", "1"])
        env = os.environ.copy()
        env["STRIPBOARD_TIMING"] = "1"
        process = subprocess.run(cmd, cwd=FRONTEND, env=env, text=True, capture_output=True)
        row = {
            "project": project, "configuration": label, "seed": seed,
            "moves": moves, "drilled_required": int(drilled), "stack_allowed": int(stack_on),
        }
        try:
            result_lines = [ln for ln in process.stdout.splitlines() if ln.startswith("{")]
            timings = [ln[7:] for ln in process.stderr.splitlines() if ln.startswith("timing ")]
            if process.returncode != 0 or not result_lines or not timings:
                raise RuntimeError("process failed/empty result; exit code {}".format(process.returncode))
            result = json.loads(result_lines[-1])
            timing = json.loads(timings[-1])
            if result.get("error") or timing.get("error"):
                raise RuntimeError(str(result.get("error") or timing.get("error")))
            if not save.is_file():
                raise RuntimeError("missing saved layout")
            solved = json.loads(save.read_text(encoding="utf-8"))
            board = solved["board"]
            # Historical 'diagonals_actual' is actually all column-changing links.
            actual_diags = sum(
                1 for wire in board.get("wires", [])
                if wire["from"]["col"] != wire["to"]["col"]
            )
            slanted = sum(
                1 for wire in board.get("wires", [])
                if wire["from"]["col"] != wire["to"]["col"]
                and wire["from"]["row"] != wire["to"]["row"]
            )
            horizontal = actual_diags - slanted
            original = originals[project]
            matches = [c for c in solved.get("components", []) if c.get("id") == original["id"]]
            f1_kept = bool(matches) and (
                not original["locked"] or (
                    bool(matches[0].get("locked")) and
                    matches[0].get("boardPos") == original["pos"] and
                    matches[0].get("rotation", 0) == original["rotation"]
                )
            )
            row.update(result)
            row.update(timing)
            row.update({
                "diagonals_actual": actual_diags,  # preserve original gate
                "slanted_actual": slanted, "horizontal_actual": horizontal,
                "board_24x56": (board.get("rows") == 24 and board.get("cols") == 56
                                and board.get("lockedRows") is True and board.get("lockedCols") is True),
                "f1_kept": f1_kept,
                "failed": False,
            })
            electrical_geometry_ok = (
                row.get("quality") == 0
                and row.get("conflicts") == 0
                and row.get("incomplete") == 0
                and row.get("geo") == 0
                and not row.get("issues")
                and row["board_24x56"] and row["f1_kept"]
            )
            row["clean"] = (
                electrical_geometry_ok and actual_diags == 0
                and row.get("offAxis", 0) == 0
                and (not drilled or row.get("knife") == 0)
                and (stack_on or row.get("stacked") == 0)
            )
            print(
                "{} {}/10 #{} · 🔌{} ✂️{} · ↘slant {} ↔horizontal {} · colΔ{} · 🔪{} · 🧵{} · "
                "Q{} geo{} · 🔁{}ms 🧭{}ms ⏱{}ms".format(
                    "✅" if row["clean"] else "❌", idx, seed,
                    row.get("wires", "?"), row.get("cuts", "?"),
                    slanted, horizontal, actual_diags, row.get("knife", "?"), row.get("stacked", "?"),
                    row.get("quality", "?"), row.get("geo", "?"),
                    fmt(row.get("annealMs")), fmt(row.get("routeMs")),
                    fmt(row.get("solveMs")),
                ), flush=True
            )
        except Exception as exc:
            row.update(failed=True, clean=False, error=str(exc))
            (location / ("seed_{:04d}.error.log".format(seed))).write_text(
                process.stdout + "\nSTDERR:\n" + process.stderr, encoding="utf-8")
            print("⚠️ {}/10 #{} FAILED: {}".format(idx, seed, exc), flush=True)
        return row
    with ThreadPoolExecutor(max_workers=jobs) as executor:
        futures = [executor.submit(solve_seed, idx, seed) for idx, seed in enumerate(SEEDS, 1)]
        for future in as_completed(futures):
            rows.append(future.result())
    rows.sort(key=lambda row: SEEDS.index(row["seed"]))
    clean = [r for r in rows if r.get("clean")]
    print(
        "📊 {} {}: ✅ {}/10 | avg solve {}ms | avg anneal {}ms | "
        "avg slants {} | avg horizontal {} | avg col-shifts {} | avg knives {} | avg stacked {}".format(
            project, label, len(clean), fmt(average(rows, "solveMs")),
            fmt(average(rows, "annealMs")), fmt(average(rows, "slanted_actual")),
            fmt(average(rows, "horizontal_actual")), fmt(average(rows, "diagonals_actual")),
            fmt(average(rows, "knife")), fmt(average(rows, "stacked"))
        ), flush=True
    )
    return rows


def final_report(records, out, moves):
    print("\n" + "=" * 109)
    print("🏆 FINAL — 10 SHARED RANDOM SEEDS × FOUR RULE SETS × TWO PROJECTS — {} MOVES".format(moves))
    print("Seeds:", ", ".join(str(x) for x in SEEDS))
    print("=" * 109)
    print("{:<9} {:<22} {:>7} {:>10} {:>10} {:>8} {:>8} {:>8} {:>12}".format(
        "PROJECT", "DRILL / STACK", "CLEAN", "SOLVE ms", "ANNEAL ms", "SLANT", "KNIFE", "STACK", "BEST CLEAN"))
    print("-" * 109)
    for project in SOURCES:
        for label, _, _ in CONFIGS:
            group = [r for r in records if r["project"] == project and r["configuration"] == label]
            clean = [r for r in group if r.get("clean")]
            best = min(clean, key=lambda r: (r["wires"], r["cuts"])) if clean else None
            best_text = ("{}W/{}C #{}".format(best["wires"], best["cuts"], best["seed"])
                         if best else "—")
            print("{:<9} {:<22} {:>7} {:>10} {:>10} {:>8} {:>8} {:>8} {:>12}".format(
                project, label, "{}/10".format(len(clean)),
                fmt(average(group, "solveMs")), fmt(average(group, "annealMs")),
                fmt(average(group, "slanted_actual")),
                fmt(average(group, "knife")), fmt(average(group, "stacked")), best_text,
            ))
    print("\n↘ SLANT changes both row and column; ↔ HORIZONTAL changes column only.")
    print("Historical diagonals_actual counts every column shift; CLEAN still requires vertical-only wiring.")
    print("KNIFE and STACK are harness counts.")
    print("CLEAN requires Q0, connectivity, geometry, 24x56 board, F1 lock preservation, "
          "zero diagonals, and the enabled drill/stack restrictions.")
    print("Both SOURCE FILES differ; differences between MOTO and MOTOMIX cannot be "
          "attributed to F1 locking alone.")
    print("All 80 layouts (when solved), individual results, and error logs: " + str(out))
    print("📁 CSV: " + str(out / "comparison.csv"), flush=True)


def physical_cpu_count():
    """Cap parallel native processes to physical cores (macOS sysctl)."""
    try:
        value = int(subprocess.check_output(["sysctl", "-n", "hw.physicalcpu"],
                                            stderr=subprocess.DEVNULL, text=True).strip())
        if value > 0:
            return value
    except (OSError, ValueError, subprocess.CalledProcessError):
        pass
    return max(1, os.cpu_count() or 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--moves", type=int, default=20000, help="Moves per seed (default: 20000)")
    parser.add_argument("--jobs", type=int, default=4, help="Parallel native solver processes (default: 4; use 1 for serial)")
    parser.add_argument("--out", type=Path, default=Path("/tmp/stripboard_drill_stack_80_c1_v162"))
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be at least 1")
    out = args.out.expanduser().resolve()
    legacy = Path("/tmp/stripboard_drill_stack_80").resolve()
    if out == legacy or (out / "comparison.csv").exists():
        parser.error("Refusing to overwrite a historical benchmark; use a new --out directory")
    cores = physical_cpu_count()
    if args.jobs > cores:
        print("⚠️ Requested {} native workers, limiting to {} physical cores.".format(args.jobs, cores), flush=True)
        args.jobs = cores
    out.mkdir(parents=True, exist_ok=True)
    if not HARNESS.is_file():
        raise SystemExit("Missing solver harness: " + str(HARNESS))
    print("🚀 {} parallel native solves (fixed seeds; each job isolated)".format(args.jobs), flush=True)
    originals = prepare(out)
    (out / "benchmark_config.json").write_text(
        json.dumps({"input_revision": INPUT_REVISION, "seeds": SEEDS, "moves": args.moves,
                    "source_sha256": {k: __import__("hashlib").sha256(v.read_bytes()).hexdigest() for k, v in SOURCES.items()},
                    "sources": {k: str(v) for k, v in SOURCES.items()},
                    "original_f1": originals, "board": {"rows": 24, "cols": 56, "locked": True},
                    "configs": [{"label": k, "drilled": d, "stack_on": st} for k, d, st in CONFIGS]},
                   indent=2), encoding="utf-8")
    records = []
    try:
        for project in SOURCES:
            for label, drilled, stack_on in CONFIGS:
                records.extend(run_case(out, project, label, drilled, stack_on, args.moves, originals, args.jobs))
    except KeyboardInterrupt:
        print("\n⏹ Interrupted; writing partial results.", flush=True)
    fields = [
        "project", "configuration", "seed", "moves", "drilled_required", "stack_allowed",
        "failed", "error", "clean", "board_24x56", "f1_kept", "quality",
        "wires", "cuts", "knife", "stacked", "offAxis", "diagonals_actual", "slanted_actual", "horizontal_actual",
        "crossings", "geo", "conflicts", "incomplete", "issues",
        "solveMs", "annealMs", "extractMs", "skeletonMs", "repairMs",
        "routeMs", "exactRepairMs", "totalMs", "sig",
    ]
    with (out / "comparison.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
    final_report(records, out, args.moves)
    if len(records) != len(SEEDS) * len(CONFIGS) * len(SOURCES):
        sys.exit(1)


if __name__ == "__main__":
    main()
