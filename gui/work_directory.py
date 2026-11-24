"""Stable Route-Mate Work directory and strictly isolated pass outputs.

Only an explicit GO for a stage may clear THAT stage's folder. Importing,
launching the GUI, and opening the other stage never erase any outputs.
"""
from __future__ import annotations

import csv
from pathlib import Path
import shutil

WORK_ROOT = Path(__file__).resolve().parents[1] / "Work"
PASS_ONE = "pass 1"
PASS_TWO = "pass 2"
SUBDIRS = (PASS_ONE, PASS_TWO, "jsons", "logs")
CSV_FIELDS = ("seed", "cut", "w", "q", "time_taken")


def ensure_work(root: Path = WORK_ROOT) -> Path:
    root = Path(root)
    if root.is_symlink():
        raise ValueError(f"Refusing a symlinked Work directory: {root}")
    root.mkdir(parents=True, exist_ok=True)
    for name in SUBDIRS:
        path = root / name
        if path.is_symlink():
            raise ValueError(f"Refusing a symlinked Work subdirectory: {path}")
        path.mkdir(parents=True, exist_ok=True)
    return root


def stage_path(stage: str, root: Path = WORK_ROOT) -> Path:
    if stage not in (PASS_ONE, PASS_TWO):
        raise ValueError("Only 'pass 1' or 'pass 2' may be cleared")
    return Path(root) / stage


def clear_started_pass(stage: str, root: Path = WORK_ROOT) -> Path:
    """Destructive by design; call ONLY after that pass's explicit GO click.

    A symlink or unexpected stage cannot redirect deletion into user data.
    The shared jsons/logs and the other pass are never touched.
    """
    root = ensure_work(root)
    folder = stage_path(stage, root)
    if folder.is_symlink():
        raise ValueError("Refusing to clear a symlinked pass directory")
    for child in folder.iterdir():
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()
    return folder


def read_pass_one(root: Path = WORK_ROOT) -> list[dict]:
    """Load only vetted Pass One CSV rows, preserving every qualifying seed.

    No solver call; works immediately after opening the GUI without JSON import.
    """
    path = stage_path(PASS_ONE, root) / "results.csv"
    if not path.is_file():
        raise FileNotFoundError(f"Pass One CSV not found: {path}")
    rows = []
    seen = set()
    with path.open("r", newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != CSV_FIELDS:
            raise ValueError(f"Unexpected Pass One CSV columns: {reader.fieldnames!r}")
        for number, row in enumerate(reader, 2):
            try:
                seed = int(row["seed"])
                cuts = int(row["cut"])
                wires = int(row["w"])
                quality = float(row["q"])
                seconds = float(row["time_taken"])
            except (TypeError, ValueError, KeyError) as exc:
                raise ValueError(f"Invalid Pass One CSV row {number}: {exc}") from exc
            import math
            if (seed <= 0 or seed in seen or cuts < 0 or wires < 0
                or not math.isfinite(quality) or not 0 <= quality <= 100
                or not math.isfinite(seconds) or seconds < 0):
                raise ValueError(f"Invalid or duplicate Pass One seed on row {number}")
            seen.add(seed)
            rows.append({"seed": seed, "cut": cuts, "w": wires,
                         "q": quality, "time_taken": seconds})
    return rows


def prepare_pass_two(root: Path = WORK_ROOT) -> tuple[Path, int]:
    """Import every Pass One survivor. No unapproved Pass Two search algorithm.

    Validate the source before touching existing Pass Two files.
    """
    rows = read_pass_one(root)
    if not rows:
        raise ValueError("Pass One has no independently verified qualifying rows")
    folder = clear_started_pass(PASS_TWO, root)
    target = folder / "candidates.csv"
    with target.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "seed": f"{row['seed']:04d}",
                             "q": f"{row['q']:.2f}",
                             "time_taken": f"{row['time_taken']:.3f}"})
    with (folder / "activity.log").open("w", encoding="utf-8") as log:
        log.write(f"PASS TWO IMPORT: {len(rows)} verified Pass One CSV rows\n")
        log.write(f"Source: {stage_path(PASS_ONE, root) / 'results.csv'}\n")
        log.write("Native Pass Two optimiser not started: search policy still unassigned.\n")
    return target, len(rows)
