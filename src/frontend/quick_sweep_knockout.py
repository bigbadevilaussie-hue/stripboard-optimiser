#!/usr/bin/env python3
"""Quick Sweep -> head-to-head Knockout -> Endurance tournament for v5Solve.js.

Run from the repository root. The solver is compiled once, the input corpus is
snapshotted once, and every run gets its own output/log files. Failed and
invalid runs remain in the manifest; any candidate the solver saved is kept.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "src" / "frontend"
SOLVER = FRONTEND / "tests" / "solver" / "v5Solve.js"
SOLVER_OUT = FRONTEND / "tests" / "solver" / "out"


@dataclass
class Result:
    stage: str
    seed: int
    moves: int
    status: str
    valid: bool
    wires: int | None = None
    cuts: int | None = None
    price: float | None = None
    quality: float | None = None
    conflicts: int | None = None
    incomplete: int | None = None
    geometry_errors: int | None = None
    off_axis_wires: int | None = None
    rows: int | None = None
    cols: int | None = None
    runtime_seconds: float = 0.0
    candidate: str | None = None
    stdout_log: str | None = None
    stderr_log: str | None = None
    error: str | None = None


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def parse_report(stdout: str) -> dict[str, Any]:
    # v5Solve emits its final machine-readable report as one JSON line.
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict) and ("quality" in value or "error" in value):
                return value
    raise ValueError("v5Solve did not emit its final JSON report")


def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(tmp, path)


def rank_key(r: Result) -> tuple:
    # Historical tournament policy: wires, then cuts, then price.
    return (
        r.wires if r.wires is not None else 10**9,
        r.cuts if r.cuts is not None else 10**9,
        r.price if r.price is not None else float("inf"),
        r.moves,
        r.seed,
    )


def run_one(stage: str, seed: int, moves: int, args: argparse.Namespace,
            run_dir: Path, data_snapshot: Path) -> Result:
    started = time.monotonic()
    stem = f"{stage.lower().replace(' ', '-')}-seed-{seed:05d}-moves-{moves:06d}"
    candidate = run_dir / "candidates" / f"{stem}.json"
    stdout_log = run_dir / "logs" / f"{stem}.stdout.txt"
    stderr_log = run_dir / "logs" / f"{stem}.stderr.txt"
    candidate.parent.mkdir(parents=True, exist_ok=True)
    stdout_log.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        args.node, str(SOLVER),
        "--data", str(data_snapshot),
        "--id", str(args.project_id),
        "--seed", str(seed),
        "--moves", str(moves),
        "--drilled", str(args.drilled),
        "--out", str(SOLVER_OUT),
        "--save", str(candidate),
    ]
    try:
        completed = subprocess.run(
            cmd, capture_output=True, text=True, timeout=args.timeout,
            cwd=FRONTEND,
        )
        stdout_log.write_text(completed.stdout or "")
        stderr_log.write_text(completed.stderr or "")
        if completed.returncode != 0:
            raise RuntimeError(f"solver exit {completed.returncode}")
        report = parse_report(completed.stdout)
        if report.get("error"):
            raise RuntimeError(str(report["error"]))

        board_data = json.loads(candidate.read_text()) if candidate.is_file() else None
        if board_data is None:
            raise RuntimeError("v5Solve produced no --save project JSON")
        board = board_data.get("board") or {}
        wires = report.get("wires", len(board.get("wires", [])))
        cuts = report.get("cuts", len(board.get("cuts", [])))
        quality = report.get("quality")
        conflicts = report.get("conflicts")
        incomplete = report.get("incomplete")
        geometry_errors = report.get("geo")
        off_axis = report.get("offAxis")
        rows = report.get("rows", board.get("rows"))
        cols = report.get("cols", board.get("cols"))
        price_value = report.get("price")
        if price_value is None:
            rate = report.get("rate")
            if isinstance(rate, dict):
                price_value = rate.get("price", rate.get("score", rate.get("E")))
            elif isinstance(rate, (int, float)):
                price_value = rate

        checks = {
            "quality": quality == 0,
            "conflicts": conflicts == 0,
            "incomplete": incomplete == 0,
            "geo": geometry_errors == 0,
            "offAxis": off_axis == 0,
        }
        if args.required_rows:
            checks["rows"] = rows == args.required_rows
        if args.required_cols:
            checks["cols"] = cols == args.required_cols
        missing = [name for name, value in checks.items()
                   if value is False and report.get(name) is None]
        reasons = [f"{name}={report.get(name)}"
                   for name, ok in checks.items() if not ok]
        if missing:
            reasons.append("missing validation fields: " + ", ".join(missing))
        valid = all(checks.values()) and not missing
        return Result(
            stage, seed, moves, "valid" if valid else "invalid", valid,
            int(wires) if isinstance(wires, (int, float)) else None,
            int(cuts) if isinstance(cuts, (int, float)) else None,
            float(price_value) if isinstance(price_value, (int, float)) else None,
            float(quality) if isinstance(quality, (int, float)) else None,
            int(conflicts) if isinstance(conflicts, (int, float)) else None,
            int(incomplete) if isinstance(incomplete, (int, float)) else None,
            int(geometry_errors) if isinstance(geometry_errors, (int, float)) else None,
            int(off_axis) if isinstance(off_axis, (int, float)) else None,
            int(rows) if isinstance(rows, (int, float)) else None,
            int(cols) if isinstance(cols, (int, float)) else None,
            time.monotonic() - started, str(candidate),
            str(stdout_log), str(stderr_log),
            "; ".join(reasons) if reasons else None,
        )
    except subprocess.TimeoutExpired as exc:
        if exc.stdout:
            stdout_log.write_text(exc.stdout if isinstance(exc.stdout, str) else exc.stdout.decode(errors="replace"))
        if exc.stderr:
            stderr_log.write_text(exc.stderr if isinstance(exc.stderr, str) else exc.stderr.decode(errors="replace"))
        return Result(stage, seed, moves, "timeout", False,
                      runtime_seconds=time.monotonic() - started,
                      candidate=str(candidate) if candidate.exists() else None,
                      stdout_log=str(stdout_log), stderr_log=str(stderr_log),
                      error=f"Exceeded {args.timeout}s timeout")
    except Exception as exc:
        return Result(stage, seed, moves, "failed", False,
                      runtime_seconds=time.monotonic() - started,
                      candidate=str(candidate) if candidate.exists() else None,
                      stdout_log=str(stdout_log) if stdout_log.exists() else None,
                      stderr_log=str(stderr_log) if stderr_log.exists() else None,
                      error=str(exc))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--project", type=Path, required=True,
                   help="source project JSON; copied to the solver corpus as projects/<id>.json")
    p.add_argument("--project-id", type=int, default=0)
    p.add_argument("--node", default="node")
    p.add_argument("--drilled", type=int, choices=(0, 1), default=1)
    p.add_argument("--quick-seeds", type=int, default=1000)
    p.add_argument("--quick-start-seed", type=int, default=1)
    p.add_argument("--quick-moves", type=int, default=50000)
    p.add_argument("--advance", type=int, default=32)
    p.add_argument("--knockout-moves", type=int, default=25000)
    p.add_argument("--finalists", type=int, default=4)
    p.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    p.add_argument("--timeout", type=int, default=900)
    p.add_argument("--required-rows", type=int, default=0)
    p.add_argument("--required-cols", type=int, default=0)
    p.add_argument("--output", type=Path, default=Path("tournament-runs"))
    p.add_argument("--skip-build", action="store_true",
                   help="skip the TypeScript solver build")
    args = p.parse_args()

    args.project = args.project.resolve()
    if not args.project.is_file():
        p.error(f"project does not exist: {args.project}")
    if args.quick_seeds < 1 or args.advance < 1 or args.finalists < 1 or args.workers < 1:
        p.error("quick-seeds, advance, finalists and workers must be positive")
    if not SOLVER.is_file():
        p.error(f"v5Solve.js not found in repository: {SOLVER}")

    # Build the exact CommonJS tree v5Solve.js loads. It also needs the
    # checked-in decoder and router WASM files from components/stripboard/v5wasm.
    if not args.skip_build:
        print("Building solver TypeScript...", flush=True)
        build = subprocess.run(
            ["npx", "tsc", "-p", "tests/solver/tsconfig.json"],
            cwd=FRONTEND, text=True, capture_output=True,
        )
        if build.returncode:
            sys.stderr.write(build.stdout + build.stderr)
            return build.returncode
    for wasm in ("v5decode.wasm", "v5route.wasm"):
        if not (FRONTEND / "components" / "stripboard" / "v5wasm" / wasm).is_file():
            p.error(f"missing solver WASM module: {wasm}; build it with npm run build:wasm")

    run_id = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    run_dir = (args.output / run_id).resolve()
    run_dir.mkdir(parents=True, exist_ok=False)

    # v5Solve reads only data/projects/<id>.json. Snapshot just that immutable
    # project rather than copying the entire solver harness.
    data_snapshot = run_dir / "input-data"
    project_target = data_snapshot / "projects" / f"{args.project_id}.json"
    project_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.project, project_target)

    manifest: dict[str, Any] = {
        "run_id": run_id,
        "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "project": str(args.project),
        "project_sha256": sha256(args.project),
        "solver": str(SOLVER),
        "solver_sha256": sha256(SOLVER),
        "settings": {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
        "results": [],
    }
    save_json(run_dir / "manifest.json", manifest)
    print(f"Run directory: {run_dir}")
    print(f"Project SHA256: {manifest['project_sha256']}")

    def stage(label: str, jobs: list[tuple[int, int]]) -> list[Result]:
        print(f"\n=== {label}: {len(jobs)} runs, {args.workers} workers ===", flush=True)
        results: list[Result] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(run_one, label, seed, moves, args, run_dir, data_snapshot)
                       for seed, moves in jobs]
            for n, future in enumerate(concurrent.futures.as_completed(futures), 1):
                result = future.result()
                results.append(result)
                print(f"[{n}/{len(jobs)}] seed={result.seed} moves={result.moves} "
                      f"{result.status} W={result.wires} C={result.cuts} P={result.price} "
                      f"{result.error or ''}", flush=True)
                manifest["results"].append(asdict(result))
                save_json(run_dir / "manifest.json", manifest)
        return results

    quick = stage("QUICK SWEEP", [
        (seed, args.quick_moves)
        for seed in range(args.quick_start_seed, args.quick_start_seed + args.quick_seeds)
    ])
    quick_leaders = sorted((r for r in quick if r.valid), key=rank_key)[:args.advance]
    if not quick_leaders:
        print("No valid quick-sweep candidates; see logs and manifest.")
        return 2
    print("\nQuick Sweep leaders:")
    for r in quick_leaders[:10]:
        print(f"  seed {r.seed}: {r.wires} wires, {r.cuts} cuts, price={r.price}")

    # Genuine single-elimination: pair adjacent quick-sweep leaders. Each pair
    # is re-solved at the same budget; the better valid result advances.
    bracket = [r.seed for r in quick_leaders]
    round_no = 1
    while len(bracket) > args.finalists:
        print(f"\n=== KNOCKOUT ROUND {round_no}: {len(bracket)} seeds ===")
        round_results = stage(f"KNOCKOUT-{round_no}", [(s, args.knockout_moves) for s in bracket])
        by_seed = {r.seed: r for r in round_results}
        next_bracket: list[int] = []
        for i in range(0, len(bracket), 2):
            pair = bracket[i:i + 2]
            if len(pair) == 1:
                next_bracket.extend(pair)
                print(f"  seed {pair[0]} receives a bye")
                continue
            a, b = (by_seed.get(s) for s in pair)
            if a and a.valid and b and b.valid:
                winner = min((a, b), key=rank_key).seed
                print(f"  {pair[0]} vs {pair[1]} -> {winner}")
                next_bracket.append(winner)
            elif a and a.valid:
                print(f"  {pair[0]} advances; {pair[1]} failed validation")
                next_bracket.append(pair[0])
            elif b and b.valid:
                print(f"  {pair[1]} advances; {pair[0]} failed validation")
                next_bracket.append(pair[1])
            else:
                print(f"  {pair[0]} vs {pair[1]} -> double elimination")
        bracket = next_bracket
        round_no += 1
        if not bracket:
            print("All knockout candidates were eliminated.")
            return 3

    finalists = bracket
    endurance_budgets = list(range(5000, 200001, 5000))
    endurance = stage("ENDURANCE", [
        (seed, moves) for seed in finalists for moves in endurance_budgets
    ])
    ranked = sorted((r for r in endurance if r.valid), key=rank_key)
    manifest["finalists"] = finalists
    manifest["champion"] = asdict(ranked[0]) if ranked else None
    manifest["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    if ranked:
        winner = ranked[0]
        champion_path = run_dir / "CHAMPION.json"
        shutil.copy2(winner.candidate, champion_path)
        save_json(run_dir / "leaderboard.json", [asdict(r) for r in ranked])
        print(f"\nCHAMPION: seed {winner.seed} at {winner.moves} moves — "
              f"{winner.wires} wires, {winner.cuts} cuts, price={winner.price}")
        print(f"Winning project: {champion_path}")
    else:
        print("\nNo valid finalist endurance runs.")
    save_json(run_dir / "manifest.json", manifest)
    print(f"Manifest: {run_dir / 'manifest.json'}")
    return 0 if ranked else 4


if __name__ == "__main__":
    sys.exit(main())
