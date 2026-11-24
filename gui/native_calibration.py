"""Native strict 100-check pre-optimisation audit. Stop before Pass 1."""
from __future__ import annotations
import copy
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import shutil
import subprocess
import tempfile
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "src/frontend"
CLI = FRONTEND / "tests/solver/v5Solve.js"
AUDITOR = FRONTEND / "tests/solver/auditSavedStrict.js"
BUILD = FRONTEND / "tests/solver/native/build"
PAIR_BUDGETS = (10000, 20000)
SEEDS = tuple(range(1, 51))
TOTAL = 100


class Cancelled(Exception):
    pass


def prereqs():
    if not shutil.which("node"):
        raise RuntimeError("Node.js is required for native V5 calibration.")
    files = [CLI, AUDITOR, BUILD / "v5native.node",
             BUILD / "libv5decode.so", BUILD / "libv5route.so",
             FRONTEND / "tests/solver/out/components/stripboard/autoLayout5.js"]
    for path in files:
        if not path.is_file():
            raise RuntimeError(f"Missing native calibration dependency: {path}")


def parse_json(output):
    for line in reversed(output.splitlines()):
        if line.startswith("{"):
            try:
                return json.loads(line)
            except ValueError:
                pass
    return None


def execute(cmd, env, cancelled):
    if cancelled():
        raise Cancelled()
    p = subprocess.Popen(cmd, cwd=FRONTEND, env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        while True:
            try:
                out, err = p.communicate(timeout=0.3)
                return p.returncode, out, err
            except subprocess.TimeoutExpired:
                if cancelled():
                    p.terminate()
                    try:
                        p.communicate(timeout=3)
                    except subprocess.TimeoutExpired:
                        p.kill()
                        p.communicate()
                    raise Cancelled()
    finally:
        if p.poll() is None:
            p.kill()
            p.communicate()


def trial(project, moves, seed, scratch, cancelled):
    if cancelled():
        raise Cancelled()
    job = scratch / f"{moves}_{seed}"
    inp = job / "input/projects/1.json"
    inp.parent.mkdir(parents=True)
    inp.write_text(json.dumps(project), encoding="utf-8")
    saved = job / "candidate.json"
    env = os.environ.copy()
    env["V5_NATIVE_LIB_DIR"] = str(BUILD)
    env.pop("V5_NATIVE_ROUTE_LIB_DIR", None)
    env["STRIPBOARD_TIMING"] = "1"
    cmd = ["node", str(CLI), "--data", str(job / "input"), "--id", "1",
           "--seed", str(seed), "--moves", str(moves), "--native", "1",
           "--strict", "1", "--drilled", "0", "--nostack", "0",
           "--drill-domain", "0", "--wire-polish", "0",
           "--routing-preference", "wires", "--save", str(saved)]
    start = perf_counter()
    code, out, err = execute(cmd, env, cancelled)
    result = parse_json(out)
    if code not in (0, 2) or not isinstance(result, dict):
        raise RuntimeError(f"Native solver failed at {moves}/{seed} ({code}): {err[-350:]}")
    if (result.get("strictValid") is True) != (code == 0):
        raise RuntimeError(f"Inconsistent native strict verdict at {moves}/{seed}")
    record = dict(moves=moves, seed=seed, seconds=round(perf_counter()-start, 3),
                  valid=False, wires=result.get("wires"), cuts=result.get("cuts"),
                  wireLength=None)
    if code == 0:
        if not saved.is_file():
            raise RuntimeError(f"Strict PASS missing saved board at {moves}/{seed}")
        solved = json.loads(saved.read_text(encoding="utf-8"))
        before, after = project["board"], solved["board"]
        for key in ("rows", "cols", "lockedRows", "lockedCols"):
            if before.get(key) != after.get(key):
                raise RuntimeError(f"Native probe changed board {key}")
        for c in project.get("components", []):
            if c.get("locked") and isinstance(c.get("boardPos"), dict):
                match = next((x for x in solved.get("components", [])
                              if x.get("id") == c.get("id")), None)
                if match is None or match.get("boardPos") != c.get("boardPos"):
                    raise RuntimeError(f"Native probe moved locked part {c.get('id')}")
        acode, aout, aerr = execute(
            ["node", str(AUDITOR), str(saved), str(inp)], env, cancelled)
        audited = parse_json(aout)
        if acode not in (0, 2) or not isinstance(audited, dict):
            raise RuntimeError(f"Independent audit failed: {aerr[-350:]}")
        if acode != 0 or audited.get("valid") is not True:
            raise RuntimeError(f"Native PASS failed independent audit: {audited.get('failures', [])[:3]}")
        if (audited.get("wires"), audited.get("cuts")) != (record["wires"], record["cuts"]):
            raise RuntimeError("Native and independent audit counts differ")
        record["valid"] = True
        record["wireLength"] = audited.get("wireLength")
    return record


def summarise(rows):
    good = [x for x in rows if x["valid"]]
    best = min(good, key=lambda x: (
        x["wires"], x["cuts"],
        x["wireLength"] if isinstance(x["wireLength"], (int, float)) else float("inf")
    )) if good else None
    return {"checked": len(rows), "passed": len(good),
            "best": {k: best[k] for k in ("seed", "wires", "cuts", "wireLength")}
                    if best else None}


def calibrate(project, workers, callback, cancelled):
    if workers not in (3, 4):
        raise ValueError("Workers must be 3 or 4")
    prereqs()
    snapshot = copy.deepcopy(project)
    with tempfile.TemporaryDirectory(prefix="stripboard_calibration_") as td:
        scratch = Path(td)
        trials = {moves: [] for moves in PAIR_BUDGETS}
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(trial, snapshot, m, seed, scratch, cancelled)
                       for seed in SEEDS for m in PAIR_BUDGETS]
            try:
                for future in as_completed(futures):
                    if cancelled():
                        raise Cancelled()
                    row = future.result()
                    trials[row["moves"]].append(row)
                    done = sum(len(v) for v in trials.values())
                    callback({"stage": "CALIBRATION", "done": done, "last": row,
                              "passes": {m: sum(x["valid"] for x in v)
                                         for m, v in trials.items()}})
            except BaseException:
                for future in futures:
                    future.cancel()
                raise
    reports = {m: summarise(v) for m, v in trials.items()}
    return {"reports": reports, "workers": workers,
            "seeds": len(SEEDS), "checks": TOTAL}
