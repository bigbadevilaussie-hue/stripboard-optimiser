#!/usr/bin/env python3
"""Native decoder speed laboratory v1.64 — A/B, exact-output-gated, CLI-only.

Compile each decoder variant into its OWN temporary output directory. Never
replace the native decoder or WASM used by the editor. Run fixed paired
MOTO/AUDIO seeds, compare saved JSON SHA256 (not just layout fingerprints),
and disqualify ANY variant that changes deterministic output.

Typical one-paste command from project root:
  python3 scripts/speed_lab_native.py --seeds 3 --repeats 2

Variant values: o3, o2, fp_off, cpu, no_errno, unroll, grid, identical,
both, cpu_both, lto. See --help for controls.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "src" / "frontend"
SOURCE = FRONTEND / "components" / "stripboard" / "v5wasm" / "decode.c"
HARNESS = FRONTEND / "tests" / "solver" / "v5Solve.js"
ORIGINAL_BUILD = FRONTEND / "tests" / "solver" / "native" / "build"
FIXTURES = {
    "AUDIO": ROOT / "test-fixtures" / "masters" / "audio" / "audio.json",
    "MOTO": ROOT / "test-fixtures" / "masters" / "moto" / "moto.json",
}
BASE_ARGS = ["-fPIC", "-shared"]
FIELDS = [
    "fixture", "policy", "seed", "repeat", "variant", "status", "reason",
    "strictValid", "sig", "jsonSha256", "wires", "cuts", "quality",
    "solveMs", "annealMs", "routeMs", "totalMs", "refSolveMs", "refAnnealMs",
    "solveSpeedupPct", "annealSpeedupPct",
]
DEFAULT_VARIANTS = (
    "o3", "o2", "fp_off", "cpu", "no_errno", "unroll",
    "grid", "identical", "both", "cpu_both", "lto",
)
POLICIES = {
    "loose": [],
    "drilled": ["--drilled", "1"],
    "no_stack": ["--nostack", "1"],
    "drilled_no_stack": ["--drilled", "1", "--nostack", "1"],
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def format_pct(ref, value):
    if not ref or not value:
        return None
    return round(100.0 * (ref / value - 1.0), 2)


def exact_verdict(reference, candidate):
    """Independent, fail-closed comparison; no timing fields are accepted."""
    if reference["exit"] != candidate["exit"]:
        return "exit_code"
    if reference["save_sha256"] != candidate["save_sha256"]:
        return "saved_json_sha256"
    if reference["result"] != candidate["result"]:
        return "cli_json_fields"
    return ""


def numeric(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def compile_flags(variant):
    cpu = ["-mcpu=native"] if platform.machine().lower() in ("arm64", "aarch64") else ["-march=native"]
    flagmap = {
        "o3": ["-O3"],
        "o2": ["-O2"],
        "fp_off": ["-O3", "-ffp-contract=off"],
        "cpu": ["-O3", *cpu],
        "no_errno": ["-O3", "-fno-math-errno"],
        "unroll": ["-O3", "-funroll-loops"],
        "grid": ["-O3", "-DV5_EXPERIMENT_FAST_GRID_CLEAR=1"],
        "identical": ["-O3", "-DV5_EXPERIMENT_FAST_IDENTICAL_GENOME=1"],
        "both": ["-O3", "-DV5_EXPERIMENT_FAST_GRID_CLEAR=1", "-DV5_EXPERIMENT_FAST_IDENTICAL_GENOME=1"],
        "cpu_both": ["-O3", *cpu, "-DV5_EXPERIMENT_FAST_GRID_CLEAR=1", "-DV5_EXPERIMENT_FAST_IDENTICAL_GENOME=1"],
        "lto": ["-O3", "-flto"],
    }
    return flagmap[variant]


def safe_dir(path):
    out = path.expanduser().resolve()
    if out == ROOT or out == FRONTEND or ROOT in out.parents:
        raise ValueError("Speed lab cannot overwrite any project source/build location")
    return out


def parse_json_line(output, prefix="{"):
    matches = [line.removeprefix(prefix) for line in output.splitlines()
               if line.startswith(prefix)]
    if not matches:
        return None
    return json.loads(matches[-1])


def make_native(variant, out, compiler):
    target = out / "builds" / variant
    target.mkdir(parents=True, exist_ok=True)
    lib = target / "libv5decode.so"
    cmd = [compiler, *compile_flags(variant), *BASE_ARGS, "-o", str(lib), str(SOURCE), "-lm"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    (target / "compile.txt").write_text(" ".join(cmd) + "\n" + proc.stdout + "\n" + proc.stderr,
                                        encoding="utf-8")
    if proc.returncode != 0 or not lib.exists():
        return None, proc.stderr.strip()[-1200:]
    return target, ""


def run_one(out, fixture, policy, seed, rep, variant, libdir=None):
    # The input is snapshotted byte-for-byte once and reused unchanged.
    base = out / "results" / fixture / policy / ("seed_%03d" % seed) / ("rep_%02d" % rep)
    base.mkdir(parents=True, exist_ok=True)
    save = base / (variant + ".json")
    env = os.environ.copy()
    env["STRIPBOARD_TIMING"] = "1"
    if libdir is None:
        env.pop("V5_NATIVE_LIB_DIR", None)
    else:
        env["V5_NATIVE_LIB_DIR"] = str(libdir)
    args = ["node", str(HARNESS), "--data", str(out / "inputs" / fixture),
            "--id", "1", "--seed", str(seed), "--moves", str(ARGS.moves),
            "--native", "1", "--strict", "1", "--routing-preference", "wires",
            "--save", str(save), *POLICIES[policy]]
    proc = subprocess.run(args, cwd=FRONTEND, env=env, capture_output=True, text=True)
    (base / (variant + ".stderr.txt")).write_text(proc.stderr, encoding="utf-8")
    if proc.returncode not in (0, 2):
        raise RuntimeError("%s/%s/%d/%d/%s: exit %d: %s" % (
            fixture, policy, seed, rep, variant, proc.returncode, proc.stderr[-500:]))
    result = parse_json_line(proc.stdout)
    timing = parse_json_line(proc.stderr, "timing ")
    if not result or not timing or not save.is_file():
        raise RuntimeError("%s: missing result, timing or JSON file" % variant)
    if result.get("strictValid") != (proc.returncode == 0):
        raise RuntimeError("%s: inconsistent strict exit code" % variant)
    return {
        "exit": proc.returncode, "result": result,
        "timing": timing, "save_sha256": sha256(save.read_bytes()),
    }


def append_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def estimate_run_count(variants, fixtures, policies, seeds, repeats):
    # A baseline before and after each group guards against clock drift.
    return len(fixtures) * len(policies) * seeds * repeats * (len(variants) + 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("/tmp/v5_native_speed_lab_v164"))
    parser.add_argument("--seeds", type=int, default=3, help="Seeds 1..N, same across all variants")
    parser.add_argument("--repeats", type=int, default=2, help="Serial repeats, alternating variant order")
    parser.add_argument("--moves", type=int, default=20000, help="Same fixed move count per run")
    parser.add_argument("--fixtures", default="AUDIO,MOTO", help="Comma-separated AUDIO,MOTO")
    parser.add_argument("--policies", default="loose,drilled_no_stack",
                        help="Comma-separated loose,drilled,no_stack,drilled_no_stack")
    parser.add_argument("--variants", default=",".join(DEFAULT_VARIANTS),
                        help="Comma-separated variants, must include o3")
    parser.add_argument("--clang", default="clang", help="Compiler (default clang)")
    args = parser.parse_args()
    global ARGS
    ARGS = args
    fixtures = [v.strip().upper() for v in args.fixtures.split(",") if v.strip()]
    policies = [v.strip() for v in args.policies.split(",") if v.strip()]
    variants = [v.strip() for v in args.variants.split(",") if v.strip()]
    if args.moves < 1 or args.seeds < 1 or args.repeats < 1:
        parser.error("moves, seeds and repeats must be positive")
    if not variants or "o3" not in variants or len(variants) != len(set(variants)) or any(v not in DEFAULT_VARIANTS for v in variants):
        parser.error("--variants must include o3, with unique recognised variant names")
    if not fixtures or len(fixtures) != len(set(fixtures)) or any(v not in FIXTURES for v in fixtures):
        parser.error("--fixtures must specify unique AUDIO and/or MOTO")
    if not policies or len(policies) != len(set(policies)) or any(v not in POLICIES for v in policies):
        parser.error("Unknown or duplicate policy")
    try:
        out = safe_dir(args.out)
    except ValueError as err:
        parser.error(str(err))
    if not HARNESS.is_file() or not SOURCE.is_file():
        parser.error("Native decoder source or CLI harness missing")
    if not (ORIGINAL_BUILD / "v5native.node").is_file() or not (ORIGINAL_BUILD / "libv5decode.so").is_file():
        parser.error("Existing native addon/build missing; run npm run build:native under src/frontend")
    if not (ORIGINAL_BUILD / "libv5route.so").is_file():
        parser.error("Native router binary missing; run npm run build:native")
    if (out / "speed_lab_raw.csv").exists():
        parser.error("Existing result file in --out: use a new output directory, never overwrite an experiment")
    for fixture in fixtures:
        data = json.loads(FIXTURES[fixture].read_text(encoding="utf-8"))
        board = data.get("board", {})
        if (board.get("rows"), board.get("cols"), board.get("lockedRows"), board.get("lockedCols")) != (24, 56, True, True):
            parser.error("%s master is not a locked 24x56 fixture" % fixture)
    if shutil.which(args.clang) is None:
        parser.error("Clang not installed")
    info = subprocess.run([args.clang, "--version"], capture_output=True, text=True)
    out.mkdir(parents=True, exist_ok=True)
    metadata = {
        "version": "v1.64-native-speed-lab",
        "fixture_sha256": {name: sha256(FIXTURES[name].read_bytes()) for name in fixtures},
        "decode_source_sha256": sha256(SOURCE.read_bytes()),
        "original_build_decode_sha256": sha256((ORIGINAL_BUILD / "libv5decode.so").read_bytes()),
        "compiler": info.stdout.split("\n", 1)[0],
        "machine": platform.platform(), "native": True, "moves": args.moves,
        "seeds": list(range(1, args.seeds + 1)), "repeats": args.repeats,
        "fixtures": fixtures, "policies": policies, "variants": variants,
        "serial": True,
    }
    (out / "speed_lab_config.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    for name in fixtures:
        dest = out / "inputs" / name / "projects" / "1.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(FIXTURES[name], dest)
    dirs = {}
    for v in variants:
        dirs[v], error = make_native(v, out, args.clang)
        if dirs[v] is None:
            print("🛑 BUILD SKIPPED {}: {}".format(v, error), flush=True)
        else:
            print("🔧 BUILD {}: {}".format(v, " ".join(compile_flags(v))), flush=True)
    if dirs.get("o3") is None:
        raise SystemExit("Cannot compile reference -O3 decoder")
    print("🏎️ Native speed lab: {} planned serial solves | {} seeds | {} repeats | {} moves".format(
        estimate_run_count([v for v in variants if dirs[v] is not None], fixtures, policies,
                           args.seeds, args.repeats), args.seeds, args.repeats, args.moves), flush=True)
    print("🛡️ Output gate: CLI result + strict flags + SHA256 of COMPLETE saved project JSON", flush=True)
    allrows, invalid = [], set()
    for fixture in fixtures:
        for policy in policies:
            for seed in range(1, args.seeds + 1):
                for rep in range(1, args.repeats + 1):
                    ordered = [v for v in variants if dirs[v] is not None and v != "o3"]
                    if (seed + rep) % 2:
                        ordered.reverse()
                    # Every candidate is judged against the same exact output
                    # from a fresh -O3 run, not against an earlier WR file.
                    ref = run_one(out, fixture, policy, seed, rep, "o3", dirs["o3"])
                    original = run_one(out, fixture, policy, seed, rep, "original", None)
                    original_issue = exact_verdict(ref, original)
                    if original_issue:
                        raise SystemExit("🛑 STOP: compiled O3 baseline differs from current existing native solver: " +
                                         original_issue + ". Preserve outputs; rebuild the standard native binary and retry in a NEW --out.")
                    print("🎯 {} {} seed #{} repeat #{} | baseline {}ms anneal {}ms".format(
                        fixture, policy, seed, rep, ref["timing"].get("solveMs"), ref["timing"].get("annealMs")), flush=True)
                    for v in ordered:
                        item = run_one(out, fixture, policy, seed, rep, v, dirs[v])
                        issue = exact_verdict(ref, item)
                        if issue:
                            invalid.add(v)
                        bt, ct = ref["timing"], item["timing"]
                        bsolve, csolve = numeric(bt.get("solveMs")), numeric(ct.get("solveMs"))
                        banneal, canneal = numeric(bt.get("annealMs")), numeric(ct.get("annealMs"))
                        row = {
                            "fixture": fixture, "policy": policy, "seed": seed, "repeat": rep,
                            "variant": v, "status": "MISMATCH" if issue else "MATCH",
                            "reason": issue, "strictValid": item["result"].get("strictValid"),
                            "sig": item["result"].get("sig"), "jsonSha256": item["save_sha256"],
                            "wires": item["result"].get("wires"), "cuts": item["result"].get("cuts"),
                            "quality": item["result"].get("quality"),
                            "solveMs": csolve, "annealMs": canneal,
                            "routeMs": numeric(ct.get("routeMs")), "totalMs": numeric(ct.get("totalMs")),
                            "refSolveMs": bsolve, "refAnnealMs": banneal,
                            "solveSpeedupPct": format_pct(bsolve, csolve),
                            "annealSpeedupPct": format_pct(banneal, canneal),
                        }
                        allrows.append(row)
                        print("{} {}: solve {:.1f}% | anneal {:.1f}% | {} W/{} C".format(
                            "❌" if issue else "✅", v, row["solveSpeedupPct"] or 0,
                            row["annealSpeedupPct"] or 0, row["wires"], row["cuts"]), flush=True)
                    append_csv(out / "speed_lab_raw.csv", allrows, FIELDS)
    summary = []
    for v in variants:
        rows = [r for r in allrows if r["variant"] == v]
        if not rows:
            continue
        good = [r for r in rows if r["status"] == "MATCH"]
        valid_variant = v not in invalid and len(good) == len(rows)
        s = {
            "variant": v, "match": valid_variant, "tests": len(rows),
            "mismatches": len(rows) - len(good),
            "medianSolveSpeedupPct": round(statistics.median(r["solveSpeedupPct"] for r in good), 2) if good else None,
            "medianAnnealSpeedupPct": round(statistics.median(r["annealSpeedupPct"] for r in good if r["annealSpeedupPct"] is not None), 2)
                                    if any(r["annealSpeedupPct"] is not None for r in good) else None,
            "flags": " ".join(compile_flags(v)),
            "status": "ELIGIBLE_TO_RETEST" if valid_variant else "REJECTED_DIFFERENT_OUTPUT",
        }
        summary.append(s)
    if summary:
        append_csv(out / "speed_lab_summary.csv", summary, list(summary[0]))
    print("\n📈 SPEED LAB RESULTS (serial, paired):", flush=True)
    for s in summary:
        print("{} {:14s} median solve {:+.2f}% | anneal {:+.2f}% | {}/{} matching".format(
            "🟢" if s["match"] else "🔴", s["variant"],
            s["medianSolveSpeedupPct"] or 0, s["medianAnnealSpeedupPct"] or 0,
            s["tests"] - s["mismatches"], s["tests"]), flush=True)
    print("📁 Full results: {}".format(out / "speed_lab_raw.csv"), flush=True)
    print("📁 Summary: {}".format(out / "speed_lab_summary.csv"), flush=True)
    print("⚠️ Exploratory timings only; repeat promising variants with more seeds and ABBA interleaving.", flush=True)
    if invalid:
        raise SystemExit("REJECTED: {} variant(s) altered output: {}".format(len(invalid), ",".join(sorted(invalid))))


if __name__ == "__main__":
    main()
