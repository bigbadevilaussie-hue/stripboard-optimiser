#!/usr/bin/env python3
"""Isolated MOTOEX-only Edge experiment. Generate C from current source; never edit production C."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "src/frontend"
SOURCE = FRONTEND / "components/stripboard/v5wasm/decode.c"
BASELINE = ROOT / "research/dave-sniff/20261127-10k/summary.json"
MASKS = {"adb3d26e-a0af-4dda-b90e-51b263b6f9a8": (90,270),
         "77c3cebd-3237-48d9-85c5-b0b0dfaec1c9": (0,180)}
MARKER = "DAVE_PAIR_READY"
FLAGS = ["-O3", "-DV5_EXPERIMENT_EDGE_MOUNT=1",
         "-DV5_EXPERIMENT_FAST_GRID_CLEAR=1",
         "-DV5_EXPERIMENT_FAST_IDENTICAL_GENOME=1", "-fPIC", "-shared"]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_fixture(path):
    """Verify raw fixture fingerprint, UUIDs, pin offsets and assigned nets."""
    baseline = json.loads(BASELINE.read_bytes())["campaigns"][0]["manifest"]
    if digest(path) != baseline["sourceSha256"]:
        raise ValueError("Orientation-pair experiment requires the archived MOTOEX fixture")
    master = json.loads(path.read_bytes())
    defs = {d["id"]: d for d in master["componentDefs"]}
    parts = {c["id"]: c for c in master["components"]}
    nets = {n["id"]:n["name"] for n in master["nets"]}
    for id,angles in MASKS.items():
        part = parts[id]
        d = defs[part["defId"]]
        gps = angles == (90,270)
        pins = [(p["offsetRow"], p["offsetCol"]) for p in d["pins"]]
        expected = [(12,c) for c in range(2,7)] if gps else [(r,0) for r in range(8)]
        names = {a["pinId"]:nets[a["netId"]] for a in master["netAssignments"] if a["componentId"]==id}
        required = {"1":"net27","2":"GND","3":"net25","4":"net29"} if gps else {"1":"3V3","2":"GND","3":"net11","4":"net10"}
        if (pins != expected or names != required or d.get("flexible")
            or (gps and d.get("halfTurnOnly")) or part.get("offBoard") or part.get("boardExcluded")):
            raise ValueError("Orientation fixture geometry/net contract changed: "+part["label"])
    for relative, expected in baseline["binarySha256"].items():
        if digest(ROOT / relative) != expected:
            raise ValueError("Baseline native binary changed: "+relative)
    return baseline


# Match line of unique consecutive pin centres, independent of body origin
# and pin ordering. Require exact counts and four assigned pins. The model
# has already transformed the pins for each rotation. Any ambiguity aborts.
HELPER = r'''
static i32 daveGps = -1, daveMpu = -1;
static int daveLine(i32 s, i32 count, int horizontal) {
  if (sPinCnt[s] != count) return 0;
  i32 first = sPinStart[s], fixed = horizontal ? spRow[first] : spCol[first];
  i32 low = 2147483647, high = -2147483647, assigned = 0;
  for (i32 i = first; i < first + count; i++) {
    i32 other = horizontal ? spRow[i] : spCol[i];
    i32 along = horizontal ? spCol[i] : spRow[i];
    if (other != fixed) return 0;
    low = imin(low, along); high = imax(high, along);
    if (spNet[i] >= 0) assigned++;
    for (i32 j = first; j < i; j++)
      if (spRow[i] == spRow[j] && spCol[i] == spCol[j]) return 0;
  }
  return high - low == count - 1 && assigned == 4;
}
static void daveIdentify(void) {
  daveGps = daveMpu = -1;
  for (i32 k = 0; k < nRigid; k++) {
    i32 pi = rigidList[k], s = pShapeBase[pi];
    if (pLocked[pi]) continue;
    int gps = daveLine(s,5,1) && daveLine(s+1,5,0) &&
              daveLine(s+2,5,1) && daveLine(s+3,5,0);
    int mpu = daveLine(s,8,0) && daveLine(s+1,8,1) &&
              daveLine(s+2,8,0) && daveLine(s+3,8,1);
    if (gps) {
      if (daveGps >= 0 || halfTurn[k]) {
        fprintf(stderr, "DAVE_PAIR_AMBIGUOUS_GPS\n"); abort();
      }
      daveGps = k;
    }
    if (mpu) {
      if (daveMpu >= 0) {
        fprintf(stderr, "DAVE_PAIR_AMBIGUOUS_MPU\n"); abort();
      }
      daveMpu = k;
    }
  }
  if (daveGps < 0 || daveMpu < 0 || drillRotationMode) {
    fprintf(stderr, "DAVE_PAIR_MODEL_MISMATCH gps=%d mpu=%d\n", daveGps, daveMpu); abort();
  }
  fprintf(stderr, "DAVE_PAIR_READY gps=%d mpu=%d\n", daveGps, daveMpu);
}
static int daveAllowed(i32 k, i32 rot) {
  if (k == daveGps) return rot == 1 || rot == 3;
  if (k == daveMpu) return rot == 0 || rot == 2;
  return 1;
}

'''


def patched(source):
    def once(old,new):
        nonlocal source
        if source.count(old) != 1:
            raise ValueError("Decoder anchor changed: "+old[:100])
        source = source.replace(old,new,1)
    once("#include <stdint.h>", "#include <stdint.h>\n#include <stdio.h>\n#include <stdlib.h>")
    once("static i32 mutate(int cold) {", HELPER+"static i32 mutate(int cold) {")
    # Keep the original RNG calls and proposed angle; reject a forbidden
    # proposal, rather than redraw or apply the generic drill-only domain.
    old = "      gRot[0] = (gRot[0] + (halfTurn[0] ? 2 : 1 + rint_(3))) % 4;"
    once(old, old+"\n      if (!daveAllowed(0,gRot[0])) return 0;")
    old = "    gRot[k] = (gRot[k] + (halfTurn[k] ? 2 : 1 + rint_(3))) % 4;"
    once(old, old+"\n    if (!daveAllowed(k,gRot[k])) return 0;")
    old = "  fillI(gRot, 0, nRigid); fillI(gHv, 0, nFlex); fillI(gBr, 0, nFlex);"
    once(old,old+"\n  daveIdentify();\n  gRot[daveGps] = 1;")
    return source


def build(master):
    baseline = validate_fixture(master)
    source = SOURCE.read_text(encoding="utf-8")
    generated = patched(source).encode()
    key = hashlib.sha256(generated).hexdigest()
    directory = FRONTEND / "tests/solver/native/build" / ("edge_gps_mpu_"+key[:12])
    directory.mkdir(parents=True,exist_ok=True)
    c = directory/"decode_gps_mpu.c"
    lib = directory/"libv5decode.so"
    metadata = directory/"build.json"
    if not metadata.exists():
        c.write_bytes(generated)
        tmp = directory/"libv5decode.tmp.so"
        command = ["clang",*FLAGS,"-o",str(tmp),str(c),"-lm"]
        subprocess.run(command,check=True)
        tmp.replace(lib)
        info = {"sourceSha256":digest(SOURCE), "generatedSha256":digest(c),
                "decoderSha256":digest(lib),"flags":FLAGS,
                "compiler":subprocess.check_output(["clang","--version"],text=True),
                "baselineBinarySha256":baseline["binarySha256"],
                "masks":{k:list(v) for k,v in MASKS.items()}}
        metadata.write_text(json.dumps(info,indent=2)+"\n",encoding="utf-8")
    info = json.loads(metadata.read_bytes())
    if (digest(c)!=key or digest(lib)!=info["decoderSha256"]
        or info["sourceSha256"]!=digest(SOURCE) or info["generatedSha256"]!=key):
        raise ValueError("Orientation experiment build fingerprint mismatch")
    return directory,info


def saved_errors(saved):
    parts = {c["id"]:c for c in saved["components"]}
    errors=[]
    for id,angles in MASKS.items():
        c=parts.get(id)
        if not c or not isinstance(c.get("boardPos"),dict) or c.get("rotation",0) not in angles:
            errors.append("PAIR_ROTATION_INVALID_"+id)
    return errors
