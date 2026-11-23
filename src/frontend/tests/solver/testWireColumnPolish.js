// Pure synthetic regression: inspect independent verifiers on EVERY kept move.
const assert = require("node:assert/strict");
const path = require("path");
const { polishFixedBoardWires } = require(path.join(
  __dirname, "out/components/stripboard/wireColumnPolish.js"));
const { verify, checkGeometry } = require("./helpers.js");
const pinDef = { id:"probe", name:"Probe", category:"generic", symbol:"x",
  width:1, height:1, pins:[{id:"1",name:"1",offsetRow:0,offsetCol:0}] };
const net = (id) => ({id,name:id,color:"#f00"});
function comp(id, row, col) {
  return {id, label:id, defId:"probe", boardPos:{row,col},rotation:0,
    schematicPos:{x:0,y:0},schematicRotation:0};
}
function a(componentId, netId) {return {componentId,pinId:"1",netId};}
function run(board, parts, assignments, nets, wirePolish = true) {
  const result = {placements:[],wires:board.wires,cuts:board.cuts,
    issues:[],quality:0,starvedNetIds:[],boardSize:{rows:board.rows,cols:board.cols}};
  const before = verify(board,parts,nets,assignments,[pinDef]);
  const result0 = polishFixedBoardWires(board,parts,[pinDef],nets,assignments,
    result, wirePolish ? 6000 : 0);
  const afterBoard = {...board,cuts:result0.result.cuts,
    wires:result0.result.wires.map((w,i)=>({...w,id:"t"+i}))};
  const after = verify(afterBoard,parts,nets,assignments,[pinDef]);
  assert.equal(after.conflicts, before.conflicts,"never increase electrical conflicts");
  assert.equal(after.incomplete.length, before.incomplete.length,"never lose a connected net");
  assert.equal(checkGeometry(afterBoard,parts,[pinDef]).length,
    checkGeometry(board,parts,[pinDef]).length,"never worsen part geometry");
  assert.equal(afterBoard.rows,board.rows,"never alter physical board rows");
  assert.equal(afterBoard.cols,board.cols,"never alter physical board columns");
  return result0;
}
const knifeBoard = {rows:3,cols:9,cuts:[{row:0,col:2,kind:"between"}],
  wires:[{from:{row:0,col:3},to:{row:2,col:3}}]};
const knifeParts = [comp("a",0,2),comp("b",0,4),comp("c",2,5)];
const knifeAssignments = [a("a","A"),a("b","B"),a("c","B")];
const knife = run(knifeBoard,knifeParts,knifeAssignments,[net("A"),net("B")]);
assert.equal(knife.stats.before.knife,1,"original knife reported");
assert.equal(knife.stats.after.knife,0,"endpoint relocation frees drillable hole");
assert.equal(knife.result.cuts[0].kind,"hole");
assert.notEqual(knife.result.wires[0].from.col,3);

const stackedBoard = {rows:4,cols:8,cuts:[],
  wires:[{from:{row:0,col:4},to:{row:3,col:4}},
         {from:{row:1,col:4},to:{row:2,col:4}}]};
const stackedParts = [comp("a",0,0),comp("b",3,0),comp("c",1,0),comp("d",2,0)];
const stackedAssignments = [a("a","A"),a("b","A"),a("c","B"),a("d","B")];
const stack = run(stackedBoard,stackedParts,stackedAssignments,[net("A"),net("B")]);
assert.equal(stack.stats.before.stacked,1,"original overlap seen");
assert.equal(stack.stats.after.stacked,0,"same-strip endpoints move to clean column");
assert.ok(stack.stats.columnsMoved > 0);

const slantBoard = {rows:3,cols:9,cuts:[],
  wires:[{from:{row:0,col:1},to:{row:2,col:7}}]};
const slantParts=[comp("a",0,0),comp("b",2,6)];
const slantAssignments=[a("a","A"),a("b","A")];
const slant=run(slantBoard,slantParts,slantAssignments,[net("A")]);
assert.equal(slant.stats.before.nonvertical,1);
assert.equal(slant.stats.after.nonvertical,0,"shared copper column straightens wire");

const untouched = run(knifeBoard,knifeParts,knifeAssignments,[net("A"),net("B")],false);
assert.deepEqual(untouched.result.wires,knifeBoard.wires,"disabled polish is identity");
assert.deepEqual(untouched.result.cuts,knifeBoard.cuts,"disabled polish cannot change cuts");

console.log("✅ Generic exact wire-column / drilled-hole polish: synthetic tests passed");
