"""Pass One: real native V5 strict seeds; persistent CSV/log ONLY.

2000 seeds, 10k or 20k moves each, 3/4 CPU workers from original probe.
Every CSV row passes BOTH strict CLI validation and independent saved-board
audit. Candidate JSON is temporary and removed; none is written to Work.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import copy
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
from time import perf_counter

from gui.native_calibration import (
    Cancelled, CLI, FRONTEND, NATIVE, prerequisites, run_process,
)
from gui.work_directory import CSV_FIELDS

AUDITOR = FRONTEND / "tests/solver/auditSavedStrict.js"
DEFAULT_SEEDS = 2000
MOVE_CHOICES = (10000, 20000)


def _last_json(value: str):
    for line in reversed(value.splitlines()):
        if line.lstrip().startswith("{"):
            try:
                result = json.loads(line)
            except ValueError:
                continue
            if isinstance(result, dict):
                return result
    return None


def quality100(saved: dict) -> float:
    """Existing repo quality100 formula from run_audioex_10k_2000_quality.py.

    Q differs from native CLI 'quality' (0 on strict PASS).
    Compute it on the independently audited solved board, never the log.
    """
    board = saved["board"]
    wires = board["wires"]
    cuts = board["cuts"]
    length_mm = sum(
        math.hypot(
            w["from"]["row"] - w["to"]["row"],
            w["from"]["col"] - w["to"]["col"],
        ) for w in wires
    ) * 2.54
    unplaced = sum(
        not isinstance(c.get("boardPos"), dict)
        for c in saved.get("components", [])
        if not (c.get("offBoard") or c.get("boardExcluded"))
    )
    diagonals = sum(w["from"]["col"] != w["to"]["col"] for w in wires)
    return round(max(0.0, 100.0 -
                     0.6 * len(wires) - 0.4 * len(cuts) -
                     0.02 * length_mm - 10 * diagonals -
                     15 * unplaced), 2)


def _run_seed(project, moves, seed, drilled_only, stacking_allowed, cancelled):
    if cancelled():
        raise Cancelled()
    with tempfile.TemporaryDirectory(prefix=f"route_mate_pass1_s{seed:04d}_") as tmp:
        job = Path(tmp)
        inp = job / "input/projects/1.json"
        inp.parent.mkdir(parents=True)
        inp.write_text(json.dumps(project, ensure_ascii=False), encoding="utf-8")
        candidate = job / "candidate.json"
        env = os.environ.copy()
        env["V5_NATIVE_LIB_DIR"] = str(NATIVE)
        env.pop("V5_NATIVE_ROUTE_LIB_DIR", None)
        env["STRIPBOARD_TIMING"] = "1"
        command = [
            "node", str(CLI), "--data", str(job / "input"), "--id", "1",
            "--seed", str(seed), "--moves", str(moves), "--native", "1",
            "--strict", "1", "--drilled", "1" if drilled_only else "0",
            "--drill-domain", "1" if drilled_only else "0",
            "--nostack", "0" if stacking_allowed else "1",
            "--wire-polish", "0", "--routing-preference", "wires",
            "--save", str(candidate),
        ]
        start = perf_counter()
        exit_code, stdout, stderr = run_process(command, env, cancelled)
        seconds = round(perf_counter() - start, 3)
        result = _last_json(stdout) or {}
        if exit_code not in (0, 2):
            raise RuntimeError(
                f"Seed {seed} CLI exit={exit_code}: "
                f"{result.get('error') or stderr[-300:]}"
            )
        if (result.get("strictValid") is True) != (exit_code == 0):
            raise RuntimeError(f"Seed {seed} inconsistent native strict result/exit")
        if exit_code == 2:
            reason = ",".join(str(x) for x in (result.get("strictFailures") or []))
            return {"seed": seed, "valid": False, "seconds": seconds,
                    "reason": result.get("unsolvedReason") or reason or "strict invalid"}
        if not candidate.is_file():
            raise RuntimeError(f"Seed {seed} strict PASS missing candidate")
        saved = json.loads(candidate.read_text(encoding="utf-8"))
        audit_code, audit_stdout, audit_stderr = run_process(
            ["node", str(AUDITOR), str(candidate), str(inp)], env, cancelled,
        )
        audit = _last_json(audit_stdout) or {}
        if audit_code not in (0, 2):
            raise RuntimeError(f"Seed {seed} independent audit crashed: {audit_stderr[-300:]}")
        if audit_code != 0 or audit.get("valid") is not True:
            return {"seed": seed, "valid": False, "seconds": seconds,
                    "reason": "independent audit: " + str(audit.get("failures", []))}
        if (audit.get("wires") != result.get("wires") or
            audit.get("cuts") != result.get("cuts")):
            raise RuntimeError(f"Seed {seed} CLI and independent W/C disagree")
        if not stacking_allowed and audit.get("stacked", 0):
            raise RuntimeError(f"Seed {seed} stacking forbidden but audit found stacks")
        if drilled_only and any(c.get("kind", "between") != "hole"
                                for c in saved["board"]["cuts"]):
            raise RuntimeError(f"Seed {seed} drilled-only rule violated")
        return {
            "seed": seed, "valid": True, "cut": int(audit["cuts"]),
            "w": int(audit["wires"]), "q": quality100(saved),
            "time_taken": seconds,
        }


def run_pass_one(project, moves, workers, drilled_only, stacking_allowed,
                 pass_directory, on_progress, on_log, cancelled,
                 seeds=DEFAULT_SEEDS):
    """The GUI must clear the Pass One directory before launching this call."""
    if moves not in MOVE_CHOICES or workers not in (3, 4):
        raise ValueError("Pass One requires 10k/20k moves and 3/4 workers")
    if not isinstance(seeds, int) or seeds < 1:
        raise ValueError("Seed count must be positive")
    prerequisites()
    if not AUDITOR.is_file():
        raise RuntimeError(f"Independent saved-board auditor is missing: {AUDITOR}")
    prepared = copy.deepcopy(project)
    board = prepared["board"]
    if board.get("rows", 0) <= 0 or board.get("cols", 0) <= 0:
        raise ValueError("Invalid physical board")
    board["lockedRows"] = True
    board["lockedCols"] = True
    fingerprint = hashlib.sha256(
        json.dumps(prepared, sort_keys=True).encode("utf-8")
    ).hexdigest()
    folder = Path(pass_directory)
    if not folder.is_dir():
        raise FileNotFoundError(f"Pass One work directory missing: {folder}")
    csv_path = folder / "results.csv"
    log_path = folder / "activity.log"
    checked = qualified = 0
    with (csv_path.open("w", newline="", encoding="utf-8") as stream,
          log_path.open("w", encoding="utf-8") as report):
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        def log(message):
            report.write(message + "\n")
            report.flush()
            on_log(message)
        log(
            f"[PASS1][START] seeds=1..{seeds} moves={moves} workers={workers} "
            f"drilled_only={drilled_only} stacking_allowed={stacking_allowed} "
            f"input_sha256={fingerprint}"
        )
        try:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = [
                    pool.submit(_run_seed, prepared, moves, seed, drilled_only,
                                stacking_allowed, cancelled)
                    for seed in range(1, seeds + 1)
                ]
                try:
                    for future in as_completed(futures):
                        if cancelled():
                            raise Cancelled()
                        row = future.result()
                        checked += 1
                        if row["valid"]:
                            qualified += 1
                            writer.writerow({
                                "seed": f"{row['seed']:04d}", "cut": row["cut"],
                                "w": row["w"], "q": f"{row['q']:.2f}",
                                "time_taken": f"{row['time_taken']:.3f}",
                            })
                            stream.flush()
                            log(f"[PASS1][PASS] seed={row['seed']:04d} "
                                f"{row['w']}W/{row['cut']}C Q={row['q']:.2f} "
                                f"{row['time_taken']:.3f}s")
                        else:
                            log(f"[PASS1][REJECT] seed={row['seed']:04d} "
                                f"{row['seconds']:.3f}s {row['reason']}")
                        on_progress({"done": checked, "total": seeds,
                                     "qualified": qualified, "last": row})
                except BaseException:
                    for future in futures:
                        future.cancel()
                    raise
        except Cancelled:
            log(f"[PASS1][CANCELLED] {checked}/{seeds} attempted; "
                f"{qualified} audited rows retained in CSV")
            raise
        except BaseException as exc:
            log(f"[PASS1][ERROR] {type(exc).__name__}: {exc}")
            raise
        log(f"[PASS1][COMPLETE] {checked}/{seeds} seeds; "
            f"{qualified} independent strict PASS rows; output={csv_path}")
    return {"checked": checked, "qualified": qualified,
            "seeds": seeds, "moves": moves, "csv": str(csv_path),
            "log": str(log_path), "sha256": fingerprint}
