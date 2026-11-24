"""Read-only bridge to the repository's existing standalone schematic SVG CLI.

This invokes only the compiled SVG renderer (never Karl's optimisation CLI).
Inputs and output SVG live in an automatically removed temporary directory.
No changes are made to project JSON, sidecars, components or net assignments.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from render.standalone_bridge import _run, ensure_renderer


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
            "node", str(schematic_cli), str(input_path), "--output", str(folder),
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
