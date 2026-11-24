// Independent saved-board strict audit, synthetic fixture with legal stacks.
const assert=require("node:assert/strict");
const {auditSavedStrict}=require("./auditSavedStrict.js");
const part=(id,row,col,locked=false)=>({
  id,defId:"audit-pin",label:id,rotation:0,boardPos:{row,col},locked,
  schematicPos:{x:0,y:0},schematicRotation:0,
});
const input={
  board:{rows:4,cols:7,lockedRows:true,lockedCols:true,cuts:[],wires:[]},
  components:[part("a",0,0,true),part("b",3,0),part("c",1,2),part("d",2,2)],
  componentDefs:[{id:"audit-pin",name:"Pin",category:"generic",symbol:"x",
    width:1,height:1,pins:[{id:"1",name:"1",offsetRow:0,offsetCol:0}]}],
  nets:[{id:"A",name:"A",color:"#f00"},{id:"B",name:"B",color:"#f00"}],
  netAssignments:[
    {componentId:"a",pinId:"1",netId:"A"},
    {componentId:"b",pinId:"1",netId:"A"},
    {componentId:"c",pinId:"1",netId:"B"},
    {componentId:"d",pinId:"1",netId:"B"},
  ],
};
const saved=JSON.parse(JSON.stringify(input));
saved.board.wires=[
  {from:{row:0,col:4},to:{row:3,col:4}},
  {from:{row:1,col:4},to:{row:2,col:4}},
];
// A and B are on different ROW strips and the jumper columns overlap
// physically but remain insulated; without the wire on column 4 neither
// net has a complete connection.
const result=auditSavedStrict(saved,input);
assert.equal(result.valid,true,JSON.stringify(result));
assert.equal(result.stacked,1);
// Saved legacy boards frequently omit Cut.kind: undefined means "between".
const implicitKnife=JSON.parse(JSON.stringify(saved));
implicitKnife.board.cuts=[{row:0,col:5}];
assert.equal(auditSavedStrict(implicitKnife,input).valid,true,
  "missing cut kind is a legal between-hole knife cut");
const explicitKnife=JSON.parse(JSON.stringify(saved));
explicitKnife.board.cuts=[{row:0,col:5,kind:"between"}];
assert.equal(auditSavedStrict(explicitKnife,input).valid,true,
  "explicit between-cut behaves identically to the implicit form");
const invalidKnife=JSON.parse(JSON.stringify(saved));
invalidKnife.board.cuts=[{row:0,col:6}];
assert.ok(auditSavedStrict(invalidKnife,input).failures.some(x=>x.startsWith("ILLEGAL_CUT")),
  "between cut after final column remains illegal");
const badCutKind=JSON.parse(JSON.stringify(saved));
badCutKind.board.cuts=[{row:0,col:5,kind:"mystery"}];
assert.ok(auditSavedStrict(badCutKind,input).failures.some(x=>x.startsWith("ILLEGAL_CUT")),
  "unknown kinds are never silently accepted");
const forbidden=auditSavedStrict(saved,input,true);
assert.equal(forbidden.valid,false);
assert.ok(forbidden.failures.some(f=>f.startsWith("STACKED_")));
const diagonal=JSON.parse(JSON.stringify(saved));
diagonal.board.wires[0].to.col=5;
assert.equal(auditSavedStrict(diagonal,input).valid,false);
const shifted=JSON.parse(JSON.stringify(saved));
shifted.components[0].boardPos.col=1;
assert.ok(auditSavedStrict(shifted,input).failures.some(f=>f.startsWith("LOCKED_PART_MOVED")));
const offBoard=JSON.parse(JSON.stringify(saved));
offBoard.board.wires[0].from.col=7;
assert.equal(auditSavedStrict(offBoard,input).valid,false);
const lostPin=JSON.parse(JSON.stringify(saved));
lostPin.components[1].boardPos=null;
assert.equal(auditSavedStrict(lostPin,input).valid,false);
console.log("✅ Independent saved-board strict audit: legal insulated stacks pass, errors fail");
