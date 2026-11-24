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
from pathlib import Path

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
