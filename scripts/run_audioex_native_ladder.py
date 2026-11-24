#!/usr/bin/env python3
"""AUDIOEX locked BMS edge-mount native ladder; no GUI or Python solver.

270 independent trials by default: 10 seeds each at 5k..50k (step 5k),
then 100k..500k (step 25k). Strict CLI plus independent saved-board audit
qualifies every survivor. Keep ALL passed boards, rejected candidates, top 5,
stdout/stderr, checkpoints and exact source/binary provenance. Resume safely.

Usage from repository root:
  python3 scripts/run_audioex_native_ladder.py --jobs 4
  python3 scripts/run_audioex_native_ladder.py --jobs 4 --resume

This intentionally does not edit or overwrite the Git fixture.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "src" / "frontend"
SOURCE = ROOT / "test-fixtures/masters/audio/audioex.json"
CLI = FRONTEND / "tests/solver/v5Solve.js"
AUDITOR = FRONTEND / "tests/solver/auditSavedStrict.js"
EDGE_DECODE = FRONTEND / "tests/solver/native/build/edge/libv5decode.so"
NATIVE_ROUTE = FRONTEND / "tests/solver/native/build/libv5route.so"
NATIVE_ADDON = FRONTEND / "tests/solver/native/build/v5native.node"
SOLVER_JS = FRONTEND / "tests/solver/out/components/stripboard/autoLayout5.js"
DEFAULT_OUT = Path.home() / "Desktop/audioex_bms_fixed_native_ladder"
BUDGETS = tuple(range(5_000, 50_001, 5_000)) + tuple(range(100_000, 500_001, 25_000))
BMS_LABEL = "BMS"
BMS_POS = {"row": -2, "col": 24}
SCHEMA = "audioex-native-fixed-bms-ladder/v1"
FIELDS = ("moves", "seed", "strictPass", "cliValid", "auditValid", "exit",
          "wires", "cuts", "wireLength", "price", "knife", "stacked",
          "nonvertical", "crossings", "conflicts", "incomplete", "geometry",
          "quality", "unsolvedReason", "firstFeasibleMove", "firstFeasibleMs",
          "elapsedWallMs", "solveMs",
          "strictFailures", "auditFailures", "auditWarnings", "errors",
          "savedJson", "savedSha256", "layoutSig")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf8")


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_bytes(json_bytes(value))
    temp.replace(path)


def bms_info(data: dict) -> tuple[dict, dict]:
    matches = [c for c in data.get("components", []) if c.get("label") == BMS_LABEL]
    if len(matches) != 1:
        raise ValueError("Exactly one BMS component is required")
    bms = matches[0]
    defs = [d for d in data.get("componentDefs", []) if d.get("id") == bms.get("defId")]
    if len(defs) != 1:
        raise ValueError("BMS custom footprint definition missing or ambiguous")
    return bms, defs[0]


def prepare_audioex(data: dict) -> dict:
    """Preserve exactly this locked BMS anchor, allow its BODY overhang only."""
    source = json.loads(json.dumps(data))
    board = source.get("board", {})
    if (board.get("rows"), board.get("cols"),
        board.get("lockedRows"), board.get("lockedCols")) != (24, 56, True, True):
        raise ValueError("AUDIOEX master must already be locked 24x56 on both axes")
    bms, definition = bms_info(source)
    if bms.get("boardPos") != BMS_POS or bms.get("rotation", 0) != 0 or bms.get("locked") is not True:
        raise ValueError("BMS must be locked at row -2, col 24, rotation 0")
    if bms.get("slide") is True:
        raise ValueError("AUDIOEX source requests Slide; refuse to override a sliding BMS")
    if definition.get("width") != 7 or definition.get("height") != 12:
        raise ValueError("Unexpected BMS footprint dimensions; revalidate case geometry")
    if not definition.get("pins"):
        raise ValueError("BMS footprint has no electrical pins")
    for pin in definition["pins"]:
        row = BMS_POS["row"] + pin["offsetRow"]
        col = BMS_POS["col"] + pin["offsetCol"]
        if not (0 <= row < 24 and 0 <= col < 56):
            raise ValueError("BMS electrical pin off physical board: " + str(pin.get("name")))
    if any(c is not bms and c.get("locked") and c.get("boardPos")
           for c in source.get("components", [])):
        raise ValueError("Unexpected second locked placed part; review fixture")
    # The edge decoder is opt-in only when edge=true. Fix the exact original
    # case anchor; NEVER enumerate Slide columns.
    bms["edge"] = True
    bms["slide"] = False
    # CLI v5Solve.js always clears input cuts/wires (blankBoard). Match that
    # behavior explicitly. The source JSON and its 4 manual cuts stay intact.
    board["cuts"] = []
    board["wires"] = []
    return source


def signature(saved: dict) -> str:
    """Content identity of board geometry, independent of UUIDs for wires."""
    parts = sorted(
        (str(c.get("id")), json.dumps(c.get("boardPos"), sort_keys=True),
         c.get("rotation", 0), json.dumps(c.get("flexibleEndPos"), sort_keys=True))
        for c in saved.get("components", [])
    )
    board = saved["board"]
    cuts = sorted((c["row"], c["col"], c.get("kind", "between"))
                  for c in board.get("cuts", []))
    wires = sorted(tuple(sorted(((w["from"]["row"], w["from"]["col"]),
                                  (w["to"]["row"], w["to"]["col"]))))
                   for w in board.get("wires", []))
    return digest(json.dumps([parts, cuts, wires],
                             sort_keys=True, separators=(",", ":")).encode())


def rank_key(row: dict):
    def numeric(name):
        value = row.get(name)
        return value if isinstance(value, (int, float)) and not isinstance(value, bool) else float("inf")
    return (numeric("wires"), numeric("cuts"), numeric("wireLength"),
            numeric("price"), row.get("moves", 0), row.get("seed", 0))


def rank_passes(rows: list[dict]) -> list[dict]:
    eligible = sorted((x for x in rows if x.get("strictPass") is True), key=rank_key)
    distinct, signatures = [], set()
    for entry in eligible:
        key = entry.get("layoutSig") or entry.get("savedSha256")
        if key in signatures:
            continue
        signatures.add(key)
        distinct.append(entry)
    return distinct


def last_json(stdout: str) -> dict | None:
    for line in reversed(stdout.splitlines()):
        if line.startswith("{"):
            try:
                result = json.loads(line)
                if isinstance(result, dict):
                    return result
            except ValueError:
                continue
    return None


def run_one(folder: Path, prepared: dict, moves: int, seed: int,
            timeout: int) -> dict:
    """Each worker owns one disjoint folder; never touches fixture or peers."""
    tag = f"moves_{moves:06d}_seed_{seed:03d}"
    job = folder / "jobs" / tag
    inp = job / "input/projects/1.json"
    write_json(inp, prepared)
    candidate = job / "candidate.json"
    stdout_path, stderr_path = job / "stdout.log", job / "stderr.log"
    command = ["node", str(CLI), "--data", str(job / "input"),
               "--id", "1", "--seed", str(seed), "--moves", str(moves),
               "--native", "1", "--strict", "1", "--drilled", "0",
               "--nostack", "0", "--drill-domain", "0", "--wire-polish", "0",
               "--routing-preference", "wires", "--save", str(candidate)]
    env = os.environ.copy()
    env["V5_NATIVE_LIB_DIR"] = str(EDGE_DECODE.parent)
    env.pop("V5_NATIVE_ROUTE_LIB_DIR", None)
    env["STRIPBOARD_TIMING"] = "1"
    start = time.perf_counter()
    try:
        proc = subprocess.run(command, cwd=FRONTEND, env=env, capture_output=True,
                              text=True, timeout=timeout)
        stdout, stderr, code = proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or b""
        stderr = exc.stderr or b""
        stdout = stdout.decode("utf8", "replace") if isinstance(stdout, bytes) else stdout
        stderr = stderr.decode("utf8", "replace") if isinstance(stderr, bytes) else stderr
        code, stderr = 124, stderr + f"\nTIMEOUT after {timeout}s\n"
    except OSError as exc:
        stdout, stderr, code = "", repr(exc), 127
    elapsed = round((time.perf_counter() - start) * 1000, 2)
    stdout_path.write_text(stdout, encoding="utf8")
    stderr_path.write_text(stderr, encoding="utf8")
    result = last_json(stdout) or {}
    timing = next((last_json(line[7:]) for line in reversed(stderr.splitlines())
                   if line.startswith("timing ")), None) or {}
    record = {"moves": moves, "seed": seed, "strictPass": False,
              "cliValid": result.get("strictValid") is True, "auditValid": False,
              "exit": code, "elapsedWallMs": elapsed, "solveMs": timing.get("solveMs"),
              "errors": [], "strictFailures": result.get("strictFailures") or [],
              "auditFailures": [], "auditWarnings": [],
              "unsolvedReason": result.get("unsolvedReason"),
              "firstFeasibleMove": result.get("firstFeasibleMove"),
              "firstFeasibleMs": result.get("firstFeasibleMs"),
              "command": command,
              "stdoutLog": str(stdout_path.relative_to(folder)),
              "stderrLog": str(stderr_path.relative_to(folder)),
              "preparedInput": str(inp.relative_to(folder))}
    for src, dst in [("wires","wires"),("cuts","cuts"),("knife","knife"),
                     ("stacked","stacked"),("diagonalsActual","nonvertical"),
                     ("crossings","crossings"),("conflicts","conflicts"),
                     ("incomplete","incomplete"),("geo","geometry"),
                     ("quality","quality"),("price","price")]:
        record[dst] = result.get(src)
    if code not in (0, 2):
        record["errors"].append("CLI_EXIT_" + str(code))
    if not result:
        record["errors"].append("CLI_JSON_MISSING")
    if result and result.get("strictValid") is not (code == 0):
        record["errors"].append("CLI_STRICT_EXIT_MISMATCH")
    if not candidate.exists():
        record["errors"].append("SAVED_JSON_MISSING")
    else:
        try:
            saved = json.loads(candidate.read_text(encoding="utf8"))
            sbms, _ = bms_info(saved)
            bms, _ = bms_info(prepared)
            if (sbms.get("boardPos") != BMS_POS or sbms.get("rotation",0) != 0 or
                sbms.get("locked") is not True or sbms.get("edge") is not True or
                sbms.get("slide") is not False or
                sbms.get("id") != bms.get("id")):
                record["errors"].append("BMS_CASE_ANCHOR_CHANGED")
            if (saved.get("board", {}).get("rows"), saved.get("board", {}).get("cols"),
                saved.get("board", {}).get("lockedRows"),
                saved.get("board", {}).get("lockedCols")) != (24, 56, True, True):
                record["errors"].append("LOCKED_BOARD_CHANGED")
            audit = subprocess.run(
                ["node", str(AUDITOR), str(candidate), str(inp)],
                cwd=FRONTEND, capture_output=True, text=True, timeout=120)
            (job / "audit.stdout.log").write_text(audit.stdout, encoding="utf8")
            (job / "audit.stderr.log").write_text(audit.stderr, encoding="utf8")
            audited = last_json(audit.stdout)
            if audit.returncode not in (0, 2) or not audited:
                record["errors"].append("INDEPENDENT_AUDIT_ERROR_" + str(audit.returncode))
            else:
                record["auditFailures"] = audited.get("failures", [])
                record["auditWarnings"] = audited.get("warnings", [])
                record["auditValid"] = (audited.get("valid") is True and audit.returncode == 0)
                if audited.get("valid") is not (audit.returncode == 0):
                    record["errors"].append("AUDIT_EXIT_VERDICT_MISMATCH")
                if audited.get("wires") != record["wires"] or audited.get("cuts") != record["cuts"]:
                    record["errors"].append("CLI_AUDIT_COUNT_MISMATCH")
                record["wireLength"] = audited.get("wireLength")
            record["layoutSig"] = signature(saved)
        except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
            record["errors"].append("VERIFY_EXCEPTION: " + str(exc))
        # Retain *every* candidate (even failures); do not throw away evidence.
        target = folder / ("passed" if (code == 0 and record["cliValid"] and
                          record["auditValid"] and not record["errors"]) else "rejected") / (tag + ".json")
        target.parent.mkdir(parents=True, exist_ok=True)
        candidate.replace(target)
        record["savedJson"] = str(target.relative_to(folder))
        record["savedSha256"] = digest(target.read_bytes())
    record["strictPass"] = bool(code == 0 and record["cliValid"] and
                                record["auditValid"] and not record["errors"])
    return record


def read_checkpoint(folder: Path, moves: tuple[int, ...], seeds: tuple[int, ...]) -> list[dict]:
    path = folder / "results.jsonl"
    rows, seen = [], set()
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf8").splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        key = (entry["moves"], entry["seed"])
        if key in seen or key[0] not in moves or key[1] not in seeds:
            raise ValueError("Duplicate/incompatible checkpoint row: " + str(key))
        seen.add(key)
        if entry.get("savedJson"):
            f = folder / entry["savedJson"]
            if not f.is_file() or digest(f.read_bytes()) != entry.get("savedSha256"):
                raise ValueError("Saved-board checksum missing or changed: " + str(f))
        rows.append(entry)
    return rows


def append_checkpoint(folder: Path, row: dict) -> None:
    with (folder / "results.jsonl").open("a", encoding="utf8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def publish(folder: Path, entries: list[dict], moves: tuple[int, ...],
            seeds: tuple[int, ...]) -> dict:
    top = rank_passes(entries)
    passed = [x for x in entries if x.get("strictPass")]
    summary = {
        "finished": len(entries), "total": len(moves) * len(seeds),
        "strictPasses": len(passed), "distinctPassed": len(top),
        "rejected": len(entries) - len(passed),
        "failureCounts": dict(Counter(
            error for row in entries if not row.get("strictPass")
            for error in (row.get("strictFailures") or row.get("auditFailures") or
                          row.get("errors") or ["NOT_STRICT"]))),
        "top5": top[:5], "champion": top[0] if top else None,
        "byBudget": [
            {"moves": b, "completed": sum(x["moves"] == b for x in entries),
             "passed": sum(x["moves"] == b and x.get("strictPass") for x in entries)}
            for b in moves],
    }
    write_json(folder / "summary.json", summary)
    with (folder / "results.csv").open("w", newline="", encoding="utf8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in sorted(entries, key=lambda x: (x["moves"], x["seed"])):
            value = dict(row)
            for name in ("strictFailures", "auditFailures", "auditWarnings", "errors"):
                value[name] = json.dumps(value.get(name, []), ensure_ascii=False)
            writer.writerow(value)
    with (folder / "passed_index.jsonl").open("w", encoding="utf8") as f:
        for row in sorted(passed, key=rank_key):
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    topdir = folder / "top5"
    topdir.mkdir(parents=True, exist_ok=True)
    for old in topdir.glob("rank_*.json"):
        old.unlink()
    for i, row in enumerate(top[:5], 1):
        shutil.copy2(folder / row["savedJson"], topdir /
                     f"rank_{i:02d}_{row['moves']//1000}k_seed{row['seed']:02d}_W{row['wires']}_C{row['cuts']}.json")
    champion = folder / "champion.json"
    if top:
        shutil.copy2(folder / top[0]["savedJson"], champion)
    elif champion.is_file():
        champion.unlink()
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--seeds", type=int, default=10, help="1..N independent seeds per budget")
    parser.add_argument("--seed-start", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=1800, help="seconds per native solve")
    parser.add_argument("--resume", action="store_true", help="continue exact archived configuration")
    parser.add_argument("--moves", type=str, default=None,
                        help="optional small smoke: comma-separated positive increasing move counts")
    args = parser.parse_args(argv)
    if min(args.jobs, args.seeds, args.seed_start, args.timeout) <= 0:
        parser.error("--jobs, --seeds, --seed-start and --timeout must be positive")
    if args.moves is None:
        moves = BUDGETS
    else:
        try:
            moves = tuple(int(n.strip()) for n in args.moves.split(","))
        except ValueError:
            parser.error("--moves must be comma-separated positive integers")
        if not moves or any(n <= 0 for n in moves) or tuple(sorted(set(moves))) != moves:
            parser.error("--moves must be strictly increasing positive integers")
    seeds = tuple(range(args.seed_start, args.seed_start + args.seeds))
    for needed in (SOURCE, CLI, AUDITOR, EDGE_DECODE, NATIVE_ROUTE, NATIVE_ADDON, SOLVER_JS):
        if not needed.is_file():
            parser.error(f"Missing prerequisite: {needed}. Run npm run build:solver, build:native and build:native:edge.")
    src_bytes = SOURCE.read_bytes()
    prepared = prepare_audioex(json.loads(src_bytes))
    prepared_bytes = json_bytes(prepared)
    out = args.out.expanduser().resolve()
    if out == ROOT or ROOT in out.parents:
        parser.error("Refusing to store hundreds of outputs inside source repository")
    manifest_file = out / "manifest.json"
    hashes = {str(p.relative_to(ROOT)): digest(p.read_bytes())
              for p in (CLI, AUDITOR, EDGE_DECODE, NATIVE_ROUTE, NATIVE_ADDON, SOLVER_JS)}
    identity = {"schema": SCHEMA, "sourceSha256": digest(src_bytes),
                "preparedSha256": digest(prepared_bytes),
                "bms": {"row": -2, "col": 24, "locked": True, "edge": True, "slide": False},
                "rows": 24, "cols": 56, "lockedRows": True, "lockedCols": True,
                "drilled": False, "stackingAllowed": True, "strict": True,
                "wirePolish": False, "routingPreference": "wires",
                "budgets": list(moves), "seeds": list(seeds), "binarySha256": hashes}
    if args.resume:
        if not manifest_file.is_file():
            parser.error("Cannot resume without original manifest.json")
        old = json.loads(manifest_file.read_text(encoding="utf8"))
        if old.get("identity") != identity:
            parser.error("Resume refused: source/settings/binaries changed")
        if (out / "input/projects/1.json").read_bytes() != prepared_bytes:
            parser.error("Resume refused: prepared input snapshot changed")
    else:
        if out.exists() and any(out.iterdir()):
            parser.error("Output folder exists and is nonempty: use --resume or another --out")
        out.mkdir(parents=True, exist_ok=True)
        main_input = out / "input/projects/1.json"
        main_input.parent.mkdir(parents=True, exist_ok=True)
        main_input.write_bytes(prepared_bytes)
        shutil.copy2(SOURCE, out / "original_audioex.json")
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                capture_output=True, text=True, check=True).stdout.strip()
        write_json(manifest_file, {
            "createdUTC": datetime.now(timezone.utc).isoformat(),
            "gitCommit": commit, "identity": identity,
            "originalSource": str(SOURCE),
            "masterFourCuts": True,
            "note": "Native CLI blanks source cuts/wires; source preserved separately. Body-only BMS overhang allowed.",
        })
    rows = read_checkpoint(out, moves, seeds)
    seen = {(x["moves"], x["seed"]) for x in rows}
    summary = publish(out, rows, moves, seeds)
    print(f"🔋 AUDIOEX | BMS EDGE FIXED row -2 col 24 | Slide OFF | 24×56 locked", flush=True)
    print("🔪 DRILL OFF | 🧵 STACK ON | 🛡️ native strict + saved-board audit", flush=True)
    print(f"🏁 {len(moves)} budgets × {len(seeds)} seeds = {len(moves)*len(seeds)} trials | workers {args.jobs}", flush=True)
    print(f"💾 All passed + rejected + top 5 | 📁 {out}", flush=True)
    print(f"📌 Resuming {len(rows)} completed attempts" if rows else "🚀 Fresh run", flush=True)
    for moves_count in moves:
        remaining = [seed for seed in seeds if (moves_count, seed) not in seen]
        if not remaining:
            print(f"⏭️ {moves_count//1000}k complete", flush=True)
            continue
        print(f"\n🔁 {moves_count//1000}k | {len(remaining)} seeds remaining", flush=True)
        with ThreadPoolExecutor(max_workers=args.jobs) as executor:
            futures = {executor.submit(run_one, out, prepared, moves_count, seed, args.timeout): seed
                       for seed in remaining}
            for future in as_completed(futures):
                seed = futures[future]
                try:
                    row = future.result()
                except Exception as error:
                    # A worker crash must be recorded and cannot become a pass.
                    row = {"moves": moves_count, "seed": seed, "strictPass": False,
                           "exit": 127, "errors": ["WORKER_EXCEPTION: " + repr(error)]}
                append_checkpoint(out, row)
                rows.append(row)
                seen.add((moves_count, seed))
                summary = publish(out, rows, moves, seeds)
                status = "✅ PASS" if row.get("strictPass") else ("🛑 NO FIT" if row.get("unsolvedReason") else "❌ REJECT")
                champion = summary.get("champion")
                best = f"{champion['wires']}W/{champion['cuts']}C" if champion else "none"
                first = row.get("firstFeasibleMove")
                fit = f"fit@{first}" if first is not None else "fit@none"
                why = row.get("unsolvedReason") or (
                    "STRICT_PASS" if row.get("strictPass") else
                    "STRICT_OR_AUDIT_REJECT")
                print(f"{status} {moves_count//1000}k seed {seed:02d} | "
                      f"{row.get('wires','?')}W/{row.get('cuts','?')}C | "
                      f"{fit} | {why} | best {best} "
                      f"| pass {summary['strictPasses']}/{summary['finished']} "
                      f"| ⏱ {row.get('elapsedWallMs',0)/1000:.2f}s", flush=True)
                if not row.get("strictPass"):
                    reason = row.get("strictFailures") or row.get("auditFailures") or row.get("errors") or []
                    if reason:
                        print("  ↳ " + ", ".join(map(str, reason[:5]))[:200], flush=True)
        rung = next(x for x in summary["byBudget"] if x["moves"] == moves_count)
        print(f"🏁 {moves_count//1000}k completed | ✅ {rung['passed']}/{rung['completed']} | 🏆 top five current", flush=True)
    if SOURCE.read_bytes() != src_bytes:
        raise RuntimeError("Source AUDIOEX changed during ladder; results require review")
    print(f"\n🏆 DONE: {summary['strictPasses']} strict/audited passes / {summary['total']} trials", flush=True)
    print(f"💾 All passing JSONs: {out/'passed'}")
    print(f"🏆 Top five: {out/'top5'}")
    print(f"📊 Results: {out/'results.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
