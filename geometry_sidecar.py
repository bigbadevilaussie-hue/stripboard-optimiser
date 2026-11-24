"""Collector sidecar persistence and board-local 2.5D *assumption* audit.

No per-project or component-label exceptions. The collector owns the profiles,
this module binds them to one exact project snapshot and applies the saved
component's actual pin geometry (including flexible end positions/rotations).
Both independent 2.5D engines must agree. These are conditional engineering
estimates, not measured clearance or a safety certification.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from board_geometry import BUILTIN_DEFS, component_geometry, resolve_definition
from collector_geometry import build_assumed_geometry
from placement_policy import is_off_board_component
from solve.clearance_25d import classify_jumper
from solve.clearance_25d_verify import verify_jumper_25d

PITCH = 2.54
SCHEMA = "route-mate/project-geometry-sidecar/1"


def sidecar_path(source_path: str | Path) -> Path:
    file = Path(source_path)
    return file.with_name(f"{file.stem}.routemate-geometry.json")


def _hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                     allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _collector_campaign_geometry(project: dict, source_path: str | Path):
    """Read collector's actual campaign sidecar, if one belongs to this file.

    Normal campaign path: <output>/projects/<id>.json with
    <output>/physical_geometry.json and <output>/manifest.json. Check the
    source project identifier and sidecar digest before trusting it.
    """
    project_file = Path(source_path)
    if project_file.parent.name != "projects":
        return None
    root = project_file.parent.parent
    physical = root / "physical_geometry.json"
    manifest_file = root / "manifest.json"
    if not physical.exists() or not manifest_file.exists():
        return None
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if Path(manifest.get("campaign_project", "")).resolve() != project_file.resolve():
        return None
    raw = physical.read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest.get("physical_geometry_sidecar_sha256"):
        raise ValueError("collector campaign geometry sidecar SHA-256 mismatch")
    model = json.loads(raw)
    expected = build_assumed_geometry(project)
    if model != expected:
        raise ValueError("collector campaign geometry sidecar differs from project or preset")
    return model


def make_document(project: dict, geometry: dict | None = None, *,
                  origin="collector_profile_generated_for_gui") -> dict:
    """Build a sidecar document from the same canonical collector geometry."""
    model = build_assumed_geometry(project) if geometry is None else geometry
    return {
        "schema": SCHEMA, "project_sha256": _hash(project),
        "geometry_sha256": _hash(model), "geometry": model,
        "geometry_origin": origin,
    }


def load_or_create(project: dict, source_path: str | Path, *, persist=True) -> dict:
    """Fail closed on an out-of-date sidecar; never silently accept stale geometry.

    The project hash covers positions, wiring, values and footprint overrides.
    If the project changed, rebuild from the collector's authoritative presets.
    """
    dest = sidecar_path(source_path)
    campaign_model = _collector_campaign_geometry(project, source_path)
    expected = campaign_model if campaign_model is not None else build_assumed_geometry(project)
    signature = _hash(project)
    if dest.exists():
        existing = json.loads(dest.read_text(encoding="utf-8"))
        if (isinstance(existing, dict) and existing.get("schema") == SCHEMA
                and existing.get("project_sha256") == signature
                and existing.get("geometry") == expected
                and existing.get("geometry_sha256") == _hash(expected)):
            return existing
    document = make_document(
        project, expected, origin=("collector_campaign" if campaign_model is not None
                                   else "collector_profile_generated_for_gui")
    )
    if persist:
        tmp = dest.with_name(dest.name + ".tmp")
        tmp.write_text(json.dumps(document, indent=2, ensure_ascii=False, allow_nan=False)
                       + "\n", encoding="utf-8")
        tmp.replace(dest)
    return document


def _definition(part, defs):
    definition = resolve_definition(part, defs)
    if definition is None:
        return None
    return definition


def _installed_shape(part: dict, definition: dict, entry: dict) -> dict | None:
    """Place one saved local-profile shape at the actual physical pin centroid.

    Shape centre comes from exact solved pin coordinates, not from guessed
    rotation origin. For 2-lead passives, orient rectangle long axis along the
    actual pin vector, including flexibleEndPos.
    """
    bodies = entry.get("body_solids") or []
    if not bodies:
        return None
    pins, body_cells = component_geometry(part, definition)
    if not pins:
        return None
    raw = bodies[0]
    # Universal fallback is based on the footprint's REAL installed cells.
    # Rebuild its XY envelope from the rotated/translated pin and occupancy
    # locations; do not pretend the pin centroid is a custom module centre.
    if entry.get("profile") == "footprint_envelope":
        places = [(float(pin["row"]), float(pin["col"])) for pin in pins]
        places.extend((float(row), float(col)) for row, col in body_cells)
        shape = {
            "shape": "rectangle",
            "x_min_mm": (min(x for _, x in places) - 0.5) * PITCH,
            "x_max_mm": (max(x for _, x in places) + 0.5) * PITCH,
            "y_min_mm": (min(y for y, _ in places) - 0.5) * PITCH,
            "y_max_mm": (max(y for y, _ in places) + 0.5) * PITCH,
        }
        shape.update({
            "id": str(part["id"]),
            "z_min_mm": raw["assumed_z_min_mm"],
            "z_max_mm": raw["assumed_z_max_mm"],
            "z_min_source": "assumed_standard",
        })
        return shape
    xs = [float(pin["col"]) * PITCH for pin in pins]
    ys = [float(pin["row"]) * PITCH for pin in pins]
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    raw = bodies[0]
    if raw["shape"] == "circle":
        shape = {"shape": "circle", "center_mm": [cx, cy],
                 "radius_mm": raw["radius_mm"]}
    elif raw["shape"] == "rectangle":
        w = raw["x_max_mm"] - raw["x_min_mm"]
        h = raw["y_max_mm"] - raw["y_min_mm"]
        # Local long dimension follows actual two-terminal direction.
        if len(pins) == 2 and abs(ys[1] - ys[0]) > abs(xs[1] - xs[0]):
            w, h = min(w, h), max(w, h)
        elif len(pins) == 2:
            w, h = max(w, h), min(w, h)
        elif int(part.get("rotation", 0) or 0) % 180 == 90:
            w, h = h, w
        shape = {"shape": "rectangle", "x_min_mm": cx - w / 2,
                 "x_max_mm": cx + w / 2, "y_min_mm": cy - h / 2,
                 "y_max_mm": cy + h / 2}
    else:
        raise ValueError("unsupported collector body shape")
    shape.update({
        "id": str(part["id"]), "z_min_mm": raw["assumed_z_min_mm"],
        "z_max_mm": raw["assumed_z_max_mm"],
        # Preserve collector provenance exactly; independent engines treat
        # assumed standoff as CONDITIONAL, not user-declared or measured.
        "z_min_source": "assumed_standard",
    })
    return shape


def assumed_body_pad_keepouts(project: dict) -> list[dict]:
    """Return installed nominal body XY shapes for lead-pad access screening.

    This is a conservative *design assumption*, not a measured package size.
    Uses exactly the same rotated/translated shapes as the 2.5D audit.
    The hole allocator can avoid proposing an external terminal beneath a
    component body even when that hole is unoccupied in the footprint grid.
    """
    geometry = build_assumed_geometry(project)
    definitions = dict(BUILTIN_DEFS)
    definitions.update({
        str(d["id"]): d for d in project.get("componentDefs", [])
        if isinstance(d, dict) and d.get("id")
    })
    components = {
        str(p["id"]): p for p in project.get("components", [])
        if isinstance(p, dict) and p.get("id") and not is_off_board_component(p)
        and isinstance(p.get("boardPos"), dict)
    }
    solids = []
    for entry in geometry["components"]:
        part = components.get(entry["id"])
        if part is None or not entry.get("body_solids"):
            continue
        definition = _definition(part, definitions)
        if definition is None:
            continue
        shape = _installed_shape(part, definition, entry)
        if shape is not None:
            shape["label"] = str(part.get("label") or part["id"])
            solids.append(shape)
    return solids


def assumed_pad_body_intersection(
    row: int, col: int, solids: list[dict], clearance_mm: float = 0.85,
) -> str | None:
    """Label of nominal body covering a proposed pad-access clearance disc."""
    from math import hypot
    x, y = col * PITCH, row * PITCH
    for solid in solids:
        if solid["shape"] == "circle":
            cx, cy = solid["center_mm"]
            distance = hypot(x - cx, y - cy) - solid["radius_mm"]
        else:
            dx = max(solid["x_min_mm"] - x, 0, x - solid["x_max_mm"])
            dy = max(solid["y_min_mm"] - y, 0, y - solid["y_max_mm"])
            distance = hypot(dx, dy)
        if distance < clearance_mm:
            return solid["label"]
    return None


def assumed_blocked_pad_holes(
    solids: list[dict], rows: int, cols: int, clearance_mm: float = 0.85,
) -> dict[tuple[int, int], str]:
    """Precompute only holes near nominal bodies, not every board hole per pin.

    This prevents the otherwise quadratic external-pad allocation slowdown
    on large boards or repeated Edge+Slide placement variants.
    """
    from math import ceil, floor
    blocked = {}
    for solid in solids:
        if solid["shape"] == "circle":
            cx, cy = solid["center_mm"]
            radius = solid["radius_mm"] + clearance_mm
            xmin, xmax = cx - radius, cx + radius
            ymin, ymax = cy - radius, cy + radius
        else:
            xmin = solid["x_min_mm"] - clearance_mm
            xmax = solid["x_max_mm"] + clearance_mm
            ymin = solid["y_min_mm"] - clearance_mm
            ymax = solid["y_max_mm"] + clearance_mm
        for row in range(max(0, ceil(ymin / PITCH)),
                         min(rows - 1, floor(ymax / PITCH)) + 1):
            for col in range(max(0, ceil(xmin / PITCH)),
                             min(cols - 1, floor(xmax / PITCH)) + 1):
                if (row, col) not in blocked:
                    obstacle = assumed_pad_body_intersection(
                        row, col, [solid], clearance_mm,
                    )
                    if obstacle is not None:
                        blocked[row, col] = obstacle
    return blocked


def _nominal_body_gap(a: dict, b: dict) -> float:
    """Signed XY perimeter gap (mm); negative means nominal overlap."""
    from math import hypot

    if a["shape"] == "circle" and b["shape"] == "circle":
        return hypot(a["center_mm"][0] - b["center_mm"][0],
                     a["center_mm"][1] - b["center_mm"][1]) - (
                         a["radius_mm"] + b["radius_mm"]
                     )
    if a["shape"] == "rectangle" and b["shape"] == "rectangle":
        x = max(a["x_min_mm"] - b["x_max_mm"],
                b["x_min_mm"] - a["x_max_mm"], 0)
        y = max(a["y_min_mm"] - b["y_max_mm"],
                b["y_min_mm"] - a["y_max_mm"], 0)
        if x or y:
            return hypot(x, y)
        return 0.0
    circle, rect = (
        (a, b) if a["shape"] == "circle" else (b, a)
    )
    x, y = circle["center_mm"]
    nearest_x = min(max(x, rect["x_min_mm"]), rect["x_max_mm"])
    nearest_y = min(max(y, rect["y_min_mm"]), rect["y_max_mm"])
    return hypot(x - nearest_x, y - nearest_y) - circle["radius_mm"]


def _point_nominal_body_gap(x: float, y: float, solid: dict) -> float:
    """Signed grid-point to assumed package-outline distance in millimetres."""
    from math import hypot
    if solid["shape"] == "circle":
        sx, sy = solid["center_mm"]
        return hypot(x - sx, y - sy) - solid["radius_mm"]
    dx = max(solid["x_min_mm"] - x, 0, x - solid["x_max_mm"])
    dy = max(solid["y_min_mm"] - y, 0, y - solid["y_max_mm"])
    return hypot(dx, dy)


def inspect_assumed_contacts(project: dict) -> list[dict]:
    """Advisory body/body and foreign pad/body contact from installed solids.

    This does NOT claim measured contact. It is independent of copper-net
    electrical PASS and is used to colour the same concerns red in the GUI.
    """
    from math import hypot
    from collector_geometry import CLEARANCE

    margin = CLEARANCE["min_clearance_mm"]
    pad_margin = (CLEARANCE["lead_radius_mm"]
                  + CLEARANCE["lead_margin_mm"]
                  + margin)
    solids = assumed_body_pad_keepouts(project)
    by_id = {str(p["id"]): p for p in project.get("components", [])
             if isinstance(p, dict) and p.get("id")}
    issues = []
    for i, a in enumerate(solids):
        for b in solids[i + 1:]:
            # Different z ranges imply no nominal three-dimensional body touch.
            if max(a["z_min_mm"], b["z_min_mm"]) >= min(
                a["z_max_mm"], b["z_max_mm"]
            ):
                continue
            gap = _nominal_body_gap(a, b)
            if gap < margin:
                issues.append({
                    "kind": "body_body", "component_ids": [a["id"], b["id"]],
                    "components": [a["label"], b["label"]],
                    "gap_mm": round(gap, 3),
                    "certainty": "ASSUMED_UNVERIFIED",
                })
    # A correct pin may still be under another body's nominal overhang.
    # Only check FOREIGN component pads; a capacitor's own pins sit underneath
    # its body by design and are not a clash.
    from board_geometry import component_geometry
    defs = dict(BUILTIN_DEFS)
    defs.update({str(d["id"]): d for d in project.get("componentDefs", [])
                 if isinstance(d, dict) and d.get("id")})
    for p in by_id.values():
        pid = str(p["id"])
        label = str(p.get("label") or pid)
        pins = []
        is_external = is_off_board_component(p)
        if is_external:
            if p.get("boardExcluded") is True and p.get("offBoard") is not True:
                continue
            for name, pad in (p.get("leads") or {}).items():
                pins.append((str(name), pad))
        elif isinstance(p.get("boardPos"), dict):
            definition = _definition(p, defs)
            if definition is not None:
                physical, _ = component_geometry(p, definition)
                pins.extend((str(pin["id"]), pin) for pin in physical)
        for pin, point in pins:
            row, col = int(point["row"]), int(point["col"])
            x, y = col * PITCH, row * PITCH
            for solid in solids:
                if solid["id"] == pid:
                    continue
                if solid["shape"] == "circle":
                    sx, sy = solid["center_mm"]
                    gap = hypot(x - sx, y - sy) - solid["radius_mm"]
                else:
                    dx = max(solid["x_min_mm"] - x, 0,
                             x - solid["x_max_mm"])
                    dy = max(solid["y_min_mm"] - y, 0,
                             y - solid["y_max_mm"])
                    gap = hypot(dx, dy)
                if gap < pad_margin:
                    issues.append({
                        "kind": "external_pad_body" if is_external else "pad_body",
                        "component_ids": [pid, solid["id"]],
                        "components": [label, solid["label"]],
                        "pad": {"row": row, "col": col, "pin": pin},
                        "gap_mm": round(gap, 3),
                        "certainty": "ASSUMED_UNVERIFIED",
                    })
    return issues


def assess_saved_board(project: dict, document: dict) -> dict:
    """Independent per-jumper 2.5D comparison using sidecar as source of truth."""
    if document.get("schema") != SCHEMA or document.get("project_sha256") != _hash(project):
        raise ValueError("geometry sidecar does not match project snapshot")
    model = document["geometry"]
    if document.get("geometry_sha256") != _hash(model):
        raise ValueError("geometry sidecar integrity mismatch")
    # A matching hash alone is insufficient: recompute the collector preset
    # and reject a substituted or stale model, even with a recomputed digest.
    if model != build_assumed_geometry(project):
        raise ValueError("geometry sidecar differs from authoritative collector preset")
    settings = model["clearance_assumptions"]
    defs = dict(BUILTIN_DEFS)
    defs.update({str(d["id"]): d for d in project.get("componentDefs", [])
                 if isinstance(d, dict) and d.get("id")})
    parts = {str(p["id"]): p for p in project.get("components", [])
             if isinstance(p, dict) and p.get("id") and not is_off_board_component(p)}
    solids = []
    unknown = []
    pin_records = []
    for entry in model["components"]:
        cid = entry["id"]
        if cid not in parts:
            continue
        definition = _definition(parts[cid], defs)
        if definition is None:
            unknown.append(entry.get("label") or cid)
            continue
        if isinstance(parts[cid].get("boardPos"), dict):
            pins, _ = component_geometry(parts[cid], definition)
            for pin in pins:
                pin_records.append({
                    "id": f"{cid}:{pin['id']}",
                    "center_mm": [pin["col"] * PITCH, pin["row"] * PITCH],
                })
        if not entry.get("body_solids"):
            unknown.append(entry.get("label") or cid)
            continue
        solid = _installed_shape(parts[cid], definition, entry)
        if solid is None:
            unknown.append(entry.get("label") or cid)
        else:
            solids.append(solid)
    findings = []
    by_wire = []
    counts = {"PASS": 0, "CONDITIONAL": 0, "FAIL_UNVERIFIED": 0,
              "FAIL_PROVEN": 0}
    for index, wire in enumerate(project.get("board", {}).get("wires", [])):
        a, b = wire["from"], wire["to"]
        endpoints = {
            (a["row"], a["col"]), (b["row"], b["col"]),
        }
        # Pin-hole centres are known from exact footprint geometry. A wire
        # touching an intermediate occupied hole is a HARD failure. Endpoint
        # landings are allowed here; the electrical verifier checks their net.
        occupied = [
            {**pin,
             "allowed_endpoint": (
                 (round(pin["center_mm"][1] / PITCH),
                  round(pin["center_mm"][0] / PITCH)) in endpoints
             )}
            for pin in pin_records
        ]
        # Lead radii are still hypothetical; the independent evaluators must
        # report a nominal lead clash as UNVERIFIED, never FAIL_PROVEN.
        leads = [
            {"id": pin["id"], "center_mm": pin["center_mm"],
             "radius_mm": settings["lead_radius_mm"],
             "source": "assumed_standard",
             "allowed_endpoint": pin["allowed_endpoint"]}
            for pin in occupied
        ]
        case = {
            "jumper": {"from_mm": [a["col"] * PITCH, a["row"] * PITCH],
                       "to_mm": [b["col"] * PITCH, b["row"] * PITCH]},
            "settings": settings,
            "body_solids": solids,
            "occupied_holes": occupied,
            "leads": leads,
        }
        router = classify_jumper(case)
        independent = verify_jumper_25d(case)
        if router["verdict"] != independent["verdict"] or router["findings"] != independent["findings"]:
            raise ValueError(f"independent 2.5D disagreement on {wire.get('id', index)}")
        verdict = independent["verdict"]
        counts[verdict] += 1
        by_wire.append({"id": str(wire.get("id", index)), "verdict": verdict,
                        "findings": independent["findings"]})
        for finding in independent["findings"]:
            findings.append({"wire": str(wire.get("id", index)), **finding})
    # A design-estimate PASS cannot be a physical PASS. Even a geometrically
    # unobstructed wire is conditional upon the actual package size/wiring.
    if counts["FAIL_PROVEN"]:
        status = "HARD_CONFLICT"
    elif counts["FAIL_UNVERIFIED"] or unknown:
        status = "UNVERIFIED"
    else:
        status = "ASSUMED_CLEARANCE_PASS"
    contacts = inspect_assumed_contacts(project)
    return {
        "status": status,
        "counts": counts,
        "wire_results": by_wire,
        "findings": findings,
        "unknown_bodies": sorted(unknown),
        "profile": model["preset"],
        "physical_signoff": False,
        "contact_findings": contacts,
        "contacts_status": "ASSUMED_CONTACT_RISK" if contacts else "ASSUMED_CONTACT_CLEAR",
        "scope": "assumed-body-and-lead-clearance with hard occupied-pin-hole check; nominal body/pad contacts advisory; electrical nets and cut access separately verified",
    }


__all__ = ["sidecar_path", "make_document", "load_or_create", "assess_saved_board", "assumed_body_pad_keepouts", "assumed_pad_body_intersection", "assumed_blocked_pad_holes",
           "inspect_assumed_contacts"]
