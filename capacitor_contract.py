"""Capacitor package contract shared by collector and production-renderer bridge.

The stripboard-optimiser's default package selection is reproduced here so a
capacitance value is not one body in the 2.5D sidecar and a different body in
the SVG. Dimensions are NOMINAL upstream artwork assumptions, not measured
packages or construction certification.

Source of comparison: src/frontend/components/stripboard/packageBodies.ts
and componentValues.ts in stripboard-optimiser.
"""
from __future__ import annotations

import math
import re
from typing import Any

PACKAGES = ("cap-ceramic", "cap-film", "cap-elko")
CAP_DEF_IDS = frozenset(("def-capacitor", "def-cap-polarized"))


def capacitance_farads(value: Any) -> float | None:
    """Match upstream parseCapacitance for p, n, u/micro and m prefixes."""
    if not isinstance(value, str) or not value:
        return None
    s = value.lower().replace(",", ".")
    s = re.sub(r"\s+", "", s)
    match = re.match(r"^(\d*\.?\d+)(mü|mu|[µμ]|[unpm])(\d*)", s)
    if match is None:
        return None
    head, raw_unit, tail = match.groups()
    unit = "u" if raw_unit in ("mü", "mu", "µ", "μ") else raw_unit
    try:
        number = float(f"{head}.{tail}" if tail else head)
        result = number * {"p": 1e-12, "n": 1e-9,
                           "u": 1e-6, "m": 1e-3}[unit]
        return result if math.isfinite(result) and result >= 0 else None
    except (ValueError, OverflowError):
        return None


def resolved_capacitor_package(part: dict) -> str | None:
    """Return precisely the package the upstream renderer should choose."""
    kind = str(part.get("defId") or part.get("componentDefId") or "")
    if kind not in CAP_DEF_IDS:
        return None
    selected = part.get("package")
    if selected in PACKAGES:
        return selected
    if kind == "def-cap-polarized":
        return "cap-elko"
    farads = capacitance_farads(part.get("value"))
    return "cap-film" if farads is not None and farads >= 470e-9 else "cap-ceramic"


def capacitor_body_spec(part: dict) -> dict | None:
    """Nominal visible shape and dimensions, tracking upstream packageBodies."""
    package = resolved_capacitor_package(part)
    if package is None:
        return None
    farads = capacitance_farads(part.get("value"))
    if package == "cap-ceramic":
        if farads is None:
            diameter = 5.0
        elif farads >= 100e-9:
            diameter = 5.0
        elif farads >= 10e-9:
            diameter = 4.0
        elif farads >= 1e-9:
            diameter = 3.5
        else:
            diameter = 3.0
        return {"package": package, "shape": "rectangle",
                "major_mm": diameter, "minor_mm": min(2.4, diameter * 0.6)}
    if package == "cap-film":
        return {"package": package, "shape": "rectangle",
                "major_mm": 7.2, "minor_mm": 2.5}
    uf = (farads if farads is not None else 100e-6) * 1e6
    if uf <= 4.7:
        diameter = 4.0
    elif uf <= 47:
        diameter = 5.0
    elif uf <= 100:
        diameter = 6.3
    elif uf <= 330:
        diameter = 8.0
    elif uf <= 1000:
        diameter = 10.0
    elif uf <= 2200:
        diameter = 12.5
    else:
        diameter = 16.0
    return {"package": package, "shape": "circle",
            "major_mm": diameter, "minor_mm": diameter}


def capacitor_contract_notes(part: dict) -> list[str]:
    kind = str(part.get("defId") or part.get("componentDefId") or "")
    if kind not in CAP_DEF_IDS:
        return []
    selected = part.get("package")
    notes = []
    if selected and selected not in PACKAGES:
        notes.append("unrecognised_capacitor_package_renderer_uses_default")
    package = resolved_capacitor_package(part)
    if kind == "def-capacitor" and package == "cap-elko":
        notes.append("nonpolarized_symbol_with_electrolytic_body_user_selected")
    if kind == "def-cap-polarized" and package != "cap-elko":
        notes.append("polarized_symbol_with_nonpolarized_body_user_selected")
    if capacitance_farads(part.get("value")) is None:
        notes.append("capacitance_unparsed_nominal_body_only")
    return notes


__all__ = ["CAP_DEF_IDS", "PACKAGES", "capacitance_farads",
           "resolved_capacitor_package", "capacitor_body_spec",
           "capacitor_contract_notes"]
