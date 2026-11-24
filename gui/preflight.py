"""Read-only Route-Mate JSON sniff/preflight for the native CLI GUI handover.

No solver, speed probe, renderer, subprocess, or output file is started here.
The exact caller project (including all locks and electrical IDs) is immutable.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from board_geometry import BUILTIN_DEFS
from collect import validate_project
from prepare.sanity.electrical import run_electrical_sanity


def preflight_project(source: Any, *, netlist_text: str | None = None) -> dict[str, Any]:
    """Return descriptive input validity. Never route, mutate source or write files."""
    project = validate_project(copy.deepcopy(source))
    board = project["board"]
    errors: list[str] = []
    warnings: list[str] = list(project.pop("_collectWarnings", []))

    rows, cols = board.get("rows"), board.get("cols")
    if any(type(value) is not int or value <= 0 for value in (rows, cols)):
        errors.append("board.rows and board.cols must be positive integer hole counts")

    for name in ("cuts", "wires"):
        if name in board and not isinstance(board[name], list):
            errors.append(f"board.{name} must be an array")

    assignments = project.get("netAssignments", [])
    components = project.get("components", [])
    defs = project.get("componentDefs", [])
    if defs is not None and not isinstance(defs, list):
        errors.append("componentDefs must be an array when provided")
        defs = []
    defs = defs or []
    ids = [str(d.get("id", "")) for d in defs if isinstance(d, dict)]
    duplicates = sorted({item for item in ids if item and ids.count(item) > 1})
    if duplicates:
        errors.extend(f"duplicate component definition ID: {item}" for item in duplicates)
    known_definitions = set(BUILTIN_DEFS) | set(ids)

    missing: list[str] = []
    for component in components:
        label = str(component.get("label") or component.get("id") or "(unnamed)")
        definition_id = component.get("defId") or component.get("componentDefId")
        override = component.get("footprintOverride")
        if (not isinstance(override, dict) and definition_id
                and str(definition_id) not in known_definitions):
            missing.append(f"{label} ({definition_id})")
    if missing:
        warnings.append(
            f"{len(missing)} component(s) lack an embedded/known footprint definition; "
            "import a matching KiCad .pretty library before solving"
        )

    sanity = run_electrical_sanity(project, netlist_text=netlist_text)
    errors.extend(sanity["errors"])
    warnings.extend(sanity["warnings"])
    if netlist_text is None:
        warnings.append("External .net connectivity comparison not performed (JSON only)")

    placed = sum(isinstance(c.get("boardPos"), dict) for c in components)
    offboard = sum(bool(c.get("boardExcluded") or c.get("offBoard"))
                   for c in components)
    locked = sum(c.get("locked") is True for c in components)
    edge = sum(c.get("edge") is True for c in components)
    slide = sum(c.get("slide") is True for c in components)
    rows_locked = source.get("lockedRows", board.get("lockedRows", True))
    cols_locked = source.get("lockedCols", board.get("lockedCols", True))
    if not isinstance(rows_locked, bool) or not isinstance(cols_locked, bool):
        errors.append("lockedRows and lockedCols must be booleans when supplied")

    return {
        "status": "FAIL" if errors else "PASS",
        "board": {"rows": rows, "cols": cols,
                  "lockedRows": rows_locked, "lockedCols": cols_locked},
        "components": len(components),
        "placed": placed,
        "off_board_or_excluded": offboard,
        "locked_components": locked,
        "edge": edge,
        "slide": slide,
        "nets": len(project["nets"]),
        "pin_assignments": len(assignments),
        "cuts": len(board.get("cuts", [])) if isinstance(board.get("cuts", []), list) else 0,
        "wires": len(board.get("wires", [])) if isinstance(board.get("wires", []), list) else 0,
        "missing_footprints": missing,
        "netlist_checked": netlist_text is not None,
        "electrical_sanity": sanity["status"],
        "errors": errors,
        "warnings": warnings,
        "execution": "STOPPED_BEFORE_PASS_1",
    }


def sniff_json(path: str | Path, *, netlist_path: str | Path | None = None) -> dict[str, Any]:
    """Read and inspect only. No modified project, campaign or sidecar is saved."""
    source_path = Path(path)
    raw = source_path.read_bytes()
    project = json.loads(raw.decode("utf-8"))
    netlist = Path(netlist_path).read_text(encoding="utf-8") if netlist_path else None
    report = preflight_project(project, netlist_text=netlist)
    report["source_path"] = str(source_path.resolve())
    report["source_sha256"] = hashlib.sha256(raw).hexdigest()
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only JSON sniff; never starts an optimiser")
    parser.add_argument("json_file", type=Path)
    parser.add_argument("--net", type=Path, help="Optional KiCad .net cross-check")
    args = parser.parse_args()
    try:
        report = sniff_json(args.json_file, netlist_path=args.net)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "FAIL", "errors": [str(exc)],
                          "execution": "STOPPED_BEFORE_PASS_1"}, indent=2))
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
