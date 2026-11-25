"""Adaptive audited budget probe, separate from the speed measurement and campaign files."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from time import perf_counter
import math

from gui.native_calibration import Cancelled, prerequisites, decoder_directory
from gui.pass_one import (_run_seed, _prepared_input, _save_state,
                          inspect_pass_one_campaign, _decoder_identity)
from gui.work_directory import pass_one_budget_dir

TARGET = 100
FULL = 2000
SAMPLE_SEEDS = tuple(range(10, FULL + 1, 20))  # fixed, evenly distributed across the actual campaign
TARGET_RATE = TARGET / FULL


def summary(moves, rows, source, workers, wall_seconds=None):
    count = len(rows)
    passed = [r for r in rows if r["status"] == "PASS"]
    times = [float(r["time_taken"]) for r in rows]
    if not count or any(not math.isfinite(t) or t < 0 for t in times):
        raise ValueError("Invalid probe timing or empty sample")
    rate = len(passed) / count
    # Wilson 95% interval; describes sampling uncertainty, not future guarantees.
    z = 1.96
    center = (rate + z*z/(2*count)) / (1 + z*z/count)
    half = z * math.sqrt(rate*(1-rate)/count + z*z/(4*count*count)) / (1 + z*z/count)
    return {"moves": moves, "source": source, "tested": count, "qualified": len(passed),
            "rate": rate, "estimated_survivors": round(rate * FULL),
            "rate_interval": [max(0., center-half), min(1., center+half)],
            "best_q": max((float(r["q"]) for r in passed), default=None),
            "mean_seed_seconds": sum(times)/count,
            "estimated_full_seconds": FULL * sum(times)/count/max(1,workers),
            "wall_seconds": wall_seconds}


def choose(ten, twenty=None):
    if ten["rate"] >= TARGET_RATE:
        return 10000, "10k meets the target of about 100 verified survivors per 2,000 seeds."
    if twenty is None:
        raise ValueError("Low 10k survival requires a 20k comparison")
    if not ten["qualified"] and not twenty["qualified"]:
        return 20000, "Neither budget qualified a board. 20k is the deeper trial, not a proven recommendation; review the constraints."
    if twenty["rate"] >= ten["rate"]:
        return 20000, ("20k is the better or equal observed survival option, but remains below the target."
                       if twenty["rate"] < TARGET_RATE else
                       "10k falls below the survivor target; 20k meets it.")
    return 10000, "Both budgets are below target; 10k had the higher observed survival. Results are inconclusive."


def _history(project, workspace, moves, workers, drilled, stacking):
    if workspace is None:
        return None
    try:
        info = inspect_pass_one_campaign(project, moves, workers, drilled, stacking,
                                         pass_one_budget_dir(workspace, moves), seeds=FULL)
        if info["state"] == "COMPLETED" and info["done"] == FULL and not info["errors"]:
            return summary(moves, list(info["records"].values()), "FULL campaign", workers)
    except (OSError, ValueError, TypeError, KeyError, RuntimeError):
        pass
    return None


def _sample(project, moves, workers, drilled, stacking, progress, diagnostic, cancelled):
    rows = []
    started = perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_run_seed, project, moves, seed, drilled, stacking, cancelled)
                   for seed in SAMPLE_SEEDS]
        try:
            for future in as_completed(futures):
                if cancelled():
                    raise Cancelled()
                row = future.result()
                if row["valid"] not in (True, False):
                    raise RuntimeError("Probe seed has no definitive audited result")
                row = {**row, "status": "PASS" if row["valid"] else "FAIL",
                       "time_taken": row.get("time_taken", row.get("seconds"))}
                rows.append(row)
                progress({"phase": "budget_probe", "moves": moves, "completed": len(rows),
                          "total": len(SAMPLE_SEEDS),
                          "qualified": sum(r["status"] == "PASS" for r in rows)})
        except BaseException:
            for future in futures:
                future.cancel()
            raise
    stats = summary(moves, rows, "100-seed probe", workers, perf_counter()-started)
    diagnostic(f"[BUDGET][RESULT] {moves//1000}k: {stats['qualified']}/{stats['tested']} strict PASS")
    return stats, sorted(rows, key=lambda r: r["seed"])


def probe_budget(project, workers, drilled, stacking, progress, diagnostic, cancelled,
                 *, workspace=None):
    """No campaign folder or original JSON is modified. Only probe diagnostics saved."""
    prerequisites()
    prepared, fingerprint = _prepared_input(project)
    decoder = decoder_directory(prepared)
    if cancelled():
        raise Cancelled()
    diagnostic("[BUDGET] Actual JSON, locked dimensions and routing rules; strict native solve + independent audit.")
    ten = _history(prepared, workspace, 10000, workers, drilled, stacking)
    twenty = _history(prepared, workspace, 20000, workers, drilled, stacking)
    attempts = {}
    if ten is None:
        ten, attempts["10000"] = _sample(prepared, 10000, workers, drilled, stacking,
                                         progress, diagnostic, cancelled)
    if ten["rate"] < TARGET_RATE and twenty is None:
        twenty, attempts["20000"] = _sample(prepared, 20000, workers, drilled, stacking,
                                            progress, diagnostic, cancelled)
    budget, reason = choose(ten, twenty)
    result = {"schema": 1, "input_sha256": fingerprint, "decoder": decoder.name,
              **_decoder_identity(prepared), "drilled_only": drilled, "stacking_allowed": stacking,
              "target_survivors": TARGET, "recommended_moves": budget, "reason": reason,
              "ten": ten, "twenty": twenty, "attempts": attempts}
    if cancelled():
        raise Cancelled()
    if workspace is not None:
        path = Path(workspace) / "logs" / "budget_probe.json"
        if path.parent.is_symlink() or path.is_symlink():
            raise ValueError("Unsafe probe log path")
        path.parent.mkdir(parents=True, exist_ok=True)
        _save_state(path, result)
        diagnostic(f"[BUDGET][SAVED] {path}")
    diagnostic(f"[BUDGET][CHOICE] {budget//1000}k: {reason}")
    return result

def history_budget(project, workers, drilled, stacking, *, workspace=None):
    """Read matching past campaigns only. Never start a seed or write files."""
    try:
        prepared, _ = _prepared_input(project)
        ten = _history(prepared, workspace, 10000, workers, drilled, stacking)
        twenty = _history(prepared, workspace, 20000, workers, drilled, stacking)
    except (OSError, ValueError, RuntimeError, TypeError, KeyError):
        ten = twenty = None
    if ten and (twenty or ten["rate"] >= TARGET_RATE):
        budget, reason = choose(ten, twenty)
    elif ten or twenty:
        known = ten or twenty
        budget = known["moves"] if known["qualified"] else 10000
        reason = "Only one matching campaign is available; comparison is inconclusive."
    else:
        budget, reason = 10000, "No matching campaign history. Default 10k; choose either budget."
    return {"recommended_moves": budget, "reason": reason, "ten": ten, "twenty": twenty}
