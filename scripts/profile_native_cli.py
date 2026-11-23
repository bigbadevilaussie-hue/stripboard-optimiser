#!/usr/bin/env python3
"""Profile four native CLI regressions without overwriting the 80-run benchmark.

Requires built TypeScript output:
    cd src/frontend && npx tsc -p tests/solver/tsconfig.json
Then from the repo root:
    python3 scripts/profile_native_cli.py

Runs each 20k seed with --strict, --move-summary, --finish-trace,
and STRIPBOARD_TIMING=1; reads existing 24x56 benchmark input copies.
"""
import csv
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "src" / "frontend"
HARNESS = FRONTEND / "tests" / "solver" / "v5Solve.js"
SOURCE_TS = FRONTEND / "components" / "stripboard" / "autoLayout5.ts"
BUILT_JS = FRONTEND / "tests" / "solver" / "out" / "components" / "stripboard" / "autoLayout5.js"
BENCH = Path("/tmp/stripboard_drill_stack_80")
OUT = BENCH / "cli_profile_20k"

CASES = [
    ("MOTO", "DRILL_ON_STACK_OFF", 639, True, False, "Q0 with off-axis links"),
    ("MOTOMIX", "DRILL_OFF_STACK_ON", 897, False, True, "sole baseline clean"),
    ("MOTOMIX", "DRILL_ON_STACK_OFF", 1036, True, False, "persistent geometry error"),
    ("MOTOMIX", "DRILL_OFF_STACK_OFF", 1552, False, False, "routing latency outlier"),
]


def read_lines(text, prefix):
    found = []
    for line in text.splitlines():
        if line.startswith(prefix):
            try:
                found.append(json.loads(line[len(prefix):]))
            except json.JSONDecodeError:
                pass
    return found


def main():
    if not HARNESS.is_file() or not BUILT_JS.is_file():
        raise SystemExit("❌ Missing compiled solver; rebuild with: cd src/frontend && npx tsc -p tests/solver/tsconfig.json")
    if BUILT_JS.stat().st_mtime < SOURCE_TS.stat().st_mtime:
        raise SystemExit("❌ Compiled solver is older than autoLayout5.ts. Rebuild first: cd src/frontend && npx tsc -p tests/solver/tsconfig.json")
    OUT.mkdir(parents=True, exist_ok=True)
    all_data = []
    for project, config, seed, drilled, stack, reason in CASES:
        data_dir = BENCH / project
        inp = data_dir / "projects" / "1.json"
        if not inp.is_file():
            raise SystemExit("❌ Missing benchmark input " + str(inp) + " (run scripts/benchmark_drill_stack.py first)")
        source = json.loads(inp.read_text(encoding="utf-8"))
        board = source["board"]
        if board.get("rows") != 24 or board.get("cols") != 56 or not board.get("lockedRows") or not board.get("lockedCols"):
            raise SystemExit("❌ Not a locked 24x56 benchmark source: " + str(inp))
        saved = OUT / "{}_{}_{}.json".format(project, config, seed)
        cmd = [
            "node", str(HARNESS), "--data", str(data_dir), "--id", "1", "--seed", str(seed),
            "--moves", "20000", "--native", "1", "--routing-preference", "wires",
            "--strict", "1", "--move-summary", "1", "--finish-trace", "1", "--save", str(saved),
        ]
        if drilled:
            cmd += ["--drilled", "1"]
        if not stack:
            cmd += ["--nostack", "1"]
        env = os.environ.copy()
        env["STRIPBOARD_TIMING"] = "1"
        print("\n🔬 {} / {} / seed #{} — {}".format(project, config, seed, reason), flush=True)
        proc = subprocess.run(cmd, cwd=FRONTEND, env=env, text=True, capture_output=True)
        (OUT / "{}_{}_{}.stderr.log".format(project, config, seed)).write_text(proc.stderr, encoding="utf-8")
        summaries = read_lines(proc.stdout, "{")
        # The CLI prints one final JSON object on stdout, optionally after
        # non-JSON diagnostics. Avoid guessing a source for missing results.
        result = summaries[-1] if summaries else {}
        timing = read_lines(proc.stderr, "timing ")
        finishes = read_lines(proc.stderr, "finishTrace ")
        if proc.returncode not in (0, 2) or not result or result.get("error"):
            print("❌ CLI failed: exit={} result={}".format(proc.returncode, result), flush=True)
            raise SystemExit(1)
        if not finishes or "moveSummary" not in result:
            print("❌ Missing finish trace/move summary; make sure the TypeScript solver was rebuilt.", flush=True)
            raise SystemExit(1)
        moves = result["moveSummary"]
        total = int(moves.get("attempted", 0))
        print("🔁 moves: {} | mutate rejected {} | decode failed {} | rejected {} | accepted {} | same {} | new best {}".format(
            total, moves.get("mutateFailed"), moves.get("decodeFailed"),
            moves.get("rejected"), moves.get("accepted"), moves.get("sameBoard"), moves.get("newBest")),
            flush=True,
        )
        for ft in finishes:
            for label in ("repair", "router"):
                cand = ft.get(label)
                if cand:
                    print("  {} {:<6} Q{} | ↘{} 🧵{} 🔪{} (forced {} avoidable {}) | score {} | eligible {}".format(
                        "🏆" if ft["selected"] == label else "  ",
                        label, cand["quality"], cand["diagonals"], cand["stacked"], cand["knife"],
                        cand["forcedKnife"], cand["avoidableKnife"], round(cand["score"], 1),
                        cand["eligible"]), flush=True)
            print("  📌 SELECTED:", ft["selected"], flush=True)
        t = timing[-1] if timing else {}
        failures = result.get("strictFailures", [])
        print("📐 strict={} | failures={} | ⏱ solve={}ms | 🧭 route={}ms".format(
            result.get("strictValid"), ",".join(failures) or "none",
            round(t.get("solveMs", 0)), round(t.get("routeMs", 0))), flush=True)
        all_data.append({
            "project": project, "configuration": config, "seed": seed,
            "result": result, "timing": t, "finishTrace": finishes,
            "exitCode": proc.returncode, "saved": str(saved),
        })
        (OUT / "results.json").write_text(json.dumps(all_data, indent=2), encoding="utf-8")
    print("\n✅ Four cases profiled. Full traces: " + str(OUT / "results.json"), flush=True)
    print("📁 Solved boards and raw stderr logs: " + str(OUT), flush=True)
    print("⚠️ This is instrumentation, not a before/after performance comparison; move logging adds overhead.")


if __name__ == "__main__":
    main()
