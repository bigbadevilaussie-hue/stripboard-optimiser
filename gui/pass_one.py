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
import uuid
from pathlib import Path
import subprocess
import tempfile
from time import perf_counter

from gui.native_calibration import (
    Cancelled, CLI, FRONTEND, NATIVE, prerequisites, run_process,
)
from gui.work_directory import (
    CAMPAIGN_FIELDS, CAMPAIGN_MANIFEST, load_campaign_records,
    winner_budget_dir,
)

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


def _run_seed(project, moves, seed, drilled_only, stacking_allowed, cancelled,
              *, retained_candidate=None):
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
        if retained_candidate is not None:
            # Only the separately verified replay champion is persisted.
            target = Path(retained_candidate)
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_suffix(".json.tmp")
            temporary.write_bytes(candidate.read_bytes())
            os.replace(temporary, target)
        return {
            "seed": seed, "valid": True, "cut": int(audit["cuts"]),
            "w": int(audit["wires"]), "q": quality100(saved),
            "time_taken": seconds,
        }



def _prepared_input(project):
    prepared = copy.deepcopy(project)
    board = prepared["board"]
    if board.get("rows", 0) <= 0 or board.get("cols", 0) <= 0:
        raise ValueError("Invalid physical board")
    board["lockedRows"] = True
    board["lockedCols"] = True
    fingerprint = hashlib.sha256(
        json.dumps(prepared, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return prepared, fingerprint


def _campaign_identity(fingerprint, moves, workers, drilled_only,
                       stacking_allowed, seeds):
    return {
        "schema": 1,
        "input_sha256": fingerprint,
        "moves": moves,
        "workers": workers,
        "drilled_only": bool(drilled_only),
        "stacking_allowed": bool(stacking_allowed),
        "seeds": seeds,
    }


def _save_state(path, state):
    """Atomic state change; a crash never leaves a half-written manifest."""
    temporary = Path(path).with_name(Path(path).name + f".{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def inspect_pass_one_campaign(project, moves, workers, drilled_only,
                              stacking_allowed, pass_directory,
                              seeds=DEFAULT_SEEDS):
    """Preflight resume BEFORE the GUI offers Resume, Restart or Cancel."""
    _, fingerprint = _prepared_input(project)
    expected = _campaign_identity(
        fingerprint, moves, workers, drilled_only, stacking_allowed, seeds
    )
    folder = Path(pass_directory)
    metadata = folder / CAMPAIGN_MANIFEST
    csv_path = folder / "results.csv"
    if not metadata.is_file() or metadata.is_symlink():
        raise ValueError("Cannot resume: campaign metadata is missing or unsafe")
    if not csv_path.is_file() or csv_path.is_symlink():
        raise ValueError("Cannot resume: campaign CSV is missing or unsafe")
    info = json.loads(metadata.read_text(encoding="utf-8"))
    for key, value in expected.items():
        if info.get(key) != value:
            raise ValueError(f"Cannot resume: {key} differs from the saved campaign")
    records = load_campaign_records(csv_path)
    if any(seed > seeds for seed in records):
        raise ValueError("Cannot resume: saved CSV has out-of-budget seed numbers")
    confirmed = {seed: row for seed, row in records.items()
                 if row["status"] in ("PASS", "FAIL")}
    failed = [seed for seed, row in records.items() if row["status"] == "ERROR"]
    saved_times = [float(row["time_taken"]) for row in confirmed.values()
                   if row.get("time_taken") not in (None, "")]
    return {
        "state": info.get("state", "INCOMPLETE"),
        "done": len(confirmed),
        "qualified": sum(row["status"] == "PASS" for row in confirmed.values()),
        "errors": len(failed),
        "remaining": seeds - len(confirmed),
        "seconds_per_seed": (sum(saved_times) / len(saved_times)
                             if saved_times else None),
        "records": confirmed,
        "identity": expected,
    }


def run_pass_one(project, moves, workers, drilled_only, stacking_allowed,
                 pass_directory, on_progress, on_log, cancelled,
                 seeds=DEFAULT_SEEDS, *, resume=False):
    """Persist PASS/FAIL/ERROR per seed; resume only missing or errored seeds.

    The caller chooses an empty budget folder (Restart) or a matching existing
    campaign (Resume). Legacy success-only CSVs are never silently overwritten.
    """
    if moves not in MOVE_CHOICES or workers not in (3, 4):
        raise ValueError("Pass One requires 10k/20k moves and 3/4 workers")
    if not isinstance(seeds, int) or seeds < 1:
        raise ValueError("Seed count must be positive")
    prerequisites()
    if not AUDITOR.is_file():
        raise RuntimeError(f"Independent saved-board auditor is missing: {AUDITOR}")
    prepared, fingerprint = _prepared_input(project)
    identity = _campaign_identity(
        fingerprint, moves, workers, drilled_only, stacking_allowed, seeds
    )
    folder = Path(pass_directory)
    if not folder.is_dir() or folder.is_symlink():
        raise FileNotFoundError(f"Pass One work directory missing/unsafe: {folder}")
    csv_path = folder / "results.csv"
    log_path = folder / "activity.log"
    manifest = folder / CAMPAIGN_MANIFEST
    if resume:
        snapshot = inspect_pass_one_campaign(
            project, moves, workers, drilled_only, stacking_allowed,
            folder, seeds=seeds
        )
        if snapshot["state"] == "COMPLETED":
            raise ValueError("Campaign already complete; use Restart to run again")
        retained = snapshot["records"]
        # Remove previous ERROR rows atomically: they are the seeds to retry.
        temporary = folder / f"results.{uuid.uuid4().hex}.tmp"
        try:
            with temporary.open("w", newline="", encoding="utf-8") as out:
                writer = csv.DictWriter(out, fieldnames=CAMPAIGN_FIELDS)
                writer.writeheader()
                for seed in sorted(retained):
                    writer.writerow(retained[seed])
                out.flush()
                os.fsync(out.fileno())
            os.replace(temporary, csv_path)
        finally:
            temporary.unlink(missing_ok=True)
    else:
        if csv_path.exists() or manifest.exists() or log_path.exists():
            raise ValueError("Pass One files already exist; confirm Restart or Resume first")
        retained = {}

    checked = len(retained)
    qualified = sum(row["status"] == "PASS" for row in retained.values())
    failures = sum(row["status"] == "FAIL" for row in retained.values())
    errors = 0
    attempts = [seed for seed in range(1, seeds + 1) if seed not in retained]
    _save_state(manifest, {**identity, "state": "INCOMPLETE",
                           "confirmed": checked, "qualified": qualified})

    with (csv_path.open("a" if resume else "w", newline="", encoding="utf-8") as stream,
          log_path.open("a" if resume else "w", encoding="utf-8") as report):
        writer = csv.DictWriter(stream, fieldnames=CAMPAIGN_FIELDS)
        if not resume:
            writer.writeheader()
            stream.flush()

        def log(message):
            report.write(message + "\n")
            report.flush()
            on_log(message)

        def progress(last=None):
            on_progress({"done": checked, "total": seeds,
                         "qualified": qualified, "failed": failures,
                         "errors": errors, "last": last})

        log(
            f"[PASS1][{'RESUME' if resume else 'START'}] seeds=1..{seeds} "
            f"moves={moves} workers={workers} drilled_only={drilled_only} "
            f"stacking_allowed={stacking_allowed} input_sha256={fingerprint} "
            f"retained={checked} pending={len(attempts)}"
        )
        progress()

        def safe_seed(seed):
            started = perf_counter()
            try:
                return _run_seed(prepared, moves, seed, drilled_only,
                                 stacking_allowed, cancelled)
            except Cancelled:
                raise
            except Exception as exc:
                return {
                    "seed": seed, "valid": None,
                    "seconds": round(perf_counter() - started, 3),
                    "reason": f"{type(exc).__name__}: {exc}",
                }

        try:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = [pool.submit(safe_seed, seed) for seed in attempts]
                try:
                    for future in as_completed(futures):
                        if cancelled():
                            raise Cancelled()
                        row = future.result()
                        seed = row["seed"]
                        seconds = row.get("time_taken", row.get("seconds", 0.0))
                        if row["valid"] is True:
                            status = "PASS"
                            checked += 1
                            qualified += 1
                        elif row["valid"] is False:
                            status = "FAIL"
                            checked += 1
                            failures += 1
                        else:
                            status = "ERROR"
                            errors += 1
                        data = {
                            "seed": f"{seed:04d}",
                            "cut": row.get("cut", ""),
                            "w": row.get("w", ""),
                            "q": f"{row['q']:.2f}" if status == "PASS" else "",
                            "time_taken": f"{seconds:.3f}",
                            "status": status,
                            "reason": str(row.get("reason") or "").replace("\n", " ")[:1000],
                        }
                        writer.writerow(data)
                        stream.flush()
                        os.fsync(stream.fileno())
                        if status == "PASS":
                            log(f"[PASS1][PASS] seed={seed:04d} "
                                f"{row['w']}W/{row['cut']}C Q={row['q']:.2f} "
                                f"{seconds:.3f}s")
                        else:
                            log(f"[PASS1][{status}] seed={seed:04d} "
                                f"{seconds:.3f}s {data['reason']}")
                        progress(row)
                except BaseException:
                    for future in futures:
                        future.cancel()
                    raise
        except Cancelled:
            _save_state(manifest, {**identity, "state": "STOPPED",
                                   "confirmed": checked, "qualified": qualified})
            log(f"[PASS1][CANCELLED] {checked}/{seeds} confirmed; "
                f"{qualified} PASS, {failures} FAIL, {errors} ERROR rows retained")
            raise
        except BaseException as exc:
            _save_state(manifest, {**identity, "state": "INCOMPLETE",
                                   "confirmed": checked, "qualified": qualified})
            log(f"[PASS1][ERROR] {type(exc).__name__}: {exc}")
            raise

        completed = (checked == seeds and errors == 0)
        _save_state(manifest, {**identity,
                               "state": "COMPLETED" if completed else "INCOMPLETE",
                               "confirmed": checked, "qualified": qualified})
        log(f"[PASS1][{'COMPLETE' if completed else 'INCOMPLETE'}] "
            f"{checked}/{seeds} confirmed; {qualified} strict PASS, "
            f"{failures} FAIL, {errors} ERROR; output={csv_path}")

    result = {
        "checked": checked, "qualified": qualified, "failed": failures,
        "errors": errors, "completed": completed,
        "seeds": seeds, "moves": moves, "csv": str(csv_path),
        "log": str(log_path), "sha256": fingerprint,
        "winner_json": None, "winner_error": None,
    }
    if completed and qualified:
        records = load_campaign_records(csv_path)
        winners = (row for row in records.values() if row["status"] == "PASS")
        winner = sorted(winners,
                        key=lambda r: (-float(r["q"]), int(r["w"]),
                                       int(r["cut"]), int(r["seed"])))[0]
        seed = int(winner["seed"])
        winner_folder = winner_budget_dir(folder.parent.parent, moves, create=True)
        target = winner_folder / f"winner_seed_{seed:04d}.json"
        try:
            replay = _run_seed(
                prepared, moves, seed, drilled_only, stacking_allowed,
                cancelled, retained_candidate=target
            )
            if (replay["valid"] is not True
                or replay["w"] != int(winner["w"])
                or replay["cut"] != int(winner["cut"])
                or replay["q"] != float(winner["q"])):
                raise ValueError("Replay differs from the audited Pass One CSV winner")
            result["winner_json"] = str(target)
            result["winner_seed"] = seed
            on_log(f"[PASS1][WINNER] seed={seed:04d} {replay['w']}W/"
                   f"{replay['cut']}C Q={replay['q']:.2f} strict replay saved: {target}")
        except Exception as exc:
            target.unlink(missing_ok=True)
            result["winner_error"] = f"{type(exc).__name__}: {exc}"
            on_log(f"[PASS1][WINNER][ERROR] {result['winner_error']}; no winner SVG authorised")
    return result
