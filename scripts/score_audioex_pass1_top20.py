#!/usr/bin/env python3
"""Audit and score retained AUDIOEX Pass 1 finalists; no Pass 2 is launched.

Revalidates each saved JSON with the native saved-board auditor, calculates the
historical Route-Mate 100-point heuristic, and exports a comparison against
wire-first ranking. Read-only regarding source candidate layouts.
"""
from __future__ import annotations
import argparse
import csv
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import run_audioex_native_ladder as core

PITCH_MM=2.54
FIELDS=("seed","strictPass","wires","cuts","wireLengthMm","unplaced","nonvertical",
        "auditValid","quality100","penaltyWires","penaltyCuts","penaltyWireLength",
        "penaltyDiagonals","penaltyUnplaced","penaltyInvalid","auditFailures","file")

def compute(board):
    comps=[c for c in board["components"]
           if not (c.get("offBoard") or c.get("boardExcluded"))]
    missing=sum(not isinstance(c.get("boardPos"),dict) for c in comps)
    wires=board["board"]["wires"]
    length=sum(math.hypot(w["from"]["row"]-w["to"]["row"],
                          w["from"]["col"]-w["to"]["col"]) for w in wires)*PITCH_MM
    nonvertical=sum(w["from"]["col"]!=w["to"]["col"] for w in wires)
    cuts=len(board["board"]["cuts"])
    # Route-Mate render_quality.py: 100 - 15 missing - 10 diagonal
    # - 0.4 cuts - 0.6 wires - 0.02 length mm.
    # Additional 20pt invalid-record penalty only when auditor flags it;
    # NEVER interpret the provisional score as physical validity.
    quality=max(0.,100.0-15*missing-10*nonvertical-.4*cuts-.6*len(wires)-.02*length)
    return dict(wires=len(wires),cuts=cuts,wireLengthMm=round(length,2),
                unplaced=missing,nonvertical=nonvertical,quality100=round(quality,2),
                penaltyWires=round(.6*len(wires),3),
                penaltyCuts=round(.4*cuts,3),
                penaltyWireLength=round(.02*length,3),
                penaltyDiagonals=round(10*nonvertical,3),
                penaltyUnplaced=round(15*missing,3),
                penaltyInvalid=0.0)

def last_json(text):
    for line in reversed(text.strip().splitlines()):
        try:
            value=json.loads(line)
            if isinstance(value,dict): return value
        except ValueError: pass
    return None

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out",type=Path,
        default=Path.home()/"Desktop"/"audioex_pass1_2000_25k_top20")
    args=ap.parse_args()
    out=args.out.expanduser().resolve()
    index=out/"results.jsonl"
    if not index.is_file():
        ap.error("Pass 1 results.jsonl not found")
    rows=[json.loads(x) for x in index.read_text().splitlines() if x.strip()]
    expected=core.rank_passes(rows)[:20]
    candidate_files=sorted((out/"top20").glob("seed_*.json"))
    if len(candidate_files)!=len(expected):
        ap.error(f"Missing finalist boards: found {len(candidate_files)}; expected {len(expected)}")
    prepared=core.prepare_audioex(json.loads(core.SOURCE.read_text(encoding="utf8")))
    manifest=json.loads((out/"manifest.json").read_text())
    if manifest["identity"]["preparedSha256"]!=core.digest(core.json_bytes(prepared)):
        ap.error("Fixture changed since sweep; cannot revalidate")
    results=[]
    with tempfile.TemporaryDirectory(prefix="audioex_quality_") as td:
        inp=Path(td)/"input.json"
        core.write_json(inp,prepared)
        for r in expected:
            filename=f"seed_{r['seed']:04d}_W{r['wires']}_C{r['cuts']}.json"
            file=out/"top20"/filename
            if not file.is_file(): ap.error(f"Finalist missing: {filename}")
            board=json.loads(file.read_text(encoding="utf8"))
            if core.signature(board)!=r.get("layoutSig"):
                ap.error(f"Finalist signature mismatch: {filename}")
            report=compute(board)
            proc=subprocess.run(["node",str(core.AUDITOR),str(file),str(inp)],
                                cwd=core.FRONTEND,capture_output=True,text=True,timeout=120)
            audit=last_json(proc.stdout) or {}
            report.update(seed=r["seed"],strictPass=r.get("strictPass"),
                          auditValid=proc.returncode==0 and audit.get("valid") is True,
                          auditFailures=(audit.get("failures",[]) if (proc.returncode==0 and audit.get("valid") is True)
                                         else audit.get("failures") or [f"AUDIT_EXIT_{proc.returncode}: {proc.stderr.strip()}"]),
                          file=filename)
            if report["wires"]!=r["wires"] or report["cuts"]!=r["cuts"]:
                ap.error(f"Saved counts differ from Pass 1: {filename}")
            results.append(report)
    # Hard gate: never qualify a result without current verified audit.
    if not all(x["strictPass"] and x["auditValid"] and not x["auditFailures"]
               for x in results):
        error=out/"QUALITY_AUDIT_FAILURE.json"
        core.write_json(error,results)
        ap.error(f"At least one finalist failed saved-board audit; see {error}")
    by_quality=sorted(results,key=lambda x:(-x["quality100"],x["wires"],x["cuts"],x["wireLengthMm"],x["seed"]))
    by_wires=sorted(results,key=lambda x:(x["wires"],x["cuts"],x["wireLengthMm"],x["seed"]))
    with (out/"quality100_top20.csv").open("w",newline="",encoding="utf8") as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS)
        writer.writeheader()
        for row in by_quality:
            writer.writerow({**row,"auditFailures":json.dumps(row["auditFailures"])})
    core.write_json(out/"quality100_top20.json",{
        "formula":"max(0,100 - 15*unplaced - 10*nonvertical - 0.4*cuts - 0.6*wires - 0.02*wireLengthMm)",
        "provisional":True,"hardGate":"saved-board auditor PASS",
        "historicalInvalidWirePenalty": "not included because every candidate must independently pass strict audit",
        "qualityRank":[x["seed"] for x in by_quality],
        "wireFirstRank":[x["seed"] for x in by_wires],
        "results":by_quality,
        "note":"Only retained top20 available; previously pruned valid candidates cannot be rescored without regeneration."
    })
    for pos,r in enumerate(by_quality,1):
        print(f"🏆 QUALITY {pos:02d} seed {r['seed']:04d} | {r['quality100']:.2f}/100 | "
              f"{r['wires']}W/{r['cuts']}C | {r['wireLengthMm']:.1f} mm | "
              f"penalties W -{r['penaltyWires']:.2f}, C -{r['penaltyCuts']:.2f}, "
              f"L -{r['penaltyWireLength']:.2f}, diagonal -{r['penaltyDiagonals']:.2f}, "
              f"unplaced -{r['penaltyUnplaced']:.2f}, invalid -{r['penaltyInvalid']:.2f}",flush=True)
    print(f"🛡️ {len(results)} audited finalists | 🛑 NO PASS 2",flush=True)

if __name__=="__main__":
    main()
