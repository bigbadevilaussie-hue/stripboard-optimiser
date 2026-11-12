"""Single source of truth for on-board / off-board filtering and hole sizing."""

# Built-in editor defs are NOT stored in the JSON's componentDefs, so size them by defId.
# (cols, rows) in holes, laid flat on stripboard.
BUILTIN_SIZES = {
    "def-resistor": (1, 4), "def-diode": (1, 4), "def-zener": (1, 4),
    "def-led": (1, 2), "def-capacitor": (1, 2), "def-cap-polarized": (1, 2),
    "def-fuse": (1, 3), "def-inductor": (1, 3),
    "def-npn": (1, 3), "def-pnp": (1, 3), "def-pmos": (1, 3), "def-nmos": (1, 3),
    "def-connector-2": (1, 2), "def-switch": (1, 2), "def-pushbutton": (2, 2),
}

def def_id_of(c):
    return c.get("componentDefId") or c.get("defId")

def is_off_board(c):
    return c.get("offBoard") is True or c.get("boardExcluded") is True

def split_parts(components):
    """Returns (on_board, off_board). The ONLY place this decision is made."""
    on, off = [], []
    for c in components:
        (off if is_off_board(c) else on).append(c)
    return on, off

def part_size(c, component_defs):
    """(width, height, source) - custom def first, then built-in table, then 2x2 fallback."""
    did = def_id_of(c)
    d = component_defs.get(did)
    if d and "width" in d and "height" in d:
        return d["width"], d["height"], "def"
    if did in BUILTIN_SIZES:
        w, h = BUILTIN_SIZES[did]
        return w, h, "builtin"
    return 2, 2, "FALLBACK"
