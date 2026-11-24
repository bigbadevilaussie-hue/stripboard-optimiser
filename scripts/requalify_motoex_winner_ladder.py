#!/usr/bin/env python3
"""Requalify saved ladder boards WITHOUT solving again or editing old archives.

The old polisher added "N wires still run on top..." even when stacking was
permitted. Candidates rejected ONLY for that stale message are eligible for
a fresh independent board-level audit. Every other failure is disqualifying.
Writes new requalified/ results and copies of the verified best boards; never
changes original JSONs, results.jsonl, summary.json or original champion.json.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

from run_motoex_native_edge_slide import FRONTEND, contract
from run_motoex_native_sweep import key_of, physical_layout_signature, write_json
from run_motoex_winner_ladder import DEFAULT_OUT, SEED, COLUMN

AUDITOR = FRONTEND / "tests" / "solver" / "auditSavedStrict.js"
STACK_ONLY = re.compile(r"^(\d+) wires? still run on top of another wire$")


def stack_only_reason(record: dict) -> int | None:
    """Counts exactly one allowed-stack issue and NO other old strict failure."""
    if record.get("strictFailures") != ["SOLVER_ISSUES"]:
        return None
    problems = record.get("diagnostics", {}).get("issues") or []
    if len(problems) != 1 or not isinstance(problems[0], str):
        return None
    m = STACK_ONLY.fullmatch(problems[0])
    if not m:
        return None
    # The old controller may record the expected exit-2 / strict-false errors.
    # Refuse requalification if it also observed any independent contract error.
    expected = {"STRICT_NOT_VALID: SOLVER_ISSUES", "STRICT_EXIT_2"}
    if any(error not in expected for error in (record.get("errors") or [])):
        return None
    return int(m.group(1))


def audit_json(saved: Path, input_json: Path) -> dict:
    proc = subprocess.run(
        ["node", str(AUDITOR), str(saved), str(input_json)],
        cwd=FRONTEND, capture_output=True, text=True, timeout=120,
    )
    if proc.returncode not in (0, 2):
        raise ValueError("Saved-board audit crashed: " + proc.stderr.strip())
    result = json.loads(proc.stdout)
    if result.get("valid") is not (proc.returncode == 0):
        raise ValueError("Saved-board audit exit and result disagree")
    return result


def requalify(archive: Path) -> dict:
    manifest = json.loads((archive / "manifest.json").read_text(encoding="utf8"))
    if manifest.get("seed") != SEED or manifest.get("usb", {}).get("column") != COLUMN:
        raise ValueError("Wrong seed or USB column")
    if manifest.get("stackingAllowed") is not True or manifest.get("drilledOnly") is not False:
        raise ValueError("This audit requires the exact knives-allowed, stacks-allowed ladder policy")
    if manifest.get("strictElectrical") is not True or manifest.get("strictVerticalJumpers") is not True or manifest.get("strictWireBodyCrossings") is not True:
        raise ValueError("Manifest strict policy mismatch")
    current_sha = hashlib.sha256(contract.MASTER.read_bytes()).hexdigest()
    if current_sha != manifest.get("sourceSha256"):
        raise ValueError("Canonical source hash differs; cannot certify archived boards")
    rows = [json.loads(line) for line in
            (archive / "results.jsonl").read_text(encoding="utf8").splitlines() if line.strip()]
    if len(rows) != len({r["moves"] for r in rows}):
        raise ValueError("Duplicate move budget in checkpoint")
    if not rows:
        raise ValueError("No archived candidates")
    root_summary = json.loads((archive / "summary.json").read_text(encoding="utf8"))
    baseline = root_summary.get("baseline")
    if not baseline or not (archive / baseline["savedJson"]).is_file():
        raise ValueError("Missing original baseline")
    prepared_input = archive / rows[0]["input"]
    if not prepared_input.is_file():
        raise ValueError("Archived preflight input missing")
    outcome, qualified = [], []
    candidates = [{"source":"baseline", **baseline},
                  *[{"source":"ladder", **r} for r in rows]]
    for row in candidates:
        move = row.get("moves")
        tag = "baseline" if move is None else str(move // 1000) + "K"
        permitted = row.get("strictPass") is True
        stack_count = None if permitted else stack_only_reason(row)
        if not permitted and stack_count is None:
            continue  # real failures remain failures; do not rerank them
        saved_file = archive / row["savedJson"]
        source_input = prepared_input if move is None else archive / row["input"]
        audit = audit_json(saved_file, source_input)
        record = {
            "source":row["source"], "moves":move, "savedJson":row["savedJson"],
            "previouslyStrict":permitted, "stackOnlyIssue":stack_count,
            "audit":audit,
        }
        if (row.get("wires") != audit.get("wires") or
            row.get("cuts") != audit.get("cuts")):
            audit["valid"] = False
            audit["failures"].append("RECORDED_WIRE_OR_CUT_COUNT_MISMATCH")
        if stack_count is not None and audit.get("stacked") != stack_count:
            audit["valid"] = False
            audit["failures"].append("STACKED_COUNT_MISMATCH")
        record["qualified"] = audit["valid"]
        outcome.append(record)
        if audit["valid"]:
            q = dict(row)
            q["strictPass"] = True
            q["requalifiedFromOldStackIssue"] = not permitted
            q["wireLength"] = audit["wireLength"]
            q["layoutSig"] = physical_layout_signature(
                json.loads(saved_file.read_text(encoding="utf8")))
            qualified.append(q)
            icon = "🏆" if not permitted else "✅"
            print(f"{icon} VERIFIED {tag}: {audit['wires']}W/{audit['cuts']}C "
                  f"| {audit['stacked']} allowed stacks | "
                  f"{len(audit['warnings'])} body warnings", flush=True)
        else:
            print(f"❌ REJECT {tag}: " + ", ".join(audit["failures"][:6]), flush=True)
    qualified.sort(key=lambda r: key_of(r, "wires"))
    distinct, seen = [], set()
    for q in qualified:
        if q["layoutSig"] not in seen:
            distinct.append(q)
            seen.add(q["layoutSig"])
    out = archive / "requalified"
    out.mkdir(exist_ok=True)
    top = out / "top5"
    top.mkdir(exist_ok=True)
    for old in top.glob("rank_*.json"):
        old.unlink()
    for i,q in enumerate(distinct[:5],1):
        shutil.copy2(archive / q["savedJson"], top /
            f"rank_{i:02d}_moves_{q.get('moves') or 'baseline'}_W{q['wires']}_C{q['cuts']}.json")
    champion = distinct[0] if distinct else None
    if champion:
        shutil.copy2(archive / champion["savedJson"], out / "champion.json")
    report = {
        "auditUTC":datetime.now(timezone.utc).isoformat(),
        "source":"original ladder archive, unchanged",
        "originalSummary":str(archive/"summary.json"),
        "qualifyingCandidates":len(qualified),
        "recoveredFromStackOnlyIssue":sum(q.get("requalifiedFromOldStackIssue",False) for q in qualified),
        "distinctQualifiers":len(distinct),
        "champion":champion,
        "top5":distinct[:5],
        "audits":outcome,
        "rejectedCandidatesNotReclassified":len(candidates)-len(outcome),
    }
    write_json(out / "summary.json",report)
    if champion:
        print(f"🏆 VERIFIED CHAMPION: {champion['wires']}W/{champion['cuts']}C "
              f"at {champion.get('moves') or 'baseline'} moves | {out/'champion.json'}", flush=True)
    else:
        print("🛑 NO VERIFIED CANDIDATE — inspect audit results", flush=True)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,default=DEFAULT_OUT)
    args=parser.parse_args()
    try:
        requalify(args.out.expanduser().resolve())
        return 0
    except (OSError,ValueError,KeyError,subprocess.TimeoutExpired) as error:
        print("🛑 REQUALIFICATION ERROR: "+str(error),file=sys.stderr)
        return 64


if __name__=="__main__":
    sys.exit(main())
