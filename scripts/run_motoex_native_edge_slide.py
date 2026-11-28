#!/usr/bin/env python3
"""Native Karl decoder Edge / Slide feasibility search for MOTOEX.

A physical PCB is fixed at 24x56. Its USB charger has a 6x13 package at
(row 13, col 47), with the final two rows of plastic BELOW the PCB. Both
electrical pins remain on board.

Edge yes: allow ONLY the USB's external body to overhang. Keep its full
on-board body collision footprint, fixed position, rotation, and pin checks.
Slide yes: try 51 USB columns (0..50) along this SAME bottom edge,
nearest the original column first. Each candidate is a normal full native
Karl solve, with USB fully locked at that trial position. Stop at the FIRST
strictly verified route, or report all 51 failures. No second placement
solver is involved.

The source JSON, baseline native decoder, router, WRs and WASM are untouched.
Requires opt-in native library built by npm run build:native:edge.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

# Avoid test discovery importing scripts/tests/test_motoex_usb_lock.py in
# place of our actual scripts/test_motoex_usb_lock.py contract runner.
_CONTRACT_PATH = Path(__file__).resolve().with_name("test_motoex_usb_lock.py")
_SPEC = importlib.util.spec_from_file_location("motoex_usb_lock_contract", _CONTRACT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError("Cannot load MOTOEX source/strict contract")
contract = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(contract)

from native_edge_slide_positions import anchors_for_component

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "src" / "frontend"
EDGE_LIB = FRONTEND / "tests" / "solver" / "native" / "build"  # Canonical Dave
DEFAULT_OUT = Path.home() / "Desktop" / "motoex_edge_slide_native_v1"


def bool_option(s: str) -> bool:
    if s.lower() in ("yes", "true", "1", "on"):
        return True
    if s.lower() in ("no", "false", "0", "off"):
        return False
    raise argparse.ArgumentTypeError("expected yes or no")


def slide_positions(usb: dict, definition: dict, rows: int, cols: int, slide: bool) -> list[int]:
    """The reusable generic Edge+Slide geometry produces 51 MOTOEX columns."""
    probe = {**usb, "edge": True, "slide": True}
    anchors = anchors_for_component(
        probe, definition,
        {"rows": rows, "cols": cols, "lockedRows": True, "lockedCols": True},
    )
    if anchors.side != "bottom" or any(row != usb["boardPos"]["row"] for row, _ in anchors.positions):
        raise ValueError("MOTOEX USB must slide along its ORIGINAL bottom edge")
    positions = [col for _, col in anchors.positions]
    if len(positions) != 51 or set(positions) != set(range(51)) or positions[0] != 47:
        raise ValueError("MOTOEX must have exactly 51 legal bottom-edge positions")
    return positions if slide else [usb["boardPos"]["col"]]

def prepare_trial(original: dict, edge: bool, slide: bool, col: int) -> dict:
    if slide and not edge:
        raise ValueError("Slide=yes requires Edge=yes")
    data = contract.prepare(original)
    usb = next(c for c in data["components"] if c["label"] == "USB")
    usb["boardPos"] = {"row": 13, "col": col}
    usb["locked"] = True
    usb["edge"] = edge
    usb["slide"] = slide
    if not 0 <= col <= 50:
        raise ValueError("USB column must be 0..50")
    # The *real* electrical pins must remain on board at EVERY candidate.
    raw, definition, _ = contract.usb_source(original)
    for p in definition["pins"]:
        r, c = 13 + p["offsetRow"], col + p["offsetCol"]
        if not (0 <= r < 24 and 0 <= c < 56):
            raise ValueError("USB pin outside board for column {}".format(col))
    if data["board"]["rows"] != 24 or data["board"]["cols"] != 56:
        raise AssertionError("fixture board dimensions drifted")
    if any(c.get("locked") for c in data["components"] if c["id"] != raw["id"]):
        raise AssertionError("only USB may remain locked")
    return data


def check_trial(original: dict, prepared: dict, saved: dict, result: dict, exitcode: int) -> list[str]:
    errors = contract.validate_saved(original, prepared, saved, result)
    if exitcode != 0:
        errors.append("STRICT_EXIT_{}".format(exitcode))
    usb = next((c for c in saved.get("components", []) if c.get("label") == "USB"), None)
    expected = next(c for c in prepared["components"] if c.get("label") == "USB")
    if usb is None or usb.get("edge") is not expected["edge"] or usb.get("slide") is not expected["slide"]:
        errors.append("EDGE_SLIDE_FLAGS_CHANGED")
    if usb is not None and usb.get("boardPos") != expected["boardPos"]:
        errors.append("SLIDE_ANCHOR_CHANGED_WITHIN_NATIVE_SOLVE")
    # Explicitly fail on off-PCB copper, even if a future CLI omits the
    # corresponding strict failure code by accident.
    b = saved.get("board", {})
    rows, cols = b.get("rows"), b.get("cols")
    if rows != 24 or cols != 56:
        return errors  # 24x56 is already flagged; avoid ambiguous coordinates
    def inside(p):
        return isinstance(p, dict) and type(p.get("row")) is int and type(p.get("col")) is int and 0 <= p["row"] < rows and 0 <= p["col"] < cols
    if any(not inside(k) for k in b.get("cuts", [])):
        errors.append("OUTSIDE_CUT")
    if any(not inside(w.get("from")) or not inside(w.get("to")) for w in b.get("wires", [])):
        errors.append("OUTSIDE_WIRE")
    return errors


def run(args) -> bool:
    original_bytes = contract.MASTER.read_bytes()
    original = json.loads(original_bytes)
    usb, definition, overhang = contract.usb_source(original)
    columns = slide_positions(usb, definition, 24, 56, args.slide)
    if args.slide and not args.edge:
        raise ValueError("Slide=yes requires Edge=yes")
    if args.column is not None:
        if not args.edge or not args.slide:
            raise ValueError("--column requires --edge yes --slide yes")
        if args.column not in columns:
            raise ValueError("--column must be a legal USB slide column, 0..50")
        columns = [args.column]
    if not EDGE_LIB.joinpath("libv5decode.so").is_file():
        raise ValueError("Native edge decoder missing: (cd src/frontend && npm run build:native:edge)")
    output = args.out.expanduser().resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output directory already exists and is not empty: " + str(output))
    output.mkdir(parents=True, exist_ok=True)
    project_dir = output / "input" / "projects"
    project_dir.mkdir(parents=True)
    sha = hashlib.sha256(original_bytes).hexdigest()
    (output / "source_sha256.txt").write_text(sha + "  " + str(contract.MASTER) + "\n")
    env = os.environ.copy()
    env["V5_NATIVE_LIB_DIR"] = str(EDGE_LIB)
    env.pop("V5_NATIVE_ROUTE_LIB_DIR", None)

    print("🔬 MOTOEX Edge={} Slide={} | physical 24x56 LOCKED | USB body overhang {} rows".format(
        "yes" if args.edge else "no", "yes" if args.slide else "no", overhang), flush=True)
    print("🧷 45 components, 123 assignments; USB=(13,47), rotation=0; OTHER LOCKS IGNORED", flush=True)
    print("↔️ Edge positions: {} | {}".format(len(columns), columns if args.slide else "fixed 47"), flush=True)
    print("🛡️ Hard pass: 24x56 + USB lock + strict electrical/geometry + vertical wires + drilled + no-stack", flush=True)
    print("🔄 Generic drilled rotation domain: {}".format("ON" if args.drill_domain else "OFF"), flush=True)
    print("🛠️ Verified fixed-board wire polish: {}".format("ON" if args.wire_polish else "OFF"), flush=True)
    results = []
    solved = 0
    for seed in range(args.seed_start, args.seed_start + args.seeds):
        trials = []
        winner = None
        for n, col in enumerate(columns, 1):
            prepared = prepare_trial(original, args.edge, args.slide, col)
            (project_dir / "1.json").write_text(json.dumps(prepared, ensure_ascii=False), encoding="utf-8")
            saved_path = output / "motoex_seed{}_usb_col{}.json".format(seed, col)
            cmd = ["node", str(contract.CLI), "--data", str(output / "input"),
                   "--id", "1", "--seed", str(seed), "--moves", str(args.moves),
                   "--native", "1", "--strict", "1", "--drilled", "1",
                   "--nostack", "1", "--drill-domain", "1" if args.drill_domain else "0",
                   "--wire-polish", "1" if args.wire_polish else "0",
                   "--routing-preference", args.routing,
                   "--save", str(saved_path)]
            try:
                process = subprocess.run(cmd, cwd=FRONTEND, env=env, capture_output=True,
                                         text=True, timeout=args.timeout)
                stdout, stderr, rc = process.stdout, process.stderr, process.returncode
            except subprocess.TimeoutExpired:
                stdout, stderr, rc = "", "TIMEOUT", 124
            (output / "motoex_seed{}_col{}.stderr.txt".format(seed, col)).write_text(stderr, encoding="utf-8")
            attempt = {"index": n, "seed": seed, "column": col, "exit": rc, "ok": False}
            try:
                result = contract.cli_result(stdout)
                attempt.update({"rows": result.get("rows"), "cols": result.get("cols"),
                                "quality": result.get("quality"), "wires": result.get("wires"),
                                "cuts": result.get("cuts"), "strictFailures": result.get("strictFailures", []),
                                "sig": result.get("sig"),
                                "unsolvedReason": result.get("unsolvedReason"),
                                "firstFeasibleMove": result.get("firstFeasibleMove"),
                                "firstFeasibleMs": result.get("firstFeasibleMs"),
                                "incompleteNets": result.get("incompleteNets", []),
                                "invalidDrilledOrientations": result.get("invalidDrilledOrientations", []),
                                "knifeCuts": result.get("knifeCuts", []),
                                "wirePolish": result.get("wirePolish"),
                                "wireViolations": result.get("wireViolations", [])})
                if saved_path.exists():
                    saved = json.loads(saved_path.read_text(encoding="utf-8"))
                    problems = check_trial(original, prepared, saved, result, rc)
                else:
                    problems = ["SAVED_LAYOUT_MISSING", "EXIT_{}".format(rc)]
                attempt["errors"] = problems
                attempt["ok"] = not problems
            except (ValueError, TypeError, KeyError) as exc:
                attempt["errors"] = ["CLI_OUTPUT_ERROR: " + str(exc), "EXIT_{}".format(rc)]
            trials.append(attempt)
            reasons = attempt["errors"]
            first_move = attempt.get("firstFeasibleMove")
            first_ms = attempt.get("firstFeasibleMs")
            feasibility = ("first fit move={} at {:.0f}ms".format(first_move, first_ms)
                           if first_move is not None and isinstance(first_ms, (int, float))
                           else "first fit: NEVER")
            status = ("UNSOLVED: " + attempt["unsolvedReason"] if attempt.get("unsolvedReason")
                      else "STRICT PASS" if attempt["ok"]
                      else ", ".join(attempt.get("strictFailures") or reasons[:3])[:220])
            print("{} SEED {} USB col {:2d} ({}/{}) | {}x{} | {} W / {} C | {} | {}".format(
                "✅" if attempt["ok"] else "❌", seed, col, n, len(columns),
                attempt.get("rows", "?"), attempt.get("cols", "?"),
                attempt.get("wires", "?"), attempt.get("cuts", "?"),
                status, feasibility), flush=True)
            for net in attempt.get("incompleteNets", []):
                print("   🔌 INCOMPLETE NET {}: {}".format(
                    net.get("name", net.get("id", "?")),
                    "; ".join(" + ".join(p.get("componentLabel", "?") + "." +
                                                  p.get("pinName", "?") for p in group)
                              for group in net.get("groups", []))), flush=True)
            for part in attempt.get("invalidDrilledOrientations", []):
                print("   🚫 DRILLED ROTATION {} @ {}° | {}".format(
                    part.get("component", "?"), part.get("rotation", "?"),
                    "; ".join("{} vs {}".format(*(edge.get("nets") or ["?", "?"]))
                              for edge in part.get("adjacent", []))), flush=True)
            if attempt.get("wirePolish"):
                stats = attempt["wirePolish"]
                print("   🛠️ POLISH {} accepted / {} tested | {} wires moved | {} knives drilled".format(
                    stats.get("accepted"), stats.get("tried"),
                    stats.get("columnsMoved"), stats.get("drillsRecovered")), flush=True)
                print("      BEFORE {} | AFTER {}".format(
                    stats.get("before"), stats.get("after")), flush=True)
            for cut in attempt.get("knifeCuts", []):
                flanks = cut.get("flanks", [])
                near = "{} / {}".format(
                    (cut.get("nearestLeft") or {}).get("net", "BOARD EDGE"),
                    (cut.get("nearestRight") or {}).get("net", "BOARD EDGE"))
                flanks_text = " ".join("{}:{}{}".format(
                    f.get("col"), "possible drill" if f.get("basicDrillCandidate") else "BLOCKED",
                    " wires=" + str(f.get("wireEndpoints")) if f.get("wireEndpoints") else "")
                    for f in flanks)
                print("   🔪 KNIFE row {} between cols {}-{} | nets {} | {} | {}".format(
                    cut["row"], cut["col"], cut["col"] + 1, near,
                    "FORCED adjacent differing-net pins" if cut.get("forcedByAdjacentPins")
                    else "not forced by adjacent pin pair",
                    flanks_text), flush=True)
            for wire in attempt.get("wireViolations", []):
                print("   ⚠️ WIRE {} [{}] {} -> {} | {}{}".format(
                    wire.get("wire"), "/".join(wire.get("netNames") or ["UNRESOLVED"]),
                    wire.get("from"), wire.get("to"), ",".join(wire.get("violations") or []),
                    " | crosses " + ",".join(wire["crossingComponents"])
                    if wire.get("crossingComponents") else ""), flush=True)
                if wire.get("stackedWith"):
                    print("      🧷 STACK PARTNERS: {}".format(
                        ", ".join("WIRE " + str(i) for i in wire["stackedWith"])), flush=True)
            if attempt["ok"]:
                winner = col
                solved += 1
                break
        failed_codes = Counter(
            code for x in trials for code in x.get("strictFailures", [])
        )
        results.append({"seed": seed, "winnerCol": winner, "positionsTested": len(trials),
                        "positionsAvailable": len(columns),
                        "strictPass": winner is not None, "failureCodes": dict(failed_codes),
                        "trials": trials})
        print("{} SEED {} | {} after {} / {} USB positions".format(
            "🏆" if winner is not None else "🛑", seed,
            "VERIFIED col=" + str(winner) if winner is not None else "NO STRICT ROUTE",
            len(trials), len(columns)), flush=True)
    (output / "results.json").write_text(json.dumps({
        "originalSha256": sha, "originalMaster": str(contract.MASTER),
        "board": {"rows": 24, "cols": 56, "lockedRows": True, "lockedCols": True},
        "USB": {"id": usb["id"], "edge": args.edge, "slide": args.slide,
                "row": 13, "originalCol": 47, "overhangRows": overhang},
        "moves": args.moves, "routing": args.routing,
        "drilledRotationDomain": args.drill_domain,
        "wirePolish": args.wire_polish,
        "results": results
    }, indent=2) + "\n")
    print("🏁 MOTOEX native EDGE/SLIDE: {}/{} strict PASS | {}".format(
        solved, args.seeds, output / "results.json"), flush=True)
    if contract.MASTER.read_bytes() != original_bytes:
        raise AssertionError("Original master changed during edge sweep")
    return solved == args.seeds


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--edge", type=bool_option, default=True, metavar="yes/no")
    p.add_argument("--slide", type=bool_option, default=False, metavar="yes/no")
    p.add_argument("--column", type=int, default=None, help="diagnose one legal slide column (0..50); omit to sweep all 51")
    p.add_argument("--seed-start", type=int, default=1)
    p.add_argument("--seeds", type=int, default=1)
    p.add_argument("--moves", type=int, default=20000)
    p.add_argument("--routing", choices=["wires", "cuts"], default="wires")
    p.add_argument("--drill-domain", type=bool_option, default=True, metavar="yes/no",
                   help="enable or disable generic drill-only rotation-domain pruning for A/B comparison")
    p.add_argument("--wire-polish", type=bool_option, default=False, metavar="yes/no",
                   help="run verified wire-column and drilled-cut polish after native finishing")
    p.add_argument("--timeout", type=int, default=600, help="seconds per candidate")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = p.parse_args()
    if args.moves < 1 or args.seeds < 1 or args.seed_start < 0 or args.timeout < 1:
        p.error("moves, seeds, timeout positive, seed-start nonnegative")
    try:
        passed = run(args)
    except (OSError, ValueError, AssertionError, KeyError) as exc:
        print("🛑 EDGE/SLIDE setup error: " + str(exc), file=sys.stderr)
        return 64
    return 0 if passed else 2


if __name__ == "__main__":
    sys.exit(main())
