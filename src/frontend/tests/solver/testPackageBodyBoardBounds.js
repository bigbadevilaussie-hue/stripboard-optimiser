// Strict physical-envelope regression for an unexceptional 10 mm radial can.
// Run after: npx tsc -p tests/solver/tsconfig.json
const assert = require("node:assert/strict");
const path = require("node:path");
const {checkGeometry} = require("./helpers.js");
const {packageBodyOutsideBoard} = require(path.join(__dirname,
  "out/components/stripboard/partGeometry.js"));
const {resolvePackage, MM_PER_HOLE} = require(path.join(__dirname,
  "out/components/stripboard/packageBodies.js"));

const capDef = {
  id:"def-cap-polarized", name:"Polarised Capacitor", category:"passive",
  symbol:"c", defaultLabelPrefix:"C", flexible:true, width:1, height:2,
  pins:[{id:"1",name:"1",offsetRow:0,offsetCol:0},
        {id:"2",name:"2",offsetRow:1,offsetCol:0}],
};
const rigidDef = {
  id:"synthetic-module", name:"Rigid Module", category:"generic",
  symbol:"x", defaultLabelPrefix:"U", width:2, height:2,
  pins:[{id:"1",name:"1",offsetRow:0,offsetCol:0}],
  bodyCells:[{row:0,col:1},{row:1,col:0},{row:1,col:1}],
};
const board = {rows:8,cols:8,cuts:[],wires:[]};
const cap = (row, col, horizontal=false) => ({
  id:"c6", defId:capDef.id, label:"C6", value:"470µF",
  schematicPos:{x:0,y:0},schematicRotation:0,rotation:0,
  boardPos:{row,col},
  flexibleEndPos:{row:row+(horizontal?0:1),col:col+(horizontal?1:0)},
});
const moduleAt = (row, col, extras={}) => ({
  id:"u1",defId:rigidDef.id,label:"U1",rotation:0,
  schematicPos:{x:0,y:0},schematicRotation:0,boardPos:{row,col},...extras,
});
const pkg = resolvePackage(capDef,"470µF");
assert.equal(pkg.kind,"twoPin");
assert.equal(pkg.spec.shape,"can");
assert.equal(pkg.spec.wid,10,"470µF keeps its modelled 10 mm diameter");
assert.ok(Math.abs(pkg.spec.wid/MM_PER_HOLE - 10/2.54) < 1e-10);

const top = cap(0,3);
assert.ok(packageBodyOutsideBoard(board,top,capDef),
  "can top extends past the -0.5 pitch board boundary");
assert.ok(checkGeometry(board,[top],[capDef]).some(x=>x.includes("package body off-board")),
  "independent checker must reject the same shape shown by the renderer");
const side = cap(3,0,true);
assert.ok(packageBodyOutsideBoard(board,side,capDef),"can may not overhang left edge");
const inside = cap(2,3);
assert.equal(packageBodyOutsideBoard(board,inside,capDef),false,
  "can with enough room around both leads fits");
assert.deepEqual(checkGeometry(board,[inside],[capDef]),[],"inside capacitor is legal");
assert.ok(packageBodyOutsideBoard(board,{...top,locked:true,edge:true},capDef),
  "rigid-only Edge exception cannot legalise flexible capacitors");

const ordinary = moduleAt(7,2);
assert.ok(packageBodyOutsideBoard(board,ordinary,rigidDef));
assert.ok(checkGeometry(board,[ordinary],[rigidDef]).some(x=>x.includes("package body off-board")));
assert.ok(packageBodyOutsideBoard(board,moduleAt(7,2,{edge:true}),rigidDef),
  "edge without an exact lock is not exempt");
assert.equal(packageBodyOutsideBoard(board,moduleAt(7,2,{locked:true,edge:true}),rigidDef),false,
  "an explicitly locked rigid Edge mount may overhang");
assert.deepEqual(checkGeometry(board,[moduleAt(6,2)],[rigidDef]),[]);
console.log("✅ Physical package board bounds: 10mm can, rigid Edge exemption and strict geometry");
