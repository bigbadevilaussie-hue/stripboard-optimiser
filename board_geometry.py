"""Renderer-independent logical geometry for the stripboard grid.

Coordinates are expressed in normalized hole-pitch units:
- x increases with board columns (left to right);
- y increases with board rows (top to bottom);
- hole centres have integer coordinates;
- a between-hole cut lies halfway between adjacent columns.

These values are NOT millimetres, screen pixels, component dimensions, or
clearance measurements. This module deliberately defines no physical envelope.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any


Hole = tuple[int, int]  # (row, column)


@dataclass(frozen=True, slots=True)
class GridPoint:
    """Exact point in normalized hole-pitch coordinates (x=column, y=row)."""

    x: Fraction
    y: Fraction


@dataclass(frozen=True, slots=True)
class GridSegment:
    """Straight segment between two logical board points."""

    start: GridPoint
    end: GridPoint


@dataclass(frozen=True, slots=True)
class BoardGrid:
    """Logical coordinate frame for a rectangular stripboard."""

    rows: int
    cols: int

    def __post_init__(self) -> None:
        if type(self.rows) is not int or self.rows < 1:
            raise ValueError("rows must be a positive integer")
        if type(self.cols) is not int or self.cols < 1:
            raise ValueError("cols must be a positive integer")

    def contains_hole(self, row: int, col: int) -> bool:
        """Return whether (row, col) identifies an existing board hole."""
        return (
            type(row) is int and type(col) is int
            and 0 <= row < self.rows and 0 <= col < self.cols
        )

    def hole_center(self, row: int, col: int) -> GridPoint:
        """Return the normalized centre coordinate of a board hole."""
        self._require_hole((row, col), "hole")
        return GridPoint(Fraction(col), Fraction(row))

    def between_cut_center(self, row: int, left_col: int) -> GridPoint:
        """Return the centre of the gap between (row,left_col) and its right neighbour."""
        if type(row) is not int or not 0 <= row < self.rows:
            raise ValueError(f"cut row {row!r} is outside the board")
        if type(left_col) is not int or not 0 <= left_col < self.cols - 1:
            raise ValueError(
                f"between-cut column {left_col!r} has no adjacent hole to its right"
            )
        return GridPoint(Fraction(2 * left_col + 1, 2), Fraction(row))

    def jumper_segment(self, start: Hole, end: Hole) -> GridSegment:
        """Return one legal logical jumper segment between two vertical-aligned holes."""
        self._require_hole(start, "jumper start")
        self._require_hole(end, "jumper end")
        start_row, start_col = start
        end_row, end_col = end
        if start_col != end_col:
            raise ValueError("jumper endpoints must share one column")
        if start_row == end_row:
            raise ValueError("jumper endpoints must be on different rows")
        return GridSegment(
            self.hole_center(start_row, start_col),
            self.hole_center(end_row, end_col),
        )

    def _require_hole(self, point: Hole, context: str) -> None:
        if (
            not isinstance(point, tuple) or len(point) != 2
            or not self.contains_hole(point[0], point[1])
        ):
            raise ValueError(f"{context} {point!r} is not a board hole")


__all__ = ["BoardGrid", "GridPoint", "GridSegment", "Hole"]


# Shared footprint definitions and transforms. Kept here so solver code does
# not depend on renderer-owned modules.

def _pin(pin_id: str, name: str, row: int, col: int) -> dict[str, Any]:
    return {"id": pin_id, "name": name, "offsetRow": row, "offsetCol": col}


def _inline(pin_count: int, step: int = 1, *, flexible: bool = False) -> dict[str, Any]:
    return {
        "width": 1,
        "height": (pin_count - 1) * step + 1,
        "flexible": flexible,
        "pins": [_pin(str(i + 1), str(i + 1), i * step, 0) for i in range(pin_count)],
        "bodyCells": [
            {"row": row, "col": 0}
            for row in range(1, (pin_count - 1) * step)
            if row % step
        ],
    }


def _dip(pin_count: int) -> dict[str, Any]:
    side = pin_count // 2
    pins = [_pin(str(i + 1), str(i + 1), i, 0) for i in range(side)]
    pins += [
        _pin(str(side + i + 1), str(side + i + 1), side - 1 - i, 3)
        for i in range(side)
    ]
    return {
        "width": 4, "height": side, "pins": pins,
        "bodyCells": [
            {"row": row, "col": col}
            for row in range(side) for col in (1, 2)
        ],
    }


def _builtins() -> dict[str, dict[str, Any]]:
    """The common built-in footprints used by the legacy project format.

    Custom definitions from project JSON always take precedence. This compact
    registry covers the standard parts used by the Moto and Audio benchmarks.
    """
    result: dict[str, dict[str, Any]] = {}
    for part_id, step, flexible in (
        ("def-resistor", 4, True),
        ("def-capacitor", 1, True),
        ("def-cap-polarized", 1, True),
        ("def-led", 1, True),
        ("def-diode", 3, True),
        ("def-zener", 3, True),
        ("def-inductor", 4, True),
        ("def-fuse", 5, True),
        ("def-switch", 3, False),
    ):
        result[part_id] = _inline(2, step, flexible=flexible)
    result["def-npn"] = {
        **_inline(3), "category": "semiconductor",
        "pins": [_pin("1", "B", 0, 0), _pin("2", "C", 1, 0), _pin("3", "E", 2, 0)],
    }
    result["def-pmos"] = {
        **_inline(3), "category": "semiconductor",
        "pins": [_pin("1", "G", 0, 0), _pin("2", "D", 1, 0), _pin("3", "S", 2, 0)],
    }
    result["def-pushbutton"] = {
        "width": 4, "height": 3,
        "pins": [
            _pin("1", "1", 0, 0), _pin("1", "1", 0, 3),
            _pin("2", "2", 2, 0), _pin("2", "2", 2, 3),
        ],
        "bodyCells": [
            {"row": 0, "col": 1}, {"row": 0, "col": 2},
            {"row": 1, "col": 0}, {"row": 1, "col": 1},
            {"row": 1, "col": 2}, {"row": 1, "col": 3},
            {"row": 2, "col": 1}, {"row": 2, "col": 2},
        ],
    }
    result["def-555"] = _dip(8)
    for count in (4, 6, 8, 10, 12, 14, 16, 18, 20, 24, 28, 32, 36, 40):
        result[f"def-ic-dip{count}"] = _dip(count)
    for count in range(1, 21):
        result[f"def-connector-{count}"] = _inline(count)
    for spacing in (2, 3, 4, 5, 7):
        result[f"def-generic-2pin-{spacing}h"] = _inline(2, spacing - 1)
    result["def-generic-3pin-compact"] = _inline(3)
    result["def-generic-3pin-spaced"] = _inline(3, 2)
    return result


BUILTIN_DEFS = _builtins()


def resolve_definition(component: dict[str, Any], definitions: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    """Resolve project definition, including a component-specific footprint override."""
    base = definitions.get(str(component.get("defId") or component.get("componentDefId") or ""))
    override = component.get("footprintOverride")
    if base is None and isinstance(override, dict):
        base = override
    if base is None:
        return None
    result = dict(base)
    if isinstance(override, dict):
        for key in ("width", "height", "pins", "bodyCells"):
            if key in override:
                result[key] = override[key]
    return result


def rotate_offset(row: int, col: int, rotation: int, max_row: int, max_col: int) -> tuple[int, int]:
    rotation %= 360
    if rotation == 90:
        return col, max_row - row
    if rotation == 180:
        return max_row - row, max_col - col
    if rotation == 270:
        return max_col - col, row
    return row, col


def component_geometry(
    component: dict[str, Any], definition: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[tuple[int, int]]]:
    """Return absolute pin records and body-cell coordinates."""
    pos = component.get("boardPos")
    if not isinstance(pos, dict):
        return [], []
    base_row, base_col = int(pos.get("row", 0)), int(pos.get("col", 0))
    pins = definition.get("pins") or []
    body = definition.get("bodyCells") or []
    points = [
        (int(p.get("offsetRow", 0)), int(p.get("offsetCol", 0)))
        for p in pins if isinstance(p, dict)
    ] + [
        (int(p.get("row", 0)), int(p.get("col", 0)))
        for p in body if isinstance(p, dict)
    ]
    max_row = max((p[0] for p in points), default=0)
    max_col = max((p[1] for p in points), default=0)
    rotation = int(component.get("rotation", 0) or 0) % 360

    # WR 2-pin connectors use a vertical zero-degree orientation even
    # when their serialized definition is a horizontal 2x1 footprint.
    if (str(component.get("defId") or component.get("componentDefId") or "").startswith("def-connector-")
            and len(pins) == 2 and max_row == 0 and max_col == 1):
        pins = [
            {**pin, "offsetRow": int(pin.get("offsetCol", 0)), "offsetCol": 0}
            for pin in pins
        ]
        body = [{"row": int(cell.get("col", 0)), "col": 0} for cell in body]
        max_row, max_col = 1, 0

    # A solved export may carry an explicit flexible endpoint even when
    # its saved footprint definition omits the editor's "flexible" flag.
    # Honour that endpoint for two-pin parts without changing saved geometry.
    explicit_end = component.get("flexibleEndPos")
    if len(pins) == 2 and (
        definition.get("flexible") or isinstance(explicit_end, dict)
    ):
        end = explicit_end
        if not isinstance(end, dict):
            # Flexible parts default to pin 2's unrotated offset, matching the source model.
            dr = int(pins[1].get("offsetRow", 1))
            dc = int(pins[1].get("offsetCol", 0))
            end = {"row": base_row + dr, "col": base_col + dc}
        end_row, end_col = int(end.get("row", base_row)), int(end.get("col", base_col))
        pin_points = [
            {"id": str(pins[0].get("id", "1")), "name": str(pins[0].get("name", "1")),
             "row": base_row, "col": base_col},
            {"id": str(pins[1].get("id", "2")), "name": str(pins[1].get("name", "2")),
             "row": end_row, "col": end_col},
        ]

        # Flexible two-lead parts still occupy their declared body cells.
        # Map cells along the definition's pin-to-pin axis onto the actual
        # saved lead endpoints; otherwise resistors reserve only their pads
        # and another component can be placed directly through the body.
        first = pins[0]
        second = pins[1]
        axis_row = int(second.get("offsetRow", 1)) - int(first.get("offsetRow", 0))
        axis_col = int(second.get("offsetCol", 0)) - int(first.get("offsetCol", 0))
        axis_length_sq = axis_row * axis_row + axis_col * axis_col
        body_points = []
        if axis_length_sq:
            for cell in body:
                if not isinstance(cell, dict):
                    continue
                rel_row = int(cell.get("row", 0)) - int(first.get("offsetRow", 0))
                rel_col = int(cell.get("col", 0)) - int(first.get("offsetCol", 0))
                # Only map body cells on the lead axis and strictly between
                # the two pads. Non-collinear custom artwork is not a lead
                # body cell and remains the responsibility of its own model.
                if rel_row * axis_col != rel_col * axis_row:
                    continue
                fraction = (rel_row * axis_row + rel_col * axis_col) / axis_length_sq
                if not 0.0 < fraction < 1.0:
                    continue
                row = round(base_row + fraction * (end_row - base_row))
                col = round(base_col + fraction * (end_col - base_col))
                body_points.append((row, col))
        return pin_points, body_points

    pin_points = []
    for pin in pins:
        if not isinstance(pin, dict):
            continue
        row, col = rotate_offset(
            int(pin.get("offsetRow", 0)), int(pin.get("offsetCol", 0)),
            rotation, max_row, max_col,
        )
        pin_points.append({
            "id": str(pin.get("id", "")), "name": str(pin.get("name", "")),
            "row": base_row + row, "col": base_col + col,
        })
    body_points = []
    for cell in body:
        if not isinstance(cell, dict):
            continue
        row, col = rotate_offset(
            int(cell.get("row", 0)), int(cell.get("col", 0)),
            rotation, max_row, max_col,
        )
        body_points.append((base_row + row, base_col + col))
    return pin_points, body_points


__all__ = ["BoardGrid", "GridPoint", "GridSegment", "Hole", "BUILTIN_DEFS", "component_geometry", "resolve_definition", "rotate_offset"]
