#!/usr/bin/env python3
"""Read-only static repository-integrity audit (standard library only).

Does NOT run an optimiser, install packages, modify projects, or certify a
routed board. Complements, rather than replaces, the native strict test suite.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "VERSION", "gui/VERSION", "run_gui.py", "gui/main.py",
    "gui/preflight.py", "render/schematic_bridge.py", "render/standalone_bridge.py",
    "pipeline/orchestrator.py", "prepare/sanity/electrical.py",
    "src/frontend/package.json", "src/frontend/tests/solver/v5Solve.js",
    "src/frontend/tests/solver/auditSavedStrict.js",
    "src/frontend/components/stripboard/v5wasm/decode.c",
    "src/frontend/components/stripboard/v5wasm/route.c",
    "src/frontend/standalone-renderer/dist/standalone-renderer/cli.js",
    "src/frontend/standalone-renderer/dist/standalone-renderer/schematic/cli.js",
    "test-fixtures/SHA256SUMS",
)
DELETED_APP_PATHS = ("desktop", "src/backend", "src/frontend/app", "src/frontend/public",
                     "src/frontend/components/schematic", "src/nginx")
TS_IMPORT = re.compile(r"\b(?:from\s+|require\s*\(\s*|import\s*\(\s*)['\"]([^'\"]+)['\"]")
HASH_LINE = re.compile(r"^([a-f0-9]{64})  (.+)$")


def check_repository(root: Path = ROOT) -> dict:
    """Assess the checked-out source tree, returning machine-readable findings."""
    errors: list[str] = []
    warnings: list[str] = []
    stats: dict[str, int] = {}
    # Inspect only Git-tracked files. An older checkout may retain untracked
    # desktop build debris; it must not be mistaken for a live legacy app.
    index = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root,
        capture_output=True, check=False,
    )
    if index.returncode:
        errors.append("Cannot read Git index: " + index.stderr.decode("utf-8", "replace"))
        return {"status": "FAIL", "errors": errors, "warnings": warnings, "stats": stats}
    tracked = set(index.stdout.decode("utf-8").strip("\0").split("\0"))
    stats["tracked_files"] = len(tracked)
    for rel in REQUIRED:
        if rel not in tracked or not (root / rel).is_file():
            errors.append(f"Missing required file: {rel}")
    for rel in DELETED_APP_PATHS:
        if any(path.startswith(rel + "/") for path in tracked):
            errors.append(f"Legacy application path tracked in Git: {rel}")
    if errors:
        return {"status": "FAIL", "errors": errors, "warnings": warnings, "stats": stats}

    repo_version = (root / "VERSION").read_text(encoding="utf-8").strip()
    gui_version = (root / "gui/VERSION").read_text(encoding="utf-8").strip()
    package = json.loads((root / "src/frontend/package.json").read_text(encoding="utf-8"))
    if not re.fullmatch(r"\d+\.\d{2}", repo_version):
        errors.append(f"Unexpected repository VERSION: {repo_version}")
    if not re.fullmatch(r"\d+\.\d{2}", gui_version):
        errors.append(f"Unexpected GUI VERSION: {gui_version}")
    if package.get("version") != f"{int(repo_version.split('.')[0])}.{int(repo_version.split('.')[1])}.0":
        errors.append("package.json version disagrees with repository VERSION")
    gui = (root / "gui/main.py").read_text(encoding="utf-8")
    if 'REPO_ROOT / "gui" / "VERSION"' not in gui:
        errors.append("GUI window is not reading gui/VERSION")
    _, _, stop_tail = gui.partition("    def solve_board(self):")
    stop, _, _ = stop_tail.partition("    def stop_solve(self):")
    if not stop or "self.solve_action.setEnabled(False)" not in stop or "return" not in stop:
        errors.append("GUI solver hard-stop guard missing")
    if "self.solve_action.setEnabled(True)" in gui:
        errors.append("GUI unexpectedly enables solver action")
    if "src/frontend/package-lock.json" not in tracked:
        warnings.append("No committed npm package-lock.json: npm dependency resolution is not frozen")

    fixture_dir = root / "test-fixtures"
    lines = (fixture_dir / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    listed: dict[str, str] = {}
    for line in lines:
        match = HASH_LINE.fullmatch(line)
        if not match:
            errors.append(f"Malformed SHA256SUMS line: {line[:60]}")
            continue
        expected, rel = match.groups()
        if rel in listed:
            errors.append(f"Duplicate fixture checksum entry: {rel}")
        listed[rel] = expected
        path = fixture_dir / rel
        if not path.is_file():
            errors.append(f"Missing fixture listed in SHA256SUMS: {rel}")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            errors.append(f"Fixture SHA256 mismatch: {rel}")
    actual = {rel[len("test-fixtures/"):] for rel in tracked
              if rel.startswith("test-fixtures/") and rel != "test-fixtures/SHA256SUMS"
              and (rel.endswith(".json") or rel.endswith(".net") or rel.endswith(".kicad_mod"))}
    for rel in sorted(actual - listed.keys()):
        errors.append(f"Fixture missing SHA256SUMS entry: {rel}")
    stats["fixture_files"] = len(actual)
    stats["fixture_hashes_checked"] = len(listed)

    for rel in ("masters/audio/audio.json", "masters/moto/moto.json", "masters/moto/motoex.json"):
        project = json.loads((fixture_dir / rel).read_text(encoding="utf-8"))
        parts, nets = project.get("components", []), project.get("nets", [])
        ids = [p.get("id") for p in parts]
        net_ids = [n.get("id") for n in nets]
        if len(set(ids)) != len(ids) or len(set(net_ids)) != len(net_ids):
            errors.append(f"Duplicate component/net IDs: {rel}")
        if any(x.get("componentId") not in ids or x.get("netId") not in net_ids
               for x in project.get("netAssignments", [])):
            errors.append(f"Invalid pin/component/net reference: {rel}")
        board = project.get("board", {})
        if not all(isinstance(board.get(k), int) and board[k] > 0 for k in ("rows", "cols")):
            errors.append(f"Invalid raw board dimensions: {rel}")
    stats["master_project_jsons_checked"] = 3

    # Git index gives a stable audit of the shipped source, not local build debris.
    ts_paths = sorted(root / path for path in tracked if path.endswith(".ts"))
    for file in ts_paths:
        rel_file = file.relative_to(root)
        for imported in TS_IMPORT.findall(file.read_text(encoding="utf-8")):
            if imported.startswith("@/"):
                target = root / "src/frontend" / imported[2:]
            elif imported.startswith("./") or imported.startswith("../"):
                target = file.parent / imported
            else:
                continue
            if not any(p.is_file() for p in (target, Path(str(target) + ".ts"),
                                             Path(str(target) + ".tsx"),
                                             Path(str(target) + ".js"),
                                             target / "index.ts", target / "index.js")):
                errors.append(f"Missing TypeScript source import: {rel_file} -> {imported}")
    stats["typescript_files_checked"] = len(ts_paths)

    py_paths = sorted(root / path for path in tracked if path.endswith(".py"))
    for file in py_paths:
        try:
            ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
        except (SyntaxError, UnicodeDecodeError) as exc:
            errors.append(f"Python syntax failure: {file.relative_to(root)}: {exc}")
    stats["python_files_parsed"] = len(py_paths)
    if "from solve.slide_fit import" in gui and not (root / "solve/slide_fit.py").exists():
        warnings.append("GUI Edge+Slide estimator references absent solve.slide_fit; ImportError is caught, so position count is unavailable")

    node_suites = list((root / "src/frontend/tests/solver").glob("*.test.js"))
    board_suites = list((root / "src/frontend/tests/board").glob("*.test.js"))
    stats["node_solver_default_suites"] = len(node_suites)
    stats["node_board_default_suites"] = len(board_suites)
    explicit = ["testAuditSavedStrict.js", "testNativeBodyBoardBounds.js",
                "testPackageBodyBoardBounds.js", "testWireColumnPolish.js"]
    for f in explicit:
        if not (root / "src/frontend/tests/solver" / f).exists():
            errors.append(f"Missing explicit regression: {f}")
    warnings.append("Additional test*.js scripts are not included by *.test.js default Node runner; run targeted regressions explicitly")
    warnings.append("Static check only: it does not compile C/TS, run PySide6, or independently verify a solved board")
    return {
        "status": "PASS" if not errors else "FAIL",
        "versions": {"repository": repo_version, "gui": gui_version,
                     "npm": package.get("version")},
        "errors": errors, "warnings": warnings, "stats": stats,
    }


def main() -> int:
    report = check_repository()
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if not report["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
