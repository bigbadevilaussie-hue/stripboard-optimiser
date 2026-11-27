#!/usr/bin/env python3
"""Read-only MOTOEX campaign forensics. Python standard library only; no solver."""
import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path


def read(path):
    return json.loads(path.read_bytes())


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def pos(p):
    return (p["row"], p["col"])


def local(root, name):
    p = (root / name).resolve()
    if not p.is_relative_to(root):
        raise ValueError("Path outside campaign: " + str(name))
    return p


def quality(saved):
    b = saved["board"]
    wires, cuts = b["wires"], b["cuts"]
    coverage = Counter()
    nonvertical = zero = 0
    length = 0.0
    for w in wires:
        a, z = pos(w["from"]), pos(w["to"])
        length += math.hypot(a[0]-z[0], a[1]-z[1]) * 2.54
        nonvertical += a[1] != z[1]
        zero += a == z
        if a[1] == z[1]:
            for row in range(min(a[0], z[0]), max(a[0], z[0])):
                coverage[a[1], row] += 1
    stack = max(coverage.values(), default=1 if wires else 0)
    unplaced = sum(not isinstance(c.get("boardPos"), dict)
                   for c in saved["components"]
                   if not (c.get("offBoard") or c.get("boardExcluded")))
    q = round(max(0, 100-.4*(.6*len(wires)+.4*len(cuts)+.02*length+
                             10*nonvertical+15*unplaced+max(0, stack-1)**2)), 2)
    return dict(wires=len(wires), cuts=len(cuts), length_mm=round(length, 6),
                stack=stack, q3=q, nonvertical=nonvertical, zero_length=zero,
                unplaced=unplaced)


def placement(c):
    return (c["id"], c.get("boardPos"), c.get("rotation", 0),
            c.get("flexibleEndPos"))


def signatures(saved):
    b = saved["board"]
    placements = sorted((placement(c) for c in saved["components"]),
                        key=lambda x: x[0])
    p = sha(canonical(placements).encode())
    c = sorted((x["row"], x["col"], x.get("kind", "between")) for x in b["cuts"])
    w = sorted(tuple(sorted((pos(x["from"]), pos(x["to"])))) for x in b["wires"])
    return p, sha(canonical([b["rows"], b["cols"], p, c, w]).encode())


def wire_details(entry, saved):
    """Recorded body-crossing evidence; independently compare endpoint indices."""
    d = entry.get("diagnostics", {})
    records = d.get("wireViolations")
    if not isinstance(records, list):
        return None, None, [], False
    crossing, nonvertical, bodies = set(), set(), Counter()
    wires = saved["board"]["wires"]
    valid = True
    for rec in records:
        i = rec.get("wire")
        if type(i) is not int or not 1 <= i <= len(wires):
            valid = False
            continue
        w = wires[i-1]
        if {pos(w["from"]), pos(w["to"])} != {pos(rec["from"]), pos(rec["to"])}:
            valid = False
        if "NONVERTICAL" in rec.get("violations", []):
            nonvertical.add(i)
        if "CROSSINGS" in rec.get("violations", []):
            crossing.add(i)
            bodies.update(rec.get("crossingComponents", []))
    actual = {i+1 for i,w in enumerate(wires) if w["from"]["col"] != w["to"]["col"]}
    valid &= actual == nonvertical
    if type(entry.get("crossings")) is not int or sum(bodies.values()) != entry["crossings"]:
        valid = False
    return sorted(crossing), sorted(crossing | actual), sorted(bodies.items()), bool(valid)


def invariants(saved, prepared):
    b = saved["board"]
    issues = []
    if (b.get("rows"), b.get("cols"), b.get("lockedRows"), b.get("lockedCols")) != (24,56,True,True):
        issues.append("BOARD_LOCK")
    for key in ("nets", "netAssignments", "componentDefs"):
        if saved.get(key) != prepared.get(key):
            issues.append("CHANGED_"+key)
    before = {c["id"]:c for c in prepared["components"]}
    after = {c["id"]:c for c in saved["components"]}
    if before.keys() != after.keys():
        issues.append("COMPONENT_IDS")
    for i,c in before.items():
        if c.get("locked") and after.get(i) != c:
            issues.append("LOCKED_COMPONENT_"+str(c.get("label",i)))
    if {i for i,c in before.items() if c.get("locked")} != {i for i,c in after.items() if c.get("locked")}:
        issues.append("LOCK_SET")
    def inside(p):
        return 0 <= p["row"] < 24 and 0 <= p["col"] < 56
    if any(not inside(p) for w in b["wires"] for p in (w["from"],w["to"])):
        issues.append("WIRE_OUTSIDE")
    if any(not inside(c) or (c.get("kind","between") == "between" and c["col"] == 55)
           for c in b["cuts"]):
        issues.append("CUT_OUTSIDE")
    return issues


def inspect(root):
    root = root.resolve()
    manifest = read(root/"manifest.json")
    payload = read(root/"results.json")
    entries = payload["results"]
    requested = manifest["seeds"]
    start, stride = manifest["seedStart"], manifest.get("seedStride",1)
    expected = {start+i*stride for i in range(requested)}
    actual = [e["seed"] for e in entries]
    if len(set(actual)) != len(actual):
        raise ValueError("Duplicate result seeds: "+root.name)
    if set(actual) != expected:
        raise ValueError("Incomplete or off-schedule campaign: "+root.name)
    cols = manifest["usb"]["selectedColumns"]
    if cols != [47] or manifest["usb"]["slide"]:
        raise ValueError("Expected fixed USB col47, Slide OFF")
    rows = []
    counter = Counter()
    net_patterns, offenders, failure_tags = Counter(), Counter(), Counter()
    rotations = defaultdict(Counter)
    placements, layouts, input_hashes = Counter(), Counter(), Counter()
    incomplete_hist = Counter()
    near = []
    errors = []
    for e in sorted(entries, key=lambda e:e["seed"]):
        seed = e["seed"]
        row = dict(campaign=root.name, seed=seed, column=e["column"],
                   strict=bool(e.get("strictPass")), incomplete=e.get("incomplete"),
                   geometry=e.get("geometry"), conflicts=e.get("conflicts"),
                   reported_crossings=e.get("crossings"),
                   reported_nonvertical=e.get("nonvertical"), saved=e.get("savedJson",""),
                   elapsed_ms=e.get("elapsedWallMs"), solve_ms=e.get("time",{}).get("solveMs"))
        rows.append(row)
        counter["attempts"] += 1
        counter["strict"] += row["strict"]
        failure_tags.update(e.get("strictFailures", []))
        if e.get("sourceSha256") != manifest["sourceSha256"] or e["column"] != 47:
            errors.append([seed,"SOURCE_OR_COLUMN_MISMATCH"])
        if e.get("unsolvedReason"):
            counter["unsolved"] += 1
            row["status"] = e["unsolvedReason"]
            continue
        if not e.get("savedJson"):
            counter["missing_saved"] += 1
            row["status"] = "MISSING_SAVED"
            errors.append([seed,"MISSING_SAVED"])
            continue
        try:
            raw = local(root,e["savedJson"]).read_bytes()
            if sha(raw) != e.get("savedSha256"):
                raise ValueError("SAVED_HASH_MISMATCH")
            saved = json.loads(raw)
            input_raw = local(root,e["input"]).read_bytes()
            prepared = json.loads(input_raw)
            input_hashes[sha(input_raw)] += 1
            issues = invariants(saved,prepared)
            q = quality(saved)
            row.update(q)
            counter["hash_verified"] += 1
            if issues:
                errors.append([seed,";".join(issues)])
                counter["invariant_failures"] += 1
            if any(q[k] != e.get(k) for k in ("wires","cuts","nonvertical")):
                issues.append("METRICS_MISMATCH")
                errors.append([seed,"METRICS_MISMATCH"])
            p,l = signatures(saved)
            placements[p] += 1
            layouts[l] += 1
            row.update(placement_sha=p, layout_sha=l, status="SAVED", sha256=sha(raw))
            crossing, union, bodies, diagnostic_ok = wire_details(e,saved)
            row.update(crossing_wires=len(crossing) if crossing is not None else None,
                       offender_wires=len(union) if union is not None else None,
                       offender_ids=";".join(map(str,union or [])),
                       crossing_bodies=canonical(dict(bodies)), diagnostic_ok=diagnostic_ok)
            if not diagnostic_ok:
                counter["wire_diagnostic_mismatch"] += 1
            offenders.update(dict(bodies))
            n = e.get("incomplete")
            c = e.get("conflicts")
            nets = e.get("diagnostics",{}).get("incompleteNets")
            names = sorted(str(x.get("name") or x.get("id")) for x in nets) if isinstance(nets,list) else []
            net_ok = type(n) is int and isinstance(nets,list) and len(names)==n
            row["nets"] = ";".join(names) if net_ok else "UNKNOWN"
            if net_ok:
                net_patterns[row["nets"] or "(none)"] += 1
                incomplete_hist[str(n)] += 1
            else:
                counter["net_diagnostic_missing_or_mismatch"] += 1
            complete = type(n) is int and type(c) is int and n==0 and c==0
            counter["reported_electrically_complete"] += complete
            counter["reported_incomplete"] += type(n) is int and n>0
            counter["reported_conflicts"] += type(c) is int and c>0
            counter["zero_crossing"] += e.get("crossings")==0
            counter["zero_nonvertical"] += q["nonvertical"]==0
            for comp in saved["components"]:
                label = str(comp.get("label",""))
                if label and isinstance(comp.get("boardPos"),dict):
                    rot = str(comp.get("rotation",0))
                    rotations[label][rot+" | "+row["nets"]] += 1
                    if label.upper() in ("GPS","MPU"):
                        row[label.lower()+"_rotation"] = rot
                        row[label.lower()+"_position"] = canonical(comp["boardPos"])
            # Only routing-fault candidates, not promoted to strict. No invented
            # repairability proof; geometry and connectivity remain CLI-reported.
            if (not row["strict"] and complete and net_ok and diagnostic_ok
                and e.get("geometry")==0 and not issues and not q["unplaced"]
                and not q["zero_length"] and union and len(union)<=3):
                near.append(dict(seed=seed, offenders=len(union),
                                 crossing_wires=len(crossing), nonvertical=q["nonvertical"],
                                 wires=q["wires"], cuts=q["cuts"], q3=q["q3"],
                                 ids=union, saved=row["saved"], sha256=row["sha256"]))
        except (OSError,ValueError,TypeError,KeyError,IndexError) as exc:
            row["status"] = "READ_OR_SCHEMA_ERROR"
            errors.append([seed,str(exc)])
            counter["read_or_schema_errors"] += 1
        if counter["attempts"] % 100 == 0:
            print("🔎",root.name,counter["attempts"],"/",requested,flush=True)
    near.sort(key=lambda x:(x["offenders"],-x["q3"],x["wires"],x["cuts"],x["seed"]))
    def stats(key):
        v = [r[key] for r in rows if isinstance(r.get(key),(int,float))]
        return dict(n=len(v),mean=round(statistics.mean(v),3),median=round(statistics.median(v),3)) if v else {}
    report = dict(campaign=root.name, manifest=manifest, result_sha256=sha((root/"results.json").read_bytes()),
                  reported_duration_s=payload.get("summary",{}).get("durationWallS"),
                  counts=dict(counter), net_patterns=dict(net_patterns.most_common()),
                  incomplete_histogram=dict(incomplete_hist), crossing_components=dict(offenders.most_common()),
                  failure_tags=dict(failure_tags.most_common()), rotations={k:dict(v) for k,v in rotations.items()},
                  distinct_placements=len(placements), distinct_layouts=len(layouts),
                  duplicate_placement_attempts=sum(placements.values())-len(placements),
                  duplicate_layout_attempts=sum(layouts.values())-len(layouts),
                  input_hash_counts=dict(input_hashes), elapsed_ms=stats("elapsed_ms"), solve_ms=stats("solve_ms"),
                  candidate_count=len(near), near_misses=near, errors=errors)
    return report,rows,set(placements),set(layouts)


def markdown(reports, common, overlaps):
    lines = ["# Dave — local campaign sniff", "",
             "Read-only Python inspection. Electrical/geometry/crossing status is recorded CLI evidence, not an independent copper graph/body audit. Q3 on rejected boards is descriptive only. Near misses are research candidates, not strict passes.", "",
             "## Comparison", "",
             "| Metric | "+ " | ".join(r["campaign"] for r in reports)+" |",
             "|---|"+"---:|"*len(reports)]
    for label,key in [("Attempts","attempts"),("Strict","strict"),("Unsolved","unsolved"),
                      ("Saved hashes verified","hash_verified"),("Missing saved","missing_saved"),
                      ("Reported electrically complete","reported_electrically_complete"),
                      ("Reported incomplete","reported_incomplete"),("Reported conflicts","reported_conflicts"),
                      ("Zero crossings","zero_crossing"),("Zero nonvertical","zero_nonvertical"),
                      ("Wire diagnostic mismatches","wire_diagnostic_mismatch"),
                      ("Net diagnostic mismatches","net_diagnostic_missing_or_mismatch"),
                      ("Invariant failures","invariant_failures"),("Read/schema errors","read_or_schema_errors")]:
        lines.append("| "+label+" | "+" | ".join(str(r["counts"].get(key,0)) for r in reports)+" |")
    for key in ("distinct_placements","distinct_layouts","candidate_count","reported_duration_s"):
        lines.append("| "+key+" | "+" | ".join(str(r[key]) for r in reports)+" |")
    lines += ["","## Provenance", "", "Matching manifest fields: "+canonical(common),
              "", "Cross-campaign overlaps: "+canonical(overlaps),""]
    for r in reports:
        lines += ["## "+r["campaign"],"", "### Incomplete-net combinations","",
                  "| Net combination | Boards |","|---|---:|"]
        for k,v in r["net_patterns"].items():
            lines.append("| "+k.replace("|","/")+" | "+str(v)+" |")
        lines += ["","### Most crossed components (wire/body records)",""]
        lines += ["- "+k+": "+str(v) for k,v in list(r["crossing_components"].items())[:15]]
        lines += ["","### GPS / MPU rotation versus net combination",""]
        for label in ("GPS","MPU"):
            for key,counts in r["rotations"].items():
                if key.upper()==label:
                    lines += ["- "+key+" "+k+": "+str(v) for k,v in sorted(counts.items())]
        lines += ["","### Routing-only candidates (up to three distinct offending wires)","",
                  "| Seed | Offenders | Nonvertical | Crossing wires | W/C | Raw Q3 |","|---:|---:|---:|---:|---:|---:|"]
        for x in r["near_misses"][:20]:
            lines.append("| {seed} | {offenders} | {nonvertical} | {crossing_wires} | {wires}/{cuts} | {q3} |".format(**x))
        lines += ["","Integrity warnings/errors: "+str(len(r["errors"]))+". Full details in summary.json and seeds.csv.",""]
    return "\n".join(lines)+"\n"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("runs",nargs=2,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    roots=[x.expanduser().resolve() for x in a.runs]
    out=a.out.expanduser().resolve()
    if roots[0]==roots[1] or any(out.is_relative_to(x) for x in roots):
        p.error("Require two different campaigns and separate output folder")
    if out.exists() and any(out.iterdir()):
        p.error("Output folder is not empty; preserve previous reports")
    data=[inspect(x) for x in roots]
    reports=[x[0] for x in data]
    allrows=[r for x in data for r in x[1]]
    fields=("sourceSha256","binarySha256","board","usb","moves","drilled","nostack","drillDomain","wirePolish","rank")
    common={k: reports[0]["manifest"].get(k)==reports[1]["manifest"].get(k)
            and k in reports[0]["manifest"] and k in reports[1]["manifest"] for k in fields}
    overlap=dict(seed_ids=len({r["seed"] for r in data[0][1]} & {r["seed"] for r in data[1][1]}),
                 placements=len(data[0][2]&data[1][2]), layouts=len(data[0][3]&data[1][3]))
    out.mkdir(parents=True,exist_ok=True)
    # The recorded manifests retain local provenance. No raw boards/job logs copied.
    (out/"summary.json").write_text(json.dumps(dict(campaigns=reports,matching_manifest_fields=common,
                      overlaps=overlap),indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    keys=list(dict.fromkeys(k for row in allrows for k in row))
    with (out/"seeds.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(allrows)
    report=markdown(reports,common,overlap)
    (out/"report.md").write_text(report,encoding="utf-8")
    print(report)
    print("📁",out)
    print("✅ Sniff complete — no solver executed. Inspect warnings before interpreting comparisons.")


if __name__=="__main__":
    main()
