#!/usr/bin/env python3
"""Collect a Karl/Stripboard Editor project into the legacy solver campaign format.

This ports the useful preparation steps found in stripboard-optimiser:
- validate project JSON shape;
- normalise the fields used by the GUI's prepareProjectState();
- merge missing custom footprints from a KiCad .pretty ZIP/directory;
- compare .net node count with JSON netAssignments (desktop GUI preflight);
- freeze one project as data/projects/<id>.json and write data/index.json.

It deliberately does not invent connectivity. The GUI recalculates nets from
schematic wires, labels and pin geometry; this collector preserves the exported
JSON nets/assignments and reports the .net comparison. Exact connectivity
recalculation will be shared with the engine rather than approximated here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any

from placement_policy import is_off_board_component
from collector_geometry import build_assumed_geometry

DEFAULT_IDS = {
    "def-resistor", "def-capacitor", "def-cap-polarized", "def-led",
    "def-diode", "def-potentiometer", "def-switch", "def-zener",
    "def-pushbutton", "def-inductor", "def-fuse", "def-transformer",
    "def-npn", "def-pnp", "def-nmos", "def-pmos", "def-555",
    "def-esp32-devkit-v1", "def-esp32-devkit-v1-36",
    "def-esp32-devkitc-38", "def-arduino-nano", "def-trimpot",
    "def-opamp", "def-vreg", "def-optocoupler",
    "def-generic-3pin-compact", "def-generic-3pin-spaced",
}
DEFAULT_IDS.update(f"def-connector-{n}" for n in range(1, 21))
DEFAULT_IDS.update(f"def-ic-dip{n}" for n in (4, 6, 8, 10, 12, 14, 16, 18, 20, 24, 28, 32, 36, 40))
DEFAULT_IDS.update(f"def-generic-2pin-{n}h" for n in (2, 3, 4, 5, 7))

def is_default_id(value: str | None) -> bool:
    if not value:
        return False
    return (
        value in DEFAULT_IDS
        or value.startswith("def-ic-")
        or bool(re.fullmatch(r"def-generic-2pin-\d+h", value))
    )

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def norm_name(value: str) -> str:
    return re.sub(r"[\s_-]+", "", value).lower()

def component_def_id(component: dict[str, Any]) -> str | None:
    value = component.get("defId") or component.get("componentDefId")
    return str(value) if value else None

# Karl's editor exports some built-in pin IDs as symbols while its
# netAssignments retain the stable numeric pin IDs used by the solver.
# Only exact, known legacy sequences are translated; pin order and all
# physical geometry remain untouched.
BUILTIN_PIN_ALIASES = {
    "def-diode": ("a", "k"),
    "def-zener": ("a", "k"),
    "def-led": ("a", "k"),
    "def-cap-polarized": ("+", "-"),
    "def-npn": ("b", "c", "e"),
    "def-pnp": ("b", "c", "e"),
    "def-pmos": ("g", "d", "s"),
    "def-nmos": ("g", "d", "s"),
}


def canonicalise_builtin_pin_ids(data: dict[str, Any]) -> list[str]:
    """Translate known Karl built-in pin aliases to stable 1-based IDs.

    The saved definition's pin order, names, offsets, dimensions and body
    cells are preserved. Unknown sequences are left unchanged for sanity
    validation to reject rather than guessed.
    """
    warnings: list[str] = []
    definitions = data.get("componentDefs") or []
    if not isinstance(definitions, list):
        return warnings
    for definition in definitions:
        if not isinstance(definition, dict):
            continue
        definition_id = str(definition.get("id") or "")
        aliases = BUILTIN_PIN_ALIASES.get(definition_id)
        pins = definition.get("pins")
        if not aliases or not isinstance(pins, list):
            continue
        ids = tuple(str(pin.get("id", "")).casefold()
                    for pin in pins if isinstance(pin, dict))
        if len(ids) != len(pins):
            warnings.append(f"{definition_id}: malformed pin entry; IDs not normalised")
            continue
        if ids == tuple(str(i) for i in range(1, len(pins) + 1)):
            continue
        if ids != aliases:
            warnings.append(
                f"{definition_id}: unrecognised saved pin IDs {ids}; left unchanged"
            )
            continue
        for index, pin in enumerate(pins, 1):
            pin["id"] = str(index)
        warnings.append(
            f"{definition_id}: normalised legacy pin IDs {ids} to "
            f"{tuple(str(i) for i in range(1, len(pins) + 1))}; geometry preserved"
        )
    return warnings


def validate_project(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("project JSON root must be an object")
    for key in ("components", "nets", "netAssignments"):
        if key not in data or not isinstance(data[key], list):
            raise ValueError(f"project JSON must contain an array named {key!r}")
    if not isinstance(data.get("board"), dict):
        raise ValueError("project JSON must contain a board object")
    for key in ("components", "nets", "netAssignments"):
        if any(not isinstance(item, dict) for item in data[key]):
            raise ValueError(f"every item in {key!r} must be an object")
    warnings = canonicalise_builtin_pin_ids(data)
    if warnings:
        data.setdefault("_collectWarnings", []).extend(warnings)
    return data

def parse_kicad_mod(text: str) -> dict[str, Any] | None:
    """Port of the old GUI's pad/label-to-stripboard-footprint conversion."""
    pads = []
    for m in re.finditer(
        r'\(pad\s+"([^"]+)"[^(]*\(at\s+(-?[\d.]+)\s+(-?[\d.]+)',
        text,
    ):
        pads.append({"id": m.group(1), "x": float(m.group(2)), "y": float(m.group(3))})
    if not pads:
        return None

    labels = []
    for m in re.finditer(
        r'\(fp_text user\s+"([^"]+)"\s+\(at\s+(-?[\d.]+)\s+(-?[\d.]+)',
        text,
    ):
        labels.append({"name": m.group(1), "x": float(m.group(2)), "y": float(m.group(3))})

    for pad in pads:
        pad["name"] = next(
            (label["name"] for label in labels
             if abs(pad["x"] - label["x"]) < 0.1 and abs(pad["y"] - label["y"]) < 0.1),
            pad["id"],
        )

    min_x = min(p["x"] for p in pads)
    min_y = min(p["y"] for p in pads)
    max_x = max(p["x"] for p in pads)
    max_y = max(p["y"] for p in pads)
    width = int(round((max_x - min_x) / 2.54)) + 1
    height = int(round((max_y - min_y) / 2.54)) + 1
    pins = [
        {
            "id": p["id"], "name": p["name"],
            "offsetRow": int(round((p["y"] - min_y) / 2.54)),
            "offsetCol": int(round((p["x"] - min_x) / 2.54)),
        }
        for p in pads
    ]
    pin_cells = {(p["offsetRow"], p["offsetCol"]) for p in pins}
    body = [
        {"row": row, "col": col}
        for row in range(height) for col in range(width)
        if (row, col) not in pin_cells
    ]
    return {"width": width, "height": height, "pins": pins, "bodyCells": body}

def read_footprints(source: Path) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Read .kicad_mod files from a .pretty directory, ZIP, or single file."""
    result: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []

    def add(name: str, raw: str) -> None:
        stem = Path(name).name
        if stem.endswith(".kicad_mod"):
            stem = stem[:-len(".kicad_mod")]
        parsed = parse_kicad_mod(raw)
        if parsed:
            result[stem] = parsed

    if source.is_dir():
        for file in sorted(source.rglob("*.kicad_mod")):
            if file.name.startswith("._"):
                continue
            add(file.name, file.read_text(encoding="utf-8", errors="replace"))
    elif zipfile.is_zipfile(source):
        with zipfile.ZipFile(source) as archive:
            for name in sorted(archive.namelist()):
                if name.endswith(".kicad_mod") and not Path(name).name.startswith("._"):
                    add(name, archive.read(name).decode("utf-8", errors="replace"))
    else:
        # Also accept a single modern .kicad_mod file. Legacy KiCad .mod
        # libraries are not silently misread as modern S-expressions.
        if source.suffix == ".kicad_mod":
            add(source.name, source.read_text(encoding="utf-8", errors="replace"))
        else:
            warnings.append(
                f"{source.name}: not a .pretty directory/ZIP or .kicad_mod; "
                "no footprints parsed (legacy .mod syntax is not yet supported)"
            )
    return result, warnings

def merge_footprints(data: dict[str, Any], footprints: dict[str, dict[str, Any]]) -> dict[str, Any]:
    defs = data.setdefault("componentDefs", [])
    if not isinstance(defs, list):
        raise ValueError("componentDefs must be an array")
    existing = {str(d.get("id")) for d in defs if isinstance(d, dict) and d.get("id")}
    parsed_names = list(footprints)

    for component in data["components"]:
        did = component_def_id(component)
        if not did or did in existing or is_default_id(did):
            continue
        label = str(component.get("label") or component.get("name") or "")
        clean = norm_name(label)
        if not clean:
            continue
        matches = [
            name for name in parsed_names
            if clean in norm_name(name) or norm_name(name) in clean
        ]
        if not matches:
            continue
        # Match the GUI's first-match rule, but keep an audit warning if it
        # could have selected a different footprint.
        chosen = matches[0]
        definition = dict(footprints[chosen])
        definition.update({
            "id": did,
            "name": label,
            "category": "generic",
            "symbol": f"custom-footprint-{did}",
            "defaultLabelPrefix": "?",
        })
        defs.append(definition)
        existing.add(did)
        if len(matches) > 1:
            data.setdefault("_collectWarnings", []).append(
                f"{label}: multiple footprint filename matches {matches}; GUI first-match rule chose {chosen}"
            )
    return data

def normalise_like_gui(data: dict[str, Any]) -> dict[str, Any]:
    """Mirror prepareProjectState() defaults without rewriting source identity."""
    default_ids = DEFAULT_IDS
    saved_defs = data.get("componentDefs") or []
    if not isinstance(saved_defs, list):
        raise ValueError("componentDefs must be an array")
    # Preserve every saved definition. Karl's solved exports include the
    # actual footprint geometry used for placement; replacing those built-ins
    # with the local registry can change pin coordinates and board occupancy.
    data["componentDefs"] = [
        d for d in saved_defs if isinstance(d, dict) and d.get("id")
    ]
    data["components"] = [
        {**c, "schematicRotation": c.get("schematicRotation", 0)}
        for c in data["components"]
    ]
    data["netLabels"] = data.get("netLabels") or []
    data["schematicWires"] = data.get("schematicWires") or []
    data["wiring"] = data.get("wiring") or "classic"
    board = data["board"]
    # Physical and wanted dimensions are supplied explicitly by collect.py.
    board["cuts"] = board.get("cuts") or []
    board["wires"] = board.get("wires") or []
    return data

# Adapted from stripboard-optimiser/desktop/src/stripboard_optimizer/board_estimator.py
# Original estimator and sizing helpers are GPL-3.0-only; see licenses/GPL-3.0.txt.
ESTIMATOR_ROUTING_FACTOR = 3.2
ESTIMATOR_ASPECT = 2.33
ESTIMATOR_GAP = 1
ESTIMATOR_BUILTIN_SIZES = {
    "def-resistor": (1, 4), "def-diode": (1, 4), "def-zener": (1, 4),
    "def-led": (1, 2), "def-capacitor": (1, 2), "def-cap-polarized": (1, 2),
    "def-fuse": (1, 3), "def-inductor": (1, 3),
    "def-npn": (1, 3), "def-pnp": (1, 3), "def-pmos": (1, 3), "def-nmos": (1, 3),
    "def-connector-2": (1, 2), "def-switch": (1, 2), "def-pushbutton": (2, 2),
}

def _valid_size(source: Any) -> tuple[int, int] | None:
    """Read declared dimensions, or derive a bounding box from pin/body geometry."""
    if not isinstance(source, dict):
        return None
    try:
        width, height = source.get("width"), source.get("height")
        if width is not None and height is not None:
            width, height = int(width), int(height)
            return (width, height) if width > 0 and height > 0 else None
    except (TypeError, ValueError):
        return None

    rows, cols = [], []
    for pin in source.get("pins", []):
        if isinstance(pin, dict):
            try:
                rows.append(int(pin.get("offsetRow", 0)))
                cols.append(int(pin.get("offsetCol", 0)))
            except (TypeError, ValueError):
                continue
    for cell in source.get("bodyCells", []):
        if isinstance(cell, dict):
            try:
                rows.append(int(cell.get("row", 0)))
                cols.append(int(cell.get("col", 0)))
            except (TypeError, ValueError):
                continue
    if not rows or not cols:
        return None
    return max(cols) - min(0, min(cols)) + 1, max(rows) - min(0, min(rows)) + 1

def estimate_board(components: list[dict[str, Any]], component_defs: list[dict[str, Any]],
                   factor: float = ESTIMATOR_ROUTING_FACTOR,
                   aspect: float = ESTIMATOR_ASPECT) -> dict[str, Any]:
    """Advisory board-size estimate; never changes physical board limits."""
    if not math.isfinite(factor) or factor <= 0:
        raise ValueError("estimator routing factor must be positive")
    if not math.isfinite(aspect) or aspect <= 0:
        raise ValueError("estimator aspect ratio must be positive")
    definitions = {str(d["id"]): d for d in component_defs
                   if isinstance(d, dict) and d.get("id")}
    included, unknown, excluded = [], [], 0
    for component in components:
        if is_off_board_component(component):
            excluded += 1
            continue
        did = component_def_id(component)
        override = _valid_size(component.get("footprintOverride"))
        size = override or _valid_size(definitions.get(did or ""))
        source = "component override" if override else "project definition" if size else ""
        if size is None and did in ESTIMATOR_BUILTIN_SIZES:
            size, source = ESTIMATOR_BUILTIN_SIZES[did], "built-in estimate"
        if size is None:
            size, source = (2, 2), "fallback estimate"
            unknown.append(str(component.get("label") or component.get("id") or did or "unnamed"))
        width, height = size
        try:
            rotation = int(component.get("rotation", 0)) % 360
        except (TypeError, ValueError):
            rotation = 0
        if rotation in (90, 270):
            width, height = height, width
        included.append({"label": str(component.get("label") or component.get("id") or did or "unnamed"),
                         "width": width, "height": height, "source": source})
    raw = sum(p["width"] * p["height"] for p in included)
    padded = sum((p["width"] + ESTIMATOR_GAP) * (p["height"] + ESTIMATOR_GAP) for p in included)
    target = padded * factor
    longest = max((max(p["width"], p["height"]) for p in included), default=1)
    rows = max(longest + 2, round(math.sqrt(target / aspect)))
    cols = max(1, math.ceil(target / rows))
    roomy_rows, roomy_cols = rows + 4, math.ceil(cols * 1.25)
    return {
        "included_parts": len(included), "excluded_parts": excluded,
        "raw_holes": raw, "padded_holes": padded, "target_holes": round(target),
        "rows": rows, "cols": cols, "board_holes": rows * cols,
        "tight": {"rows": rows, "cols": cols, "holes": rows * cols},
        "roomy": {"rows": roomy_rows, "cols": roomy_cols, "holes": roomy_rows * roomy_cols},
        "routing_factor": factor, "aspect_ratio": aspect, "gap_holes": ESTIMATOR_GAP,
        "unknown_size_parts": unknown,
    }

def count_netlist_nodes(path: Path) -> int:
    # Same contract as desktop ImportService.count_netlist_nodes().
    text = path.read_text(encoding="utf-8", errors="replace")
    return len(re.findall(r"(?m)^\s*\(node\s+\(ref\b", text))

def netlist_hash(data: dict[str, Any]) -> str:
    def_id = {str(c.get("id")): component_def_id(c) for c in data["components"]}
    nets: dict[str, list[str]] = {}
    for assignment in data["netAssignments"]:
        net_id = str(assignment.get("netId", ""))
        nets.setdefault(net_id, []).append(
            f"{def_id.get(str(assignment.get('componentId')), '?')}:{assignment.get('pinId', '?')}"
        )
    signature = sorted("|".join(sorted(pins)) for pins in nets.values())
    return hashlib.sha1(json.dumps(signature, separators=(",", ":")).encode()).hexdigest()[:12]

def layout_hash(data: dict[str, Any]) -> str:
    comps = [
        {key: c.get(key) for key in (
            "id", "defId", "componentDefId", "footprintOverride", "boardPos",
            "flexibleEndPos", "rotation", "boardExcluded", "locked"
        )}
        for c in data["components"]
    ]
    board = data["board"]
    payload = {
        "comps": comps, "assignments": data["netAssignments"],
        "rows": board["rows"], "cols": board["cols"],
        "wires": board["wires"], "cuts": board["cuts"],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(raw.encode()).hexdigest()[:12]

def campaign_index(data: dict[str, Any], project_id: int) -> dict[str, Any]:
    defs = {str(d["id"]): d for d in data.get("componentDefs", []) if d.get("id")}
    comp_ids = {str(c.get("id")) for c in data["components"]}
    assigned_ids = {str(a.get("componentId")) for a in data["netAssignments"]}
    placeable = [c for c in data["components"] if not c.get("boardExcluded")]
    unresolved = sum(
        1 for c in data["components"]
        if not (did := component_def_id(c))
        or (did not in defs and not is_default_id(did))
    )
    net_by_pin = {
        (str(a.get("componentId")), str(a.get("pinId"))): str(a.get("netId"))
        for a in data["netAssignments"]
    }
    shorted = 0
    for component in data["components"]:
        did = component_def_id(component)
        definition = defs.get(did or "")
        if not definition or definition.get("flexible"):
            continue
        seen: dict[tuple[int, int], str] = {}
        for pin in definition.get("pins", []):
            net = net_by_pin.get((str(component.get("id")), str(pin.get("id"))))
            if not net:
                continue
            cell = (int(pin.get("offsetRow", 0)), int(pin.get("offsetCol", 0)))
            if cell in seen and seen[cell] != net:
                shorted += 1
                break
            seen[cell] = net
    board = data["board"]
    return {
        "id": project_id,
        "parts": len(placeable),
        "nets": len(data["nets"]),
        "assignments": len(data["netAssignments"]),
        "rows": board["rows"],
        "cols": board["cols"],
        "actualRows": board["actualRows"],
        "actualCols": board["actualCols"],
        "wantedRows": board["wantedRows"],
        "wantedRowsMode": board["wantedRowsMode"],
        "wantedCols": board["wantedCols"],
        "wantedColsMode": board["wantedColsMode"],
        "wires": len(board["wires"]),
        "cuts": len(board["cuts"]),
        "conflicts": -1,
        "incomplete": -1,
        "unresolvedDefs": unresolved,
        "shortedDefs": shorted,
        "removedParts": len(comp_ids - assigned_ids),
        "netlistHash": netlist_hash(data),
        "layoutHash": layout_hash(data),
        "dupIds": [],
    }

def required_dimension(value: int | None, prompt: str, parser: argparse.ArgumentParser) -> int:
    """Require a positive dimension; prompt interactively when omitted."""
    if value is None:
        if not sys.stdin.isatty():
            parser.error(f"{prompt} is required (use the matching command-line option)")
        while True:
            try:
                raw = input(f"{prompt}: ").strip()
            except EOFError:
                parser.error(f"{prompt} is required")
            try:
                value = int(raw)
            except ValueError:
                print("Enter a whole number greater than zero.")
                continue
            if value > 0:
                break
            print("Enter a whole number greater than zero.")
    if value <= 0:
        parser.error(f"{prompt} must be greater than zero")
    return value


def required_mode(value: str | None, prompt: str, parser: argparse.ArgumentParser) -> str:
    """Require either fixed or max, prompting when omitted."""
    if value is None:
        if not sys.stdin.isatty():
            parser.error(f"{prompt} is required (choose fixed or max)")
        while True:
            try:
                raw = input(f"{prompt} [fixed/max]: ").strip().lower()
            except EOFError:
                parser.error(f"{prompt} is required")
            if raw in ("fixed", "max"):
                value = raw
                break
            print("Enter 'fixed' or 'max'.")
    if value not in ("fixed", "max"):
        parser.error(f"{prompt} must be 'fixed' or 'max'")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, required=True, help="Karl/Stripboard Editor project JSON")
    parser.add_argument("--net", type=Path, help="matching KiCad .net export (node-count cross-check)")
    parser.add_argument("--mod", type=Path, help=".pretty directory, ZIP archive, or one .kicad_mod file")
    parser.add_argument("--actual-rows", type=int, help="physical board rows (prompted if omitted)")
    parser.add_argument("--actual-cols", type=int, help="physical board columns (prompted if omitted)")
    parser.add_argument("--wanted-rows-mode", choices=("fixed", "max"), help="wanted rows mode")
    parser.add_argument("--wanted-rows", type=int, help="wanted rows value")
    parser.add_argument("--wanted-cols-mode", choices=("fixed", "max"), help="wanted columns mode")
    parser.add_argument("--wanted-cols", type=int, help="wanted columns value")
    parser.add_argument("--id", type=int, default=0, help="project id used by the campaign runner")
    parser.add_argument("--out", type=Path, default=Path("campaign-input"), help="campaign data directory")
    args = parser.parse_args()

    for name, path in (("JSON", args.json), ("NET", args.net), ("MOD", args.mod)):
        if path is not None and not path.exists():
            parser.error(f"{name} input does not exist: {path}")

    actual_rows = required_dimension(args.actual_rows, "Actual physical board rows", parser)
    actual_cols = required_dimension(args.actual_cols, "Actual physical board columns", parser)
    wanted_rows_mode = required_mode(args.wanted_rows_mode, "Wanted rows mode", parser)
    wanted_rows = required_dimension(args.wanted_rows, "Wanted rows value", parser)
    wanted_cols_mode = required_mode(args.wanted_cols_mode, "Wanted columns mode", parser)
    wanted_cols = required_dimension(args.wanted_cols, "Wanted columns value", parser)

    if wanted_rows_mode == "fixed" and wanted_rows > actual_rows:
        parser.error("fixed wanted rows value cannot exceed actual physical board rows")
    if wanted_cols_mode == "fixed" and wanted_cols > actual_cols:
        parser.error("fixed wanted columns value cannot exceed actual physical board columns")

    try:
        data = validate_project(json.loads(args.json.read_text(encoding="utf-8")))
        data = normalise_like_gui(data)
        # Never silently inherit the source JSON's board dimensions.
        data["board"].update({
            "rows": actual_rows, "cols": actual_cols,
            "actualRows": actual_rows, "actualCols": actual_cols,
            "wantedRowsMode": wanted_rows_mode, "wantedRows": wanted_rows,
            "wantedColsMode": wanted_cols_mode, "wantedCols": wanted_cols,
        })
        warnings = list(data.pop("_collectWarnings", []))

        footprint_count = 0
        if args.mod:
            footprints, fp_warnings = read_footprints(args.mod)
            warnings.extend(fp_warnings)
            before = len(data.get("componentDefs", []))
            merge_footprints(data, footprints)
            footprint_count = len(data.get("componentDefs", [])) - before
            warnings.extend(data.pop("_collectWarnings", []))

        missing = []
        known = {str(d.get("id")) for d in data.get("componentDefs", []) if d.get("id")} | DEFAULT_IDS
        for component in data["components"]:
            did = component_def_id(component)
            if did and did not in known and not is_default_id(did):
                missing.append({"component": component.get("label") or component.get("id"), "defId": did})

        net_nodes = None
        if args.net:
            net_nodes = count_netlist_nodes(args.net)
            if net_nodes != len(data["netAssignments"]):
                raise ValueError(
                    f"CRITICAL MISMATCH: JSON has {len(data['netAssignments'])} pin assignments, "
                    f".net has {net_nodes} (node (ref ...) records)"
                )

        entry = campaign_index(data, args.id)
        estimate = estimate_board(data["components"], data.get("componentDefs", []))
        # Fixed axes are exact; max axes are upper bounds. Estimate whether
        # the routing-area target can fit within the selected envelope.
        target_holes = estimate["target_holes"]
        allowed_holes = wanted_rows * wanted_cols
        route_warnings = []
        if wanted_rows_mode == "fixed" and wanted_cols_mode == "fixed":
            estimate_fits = target_holes <= allowed_holes
            fit_detail = f"fixed {wanted_rows} x {wanted_cols}"
        elif wanted_rows_mode == "fixed":
            required_cols = math.ceil(target_holes / wanted_rows)
            estimate_fits = required_cols <= wanted_cols
            fit_detail = f"{required_cols} columns required at fixed {wanted_rows} rows"
        elif wanted_cols_mode == "fixed":
            required_rows = math.ceil(target_holes / wanted_cols)
            estimate_fits = required_rows <= wanted_rows
            fit_detail = f"{required_rows} rows required at fixed {wanted_cols} columns"
        else:
            estimate_fits = target_holes <= allowed_holes
            fit_detail = f"maximum envelope {wanted_rows} x {wanted_cols}"
        if not estimate_fits:
            route_warnings.append(
                f"ESTIMATED ROUTE FAILURE: {fit_detail}; wanted limit is "
                f"{wanted_rows_mode} {wanted_rows} rows / "
                f"{wanted_cols_mode} {wanted_cols} columns "
                f"({allowed_holes} holes available, {target_holes} estimated)"
            )
        estimate["wanted_limits"] = {
            "rows_mode": wanted_rows_mode, "rows": wanted_rows,
            "cols_mode": wanted_cols_mode, "cols": wanted_cols,
            "capacity_holes": allowed_holes, "estimated_fit": estimate_fits,
            "route_warnings": route_warnings,
        }
        entry["boardEstimate"] = estimate
        if missing:
            warnings.append(f"{len(missing)} component definitions remain unresolved")
        if entry["shortedDefs"]:
            warnings.append(f"{entry['shortedDefs']} custom footprint(s) place different-net pins on the same hole")
        warnings.append("Footprints without saved project geometry are left to the solver verifier; saved built-in and custom geometry is checked by the collector.")
        if net_nodes is not None:
            entry["netlistNodes"] = net_nodes

        out = args.out.resolve()
        projects = out / "projects"
        projects.mkdir(parents=True, exist_ok=True)
        target = projects / f"{args.id}.json"
        tmp = target.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(target)
        (out / "index.json").write_text(json.dumps([entry], indent=2) + "\n", encoding="utf-8")

        # Persist immutable, footprint-local geometric *assumptions* beside
        # collected project. These are not measured dimensions, and never
        # silently become 2.5D routing permissions.
        physical_sidecar = build_assumed_geometry(data)
        geometry_path = out / "physical_geometry.json"
        geometry_tmp = out / "physical_geometry.json.tmp"
        geometry_tmp.write_text(
            json.dumps(physical_sidecar, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        geometry_tmp.replace(geometry_path)

        sources = out / "sources"
        sources.mkdir(exist_ok=True)
        for source in (args.json, args.net, args.mod):
            if source is not None and source.is_file():
                shutil.copy2(source, sources / source.name)

        warnings.extend(route_warnings)

        manifest = {
            "project_id": args.id,
            "source_json": str(args.json.resolve()),
            "source_json_sha256": sha256(args.json),
            "netlist": str(args.net.resolve()) if args.net else None,
            "netlist_sha256": sha256(args.net) if args.net else None,
            "footprint_source": str(args.mod.resolve()) if args.mod else None,
            "footprint_files_parsed": footprint_count,
            "campaign_project": str(target),
            "campaign_index": str(out / "index.json"),
            "netlist_nodes": net_nodes,
            "json_pin_assignments": len(data["netAssignments"]),
            "board_estimate": estimate,
            "physical_geometry_sidecar": str(geometry_path),
            "physical_geometry_sidecar_sha256": sha256(geometry_path),
            "geometry_preset_version": physical_sidecar["preset"],
            "geometry_unverified_components": physical_sidecar["unverified_count"],
            "actual_board": {"rows": actual_rows, "cols": actual_cols},
            "wanted_board": {
                "rows": {"mode": wanted_rows_mode, "value": wanted_rows},
                "cols": {"mode": wanted_cols_mode, "value": wanted_cols},
            },
            "component_count": len(data["components"]),
            "custom_definition_count": len(data.get("componentDefs", [])),
            "warnings": warnings,
            "connectivity_policy": "preserve exported JSON nets/netAssignments; .net is a node-count cross-check",
        }
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        print(f"COLLECTED project {args.id}")
        print(f"  actual physical board: {actual_rows} rows x {actual_cols} columns")
        print(f"  wanted rows: {wanted_rows_mode} {wanted_rows}")
        print(f"  wanted columns: {wanted_cols_mode} {wanted_cols}")
        print(f"  components: {len(data['components'])}")
        print(f"  nets / pin assignments: {len(data['nets'])} / {len(data['netAssignments'])}")
        print(f"  custom definitions: {len(data.get('componentDefs', []))}")
        print(f"  physical assumptions: {geometry_path} ({physical_sidecar['preset']}; NOT measured)")
        print(f"  footprints added: {footprint_count}")
        if net_nodes is not None:
            print(f"  .net node records: {net_nodes} (matched)")
        print(f"  unresolved definitions: {entry['unresolvedDefs']}")
        print(f"  shorted footprints: {entry['shortedDefs']}")
        print("  board estimate (tight): {} x {} = {} holes".format(estimate["rows"], estimate["cols"], estimate["board_holes"]))
        print("  board estimate (roomy): {} x {} = {} holes".format(estimate["roomy"]["rows"], estimate["roomy"]["cols"], estimate["roomy"]["holes"]))
        if estimate["unknown_size_parts"]:
            print("  WARNING: fallback 2x2 estimate for: " + ", ".join(estimate["unknown_size_parts"]))
        print(f"  campaign input: {target}")
        for warning in route_warnings:
            print(f"  WARNING: {warning}")
        for warning in warnings:
            print(f"  WARNING: {warning}")
        return 0
    except (OSError, json.JSONDecodeError, ValueError, zipfile.BadZipFile) as exc:
        print(f"collect: ERROR: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
