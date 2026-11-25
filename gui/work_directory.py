"""Stable Route-Mate Work directory and strictly isolated pass outputs.

Only an explicit GO for a stage may clear THAT stage's folder. Importing,
launching the GUI, and opening the other stage never erase any outputs.
"""
from __future__ import annotations

import csv
import copy
import hashlib
import json
import re
import shutil
import unicodedata
import math
from gui.quality import QUALITY_VERSION
from pathlib import Path

from gui.runtime_paths import work_root

WORK_ROOT = work_root()
PASS_ONE = "pass 1"
PASS_TWO = "pass 2"
SUBDIRS = (PASS_ONE, PASS_TWO, "jsons", "logs")
CSV_FIELDS = ("seed", "cut", "w", "q", "time_taken")

CAMPAIGN_FIELDS = CSV_FIELDS + ("s", "wire_length_mm", "quality_version", "status", "reason")
CAMPAIGN_MANIFEST = "campaign.json"
MOVE_BUDGETS = (10000, 20000)


def pass_one_budget_dir(root: Path, moves: int, *, create: bool = False,
                        debug: bool = False) -> Path:
    """Full and 200-seed debug campaigns are isolated for each move budget."""
    if moves not in MOVE_BUDGETS:
        raise ValueError(f"Unsupported Pass One move budget: {moves}")
    base = Path(root) / PASS_ONE / f"{moves // 1000}k"
    folder = base / "debug" if debug else base
    if base.is_symlink() or folder.is_symlink():
        raise ValueError(f"Refusing symlinked Pass One campaign: {folder}")
    if create:
        ensure_work(root)
        folder.mkdir(parents=True, exist_ok=True)
    return folder


def winner_budget_dir(root: Path, moves: int, *, create: bool = False,
                      debug: bool = False) -> Path:
    if moves not in MOVE_BUDGETS:
        raise ValueError(f"Unsupported Pass One move budget: {moves}")
    base = Path(root) / "jsons" / f"{moves // 1000}k"
    folder = base / "debug" if debug else base
    if base.is_symlink() or folder.is_symlink():
        raise ValueError(f"Refusing symlinked winner directory: {folder}")
    if create:
        ensure_work(root)
        folder.mkdir(parents=True, exist_ok=True)
    return folder


def pass_one_campaign_sources(root: Path) -> list[tuple[str, Path]]:
    """Completed/incomplete budgeted CSVs and unmodified legacy CSV.

    The GUI shows both so an old 10k Moto CSV remains accessible in Pass Two.
    """
    base = Path(root) / PASS_ONE
    result = []
    for moves in MOVE_BUDGETS:
        folder = pass_one_budget_dir(root, moves)
        csv_file = folder / "results.csv"
        if csv_file.is_file() and not csv_file.is_symlink():
            result.append((f"{moves // 1000}k moves", csv_file))
        debug_csv = pass_one_budget_dir(root, moves, debug=True) / "results.csv"
        if debug_csv.is_file() and not debug_csv.is_symlink():
            result.append((f"{moves // 1000}k moves (DEBUG 200)", debug_csv))
    old = base / "results.csv"
    if old.is_file() and not old.is_symlink():
        result.append(("Legacy Pass One (preserved)", old))
    return result


def campaign_existing_files(root: Path, moves: int, *, debug: bool = False) -> list[Path]:
    """Inventory only the selected full or debug campaign for confirmation."""
    paths = (pass_one_budget_dir(root, moves, debug=debug),
             winner_budget_dir(root, moves, debug=debug))
    found = []
    for folder in paths:
        if folder.is_symlink():
            raise ValueError(f"Refusing symlinked campaign directory: {folder}")
        if folder.is_dir():
            for child in sorted(folder.iterdir()):
                if not debug and child.name == "debug":
                    if child.is_symlink():
                        raise ValueError(f"Refusing symlinked debug directory: {child}")
                    continue
                found.append(child)
    return found


def clear_pass_one_budget(root: Path, moves: int, *, debug: bool = False) -> Path:
    """Clear ONLY the approved full/debug campaign, preserving its sibling."""
    workspace = ensure_work(root)
    folders = (pass_one_budget_dir(workspace, moves, create=True, debug=debug),
               winner_budget_dir(workspace, moves, create=True, debug=debug))
    for folder in folders:
        if folder.is_symlink():
            raise ValueError(f"Refusing symlinked campaign directory: {folder}")
        for child in folder.iterdir():
            if not debug and child.name == "debug":
                if child.is_symlink():
                    raise ValueError(f"Refusing symlinked debug directory: {child}")
                continue
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()
    return pass_one_budget_dir(workspace, moves, debug=debug)


def load_campaign_records(csv_file: Path) -> dict[int, dict]:
    """Load every recorded attempt; no seed inferred from row order."""
    path = Path(csv_file)
    records = {}
    with path.open("r", newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != CAMPAIGN_FIELDS:
            raise ValueError(f"Unexpected campaign CSV columns: {reader.fieldnames!r}")
        for index, row in enumerate(reader, 2):
            try:
                seed = int(row["seed"])
                status = row["status"]
            except (KeyError, ValueError, TypeError) as exc:
                raise ValueError(f"Invalid campaign CSV row {index}: {exc}") from exc
            if seed <= 0 or seed in records or status not in ("PASS", "FAIL", "ERROR"):
                raise ValueError(f"Duplicate seed or invalid status at row {index}")
            if row.get("quality_version") != QUALITY_VERSION:
                raise ValueError(f"Wrong quality version at row {index}")
            if status == "PASS":
                try:
                    cut = int(row["cut"])
                    wire = int(row["w"])
                    quality = float(row["q"])
                    stack = int(row["s"])
                    length = float(row["wire_length_mm"])
                    if stack < 0 or stack > wire or (wire > 0 and stack == 0) or not math.isfinite(length) or length < 0:
                        raise ValueError("Invalid stack or wire length")
                    if cut < 0 or wire < 0 or not 0 <= quality <= 100:
                        raise ValueError("W/C/Q outside valid range")
                except (ValueError, TypeError, KeyError) as exc:
                    raise ValueError(f"Invalid PASS metrics at row {index}: {exc}") from exc
            records[seed] = dict(row)
    return records



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


def read_pass_one(root: Path = WORK_ROOT, *, csv_path: Path | None = None) -> list[dict]:
    """Read verified PASS seeds only; old successful-only CSVs stay readable.

    New budget campaigns must be COMPLETED before they enter Pass Two.
    """
    path = Path(csv_path) if csv_path is not None else stage_path(PASS_ONE, root) / "results.csv"
    if not path.is_file() or path.is_symlink():
        raise FileNotFoundError(f"Pass One CSV not found or is a symlink: {path}")
    rows = []
    seen = set()
    with path.open("r", newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fields = tuple(reader.fieldnames or ())
        if fields == CSV_FIELDS + ("status", "reason"):
            raise ValueError(f"Q1/Q2 campaign obsolete; rerun Pass One using {QUALITY_VERSION}")
        if fields not in (CSV_FIELDS, CAMPAIGN_FIELDS):
            raise ValueError(f"Unexpected Pass One CSV columns: {reader.fieldnames!r}")
        if fields == CAMPAIGN_FIELDS:
            manifest = path.parent / CAMPAIGN_MANIFEST
            if not manifest.is_file() or manifest.is_symlink():
                raise ValueError(f"Missing campaign completion metadata: {manifest}")
            state = json.loads(manifest.read_text(encoding="utf-8"))
            if state.get("quality_version") != QUALITY_VERSION:
                raise ValueError(f"Q1/Q2 campaign obsolete; rerun Pass One using {QUALITY_VERSION}")
            if state.get("state") != "COMPLETED":
                raise ValueError(f"Pass One {path.parent.name} is {state.get('state', 'INCOMPLETE')}; resume it before Pass Two.")
        for number, row in enumerate(reader, 2):
            if fields == CAMPAIGN_FIELDS and row.get("quality_version") != QUALITY_VERSION:
                raise ValueError(f"Wrong quality version on row {number}")
            try:
                seed = int(row["seed"])
            except (TypeError, ValueError, KeyError) as exc:
                raise ValueError(f"Invalid Pass One seed on row {number}: {exc}") from exc
            if seed <= 0 or seed in seen:
                raise ValueError(f"Invalid or duplicate seed on row {number}")
            seen.add(seed)
            if fields == CAMPAIGN_FIELDS:
                if row["status"] not in ("PASS", "FAIL", "ERROR"):
                    raise ValueError(f"Invalid Pass One status at row {number}")
                if row["status"] != "PASS":
                    continue
            try:
                cuts = int(row["cut"])
                wires = int(row["w"])
                quality = float(row["q"])
                seconds = float(row["time_taken"])
            except (TypeError, ValueError, KeyError) as exc:
                raise ValueError(f"Invalid Pass One PASS row {number}: {exc}") from exc
            import math
            if (cuts < 0 or wires < 0 or not math.isfinite(quality)
                or not 0 <= quality <= 100 or not math.isfinite(seconds)
                or seconds < 0):
                raise ValueError(f"Invalid Pass One metrics on row {number}")
            record = {"seed": seed, "cut": cuts, "w": wires,
                      "q": quality, "time_taken": seconds}
            if fields == CAMPAIGN_FIELDS:
                stack, length = int(row["s"]), float(row["wire_length_mm"])
                if not 0 <= stack <= wires or not math.isfinite(length) or length < 0:
                    raise ValueError(f"Invalid {QUALITY_VERSION} metrics at row {number}")
                record.update(s=stack, wire_length_mm=length, quality_version=QUALITY_VERSION)
            rows.append(record)
    return rows


def prepare_pass_two(root: Path = WORK_ROOT, *,
                     source_csv: Path | None = None) -> tuple[Path, int]:
    """Import verified survivors from the exact selected budget/legacy CSV."""
    rows = read_pass_one(root, csv_path=source_csv)
    if not rows:
        raise ValueError("Pass One has no independently verified qualifying rows")
    if any(row.get("quality_version") != QUALITY_VERSION for row in rows):
        raise ValueError(f"Q1/Q2 results cannot enter Pass Two; rerun Pass One using {QUALITY_VERSION}")
    folder = clear_started_pass(PASS_TWO, root)
    target = folder / "candidates.csv"
    with target.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=CSV_FIELDS + ("s", "wire_length_mm", "quality_version"))
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "seed": f"{row['seed']:04d}",
                             "q": f"{row['q']:.2f}",
                             "time_taken": f"{row['time_taken']:.3f}"})
    with (folder / "activity.log").open("w", encoding="utf-8") as log:
        log.write(f"PASS TWO IMPORT: {len(rows)} verified Pass One CSV rows\n")
        log.write(f"Quality version: {QUALITY_VERSION}\n")
        log.write(f"Source: {source_csv or (stage_path(PASS_ONE, root) / 'results.csv')}\n")
        log.write("Native Pass Two optimiser not started: search policy still unassigned.\n")
    return target, len(rows)


# A workspace is identified by the canonical SOURCE FILE PATH, never by the
# contents of the JSON. Editing a file keeps its workspace. Files with the same
# name in two different folders cannot collide.
WORKSPACE_SCHEMA = 1
WORKSPACE_MANIFEST = "project.json.info"
_WORKSPACE_ID = re.compile(r"^[a-z0-9][a-z0-9-]*--[a-f0-9]{12}$")


def _canonical_source(source: Path) -> Path:
    file = Path(source).expanduser().resolve()
    if file.suffix.lower() != ".json" or not file.is_file():
        raise ValueError(f"Expected an existing source .json file: {source}")
    return file


def project_workspace_name(source: Path) -> str:
    """Stable, readable and collision-resistant: audio--e3b1... (12 hex)."""
    path = _canonical_source(source)
    normal = unicodedata.normalize("NFKD", path.stem)
    slug = re.sub(r"[^a-z0-9]+", "-", normal.encode("ascii", "ignore").decode().lower())
    slug = slug.strip("-")[:48].rstrip("-") or "project"
    digest = hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:12]
    return f"{slug}--{digest}"


def ensure_workspace_root(root: Path = WORK_ROOT) -> Path:
    """Ensure Work/ itself exists, WITHOUT creating any global pass folders."""
    folder = Path(root)
    if folder.is_symlink():
        raise ValueError(f"Refusing a symlinked Work directory: {folder}")
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _read_manifest(folder: Path) -> dict:
    manifest = folder / WORKSPACE_MANIFEST
    if manifest.is_symlink():
        raise ValueError(f"Refusing symlinked workspace metadata: {manifest}")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if (data.get("schema") != WORKSPACE_SCHEMA
            or not isinstance(data.get("source_path"), str)
            or not isinstance(data.get("source_name"), str)
            or data.get("workspace_name") != folder.name):
        raise ValueError(f"Invalid workspace metadata: {manifest}")
    return data


def project_workspace(source: Path, root: Path = WORK_ROOT, *, create: bool = False) -> Path:
    """Return ONE stable workspace per source JSON, independent of JSON edits."""
    file = _canonical_source(source)
    base = Path(root)
    folder = base / project_workspace_name(file)
    if not create:
        if not folder.is_dir() or folder.is_symlink():
            raise FileNotFoundError(f"No project workspace: {folder}")
    else:
        ensure_workspace_root(base)
        if folder.is_symlink():
            raise ValueError(f"Refusing symlinked project workspace: {folder}")
        ensure_work(folder)  # Only the chosen project's own four subdirectories.
    manifest = folder / WORKSPACE_MANIFEST
    if manifest.exists() or manifest.is_symlink():
        data = _read_manifest(folder)
        if data["source_path"] != str(file) or data["source_name"] != file.name:
            raise ValueError(f"Workspace already belongs to another JSON: {folder}")
    elif create:
        manifest.write_text(
            json.dumps({"schema": WORKSPACE_SCHEMA, "source_name": file.name,
                        "source_path": str(file), "workspace_name": folder.name},
                       indent=2) + "\n",
            encoding="utf-8",
        )
    else:
        raise ValueError(f"Workspace lacks source metadata: {folder}")
    return folder


def list_project_workspaces(root: Path = WORK_ROOT) -> list[tuple[str, Path]]:
    """Discover named projects on cold GUI launch, without reading source JSONs."""
    base = Path(root)
    if not base.exists():
        return []
    if base.is_symlink():
        raise ValueError(f"Refusing symlinked Work directory: {base}")
    found = []
    for folder in base.iterdir():
        if folder.is_symlink() or not folder.is_dir() or not _WORKSPACE_ID.fullmatch(folder.name):
            continue
        if not (folder / WORKSPACE_MANIFEST).is_file():
            continue
        data = _read_manifest(folder)
        # Identity check does not require original JSON to still be present.
        path = Path(data["source_path"])
        normal = unicodedata.normalize("NFKD", path.stem)
        slug = re.sub(r"[^a-z0-9]+", "-", normal.encode("ascii", "ignore").decode().lower())
        slug = slug.strip("-")[:48].rstrip("-") or "project"
        digest = hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:12]
        if folder.name != f"{slug}--{digest}" or path.name != data["source_name"]:
            raise ValueError(f"Workspace identity mismatch: {folder}")
        found.append((f"{data['source_name']}  ·  {folder.name}", folder))
    return sorted(found, key=lambda item: item[0].casefold())


def adopt_matching_legacy_pass_one(project: dict, folder: Path,
                                   root: Path = WORK_ROOT) -> bool:
    """COPY old root-level results only when their exact prepared input SHA matches.

    Never move or overwrite existing results; unmatched legacy data stays where
    it is. This allows the old champion to survive the workspace transition.
    """
    source = Path(root) / PASS_ONE
    old_csv, old_log = source / "results.csv", source / "activity.log"
    target = Path(folder) / PASS_ONE
    if not old_csv.is_file() or not old_log.is_file() or not target.is_dir():
        return False
    if any(target.iterdir()):
        return False
    prepared = copy.deepcopy(project)
    prepared["board"]["lockedRows"] = True
    prepared["board"]["lockedCols"] = True
    signature = hashlib.sha256(
        json.dumps(prepared, sort_keys=True).encode("utf-8")
    ).hexdigest()
    first_line = next(
        (line for line in old_log.read_text(encoding="utf-8").splitlines()
         if line.startswith("[PASS1][START] ")), ""
    )
    if f"input_sha256={signature}" not in first_line.split():
        return False
    if not read_pass_one(root):
        return False
    # Only create destination files; the originals remain untouched.
    with (target / "results.csv").open("xb") as output:
        output.write(old_csv.read_bytes())
    with (target / "activity.log").open("xb") as output:
        output.write(old_log.read_bytes())
    return True
