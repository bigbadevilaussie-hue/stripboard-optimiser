"""Reusable native Edge+Slide anchor enumeration for rigid custom footprints.

A slide is an EXTERNAL retry across the SAME native solver, never a new
placement algorithm. This module is deliberately independent of Route-Mate
and the C optimiser. It does not use an artificial candidate cap.

Resolved custom component definitions/footprint overrides are supported.
Unknown builtin definitions must be resolved upstream (fail closed), rather
than guessing an incorrect component size or pin location.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EdgeAnchor:
    component_id: str
    label: str
    side: str
    original: tuple[int, int]
    positions: tuple[tuple[int, int], ...]


def _rotated_coords(component: dict, definition: dict):
    pins = definition.get("pins") or []
    body = definition.get("bodyCells") or []
    if not pins:
        raise ValueError("Edge mount must have electrical pins")
    coordinates = [(p["offsetRow"], p["offsetCol"]) for p in pins]
    coordinates += [(b["row"], b["col"]) for b in body]
    if not body:
        # A footprint without discrete body cells still occupies its
        # specified width/height (equivalent to its bounding box).
        w, h = definition.get("width"), definition.get("height")
        if type(w) is not int or type(h) is not int or w < 1 or h < 1:
            raise ValueError("Unresolved rigid footprint bounds")
        coordinates += [(0, 0), (h - 1, w - 1)]
    maxrow = max(r for r, _ in coordinates)
    maxcol = max(c for _, c in coordinates)
    rot = component.get("rotation", 0) or 0
    if rot not in (0, 90, 180, 270):
        raise ValueError("Unknown edge mount rotation")
    def rotate(pt):
        r, c = pt
        if rot == 90:
            return c, maxrow - r
        if rot == 180:
            return maxrow - r, maxcol - c
        if rot == 270:
            return maxcol - c, r
        return r, c
    footprint = [rotate(p) for p in coordinates]
    electric = [rotate((p["offsetRow"], p["offsetCol"])) for p in pins]
    return footprint, electric


def anchors_for_component(component: dict, definition: dict, board: dict) -> EdgeAnchor:
    if not (component.get("locked") is True and component.get("edge") is True
            and component.get("slide") is True):
        raise ValueError("Slide requires a locked Edge component")
    if not (board.get("lockedRows") and board.get("lockedCols")):
        raise ValueError("Both physical board dimensions must be locked")
    rows, cols = board["rows"], board["cols"]
    if not all(type(v) is int and v > 0 for v in (rows, cols)):
        raise ValueError("Invalid physical board dimensions")
    pos = component.get("boardPos")
    if not isinstance(pos, dict) or type(pos.get("row")) is not int or type(pos.get("col")) is not int:
        raise ValueError("Locked Edge+Slide requires a saved integer board position")
    label = component.get("label") or component["id"]
    footprint, electric = _rotated_coords(component, definition)
    rlo = min(p[0] for p in footprint)
    rhi = max(p[0] for p in footprint)
    clo = min(p[1] for p in footprint)
    chi = max(p[1] for p in footprint)
    minr, maxr = pos["row"] + rlo, pos["row"] + rhi
    minc, maxc = pos["col"] + clo, pos["col"] + chi
    outside = [
        side for side, bad in (
            ("top", minr < 0), ("bottom", maxr >= rows),
            ("left", minc < 0), ("right", maxc >= cols)
        ) if bad
    ]
    if len(outside) > 1:
        raise ValueError(f"{label}: edge body overhangs multiple physical board sides")
    if outside:
        side = outside[0]
    else:
        side = min(
            (("top", minr), ("bottom", rows - 1 - maxr),
             ("left", minc), ("right", cols - 1 - maxc)),
            key=lambda item: item[1]
        )[0]
    if any(not (0 <= pos["row"] + r < rows and 0 <= pos["col"] + c < cols)
           for r, c in electric):
        raise ValueError(f"{label}: saved Edge+Slide electrical pin off board")
    width, height = chi - clo + 1, rhi - rlo + 1
    if side in ("top", "bottom"):
        if width > cols:
            raise ValueError(f"{label}: footprint too wide to slide along {side}")
        candidates = [(pos["row"], col - clo) for col in range(cols - width + 1)]
        axis = 1
    else:
        if height > rows:
            raise ValueError(f"{label}: footprint too tall to slide along {side}")
        candidates = [(row - rlo, pos["col"]) for row in range(rows - height + 1)]
        axis = 0
    candidates = [
        candidate for candidate in candidates
        if all(0 <= candidate[0] + r < rows and 0 <= candidate[1] + c < cols
               for r, c in electric)
    ]
    original = (pos["row"], pos["col"])
    if original not in candidates:
        raise ValueError(f"{label}: saved position is not a legal {side} slide anchor")
    candidates.sort(key=lambda p: (abs(p[axis] - original[axis]), p[axis]))
    if len(candidates) != len(set(candidates)):
        raise AssertionError("Duplicate edge slide anchors")
    return EdgeAnchor(str(component["id"]), str(label), side, original, tuple(candidates))


def edge_slide_anchors(project: dict[str, Any]) -> list[EdgeAnchor]:
    defs = {str(d["id"]): d for d in project.get("componentDefs", [])}
    result = []
    for component in project.get("components", []):
        if component.get("offBoard") or component.get("boardExcluded"):
            continue
        if not (component.get("locked") is True and component.get("edge") is True
                and component.get("slide") is True):
            continue
        definition = defs.get(str(component.get("defId")))
        if definition is None:
            raise ValueError(f"{component.get('label')}: unresolved footprint; add its componentDef")
        override = component.get("footprintOverride")
        if override:
            definition = {**definition, **override}
        if definition.get("flexible"):
            raise ValueError("Flexible edge sliders not yet supported by the native decoder")
        result.append(anchors_for_component(component, definition, project["board"]))
    return result
