"""Public renderer API used by Route-Mate.

All application previews go through the parity-tested standalone production
renderer. The lightweight renderer is not used by the GUI.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .standalone_bridge import render_project_data


def render_front(
    project: dict[str, Any],
    *,
    show_labels: bool = True,
    show_pin_labels: bool = True,
    scale: float = 1.0,
    highlight_component_id: str | None = None,
) -> str:
    """Return the production component-side SVG for an in-memory project."""
    if not show_labels or not show_pin_labels or scale != 1.0:
        raise ValueError(
            "The production renderer currently requires labels and pin labels, at native scale."
        )
    top_svg, _copper_svg, _log = render_project_data(
        project, highlight_component_id=highlight_component_id
    )
    return top_svg


def render_front_svg(
    project: dict[str, Any],
    *,
    show_labels: bool = True,
    show_pin_labels: bool = True,
    scale: float = 1.0,
    highlight_component_id: str | None = None,
) -> str:
    """Explicitly named alias for render_front()."""
    return render_front(
        project,
        show_labels=show_labels,
        show_pin_labels=show_pin_labels,
        scale=scale,
        highlight_component_id=highlight_component_id,
    )


def write_front_svg(
    project: dict[str, Any],
    destination: str | Path,
    *,
    show_labels: bool = True,
    show_pin_labels: bool = True,
    scale: float = 1.0,
    highlight_component_id: str | None = None,
) -> Path:
    """Render and write one production component-side SVG file."""
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_front(
            project,
            show_labels=show_labels,
            show_pin_labels=show_pin_labels,
            scale=scale,
            highlight_component_id=highlight_component_id,
        ),
        encoding="utf-8",
    )
    return path
