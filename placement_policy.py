"""Shared board-mounting policy for imported project components.

Explicit source flags always win. A small identity exception covers the
known Moto-Mate NEO-6M module, which is mounted remotely and whose source
export omits the offBoard flag. Keep this rule in code: imported JSON remains
untouched.
"""
from __future__ import annotations

# Stable Karl component-definition ID for the off-board-mounted NEO-6M GPS
# in the Moto-Mate fixture. USB already carries offBoard=True in its export.
OFF_BOARD_DEFINITION_IDS = frozenset({
    "custom-fd3b91be-3685-42db-acae-7e2ab9735565",
})


def is_off_board_component(component: dict) -> bool:
    """Return whether a component is mounted off the stripboard."""
    if not isinstance(component, dict):
        return False
    if component.get("offBoard") is True or component.get("boardExcluded") is True:
        return True
    definition_id = component.get("defId") or component.get("componentDefId")
    return str(definition_id or "") in OFF_BOARD_DEFINITION_IDS


__all__ = ["OFF_BOARD_DEFINITION_IDS", "is_off_board_component"]
