"""Runtime estimate from a ProbeResult. Pure math, no I/O."""
from dataclasses import dataclass, field
from .probe import ProbeResult


@dataclass(frozen=True)
class RuntimeEstimate:
    seconds_point: float
    seconds_low: float
    seconds_high: float
    basis: str  # "probe" | "fallback"
    notes: list[str] = field(default_factory=list)


# Parallel overhead on a 4-thread solve is real and not linear. Measured
# cold-start overhead (node spawn, WASM load) amortises across seeds, so we
# don't scale it. If you later measure actuals, replace this with a fitted curve.
_PARALLEL_OVERHEAD = 1.15


def estimate(probe: ProbeResult,
             moves_total: int,
             threads: int,
             has_locks: bool = False) -> RuntimeEstimate:
    notes: list[str] = []

    if not probe.ok or probe.ms_per_decode is None:
        notes.append("No valid probe result — cannot estimate without calibration")
        if probe.error:
            notes.append(f"probe error: {probe.error}")
        return RuntimeEstimate(0.0, 0.0, 0.0, "fallback", notes)

    if moves_total <= 0:
        notes.append("moves_total is zero or negative; nothing to estimate")
        return RuntimeEstimate(0.0, 0.0, 0.0, "probe", notes)

    if threads < 1:
        threads = 1
        notes.append("threads clamped to 1")

    # Decode ms × moves = single-threaded wall time. Divide by threads for
    # ideal parallel, then apply the overhead multiplier.
    single_thread_s = (probe.ms_per_decode * moves_total) / 1000.0
    parallel_s = (single_thread_s / threads) * _PARALLEL_OVERHEAD

    # Range: ±30% point estimate. Wide because contention and cache effects
    # on real hardware vary, and because a partly-locked board may spend
    # more of its time in the finish stage than the anneal.
    low = parallel_s * 0.7
    high = parallel_s * 1.6

    if has_locks:
        notes.append("board has locked parts or locked dimensions; estimate may be low")

    return RuntimeEstimate(
        seconds_point=parallel_s,
        seconds_low=low,
        seconds_high=high,
        basis="probe",
        notes=notes,
    )
