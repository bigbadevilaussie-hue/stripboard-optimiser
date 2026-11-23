#!/usr/bin/env python3
"""motoex locked-USB, 24x56 native CLI regression test.

Original master JSON is NEVER edited. Test input:
  - fixes the actual board at 24 rows x 56 columns, locked on both axes
  - keeps ONLY the USB fixed at its source position and rotation
  - clears EVERY other part's pre-existing on-board location and lock
  - retains off-board components, definitions, nets, assignments unchanged

The USB's 6x13 body intentionally extends two rows beyond the board's
bottom edge (rows 13..25, board rows 0..23). USB pins remain on the board.
A pass requires an exactly 24x56 strict-valid final board with USB unmoved.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "test-fixtures" / "masters" / "moto" / "motoex.json"
FRONTEND = ROOT / "src" / "frontend"
CLI = FRONTEND / "tests" / "solver" / "v5Solve.js"
USB_LABEL = "USB"
TARGET_ROWS = 24
TARGET_COLS = 56


def usb_source(master):
    parts = [c for c in master["components"] if c.get("label") == USB_LABEL]
    if len(parts) != 1:
        raise ValueError("Expected exactly one component labelled USB")
    usb = parts[0]
    defs = {d["id"]: d for d in master.get("componentDefs", [])}
    definition = defs.get(usb["defId"])
    if definition is None:
        raise ValueError("USB footprint definition missing from custom componentDefs")
    if not usb.get("locked") or usb.get("boardPos") is None:
        raise ValueError("Source USB must already be locked with a boardPos")
    if usb.get("rotation", 0) != 0:
        raise ValueError("USB test currently expects the 0-degree source footprint")
    pos = usb["boardPos"]
    if not all(isinstance(pos.get(k), int) for k in ("row", "col")):
        raise ValueError("USB board position must be integer holes")
    h, w = definition["height"], definition["width"]
    if w != 6 or h != 13 or pos != {"row": 13, "col": 47}:
        raise ValueError("USB fixture drift: expected footprint 6x13 at row 13, col 47")
    if pos["row"] + h <= TARGET_ROWS:
        raise ValueError("USB is no longer overhanging the test board")
    overhang_rows = pos["row"] + h - TARGET_ROWS
    if overhang_rows != 2:
        raise ValueError("Expected exactly two USB body rows past the bottom edge")
    if not definition.get("pins"):
        raise ValueError("USB footprint has no pins")
    for pin in definition["pins"]:
        row = pos["row"] + pin["offsetRow"]
        col = pos["col"] + pin["offsetCol"]
        if not (0 <= row < TARGET_ROWS and 0 <= col < TARGET_COLS):
            raise ValueError("USB electrical pin outside the board: " + str(pin))
    return usb, definition, overhang_rows


def prepare(master):
    """Return an isolated input without changing the original source."""
    usb, _, _ = usb_source(master)
    data = json.loads(json.dumps(master))
    data["board"].update(rows=TARGET_ROWS, cols=TARGET_COLS,
                         lockedRows=True, lockedCols=True, cuts=[], wires=[])
    for c in data["components"]:
        if c["id"] == usb["id"]:
            continue
        # Existing on-board positions are NOT test constraints, including the
        # other pre-locked TVS. Keep offBoard, net connectivity, rotation and
        # footprint definitions; the CLI already resets movable rotations.
        c.pop("locked", None)
        c["boardPos"] = None
        c.pop("flexibleEndPos", None)
    usb2 = next(c for c in data["components"] if c["id"] == usb["id"])
    if usb2 != usb:
        raise AssertionError("USB source fields changed during preparation")
    if sum(bool(c.get("locked") and c.get("boardPos")) for c in data["components"]) != 1:
        raise AssertionError("Test must contain ONLY the one locked USB")
    if len(data["netAssignments"]) != len(master["netAssignments"]) or data["nets"] != master["nets"]:
        raise AssertionError("Preparation modified electrical connectivity")
    return data


def validate_saved(source, prepared, saved, result):
    errors = []
    board = saved.get("board", {})
    if (board.get("rows"), board.get("cols")) != (TARGET_ROWS, TARGET_COLS):
        errors.append("BOARD_NOT_24x56: returned {}x{}".format(board.get("rows"), board.get("cols")))
    if not board.get("lockedRows") or not board.get("lockedCols"):
        errors.append("BOARD_LOCKS_LOST")
    originals = {c["id"]: c for c in source["components"]}
    actuals = {c["id"]: c for c in saved.get("components", [])}
    expected = next(c for c in prepared["components"] if c.get("label") == USB_LABEL)
    got = actuals.get(expected["id"])
    if got is None:
        errors.append("USB_MISSING")
    else:
        if got.get("boardPos") != expected["boardPos"]:
            errors.append("USB_MOVED: {} -> {}".format(expected["boardPos"], got.get("boardPos")))
        if got.get("rotation", 0) != expected.get("rotation", 0):
            errors.append("USB_ROTATED")
        if got.get("locked") is not True:
            errors.append("USB_UNLOCKED")
    for cid, original in originals.items():
        if cid == expected["id"]:
            continue
        other = actuals.get(cid)
        if other is None:
            errors.append("COMPONENT_MISSING: " + str(original.get("label")))
        elif other.get("locked") and other.get("boardPos"):
            errors.append("UNEXPECTED_LOCK: " + str(original.get("label")))
    if saved.get("nets") != source["nets"] or saved.get("netAssignments") != source["netAssignments"]:
        errors.append("NETS_OR_ASSIGNMENTS_CHANGED")
    if saved.get("componentDefs") != source.get("componentDefs"):
        errors.append("FOOTPRINTS_CHANGED")
    if not result.get("strictValid", False):
        errors.append("STRICT_NOT_VALID: " + ",".join(result.get("strictFailures") or []))
    if result.get("rows") != TARGET_ROWS or result.get("cols") != TARGET_COLS:
        errors.append("CLI_DIMENSIONS_MISMATCH")
    return errors


def cli_result(stdout):
    lines = [x for x in stdout.splitlines() if x.startswith("{")]
    if not lines:
        raise ValueError("Missing JSON result from native CLI stdout")
    return json.loads(lines[-1])


def run(master_path, out, seeds, moves, use_fast, drilled, nostack, routing, timeout):
    if out.exists() and any(out.iterdir()):
        raise ValueError("Output folder is not empty; choose a fresh --out")
    if not CLI.is_file():
        raise ValueError("CLI missing: " + str(CLI))
    source_bytes = master_path.read_bytes()
    source = json.loads(source_bytes)
    prepared = prepare(source)
    _, definition, overhang = usb_source(source)
    out.mkdir(parents=True, exist_ok=True)
    inputs = out / "input" / "projects"
    inputs.mkdir(parents=True)
    (inputs / "1.json").write_text(json.dumps(prepared, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "source_sha256.txt").write_text(hashlib.sha256(source_bytes).hexdigest() + "  " + str(master_path) + "\n")
    print("🔎 MOTOEX source: {} | SHA256 {}".format(master_path, hashlib.sha256(source_bytes).hexdigest()), flush=True)
    print("🔒 USB: fixed at (13,47), rotation 0, footprint {}x{}; overhang {} body rows".format(
        definition["width"], definition["height"], overhang), flush=True)
    print("📐 Board: 24x56, BOTH dimensions locked; other components UNLOCKED and position-cleared", flush=True)
    print("🧷 {} parts / {} assignments / {} off-board components".format(
        len(prepared["components"]), len(prepared["netAssignments"]),
        sum(bool(c.get("offBoard")) for c in prepared["components"])), flush=True)
    env = os.environ.copy()
    env.pop("V5_NATIVE_LIB_DIR", None)
    env.pop("V5_NATIVE_ROUTE_LIB_DIR", None)
    if use_fast:
        libdir = FRONTEND / "tests" / "solver" / "native" / "build" / "fast"
        if not (libdir / "libv5decode.so").is_file():
            raise ValueError("Fast library missing; run (cd src/frontend && npm run build:native:fast)")
        env["V5_NATIVE_LIB_DIR"] = str(libdir)
    report = []
    for seed in seeds:
        saved_path = out / "motoex_seed_{}.json".format(seed)
        cmd = ["node", str(CLI), "--data", str(out / "input"), "--id", "1",
               "--seed", str(seed), "--moves", str(moves), "--native", "1",
               "--strict", "1", "--drilled", str(int(drilled)), "--nostack", str(int(nostack)),
               "--routing-preference", routing, "--save", str(saved_path)]
        try:
            proc = subprocess.run(cmd, cwd=FRONTEND, env=env, text=True,
                                  capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired as err:
            entry = {"seed": seed, "pass": False, "exit": None, "errors": ["CLI_TIMEOUT"], "error": str(err)}
            report.append(entry)
            print("❌ SEED {} timed out".format(seed), flush=True)
            continue
        (out / "motoex_seed_{}.stderr.txt".format(seed)).write_text(proc.stderr, encoding="utf-8")
        entry = {"seed": seed, "exit": proc.returncode, "errors": [], "pass": False}
        try:
            result = cli_result(proc.stdout)
            entry.update({"sig": result.get("sig"), "wires": result.get("wires"),
                          "cuts": result.get("cuts"), "rows": result.get("rows"),
                          "cols": result.get("cols"), "strictFailures": result.get("strictFailures", []),
                          "quality": result.get("quality")})
            if not saved_path.is_file():
                entry["errors"].append("SAVED_JSON_MISSING")
            else:
                saved = json.loads(saved_path.read_text(encoding="utf-8"))
                entry["errors"].extend(validate_saved(source, prepared, saved, result))
            if proc.returncode not in (0, 2):
                entry["errors"].append("CLI_ERROR_EXIT_{}".format(proc.returncode))
            if proc.returncode == 2:
                entry["errors"].append("CLI_STRICT_REJECTED")
        except (ValueError, KeyError, TypeError) as err:
            entry["errors"].append("OUTPUT_ERROR: " + str(err))
        entry["pass"] = not entry["errors"]
        report.append(entry)
        print("{} SEED {} | {}x{} | {} wires / {} cuts | {}".format(
            "✅" if entry["pass"] else "❌", seed, entry.get("rows", "?"),
            entry.get("cols", "?"), entry.get("wires", "?"), entry.get("cuts", "?"),
            "PASS" if entry["pass"] else "; ".join(entry["errors"])), flush=True)
    (out / "results.json").write_text(json.dumps({
        "source": str(master_path), "sourceSha256": hashlib.sha256(source_bytes).hexdigest(),
        "settings": {"board": "24x56 locked", "onlyLockedPart": "USB", "moves": moves,
                     "fast": use_fast, "drilled": drilled, "nostack": nostack,
                     "routing": routing, "seeds": seeds},
        "results": report}, indent=2) + "\n", encoding="utf-8")
    passed = sum(x["pass"] for x in report)
    print("🏁 MOTOEX: {} / {} passed | details {}".format(passed, len(report), out / "results.json"), flush=True)
    return passed == len(report)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--master", type=Path, default=MASTER)
    p.add_argument("--out", type=Path, default=Path("/tmp/stripboard_motoex_locked_usb"))
    p.add_argument("--seed-start", type=int, default=1)
    p.add_argument("--seeds", type=int, default=3)
    p.add_argument("--moves", type=int, default=20000)
    p.add_argument("--fast", action="store_true", help="Use optional fast native decoder, unchanged router")
    p.add_argument("--drilled", action="store_true", help="Forbid knife cuts")
    p.add_argument("--nostack", action="store_true", help="Forbid stacked jumper wires")
    p.add_argument("--routing", choices=["wires", "cuts"], default="wires")
    p.add_argument("--timeout", type=int, default=900, help="Per-seed process timeout in seconds")
    args = p.parse_args()
    if args.seeds < 1 or args.moves < 1 or args.timeout < 1 or args.seed_start < 0:
        p.error("seeds, moves, timeout must be positive; seed-start must be nonnegative")
    try:
        ok = run(args.master.expanduser().resolve(), args.out.expanduser().resolve(),
                 list(range(args.seed_start, args.seed_start + args.seeds)),
                 args.moves, args.fast, args.drilled, args.nostack, args.routing, args.timeout)
    except (ValueError, OSError, KeyError) as exc:
        print("🛑 MOTOEX test setup failed: " + str(exc), file=sys.stderr)
        return 64
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
