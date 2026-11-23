// Generic native Edge experiment: drill-only orientation restrictions.
// No test-fixture names, labels, or hard-coded part whitelist.
const assert = require("node:assert/strict");
const fs = require("fs");
const path = require("path");
const out = path.join(__dirname, "out");
const decodeModule = new WebAssembly.Module(fs.readFileSync(
  path.join(__dirname, "../../components/stripboard/v5wasm/v5decode.wasm")));
const routeModule = new WebAssembly.Module(fs.readFileSync(
  path.join(__dirname, "../../components/stripboard/v5wasm/v5route.wasm")));
process.env.V5_NATIVE_LIB_DIR = path.join(__dirname, "native/build/edge");
require("./nativeInstance.js").install(decodeModule, routeModule);
const { V5WasmDecoder } = require(path.join(out, "components/stripboard/v5wasm/v5Wasm.js"));

const shapes = (nets) => [0, 1, 2, 3].map((rot) => {
  const vertical = rot % 2 === 1;
  return {
    w: vertical ? 1 : 2, h: vertical ? 2 : 1,
    entry: -1, body: vertical ? [0, 1, 0, 0] : [0, 0, 0, 1],
    pins: nets.map((net, i) => ({
      rowOff: vertical ? i : 0, colOff: vertical ? 0 : i, net
    }))
  };
});
function model(nets, locked = false, halfTurn = false) {
  const nNets = Math.max(0, ...nets.filter((n) => n >= 0).map((n) => n + 1));
  return {
    parts: [{kind:0, locked, isConn:false, clr:0, lines:1, fat:false,
      idx:0, sides:-1, lockY0:0, lockY1:0, lockX:0, lockRot:0,
      lockFlexH:0, shapes:shapes(nets)}],
    nNets, netPins:Array.from({length:nNets}, (_,n) => nets.flatMap((v,i) =>
      v === n ? [{pi:0,kind:0,end:0,pinIdx:[i,i,i,i]}] : [])),
    flexIdx:[], rigidIdx:[0], siblingGroups:[], mRow:0, mCol:0,
    lockedRowsCap:-1, lockedColsCap:-1, sidesDef:15, clrPad:0,
    wBCut:24, wWire:4, wCut:0.05, conns:[], pullNets:[], pullNet:[],
    halfTurn:[halfTurn], canHV:[], rotK:[0],
  };
}
function decoder(nets, locked = false, halfTurn = false) {
  return new V5WasmDecoder(decodeModule, model(nets, locked, halfTurn));
}
const unrestricted = decoder([0, 1]);
assert.equal(unrestricted.labInit().rot[0], 0, "ordinary non-drilled starts at 0");
const d = decoder([0, 1]);
assert.equal(d.setDrilledRotationDomain(true), true, "opt-in setter missing");
d.rngSet(123);
const g = d.labInit();
assert.equal(g.rot[0], 1, "different-net adjacent pins should start vertical");
d.writeGenome({...g, rot:[0]});
assert.equal(d.decode().status, 0, "horizontal incompatible rotation must fail decode");
d.writeGenome({...g, rot:[2]});
assert.equal(d.decode().status, 0, "180-degree incompatible rotation must fail decode");
d.writeGenome(g);
assert.equal(d.decode().status, 2, "vertical compatible rotation must decode");
for (let i = 0; i < 1000; i++) {
  const next = d.labMutate(g);
  if (next) assert.ok([1,3].includes(next.rot[0]), "rotation move left allowed domain");
}
const sameNet = decoder([0, 0]);
sameNet.setDrilledRotationDomain(true);
assert.equal(sameNet.labInit().rot[0], 0, "same-net adjacent pins must remain permitted");
const floating = decoder([-1, -1]);
floating.setDrilledRotationDomain(true);
assert.equal(floating.labInit().rot[0], 1, "floating pins each require isolation");
const half = decoder([0, 1], false, true);
half.setDrilledRotationDomain(true);
assert.equal(half.labInit().rot[0], 1, "half-turn part may start in allowed odd parity");
const locked = decoder([0, 1], true);
locked.setDrilledRotationDomain(true);
const fixed = locked.labInit();
locked.writeGenome(fixed);
assert.equal(locked.decode().status, 0, "invalid locked rotation must be reported infeasible");
console.log("✅ Native generic drilled rotation domain: synthetic tests passed");
