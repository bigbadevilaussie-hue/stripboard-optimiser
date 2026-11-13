"""Adapter from the desktop worker to the repository's v5 Node harness."""

import json
import os
import shutil
import subprocess
import threading
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
FRONTEND = Path(
    os.environ.get("STRIPBOARD_FRONTEND_DIR", REPO_ROOT / "src" / "frontend")
).expanduser().resolve()
HARNESS = FRONTEND / "tests" / "solver" / "v5Solve.js"
SOLVER_OUT = FRONTEND / "tests" / "solver" / "out"


def _check_solver_files(native=False):
    if not FRONTEND.is_dir():
        raise FileNotFoundError(
            f"Frontend directory not found: {FRONTEND}. "
            "Set STRIPBOARD_FRONTEND_DIR to the repository's src/frontend directory."
        )
    if not HARNESS.is_file():
        raise FileNotFoundError(f"v5 solver harness not found: {HARNESS}")

    required = [
        SOLVER_OUT / "components" / "stripboard" / "autoLayout5.js",
        FRONTEND / "components" / "stripboard" / "v5wasm" / "v5decode.wasm",
        FRONTEND / "components" / "stripboard" / "v5wasm" / "v5route.wasm",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        details = "\n".join(f"  - {path}" for path in missing)
        raise FileNotFoundError(
            "The compiled v5 solver or its WASM modules are missing:\n"
            f"{details}\n"
            "Build the solver output from src/frontend before starting optimisation."
        )

    if native:
        native_dir = FRONTEND / "tests" / "solver" / "native" / "build"
        native_files = [
            native_dir / "v5native.node",
            native_dir / "libv5decode.so",
            native_dir / "libv5route.so",
        ]
        missing_native = [str(path) for path in native_files if not path.is_file()]
        if missing_native:
            raise FileNotFoundError(
                "The optional native solver build is incomplete:\n"
                + "\n".join(f"  - {path}" for path in missing_native)
            )


def solve_one(
    project_json,
    seed,
    work,
    node="node",
    effort=1.0,
    native=False,
    drilled=False,
    on_log=None,
    on_progress=None,
    register_process=None,
    unregister_process=None,
):
    """Run one deterministic seed and return (summary, saved_project_path)."""
    _check_solver_files(native=native)

    project_json = Path(project_json).expanduser().resolve()
    if not project_json.is_file():
        raise FileNotFoundError(f"Solver input JSON not found: {project_json}")

    work = Path(work).expanduser().resolve()
    job = work / f"s{seed}_e{effort:g}"
    projects = job / "projects"
    projects.mkdir(parents=True, exist_ok=True)

    input_copy = projects / "1.json"
    shutil.copy2(project_json, input_copy)
    save_file = job / "solved.json"

    command = [
        node,
        str(HARNESS),
        "--data",
        str(job),
        "--id",
        "1",
        "--seed",
        str(seed),
        "--effort",
        str(effort),
        "--save",
        str(save_file),
        "--progress",
        "1",
    ]
    if native:
        command.extend(["--native", "1"])
    if drilled:
        command.extend(["--drilled", "1"])

    proc = subprocess.Popen(
        command,
        cwd=str(FRONTEND),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    if register_process:
        register_process(proc)

    stderr_errors = []

    def pump_stderr():
        try:
            for raw_line in proc.stderr:
                line = raw_line.strip()
                if not line:
                    continue
                if line.startswith("progress "):
                    fields = line.split()
                    try:
                        fraction = float(fields[1])
                    except (IndexError, ValueError):
                        if on_log:
                            on_log(f"[seed {seed}] Unrecognised progress: {line}")
                        continue
                    if on_progress:
                        on_progress(seed, fraction)
                elif on_log:
                    on_log(f"[seed {seed}] {line}")
        except Exception as exc:
            stderr_errors.append(exc)

    stderr_thread = threading.Thread(
        target=pump_stderr,
        name=f"solver-stderr-{seed}",
        daemon=True,
    )
    stderr_thread.start()
    try:
        stdout_text = proc.stdout.read()
        return_code = proc.wait()
        stderr_thread.join()
    finally:
        if unregister_process:
            unregister_process(proc)
        if proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass

    if stderr_errors:
        raise RuntimeError(f"Could not read solver output: {stderr_errors[0]}")

    for line in reversed(stdout_text.strip().splitlines()):
        try:
            result = json.loads(line)
        except ValueError:
            continue
        if isinstance(result, dict):
            if result.get("error"):
                raise RuntimeError(result["error"])
            if "rows" not in result or "cols" not in result:
                raise RuntimeError(f"Solver returned an incomplete summary: {result}")
            if not save_file.is_file():
                raise RuntimeError("Solver returned a summary but did not save the solved project.")
            return result, save_file

    raise RuntimeError(
        f"Solver produced no JSON summary (exit code {return_code}); "
        "the process may have been stopped or crashed."
    )


def is_valid(summary):
    """Apply the solver harness's independent geometry/electrical result flags."""
    return (
        summary.get("conflicts") == 0
        and summary.get("incomplete") == 0
        and summary.get("geo") == 0
        and not summary.get("issues")
    )


def rank_key(summary):
    """Lower price, then fewer wires and cuts, wins the desktop's current policy."""
    return (
        summary.get("price", summary.get("rate", 1e9)),
        summary.get("wires", 1e9),
        summary.get("cuts", 1e9),
    )
