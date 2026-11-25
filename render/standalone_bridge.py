"""Bridge to the parity-tested standalone stripboard production renderer.

The production renderer is the single source of board artwork for the GUI.
It is fetched as a sparse checkout of the upstream project on first use.
Route-Mate's mounting policy is applied before production rendering.
"""
from __future__ import annotations

import json
import shutil
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import Any


UPSTREAM = "https://github.com/bigbadevilaussie-hue/stripboard-optimiser.git"
# Pinned source and compiled dist audited with both nominal capacitor classes.
# A stale user cache must not silently change the on-board package artwork.
UPSTREAM_COMMIT = "7477431ff3939c4a51026852e4390d44299151c1"
CACHE = Path.home() / ".cache" / "route-mate" / "stripboard-optimiser"
SPARSE_PATH = "src/frontend/standalone-renderer/dist"
CLI = CACHE / SPARSE_PATH / "standalone-renderer" / "cli.js"
HOLE_PITCH = 30.0
HOLE_ORIGIN = 60.0


def add_alternating_row_bands(
    svg: str, rows: int, *, pitch: float = HOLE_PITCH, origin: float = HOLE_ORIGIN
) -> str:
    """Add alternating row bands behind the production SVG artwork."""
    import re

    if type(rows) is not int or rows < 1:
        raise ValueError("rows must be a positive integer")
    match = re.search(r'<svg\b[^>]*\bviewBox="([^"]+)"', svg)
    if not match:
        raise ValueError("Renderer SVG has no viewBox")
    values = [float(value) for value in match.group(1).replace(",", " ").split()]
    if len(values) != 4:
        raise ValueError("Renderer SVG has an invalid viewBox")
    x, _y, width, _height = values
    bands = []
    for row in range(rows):
        if row % 2 == 0:
            continue
        band_y = origin + row * pitch - pitch / 2
        bands.append(
            f'<rect x="{x:g}" y="{band_y:g}" width="{width:g}" height="{pitch:g}" '
            'fill="#f1f3f5" opacity="0.72" data-route-mate-row-band="1"/>'
        )
    insertion = "".join(bands)
    return re.sub(r'(<svg\b[^>]*>)', lambda m: m.group(1) + insertion, svg, count=1)


def add_board_coordinate_labels(
    svg: str, rows: int, cols: int, *,
    pitch: float = HOLE_PITCH, origin: float = HOLE_ORIGIN,
    mirrored: bool = False,
) -> str:
    """Add unobtrusive 1-based row and column labels aligned to board holes."""
    import re

    if type(rows) is not int or rows < 1:
        raise ValueError("rows must be a positive integer")
    if type(cols) is not int or cols < 1:
        raise ValueError("cols must be a positive integer")
    if pitch <= 0:
        raise ValueError("pitch must be positive")
    if not re.search(r'<svg\b[^>]*\bviewBox="[^"]+"', svg):
        raise ValueError("Renderer SVG has no viewBox")

    # The production renderer's R0·C0 caption is superseded by these rulers.
    svg = re.sub(
        r'<text\b[^>]*>[^<]*R0·C0[^<]*</text>', "", svg, count=1
    )
    labels = []
    label_y = origin - 22
    for col in range(cols):
        visual_col = cols - 1 - col if mirrored else col
        number = col + 1
        x = origin + visual_col * pitch
        labels.append(
            f'<text x="{x:g}" y="{label_y:g}" text-anchor="middle" '
            'font-family="sans-serif" font-size="10" font-weight="400" '
            'fill="#555" data-route-mate-column="' + str(number) + '">'
            + str(number) + '</text>'
        )
    label_x = origin - 22
    for row in range(rows):
        y = origin + row * pitch + 3
        number = row + 1
        labels.append(
            f'<text x="{label_x:g}" y="{y:g}" text-anchor="end" '
            'font-family="sans-serif" font-size="10" font-weight="400" '
            'fill="#555" data-route-mate-row="' + str(number) + '">'
            + str(number) + '</text>'
        )
    return re.sub(r'</svg\s*>', "".join(labels) + '</svg>', svg, count=1)



def add_offboard_terminals(svg: str, project: dict[str, Any]) -> str:
    """Draw selectable-style ring terminals at the allocated off-board holes."""
    import re
    from html import escape
    from placement_policy import is_off_board_component

    marks = []
    for component in project.get("components", []):
        if not isinstance(component, dict) or not is_off_board_component(component):
            continue
        if component.get("boardExcluded") is True and component.get("offBoard") is not True:
            continue
        label = str(component.get("label") or component.get("id"))
        for pin, point in (component.get("leads") or {}).items():
            row, col = int(point["row"]), int(point["col"])
            x = HOLE_ORIGIN + col * HOLE_PITCH
            y = HOLE_ORIGIN + row * HOLE_PITCH
            name = escape(f"{label} {pin}")
            marks.append(
                f'<g data-route-mate-terminal="{escape(str(component.get("id")))}" '
                f'data-pin="{escape(str(pin))}" data-row="{row}" data-col="{col}">'
                f'<circle cx="{x:g}" cy="{y:g}" r="11" fill="#ffffff" '
                f'fill-opacity="0.9" stroke="#dc5555" stroke-width="4"/>'
                f'<circle cx="{x:g}" cy="{y:g}" r="4.5" fill="#b32828"/>'
                f'<text x="{x:g}" y="{y-15:g}" text-anchor="middle" '
                f'font-family="sans-serif" font-size="11" font-weight="600" '
                f'fill="#222">{name}</text></g>'
            )
    return re.sub(r'</svg\s*>', lambda m: ''.join(marks) + m.group(0), svg, count=1)


def add_top_side_cuts(svg: str, project: dict[str, Any]) -> str:
    """Mark routed copper cuts on the component-side preview at their exact locations.

    These are reference markers: cuts are physically made on the copper side.
    Coordinates are zero-based in project JSON and use the production hole grid.
    """
    import re
    from html import escape

    board = project.get("board", {})
    rows, cols = int(board.get("rows", 0)), int(board.get("cols", 0))
    cuts = board.get("cuts", [])
    if not isinstance(cuts, list) or not cuts:
        return svg
    marks = []
    for index, cut in enumerate(cuts, 1):
        if not isinstance(cut, dict):
            continue
        row, col = cut.get("row"), cut.get("col")
        if type(row) is not int or type(col) is not int:
            continue
        kind = cut.get("kind", "between")
        if not (0 <= row < rows and 0 <= col < cols):
            continue
        if kind == "between":
            if col >= cols - 1:
                continue
            x = HOLE_ORIGIN + (col + 0.5) * HOLE_PITCH
        elif kind == "hole":
            x = HOLE_ORIGIN + col * HOLE_PITCH
        else:
            continue
        y = HOLE_ORIGIN + row * HOLE_PITCH
        # Match the copper-side cut symbol: a plain red X, no surrounding circle.
        marks.append(
            f'<g data-route-mate-cut="{index}" data-cut-row="{row}" '
            f'data-cut-col="{col}" data-cut-kind="{escape(str(kind))}">'
            f'<path d="M {x-7:g} {y-7:g} L {x+7:g} {y+7:g} '
            f'M {x+7:g} {y-7:g} L {x-7:g} {y+7:g}" '
            f'stroke="#ff2424" stroke-width="4" stroke-linecap="round"/>'
            '</g>'
        )
    return re.sub(r'</svg\s*>', lambda m: ''.join(marks) + m.group(0), svg, count=1)


def add_assumed_contact_highlights(
    svg: str, project: dict[str, Any], *, mirrored: bool = False,
) -> str:
    """Red outlines for nominal body/body and body/pad contact risk.

    These marks are NOT proof of physical collision. Body outlines and grid
    pads derive from the same versioned collector as the 2.5D sidecar; the
    production renderer is still responsible for the actual part artwork.
    """
    import re
    from html import escape
    from geometry_sidecar import (
        assumed_body_pad_keepouts, inspect_assumed_contacts,
    )
    from capacitor_contract import resolved_capacitor_package

    issues = inspect_assumed_contacts(project)
    components = {
        str(c.get("id")): c for c in project.get("components", [])
        if isinstance(c, dict) and c.get("id")
    }
    # Machine-readable package provenance on each top view, even if nothing
    # touches: useful for SVG tests and debugging stale renderer packages.
    metadata = []
    if not mirrored:
        for cid, part in components.items():
            package = resolved_capacitor_package(part)
            if package is not None:
                metadata.append(
                    '<g data-route-mate-cap-package="' + escape(package, quote=True)
                    + '" data-route-mate-cap-id="' + escape(cid, quote=True)
                    + '" data-route-mate-cap-value="'
                    + escape(str(part.get("value") or ""), quote=True)
                    + '"></g>'
                )
    if not issues:
        return re.sub(r"</svg\s*>", lambda m: "".join(metadata) + m.group(0),
                      svg, count=1)

    from collector_geometry import PITCH_MM
    scale = HOLE_PITCH / PITCH_MM
    cols = int(project["board"]["cols"])
    def px_x(x_mm: float) -> float:
        original = HOLE_ORIGIN + x_mm * scale
        if mirrored:
            return 2 * HOLE_ORIGIN + (cols - 1) * HOLE_PITCH - original
        return original
    def px_y(y_mm: float) -> float:
        return HOLE_ORIGIN + y_mm * scale

    affected = {}
    pads = {}
    for issue in issues:
        reason = (f"{issue['kind']}: "
                  + " / ".join(issue["components"])
                  + f", nominal gap {issue['gap_mm']} mm; NOT measured")
        for cid in issue["component_ids"]:
            affected.setdefault(cid, set()).add(reason)
        if "pad" in issue:
            pad = issue["pad"]
            pads.setdefault((pad["row"], pad["col"]), set()).add(reason)

    shapes = {
        shape["id"]: shape for shape in assumed_body_pad_keepouts(project)
    }
    marks = []
    for cid, messages in sorted(affected.items()):
        shape = shapes.get(cid)
        if shape is None:
            continue
        title = escape("; ".join(sorted(messages)))
        attrs = (
            'fill="none" stroke="#e11d48" stroke-width="3" '
            'stroke-dasharray="7 3" pointer-events="none"'
        )
        if shape["shape"] == "circle":
            x, y = shape["center_mm"]
            outline = (
                f'<circle cx="{px_x(x):g}" cy="{px_y(y):g}" '
                f'r="{(shape["radius_mm"] * scale):g}" {attrs}/>'
            )
        else:
            lo = px_x(shape["x_min_mm"])
            hi = px_x(shape["x_max_mm"])
            outline = (
                f'<rect x="{min(lo, hi):g}" y="{px_y(shape["y_min_mm"]):g}" '
                f'width="{abs(hi-lo):g}" '
                f'height="{(shape["y_max_mm"]-shape["y_min_mm"])*scale:g}" '
                f'{attrs}/>'
            )
        marks.append(
            '<g data-route-mate-nominal-contact="body" '
            f'data-component-id="{escape(cid, quote=True)}">'
            f'<title>{title}</title>{outline}</g>'
        )
    for (row, col), messages in sorted(pads.items()):
        x = px_x(col * PITCH_MM)
        y = px_y(row * PITCH_MM)
        title = escape("; ".join(sorted(messages)))
        marks.append(
            '<g data-route-mate-nominal-contact="pad" '
            f'data-row="{row}" data-col="{col}"><title>{title}</title>'
            f'<circle cx="{x:g}" cy="{y:g}" r="12" fill="none" '
            'stroke="#e11d48" stroke-width="3" pointer-events="none"/>'
            '</g>'
        )
    return re.sub(r"</svg\s*>", lambda m: "".join(metadata + marks) + m.group(0),
                  svg, count=1)


def add_component_highlight(
    svg: str, project: dict[str, Any], component_id: str | None
) -> str:
    """Overlay a selection outline using the shared board-footprint geometry."""
    if component_id is None:
        return svg

    import re
    from board_geometry import BUILTIN_DEFS, component_geometry, resolve_definition

    component = next(
        (item for item in project.get("components", [])
         if isinstance(item, dict) and str(item.get("id")) == str(component_id)),
        None,
    )
    if component is None or not isinstance(component.get("boardPos"), dict):
        return svg

    definitions = dict(BUILTIN_DEFS)
    for definition in project.get("componentDefs", []):
        if isinstance(definition, dict) and definition.get("id"):
            definitions[str(definition["id"])] = definition
    definition = resolve_definition(component, definitions)

    if definition:
        pins, body_cells = component_geometry(component, definition)
        points = [(int(pin["row"]), int(pin["col"])) for pin in pins]
        points.extend((int(row), int(col)) for row, col in body_cells)
    else:
        pos = component["boardPos"]
        points = [(int(pos.get("row", 0)), int(pos.get("col", 0)))]

    if not points:
        return svg

    min_row = min(row for row, _ in points)
    max_row = max(row for row, _ in points)
    min_col = min(col for _, col in points)
    max_col = max(col for _, col in points)
    pad = 17.0
    x = HOLE_ORIGIN + min_col * HOLE_PITCH - pad
    y = HOLE_ORIGIN + min_row * HOLE_PITCH - pad
    width = (max_col - min_col) * HOLE_PITCH + pad * 2
    height = (max_row - min_row) * HOLE_PITCH + pad * 2
    overlay = (
        f'<rect x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}" '
        'rx="8" fill="#f59e0b" fill-opacity="0.12" stroke="#f97316" '
        'stroke-width="3.5" stroke-dasharray="7 4" '
        'data-route-mate-highlight="1"/>'
    )
    return re.sub(r'</svg\s*>', overlay + '</svg>', svg, count=1)


def _run(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args, cwd=str(cwd) if cwd else None, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )


def _bundled_runtime() -> tuple[Path, Path] | None:
    """Use the included standalone renderer and Node when PyInstaller-frozen."""
    if not getattr(sys, "frozen", False):
        return None
    root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    node = root / "renderer-runtime" / "node"
    dist = root / "renderer-runtime" / "dist"
    cli = dist / "standalone-renderer" / "cli.js"
    required = (
        cli,
        dist / "standalone-renderer" / "render.js",
        dist / "standalone-renderer" / "schematic" / "cli.js",
        dist / "data" / "defaultComponents.js",
        dist / "components" / "stripboard" / "boardLayout.js",
        dist / "utils" / "resolveComponentDef.js",
    )
    if not node.is_file() or any(not file.is_file() for file in required):
        raise RuntimeError("Standalone app is missing required bundled renderer files.")
    return node, cli


def ensure_renderer() -> Path:
    """Use our EXISTING local renderer; never clone Git or run a solver."""
    bundled = _bundled_runtime()
    if bundled is not None:
        return bundled[1]
    root = Path(__file__).resolve().parent.parent
    cli = root / "src" / "frontend" / "standalone-renderer" / "dist" / "standalone-renderer" / "cli.js"
    if not cli.is_file():
        raise RuntimeError(
            "Local standalone board renderer is missing. Run "
            "'cd src/frontend && npm run build:renderers'. "
            "Preflight still works without it."
        )
    if not shutil.which("node"):
        raise RuntimeError("Node.js is required for board preview (not for JSON preflight).")
    return cli


def _cap_label_clearance_adjustments(project: dict[str, Any]) -> list[dict]:
    """Move ONLY misleading capacitor labels that fall on a foreign body.

    SVG labels are not physical placement. A saved boardLabelOffset may have
    come from an older board; rendering it into a different capacitor's
    nominal package makes a small ceramic appear as a large electrolytic.
    Never alter part positions, pin holes, rotations, package choice or source.
    """
    from math import hypot
    from board_geometry import BUILTIN_DEFS, component_geometry, resolve_definition
    from capacitor_contract import resolved_capacitor_package
    from collector_geometry import PITCH_MM
    from geometry_sidecar import assumed_body_pad_keepouts

    solids = assumed_body_pad_keepouts(project)
    if not solids:
        return []
    defs = dict(BUILTIN_DEFS)
    defs.update({str(d["id"]): d for d in project.get("componentDefs", [])
                 if isinstance(d, dict) and d.get("id")})
    rows, cols = int(project["board"]["rows"]), int(project["board"]["cols"])
    adjustments = []

    def point_gap_mm(x: float, y: float, body: dict) -> float:
        if body["shape"] == "circle":
            bx, by = body["center_mm"]
            return hypot(x - bx, y - by) - body["radius_mm"]
        dx = max(body["x_min_mm"] - x, 0, x - body["x_max_mm"])
        dy = max(body["y_min_mm"] - y, 0, y - body["y_max_mm"])
        return hypot(dx, dy)

    for part in project.get("components", []):
        if resolved_capacitor_package(part) is None:
            continue
        if not isinstance(part.get("boardPos"), dict):
            continue
        definition = resolve_definition(part, defs)
        if definition is None:
            continue
        pins, _ = component_geometry(part, definition)
        if len(pins) != 2:
            continue
        # For radial ceramic, film, and electrolytic bodyAnchor() is zero in
        # upstream partDrawing: the default label is at pin midpoint.
        x = (float(pins[0]["col"]) + float(pins[1]["col"])) / 2 * PITCH_MM
        y = (float(pins[0]["row"]) + float(pins[1]["row"])) / 2 * PITCH_MM
        others = [s for s in solids if s["id"] != str(part["id"])]
        if not others:
            continue

        label = str(part.get("label") or part["id"])
        original = part.get("boardLabelOffset") or {}
        original = {"x": float(original.get("x", 0)),
                    "y": float(original.get("y", 0))}
        scale = PITCH_MM / HOLE_PITCH
        # Approximate label half-height plus clearance in millimetres.
        # This is a *text-layout* concern, not an engineering keepout.
        text_margin = 1.2

        def score(candidate: dict) -> float:
            cx = x + candidate["x"] * scale
            cy = y + candidate["y"] * scale
            if (cx < -0.5 * PITCH_MM
                    or cx > (cols - 0.5) * PITCH_MM
                    or cy < -0.5 * PITCH_MM
                    or cy > (rows - 0.5) * PITCH_MM):
                return float("-inf")
            return min(point_gap_mm(cx, cy, s) for s in others)

        if score(original) >= text_margin:
            continue
        options = [
            {"x": 0.0, "y": 0.0},
            {"x": 0.0, "y": 22.0}, {"x": 0.0, "y": -22.0},
            {"x": 22.0, "y": 0.0}, {"x": -22.0, "y": 0.0},
            {"x": 0.0, "y": 35.0}, {"x": 0.0, "y": -35.0},
            {"x": 35.0, "y": 0.0}, {"x": -35.0, "y": 0.0},
        ]
        selected = next((option for option in options
                         if score(option) >= text_margin), None)
        if selected is None:
            # Best available label position, without any false claim of
            # physical clearance. Never leave it knowingly inside a can
            # merely because the board's former manual offset said so.
            selected = max(options, key=score)
        if selected == original:
            continue
        obstruction = min(others, key=lambda s: point_gap_mm(
            x + original["x"] * scale,
            y + original["y"] * scale, s,
        ))
        part["boardLabelOffset"] = selected
        adjustments.append({
            "label": label, "blocked_by": obstruction["label"],
            "original": original, "rendered": selected,
        })
    return adjustments


def _renderer_input(project: dict[str, Any], *, web_preview: bool = False) -> dict[str, Any]:
    """Copy the project and remove components not mounted on the stripboard."""
    from placement_policy import is_off_board_component

    from capacitor_contract import resolved_capacitor_package
    render_project = dict(project)
    components = project.get("components", [])
    if isinstance(components, list):
        render_project["components"] = []
        for component in components:
            if is_off_board_component(component):
                if web_preview and component.get("boardExcluded") is not True:
                    # Karl's virtual pads supply net colours and terminal labels.
                    render_project["components"].append(dict(component, offBoard=True))
                continue
            part = dict(component)
            # The production renderer accepts explicit package IDs. Supply
            # the same resolved ID used by collector/sidecar to avoid any
            # implicit default or cached-version ambiguity. Never mutate
            # the project's original package selection.
            cap_package = resolved_capacitor_package(component)
            if cap_package is not None:
                part["package"] = cap_package
            render_project["components"].append(part)
    render_project["_routeMateLabelAdjustments"] = (
        _cap_label_clearance_adjustments(render_project)
    )
    return render_project


def render_project(
    project_path: Path, output_dir: Path, *,
    highlight_component_id: str | None = None, web_preview: bool = False,
) -> tuple[str, str, str]:
    """Render both production board sides and return top SVG, copper SVG and log."""
    cli = ensure_renderer()
    source_project = json.loads(project_path.read_text(encoding="utf-8"))
    project = _renderer_input(source_project, web_preview=True) if web_preview else _renderer_input(source_project)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Never rewrite the caller's project file: the production renderer receives
    # a temporary copy with Route-Mate's off-board mounting policy applied.
    with tempfile.TemporaryDirectory(prefix="route-mate-render-input-") as tmp:
        render_input = Path(tmp) / "project.json"
        render_input.write_text(
            json.dumps(project, ensure_ascii=False), encoding="utf-8"
        )
        runtime = _bundled_runtime()
        node = str(runtime[0]) if runtime else "node"
        args = [node, str(cli), str(render_input), "--output", str(output_dir)]
        if web_preview:
            args.append("--web-preview")
            if highlight_component_id is not None:
                args.extend(["--highlight", str(highlight_component_id)])
        result = _run(args)
    if result.returncode:
        raise RuntimeError("Production renderer failed:\n" + result.stdout)
    top = output_dir / "board-top.svg"
    copper = output_dir / "board-copper.svg"
    if not top.is_file() or not copper.is_file():
        raise RuntimeError("Production renderer did not produce both board SVGs.")

    rows = int(project["board"]["rows"])
    cols = int(project["board"]["cols"])
    top_svg = top.read_text(encoding="utf-8")
    if web_preview:
        if 'data-render-style="web"' not in top_svg:
            raise RuntimeError("Web preview missing; rebuild with npm run build:renderers.")
    else:
        top_svg = add_alternating_row_bands(top_svg, rows)
        top_svg = add_top_side_cuts(top_svg, project)
        top_svg = add_offboard_terminals(top_svg, source_project)
        top_svg = add_component_highlight(top_svg, project, highlight_component_id)
        top_svg = add_board_coordinate_labels(top_svg, rows, cols)
    # Nominal contact warnings belong in Activity and physical reports,
    # not the board artwork. Keep only the explicit lock-review highlight.
    copper_svg = add_board_coordinate_labels(
        copper.read_text(encoding="utf-8"), rows, cols, mirrored=True
    )
    corrections = project.get("_routeMateLabelAdjustments") or []
    label_log = "\n".join(
        f"[CAPACITOR][LABEL] {item['label']}: stale board-label offset "
        f"would overlap {item['blocked_by']}; moved annotation only "
        f"{item['original']} -> {item['rendered']}"
        for item in corrections
    )
    return top_svg, copper_svg, "\n".join(
        part for part in (result.stdout.strip(), label_log) if part
    )


def render_project_data(
    project: dict[str, Any], *, highlight_component_id: str | None = None,
    web_preview: bool = False,
) -> tuple[str, str, str]:
    """Render an in-memory project through the production renderer."""
    with tempfile.TemporaryDirectory(prefix="route-mate-render-") as tmp:
        root = Path(tmp)
        project_path = root / "project.json"
        project_path.write_text(
            json.dumps(project, ensure_ascii=False), encoding="utf-8"
        )
        return render_project(
            project_path, root / "output",
            highlight_component_id=highlight_component_id,
            **({"web_preview": True} if web_preview else {}),
        )
