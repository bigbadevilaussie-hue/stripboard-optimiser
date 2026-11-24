// Native-only regression for rigid body overhang with negative fixed origin.
// Requires npm run build:solver && npm run build:native && npm run build:native:edge.
// This must fail before the opt-in EDGE decoder constraint fix, and pass after.
// It never starts a full audioex solver campaign.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const wasm = path.join(__dirname, "../../components/stripboard/v5wasm");
const decMod = new WebAssembly.Module(fs.readFileSync(path.join(wasm, "v5decode.wasm")));
const routeMod = new WebAssembly.Module(fs.readFileSync(path.join(wasm, "v5route.wasm")));
process.env.V5_NATIVE_LIB_DIR = path.join(__dirname, "native/build/edge");
require("./nativeInstance.js").install(decMod, routeMod);
const { V5WasmDecoder } = require(path.join(
  __dirname, "out/components/stripboard/v5wasm/v5Wasm.js"
));

function model({row, col, edge}) {
  // Each test pins electrically ON the physical board, even when its
  // plastic body origin is outside. A left-edge test must NOT reuse the
  // actual BMS pin at column offset zero.
  const pins = col < 0
    ? [{rowOff:4,colOff:4,net:0},{rowOff:11,colOff:6,net:1}]
    : [{rowOff:4,colOff:0,net:0},{rowOff:11,colOff:6,net:1}];
  const shape = {
    w:7, h:12, entry:-1,
    body:[0,11,0,6],
    pins,
  };
  return {
    parts:[{
      kind:0, locked:true, isConn:false, clr:0, lines:1,
      fat:false, idx:0, sides:edge ? -2 : -1,
      lockY0:row, lockY1:0, lockX:col, lockRot:0,
      lockFlexH:0, shapes:[shape,shape,shape,shape],
    }],
    nNets:2,
    netPins:[
      [{pi:0,kind:0,end:0,pinIdx:[0,0,0,0]}],
      [{pi:0,kind:0,end:0,pinIdx:[1,1,1,1]}],
    ],
    flexIdx:[], rigidIdx:[0], siblingGroups:[],
    mRow:0, mCol:0, lockedRowsCap:24, lockedColsCap:56,
    sidesDef:15, clrPad:0, wBCut:24, wWire:4, wCut:0.05,
    conns:[], pullNets:[], pullNet:[], halfTurn:[],
    canHV:[], rotK:[],
  };
}
function run(opts) {
  const decoder = new V5WasmDecoder(decMod, model(opts));
  decoder.rngSet(1);
  decoder.writeGenome(decoder.labInit());
  return decoder.decode();
}
// AUDIOEX: the BMS body occupies rows -2..9, with pins at 2 and 9.
const topEdge = run({row:-2, col:24, edge:true});
assert.equal(topEdge.status, 2,
  "negative locked BMS body origin must decode with opt-in Edge Mount");
assert.equal(topEdge.lockOver, 0,
  "a body-only overhang must not grow or violate locked 24x56 PCB");

// The same negative anchor without explicit edge permission must not decode.
const unapproved = run({row:-2, col:24, edge:false});
assert.equal(unapproved.status, 0,
  "ordinary locked rigid part cannot use negative origin");
// A left-edge overhang is governed by the symmetric column rule.
const leftEdge = run({row:4, col:-2, edge:true});
assert.equal(leftEdge.status, 2,
  "negative locked X origin is legal only for opt-in edge mount");
assert.equal(leftEdge.lockOver, 0,
  "left-edge body-only overhang cannot enlarge purchased board");
const leftUnapproved = run({row:4, col:-2, edge:false});
assert.equal(leftUnapproved.status, 0,
  "non-edge part cannot use negative X origin");
// A valid fixed on-board part must keep pre-existing behaviour.
const normal = run({row:4, col:24, edge:false});
assert.equal(normal.status, 2,
  "ordinary nonnegative locked placement must still decode");
console.log("✅ Native rigid Edge mount negative X/Y anchor regression passed");
