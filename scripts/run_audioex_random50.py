#!/usr/bin/env python3
"""Original AUDIOEX reproducible 50-seed run (4 workers, 50k moves).

Uses the standard native ladder and saved-board independent audit.
For deep diagnostics use scripts/run_audioex_debug50.py instead.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from scripts import run_audioex_native_ladder as core
from scripts.run_audioex_debug50 import SEEDS, MOVES

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path,
        default=Path.home()/"Desktop"/"audioex_random50_git")
    p.add_argument("--jobs",type=int,default=4)
    p.add_argument("--timeout",type=int,default=1800)
    p.add_argument("--resume",action="store_true")
    a=p.parse_args()
    if a.jobs<1 or a.timeout<1:p.error("positive jobs and timeout required")
    out=a.out.expanduser().resolve()
    if out==ROOT or ROOT in out.parents:p.error("Output cannot be inside repo")
    needed=[core.SOURCE,core.CLI,core.AUDITOR,core.EDGE_DECODE,
            core.NATIVE_ROUTE,core.NATIVE_ADDON,core.SOLVER_JS]
    for f in needed:
        if not f.is_file():p.error(f"Missing build dependency: {f}")
    source=core.SOURCE.read_bytes()
    prepared=core.prepare_audioex(json.loads(source))
    identity={"schema":"audioex-random50-git/v1","moves":MOVES,"seeds":list(SEEDS),
              "sourceSha256":core.digest(source),
              "preparedSha256":core.digest(core.json_bytes(prepared)),
              "buildSha256":{str(f.relative_to(ROOT)):core.digest(f.read_bytes())
                             for f in needed[1:]},
              "strict":True,"drilled":False,"stacking":True}
    manifest=out/"manifest.json"
    if a.resume:
        if not manifest.is_file() or json.loads(manifest.read_text())["identity"]!=identity:
            p.error("Resume refused: settings/source/build changed")
    else:
        if out.exists() and any(out.iterdir()):
            p.error("Output folder nonempty; use --resume or another --out")
        out.mkdir(parents=True,exist_ok=True)
        (out/"prepared_audioex.json").write_bytes(core.json_bytes(prepared))
        shutil.copy2(core.SOURCE,out/"original_audioex.json")
        (out/"selected_seeds.txt").write_text("\n".join(map(str,SEEDS))+"\n")
        commit=subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,
                              capture_output=True,text=True,check=True).stdout.strip()
        core.write_json(manifest,{"identity":identity,
            "gitCommit":commit,"createdUTC":datetime.now(timezone.utc).isoformat()})
    rows=core.read_checkpoint(out,(MOVES,),SEEDS)
    seen={r["seed"] for r in rows}
    print(f"🔋 AUDIOEX | {len(SEEDS)} seeds | 50k | {a.jobs} workers | {len(rows)} done",flush=True)
    core.publish(out,rows,(MOVES,),SEEDS)
    with ThreadPoolExecutor(max_workers=a.jobs) as pool:
        futs={pool.submit(core.run_one,out,prepared,MOVES,s,a.timeout):s
              for s in SEEDS if s not in seen}
        for fut in as_completed(futs):
            seed=futs[fut]
            try:r=fut.result()
            except Exception as e:r={"moves":MOVES,"seed":seed,"strictPass":False,
                                     "exit":127,"errors":["WORKER_EXCEPTION "+repr(e)]}
            if r.get("savedJson"):
                src=out/r["savedJson"]
                kind="passed" if r.get("strictPass") else "rejected"
                fmt=lambda v:str(v) if isinstance(v,int) else "NA"
                dst=out/kind/f"seed_{seed:04d}_W{fmt(r.get('wires'))}_C{fmt(r.get('cuts'))}.json"
                src.replace(dst)
                r["savedJson"]=str(dst.relative_to(out))
                r["savedSha256"]=core.digest(dst.read_bytes())
            core.append_checkpoint(out,r)
            rows.append(r)
            summary=core.publish(out,rows,(MOVES,),SEEDS)
            print(f"{'✅ PASS' if r.get('strictPass') else '❌ REJECT'} seed {seed:04d} | "+
                  f"{r.get('wires','?')}W/{r.get('cuts','?')}C | "+
                  f"{summary['strictPasses']}/{len(rows)} passes",flush=True)
    if core.SOURCE.read_bytes()!=source:raise RuntimeError("Source changed during run")
    print("🏁 DONE",out/"results.csv",out/"top5")

if __name__=="__main__":
    main()
