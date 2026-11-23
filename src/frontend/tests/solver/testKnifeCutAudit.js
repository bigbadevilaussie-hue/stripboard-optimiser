// Synthetic tests for generic knife diagnostics, without MOTOEX-specific data.
const assert = require("node:assert/strict");
const { auditKnifeCuts } = require("./knifeCutAudit.js");
const def = {
  id:"pair", name:"Generic pair", category:"connector", symbol:"P",
  width:2, height:1,
  pins:[{id:"A",name:"A",offsetRow:0,offsetCol:0},
        {id:"B",name:"B",offsetRow:0,offsetCol:1}],
};
const component = {
  id:"pair1",defId:"pair",label:"P1",boardPos:{row:1,col:2},rotation:0,
  schematicPos:{x:0,y:0},schematicRotation:0,
};
const nets = [{id:"red",name:"RED"},{id:"blue",name:"BLUE"}];
const board = {rows:3,cols:8,cuts:[{row:1,col:2}],wires:[]};
const asg = [{componentId:"pair1",pinId:"A",netId:"red"},
             {componentId:"pair1",pinId:"B",netId:"blue"}];
let cuts = auditKnifeCuts(board,[component],[def],asg,nets);
assert.equal(cuts.length,1);
assert.equal(cuts[0].forcedByAdjacentPins,true);
assert.equal(cuts[0].nearestLeft.net,"RED");
assert.equal(cuts[0].nearestRight.net,"BLUE");
assert.equal(cuts[0].flanks.filter(x=>x.basicDrillCandidate).length,0);

cuts = auditKnifeCuts(board,[component],[def],
  asg.map(a=>({...a,netId:"red"})),nets);
assert.equal(cuts[0].forcedByAdjacentPins,false,
  "adjacent pins on same net must not be called forced");

const spaced = {...component,boardPos:{row:1,col:0}};
const wide = {...def,width:5,pins:[def.pins[0],{...def.pins[1],offsetCol:4}]};
const spacedBoard = {...board,cuts:[{row:1,col:2}]};
cuts = auditKnifeCuts(spacedBoard,[spaced],[wide],asg,nets);
assert.equal(cuts[0].forcedByAdjacentPins,false);
assert.equal(cuts[0].flanks.filter(x=>x.basicDrillCandidate).length,2);
const withWire = {...spacedBoard,wires:[{from:{row:1,col:2},to:{row:2,col:2}}]};
cuts = auditKnifeCuts(withWire,[spaced],[wide],asg,nets);
assert.equal(cuts[0].flanks[0].basicDrillCandidate,false);
assert.deepEqual(cuts[0].flanks[0].wireEndpoints,[1]);

const unassigned = auditKnifeCuts(board,[component],[def],
  [{componentId:"pair1",pinId:"A",netId:"red"}],nets);
assert.equal(unassigned[0].forcedByAdjacentPins,true);
console.log("✅ Generic knife-cut diagnostics: synthetic tests passed");
