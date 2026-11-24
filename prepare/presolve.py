"""Read-only PREPARE intelligence for every component and advisory board sizing.

No placement, routing, physical-clearance or source-project mutation occurs here.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from board_geometry import BUILTIN_DEFS, resolve_definition, component_geometry
from pipeline.contracts import project_sha256
from placement_policy import is_off_board_component

SCHEMA = "route-mate-presolve"
VERSION = 1


def _pack_rectangles(rectangles: list[list[tuple[int, int]]], rows: int, cols: int) -> bool:
    """Deterministic first-fit packing of conservative footprint rectangles.

    This is a sufficient placement-only witness, NOT a physical routing proof.
    """
    occupied: set[tuple[int, int]] = set()
    order = sorted(rectangles, key=lambda options: -min(r * c for r, c in options))
    for options in order:
        placed = False
        for height, width in sorted(set(options), key=lambda pair: (pair[0] * pair[1], pair)):
            if height > rows or width > cols:
                continue
            for top in range(rows - height + 1):
                for left in range(cols - width + 1):
                    cells = {(r, c) for r in range(top, top + height)
                             for c in range(left, left + width)}
                    if not occupied.intersection(cells):
                        occupied.update(cells)
                        placed = True
                        break
                if placed:
                    break
            if placed:
                break
        if not placed:
            return False
    return True


def _placement_candidate(records: list[dict[str, Any]], board: dict[str, Any]) -> dict[str, Any]:
    """Find a no-padding rectangle-packing witness when dimensions may change.

    Existing locked axes are hard limits. No wire, cut or clearance allowances
    are guessed. Failure to pack does not establish impossibility.
    """
    if any(not record["geometry"]["resolved"] and not record["off_board"] for record in records):
        return {"status": "unknown_unresolved_footprints", "rows": None, "cols": None}
    rectangles = [
        [(o["span_rows"], o["span_cols"]) for o in record["geometry"]["orientations"]]
        for record in records if not record["off_board"]
    ]
    if not rectangles:
        return {"status": "no_on_board_components", "rows": None, "cols": None}
    source_rows, source_cols = board.get("rows"), board.get("cols")
    lock_rows, lock_cols = bool(board.get("lockedRows")), bool(board.get("lockedCols"))
    if lock_rows and (type(source_rows) is not int or source_rows < 1):
        return {"status": "invalid_locked_rows", "rows": None, "cols": None}
    if lock_cols and (type(source_cols) is not int or source_cols < 1):
        return {"status": "invalid_locked_cols", "rows": None, "cols": None}
    # The sum of maximum dimensions provides a finite packing search ceiling,
    # not a requested allowance or a recommended size.
    max_rows = sum(max(r for r, _ in options) for options in rectangles)
    max_cols = sum(max(c for _, c in options) for options in rectangles)
    min_rows = max(min(r for r, _ in options) for options in rectangles)
    min_cols = max(min(c for _, c in options) for options in rectangles)
    row_choices = [source_rows] if lock_rows else range(min_rows, max_rows + 1)
    col_choices = [source_cols] if lock_cols else range(min_cols, max_cols + 1)
    candidates = sorted(
        ((r, c) for r in row_choices for c in col_choices),
        key=lambda pair: (pair[0] * pair[1], pair[0], pair[1]),
    )
    for rows, cols in candidates:
        if _pack_rectangles(rectangles, rows, cols):
            return {"status": "placement_only_candidate", "rows": rows, "cols": cols}
    return {"status": "no_first_fit_witness", "rows": None, "cols": None}


def _orientation_intelligence(pins: list[dict[str, Any]], body: list[tuple[int, int]],
                              net_by_pin: dict[str, str]) -> dict[str, Any]:
    """Evidence-based stripboard topology hints, never a routing certificate.

    Copper runs along columns. A vertical top-side jumper cannot traverse a
    body cell. Do not confuse body obstruction with underside copper isolation.
    """
    pin_cells = {(int(p["row"]), int(p["col"])) for p in pins}
    body_cells = set(body)
    columns: dict[int, set[int]] = defaultdict(set)
    row_nets: dict[int, set[str]] = defaultdict(set)
    for p in pins:
        row, col = int(p["row"]), int(p["col"])
        columns[col].add(row)
        net = net_by_pin.get(str(p["id"]))
        if net:
            row_nets[row].add(net)
    # A pair of populated pin columns with body occupancy between them.
    pin_cols = sorted(columns)
    dual_row = (len(pin_cols) == 2 and len(columns[pin_cols[0]]) >= 2
                and len(columns[pin_cols[1]]) >= 2
                and any(pin_cols[0] < c < pin_cols[1] for _, c in body_cells))
    # Each strip carrying N distinct assigned nets needs at least N-1
    # isolating boundaries, but their feasibility is not established here.
    cut_lower_bound = sum(max(0, len(nets) - 1) for nets in row_nets.values())
    # For vertical jumpers, a body cell in a column obstructs that lane.
    obstructed_columns = sorted({c for _, c in body_cells})
    return {
        "topology": "dual_row_module" if dual_row else "other",
        "pin_columns": pin_cols,
        "pin_count": len(pins),
        "body_cell_count": len(body_cells),
        "vertical_jumper_obstructed_columns": obstructed_columns,
        "strip_cut_lower_bound": cut_lower_bound,
        "routing_feasibility": "unverified",
    }


def analyse_project(project: dict[str, Any]) -> dict[str, Any]:
    """Return uniform per-component records and a non-certifying board estimate."""
    board = project.get("board", {})
    if not isinstance(board, dict):
        raise ValueError("board must be an object")
    defs = {**BUILTIN_DEFS, **{
        str(d["id"]): d for d in project.get("componentDefs", [])
        if isinstance(d, dict) and d.get("id")
    }}
    assignments: dict[str, dict[str, str]] = defaultdict(dict)
    fanout: Counter[str] = Counter()
    for item in project.get("netAssignments", []):
        if not isinstance(item, dict):
            continue
        cid, pid, nid = (str(item.get(k, "")) for k in ("componentId", "pinId", "netId"))
        if cid and pid and nid:
            if pid in assignments[cid] and assignments[cid][pid] != nid:
                raise ValueError(f"pin {cid}/{pid} is assigned to multiple nets")
            assignments[cid][pid] = nid
            fanout[nid] += 1

    records = []
    unresolved = []
    placeable_area = 0
    largest_rows = largest_cols = 0
    for component in project.get("components", []):
        cid = str(component["id"])
        definition = resolve_definition(component, defs)
        off_board = is_off_board_component(component)
        net_by_pin = assignments[cid]
        record: dict[str, Any] = {
            "component_id": cid,
            "definition_id": str(component.get("defId") or component.get("componentDefId") or ""),
            "off_board": off_board,
            "geometry": {"resolved": definition is not None, "orientations": []},
            "electrical": {
                "assigned_pin_count": len(net_by_pin),
                "distinct_net_count": len(set(net_by_pin.values())),
                "net_ids": sorted(set(net_by_pin.values())),
                "net_fanout": {n: fanout[n] for n in sorted(set(net_by_pin.values()))},
            },
            "placement": {
                "locked": bool(component.get("locked", False)),
                "existing_board_pos": component.get("boardPos"),
                "candidate_status": "advisory_only",
            },
            "warnings": [],
        }
        if definition is None:
            record["warnings"].append("unresolved_footprint")
            unresolved.append(cid)
        else:
            orientations = [int(component.get("rotation", 0) or 0) % 360] if (
                component.get("locked") and component.get("boardPos") is not None
            ) else [0, 90, 180, 270]
            for rotation in orientations:
                # Use the shared geometry resolver; anchor at zero only for analysis.
                # FlexibleEndPos is absolute and therefore requires translation.
                temp = {**component, "boardPos": {"row": 0, "col": 0}, "rotation": rotation}
                end = component.get("flexibleEndPos")
                pos = component.get("boardPos")
                if isinstance(end, dict) and isinstance(pos, dict):
                    temp["flexibleEndPos"] = {
                        "row": int(end["row"]) - int(pos["row"]),
                        "col": int(end["col"]) - int(pos["col"]),
                    }
                elif isinstance(end, dict):
                    # Without an anchor, an absolute endpoint cannot be normalised.
                    temp.pop("flexibleEndPos", None)
                    record["warnings"].append("unanchored_flexible_endpoint")
                pins, body = component_geometry(temp, definition)
                cells = [(int(p["row"]), int(p["col"])) for p in pins] + list(body)
                min_row = min((r for r, _ in cells), default=0)
                min_col = min((c for _, c in cells), default=0)
                max_row = max((r for r, _ in cells), default=0)
                max_col = max((c for _, c in cells), default=0)
                rows: dict[int, list[dict[str, Any]]] = defaultdict(list)
                for pin in pins:
                    rows[int(pin["row"])].append({
                        "pin_id": str(pin["id"]), "col": int(pin["col"]),
                        "net_id": net_by_pin.get(str(pin["id"])),
                    })
                conflicts = []
                for row, entries in sorted(rows.items()):
                    entries.sort(key=lambda p: (p["col"], p["pin_id"]))
                    for left, right in zip(entries, entries[1:]):
                        if left["net_id"] and right["net_id"] and left["net_id"] != right["net_id"]:
                            if left["col"] == right["col"]:
                                record["warnings"].append("different_nets_same_hole")
                            else:
                                conflicts.append({
                                    "row": row, "left_pin": left["pin_id"],
                                    "right_pin": right["pin_id"],
                                    "possible_cut_gaps": list(range(left["col"], right["col"])),
                                    "verified": False,
                                })
                record["geometry"]["orientations"].append({
                    "rotation": rotation,
                    "span_rows": max_row - min_row + 1,
                    "span_cols": max_col - min_col + 1,
                    "pins": [{**p, "net_id": net_by_pin.get(str(p["id"]))} for p in pins],
                    "body_cells": [{"row": r, "col": c} for r, c in body],
                    "pin_rows": [{"row": r, "pins": entries} for r, entries in sorted(rows.items())],
                    "different_net_pairs": conflicts,
                    "physical_clearance_verified": False,
                    "routing_intelligence": _orientation_intelligence(pins, body, net_by_pin),
                })
            if not off_board:
                area = min(o["span_rows"] * o["span_cols"] for o in record["geometry"]["orientations"])
                placeable_area += area
                largest_rows = max(largest_rows, min(o["span_rows"] for o in record["geometry"]["orientations"]))
                largest_cols = max(largest_cols, min(o["span_cols"] for o in record["geometry"]["orientations"]))
        records.append(record)

    candidate = _placement_candidate(records, board)
    rows = board.get("rows")
    cols = board.get("cols")
    locked_rows = bool(board.get("lockedRows", False))
    locked_cols = bool(board.get("lockedCols", False))
    existing_area = rows * cols if type(rows) is int and type(cols) is int and rows > 0 and cols > 0 else None
    return {
        "schema": SCHEMA, "schema_version": VERSION,
        "source_project_sha256": project_sha256(project),
        "components": records,
        "board": {
            "source_rows": rows, "source_cols": cols,
            "locked_rows": locked_rows, "locked_cols": locked_cols,
            "sum_min_footprint_bounding_areas": placeable_area,
            "largest_component_min_rows": largest_rows,
            "largest_component_min_cols": largest_cols,
            "source_area": existing_area,
            "source_area_vs_footprint_estimate": (
                "below_estimate" if existing_area is not None and existing_area < placeable_area
                else "not_below_estimate" if existing_area is not None else "unknown"
            ),
            "recommended_rows": None, "recommended_cols": None,
            "placement_candidate_rows": candidate["rows"],
            "placement_candidate_cols": candidate["cols"],
            "placement_candidate_status": candidate["status"],
            "recommendation_status": "requires_physical_routing_verification",
            "physical_fit_verified": False,
        },
        "warnings": [{"component_id": cid, "code": "unresolved_footprint"} for cid in unresolved],
    }
