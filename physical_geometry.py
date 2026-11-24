"""Physical coordinates derived from Route-Mate's exact logical board geometry.

The saved project geometry remains authoritative for component pin/body occupancy.
This module only converts normalized hole-pitch coordinates into millimetres;
it does not infer component dimensions or clearances from artwork or labels.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from board_geometry import BoardGrid, GridPoint, component_geometry

# Standard stripboard pitch: exactly 0.1 inch = 2.54 mm.
HOLE_PITCH_MM = Fraction(127, 50)
HALF_PITCH_MM = HOLE_PITCH_MM / 2


@dataclass(frozen=True, slots=True)
class PhysicalPoint:
    """Exact physical coordinate in millimetres."""

    x_mm: Fraction
    y_mm: Fraction


@dataclass(frozen=True, slots=True)
class PhysicalSegment:
    """Straight physical segment in millimetres."""

    start: PhysicalPoint
    end: PhysicalPoint


@dataclass(frozen=True, slots=True)
class PhysicalCell:
    """Square occupancy cell centred on a board hole, in millimetres."""

    row: int
    col: int
    left_mm: Fraction
    top_mm: Fraction
    right_mm: Fraction
    bottom_mm: Fraction


def to_physical(point: GridPoint) -> PhysicalPoint:
    """Convert an exact normalized grid point to millimetres."""
    return PhysicalPoint(point.x * HOLE_PITCH_MM, point.y * HOLE_PITCH_MM)


def physical_hole_center(grid: BoardGrid, row: int, col: int) -> PhysicalPoint:
    """Return the physical centre of a board hole."""
    return to_physical(grid.hole_center(row, col))


def physical_between_cut_center(
    grid: BoardGrid, row: int, left_col: int
) -> PhysicalPoint:
    """Return the physical centre of the gap for a between-hole cut."""
    return to_physical(grid.between_cut_center(row, left_col))


def cut_approach_occupancy_conflicts(
    grid: BoardGrid,
    row: int,
    left_col: int,
    component_cells: list[PhysicalCell],
    tool_radius_mm: Fraction,
) -> list[PhysicalCell]:
    """Find occupancy squares intersecting a vertical cut-tool approach.

    The approach is modelled as a closed circular horizontal footprint at
    the between-hole gap, projected down from above the board. The radius
    MUST be supplied explicitly; bodyCells remain occupancy proxies, not
    measured package envelopes. An empty result is NOT physical PASS.
    Boundary contact is an obstruction.
    """
    radius = Fraction(tool_radius_mm)
    if radius < 0:
        raise ValueError("tool_radius_mm must be non-negative")
    centre = physical_between_cut_center(grid, row, left_col)
    conflicts = []
    for cell in component_cells:
        dx = max(cell.left_mm - centre.x_mm, Fraction(0),
                 centre.x_mm - cell.right_mm)
        dy = max(cell.top_mm - centre.y_mm, Fraction(0),
                 centre.y_mm - cell.bottom_mm)
        if dx * dx + dy * dy <= radius * radius:
            conflicts.append(cell)
    return conflicts


def assess_cut_access(
    grid: BoardGrid,
    row: int,
    left_col: int,
    component_cells: list[PhysicalCell],
    *,
    tool_radius_mm: Fraction | None = None,
    measured_envelopes: bool = False,
) -> dict[str, Any]:
    """Conservative Gate 1 cut-access assessment, never an inferred PASS.

    A collision with known occupancy is a hard obstruction. Otherwise, tool
    size and measured component envelopes are both required for clearance.
    The caller must not treat UNKNOWN as permission to cut.
    """
    # Validate the between-hole gap even when tool geometry is missing.
    physical_between_cut_center(grid, row, left_col)
    if tool_radius_mm is None:
        return {"status": "UNKNOWN", "reason": "tool_radius_missing"}
    conflicts = cut_approach_occupancy_conflicts(
        grid, row, left_col, component_cells, tool_radius_mm
    )
    if conflicts:
        return {
            "status": "BLOCKED",
            "reason": "component_occupancy_intersection",
            "conflicting_cells": [(cell.row, cell.col) for cell in conflicts],
        }
    if not measured_envelopes:
        return {"status": "UNKNOWN", "reason": "measured_envelopes_missing"}
    return {"status": "CLEAR_WITH_SUPPLIED_GEOMETRY", "reason": None}


def physical_jumper_segment(
    grid: BoardGrid, start: tuple[int, int], end: tuple[int, int]
) -> PhysicalSegment:
    """Return one legal vertical jumper segment in physical coordinates."""
    segment = grid.jumper_segment(start, end)
    return PhysicalSegment(to_physical(segment.start), to_physical(segment.end))


def physical_component_body(
    component: dict[str, Any], definition: dict[str, Any]
) -> list[PhysicalCell]:
    """Map saved bodyCells/footprintOverride occupancy to physical cell squares.

    This deliberately uses component_geometry(), so rotations and flexible
    two-lead endpoints follow the same authoritative project geometry as the
    solver. A body cell is one pitch-square occupancy cell, not a claim about
    the component's measured outer package dimensions.
    """
    _, body_points = component_geometry(component, definition)
    cells = []
    for row, col in body_points:
        x = Fraction(col) * HOLE_PITCH_MM
        y = Fraction(row) * HOLE_PITCH_MM
        cells.append(PhysicalCell(
            row=row,
            col=col,
            left_mm=x - HALF_PITCH_MM,
            top_mm=y - HALF_PITCH_MM,
            right_mm=x + HALF_PITCH_MM,
            bottom_mm=y + HALF_PITCH_MM,
        ))
    return cells


def physical_segment_intersects_cell(segment: PhysicalSegment, cell: PhysicalCell) -> bool:
    """Exact centreline intersection with a closed occupancy square.

    No wire diameter, package overhang, or unmeasured clearance is added.
    Boundary contact counts as intersection.
    """
    x1, y1 = segment.start.x_mm, segment.start.y_mm
    dx = segment.end.x_mm - x1
    dy = segment.end.y_mm - y1
    t0, t1 = Fraction(0), Fraction(1)
    for origin, delta, lower, upper in (
        (x1, dx, cell.left_mm, cell.right_mm),
        (y1, dy, cell.top_mm, cell.bottom_mm),
    ):
        if delta == 0:
            if origin < lower or origin > upper:
                return False
            continue
        enter, leave = (lower-origin)/delta, (upper-origin)/delta
        if enter > leave:
            enter, leave = leave, enter
        t0, t1 = max(t0, enter), min(t1, leave)
        if t0 > t1:
            return False
    return True


def physical_segments_intersect(first: PhysicalSegment, second: PhysicalSegment) -> bool:
    """Exact closed-segment test; crossing, touching and overlap all count."""
    def cross(a: PhysicalPoint, b: PhysicalPoint, c: PhysicalPoint) -> Fraction:
        return ((b.x_mm-a.x_mm)*(c.y_mm-a.y_mm)
                - (b.y_mm-a.y_mm)*(c.x_mm-a.x_mm))

    def on_segment(a: PhysicalPoint, b: PhysicalPoint, p: PhysicalPoint) -> bool:
        return (min(a.x_mm,b.x_mm) <= p.x_mm <= max(a.x_mm,b.x_mm)
                and min(a.y_mm,b.y_mm) <= p.y_mm <= max(a.y_mm,b.y_mm))

    a, b, c, d = first.start, first.end, second.start, second.end
    o1, o2, o3, o4 = cross(a,b,c), cross(a,b,d), cross(c,d,a), cross(c,d,b)
    if o1 == 0 and on_segment(a,b,c): return True
    if o2 == 0 and on_segment(a,b,d): return True
    if o3 == 0 and on_segment(c,d,a): return True
    if o4 == 0 and on_segment(c,d,b): return True
    return ((o1 > 0) != (o2 > 0)) and ((o3 > 0) != (o4 > 0))


def _point_segment_distance_squared(point: PhysicalPoint, segment: PhysicalSegment) -> Fraction:
    dx = segment.end.x_mm - segment.start.x_mm
    dy = segment.end.y_mm - segment.start.y_mm
    length_squared = dx * dx + dy * dy
    if length_squared == 0:
        return ((point.x_mm - segment.start.x_mm) ** 2
                + (point.y_mm - segment.start.y_mm) ** 2)
    projection = ((point.x_mm - segment.start.x_mm) * dx
                 + (point.y_mm - segment.start.y_mm) * dy) / length_squared
    projection = max(Fraction(0), min(Fraction(1), projection))
    nearest_x = segment.start.x_mm + projection * dx
    nearest_y = segment.start.y_mm + projection * dy
    return (point.x_mm - nearest_x) ** 2 + (point.y_mm - nearest_y) ** 2


def physical_segment_within_cell_radius(
    segment: PhysicalSegment, cell: PhysicalCell, radius_mm: Fraction
) -> bool:
    """Test a round wire envelope against a closed occupancy square.

    radius_mm is an explicit physical input; no wire diameter or clearance is
    assumed. Exact squared-distance comparisons avoid floating-point error.
    """
    radius = Fraction(radius_mm)
    if radius < 0:
        raise ValueError("radius_mm must be non-negative")
    if physical_segment_intersects_cell(segment, cell):
        return True

    def point_rectangle_distance_squared(point: PhysicalPoint) -> Fraction:
        dx = max(cell.left_mm - point.x_mm, Fraction(0),
                 point.x_mm - cell.right_mm)
        dy = max(cell.top_mm - point.y_mm, Fraction(0),
                 point.y_mm - cell.bottom_mm)
        return dx * dx + dy * dy

    if min(point_rectangle_distance_squared(segment.start),
           point_rectangle_distance_squared(segment.end)) <= radius * radius:
        return True

    corners = (
        PhysicalPoint(cell.left_mm, cell.top_mm),
        PhysicalPoint(cell.left_mm, cell.bottom_mm),
        PhysicalPoint(cell.right_mm, cell.top_mm),
        PhysicalPoint(cell.right_mm, cell.bottom_mm),
    )
    return any(_point_segment_distance_squared(corner, segment) <= radius * radius
               for corner in corners)


def jumper_envelope_intersects_component(
    jumper: PhysicalSegment,
    component_cells: list[PhysicalCell],
    radius_mm: Fraction,
) -> bool:
    """Check a round jumper wire envelope using an explicitly supplied radius."""
    return any(physical_segment_within_cell_radius(jumper, cell, radius_mm)
               for cell in component_cells)


def jumper_intersects_component(jumper: PhysicalSegment, component_cells: list[PhysicalCell]) -> bool:
    """Check exact centreline collision, cheaply rejecting distant body cells.

    An axis-aligned bounding-box rejection cannot discard a real collision.
    Inclusive comparisons retain boundary-touch collisions; shortlisted cells
    still use the existing exact Fraction-based segment/rectangle test.
    """
    min_x = min(jumper.start.x_mm, jumper.end.x_mm)
    max_x = max(jumper.start.x_mm, jumper.end.x_mm)
    min_y = min(jumper.start.y_mm, jumper.end.y_mm)
    max_y = max(jumper.start.y_mm, jumper.end.y_mm)
    return any(
        physical_segment_intersects_cell(jumper, cell)
        for cell in component_cells
        if cell.right_mm >= min_x and cell.left_mm <= max_x
        and cell.bottom_mm >= min_y and cell.top_mm <= max_y
    )


def jumpers_intersect(first: PhysicalSegment, second: PhysicalSegment) -> bool:
    """Check jumper centreline crossing or shared physical segment space."""
    return physical_segments_intersect(first, second)


def jumper_endpoint_available(
    grid: BoardGrid,
    hole: tuple[int, int],
    occupied_holes: set[tuple[int, int]] | frozenset[tuple[int, int]] = frozenset(),
    landing_holes: set[tuple[int, int]] | frozenset[tuple[int, int]] = frozenset(),
) -> bool:
    """Return whether a jumper endpoint is valid and not already occupied.

    A hole explicitly listed in landing_holes is permitted as an intentional
    landing even if it is also listed as occupied. This function checks hole
    identity/occupancy only; it does not claim physical access or solder
    clearance, which require additional measured geometry.
    """
    grid.hole_center(*hole)  # Raises ValueError for an invalid board hole.
    return hole in landing_holes or hole not in occupied_holes


def project_geometry_confidence(project: dict[str, Any]) -> dict[str, Any]:
    """Report what the saved project can and cannot support physically.

    Grid occupancy is reported separately from measured package geometry.
    This function deliberately does not infer millimetre body dimensions from
    width/height, bodyCells, artwork, or pin spacing.
    """
    if not isinstance(project, dict):
        raise ValueError("project must be an object")
    components = project.get("components")
    definitions = project.get("componentDefs")
    if not isinstance(components, list) or not isinstance(definitions, list):
        raise ValueError("project must contain components and componentDefs arrays")

    by_id = {
        str(item.get("id")): item
        for item in definitions
        if isinstance(item, dict) and item.get("id") is not None
    }
    rows: list[dict[str, Any]] = []
    occupancy_count = 0
    unresolved_count = 0
    for component in components:
        if not isinstance(component, dict):
            raise ValueError("every component must be an object")
        ref = str(component.get("ref") or component.get("reference")
                  or component.get("label") or component.get("id") or "")
        def_id = str(component.get("defId") or component.get("componentDefId") or "")
        definition = by_id.get(def_id)
        if definition is None:
            rows.append({
                "component": ref, "definition_id": def_id,
                "grid_occupancy": "unresolved",
                "measured_body_dimensions_mm": "not_provided",
            })
            unresolved_count += 1
            continue

        effective = dict(definition)
        override = component.get("footprintOverride")
        if isinstance(override, dict):
            effective.update(override)
        body_cells = effective.get("bodyCells")
        has_occupancy = isinstance(body_cells, list) and len(body_cells) > 0
        if has_occupancy:
            occupancy_count += 1
        rows.append({
            "component": ref,
            "definition_id": def_id,
            "grid_occupancy": "saved_body_cells" if has_occupancy else "pins_only_or_empty",
            "body_cell_count": len(body_cells) if isinstance(body_cells, list) else 0,
            "measured_body_dimensions_mm": "not_provided",
        })

    total = len(components)
    return {
        "status": "INCOMPLETE_PHYSICAL_DIMENSIONS",
        "component_count": total,
        "grid_occupancy_count": occupancy_count,
        "unresolved_definition_count": unresolved_count,
        "measured_body_dimensions_count": 0,
        "physical_clearance_verifiable": False,
        "components": rows,
    }


__all__ = [
    "HOLE_PITCH_MM",
    "HALF_PITCH_MM",
    "PhysicalPoint",
    "PhysicalSegment",
    "PhysicalCell",
    "to_physical",
    "physical_hole_center",
    "physical_between_cut_center",
    "cut_approach_occupancy_conflicts",
    "assess_cut_access",
    "physical_jumper_segment",
    "physical_component_body",
    "physical_segment_intersects_cell",
    "physical_segment_within_cell_radius",
    "jumper_envelope_intersects_component",
    "physical_segments_intersect",
    "jumper_intersects_component",
    "jumpers_intersect",
    "jumper_endpoint_available",
    "project_geometry_confidence",
]
