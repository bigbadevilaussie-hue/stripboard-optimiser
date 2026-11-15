#!/usr/bin/env python3
"""Quick Sweep -> Knockout -> Endurance tournament for v5Solve.js.

Run from the repository root. Each solver invocation receives a private copy
of the solver data directory, so concurrent runs cannot overwrite projects/0.json.
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
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Result:
    seed: int
    moves: int
    status: str
    valid: bool
    wires: int | None = None
    cuts: int | None = None
    price: float | None = None
    quality: int | None = None
    conflicts: int | None = None
    rows: int | None = None
    cols: int | None = None
    diagonals: int | None = None
    runtime_seconds: float = 0.0
    candidate: str | None = None
    error: str | None = None


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def parse_solver_json(stdout: str) -> dict[str, Any]:
    start = stdout.find("{")
    if start < 0:
        raise ValueError("Solver stdout did not contain JSON")
    decoder = json.JSONDecoder()
    value, _ = decoder.raw_decode(stdout[start:])
    if not isinstance(value, dict):
        raise ValueError("Solver JSON result was not an object")
    return value


def _point(value: Any) -> tuple[int, int] | None:
    if isinstance(value, dict):
        row = value.get("row", value.get("r", value.get("y")))
        col = value.get("col", value.get("column", value.get("c", value.get("x"))))
        if isinstance(row, (int, float)) and isinstance(col, (int, float)):
            return int(row), int(col)
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        if all(isinstance(x, (int, float)) for x in value[:2]):
            return int(value[0]), int(value[1])
    return None


def count_diagonals(wires: list[Any]) -> int | None:
    """Count diagonals when the saved wire endpoint schema is recognisable."""
    count = 0
    for wire in wires:
        if not isinstance(wire, dict):
            return None
        pair = None
        for a, b in (("from", "to"), ("start", "end"), ("a", "b"),
                     ("p1", "p2"), ("startPos", "endPos")):
            if a in wire and b in wire:
                pair = (_point(wire[a]), _point(wire[b]))
                break
        if pair is None or pair[0] is None or pair[1] is None:
            return None
        if pair[0][0] != pair[1][0] and pair[0][1] != pair[1][1]:
            count += 1
    return count


def run_one(seed: int, moves: int, args: argparse.Namespace,
            run_dir: Path) -> Result:
    started = time.monotonic()
    candidate = run_dir / "candidates" / f"seed-{seed:05d}-moves-{moves:06d}.json"
    candidate.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix=f"stripopt-{seed}-") as temp:
            worker_data = Path(temp) / "solver-data"
            shutil.copytree(args.solver_data, worker_data)
            # The harness reads projects/<id>.json. Always start from the
            # immutable imported project, never from another worker's output.
            project_target = worker_data / "projects" / f"{args.project_id}.json"
            project_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(args.project, project_target)

            cmd = [
                args.node, str(args.solver),
                "--data", str(worker_data),
                "--id", str(args.project_id),
                "--seed", str(seed),
                "--moves", str(moves),
                "--drilled", str(args.drilled),
                "--save", str(candidate),
            ]
            completed = subprocess.run(
                cmd, capture_output=True, text=True, timeout=args.timeout,
                cwd=ROOT,
            )
            if completed.returncode != 0:
                raise RuntimeError(
                    f"solver exit {completed.returncode}: "
                    f"{(completed.stderr or completed.stdout)[-1200:]}"
                )
            report = parse_solver_json(completed.stdout)
            if not candidate.is_file():
                raise RuntimeError("Solver reported completion but saved no candidate")
            board_data = json.loads(candidate.read_text())
            board = board_data.get("board", {})
            wires_list = board.get("wires", board_data.get("wires", []))
            cuts_list = board.get("cuts", board_data.get("cuts", []))
            if not isinstance(wires_list, list) or not isinstance(cuts_list, list):
                raise ValueError("Candidate wires/cuts are not arrays")

            wires = len(wires_list)
            cuts = len(cuts_list)
            quality = report.get("quality")
            conflicts = report.get("conflicts")
            rows = report.get("rows", board.get("rows"))
            cols = report.get("cols", board.get("cols"))
            price = report.get("price", report.get("score", report.get("E")))
            diagonals = count_diagonals(wires_list)

            reasons = []
            if quality != 0:
                reasons.append(f"quality={quality}")
            if conflicts != 0:
                reasons.append(f"conflicts={conflicts}")
            if diagonals is None:
                reasons.append("diagonal status could not be verified from wire schema")
            elif diagonals != 0:
                reasons.append(f"diagonal wires={diagonals}")
            if args.required_rows and rows != args.required_rows:
                reasons.append(f"rows={rows}, required {args.required_rows}")
            if args.required_cols and cols != args.required_cols:
                reasons.append(f"cols={cols}, required {args.required_cols}")

            valid = not reasons
            if not valid:
                candidate.unlink(missing_ok=True)
            return Result(seed, moves, "complete" if valid else "invalid",
                          valid, wires, cuts,
                          float(price) if isinstance(price, (int, float)) else None,
                          quality, conflicts, rows, cols, diagonals,
                          time.monotonic() - started,
                          str(candidate) if valid else None,
                          "; ".join(reasons) if reasons else None)
    except subprocess.TimeoutExpired:
        return Result(seed, moves, "timeout", False,
                      runtime_seconds=time.monotonic() - started,
                      error=f"Exceeded {args.timeout}s timeout")
    except Exception as exc:
        return Result(seed, moves, "failed", False,
                      runtime_seconds=time.monotonic() - started,
                      error=str(exc))


def rank_key(r: Result) -> tuple:
    # Tournament policy matching the historical Arena comparison:
    # fewer jumper wires, then fewer cuts, then lower price.
    return (r.wires if r.wires is not None else 10**9,
            r.cuts if r.cuts is not None else 10**9,
            r.price if r.price is not None else float("inf"))


def save_json(path: Path, value: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(tmp, path)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--project", type=Path, default=Path("tests/solver/projects/0.json"))
    p.add_argument("--solver-data", type=Path, default=Path("tests/solver"))
    p.add_argument("--solver", type=Path, default=Path("tests/solver/v5Solve.js"))
    p.add_argument("--project-id", type=int, default=0)
    p.add_argument("--node", default="node")
    p.add_argument("--drilled", type=int, choices=(0, 1), default=1)
    p.add_argument("--quick-seeds", type=int, default=1000)
    p.add_argument("--quick-start-seed", type=int, default=1)
    p.add_argument("--quick-moves", type=int, default=50000)
    p.add_argument("--advance", type=int, default=32,
                   help="Number of valid quick-sweep candidates entering knockout")
    p.add_argument("--knockout-moves", type=int, default=25000)
    p.add_argument("--finalists", type=int, default=4)
    p.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    p.add_argument("--timeout", type=int, default=900)
    p.add_argument("--required-rows", type=int, default=0)
    p.add_argument("--required-cols", type=int, default=0)
    p.add_argument("--output", type=Path, default=Path("tournament-runs"))
    args = p.parse_args()

    for attr in ("project", "solver_data", "solver"):
        path = getattr(args, attr)
        setattr(args, attr, path.resolve())
        if not path.exists():
            p.error(f"{attr} does not exist: {path}")
    if args.quick_seeds < 1 or args.advance < 2 or args.finalists < 1 or args.workers < 1:
        p.error("quick-seeds/workers/finalists must be positive and advance must be >= 2")

    run_id = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    run_dir = (args.output / run_id).resolve()
    run_dir.mkdir(parents=True, exist_ok=False)
    manifest = {
        "run_id": run_id, "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "project": str(args.project), "project_sha256": sha256(args.project),
        "solver": str(args.solver), "solver_data": str(args.solver_data),
        "settings": {k: str(v) if isinstance(v, Path) else v
                     for k, v in vars(args).items()},
        "results": [],
    }
    save_json(run_dir / "manifest.json", manifest)
    print(f"Run: {run_dir}")
    print(f"Input SHA256: {manifest['project_sha256']}")

    def stage(label: str, jobs: list[tuple[int, int]]) -> list[Result]:
        print(f"\n=== {label}: {len(jobs)} runs, {args.workers} workers ===", flush=True)
        results: list[Result] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(run_one, seed, moves, args, run_dir)
                       for seed, moves in jobs]
            for n, future in enumerate(concurrent.futures.as_completed(futures), 1):
                result = future.result()
                results.append(result)
                print(f"[{n:>4}/{len(jobs)}] seed={result.seed} moves={result.moves} "
                      f"{result.status} wires={result.wires} cuts={result.cuts} "
                      f"price={result.price} {result.error or ''}", flush=True)
                manifest["results"].append(asdict(result))
                save_json(run_dir / "manifest.json", manifest)
        return results

    quick = stage("QUICK SWEEP", [
        (seed, args.quick_moves)
        for seed in range(args.quick_start_seed,
                          args.quick_start_seed + args.quick_seeds)
    ])
    survivors = sorted((r for r in quick if r.valid), key=rank_key)[:args.advance]
    if not survivors:
        print("No valid quick-sweep candidates; stopping.")
        return 2
    print("\nQuick sweep leaders:")
    for r in survivors[:10]:
        print(f"  seed {r.seed}: {r.wires} wires, {r.cuts} cuts, price={r.price}")

    # Single-elimination bracket. Odd-sized rounds give the best-ranked
    # candidate a bye. Each pairing is re-solved at the same move budget.
    bracket = [r.seed for r in survivors]
    round_no = 1
    while len(bracket) > max(args.finalists, 1):
        print(f"\n=== KNOCKOUT ROUND {round_no}: {len(bracket)} seeds ===")
        jobs = [(seed, args.knockout_moves) for seed in bracket]
        round_results = stage(f"KNOCKOUT {round_no}", jobs)
        valid = {r.seed: r for r in round_results if r.valid}
        ordered = [s for s in bracket if s in valid]
        ordered.sort(key=lambda s: rank_key(valid[s]))
        next_round = []
        i = 0
        while i + 1 < len(ordered):
            a, b = ordered[i], ordered[i + 1]
            winner = min((a, b), key=lambda s: rank_key(valid[s]))
            next_round.append(winner)
            print(f"  {a} vs {b} -> {winner}")
            i += 2
        if i < len(ordered):
            next_round.append(ordered[i])
            print(f"  {ordered[i]} receives bye")
        bracket = next_round
        round_no += 1
        if not bracket:
            print("All knockout candidates failed validation.")
            return 3

    finalists = bracket[:args.finalists]
    endurance_budgets = list(range(5000, 200001, 5000))
    endurance = stage("FINALIST ENDURANCE (5k..200k)", [
        (seed, moves) for seed in finalists for moves in endurance_budgets
    ])
    best_by_seed: dict[int, Result] = {}
    for result in endurance:
        if result.valid and (result.seed not in best_by_seed or
                             rank_key(result) < rank_key(best_by_seed[result.seed])):
            best_by_seed[result.seed] = result
    ranked = sorted(best_by_seed.values(), key=rank_key)
    manifest["finalists"] = finalists
    manifest["champion"] = asdict(ranked[0]) if ranked else None
    manifest["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    save_json(run_dir / "manifest.json", manifest)
    if ranked:
        winner = ranked[0]
        champion_path = run_dir / "CHAMPION.json"
        shutil.copy2(winner.candidate, champion_path)
        save_json(run_dir / "leaderboard.json", [asdict(r) for r in ranked])
        print(f"\nCHAMPION: seed {winner.seed}, at {winner.moves} moves — "
              f"{winner.wires} wires, {winner.cuts} cuts, price={winner.price}")
        print(f"Saved: {champion_path}")
    else:
        print("\nNo valid finalist endurance runs.")
        return 4
    print(f"Manifest: {run_dir / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
