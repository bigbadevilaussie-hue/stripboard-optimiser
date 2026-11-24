"""Legacy lightweight renderer retained only for isolated unit tests.

Application and GUI previews must use the production renderer exposed by
render.render. This module intentionally omits production package artwork and
must not be wired into the application workflow.
"""

from __future__ import annotations

import html
import math
from typing import Any

from board_geometry import BUILTIN_DEFS, component_geometry, resolve_definition
from placement_policy import is_off_board_component

PITCH = 30.0
PADDING = 42.0
BOARD_MARGIN = 17.0


def _number(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _xy(row: float, col: float) -> tuple[float, float]:
    return PADDING + col * PITCH, PADDING + row * PITCH


def _net_data(project: dict[str, Any], components: list[dict[str, Any]], definitions: dict[str, dict[str, Any]]):
    nets = {str(n.get("id")): n for n in project.get("nets", []) if isinstance(n, dict)}
    assignments: dict[tuple[str, str], str] = {}
    position_nets: dict[tuple[int, int], set[str]] = {}
    for item in project.get("netAssignments", []):
        if not isinstance(item, dict):
            continue
        cid, pid, nid = str(item.get("componentId")), str(item.get("pinId")), str(item.get("netId"))
        assignments[(cid, pid)] = nid
    for component in components:
        definition = resolve_definition(component, definitions)
        if not definition or is_off_board_component(component):
            continue
        pins, _ = component_geometry(component, definition)
        for pin in pins:
            net_id = assignments.get((str(component.get("id")), pin["id"]))
            if net_id:
                position_nets.setdefault((pin["row"], pin["col"]), set()).add(net_id)

    def colour_at(row: int, col: int) -> str:
        ids = position_nets.get((row, col), set())
        if len(ids) > 1:
            return "#dc2626"
        if ids:
            net = nets.get(next(iter(ids)), {})
            colour = net.get("color")
            if isinstance(colour, str) and colour.startswith("#") and len(colour) in (4, 7):
                return colour
        return "#263238"

    return assignments, position_nets, colour_at, nets


def _board_holes(board: dict[str, Any], rows: int, cols: int):
    pattern = board.get("pattern")
    pattern_map = pattern.get("map") if isinstance(pattern, dict) else None
    if not isinstance(pattern_map, list):
        for row in range(rows):
            for col in range(cols):
                yield row, col
        return
    for row in range(rows):
        line_index = row * 2
        line = pattern_map[line_index] if line_index < len(pattern_map) else ""
        for col in range(cols):
            if isinstance(line, str) and col * 2 < len(line) and line[col * 2] == "o":
                yield row, col


def render_front_board(
    project: dict[str, Any],
    *,
    show_labels: bool = True,
    show_pin_labels: bool = False,
    scale: float = 1.0,
    highlight_component_id: str | None = None,
) -> str:
    """Render a project dict to a component-side SVG string."""
    if not isinstance(project, dict):
        raise TypeError("project must be a dictionary")
    board = project.get("board")
    if not isinstance(board, dict):
        raise ValueError("project must contain a board object")
    try:
        rows, cols = int(board["rows"]), int(board["cols"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("board.rows and board.cols must be positive integers") from None
    if rows < 1 or cols < 1:
        raise ValueError("board.rows and board.cols must be positive integers")
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError("scale must be a positive finite number")

    raw_components = project.get("components", [])
    if not isinstance(raw_components, list):
        raise ValueError("project.components must be an array")
    components = [c for c in raw_components if isinstance(c, dict)]
    definitions = dict(BUILTIN_DEFS)
    for definition in project.get("componentDefs", []):
        if isinstance(definition, dict) and definition.get("id"):
            definitions[str(definition["id"])] = definition

    width = (cols - 1) * PITCH + PADDING * 2
    height = (rows - 1) * PITCH + PADDING * 2
    svg_width, svg_height = width * scale, height * scale
    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Stripboard component side" '
        f'viewBox="0 0 {_number(width)} {_number(height)}" '
        f'width="{_number(svg_width)}" height="{_number(svg_height)}">',
        '<rect width="100%" height="100%" fill="#f4f1e8"/>',
        f'<rect x="{_number(PADDING - BOARD_MARGIN)}" y="{_number(PADDING - BOARD_MARGIN)}" '
        f'width="{_number((cols - 1) * PITCH + BOARD_MARGIN * 2)}" '
        f'height="{_number((rows - 1) * PITCH + BOARD_MARGIN * 2)}" '
        'rx="5" fill="#d8c6a0" stroke="#8f8065" stroke-width="1.5"/>',
        "<g>",
    ]

    # The hole field is the first expensive operation; a single pass builds it.
    holes = [
        f'<circle cx="{_number(_xy(row, col)[0])}" cy="{_number(_xy(row, col)[1])}" '
        'r="4.2" fill="#f8f7f2" stroke="#655f53" stroke-width="1.25"/>'
        for row, col in _board_holes(board, rows, cols)
    ]
    parts.extend(holes)

    assignments, position_nets, colour_at, nets = _net_data(project, components, definitions)

    # Jumper wires are component-side objects. Cuts and copper artwork are
    # deliberately excluded; they belong to the later final copper-side view.
    for wire in board.get("wires", []) if isinstance(board.get("wires"), list) else []:
        if not isinstance(wire, dict):
            continue
        a, b = wire.get("from"), wire.get("to")
        if not isinstance(a, dict) or not isinstance(b, dict):
            continue
        try:
            ax, ay = _xy(float(a["row"]), float(a["col"]))
            bx, by = _xy(float(b["row"]), float(b["col"]))
        except (KeyError, TypeError, ValueError):
            continue
        na = position_nets.get((int(a["row"]), int(a["col"])), set())
        nb = position_nets.get((int(b["row"]), int(b["col"])), set())
        common = na & nb
        ink = "#263238"
        if len(na | nb) > 1:
            ink = "#dc2626"
        elif len(common) == 1:
            colour = nets.get(next(iter(common)), {}).get("color")
            if isinstance(colour, str) and colour.startswith("#") and len(colour) in (4, 7):
                ink = colour
        parts.append(
            f'<line x1="{_number(ax)}" y1="{_number(ay)}" x2="{_number(bx)}" y2="{_number(by)}" '
            f'stroke="#fff" stroke-width="8" stroke-linecap="round"/>'
            f'<line x1="{_number(ax)}" y1="{_number(ay)}" x2="{_number(bx)}" y2="{_number(by)}" '
            f'stroke="{ink}" stroke-width="4.2" stroke-linecap="round"/>'
        )

    # Parts are drawn as simple top-view package silhouettes. The geometry
    # matches the source footprint grid; detailed package art can be layered in
    # later without changing the public render_front() API.
    for component in components:
        if is_off_board_component(component) or not component.get("boardPos"):
            continue
        definition = resolve_definition(component, definitions)
        if not definition:
            pos = component["boardPos"]
            x, y = _xy(float(pos.get("row", 0)), float(pos.get("col", 0)))
            parts.append(
                f'<g><circle cx="{_number(x)}" cy="{_number(y)}" r="8" fill="#fff2cc" stroke="#b45309" stroke-width="2"/>'
                f'<text x="{_number(x)}" y="{_number(y + 4)}" text-anchor="middle" font-size="11" fill="#78350f">?</text></g>'
            )
            if str(component.get("id")) == str(highlight_component_id):
                parts.append(
                    f'<circle cx="{_number(x)}" cy="{_number(y)}" r="19" '
                    'fill="none" stroke="#f97316" stroke-width="4" stroke-dasharray="5 3"/>'
                )
            continue

        pins, body_cells = component_geometry(component, definition)
        if not pins:
            continue
        all_points = [(p["row"], p["col"]) for p in pins] + body_cells
        min_row = min(p[0] for p in all_points)
        max_row = max(p[0] for p in all_points)
        min_col = min(p[1] for p in all_points)
        max_col = max(p[1] for p in all_points)
        x0, y0 = _xy(min_row, min_col)
        x1, y1 = _xy(max_row, max_col)
        pad = 8.0

        if definition.get("flexible") and len(pins) >= 2:
            p1x, p1y = _xy(pins[0]["row"], pins[0]["col"])
            p2x, p2y = _xy(pins[1]["row"], pins[1]["col"])
            length = math.hypot(p2x - p1x, p2y - p1y)
            angle = math.degrees(math.atan2(p2y - p1y, p2x - p1x))
            body_len = max(16.0, min(length - 8.0, 44.0))
            parts.append(
                f'<rect x="{_number(-body_len / 2)}" y="-6" width="{_number(body_len)}" height="12" '
                f'rx="5" fill="#d6d3d1" fill-opacity=".9" stroke="#343a40" stroke-width="1.8" '
                f'transform="translate({_number((p1x + p2x) / 2)} {_number((p1y + p2y) / 2)}) rotate({_number(angle)})"/>'
            )
        else:
            bx0, by0 = x0 - pad, y0 - pad
            bw, bh = max(16.0, x1 - x0 + pad * 2), max(16.0, y1 - y0 + pad * 2)
            parts.append(
                f'<rect x="{_number(bx0)}" y="{_number(by0)}" width="{_number(bw)}" height="{_number(bh)}" '
                'rx="4" fill="#343a40" fill-opacity=".9" stroke="#111827" stroke-width="2"/>'
            )

        for pin in pins:
            x, y = _xy(pin["row"], pin["col"])
            colour = colour_at(pin["row"], pin["col"])
            parts.append(
                f'<circle cx="{_number(x)}" cy="{_number(y)}" r="6.1" fill="{colour}" '
                'stroke="#f8fafc" stroke-width="1.5"/>'
            )
            if show_pin_labels and pin.get("name"):
                parts.append(
                    f'<text x="{_number(x)}" y="{_number(y + 10)}" text-anchor="middle" '
                    f'font-size="8" fill="#111827" stroke="#fff" stroke-width="2.5" paint-order="stroke">'
                    f'{html.escape(str(pin["name"]))}</text>'
                )

        if str(component.get("id")) == str(highlight_component_id):
            hx0, hy0 = _xy(min_row, min_col)
            hx1, hy1 = _xy(max_row, max_col)
            parts.append(
                f'<rect x="{_number(hx0 - 17)}" y="{_number(hy0 - 17)}" '
                f'width="{_number(hx1 - hx0 + 34)}" height="{_number(hy1 - hy0 + 34)}" '
                'rx="9" fill="#f59e0b" fill-opacity=".12" stroke="#f97316" '
                'stroke-width="3.5" stroke-dasharray="7 4" '
                'data-route-mate-highlight="1"/>'
            )

        if show_labels:
            label = html.escape(str(component.get("label") or component.get("id") or ""))
            lx, ly = (x0 + x1) / 2, y0 - 13
            parts.append(
                f'<text x="{_number(lx)}" y="{_number(ly)}" text-anchor="middle" '
                'font-family="Helvetica" font-size="12" font-weight="700" '
                'fill="#111827" stroke="#fff" stroke-width="3.5" paint-order="stroke">'
                f'{label}</text>'
            )

    # Off-board parent parts are not board-mounted. Rendering their optional
    # saved lead-pad positions is a separate follow-up; never draw the parent
    # footprint on the board merely because it has schematic pins.
    parts.extend(['</g>', '</svg>'])
    return "".join(parts)
