#!/usr/bin/env python3
"""Original audio.net drill ON: seeds 1..50, 20k moves, full native forensics."""
import argparse
import json
import re
import sys
import time
import csv
import subprocess
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import run_audioex_native_ladder as core

MOVES = 20_000
SEEDS = tuple(range(1, 51))
SOURCE_NET = ROOT / "test-fixtures/masters/audio/audio.net"
SOURCE_JSON = ROOT / "test-fixtures/masters/audio/audio.json"
OUT = Path.home() / "Documents/Stripboard-Experiment-Archive/audio_net_drill_on_20k_debug50"

def verify_netlist(data, net_text):
    names = {n["id"]: n["name"] for n in data["nets"]}
    labels = {c["id"]: c["label"] for c in data["components"]}
    actual = {(names[a["netId"]], labels[a["componentId"]], str(a["pinId"]))
              for a in data["netAssignments"]}
    pieces = re.split(r'\(net\s+\(code\s+"[^"]+"\)\s+\(name\s+"([^"]+)"\)', net_text)
    expected = set()
    for i in range(1, len(pieces), 2):
        net_name, section = pieces[i], pieces[i+1]
        for ref, pin in re.findall(r'\(node\s+\(ref\s+"([^"]+)"\)\s+\(pin\s+"([^"]+)"\)', section):
            expected.add((net_name, ref, pin))
    if not expected or actual != expected:
        raise ValueError("audio.net / audio.json pin mismatch: " + json.dumps({
            "netCount": len(set(n for n, _, _ in expected)),
            "netPins": len(expected), "jsonPins": len(actual),
            "missingInJson": sorted(expected-actual)[:20],
            "missingInNet": sorted(actual-expected)[:20]}))
    return {"nets": len(set(x[0] for x in expected)), "assignedPins": len(expected)}

def manifest_identity(data):
    required = [core.CLI, core.AUDITOR, core.EDGE_DECODE,
                core.NATIVE_ROUTE, core.NATIVE_ADDON, core.SOLVER_JS]
    for p in required:
        if not p.is_file():
            raise FileNotFoundError("Build missing: " + str(p))
    return {
        "schema": "audio-net-drill-on-debug50-20k/v1",
        "netlistSha256": core.digest(SOURCE_NET.read_bytes()),
        "sourceJsonSha256": core.digest(SOURCE_JSON.read_bytes()),
        "netlistValidation": verify_netlist(data, SOURCE_NET.read_text(encoding="utf8")),
        "compiledSha256": {str(p.relative_to(ROOT)): core.digest(p.read_bytes()) for p in required},
        "moves": MOVES, "seeds": list(SEEDS),
        "drillOnly": True, "drillRotationDomain": True,
        "strict": True, "stacking": True, "forensicBypassPrecheck": True
    }

def save_summary(out, rows):
    reasons = Counter()
    for r in rows:
        if not r.get("strictPass"):
            reasons.update(r.get("strictFailures") or r.get("auditFailures") or
                           r.get("errors") or [r.get("unsolvedReason") or "UNCLASSIFIED"])
    summary = {
        "completed": len(rows), "total": len(SEEDS),
        "strictPasses": sum(bool(r.get("strictPass")) for r in rows),
        "failureReasons": dict(reasons),
        "unsolvedReasons": dict(Counter(r.get("unsolvedReason") or "none"
                       for r in rows if not r.get("strictPass"))),
        "elapsedWallMsSum": sum(r.get("elapsedWallMs") or 0 for r in rows)
    }
    core.write_json(out / "summary.json", summary)
    fields = core.FIELDS
    with (out / "results.csv").open("w", newline="", encoding="utf8") as file:
        writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in sorted(rows, key=lambda r:r["seed"]):
            item = dict(row)
            for f in ("strictFailures", "auditFailures", "auditWarnings", "errors"):
                item[f] = json.dumps(item.get(f, []))
            writer.writerow(item)
    return summary

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()
    if args.jobs < 1 or args.timeout < 1:
        ap.error("jobs and timeout must be positive")
    out = args.out.expanduser().resolve()
    data = json.loads(SOURCE_JSON.read_text(encoding="utf8"))
    if (data["board"]["rows"], data["board"]["cols"],
        data["board"]["lockedRows"], data["board"]["lockedCols"]) != (24,56,True,True):
        raise ValueError("audio.json board unexpectedly changed")
    if any(c.get("locked") and c.get("boardPos") for c in data["components"]):
        raise ValueError("original audio.json contains locked placed component")
    identity = manifest_identity(data)
    if args.resume:
        if not (out/"manifest.json").is_file():
            ap.error("missing resume manifest")
        previous = json.loads((out/"manifest.json").read_text())
        if previous["identity"] != identity:
            ap.error("source/binary identity mismatch; refusing resume")
        rows = core.read_checkpoint(out, (MOVES,), SEEDS)
    else:
        if out.exists() and any(out.iterdir()):
            ap.error("output already exists; use --resume")
        out.mkdir(parents=True,exist_ok=True)
        commit = subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,
                   capture_output=True,text=True,check=True).stdout.strip()
        core.write_json(out/"manifest.json",{
            "identity":identity,"gitCommit":commit,
            "createdUTC":datetime.now(timezone.utc).isoformat()})
        rows = []
    remaining = [s for s in SEEDS if s not in {r["seed"] for r in rows}]
    start=time.perf_counter()
    print("🔩 AUDIO.NET | 24×56 LOCKED | no locked BMS | STRICT | STACK ON",flush=True)
    print("✅ audio.net matches audio.json | " + str(identity["netlistValidation"]),flush=True)
    print("🔬 DRILL ON ONLY | seeds 1–50 | 20k moves | 3 workers default",flush=True)
    print("🧪 Native drill rotation domain ON | finish trace + move summary | precheck bypass for forensics",flush=True)
    print("💾 ALL stdout/stderr, saved candidates, audits, results kept: " + str(out),flush=True)
    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        futures={executor.submit(core.run_one,out,data,MOVES,s,args.timeout,
                    drilled=True,drill_domain=True,forensic=True,
                    enforce_bms_anchor=False):s for s in remaining}
        for future in as_completed(futures):
            seed=futures[future]
            try: r=future.result()
            except Exception as ex:
                r={"moves":MOVES,"seed":seed,"strictPass":False,"errors":[repr(ex)]}
            core.append_checkpoint(out,r)
            rows.append(r)
            save_summary(out,rows)
            print(("✅ PASS" if r.get("strictPass") else "❌ NOT STRICT") +
                f" seed {seed:02d} ({len(rows)}/50) | {r.get('wires','?')}W/{r.get('cuts','?')}C" +
                f" | reason {r.get('unsolvedReason') or r.get('strictFailures') or r.get('errors') or 'none'}" +
                f" | incomplete {r.get('incomplete','?')} conflicts {r.get('conflicts','?')}" +
                f" knife {r.get('knife','?')}" +
                f" | ⏱️ solve {(r.get('solveMs') or 0)/1000:.2f}s" +
                f" trial {(r.get('elapsedWallMs') or 0)/1000:.2f}s" +
                f" total {time.perf_counter()-start:.1f}s",flush=True)
    summary=save_summary(out,rows)
    print(f"🏁 DONE {len(rows)}/50 | {summary['strictPasses']} strict passes",flush=True)
    print("🧾 Failure reasons: " + str(summary["failureReasons"]),flush=True)
    print("📁 " + str(out) + " | 🛑 NO PASS 2",flush=True)

if __name__=="__main__":
    main()
