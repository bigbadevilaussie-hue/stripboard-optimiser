#!/usr/bin/env python3
"""Native V5 discovery with auditable candidate policies and lossless resumes.

This is a CONTROLLER, not another layout engine. A native CLI exit=2 can
still produce a promising saved board. Only saved-board audit qualification
can admit an experimental candidate to the shortlist.
"""
import argparse
import csv
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gui.native_calibration import CLI, FRONTEND, prerequisites, decoder_directory  # noqa: E402
from gui.quality import construction_metrics  # noqa: E402

AUDITOR = FRONTEND / "tests/solver/auditSavedStrict.js"
POLICIES = ("strict", "diagonal", "crossings", "archive")
PASS_STATUSES = ("STRICT_PASS", "DIAG_PASS", "ROUTE_CANDIDATE")
FIELDS = [
    "seed", "moves", "status", "native_strict", "audit_strict",
    "q3", "wires", "cuts", "stack", "wire_length_mm",
    "diagonals", "body_crossings", "electrical_complete",
    "native_exit", "audit_exit", "native_failures", "native_issues",
    "audit_failures", "candidate_gz", "native_json", "audit_json",
    "solve_wall_s", "audit_wall_s", "wall_s", "completed_utc",
]


def last_json(text):
    for line in reversed(text.splitlines()):
        try:
            parsed = json.loads(line)
        except (ValueError, TypeError):
            continue
        if isinstance(parsed, dict):
            return parsed
    return {}


def json_cell(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def winner_rank(row):
    return (
        float(row["q3"]),
        -int(row["wires"]),
        -int(row["cuts"]),
        -int(row["seed"]),
    )


def source_fingerprint(prepared):
    payload = json.dumps(prepared, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def process_seed(seed, args, prepared_path, native_dir, out):
    row = {field: "" for field in FIELDS}
    row.update(seed=f"{seed:04d}", moves=args.moves, status="ERROR")
    start = time.perf_counter()

    with tempfile.TemporaryDirectory(prefix=f"candidate_{seed:04d}_") as tmp:
        job = Path(tmp)
        inp = job / "input/projects/1.json"
        inp.parent.mkdir(parents=True)
        shutil.copy2(prepared_path, inp)
        candidate_file = job / "saved.json"

        env = os.environ.copy()
        env["V5_NATIVE_LIB_DIR"] = str(native_dir)
        env.pop("V5_NATIVE_ROUTE_LIB_DIR", None)
        env["STRIPBOARD_TIMING"] = "1"

        cmd = [
            "node", str(CLI), "--data", str(job / "input"), "--id", "1",
            "--seed", str(seed), "--moves", str(args.moves),
            "--native", "1", "--strict", "1", "--candidate-policy", args.policy,
            "--drilled", "1" if args.drilled else "0",
            "--drill-domain", "1" if args.drilled else "0",
            "--nostack", "1" if args.no_stack else "0",
            "--wire-polish", "0", "--routing-preference", args.routing,
            "--save", str(candidate_file),
        ]
        try:
            start_solve = time.perf_counter()
            native_proc = subprocess.run(
                cmd, cwd=FRONTEND, env=env, capture_output=True, text=True
            )
            row["solve_wall_s"] = f"{time.perf_counter() - start_solve:.3f}"
            row["native_exit"] = native_proc.returncode
            native = last_json(native_proc.stdout)
            row["native_json"] = json_cell(native)
            row["native_strict"] = native.get("strictValid", "")
            row["native_failures"] = json_cell(native.get("strictFailures", []))
            row["native_issues"] = json_cell(native.get("issues", []))

            # Archive every candidate, including rejected/incomplete boards.
            if candidate_file.is_file():
                archive_rel = f"candidates/seed_{seed:04d}.json.gz"
                archive = out / archive_rel
                archive.parent.mkdir(parents=True, exist_ok=True)
                temporary = archive.with_name(archive.name + ".tmp")
                with candidate_file.open("rb") as source, gzip.open(
                    temporary, "wb", compresslevel=5
                ) as dest:
                    shutil.copyfileobj(source, dest)
                os.replace(temporary, archive)
                row["candidate_gz"] = archive_rel

            if native_proc.returncode not in (0, 2) or not native:
                row["status"] = "ERROR_NATIVE"
            elif not candidate_file.is_file():
                row["status"] = "FAIL_NO_BOARD" if native_proc.returncode == 2 else "ERROR_NO_BOARD"
            else:
                start_audit = time.perf_counter()
                audit_proc = subprocess.run(
                    [
                        "node", str(AUDITOR), str(candidate_file), str(inp),
                        "--candidate-policy", args.policy,
                    ],
                    cwd=FRONTEND, env=env, capture_output=True, text=True
                )
                row["audit_wall_s"] = f"{time.perf_counter() - start_audit:.3f}"
                row["audit_exit"] = audit_proc.returncode
                audit = last_json(audit_proc.stdout)
                row["audit_json"] = json_cell(audit)
                row["audit_failures"] = json_cell(audit.get("failures", []))
                choice = audit.get("candidate") or {}
                row["audit_strict"] = audit.get("valid", "")
                row["diagonals"] = choice.get("diagonals", "")
                row["body_crossings"] = choice.get("bodyCrossings", "")
                row["electrical_complete"] = choice.get("electricalComplete", "")

                if audit_proc.returncode not in (0, 2) or not choice:
                    row["status"] = "ERROR_AUDIT"
                elif not isinstance(choice.get("qualified"), bool):
                    row["status"] = "ERROR_AUDIT"
                elif (choice["qualified"]) != (audit_proc.returncode == 0):
                    row["status"] = "ERROR_AUDIT_MISMATCH"
                elif (native.get("strictValid") is True) != (native_proc.returncode == 0):
                    row["status"] = "ERROR_NATIVE_MISMATCH"
                elif (audit.get("valid") is True) != (native.get("strictValid") is True):
                    # Native vs audited strict disagreement is diagnostic;
                    # never accidentally award a strict WR.
                    if audit.get("valid") is True:
                        row["status"] = "ERROR_STRICT_DISAGREEMENT"
                    elif choice["qualified"]:
                        row["status"] = choice["status"]
                    else:
                        row["status"] = "FAIL"
                elif choice["qualified"]:
                    row["status"] = choice["status"]
                else:
                    row["status"] = "FAIL"

                if row["status"] in PASS_STATUSES:
                    saved = json.loads(candidate_file.read_text(encoding="utf-8"))
                    score = construction_metrics(saved)
                    row.update(
                        q3=f'{score["q"]:.2f}',
                        wires=score["w"],
                        cuts=score["cut"],
                        stack=score["s"],
                        wire_length_mm=score["wire_length_mm"],
                    )
                    if (int(row["wires"]) != audit.get("wires")
                            or int(row["cuts"]) != audit.get("cuts")):
                        row["status"] = "ERROR_COUNT_DISAGREEMENT"

        except Exception as exc:
            row["status"] = "ERROR_RUNNER"
            row["audit_failures"] = json_cell(
                {"exception": f"{type(exc).__name__}: {exc}"}
            )

    row["wall_s"] = f"{time.perf_counter() - start:.3f}"
    row["completed_utc"] = datetime.now(timezone.utc).isoformat()
    return row


def save_champion(out, row):
    status = row["status"]
    name = {
        "STRICT_PASS": "WR_strict.json",
        "DIAG_PASS": "WR_diagonal_candidate.json",
        "ROUTE_CANDIDATE": "WR_routing_candidate.json",
    }[status]
    archive = out / row["candidate_gz"]
    if not archive.is_file():
        raise FileNotFoundError(f"Missing archived champion: {archive}")
    target = out / name
    temporary = target.with_name(target.name + ".tmp")
    with gzip.open(archive, "rb") as source, temporary.open("wb") as dest:
        shutil.copyfileobj(source, dest)
    os.replace(temporary, target)
    meta = out / (name.removesuffix(".json") + ".metadata.json")
    meta.write_text(json.dumps({
        "seed": row["seed"], "status": status, "q3": row["q3"],
        "wires": row["wires"], "cuts": row["cuts"],
        "diagonals": row["diagonals"],
        "bodyCrossings": row["body_crossings"],
        "buildReady": status == "STRICT_PASS",
        "archive": row["candidate_gz"],
    }, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path,
                        help="Moto prepared or source project JSON")
    parser.add_argument("--out", type=Path, default=None,
                        help="New/resumable output folder; default is Work/candidate_hunt_...")
    parser.add_argument("--policy", choices=POLICIES, default="diagonal")
    parser.add_argument("--seeds", type=int, default=5000)
    parser.add_argument("--first-seed", type=int, default=0)
    parser.add_argument("--moves", type=int, default=10000)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--routing", choices=("wires", "cuts"), default="wires")
    parser.add_argument("--drilled", action="store_true")
    parser.add_argument("--no-stack", action="store_true")
    args = parser.parse_args()
    if args.seeds < 1 or args.first_seed < 0 or args.moves < 1 or args.workers < 1:
        parser.error("--seeds, --moves, --workers must be positive and --first-seed nonnegative")
    prerequisites()
    if not AUDITOR.is_file():
        raise SystemExit(f"Missing saved-board auditor: {AUDITOR}")
    if not args.input.is_file():
        raise SystemExit(f"Missing input: {args.input}")
    out = (args.out or ROOT / "Work" /
           f"candidate_hunt_{args.policy}_{args.seeds}x{args.moves}").resolve()
    prepared = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(prepared.get("board"), dict):
        raise SystemExit("Invalid project: board not found")
    if not prepared["board"].get("rows") or not prepared["board"].get("cols"):
        raise SystemExit("Invalid physical board dimensions")
    prepared["board"]["lockedRows"] = True
    prepared["board"]["lockedCols"] = True
    decoder = decoder_directory(prepared)
    identity = {
        "schema": 1, "input_sha256": source_fingerprint(prepared),
        "policy": args.policy, "first_seed": args.first_seed,
        "seeds": args.seeds, "moves": args.moves, "workers": args.workers,
        "routing": args.routing, "drilled": args.drilled,
        "no_stack": args.no_stack, "decoder": str(decoder),
    }

    out.mkdir(parents=True, exist_ok=True)
    manifest = out / "manifest.json"
    prepared_file = out / "prepared_input.json"
    csv_path = out / "results.csv"
    if manifest.is_file():
        if json.loads(manifest.read_text()) != identity:
            raise SystemExit("Campaign settings differ; choose a fresh --out folder")
        if not prepared_file.is_file() or not csv_path.is_file():
            raise SystemExit("Incomplete campaign metadata; not safe to resume")
    else:
        if any(out.iterdir()):
            raise SystemExit("Output folder is not empty; choose a fresh --out")
        prepared_file.write_text(json.dumps(prepared, indent=2) + "\n")
        manifest.write_text(json.dumps(identity, indent=2) + "\n")

    completed = set()
    best = {}
    if csv_path.is_file():
        with csv_path.open(newline="") as f:
            for row in csv.DictReader(f):
                if not row["status"].startswith("ERROR"):
                    completed.add(int(row["seed"]))
                if row["status"] in PASS_STATUSES:
                    old = best.get(row["status"])
                    if old is None or winner_rank(row) > winner_rank(old):
                        best[row["status"]] = row
    for row in best.values():
        save_champion(out, row)

    remaining = (
        seed for seed in range(args.first_seed, args.first_seed + args.seeds)
        if seed not in completed
    )
    print(f"🦂 Native candidate hunt: {args.seeds:,} seeds × {args.moves:,} moves", flush=True)
    print(f"⚙️ {args.workers} workers | policy={args.policy} | strict final audit unchanged", flush=True)
    print(f"📊 Completed: {len(completed):,}/{args.seeds:,}", flush=True)
    print(f"🔐 Input SHA256: {identity['input_sha256']}", flush=True)
    print(f"💾 Output: {out}", flush=True)

    with csv_path.open("a", newline="", buffering=1) as log:
        writer = csv.DictWriter(log, fieldnames=FIELDS)
        if log.tell() == 0:
            writer.writeheader()
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            active = {}
            n_logged = len(completed)

            def top_up():
                while len(active) < args.workers:
                    try:
                        seed = next(remaining)
                    except StopIteration:
                        return
                    active[pool.submit(process_seed, seed, args, prepared_file, decoder, out)] = seed

            top_up()
            while active:
                ready, _ = wait(active, return_when=FIRST_COMPLETED)
                for future in ready:
                    active.pop(future)
                    row = future.result()
                    writer.writerow(row)
                    log.flush()
                    os.fsync(log.fileno())
                    n_logged += 1
                    status = row["status"]
                    if status in PASS_STATUSES:
                        old = best.get(status)
                        if old is None or winner_rank(row) > winner_rank(old):
                            save_champion(out, row)
                            best[status] = row
                        symbol = {"STRICT_PASS": "🏆", "DIAG_PASS": "🟠",
                                  "ROUTE_CANDIDATE": "🛠️"}[status]
                        print(
                            f'{symbol} [{n_logged}/{args.seeds}] Seed {row["seed"]} '
                            f'{status} Q3={row["q3"]} '
                            f'{row["wires"]}W/{row["cuts"]}C '
                            f'📐 {row["diagonals"]} diagonals, '
                            f'{row["body_crossings"]} body crossings '
                            f'⏱️ {row["wall_s"]}s', flush=True
                        )
                top_up()

    print(f"🏁 Campaign finished; CSV: {csv_path}", flush=True)
    for status, row in best.items():
        print(f'  {status}: seed {row["seed"]}, Q3={row["q3"]}', flush=True)


if __name__ == "__main__":
    main()
