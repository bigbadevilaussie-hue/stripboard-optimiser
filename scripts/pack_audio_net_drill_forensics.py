#!/usr/bin/env python3
"""Read existing audio.net Drill ON debug50 output; make a small analysis ZIP.

No solver calls, no deletions, no Git push. Retains chosen raw failure logs and
candidate boards along with a 50-seed overview for uploading to the chat.
"""
from __future__ import annotations
import argparse
from collections import Counter
from pathlib import Path
import csv
import json
import zipfile

DEFAULT = Path.home() / "Documents/Stripboard-Experiment-Archive/audio_net_drill_on_20k_debug50"
SELECTED = (3, 6, 12, 26, 32, 34, 49)
ALLOWED = {"stdoutLog", "stderrLog", "savedJson", "preparedInput"}

def extract_lines(path: Path):
    out = []
    with path.open(encoding="utf8") as f:
        for raw in f:
            try:
                row = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                out.append(row)
    return out

def safe_existing(base: Path, relative: str):
    dest = (base / relative).resolve()
    if not dest.is_relative_to(base.resolve()):
        raise ValueError("Unsafe path in results: " + str(relative))
    return dest if dest.is_file() else None

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in-dir", type=Path, default=DEFAULT)
    ap.add_argument("--seeds", type=int, nargs="*", default=list(SELECTED))
    args = ap.parse_args()
    folder = args.in_dir.expanduser().resolve()
    rows = extract_lines(folder / "results.jsonl")
    if not rows:
        ap.error("No result rows found in " + str(folder))
    seeds = {r["seed"]: r for r in rows}
    summary = {
        "totalRows": len(rows),
        "passed": sorted(r["seed"] for r in rows if r.get("strictPass")),
        "failed": sorted(r["seed"] for r in rows if not r.get("strictPass")),
        "reasonCounts": dict(Counter(reason for r in rows
            for reason in (r.get("strictFailures") or r.get("errors") or [r.get("unsolvedReason") or "none"]))),
        "selected": [s for s in args.seeds if s in seeds],
        "sourceFolder": folder.name,
    }
    output = folder / "audio_net_drill_forensics_upload.zip"
    if output.exists():
        ap.error("Bundle already exists, refusing overwrite: " + str(output))
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=7) as z:
        z.writestr("overview.json", json.dumps(summary, indent=2))
        z.writestr("all_50_results.jsonl", "\n".join(json.dumps(r, sort_keys=True) for r in sorted(rows,key=lambda x:x["seed"]))+"\n")
        for name in ("manifest.json", "summary.json", "results.csv"):
            p=folder/name
            if p.is_file(): z.write(p, name)
        for seed in args.seeds:
            row=seeds.get(seed)
            if not row: continue
            z.writestr(f"seed_{seed:02d}/result.json", json.dumps(row, indent=2))
            for field in ALLOWED:
                value=row.get(field)
                if isinstance(value,str):
                    p=safe_existing(folder,value)
                    if p: z.write(p, f"seed_{seed:02d}/{field}{p.suffix}")
            # Preserve audit and all native logs from the job folder, if present.
            path=row.get("stdoutLog")
            if isinstance(path,str):
                job=safe_existing(folder,path)
                if job:
                    for p in sorted(job.parent.glob("*")):
                        if p.is_file() and p.name not in {"candidate.json", "stdout.log", "stderr.log"}:
                            z.write(p,f"seed_{seed:02d}/job/{p.name}")
    print(f"✅ Analysed {len(rows)} seeds | PASS {len(summary['passed'])}: {summary['passed']}")
    print(f"🔬 Packed focus seeds: {summary['selected']}")
    print(f"📦 {output} ({output.stat().st_size / 1024:.1f} KiB)")
    print("📎 Attach this ZIP in the chat for detailed failure analysis.")

if __name__ == "__main__":
    main()
