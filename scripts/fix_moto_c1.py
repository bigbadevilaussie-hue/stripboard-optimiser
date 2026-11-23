#!/usr/bin/env python3
"""v1.62 CLI-only: correct C1 1000mf -> 1000µF in active MOTO/MOTOMIX sources.

Dry-run: python3 scripts/fix_moto_c1.py
Apply:   python3 scripts/fix_moto_c1.py --apply

Default scan: repository, ~/Documents, ~/Downloads, ~/Desktop. Supply --root
one or more times to scan other folders. Historical saved benchmark layouts
and baselines are NEVER rewritten: correcting their inputs would invalidate
the archived original solve fingerprints. New benchmark output must use a
fresh directory. Backs up the exact original bytes before each edit.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
REVISION = "v1.62-C1-1000uF"
OLD_VALUE = "1000mf"
NEW_VALUE = "1000µF"

PRUNE = {
    ".git", ".venv", "venv", "node_modules", ".next", "__pycache__",
    "dist", "build", "coverage", "stripboard_c1_originals",
}
ARCHIVES = (
    "stripboard_drill_stack_80", "stripboard_baseline_80",
    "cli_profile_v160", "cli_budget_sweep_v161",
    "stripboard_arena", "stripboard_c1_originals",
)
VALUE_TOKEN = re.compile(r'"1000mf"', re.IGNORECASE)
C1_NET = re.compile(r'(\(comp\s+\(ref\s+"C1"\)\s*\(value\s+")1000mf(")', re.IGNORECASE)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def is_archive(path):
    return any(any(part.lower().startswith(prefix) for prefix in ARCHIVES)
               for part in path.parts)


def is_candidate(path):
    if path.suffix.lower() not in (".json", ".net"):
        return False
    return (path.name.lower().startswith("moto")
            or any(part.lower() in ("moto", "motomix") for part in path.parts))


def discover(roots):
    found = set()
    for root in roots:
        root = root.expanduser().resolve()
        if not root.is_dir():
            print("ℹ️ Scan root not found:", root)
            continue
        for folder, dirs, names in os.walk(root, followlinks=False):
            current = Path(folder)
            dirs[:] = [d for d in dirs if d not in PRUNE and not d.startswith(".")
                       and not is_archive(current / d)]
            if is_archive(current):
                dirs.clear()
                continue
            for name in names:
                path = current / name
                if path.is_symlink() or not is_candidate(path):
                    continue
                found.add(path)
    return sorted(found)


def corrected_text(path, text):
    """Return (status, new_text). Only update the verified C1 value."""
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(text)
        except (ValueError, UnicodeDecodeError):
            return "invalid-json", text
        if not isinstance(data, dict):
            return "not-project", text
        parts = data.get("components", [])
        if not isinstance(parts, list):
            return "not-project", text
        c1s = [c for c in parts if isinstance(c, dict) and c.get("label") == "C1"]
        if len(c1s) != 1:
            return "not-one-C1", text
        value = c1s[0].get("value")
        if value == NEW_VALUE:
            return "already-correct", text
        if not isinstance(value, str) or value.lower() != OLD_VALUE:
            return "other-C1-value", text
        # Avoid accidentally changing a similarly labelled second component.
        matches = list(VALUE_TOKEN.finditer(text))
        if len(matches) != 1:
            return "ambiguous-value", text
        changed = text[:matches[0].start()] + '"' + NEW_VALUE + '"' + text[matches[0].end():]
        check = json.loads(changed)
        if next(c for c in check["components"] if c.get("label") == "C1")["value"] != NEW_VALUE:
            raise AssertionError("C1 JSON post-check failed")
        return "update", changed

    if path.suffix.lower() == ".net":
        matches = list(C1_NET.finditer(text))
        if len(matches) == 1:
            changed = C1_NET.sub(lambda m: m.group(1) + NEW_VALUE + m.group(2), text, count=1)
            return "update", changed
        if len(matches) > 1:
            return "ambiguous-C1-net", text
        if re.search(r'\(comp\s+\(ref\s+"C1"\)\s+\(value\s+"1000µF"\)', text):
            return "already-correct", text
        return "no-matching-C1", text

    return "unsupported", text


def backup_target(path, destination, home):
    try:
        relative = path.relative_to(home)
    except ValueError:
        relative = Path("outside-home") / Path(path.as_posix().lstrip("/"))
    return destination / relative


def atomic_write(path, data):
    fd, name = tempfile.mkstemp(prefix=".c1-fix-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        shutil.copystat(path, name)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def apply_one(path, target, backup_dir, home):
    original = path.read_bytes()
    after = target.encode("utf-8")
    backup = backup_target(path, backup_dir, home)
    backup.parent.mkdir(parents=True, exist_ok=True)
    if backup.exists() and backup.read_bytes() != original:
        raise RuntimeError("Backup already exists with different contents: " + str(backup))
    if not backup.exists():
        shutil.copy2(path, backup)
    if backup.read_bytes() != original:
        raise RuntimeError("Backup verification failed: " + str(backup))
    atomic_write(path, after)
    if path.read_bytes() != after:
        raise RuntimeError("Post-write verification failed: " + str(path))
    return {"file": str(path), "backup": str(backup),
            "before_sha256": sha256(original), "after_sha256": sha256(after)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Actually modify sources (default: dry-run)")
    parser.add_argument("--root", type=Path, action="append", help="Search root; can be repeated")
    parser.add_argument("--backup-dir", type=Path,
                        default=Path.home() / "Desktop" / "stripboard_c1_originals")
    args = parser.parse_args()
    home = Path.home().resolve()
    roots = args.root or [ROOT, home / "Documents", home / "Downloads", home / "Desktop"]
    backup_dir = args.backup_dir.expanduser().resolve()
    changed = []
    reviewed = []
    failures = []
    seen = []
    for path in discover(roots):
        try:
            raw = path.read_bytes()
            if len(raw) > 20_000_000:
                continue
            text = raw.decode("utf-8")
            state, corrected = corrected_text(path, text)
            if state == "update":
                print(("✏️  FIX " if args.apply else "🔎 WOULD FIX ") + str(path), flush=True)
                if args.apply:
                    changed.append(apply_one(path, corrected, backup_dir, home))
                else:
                    seen.append(str(path))
            elif state == "already-correct":
                print("✅ Correct:", path)
            elif state in ("ambiguous-value", "ambiguous-C1-net", "invalid-json"):
                failures.append((str(path), state))
                print("❌ REVIEW:", path, state)
            elif state == "other-C1-value":
                reviewed.append((str(path), state))
                print("ℹ️ Other C1 value (left alone):", path)
        except (OSError, UnicodeDecodeError, ValueError, AssertionError) as exc:
            failures.append((str(path), str(exc)))
            print("❌ ERROR:", path, exc)
    if args.apply:
        backup_dir.mkdir(parents=True, exist_ok=True)
        manifest = backup_dir / "c1_migration_manifest.json"
        # Do not silently overwrite previous manifests with different changes.
        if manifest.exists():
            old = json.loads(manifest.read_text(encoding="utf-8"))
            entries = old.get("updated", [])
        else:
            entries = []
        by_path = {entry["file"]: entry for entry in entries}
        for entry in changed:
            by_path[entry["file"]] = entry
        manifest.write_text(json.dumps({"revision": REVISION, "updated": list(by_path.values()),
                                        "review": reviewed, "failures": failures},
                                       indent=2, ensure_ascii=False), encoding="utf-8")
        print("🏁 Corrected {} active source files. Backups and manifest: {}".format(len(changed), backup_dir))
    else:
        print("🏁 Dry-run: {} files need correction. Run with --apply to update.".format(len(seen)))
    if failures:
        print("⚠️ {} files require manual inspection; no guesswork applied.".format(len(failures)))
        raise SystemExit(1)
    print("🔒 Archived 80-run/36-run benchmark outputs have NOT been rewritten.")


if __name__ == "__main__":
    main()
