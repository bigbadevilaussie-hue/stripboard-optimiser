#!/usr/bin/env python3
"""Run Karl's native C solver over all legal Edge+Slide locked anchors.

Input is a READY project JSON (board dimensions already fixed and locked,
parts annotated with booleans locked/edge/slide). Route-Mate can export this
same schema. No new placement or routing solver is introduced.

The engine sees each slide candidate as an ordinary fixed lock; stops on the
first FULL strict-valid route. More than one slide part uses the Cartesian
product of its legal positions, never an arbitrary subset. Explicitly report
and retain all tried candidates when no route succeeds.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys

from native_edge_slide_positions import edge_slide_anchors

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "src" / "frontend"
NATIVE_EDGE_LIB = FRONTEND / "tests" / "solver" / "native" / "build" / "edge"
SOLVER = FRONTEND / "tests" / "solver" / "v5Solve.js"


def prepare_variation(project: dict, anchor_ids: list[str], locations: tuple[tuple[int, int], ...]) -> dict:
    if len(anchor_ids) != len(locations):
        raise ValueError("Slide positions/parts mismatch")
    trial = json.loads(json.dumps(project))
    indexed = {str(c["id"]): c for c in trial["components"]}
    for cid, (row, col) in zip(anchor_ids, locations):
        c = indexed[cid]
        if not (c.get("locked") is True and c.get("edge") is True and c.get("slide") is True):
            raise ValueError("Slide candidate lost Edge/Slide lock")
        c["boardPos"] = {"row": row, "col": col}
    return trial


def verify_candidate(source: dict, candidate: dict, saved: dict, result: dict, exitcode: int) -> list[str]:
    reasons = []
    board = source["board"]
    expected_size = (board["rows"], board["cols"])
    actual = saved.get("board", {})
    if (actual.get("rows"), actual.get("cols")) != expected_size:
        reasons.append("BOARD_DIMENSIONS_CHANGED")
    if not (actual.get("lockedRows") and actual.get("lockedCols")):
        reasons.append("BOARD_LOCKS_LOST")
    if not result.get("strictValid") or exitcode != 0:
        reasons.append("NOT_STRICT_VALID")
    original_components = {str(c["id"]): c for c in candidate["components"]}
    saved_components = {str(c["id"]): c for c in saved.get("components", [])}
    if original_components.keys() != saved_components.keys():
        reasons.append("COMPONENT_SET_CHANGED")
    for cid, original in original_components.items():
        if not original.get("locked") or original.get("boardPos") is None:
            continue
        final = saved_components.get(cid)
        if (not final or final.get("boardPos") != original.get("boardPos")
                or final.get("rotation", 0) != original.get("rotation", 0)
                or not final.get("locked")):
            reasons.append("LOCKED_PART_MOVED_" + cid)
        if final and (final.get("edge") != original.get("edge")
                      or final.get("slide") != original.get("slide")):
            reasons.append("EDGE_SLIDE_FLAGS_CHANGED_" + cid)
    if saved.get("nets") != source.get("nets") or saved.get("netAssignments") != source.get("netAssignments"):
        reasons.append("ELECTRICAL_INPUT_CHANGED")
    if saved.get("componentDefs") != source.get("componentDefs"):
        reasons.append("FOOTPRINT_DEFS_CHANGED")
    rows, cols = expected_size
    def inside(p):
        return (isinstance(p, dict) and type(p.get("row")) is int
                and type(p.get("col")) is int and
                0 <= p["row"] < rows and 0 <= p["col"] < cols)
    if any(not inside(c) for c in actual.get("cuts", [])):
        reasons.append("CUT_OUTSIDE_BOARD")
    if any(not inside(w.get("from")) or not inside(w.get("to"))
           for w in actual.get("wires", [])):
        reasons.append("WIRE_OUTSIDE_BOARD")
    return reasons


def run(project_path: Path, out: Path, seed: int, moves: int, timeout: int,
        drilled: bool, nostack: bool, routing: str) -> bool:
    source_bytes = project_path.read_bytes()
    source = json.loads(source_bytes)
    b = source["board"]
    if not b.get("lockedRows") or not b.get("lockedCols"):
        raise ValueError("Edge+Slide requires both physical dimensions locked")
    if not NATIVE_EDGE_LIB.joinpath("libv5decode.so").is_file():
        raise ValueError("Native edge library not built; use npm run build:native:edge")
    anchors = edge_slide_anchors(source)
    choices = [a.positions for a in anchors]
    count = 1
    for p in choices:
        count *= len(p)
    if out.exists() and any(out.iterdir()):
        raise ValueError("Output folder must be empty: " + str(out))
    out.mkdir(parents=True, exist_ok=True)
    input_dir = out / "input" / "projects"
    input_dir.mkdir(parents=True)
    sha = hashlib.sha256(source_bytes).hexdigest()
    (out / "source_sha256.txt").write_text(sha + "  " + str(project_path) + "\n")
    print("🔒 Physical board: {}×{} both locked; {} Edge+Slide components, {} candidate combinations".format(
        b["rows"], b["cols"], len(anchors), count), flush=True)
    for a in anchors:
        print("↔️ {} ({}) {} positions on {} edge; fixed other axis".format(
            a.label, a.component_id, len(a.positions), a.side), flush=True)
    env = os.environ.copy()
    env["V5_NATIVE_LIB_DIR"] = str(NATIVE_EDGE_LIB)
    env.pop("V5_NATIVE_ROUTE_LIB_DIR", None)
    tried = []
    winner = None
    for i, positions in enumerate(itertools.product(*choices), 1):
        trial = prepare_variation(source, [a.component_id for a in anchors], positions)
        (input_dir / "1.json").write_text(json.dumps(trial, ensure_ascii=False), encoding="utf-8")
        save = out / "candidate_{:05d}.json".format(i)
        cmd = ["node", str(SOLVER), "--data", str(out / "input"),
               "--id", "1", "--seed", str(seed), "--moves", str(moves),
               "--native", "1", "--strict", "1",
               "--drilled", "1" if drilled else "0",
               "--nostack", "1" if nostack else "0",
               "--routing-preference", routing, "--save", str(save)]
        try:
            proc = subprocess.run(cmd, cwd=FRONTEND, env=env,
                                  capture_output=True, text=True, timeout=timeout)
            code = proc.returncode
            lines = [v for v in proc.stdout.splitlines() if v.startswith("{")]
            result = json.loads(lines[-1]) if lines else {"error": "NO_CLI_OUTPUT"}
            stderr = proc.stderr
        except subprocess.TimeoutExpired:
            code, result, stderr = 124, {"error": "CLI_TIMEOUT"}, "CLI_TIMEOUT\n"
        (out / "candidate_{:05d}.stderr.txt".format(i)).write_text(stderr)
        saved = json.loads(save.read_text(encoding="utf-8")) if save.is_file() else None
        errors = verify_candidate(source, trial, saved, result, code) if saved is not None else ["SAVED_JSON_MISSING", "CLI_EXIT_" + str(code)]
        attempt = {
            "index": i, "locations": [
                {"componentId": a.component_id, "row": r, "col": c, "edge": a.side}
                for a, (r, c) in zip(anchors, positions)
            ],
            "pass": not errors, "errors": errors, "exit": code,
            "strictFailures": result.get("strictFailures", []),
            "rows": result.get("rows"), "cols": result.get("cols"),
            "wires": result.get("wires"), "cuts": result.get("cuts"),
            "quality": result.get("quality"), "sig": result.get("sig"),
        }
        tried.append(attempt)
        tag = "✅" if attempt["pass"] else "❌"
        detail = "STRICT PASS" if attempt["pass"] else ",".join(result.get("strictFailures") or errors)
        print("{} candidate {}/{} {}×{} | {} W / {} C | {}".format(
            tag, i, count, result.get("rows", "?"), result.get("cols", "?"),
            result.get("wires", "?"), result.get("cuts", "?"), detail[:260]), flush=True)
        if attempt["pass"]:
            winner = attempt
            break
    report = {
        "source": str(project_path), "sourceSha256": sha,
        "board": {"rows": b["rows"], "cols": b["cols"], "lockedRows": True, "lockedCols": True},
        "seed": seed, "moves": moves, "drilled": drilled, "nostack": nostack,
        "routing": routing, "candidateCount": count,
        "attemptsChecked": len(tried), "strictPassed": winner is not None,
        "winner": winner, "attempts": tried,
    }
    (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    if project_path.read_bytes() != source_bytes:
        raise AssertionError("Original project was unexpectedly modified")
    print("{} Native edge slide: {}/{} examined, {}".format(
        "🏆" if winner else "🛑", len(tried), count,
        "VERIFIED" if winner else "NO STRICT VALID LAYOUT"), flush=True)
    return winner is not None


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--project", required=True, type=Path, help="prepared JSON with locked Edge/Slide fields")
    p.add_argument("--out", required=True, type=Path, help="new empty results folder")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--moves", type=int, default=20000)
    p.add_argument("--timeout", type=int, default=900)
    p.add_argument("--drilled", action="store_true")
    p.add_argument("--nostack", action="store_true")
    p.add_argument("--routing", choices=["wires", "cuts"], default="wires")
    args = p.parse_args()
    if args.moves < 1 or args.timeout < 1 or args.seed < 0:
        p.error("invalid moves, timeout or seed")
    try:
        return 0 if run(args.project.expanduser().resolve(),
                        args.out.expanduser().resolve(), args.seed,
                        args.moves, args.timeout, args.drilled,
                        args.nostack, args.routing) else 2
    except (OSError, ValueError, KeyError, AssertionError) as exc:
        print("🛑 Native Edge+Slide setup error: " + str(exc), file=sys.stderr)
        return 64


if __name__ == "__main__":
    sys.exit(main())
