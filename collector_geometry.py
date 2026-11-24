"""Versioned, deterministic *assumed* package geometry for collected projects.

Coordinates are UNROTATED FOOTPRINT-LOCAL millimetres, not board absolute.
These are design exploration defaults, never measured values or construction
certification. The sidecar is not automatically trusted by the 2.5D verifier.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any

from capacitor_contract import (
    capacitor_body_spec, capacitor_contract_notes,
    resolved_capacitor_package, capacitance_farads,
)

PITCH_MM = 2.54
SCHEMA = "route-mate/assumed-geometry/1.0"
PRESET_VERSION = "standard-through-hole-v3"
CLEARANCE = {
    "wire_od_mm": 0.9,
    "min_clearance_mm": 0.3,
    "z_margin_mm": 0.3,
    "lead_radius_mm": 0.35,
    "lead_margin_mm": 0.2,
    "search_preference_margin_mm": 0.0,
}
# No footprint-agnostic mounting height is inferred.
# None means unknown: never convert to a measured or verified clearance.
PROFILES = {
    "electrolytic_small": ("circle", 5.0, 1.5, 8.0),
    "electrolytic_medium": ("circle", 6.3, 1.5, 12.0),
    "electrolytic_large": ("circle", 10.0, 1.5, 20.0),
    "ceramic": ("rectangle", 4.0, 2.5, 1.5),
    "film": ("rectangle", 7.2, 2.5, 1.8),
    "resistor": ("rectangle", 6.3, 2.5, 1.2),
    "diode": ("rectangle", 4.0, 2.5, 1.2),
    "led": ("circle", 5.0, 1.0, 7.0),
    "to92": ("rectangle", 4.8, 3.8, 3.5),
    "to220": ("rectangle", 10.0, 4.5, 3.0),
}
# The universal fallback is an explicitly assumed envelope, derived from
# the FOOTPRINT dimensions/occupied cells, never from a component label.
# Standoff and nominal height are deliberately visible in the versioned preset:
# they are design hypotheses, NOT measurements of the installed component.
FOOTPRINT_ENVELOPE_ASSUMPTIONS = {
    "standoff_mm": 1.5,
    "body_height_mm": 2.54,
}

# Height tuple member is nominal body height, not clearance to board.
# Installation standoffs are intentionally fixed assumptions, NOT measurements.
ASSUMED_STANDOFF_MM = {
    "electrolytic_small": 1.5, "electrolytic_medium": 1.5,
    "electrolytic_large": 1.5, "ceramic": 1.0, "film": 1.0,
    "resistor": 1.0, "diode": 1.0, "led": 1.0,
    "to92": 2.0, "to220": 2.5,
}


def _finite(value: Any, what: str, minimum: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{what} must be numeric")
    number = float(value)
    if not math.isfinite(number) or number < minimum:
        raise ValueError(f"{what} must be finite and >= {minimum}")
    return number


def _pins(definition: dict) -> list[dict[str, Any]]:
    out = []
    for index, pin in enumerate(definition.get("pins") or []):
        if not isinstance(pin, dict):
            raise ValueError("footprint has non-object pin")
        row = _finite(pin.get("offsetRow", 0), "pin row")
        col = _finite(pin.get("offsetCol", 0), "pin col")
        out.append({
            "id": str(pin.get("id", index + 1)),
            "x_mm": round(col * PITCH_MM, 6),
            "y_mm": round(row * PITCH_MM, 6),
            "lead_radius_mm": CLEARANCE["lead_radius_mm"],
            "source": "footprint_pin_with_assumed_lead_radius",
        })
    return out


def _profile(component: dict) -> str | None:
    kind = str(component.get("defId") or component.get("componentDefId") or "").lower()
    package = str(component.get("package") or "").lower().replace("-", "").replace("_", "")
    if package.startswith("to220"):
        return "to220"
    if package.startswith("to92"):
        return "to92"
    cap = capacitor_body_spec(component)
    if cap is not None:
        if cap["package"] == "cap-ceramic":
            return "ceramic"
        if cap["package"] == "cap-film":
            return "film"
        uf = (capacitance_farads(component.get("value")) or 0) * 1e6
        if uf >= 470:
            return "electrolytic_large"
        if uf >= 47:
            return "electrolytic_medium"
        return "electrolytic_small"
    return {
        "def-resistor": "resistor",
        "def-diode": "diode",
        "def-zener": "diode",
        "def-led": "led",
        "def-npn": "to92",
        "def-pnp": "to92",
        "def-nmos": "to92",
        "def-pmos": "to92",
    }.get(kind)


def _body(profile: str, pins: list[dict],
          cap_spec: dict | None = None) -> dict:
    shape, major, minor, height = PROFILES[profile]
    if cap_spec is not None:
        shape = cap_spec["shape"]
        major, minor = cap_spec["major_mm"], cap_spec["minor_mm"]
    cx = sum(pin["x_mm"] for pin in pins) / len(pins)
    cy = sum(pin["y_mm"] for pin in pins) / len(pins)
    if shape == "circle":
        solid = {"shape": "circle", "center_mm": [round(cx, 6), round(cy, 6)],
                 "radius_mm": major / 2}
    else:
        # Longer axis follows pin-to-pin vector for two-lead passives.
        # Three-pin TO-92 and TO-220 bodies are transverse to pin row.
        if profile in {"to92", "to220"}:
            w, h = major, minor
        elif len(pins) == 2 and abs(pins[0]["y_mm"] - pins[1]["y_mm"]) >= abs(
                pins[0]["x_mm"] - pins[1]["x_mm"]):
            w, h = minor, major
        else:
            w, h = major, minor
        solid = {
            "shape": "rectangle",
            "x_min_mm": round(cx - w / 2, 6),
            "x_max_mm": round(cx + w / 2, 6),
            "y_min_mm": round(cy - h / 2, 6),
            "y_max_mm": round(cy + h / 2, 6),
        }
    standoff = ASSUMED_STANDOFF_MM[profile]
    return {
        **solid, "body_height_mm": height,
        "assumed_standoff_mm": standoff,
        "assumed_z_min_mm": standoff,
        "assumed_z_max_mm": round(standoff + height, 6),
        "installation_clearance": "CONDITIONAL_ASSUMED",
        "provenance": {"kind": "assumed_standard", "preset": PRESET_VERSION,
                       "profile": profile},
    }


def _footprint_envelope(definition: dict, pins: list[dict]) -> dict:
    """Assumed generic body, with XY extent derived from saved footprint.

    Unlike artwork-only proxies, this is deliberately opt-in as an ASSUMED
    bounding envelope in standard-through-hole-v2; it makes no measured-size
    claim. The board audit will reproject the complete actual pin/body geometry
    after rotations and flexible endpoints.
    """
    rows = [pin["y_mm"] / PITCH_MM for pin in pins]
    cols = [pin["x_mm"] / PITCH_MM for pin in pins]
    for cell in definition.get("bodyCells") or []:
        if not isinstance(cell, dict):
            raise ValueError("footprint contains non-object bodyCell")
        rows.append(_finite(cell.get("row"), "body cell row"))
        cols.append(_finite(cell.get("col"), "body cell col"))
    if not rows or not cols:
        raise ValueError("footprint envelope requires known pins or body cells")
    extent = {
        "shape": "rectangle",
        "x_min_mm": round((min(cols) - 0.5) * PITCH_MM, 6),
        "x_max_mm": round((max(cols) + 0.5) * PITCH_MM, 6),
        "y_min_mm": round((min(rows) - 0.5) * PITCH_MM, 6),
        "y_max_mm": round((max(rows) + 0.5) * PITCH_MM, 6),
    }
    standoff = FOOTPRINT_ENVELOPE_ASSUMPTIONS["standoff_mm"]
    height = FOOTPRINT_ENVELOPE_ASSUMPTIONS["body_height_mm"]
    return {
        **extent, "body_height_mm": height,
        "assumed_standoff_mm": standoff,
        "assumed_z_min_mm": standoff,
        "assumed_z_max_mm": round(standoff + height, 6),
        "installation_clearance": "CONDITIONAL_ASSUMED",
        "provenance": {
            "kind": "assumed_standard", "preset": PRESET_VERSION,
            "profile": "footprint_envelope",
            "xy_basis": "footprint_pins_and_bodyCells",
            "dimensions_measured": False,
        },
    }


def _artwork_proxies(definition: dict) -> list[dict[str, Any]]:
    """Soft bounding box of footprint bodyCells; never a hard body solid."""
    cells = definition.get("bodyCells") or []
    if not cells:
        return []
    rows, cols = [], []
    for cell in cells:
        if not isinstance(cell, dict):
            raise ValueError("footprint bodyCells contains non-object")
        rows.append(_finite(cell.get("row"), "body cell row"))
        cols.append(_finite(cell.get("col"), "body cell col"))
    return [{
        "shape": "rectangle",
        "x_min_mm": round((min(cols) - 0.5) * PITCH_MM, 6),
        "x_max_mm": round((max(cols) + 0.5) * PITCH_MM, 6),
        "y_min_mm": round((min(rows) - 0.5) * PITCH_MM, 6),
        "y_max_mm": round((max(rows) + 0.5) * PITCH_MM, 6),
        "source": "footprint_bodyCells_proxy",
        "routing_role": "ADVISORY_ONLY",
    }]


def build_assumed_geometry(project: dict) -> dict:
    """Build an advisory sidecar without mutating the exported project."""
    if not isinstance(project, dict):
        raise ValueError("project must be an object")
    definitions = {
        str(d["id"]): d for d in project.get("componentDefs", [])
        if isinstance(d, dict) and d.get("id")
    }
    # Import only exact logical footprint templates: they give pin coordinates,
    # NOT real measured package dimensions.
    from board_geometry import BUILTIN_DEFS
    entries = []
    for part in project.get("components", []):
        if not isinstance(part, dict):
            raise ValueError("component must be an object")
        cid = str(part.get("id") or "")
        if not cid:
            raise ValueError("component missing ID")
        did = str(part.get("defId") or part.get("componentDefId") or "")
        defined = definitions.get(did) or BUILTIN_DEFS.get(did)
        override = part.get("footprintOverride")
        if not isinstance(defined, dict) and not isinstance(override, dict):
            entries.append({"id": cid, "defId": did, "label": str(part.get("label") or ""),
                            "status": "UNVERIFIED", "reason": "footprint_unresolved",
                            "pins": [], "body_solids": []})
            continue
        definition = dict(defined or {})
        if isinstance(override, dict):
            for key in ("pins", "width", "height", "bodyCells"):
                if key in override:
                    definition[key] = override[key]
        pins = _pins(definition)
        if not pins:
            entries.append({"id": cid, "defId": did, "label": str(part.get("label") or ""),
                            "status": "UNVERIFIED", "reason": "footprint_has_no_pins",
                            "pins": [], "body_solids": []})
            continue
        profile = _profile(part)
        # Unknown package names are NOT silently empty bodies: build one
        # generic assumed envelope from the actual source footprint data.
        # Its geometry remains conditional and must be measured before build.
        if profile:
            body = [_body(profile, pins, capacitor_body_spec(part))]
        else:
            profile = "footprint_envelope"
            body = [_footprint_envelope(definition, pins)]
        artwork_proxies = _artwork_proxies(definition)
        reasons = capacitor_contract_notes(part)
        if profile == "footprint_envelope":
            reasons.append("body_extents_from_footprint_not_measured")
        if body:
            reasons.append("installed_standoff_is_assumed_not_measured")
        if isinstance(override, dict) and "bodyCells" in override:
            reasons.append("footprint_bodyCells_are_not_measured_solids")
        entries.append({
            "id": cid, "defId": did, "label": str(part.get("label") or ""),
            "status": "ASSUMED_UNVERIFIED" if body else "UNVERIFIED",
            "package_hint": str(part.get("package") or ""),
            "render_package": resolved_capacitor_package(part),
            "profile": profile,
            "pins": pins, "body_solids": body,
            "artwork_proxies": artwork_proxies,
            "notes": reasons,
            "frame": "unrotated_footprint_local_mm",
            "off_board": bool(part.get("offBoard") or part.get("boardExcluded")),
        })
    # IDs must not silently alias different physical profiles.
    ids = [e["id"] for e in entries]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate component IDs")
    entries.sort(key=lambda x: x["id"])
    digest = hashlib.sha256(json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {
        "schema": SCHEMA, "preset": PRESET_VERSION, "grid_pitch_mm": PITCH_MM,
        "coordinate_frame": "unrotated_footprint_local_mm",
        "clearance_assumptions": {**CLEARANCE, "provenance": "assumed_standard"},
        "policy": {
            "routing_use": "advisory_only_until_placement_transforms_and_spec_amendment",
            "physical_verification": "NOT_BUILD_READY",
            "assumed_standoff": "CONDITIONAL_ASSUMED_NOT_VERIFIED",
            "unknown_standoff": "FAIL_UNVERIFIED",
            "intermediate_occupied_holes": "HARD_BLOCK",
            "artwork": "NOT_HARD_BODY",
            "fallback_body": "FOOTPRINT_ENVELOPE_ASSUMED_NOT_MEASURED",
            "cut_tool_access": "UNVERIFIED",
            "thermal": "UNVERIFIED_UNLESS_EXPLICITLY_DOCUMENTED",
        },
        "component_count": len(entries),
        "unverified_count": sum(x["status"] == "UNVERIFIED" for x in entries),
        "components": entries, "components_sha256": digest,
    }


__all__ = ["build_assumed_geometry", "CLEARANCE", "SCHEMA", "PRESET_VERSION", "FOOTPRINT_ENVELOPE_ASSUMPTIONS"]
