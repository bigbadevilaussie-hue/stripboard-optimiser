"""Run the solver's --speedprobe against a project and return ms/decode.

Self-contained: resolves node and the solver harness relative to the repo,
does not import solver_adapter. Can be called with any project JSON. Fails
cleanly (ok=False) on any error; never raises.
"""
import json
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path


# Repo layout: <repo>/desktop/src/stripboard_optimizer/solver/probe.py
#              <repo>/src/frontend/tests/solver/v5Solve.js
_HERE = Path(__file__).resolve()
_REPO = _HERE.parent.parent.parent.parent.parent
_FRONTEND = _REPO / "src" / "frontend"
_HARNESS = _FRONTEND / "tests" / "solver" / "v5Solve.js"


@dataclass
class ProbeResult:
    ok: bool
    ms_per_decode: float | None
    decodes: int
    elapsed_ms: float | None
    error: str | None
    node_path: str | None


def _resolve_node() -> str | None:
    node = shutil.which("node")
    if node:
        return node
    for guess in ("/usr/local/bin/node", "/opt/homebrew/bin/node", "/opt/local/bin/node"):
        if os.path.isfile(guess) and os.access(guess, os.X_OK):
            return guess
    return None


def run_speed_probe(project_json_path: str | Path, decodes: int = 10,
                    timeout_s: int = 60) -> ProbeResult:
    project = Path(project_json_path).expanduser().resolve()
    if not project.is_file():
        return ProbeResult(False, None, decodes, None,
                           f"Project JSON not found: {project}", None)
    if not _HARNESS.is_file():
        return ProbeResult(False, None, decodes, None,
                           f"Solver harness not found: {_HARNESS}", None)
    node = _resolve_node()
    if node is None:
        return ProbeResult(False, None, decodes, None,
                           "node executable not found on PATH", None)

    work = Path(tempfile.mkdtemp(prefix="probe_"))
    try:
        projects = work / "projects"
        projects.mkdir(parents=True)
        shutil.copy2(project, projects / "1.json")

        cmd = [
            node, str(_HARNESS),
            "--data", str(work), "--id", "1",
            "--seed", "0", "--speedprobe", str(decodes),
        ]
        t0 = time.monotonic()
        try:
            r = subprocess.run(cmd, cwd=str(_FRONTEND),
                               capture_output=True, text=True, timeout=timeout_s)
        except subprocess.TimeoutExpired:
            return ProbeResult(False, None, decodes, None,
                               f"Speed probe timed out after {timeout_s}s", node)
        elapsed_ms = (time.monotonic() - t0) * 1000.0

        if r.returncode != 0:
            tail = (r.stderr or r.stdout or "").strip().splitlines()
            tail = tail[-3:] if tail else []
            return ProbeResult(False, None, decodes, elapsed_ms,
                               "probe exited " + str(r.returncode) + ": " + " | ".join(tail),
                               node)

        for line in (r.stderr or "").splitlines():
            line = line.strip()
            if line.startswith("probeMs "):
                try:
                    ms = float(line.split()[1])
                    return ProbeResult(True, ms, decodes, elapsed_ms, None, node)
                except (IndexError, ValueError):
                    return ProbeResult(False, None, decodes, elapsed_ms,
                                       f"probeMs line unparseable: {line}", node)
        return ProbeResult(False, None, decodes, elapsed_ms,
                           "probe finished without a probeMs line on stderr", node)
    finally:
        shutil.rmtree(work, ignore_errors=True)
