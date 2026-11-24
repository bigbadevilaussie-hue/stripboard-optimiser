"""Independent 2.5D physical clearance verdict implementation.

Does NOT use the router's classify_jumper or its gap-map decisions.
Recomputes circle, polygon, lead and body decisions independently. Only the
published numerical tolerance is shared with the router implementation.
"""
from __future__ import annotations

from math import hypot

from .clearance_25d import EPS_MM


def _pt(values):
    return float(values[0]), float(values[1])


def _point_line_distance(point, start, end):
    dx, dy = end[0] - start[0], end[1] - start[1]
    length2 = dx * dx + dy * dy
    fraction = 0.0 if length2 == 0 else (
        ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / length2
    )
    fraction = min(1.0, max(0.0, fraction))
    return hypot(point[0] - start[0] - fraction * dx,
                 point[1] - start[1] - fraction * dy)


def _cross(a, b, c):
    return ((b[0] - a[0]) * (c[1] - a[1])
            - (b[1] - a[1]) * (c[0] - a[0]))


def _on_edge(p, a, b):
    return (_point_line_distance(p, a, b) <= EPS_MM
            and min(a[0], b[0]) - EPS_MM <= p[0] <= max(a[0], b[0]) + EPS_MM
            and min(a[1], b[1]) - EPS_MM <= p[1] <= max(a[1], b[1]) + EPS_MM)


def _edge_intersects(a, b, c, d):
    if any((_on_edge(p, s, e) for p, s, e in (
            (a, c, d), (b, c, d), (c, a, b), (d, a, b)))):
        return True
    return ((_cross(a, b, c) > 0) != (_cross(a, b, d) > 0)
            and (_cross(c, d, a) > 0) != (_cross(c, d, b) > 0))


def _in_polygon(point, vertices):
    if any(_on_edge(point, vertices[i], vertices[(i + 1) % len(vertices)])
           for i in range(len(vertices))):
        return True
    x, y = point
    crossings = 0
    for i in range(len(vertices)):
        a, b = vertices[i], vertices[(i + 1) % len(vertices)]
        if (a[1] > y) != (b[1] > y):
            at_x = a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
            crossings += int(at_x >= x)
    return crossings % 2 == 1


def _outline_distance_independent(start, end, solid):
    """Verifier's own circle/rectangle/polygon segment distance computation."""
    shape = solid.get("shape")
    if shape == "circle":
        centre = _pt(solid["center_mm"])
        radius = float(solid["radius_mm"])
        if radius < 0:
            raise ValueError("negative circle radius")
        return max(0.0, _point_line_distance(centre, start, end) - radius)
    if shape == "rectangle":
        x0, x1 = float(solid["x_min_mm"]), float(solid["x_max_mm"])
        y0, y1 = float(solid["y_min_mm"]), float(solid["y_max_mm"])
        if x1 < x0 or y1 < y0:
            raise ValueError("invalid rectangle")
        vertices = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    elif shape == "polygon":
        vertices = [_pt(x) for x in solid["vertices_mm"]]
        if len(vertices) < 3:
            raise ValueError("polygon needs >=3 vertices")
    else:
        raise ValueError(f"unsupported solid shape: {shape!r}")
    if _in_polygon(start, vertices) or _in_polygon(end, vertices):
        return 0.0
    smallest = float("inf")
    for i in range(len(vertices)):
        a, b = vertices[i], vertices[(i + 1) % len(vertices)]
        if _edge_intersects(start, end, a, b):
            return 0.0
        smallest = min(
            smallest, _point_line_distance(start, a, b),
            _point_line_distance(end, a, b),
            _point_line_distance(a, start, end),
            _point_line_distance(b, start, end),
        )
    return smallest



def verify_jumper_25d(case: dict) -> dict:
    """Evaluate geometry independently, with coded evidence per obstruction."""
    wire = case["jumper"]
    start, end = _pt(wire["from_mm"]), _pt(wire["to_mm"])
    settings = case["settings"]
    outer_radius = float(settings["wire_od_mm"]) / 2
    clearance = float(settings["min_clearance_mm"])
    z_margin = float(settings["z_margin_mm"])
    lead_margin = float(settings["lead_margin_mm"])
    lift = float(wire.get("lift_mm", 0))
    if min(outer_radius, clearance, z_margin, lead_margin, lift) < 0:
        raise ValueError("clearance dimensions must be non-negative")
    if start == end:
        return {"verdict": "FAIL_PROVEN", "findings": [
            {"verdict": "FAIL_PROVEN", "reason": "zero_length_jumper", "item": ""}]}
    findings = []

    def record(verdict, reason, item):
        findings.append({"verdict": verdict, "reason": reason, "item": str(item)})

    for hole in case.get("occupied_holes", []):
        p = _pt(hole["center_mm"])
        at_end = min(hypot(p[0] - x[0], p[1] - x[1]) for x in (start, end)) <= EPS_MM
        if at_end and hole.get("allowed_endpoint") is True:
            continue
        if _point_line_distance(p, start, end) <= EPS_MM:
            record("FAIL_PROVEN", "occupied_hole", hole.get("id", ""))

    for lead in case.get("leads", []):
        p = _pt(lead["center_mm"])
        at_end = min(hypot(p[0] - x[0], p[1] - x[1]) for x in (start, end)) <= EPS_MM
        if at_end and lead.get("allowed_endpoint") is True:
            continue
        limit = outer_radius + lead_margin + float(lead["radius_mm"])
        if _point_line_distance(p, start, end) < limit - EPS_MM:
            if lead.get("source") == "assumed_standard":
                record("FAIL_UNVERIFIED", "assumed_lead_clearance", lead.get("id", ""))
            else:
                record("FAIL_PROVEN", "lead_clearance", lead.get("id", ""))

    for solid in case.get("body_solids", []):
        threshold = outer_radius + clearance
        if _outline_distance_independent(start, end, solid) >= threshold - EPS_MM:
            continue
        source = solid["z_min_source"]
        if source not in ("datasheet", "measured", "user_declared",
                          "default_flush", "assumed_standard"):
            raise ValueError("unsupported standoff provenance")
        bottom = float(solid["z_min_mm"])
        top = float(solid["z_max_mm"])
        if bottom < 0 or top < bottom:
            raise ValueError("invalid solid z interval")
        name = solid.get("id", "")
        if source == "default_flush":
            record("FAIL_UNVERIFIED", "standoff_unknown", name)
        elif lift + 2 * outer_radius + z_margin <= bottom + EPS_MM:
            if source == "assumed_standard":
                record("CONDITIONAL", "assumed_standoff", name)
            elif source == "user_declared":
                record("CONDITIONAL", "declared_standoff", name)
        elif lift >= top + z_margin - EPS_MM:
            if source == "assumed_standard":
                record("CONDITIONAL", "assumed_height", name)
            elif source == "user_declared":
                record("CONDITIONAL", "declared_height", name)
        elif solid.get("allow_contact") is True:
            if solid.get("contact_source") not in ("datasheet", "measured", "user_declared"):
                raise ValueError("contact requires provenance")
            record("CONDITIONAL", "declared_contact", name)
        else:
            if source == "assumed_standard":
                record("FAIL_UNVERIFIED", "assumed_body_conflict", name)
            else:
                record("FAIL_PROVEN", "body_clearance", name)

    for zone in case.get("thermal_zones", []):
        if "component_temp_c" not in zone or "wire_insulation_limit_c" not in zone:
            continue
        if float(zone["component_temp_c"]) <= float(zone["wire_insulation_limit_c"]):
            continue
        if _outline_distance_independent(start, end, zone) < outer_radius + clearance - EPS_MM:
            record("FAIL_PROVEN", "thermal_keepout", zone.get("id", ""))

    ranking = ("PASS", "CONDITIONAL", "FAIL_UNVERIFIED", "FAIL_PROVEN")
    worst = max((ranking.index(f["verdict"]) for f in findings), default=0)
    return {"verdict": ranking[worst], "findings": findings}


__all__ = ["verify_jumper_25d"]
