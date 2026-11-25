"""Read-only, 100-point JSON complexity rubric. No native decoder or seed searches."""
from collections import Counter
import hashlib
import json
from pathlib import Path

from board_geometry import BUILTIN_DEFS, resolve_definition
from placement_policy import is_off_board_component

VERSION = "SNIFF1"
THRESHOLD = 60.0
REFERENCE_HOLES = 24 * 56
# Historical strict survivor counts (2,000 trials per budget).
REFERENCES = {"Audio": {"10000": 170, "20000": 215},
              "Moto": {"10000": 15, "20000": 37}}


def _positive(value, name):
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def assess(project, drilled_only=False, stacking_allowed=True):
    """Score actual prepared geometry and rules; 0 easy to 100 difficult.

    Six weighted factors sum to 100 possible points. This is a heuristic,
    not 100 separate validations or a prediction of seed survival.
    """
    board = project["board"]
    rows = _positive(board["rows"], "rows")
    cols = _positive(board["cols"], "cols")
    # Both preferred modes are treated as an upper bound on available area,
    # never larger than the physical board. This is a pressure estimate only.
    rr = min(rows, _positive(board.get("wantedRows", rows), "preferred rows"))
    cc = min(cols, _positive(board.get("wantedCols", cols), "preferred columns"))
    holes = rr * cc
    components = project["components"]
    assignments = project["netAssignments"]
    on_board = [p for p in components if not is_off_board_component(p)]
    on_ids = {p["id"] for p in on_board}
    on_pins = sum(a["componentId"] in on_ids for a in assignments)
    net_sizes = Counter(a["netId"] for a in assignments)
    demand = sum(max(0, n - 1) for n in net_sizes.values())
    fanout = max(net_sizes.values(), default=0)
    definitions = {**BUILTIN_DEFS,
                   **{d["id"]: d for d in project.get("componentDefs", [])}}
    footprint_area = 0
    unknown = []
    locks = []
    lock_pressure = 0
    for part in on_board:
        definition = resolve_definition(part, definitions)
        if (definition is None or
                type(definition.get("width")) is not int or
                type(definition.get("height")) is not int or
                definition["width"] <= 0 or definition["height"] <= 0):
            unknown.append(part.get("label") or part["id"])
        else:
            footprint_area += definition["width"] * definition["height"]
        if part.get("locked") is True:
            mode = "Slide" if part.get("edge") and part.get("slide") else (
                "Edge" if part.get("edge") else "Fixed")
            lock_pressure += {"Fixed": 2, "Edge": 4, "Slide": 6}[mode]
            locks.append({"part": part.get("label") or part["id"], "mode": mode})
    def points(value, maximum, weight):
        return weight * min(1.0, max(0.0, value / maximum))
    # Larger boards ease density, not the absolute number of placement or
    # connection decisions. Keep a floor for density on very large boards.
    density_scale = max(0.5, REFERENCE_HOLES / holes)
    factors = {
        "placement": points(len(on_board), 32, 25),
        "pin_density": points(on_pins * density_scale, 100, 25),
        "net_demand": points(demand, 100, 20),
        "footprint_pressure": points(footprint_area / holes, 0.4, 15),
        "fanout": points(fanout, 25, 5),
        "constraints": min(10, lock_pressure + 2 * bool(drilled_only)
                           + 2 * (not stacking_allowed)),
    }
    raw = sum(factors.values())
    score = round(raw, 2)
    # Unresolved geometry must not silently bias the score towards easy.
    recommend = 20000 if raw >= THRESHOLD or unknown else 10000
    if unknown:
        reason = "Unresolved footprints; 20k is the conservative trial."
    elif recommend == 20000:
        reason = "Higher placement/routing pressure; 20k recommended."
    else:
        reason = "Lower placement/routing pressure; 10k recommended."
    return {
        "version": VERSION, "complexity_score": score, "threshold": THRESHOLD,
        "recommended_moves": recommend, "reason": reason,
        "factors": {key: round(value, 3) for key, value in factors.items()},
        "features": {"rows": rows, "cols": cols, "effective_rows": rr,
                     "effective_cols": cc, "on_board_parts": len(on_board),
                     "off_board_parts": len(components)-len(on_board),
                     "on_board_assignments": on_pins, "assignments": len(assignments),
                     "nets": len(net_sizes), "connection_demand": demand,
                     "max_fanout": fanout, "nominal_footprint_cells": footprint_area,
                     "unknown_footprints": unknown, "locks": locks,
                     "drilled_only": bool(drilled_only),
                     "stacking_allowed": bool(stacking_allowed)},
        "input_sha256": hashlib.sha256(json.dumps(project, sort_keys=True).encode()).hexdigest(),
        "reference_survivors": REFERENCES,
        "warning": "Heuristic calibrated on two circuit families; not a fit proof or survival forecast.",
    }


def save_report(workspace, result):
    """Save audit evidence separately from source JSON and campaign directories."""
    if workspace is None:
        return
    from tempfile import NamedTemporaryFile
    folder = Path(workspace) / "logs"
    path = folder / "json_sniff.json"
    if folder.is_symlink() or path.is_symlink():
        raise ValueError("Unsafe JSON sniff log path")
    folder.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=folder,
                                prefix=".json-sniff-", delete=False) as stream:
            temp = Path(stream.name)
            json.dump(result, stream, indent=2)
            stream.write("\n")
        temp.replace(path)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
