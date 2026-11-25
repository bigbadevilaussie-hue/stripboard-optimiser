"""Versioned construction-quality scoring; strict audit is unchanged."""
from collections import Counter
import math
import os

QUALITY_VERSION = "Q3"
PENALTY_SCALE = {"Q2": 1.0, "Q3": 0.4}
# Targets for the future verified Pass Two / Grand Final stop policy.
TARGET_QUALITY_MIN = 85
TARGET_QUALITY_DEFAULT = 90
TARGET_QUALITY_MAX = 95

def cpu_allocation():
    """Reserve one logical CPU where possible."""
    available = getattr(os, "process_cpu_count", os.cpu_count)() or 1
    return available, max(1, available - 1)

def max_stack_depth(wires):
    """Maximum positive-length overlap on vertical hole-to-hole segments."""
    coverage = Counter()
    for wire in wires:
        a, b = wire["from"], wire["to"]
        if a["col"] == b["col"]:
            for row in range(min(a["row"], b["row"]), max(a["row"], b["row"])):
                coverage[a["col"], row] += 1
    return max(coverage.values(), default=1 if wires else 0)

def construction_metrics(saved, *, quality_version=QUALITY_VERSION):
    """Score saved geometry; Q2 remains available for historical comparisons."""
    if quality_version not in PENALTY_SCALE:
        raise ValueError(f"Unsupported construction quality version: {quality_version}")
    board = saved["board"]
    wires, cuts = board["wires"], board["cuts"]
    length = sum(math.hypot(w["from"]["row"] - w["to"]["row"],
                            w["from"]["col"] - w["to"]["col"])
                 for w in wires) * 2.54
    unplaced = sum(not isinstance(c.get("boardPos"), dict)
                   for c in saved.get("components", [])
                   if not (c.get("offBoard") or c.get("boardExcluded")))
    nonvertical = sum(w["from"]["col"] != w["to"]["col"] for w in wires)
    s = max_stack_depth(wires)
    penalty = (.6 * len(wires) + .4 * len(cuts) + .02 * length
               + 10 * nonvertical + 15 * unplaced + max(0, s - 1) ** 2)
    q = round(max(0., 100 - PENALTY_SCALE[quality_version] * penalty), 2)
    return {"w": len(wires), "cut": len(cuts), "s": s,
            "wire_length_mm": round(length, 6), "q": q}
