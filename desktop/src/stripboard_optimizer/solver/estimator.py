"""Empirical wall-time estimate for one v5 solver seed.

Calibration is based on the measured 123-pin, effort-1 desktop run: about
473 seconds for 12 seeds in three batches on four workers. Each seed is an
independent Node/WASM process, so threads reduce batch count, not seed time.
"""
from dataclasses import dataclass, field
from .probe import ProbeResult


@dataclass(frozen=True)
class RuntimeEstimate:
    seconds_point: float
    seconds_low: float
    seconds_high: float
    basis: str
    notes: list[str] = field(default_factory=list)


# One observed run: 1.28M capped moves took approximately 155 seconds/seed.
_SECONDS_PER_MOVE = 155.0 / 1_280_000
_LOW_FACTOR = 0.65
_HIGH_FACTOR = 1.50


def estimate(probe: ProbeResult,
             moves_total: int,
             threads: int,
             has_locks: bool = False) -> RuntimeEstimate:
    notes = [
        "Empirical calibration: one 123-pin, effort-1 run; actual hardware and routing complexity vary.",
        "Threads affect the number of seed batches, not the duration of an individual seed.",
    ]
    if moves_total <= 0:
        notes.append("moves_total is zero or negative; nothing to estimate")
        return RuntimeEstimate(0.0, 0.0, 0.0, "empirical", notes)
    if threads < 1:
        notes.append("threads clamped to 1")
    point = _SECONDS_PER_MOVE * moves_total
    if has_locks:
        notes.append("Locked parts or dimensions can change solve time.")
    return RuntimeEstimate(
        seconds_point=point,
        seconds_low=point * _LOW_FACTOR,
        seconds_high=point * _HIGH_FACTOR,
        basis="empirical",
        notes=notes,
    )
