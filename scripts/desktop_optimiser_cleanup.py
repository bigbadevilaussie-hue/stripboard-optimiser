#!/usr/bin/env python3
"""Recursive, cautious inventory and non-destructive Desktop experiment cleanup."""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import argparse, json, os, re, shutil

ROOT = Path(__file__).resolve().parents[1]
DESKTOP = Path.home() / "Desktop"
ARCHIVE = Path.home() / "Documents" / "Stripboard-Experiment-Archive"
PRIVATE = Path.home() / "Documents" / "stripboard_desktop_recursive_listing.txt"
PUBLIC = ROOT / "docs" / "desktop_optimiser_inventory.json"
DIR_RX = [r"audioex_[\w-]+",r"motoex_[\w-]+",r"stripboard_[\w-]+",
          r"sweep_850k(?:_full)?",r"effort_sweep"]
FILE_RX = [r"audio_ladder_v\d+\.log",r"stripboard_[\w-]+\.log",
           r"MOTOEX_(?:CHAMPION|STRICT)_[\w.-]+\.(?:json|png)",
           r"motoex_col(?:25|41)_[\w-]+\.json"]
PROTECTED = {"audioex_pass1_2000_25k_top20"}

def selected():
    found = []
    for p in sorted(DESKTOP.iterdir()):
        if p.is_symlink():
            continue
        if p.is_dir() and any(re.fullmatch(rx,p.name) for rx in DIR_RX):
            found.append(p)
        elif p.is_file() and any(re.fullmatch(rx,p.name) for rx in FILE_RX):
            found.append(p)
    return found

def details(p):
    if p.is_file():
        return [(p.name,p.stat().st_size,p.suffix.lower())]
    result = []
    for base, dirs, files in os.walk(p,followlinks=False):
        dirs[:] = sorted(d for d in dirs if not (Path(base)/d).is_symlink())
        for name in sorted(files):
            f = Path(base)/name
            if f.is_file() and not f.is_symlink():
                try: result.append((str(f.relative_to(DESKTOP)),f.stat().st_size,f.suffix.lower()))
                except OSError: pass
    return result

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--move",action="store_true",help="move allowlisted outputs to Documents; never delete")
    args = ap.parse_args()
    if not DESKTOP.is_dir():
        ap.error("Desktop directory missing")
    files = selected()
    private = ["PRIVATE recursive Desktop optimiser listing — DO NOT COMMIT", ""]
    rows = []
    for p in files:
        data = details(p)
        private.extend([f"=== {p.name} ==="]+[f"{name}\t{size}" for name,size,_ in data]+[""])
        ext = Counter(extension or "(none)" for _,_,extension in data)
        rows.append(dict(name=p.name,kind="directory" if p.is_dir() else "file",
                         files=len(data),bytes=sum(size for _,size,_ in data),
                         extensions=dict(ext),protected=p.name in PROTECTED))
    PRIVATE.parent.mkdir(parents=True,exist_ok=True)
    PRIVATE.write_text("\n".join(private)+"\n",encoding="utf-8")
    if args.move:
        ARCHIVE.mkdir(parents=True,exist_ok=True)
        for p,row in zip(files,rows):
            if row["protected"]:
                row["action"] = "PROTECTED_ACTIVE_RUN"
            elif (ARCHIVE/p.name).exists():
                row["action"] = "SKIPPED_DESTINATION_EXISTS"
                print(f"⏭️ SKIP {p.name}: destination exists",flush=True)
            else:
                try:
                    shutil.move(str(p),str(ARCHIVE/p.name))
                    row["action"] = "MOVED"
                    print(f"📦 MOVED {p.name}",flush=True)
                except (OSError,shutil.Error) as error:
                    row["action"] = "ERROR"
                    print(f"❌ {p.name}: {error}",flush=True)
    else:
        for row in rows: row["action"] = "PROTECTED_ACTIVE_RUN" if row["protected"] else "ELIGIBLE_TO_MOVE"
    report = dict(schema="desktop-optimiser-inventory/v1",
                  timestamp_utc=datetime.now(timezone.utc).isoformat(),
                  scope="Allowlisted optimiser output only; excludes private files, apps, source repos, symlinks",
                  private_recursive_listing="~/Documents/stripboard_desktop_recursive_listing.txt (DO NOT COMMIT)",
                  archive="~/Documents/Stripboard-Experiment-Archive",
                  moved=args.move,entries=rows,
                  total_files=sum(r["files"] for r in rows),
                  total_bytes=sum(r["bytes"] for r in rows))
    PUBLIC.parent.mkdir(parents=True,exist_ok=True)
    PUBLIC.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(f"📋 {len(rows)} experiment items; {report['total_files']} nested files",flush=True)
    print(f"🔒 FULL recursive listing (private): {PRIVATE}",flush=True)
    print(f"📊 Public-safe Git summary: {PUBLIC}",flush=True)
    print("🛡️ Active 2000-seed Pass 1 and unrelated personal Desktop items remain untouched",flush=True)
    if args.move: print("✅ Moved eligible outputs to Documents. NOTHING DELETED.",flush=True)
    else: print("🔎 Inventory only. Nothing moved. Run --move to clear eligible items.",flush=True)

if __name__ == "__main__":
    main()
