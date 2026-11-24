"""Adapt standalone schematic text for QtSvg only.

The standalone schematic SVG paints a thick white label halo behind dark text
using SVG paint-order="stroke". QtSvg does not consistently honor paint-order,
so the halo can cover the glyphs and make labels appear nearly invisible.

This deliberately edits ONLY white-stroked <text> opening tags in the in-memory
Qt view; the original generated SVG and the board/copper views are unchanged.
"""
from __future__ import annotations

import re

_TEXT_TAG = re.compile(r"<text\b[^>]*>", re.IGNORECASE)
_WHITE_STROKE = re.compile(
    r"""\s+stroke\s*=\s*(['"])(?:#fff|#ffffff|white)\1""",
    re.IGNORECASE,
)
_STROKE_DISPLAY = re.compile(
    r"""\s+(?:stroke-width|stroke-linejoin|paint-order)\s*=\s*(['"])[^'"]*\1""",
    re.IGNORECASE,
)


def schematic_svg_for_qt(svg: str) -> str:
    """Suppress only white text halos that Qt can paint over black lettering."""
    def adjust(match: re.Match[str]) -> str:
        tag = match.group(0)
        if not _WHITE_STROKE.search(tag):
            return tag
        tag = _WHITE_STROKE.sub(' stroke="none"', tag)
        return _STROKE_DISPLAY.sub("", tag)

    return _TEXT_TAG.sub(adjust, svg)
