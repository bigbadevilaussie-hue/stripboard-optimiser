"""Explicit 2.5D jumper/part clearance contract (millimetres, board-top z=0).

The contract is independent of footprint artwork. Only supplied physical solids
and lead geometry participate. No standoff or package dimensions are inferred.
Router and verifier may implement the same normative contract independently.
"""
from __future__ import annotations

from math import hypot, isfinite
from typing import Any

EPS_MM = 1e-9
RANK = {"PASS": 0, "CONDITIONAL": 1, "FAIL_UNVERIFIED": 2, "FAIL_PROVEN": 3}
VALID_SOURCES = {"datasheet", "user_declared", "measured", "default_flush", "assumed_standard"}


def _number(value: Any, name: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    result = float(value)
    if not isfinite(result) or (minimum is not None and result < minimum):
        raise ValueError(f"{name} invalid: {value!r}")
    return result


def _point(value: Any, name: str) -> tuple[float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f"{name} must be [x_mm, y_mm]")
    return _number(value[0], name + ".x"), _number(value[1], name + ".y")


def _distance_point_segment(p, a, b) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    d2 = dx * dx + dy * dy
    if d2 == 0:
        return hypot(p[0] - a[0], p[1] - a[1])
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / d2))
    return hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))


def _orient(a, b, c) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _segments_cross(a, b, c, d) -> bool:
    o1, o2 = _orient(a, b, c), _orient(a, b, d)
    o3, o4 = _orient(c, d, a), _orient(c, d, b)
    opposite = lambda x, y: (x > EPS_MM and y < -EPS_MM) or (x < -EPS_MM and y > EPS_MM)
    if opposite(o1, o2) and opposite(o3, o4):
        return True
    for p, q, r in ((a, b, c), (a, b, d), (c, d, a), (c, d, b)):
        if abs(_orient(p, q, r)) <= EPS_MM and (
            min(p[0], q[0]) - EPS_MM <= r[0] <= max(p[0], q[0]) + EPS_MM
            and min(p[1], q[1]) - EPS_MM <= r[1] <= max(p[1], q[1]) + EPS_MM
        ):
            return True
    return False


def _segment_distance(a, b, c, d) -> float:
    if _segments_cross(a, b, c, d):
        return 0.0
    return min(
        _distance_point_segment(a, c, d),
        _distance_point_segment(b, c, d),
        _distance_point_segment(c, a, b),
        _distance_point_segment(d, a, b),
    )


def _inside_polygon(point, vertices) -> bool:
    x, y = point
    inside = False
    for i, a in enumerate(vertices):
        b = vertices[(i + 1) % len(vertices)]
        if _distance_point_segment(point, a, b) <= EPS_MM:
            return True
        if (a[1] > y) != (b[1] > y):
            cross_x = a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
            if cross_x >= x:
                inside = not inside
    return inside


def outline_distance(a, b, solid: dict[str, Any]) -> float:
    """Exact shape-specific 2D distance from a segment to a solid outline."""
    shape = solid.get("shape")
    if shape == "circle":
        center = _point(solid["center_mm"], "circle.center_mm")
        radius = _number(solid["radius_mm"], "circle.radius_mm", minimum=0)
        return max(0.0, _distance_point_segment(center, a, b) - radius)
    if shape == "rectangle":
        x0 = _number(solid["x_min_mm"], "x_min_mm")
        x1 = _number(solid["x_max_mm"], "x_max_mm")
        y0 = _number(solid["y_min_mm"], "y_min_mm")
        y1 = _number(solid["y_max_mm"], "y_max_mm")
        if x1 < x0 or y1 < y0:
            raise ValueError("invalid rectangle bounds")
        corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    elif shape == "polygon":
        corners = [_point(v, "polygon vertex") for v in solid["vertices_mm"]]
        if len(corners) < 3:
            raise ValueError("polygon requires at least three vertices")
    else:
        raise ValueError(f"unsupported body shape: {shape!r}")
    if _inside_polygon(a, corners) or _inside_polygon(b, corners):
        return 0.0
    return min(
        _segment_distance(a, b, corners[i], corners[(i + 1) % len(corners)])
        for i in range(len(corners))
    )


def _result(code: str, reason: str, item: str = "") -> dict[str, str]:
    return {"verdict": code, "reason": reason, "item": item}


def classify_jumper(case: dict[str, Any]) -> dict[str, Any]:
    """Classify one installed straight jumper against explicit physical geometry.

    Coordinates and distances are millimetres. Endpoint hole occupancy is
    intentional/allowed only when explicitly listed as permitted. Artwork
    is never used. A missing required physical dimension raises ValueError.
    """
    wire = case["jumper"]
    a = _point(wire["from_mm"], "jumper.from_mm")
    b = _point(wire["to_mm"], "jumper.to_mm")
    if a == b:
        return _result("FAIL_PROVEN", "zero_length_jumper")
    settings = case["settings"]
    od = _number(settings["wire_od_mm"], "wire_od_mm", minimum=0)
    margin = _number(settings["min_clearance_mm"], "min_clearance_mm", minimum=0)
    z_margin = _number(settings["z_margin_mm"], "z_margin_mm", minimum=0)
    lead_margin = _number(settings["lead_margin_mm"], "lead_margin_mm", minimum=0)
    lift = _number(wire.get("lift_mm", 0), "lift_mm", minimum=0)
    wire_top = lift + od
    radius = od / 2
    findings = []

    for hole in case.get("occupied_holes", []):
        point = _point(hole["center_mm"], "hole.center_mm")
        # Endpoints are legal only with an explicit permitted landing.
        endpoint = hypot(a[0] - point[0], a[1] - point[1]) <= EPS_MM or (
            hypot(b[0] - point[0], b[1] - point[1]) <= EPS_MM
        )
        if endpoint and hole.get("allowed_endpoint", False):
            continue
        if _distance_point_segment(point, a, b) <= EPS_MM:
            findings.append(_result("FAIL_PROVEN", "occupied_hole", str(hole.get("id", ""))))

    for lead in case.get("leads", []):
        center = _point(lead["center_mm"], "lead.center_mm")
        lr = _number(lead["radius_mm"], "lead.radius_mm", minimum=0)
        # Cylindrical lead envelopes are always checked without the body z-gate.
        at_endpoint = min(hypot(center[0] - p[0], center[1] - p[1])
                          for p in (a, b)) <= EPS_MM
        if at_endpoint and lead.get("allowed_endpoint", False):
            continue
        if _distance_point_segment(center, a, b) + EPS_MM < radius + lr + lead_margin:
            if lead.get("source") == "assumed_standard":
                findings.append(_result("FAIL_UNVERIFIED", "assumed_lead_clearance",
                                        str(lead.get("id", ""))))
            else:
                findings.append(_result("FAIL_PROVEN", "lead_clearance",
                                        str(lead.get("id", ""))))

    for solid in case.get("body_solids", []):
        name = str(solid.get("id", ""))
        distance = outline_distance(a, b, solid)
        if distance + EPS_MM >= radius + margin:
            continue
        source = solid.get("z_min_source")
        if source not in VALID_SOURCES:
            raise ValueError(f"{name}: invalid or missing z_min_source")
        zmin = _number(solid["z_min_mm"], f"{name}.z_min_mm", minimum=0)
        zmax = _number(solid["z_max_mm"], f"{name}.z_max_mm", minimum=zmin)
        if source == "default_flush":
            # Unknown standoff is NOT a proven collision.
            findings.append(_result("FAIL_UNVERIFIED", "standoff_unknown", name))
        elif wire_top + z_margin <= zmin + EPS_MM:
            if source in {"user_declared", "assumed_standard"}:
                reason = ("assumed_standoff" if source == "assumed_standard"
                          else "declared_standoff")
                findings.append(_result("CONDITIONAL", reason, name))
        elif lift >= zmax + z_margin - EPS_MM:
            # Lifted jumper entirely above the explicit solid.
            if source in {"user_declared", "assumed_standard"}:
                reason = ("assumed_height" if source == "assumed_standard"
                          else "declared_height")
                findings.append(_result("CONDITIONAL", reason, name))
        elif solid.get("allow_contact", False):
            if solid.get("contact_source") not in {"measured", "datasheet", "user_declared"}:
                raise ValueError(f"{name}: contact permission requires provenance")
            findings.append(_result("CONDITIONAL", "declared_contact", name))
        else:
            if source == "assumed_standard":
                findings.append(_result("FAIL_UNVERIFIED", "assumed_body_conflict", name))
            else:
                findings.append(_result("FAIL_PROVEN", "body_clearance", name))

    for zone in case.get("thermal_zones", []):
        if "component_temp_c" not in zone or "wire_insulation_limit_c" not in zone:
            continue  # no guessed thermal keepout
        temperature = _number(zone["component_temp_c"], "component_temp_c")
        insulation_limit = _number(zone["wire_insulation_limit_c"], "wire_insulation_limit_c")
        if temperature <= insulation_limit:
            continue
        if outline_distance(a, b, zone) + EPS_MM < radius + margin:
            findings.append(_result("FAIL_PROVEN", "thermal_keepout", str(zone.get("id", ""))))

    verdict = max((f["verdict"] for f in findings), key=lambda x: RANK[x], default="PASS")
    return {"verdict": verdict, "findings": findings,
            "measured_geometry_only": verdict == "PASS" and all(
                s.get("z_min_source") in {"measured", "datasheet"}
                for s in case.get("body_solids", [])
            )}


__all__ = ["EPS_MM", "classify_jumper", "outline_distance"]
