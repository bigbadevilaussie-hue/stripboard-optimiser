"""Compatibility exports for the renderer's shared footprint geometry.

The implementation lives in the renderer-independent top-level board_geometry
module so solver and rendering code use exactly the same footprint semantics.
"""
from board_geometry import (
    BUILTIN_DEFS,
    component_geometry,
    resolve_definition,
    rotate_offset,
)

__all__ = ["BUILTIN_DEFS", "component_geometry", "resolve_definition", "rotate_offset"]
