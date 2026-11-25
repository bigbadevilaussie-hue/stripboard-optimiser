"""Read-only bridge to the repository's existing standalone schematic SVG CLI.

This invokes only the compiled SVG renderer (never Karl's optimisation CLI).
Inputs and output SVG live in an automatically removed temporary directory.
No changes are made to project JSON, sidecars, components or net assignments.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from render.standalone_bridge import _run, ensure_renderer
from gui.runtime_paths import node_command, tool_path


def render_schematic_data(project: dict[str, Any]) -> tuple[str, str]:
    """Return (schematic.svg contents, CLI diagnostic) from the existing renderer."""
    if not isinstance(project, dict):
        raise ValueError("Schematic project must be a JSON object.")

    # The board and schematic CLIs are siblings in the existing compiled
    # standalone-renderer/dist/standalone-renderer tree.
    board_cli = ensure_renderer()
    schematic_cli = board_cli.parent / "schematic" / "cli.js"
    if not schematic_cli.is_file():
        raise RuntimeError(
            "Local schematic renderer is missing. From src/frontend run "
            "'npm run build:renderers'. No solver was started."
        )

    with tempfile.TemporaryDirectory(prefix="route-mate-schematic-") as scratch:
        folder = Path(scratch)
        input_path = folder / "project.json"
        output_path = folder / "schematic.svg"
        input_path.write_text(
            json.dumps(project, ensure_ascii=False), encoding="utf-8"
        )
        result = _run([
            node_command(), str(schematic_cli), str(input_path), "--output", str(folder),
        ])
        if result.returncode != 0:
            raise RuntimeError(
                "Standalone schematic renderer failed:\n" + result.stdout
            )
        if not output_path.is_file():
            raise RuntimeError(
                "Standalone schematic renderer did not create schematic.svg."
            )
        svg = output_path.read_text(encoding="utf-8")
        if "<svg" not in svg:
            raise ValueError("Standalone schematic renderer produced invalid SVG.")
        return svg, result.stdout.strip()


def rasterize_board_svg(svg: str) -> bytes:
    """Render the unmodified board SVG through the same librsvg path as schematic."""
    return _rasterize_svg(svg, "board")


def rasterize_schematic_svg(svg: str) -> bytes:
    """Use the exact SVG-to-PNG conversion used by the working Tk GUI.

    Old Tk implementation, desktop/src/stripboard_optimizer/ui/main_window.py:
    rsvg-convert -w 2400 -b white -o schematic.png schematic.svg

    QtSvg can render white label outlines over text despite SVG paint-order,
    causing apparently missing component labels. librsvg produces the same
    raster preview that the old Tk GUI used without changing the schematic SVG.
    """
    return _rasterize_svg(svg, "schematic")


def _rasterize_svg(svg: str, kind: str) -> bytes:
    if not isinstance(svg, str) or "<svg" not in svg:
        raise ValueError(f"Standalone {kind} must be a valid SVG string.")
    converter = tool_path("rsvg-convert")
    if converter is None:
        raise RuntimeError(
            f"{kind.capitalize()} preview requires rsvg-convert "
            "(install it with 'brew install librsvg' or MacPorts librsvg). "
            f"The standalone {kind} SVG itself is still available."
        )
    with tempfile.TemporaryDirectory(prefix=f"stripsolve-{kind}-png-") as scratch:
        folder = Path(scratch)
        svg_path = folder / f"{kind}.svg"
        png_path = folder / f"{kind}.png"
        svg_path.write_text(svg, encoding="utf-8")
        try:
            result = subprocess.run(
                [converter, "-w", "2400", "-b", "white",
                 "-o", str(png_path), str(svg_path)],
                capture_output=True, text=True, timeout=60, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError(f"{kind.capitalize()} rasterization failed: {exc}") from exc
        if result.returncode != 0:
            raise RuntimeError(
                f"{kind.capitalize()} rasterization failed: "
                + (result.stderr or result.stdout).strip()
            )
        if not png_path.is_file():
            raise RuntimeError(f"rsvg-convert did not produce {kind}.png.")
        data = png_path.read_bytes()
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("rsvg-convert returned an invalid PNG.")
        return data
