// Native C decoder must penalise the full 10 mm can, not only its lead holes.
// Requires npm run build:native:edge and TS compilation.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const decodeModule = new WebAssembly.Module(fs.readFileSync(
  path.join(__dirname,"../../components/stripboard/v5wasm/v5decode.wasm")));
const routeModule = new WebAssembly.Module(fs.readFileSync(
  path.join(__dirname,"../../components/stripboard/v5wasm/v5route.wasm")));
process.env.V5_NATIVE_LIB_DIR = path.join(__dirname,"native/build/edge");
require("./nativeInstance.js").install(decodeModule,routeModule);
const {V5WasmDecoder} = require(path.join(__dirname,
  "out/components/stripboard/v5wasm/v5Wasm.js"));

function model(row) {
  return {
    parts:[{kind:1,locked:true,isConn:false,clr:0,lines:0,fat:true,
      idx:0,sides:-1,lockY0:row,lockY1:row+1,lockX:3,lockRot:0,
      lockFlexH:0,flex:{na:0,nb:1,minS:1,maxS:4,canH:false,dc0:0,
        vd:[false,true,true,true,true],hasSpec:true,shape:2,mark:false,
        len:10,r:5/2.54}}],
    nNets:2,
    netPins:[
      [{pi:0,kind:1,end:0,pinIdx:[0,0,0,0]}],
      [{pi:0,kind:1,end:1,pinIdx:[0,0,0,0]}],
    ],
    flexIdx:[0],rigidIdx:[],siblingGroups:[],
    mRow:0,mCol:0,lockedRowsCap:8,lockedColsCap:8,
    sidesDef:15,clrPad:0,wBCut:24,wWire:4,wCut:0.05,
    conns:[],pullNets:[],pullNet:[],halfTurn:[],canHV:[false],rotK:[],
  };
}
function decode(row){
  const dec=new V5WasmDecoder(decodeModule,model(row));
  dec.rngSet(1);
  dec.writeGenome(dec.labInit());
  return dec.decode();
}
const top=decode(0),inside=decode(2),bottom=decode(6);
assert.equal(top.status,2,"top-edge layout decodes so geometry is measurable");
assert.ok(top.geoBad > 0,"offboard can at top must incur native geoBad");
assert.equal(inside.status,2);
assert.equal(inside.geoBad,0,"same capacitor fits when moved inward");
assert.equal(bottom.status,2);
assert.ok(bottom.geoBad > 0,"bottom-edge can must incur native geoBad");
console.log("✅ Native C board-envelope 10mm capacitor regression");
