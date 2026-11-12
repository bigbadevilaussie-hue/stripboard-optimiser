"""Guess a stripboard size from the parts list. No AI needed, just area + slack."""
import math
from stripboard_optimizer.filters import split_parts, part_size

# Calibrated on ONE real board (Moto-Mate: 32 parts, 244 raw holes, 24x56 worked).
# Refine ROUTING_FACTOR as you collect more finished boards.
ROUTING_FACTOR = 3.2     # board area / padded part area
ASPECT = 2.33            # cols / rows you tend to use (56/24)
GAP = 1                  # empty hole kept around each part

def estimate_board(components, component_defs, factor=ROUTING_FACTOR, aspect=ASPECT):
    on, _ = split_parts(components)
    dims = [part_size(c, component_defs)[:2] for c in on]
    raw = sum(w * h for w, h in dims)
    padded = sum((w + GAP) * (h + GAP) for w, h in dims)
    target = padded * factor

    longest = max((max(w, h) for w, h in dims), default=1)
    min_rows = longest + 2                        # tallest part must fit with a margin
    rows = max(min_rows, round(math.sqrt(target / aspect)))
    cols = math.ceil(target / rows)
    return {"raw_holes": raw, "padded_holes": padded, "target_holes": round(target),
            "rows": rows, "cols": cols, "board_holes": rows * cols,
            "tight": (rows, cols), "roomy": (rows + 4, math.ceil(cols * 1.25))}
