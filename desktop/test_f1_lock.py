"""Lock regression test.

Checks that a solve:
  - preserves a locked flexible part's original endpoints,
  - preserves a locked rigid part's original position and rotation,
  - preserves board dimension locks, if present.

Paths are relative to this test file. Runs from anywhere.

Usage: python3 desktop/test_f1_lock.py [path/to/fixture.json]
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# This file lives at <repo>/desktop/test_f1_lock.py
# Frontend harness: <repo>/src/frontend
# Default fixture: <repo>/test-fixtures/cases/moto/motomix.json
#                  fallback: ~/Desktop/koala/motomix.json
TEST_DIR = Path(__file__).resolve().parent
REPO = TEST_DIR.parent
FRONTEND = REPO / "src/frontend"
DEFAULT_FIXTURES = [
    REPO / "test-fixtures" / "cases" / "moto" / "motomix.json",
    REPO / "test-fixtures" / "masters" / "moto" / "moto.json",
    Path.home() / "Desktop" / "koala" / "motomix.json",
]


def find_part(components, label=None, flexible=None):
    for c in components:
        if label is not None and c.get("label") != label:
            continue
        if flexible is not None:
            has_flex = "flexibleEndPos" in c
            if has_flex != flexible:
                continue
        return c
    return None


def run(fixture: Path) -> int:
    if not fixture.is_file():
        print(f"FAIL: fixture not found: {fixture}")
        return 1
    if not (FRONTEND / "tests" / "solver" / "v5Solve.js").is_file():
        print(f"FAIL: solver harness not found: {FRONTEND / 'tests/solver/v5Solve.js'}")
        return 1

    original = json.loads(fixture.read_text())
    comps_in = original.get("components", [])
    board_in = original.get("board", {})

    # Find a locked flexible part: prefer F1, else first locked flexible
    f1_in = find_part([c for c in comps_in if c.get("locked")], label="F1", flexible=True)
    if f1_in is None:
        f1_in = find_part([c for c in comps_in if c.get("locked")], flexible=True)
    rigid_in = find_part([c for c in comps_in if c.get("locked")], flexible=False)
    locks_in = (board_in.get("lockedRows", False), board_in.get("lockedCols", False))
    dims_in = (board_in.get("rows", 0), board_in.get("cols", 0))

    if f1_in is None:
        print("SKIP: no locked flexible part in fixture — cannot test flex lock")
        f1_in = None
    if rigid_in is None:
        print("SKIP: no locked rigid part in fixture — cannot test rigid lock")
    if f1_in is None and rigid_in is None and locks_in == (False, False):
        print("FAIL: fixture has nothing to test")
        return 1

    if f1_in:
        print("INPUT flexible:", f1_in.get("label"),
              "| boardPos:", f1_in.get("boardPos"),
              "| flexibleEndPos:", f1_in.get("flexibleEndPos"),
              "| locked:", f1_in.get("locked"))
    if rigid_in:
        print("INPUT rigid:", rigid_in.get("label"),
              "| boardPos:", rigid_in.get("boardPos"),
              "| rotation:", rigid_in.get("rotation"),
              "| locked:", rigid_in.get("locked"))
    print("INPUT board: rows=", dims_in[0], "cols=", dims_in[1],
          "| locks:", locks_in)

    work = Path(tempfile.mkdtemp(prefix="locktest_"))
    projects = work / "projects"
    projects.mkdir(parents=True)
    shutil.copy2(fixture, projects / "1.json")
    save = work / "solved.json"

    cmd = [
        "node", str(FRONTEND / "tests" / "solver" / "v5Solve.js"),
        "--data", str(work), "--id", "1",
        "--seed", "0", "--effort", "0.1",
        "--save", str(save),
    ]
    print("\nRunning:", " ".join(cmd))
    r = subprocess.run(cmd, cwd=str(FRONTEND), capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        print("FAIL: solver exited", r.returncode)
        print(r.stdout[-2000:])
        print(r.stderr[-2000:])
        return 1
    if not save.is_file():
        print("FAIL: solver did not save")
        return 1

    solved = json.loads(save.read_text())
    comps_out = solved.get("components", [])
    board_out = solved.get("board", {})
    dims_out = (board_out.get("rows", 0), board_out.get("cols", 0))
    locks_out = (board_out.get("lockedRows", False), board_out.get("lockedCols", False))

    ok = True

    # 1) Flexible lock: coordinates must not move
    if f1_in:
        out = find_part(comps_out, label=f1_in.get("label"))
        if out is None:
            print(f"FAIL: {f1_in.get('label')} missing from output")
            ok = False
        else:
            print("OUTPUT flexible:", out.get("label"),
                  "| boardPos:", out.get("boardPos"),
                  "| flexibleEndPos:", out.get("flexibleEndPos"),
                  "| locked:", out.get("locked"))
            if out.get("boardPos") != f1_in.get("boardPos"):
                print(f"FAIL: {f1_in.get('label')} boardPos moved: {f1_in.get('boardPos')} -> {out.get('boardPos')}")
                ok = False
            if out.get("flexibleEndPos") != f1_in.get("flexibleEndPos"):
                print(f"FAIL: {f1_in.get('label')} flexibleEndPos moved: {f1_in.get('flexibleEndPos')} -> {out.get('flexibleEndPos')}")
                ok = False
            if out.get("locked") is not True:
                print(f"FAIL: {f1_in.get('label')} locked flag lost in output")
                ok = False

    # 2) Rigid lock: position and rotation must not move
    if rigid_in:
        out = find_part(comps_out, label=rigid_in.get("label"))
        if out is None:
            print(f"FAIL: {rigid_in.get('label')} missing from output")
            ok = False
        else:
            print("OUTPUT rigid:", out.get("label"),
                  "| boardPos:", out.get("boardPos"),
                  "| rotation:", out.get("rotation"),
                  "| locked:", out.get("locked"))
            if out.get("boardPos") != rigid_in.get("boardPos"):
                print(f"FAIL: {rigid_in.get('label')} boardPos moved: {rigid_in.get('boardPos')} -> {out.get('boardPos')}")
                ok = False
            if out.get("rotation") != rigid_in.get("rotation"):
                print(f"FAIL: {rigid_in.get('label')} rotation changed: {rigid_in.get('rotation')} -> {out.get('rotation')}")
                ok = False
            if out.get("locked") is not True:
                print(f"FAIL: {rigid_in.get('label')} locked flag lost in output")
                ok = False

    # 3) Board dimension locks: flags preserved in output
    print("OUTPUT board: rows=", dims_out[0], "cols=", dims_out[1],
          "| locks:", locks_out)
    if locks_out != locks_in:
        print(f"FAIL: board lock flags changed: {locks_in} -> {locks_out}")
        ok = False

    # 3b) Board dimension locks: if rows locked, output rows must be <= dims_in[0]
    if locks_in[0] and dims_out[0] > dims_in[0]:
        print(f"FAIL: locked rows violated: input {dims_in[0]}, output {dims_out[0]}")
        ok = False
    if locks_in[1] and dims_out[1] > dims_in[1]:
        print(f"FAIL: locked cols violated: input {dims_in[1]}, output {dims_out[1]}")
        ok = False

    if ok:
        print("\nPASS: all locked parts and board dimensions preserved")
        return 0
    return 1


if __name__ == "__main__":
    if len(sys.argv) > 1:
        fixture = Path(sys.argv[1]).expanduser().resolve()
    else:
        fixture = next((p for p in DEFAULT_FIXTURES if p.is_file()), DEFAULT_FIXTURES[0])
    print(f"Using fixture: {fixture}")
    print(f"Using frontend: {FRONTEND}")
    sys.exit(run(fixture))
