"""Native V5 100-point decoder-speed measurement. No optimisation solves."""
from __future__ import annotations
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "src/frontend"
CLI = FRONTEND / "tests/solver/v5Solve.js"
NATIVE = FRONTEND / "tests/solver/native/build"
POINTS = 100


class Cancelled(Exception):
    pass


def prerequisites():
    if not shutil.which("node"):
        raise RuntimeError("Node.js is required for the native decoder probe.")
    for item in (
        CLI, NATIVE / "v5native.node", NATIVE / "libv5decode.so",
        NATIVE / "libv5route.so",
        FRONTEND / "tests/solver/out/components/stripboard/autoLayout5.js",
    ):
        if not item.is_file():
            raise RuntimeError(f"Missing native probe dependency: {item}")


def run_process(command, env, cancelled):
    if cancelled():
        raise Cancelled()
    process = subprocess.Popen(
        command, cwd=FRONTEND, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        while True:
            try:
                stdout, stderr = process.communicate(timeout=0.25)
                return process.returncode, stdout, stderr
            except subprocess.TimeoutExpired:
                if cancelled():
                    process.terminate()
                    try:
                        process.communicate(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.communicate()
                    raise Cancelled()
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate()


def calibrate(project, workers, drilled_only, stacking_allowed, progress, diagnostic, cancelled):
    """Use native --speedprobe 100 once, without annealing or board routing.

    Cut policy changes decoder constraints. Stacking is a future router/finish
    constraint, not measurable with this decoder-only instrument.
    """
    if workers not in (3, 4):
        raise ValueError("CPU probe must select 3 or 4 workers first.")
    if type(drilled_only) is not bool or type(stacking_allowed) is not bool:
        raise ValueError("Cuts and stacking selections must be Boolean.")
    prerequisites()
    prepared = copy.deepcopy(project)
    board = prepared.get("board")
    if (not isinstance(board, dict)
        or type(board.get("rows")) is not int or board["rows"] <= 0
        or type(board.get("cols")) is not int or board["cols"] <= 0):
        raise ValueError("The selected physical board must have positive dimensions.")
    board["lockedRows"] = True
    board["lockedCols"] = True
    payload = json.dumps(prepared, ensure_ascii=False, sort_keys=True).encode("utf-8")
    sha = hashlib.sha256(payload).hexdigest()
    parts = prepared.get("components", [])
    anchors = [p for p in parts if p.get("locked") and isinstance(p.get("boardPos"), dict)]
    diagnostic(f"[MOVE100][INPUT] sha256={sha}; actual={board['rows']}x{board['cols']}; "
               f"physical_lock=True/True; preferred={board.get('wantedRows')} "
               f"({board.get('wantedRowsMode')}) x {board.get('wantedCols')} "
               f"({board.get('wantedColsMode')})")
    diagnostic(f"[MOVE100][INPUT] components={len(parts)} nets={len(prepared.get('nets', []))} "
               f"assignments={len(prepared.get('netAssignments', []))} anchors={len(anchors)}")
    for p in anchors:
        diagnostic(f"[MOVE100][LOCK] {p.get('label') or p.get('id')}: "
                   f"boardPos={p['boardPos']} edge={p.get('edge')} slide={p.get('slide')} "
                   f"rotation={p.get('rotation', 0)}")
    diagnostic(f"[MOVE100][POLICY] drilled_only={drilled_only} "
               f"knife_allowed={not drilled_only} stacking_allowed={stacking_allowed} "
               f"future_workers={workers}")
    diagnostic("[MOVE100][NOTE] Drill-domain changes decoder constraints; stacking affects "
               "the router, which this 100-decoder speed probe does NOT exercise.")
    with tempfile.TemporaryDirectory(prefix="stripboard_move100_") as scratch:
        path = Path(scratch) / "projects/1.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        command = [
            "node", str(CLI), "--data", scratch, "--id", "1",
            "--native", "1", "--speedprobe", str(POINTS),
            "--drilled", "1" if drilled_only else "0",
            "--drill-domain", "1" if drilled_only else "0",
            "--nostack", "0" if stacking_allowed else "1",
            "--routing-preference", "wires",
        ]
        env = os.environ.copy()
        env["V5_NATIVE_LIB_DIR"] = str(NATIVE)
        env.pop("V5_NATIVE_ROUTE_LIB_DIR", None)
        env["STRIPBOARD_TIMING"] = "1"
        diagnostic("[MOVE100][COMMAND] " + " ".join(command))
        diagnostic(f"[MOVE100][ENV] V5_NATIVE_LIB_DIR={NATIVE}; STRIPBOARD_TIMING=1")
        progress({"phase": "running", "completed": 0})
        started = perf_counter()
        code, stdout, stderr = run_process(command, env, cancelled)
        elapsed = perf_counter() - started
        diagnostic(f"[MOVE100][EXIT] code={code}; wall={elapsed:.3f}s")
        for line in stderr.splitlines():
            diagnostic("[MOVE100][stderr] " + line)
        for line in stdout.splitlines():
            diagnostic("[MOVE100][stdout] " + line)
        if code != 0:
            cause = None
            for line in reversed(stdout.splitlines()):
                if line.lstrip().startswith("{"):
                    try:
                        parsed = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(parsed, dict) and parsed.get("error"):
                        cause = str(parsed["error"])
                        break
            if cause:
                diagnostic(f"[MOVE100][REJECTED INPUT] {cause}")
                raise RuntimeError(
                    f"Native decoder rejected constraints: {cause} "
                    f"(exit {code}; see Activity)"
                )
            raise RuntimeError(
                f"Native decoder probe exited {code}. See Activity diagnostics."
            )
        matches = re.findall(r"(?m)^probeMs\s+([0-9]+(?:\.[0-9]+)?)\s*$", stderr)
        if len(matches) != 1:
            raise RuntimeError("No unique probeMs timing was emitted. See Activity.")
        ms = float(matches[0])
        if not math.isfinite(ms) or ms <= 0:
            raise RuntimeError(f"Native decoder returned invalid probeMs {ms}")
    speed = 1000.0 / ms
    diagnostic(f"[MOVE100][RESULT] {POINTS} random genome decodes, "
               f"mean={ms:.6f} ms/decode, {speed:,.2f} decodes/s.")
    diagnostic("[MOVE100][CAVEAT] Decoder throughput is NOT optimiser move throughput; "
               "no quality-optimal move budget or full runtime is inferred.")
    diagnostic("[MOVE100][STOP] 0 solve attempts; no placement, routing or final electrical audit.")
    progress({"phase": "done", "completed": POINTS})
    return {"points": POINTS, "ms_per_decode": ms, "decodes_per_second": speed,
            "seconds": elapsed, "drilled_only": drilled_only,
            "stacking_allowed": stacking_allowed, "workers": workers}
