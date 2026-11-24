#!/usr/bin/env python3
"""Forensic rerun of the AUDIOEX 50-seed, 50k-move native experiment.

Uses the original edge-enabled native solver; does not modify solver/fixture.
Run from repo root: python3 scripts/run_audioex_debug50.py --jobs 4
Outputs CSV/JSON, saved boards, CLI stderr/stdout and audit evidence.
"""
from __future__ import annotations
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from scripts import run_audioex_native_ladder as core

SEEDS = (3,8,56,92,119,149,155,156,283,291,334,355,505,514,597,722,870,
         898,928,953,1003,1083,1112,1151,1165,1196,1208,1242,1308,1377,
         1384,1417,1443,1485,1550,1557,1591,1621,1632,1637,1688,1716,
         1798,1801,1816,1857,1930,1931,1951,1999)
MOVES = 50000
FLAGS = ("--native","1","--strict","1","--drilled","0","--nostack","0",
         "--drill-domain","0","--wire-polish","0","--routing-preference","wires",
         "--finish-trace","1","--move-summary","1")
FIELDS = ("seed","moves","strictPass","exit","wires","cuts","cutsMinusWires",
          "firstFeasibleMove","firstFeasibleMs","selectedFinish",
          "repairWires","repairCuts","repairCompliant","repairFailures",
          "routerWires","routerCuts","routerCompliant","routerFailures",
          "incompleteNets","wireViolations","rotations","rotationDomainCheck",
          "independentCopperOracle","moveAttempted","moveRejected","moveAccepted",
          "moveSameBoard","moveNewBest","moveMutateFailed","moveDecodeFailed",
          "quality","conflicts","incomplete","geometry","nonvertical","crossings",
          "strictFailures","auditFailures","auditWarnings","errors",
          "layoutSig","savedJson","elapsedSeconds")

def json_line(s):
    try:
        return json.loads(s)
    except (TypeError, ValueError):
        return None

def run_one(out: Path, prepared: dict, seed: int, timeout: int):
    job=out/"jobs"/f"seed_{seed:04d}"
    inp=job/"input"/"projects"/"1.json"
    core.write_json(inp,prepared)
    candidate=job/"candidate.json"
    cmd=["node",str(core.CLI),"--data",str(job/"input"),"--id","1",
         "--seed",str(seed),"--moves",str(MOVES),*FLAGS,"--save",str(candidate)]
    env=os.environ.copy()
    env["V5_NATIVE_LIB_DIR"]=str(core.EDGE_DECODE.parent)
    env.pop("V5_NATIVE_ROUTE_LIB_DIR",None)
    env["STRIPBOARD_TIMING"]="1"
    start=time.perf_counter()
    try:
        p=subprocess.run(cmd,cwd=core.FRONTEND,env=env,capture_output=True,
                         text=True,timeout=timeout)
        stdout,stderr,code=p.stdout,p.stderr,p.returncode
    except subprocess.TimeoutExpired as e:
        stdout=e.stdout or b""
        stderr=e.stderr or b""
        if isinstance(stdout,bytes): stdout=stdout.decode("utf8","replace")
        if isinstance(stderr,bytes): stderr=stderr.decode("utf8","replace")
        stderr+="\nTIMEOUT\n";code=124
    except OSError as e:
        stdout="";stderr=str(e);code=127
    elapsed=round(time.perf_counter()-start,3)
    (job/"stdout.log").write_text(stdout,encoding="utf8")
    (job/"stderr.log").write_text(stderr,encoding="utf8")
    cli=core.last_json(stdout) or {}
    traces=[x for line in stderr.splitlines()
            if line.startswith("finishTrace ")
            for x in [json_line(line[len("finishTrace "):])] if isinstance(x,dict)]
    trace=traces[-1] if traces else {}
    summary=cli.get("moveSummary") or {}
    errors=[]
    audit={}
    rotations=[]
    saved=None;sig=None
    if not candidate.is_file():
        errors.append("SAVED_JSON_MISSING")
    else:
        try:
            doc=json.loads(candidate.read_text(encoding="utf8"))
            bms,_=core.bms_info(doc); original,_=core.bms_info(prepared)
            if (bms.get("id")!=original.get("id") or
                bms.get("boardPos")!=core.BMS_POS or
                bms.get("rotation",0)!=0 or bms.get("locked") is not True or
                bms.get("edge") is not True or bms.get("slide") is not False):
                errors.append("BMS_ANCHOR_OR_FLAGS_CHANGED")
            board=doc.get("board",{})
            if (board.get("rows"),board.get("cols"),
                board.get("lockedRows"),board.get("lockedCols"))!=(24,56,True,True):
                errors.append("BOARD_LOCK_CHANGED")
            a=subprocess.run(["node",str(core.AUDITOR),str(candidate),str(inp)],
                             cwd=core.FRONTEND,capture_output=True,
                             text=True,timeout=120)
            (job/"audit.stdout.log").write_text(a.stdout,encoding="utf8")
            (job/"audit.stderr.log").write_text(a.stderr,encoding="utf8")
            audit=core.last_json(a.stdout) or {}
            if a.returncode!=0 or audit.get("valid") is not True:
                errors.append("SAVED_AUDIT_FAILED_"+str(a.returncode))
            if (audit.get("wires")!=cli.get("wires") or
                audit.get("cuts")!=cli.get("cuts")):
                errors.append("AUDIT_CLI_COUNTS_MISMATCH")
            sig=core.signature(doc)
            definitions={d.get("id"):d for d in doc.get("componentDefs",[])}
            for c in doc.get("components",[]):
                if c.get("offBoard") or c.get("boardExcluded"):continue
                d=definitions.get(c.get("defId"))
                if d and d.get("flexible"):continue
                rotations.append({"componentId":c.get("id"),"label":c.get("label"),
                                  "rotation":c.get("rotation",0),
                                  "allowed":"NOT_INDEPENDENTLY_CHECKED"})
        except (OSError,ValueError,TypeError,KeyError,subprocess.TimeoutExpired) as e:
            errors.append("VERIFY_EXCEPTION_"+str(e))
        if cli.get("strictValid") is not (code==0):
            errors.append("CLI_EXIT_VERDICT_MISMATCH")
        good=(code==0 and cli.get("strictValid") is True and
              audit.get("valid") is True and not errors)
        w,c=cli.get("wires"),cli.get("cuts")
        label=lambda v:str(v) if isinstance(v,int) else "NA"
        target=out/("passed" if good else "rejected")/(
            f"seed_{seed:04d}_W{label(w)}_C{label(c)}.json")
        target.parent.mkdir(parents=True,exist_ok=True)
        candidate.replace(target)
        saved=str(target.relative_to(out))
    good=(code==0 and cli.get("strictValid") is True and
          audit.get("valid") is True and not errors and saved is not None)
    r={"seed":seed,"moves":MOVES,"strictPass":good,"exit":code,
       "wires":cli.get("wires"),"cuts":cli.get("cuts"),
       "cutsMinusWires":(cli["cuts"]-cli["wires"] if
                         isinstance(cli.get("cuts"),int) and
                         isinstance(cli.get("wires"),int) else None),
       "firstFeasibleMove":cli.get("firstFeasibleMove"),
       "firstFeasibleMs":cli.get("firstFeasibleMs"),
       "selectedFinish":trace.get("selected"),
       "incompleteNets":cli.get("incompleteNets",[]),
       "wireViolations":cli.get("wireViolations",[]),
       "rotations":rotations,"rotationDomainCheck":"NOT_INDEPENDENTLY_CHECKED",
       "independentCopperOracle":"NOT_IMPLEMENTED",
       "quality":cli.get("quality"),"conflicts":cli.get("conflicts"),
       "incomplete":cli.get("incomplete"),"geometry":cli.get("geo"),
       "nonvertical":cli.get("diagonalsActual"),"crossings":cli.get("crossings"),
       "strictFailures":cli.get("strictFailures",[]),
       "auditFailures":audit.get("failures",[]),
       "auditWarnings":audit.get("warnings",[]),"errors":errors,
       "layoutSig":sig,"savedJson":saved,"elapsedSeconds":elapsed}
    for name in ("repair","router"):
        t=trace.get(name) or {}
        v=t.get("verification") or {}
        r[name+"Wires"]=t.get("wires")
        r[name+"Cuts"]=t.get("cuts")
        r[name+"Compliant"]=v.get("compliant")
        r[name+"Failures"]=v.get("failReasons",[])
    for field,src in (("moveAttempted","attempted"),("moveRejected","rejected"),
                      ("moveAccepted","accepted"),("moveSameBoard","sameBoard"),
                      ("moveNewBest","newBest"),("moveMutateFailed","mutateFailed"),
                      ("moveDecodeFailed","decodeFailed")):
        r[field]=summary.get(src)
    core.write_json(job/"diagnostic.json",
                    {"row":r,"cli":cli,"finishTraces":traces,"command":cmd})
    return r

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--jobs",type=int,default=4)
    p.add_argument("--timeout",type=int,default=1800)
    p.add_argument("--out",type=Path,
                   default=Path.home()/"Desktop"/"audioex_debug50_git")
    p.add_argument("--resume",action="store_true")
    args=p.parse_args()
    if args.jobs<1 or args.timeout<1:p.error("positive --jobs and --timeout required")
    out=args.out.expanduser().resolve()
    if out==core.ROOT or core.ROOT in out.parents:
        p.error("output directory cannot be inside repository")
    prereqs=[core.SOURCE,core.CLI,core.AUDITOR,core.EDGE_DECODE,
             core.NATIVE_ROUTE,core.NATIVE_ADDON,core.SOLVER_JS]
    for f in prereqs:
        if not f.is_file():p.error("Missing compiled prerequisite: "+str(f))
    source=core.SOURCE.read_bytes()
    prepared=core.prepare_audioex(json.loads(source))
    identity={"schema":"audioex-forensic-git/v1","seeds":list(SEEDS),
              "moves":MOVES,"flags":list(FLAGS),
              "sourceSha256":core.digest(source),
              "preparedSha256":core.digest(core.json_bytes(prepared)),
              "binaries":{str(f.relative_to(core.ROOT)):core.digest(f.read_bytes())
                          for f in prereqs[1:]}}
    manifest=out/"manifest.json"
    if args.resume:
        if not manifest.is_file() or json.loads(manifest.read_text()).get("identity")!=identity:
            p.error("Cannot resume: manifest/source/binaries/flags mismatch")
    else:
        if out.exists() and any(out.iterdir()):
            p.error("Output folder nonempty. Use --resume or another --out")
        out.mkdir(parents=True,exist_ok=True)
        shutil.copy2(core.SOURCE,out/"original_audioex.json")
        (out/"prepared_audioex.json").write_bytes(core.json_bytes(prepared))
        (out/"selected_seeds.txt").write_text("\n".join(map(str,SEEDS))+"\n")
        head=subprocess.run(["git","rev-parse","HEAD"],cwd=core.ROOT,
                            capture_output=True,text=True,check=True).stdout.strip()
        core.write_json(manifest,{"identity":identity,"gitCommit":head,
                        "createdUTC":datetime.now(timezone.utc).isoformat()})
    rows={}
    for path in sorted((out/"jobs").glob("seed_*/diagnostic.json")):
        obj=json.loads(path.read_text())
        row=obj["row"]
        if row["seed"] not in SEEDS or row["seed"] in rows:
            p.error("Unexpected/duplicate checkpoint")
        if row.get("savedJson") and not (out/row["savedJson"]).is_file():
            p.error("Missing saved candidate: "+str(row["savedJson"]))
        rows[row["seed"]]=row
    def publish():
        allrows=[rows[s] for s in sorted(rows)]
        with (out/"debug_results.csv").open("w",newline="",encoding="utf8") as stream:
            writer=csv.DictWriter(stream,fieldnames=FIELDS)
            writer.writeheader()
            for row in allrows:
                writer.writerow({f:json.dumps(row.get(f),ensure_ascii=False)
                                 if isinstance(row.get(f),(dict,list)) else row.get(f)
                                 for f in FIELDS})
        with (out/"debug_results.jsonl").open("w",encoding="utf8") as stream:
            for row in allrows:stream.write(json.dumps(row,ensure_ascii=False)+"\n")
        count=Counter(x for row in allrows for x in row.get("strictFailures",[]))
        with (out/"CLAUDE_HANDOFF.md").open("w",encoding="utf8") as f:
            f.write("# AUDIOEX 50-seed forensic rerun\n\n")
            f.write(f"Completed {len(rows)}/50; strict passes {sum(r['strictPass'] for r in allrows)}.\n\n")
            f.write("## Strict failure histogram\n\n")
            for k,n in count.most_common():f.write(f"- {k}: {n}\n")
            f.write("\n## Incomplete-net signature\n\n")
            for s in (722,1208,1377,1384):
                if s in rows:
                    r=rows[s]
                    f.write(f"- seed {s}: delta {r['cutsMinusWires']}, "+
                            f"incomplete nets {json.dumps(r['incompleteNets'])}\n")
            f.write("\n## Verification boundaries\n\n")
            f.write("Saved-board CLI audit reuses some implementation helpers. "+
                    "A disjoint copper-graph oracle and independent rotation-domain "+
                    "checker are NOT implemented; CSV fields explicitly say so. "+
                    "Do not interpret these as certified checks.\n")
    publish()
    remaining=[s for s in SEEDS if s not in rows]
    print(f"🔬 AUDIOEX | 50k moves | 4-worker-compatible | {len(remaining)} remaining",flush=True)
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        tasks={ex.submit(run_one,out,prepared,s,args.timeout):s for s in remaining}
        for future in as_completed(tasks):
            seed=tasks[future]
            try:row=future.result()
            except Exception as e:
                row={"seed":seed,"moves":MOVES,"strictPass":False,
                     "errors":["WORKER_EXCEPTION: "+repr(e)]}
                job=out/"jobs"/f"seed_{seed:04d}"
                core.write_json(job/"diagnostic.json",{"row":row})
            rows[seed]=row
            publish()
            print(f"{'✅ PASS' if row.get('strictPass') else '❌ REJECT'} "+
                  f"seed {seed:04d} | {row.get('wires','?')}W/{row.get('cuts','?')}C "+
                  f"| fit@{row.get('firstFeasibleMove','?')} "+
                  f"| {row.get('strictFailures',[])} "+
                  f"| finish {row.get('selectedFinish','?')}",flush=True)
    if core.SOURCE.read_bytes()!=source:raise RuntimeError("Source fixture changed")
    print(f"🏁 DONE | {out/'CLAUDE_HANDOFF.md'} | {out/'debug_results.csv'}",flush=True)

if __name__=="__main__":
    main()
