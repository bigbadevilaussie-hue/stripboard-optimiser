#!/usr/bin/env python3
"""AUDIOEX PASS 1 only: seeds 1..2000, 25k moves, preserve ALL strict boards; rank top 20 by quality and wires.

Uses the unchanged native ladder run_one() and independent saved-layout audit.
All rejected candidate JSONs and per-seed logs are deleted
after verification. Stores small results.csv/jsonl and manifest for provenance.
Run from repository root: python3 scripts/run_audioex_pass1_lossless.py --jobs 4
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from scripts import run_audioex_native_ladder as core

MOVES=25_000
SEEDS=tuple(range(1,2001))
FIELDS=("seed","moves","strictPass","wires","cuts","wireLength","price",
        "quality","conflicts","incomplete","nonvertical","crossings",
        "firstFeasibleMove","strictFailures","auditFailures","errors",
        "layoutSig","elapsedWallMs","quality100","wireLengthMm")
SCHEMA="audioex-pass1-lossless-2000-25k/v1"

def score_quality(board):
    import math
    wires=board["board"]["wires"]
    cuts=board["board"]["cuts"]
    length=sum(math.hypot(w["from"]["row"]-w["to"]["row"],w["from"]["col"]-w["to"]["col"]) for w in wires)*2.54
    misplaced=sum(not isinstance(x.get("boardPos"),dict) for x in board.get("components",[]) if not (x.get("offBoard") or x.get("boardExcluded")))
    diagonals=sum(w["from"]["col"]!=w["to"]["col"] for w in wires)
    return round(max(0.,100.-15*misplaced-10*diagonals-.4*len(cuts)-.6*len(wires)-.02*length),2),round(length,2)

def compact(row):
    return {k:row.get(k) for k in FIELDS}

def publish(out,rows):
    # Strict-passing layouts remain preserved in qualified_all, even after demotion.
    eligible=core.rank_passes(rows)
    winner_rows=sorted(eligible,key=lambda r:(-r["quality100"],r["wires"],r["cuts"],r["wireLengthMm"],r["seed"]))[:20]
    wanted={r["seed"] for r in winner_rows}
    champions=out/"top20"
    champions.mkdir(parents=True,exist_ok=True)
    # Candidate files are stored by their immutable seed, even if rank changes.
    for file in champions.glob("seed_*.json"):
        if int(file.stem.split("_")[1]) not in wanted:
            file.unlink()
    # Rebuild ranked view from permanent verified copies. A previously
    # unranked qualifier can enter the top20 after a later result changes
    # deduplication/ranking; never depend on its transient job folder.
    for r in winner_rows:
        filename=f"seed_{r['seed']:04d}_W{r['wires']}_C{r['cuts']}.json"
        permanent=out/"qualified_all"/filename
        ranked=champions/filename
        if not permanent.is_file():
            raise RuntimeError(f"Missing qualified layout: {permanent}")
        if not ranked.is_file():
            shutil.copy2(permanent,ranked)
    with (out/"results.csv").open("w",newline="",encoding="utf8") as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS)
        writer.writeheader()
        for r in sorted(rows,key=lambda r:r["seed"]):
            value=compact(r)
            for field in ("strictFailures","auditFailures","errors"):
                value[field]=json.dumps(value.get(field) or [],ensure_ascii=False)
            writer.writerow(value)
    with (out/"results.jsonl").open("w",encoding="utf8") as f:
        for r in sorted(rows,key=lambda r:r["seed"]):
            f.write(json.dumps(compact(r),ensure_ascii=False,sort_keys=True)+"\n")
    with (out/"top20.txt").open("w",encoding="utf8") as f:
        for rank,r in enumerate(winner_rows,1):
            f.write(f"{rank}. seed {r['seed']} | {r['wires']}W/{r['cuts']}C | "+
                    f"top20/seed_{r['seed']:04d}_W{r['wires']}_C{r['cuts']}.json\n")
    return winner_rows

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs",type=int,default=4)
    parser.add_argument("--timeout",type=int,default=1800)
    parser.add_argument("--out",type=Path,
        default=Path.home()/"Documents"/"Stripboard-Experiment-Archive"/"audioex_pass1_2000_25k_lossless")
    parser.add_argument("--resume",action="store_true")
    args=parser.parse_args()
    if args.jobs<1 or args.timeout<1:
        parser.error("jobs and timeout must be positive")
    out=args.out.expanduser().resolve()
    if out==ROOT or ROOT in out.parents:
        parser.error("Output directory must be outside the repository")
    prerequisites=(core.SOURCE,core.CLI,core.AUDITOR,
                   core.EDGE_DECODE,core.NATIVE_ROUTE,
                   core.NATIVE_ADDON,core.SOLVER_JS)
    for file in prerequisites:
        if not file.is_file():
            parser.error(f"Missing built prerequisite {file}")
    original=core.SOURCE.read_bytes()
    prepared=core.prepare_audioex(json.loads(original))
    identity={
        "schema":SCHEMA,
        "moves":MOVES,"seeds":list(SEEDS),
        "sourceSha256":core.digest(original),
        "preparedSha256":core.digest(core.json_bytes(prepared)),
        "nativeArtifacts":{str(p.relative_to(ROOT)):core.digest(p.read_bytes())
                           for p in prerequisites[1:]},
        "strict":True,"drilledOnly":False,"stackingAllowed":True,
        "wirePolish":False,"ranking":"quality100,wires,cuts,length",
    }
    manifest=out/"manifest.json"
    if args.resume:
        if not manifest.is_file() or json.loads(manifest.read_text()).get("identity")!=identity:
            parser.error("Cannot resume: manifest, fixture, flags, or compiled binaries changed")
        records=out/"results.jsonl"
        if not records.is_file():
            parser.error("Cannot resume without results.jsonl")
        rows=[json.loads(line) for line in records.read_text().splitlines() if line.strip()]
        ids=[r["seed"] for r in rows]
        if len(set(ids))!=len(ids) or not set(ids).issubset(SEEDS):
            parser.error("Invalid or duplicate seed checkpoint")
        expected=sorted(core.rank_passes(rows),key=lambda r:(-r["quality100"],r["wires"],r["cuts"],r["wireLengthMm"],r["seed"]))[:20]
        for r in rows:
            if not r.get("strictPass"): continue
            p=out/"qualified_all"/f"seed_{r['seed']:04d}_W{r['wires']}_C{r['cuts']}.json"
            if not p.is_file() or core.signature(json.loads(p.read_text()))!=r["layoutSig"]:
                parser.error("Missing/changed qualified board; cannot safely resume")
        for r in expected:
            p=out/"top20"/f"seed_{r['seed']:04d}_W{r['wires']}_C{r['cuts']}.json"
            if not p.is_file() or core.signature(json.loads(p.read_text()))!=r["layoutSig"]:
                parser.error("Missing/changed top-twenty board; cannot safely resume")
    else:
        if out.exists() and any(out.iterdir()):
            parser.error("Output folder nonempty: select new --out or use --resume")
        out.mkdir(parents=True,exist_ok=True)
        rows=[]
        git=subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,capture_output=True,
                           text=True,check=True).stdout.strip()
        core.write_json(manifest,{"identity":identity,"gitCommit":git,
                                 "createdUTC":datetime.now(timezone.utc).isoformat()})
        publish(out,rows)
    seen={r["seed"] for r in rows}
    remaining=[s for s in SEEDS if s not in seen]
    print("🔋 AUDIOEX | 24×56 LOCKED | BMS -2,24 | SLIDE OFF",flush=True)
    print("🔪 DRILL OFF | 🧵 STACK ON | 🛡️ STRICT + SAVED AUDIT",flush=True)
    print(f"🎲 seeds 1–2000 | 25k | ⚙️ {args.jobs} workers | "+
          "💾 PRESERVE EVERY STRICT PASS | 🏆 TOP 20 BY QUALITY",flush=True)
    print(f"📁 {out} | {len(remaining)} remaining | PASS 1 ONLY; NO PASS 2",flush=True)
    # Every worker has its own temporary job folder. Only the main thread
    # deletes results; no files are removed while their worker is running.
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures={pool.submit(core.run_one,out,prepared,MOVES,s,args.timeout):s
                 for s in remaining}
        for future in as_completed(futures):
            seed=futures[future]
            try:
                row=future.result()
            except Exception as exc:
                row={"moves":MOVES,"seed":seed,"strictPass":False,
                     "errors":["WORKER_EXCEPTION: "+repr(exc)]}
            # Every strict pass is retained permanently, not only the top twenty.
            saved=out/row["savedJson"] if row.get("savedJson") else None
            if row.get("strictPass"):
                if saved and saved.is_file():
                    board=json.loads(saved.read_text(encoding="utf8"))
                    row["quality100"],row["wireLengthMm"]=score_quality(board)
                    target=out/"qualified_all"/f"seed_{seed:04d}_W{row['wires']}_C{row['cuts']}.json"
                    target.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(saved,target)
                else:
                    row["strictPass"]=False
                    row.setdefault("errors",[]).append("QUALIFIED_BOARD_MISSING")
            proposed=sorted(core.rank_passes(rows+[row]),
                key=lambda r:(-r["quality100"],r["wires"],r["cuts"],r["wireLengthMm"],r["seed"]))[:20]
            qualifies=bool(row.get("strictPass")) and any(r["seed"]==seed for r in proposed)
            if qualifies:
                target=out/"top20"/f"seed_{seed:04d}_W{row['wires']}_C{row['cuts']}.json"
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(out/"qualified_all"/target.name,target)
            # Remove all generated candidate boards/logs, including rejects.
            job=out/"jobs"/f"moves_{MOVES:06d}_seed_{seed:03d}"
            if job.is_dir():
                shutil.rmtree(job)
            if saved and saved.is_file():
                saved.unlink()
            rows.append(compact(row))
            ranks=publish(out,rows)
            winner=ranks[0] if ranks else None
            best=f"{winner['wires']}W/{winner['cuts']}C" if winner else "none"
            topmark=" 🏆 TOP20" if qualifies and row.get("strictPass") else ""
            if row.get("strictPass"):
                print(f"✅ PASS seed {seed:04d} ({len(rows)}/2000) | "+
                      f"{row.get('wires','?')}W/{row.get('cuts','?')}C"+
                      f"{topmark} | best {best}",flush=True)
    # No failed boards or full job folders should survive.
    for folder in ("jobs","passed","rejected"):
        p=out/folder
        if p.exists():
            shutil.rmtree(p)
    if core.SOURCE.read_bytes()!=original:
        raise RuntimeError("Original fixture changed during run")
    ranks=publish(out,rows)
    print(f"🏁 DONE: {len(rows)} trials | "+
          f"{sum(r.get('strictPass') is True for r in rows)} strict passes | "+
          f"{len(ranks)} distinct top boards",flush=True)
    print(f"🏆 {out/'top20'} | 💾 ALL PASSES {out/'qualified_all'} | 🛑 STOPPED BEFORE PASS 2",flush=True)

if __name__=="__main__":
    main()
