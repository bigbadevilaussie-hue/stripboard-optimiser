// Independent saved-board strict audit, synthetic fixture with legal stacks.
const assert=require("node:assert/strict");
const {auditSavedStrict}=require("./auditSavedStrict.js");
const {preserveInputLockMetadata}=require("./preserveInputLockMetadata.js");
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
// Native blankComps clears "locked" from MOVABLE components, even when the
// original JSON explicitly contained locked:false. Without restoration, a
// genuinely strict valid candidate is falsely rejected as a definition edit.
const sanitisedNative=JSON.parse(JSON.stringify(saved));
delete sanitisedNative.components[1].locked;
const nativeRejection=auditSavedStrict(sanitisedNative,input);
assert.equal(nativeRejection.valid,false);
assert.ok(nativeRejection.failures.includes("COMPONENT_DEFINITION_CHANGED_b_locked"));
const restoredNative={
  ...sanitisedNative,
  components:preserveInputLockMetadata(input.components,sanitisedNative.components),
};
assert.equal(restoredNative.components[1].locked,false);
assert.equal(auditSavedStrict(restoredNative,input).valid,true,
  "native strict-valid board must survive saved-JSON metadata normalisation");
assert.deepEqual(restoredNative.board,sanitisedNative.board,
  "restoring metadata cannot alter cuts, jumpers or positions");

// Preserve the distinction between ABSENT and false for original inputs.
const sourceWithoutFlag=JSON.parse(JSON.stringify(input));
delete sourceWithoutFlag.components[1].locked;
const writtenWithFalse=JSON.parse(JSON.stringify(saved));
writtenWithFalse.components[1].locked=false;
const restoredAbsent={
  ...writtenWithFalse,
  components:preserveInputLockMetadata(sourceWithoutFlag.components,
    writtenWithFalse.components),
};
assert.equal(Object.hasOwn(restoredAbsent.components[1],"locked"),false);
assert.equal(auditSavedStrict(restoredAbsent,sourceWithoutFlag).valid,true);

// Do not relax the independent gates: a moved locked part and diagonal jumper
// remain invalid even after the only allowed lock-metadata restoration.
const movedLocked=JSON.parse(JSON.stringify(restoredNative));
movedLocked.components[0].boardPos.col=1;
assert.ok(auditSavedStrict(movedLocked,input).failures.some(
  x=>x.startsWith("LOCKED_PART_MOVED_")));
const badWire=JSON.parse(JSON.stringify(restoredNative));
badWire.board.wires[0].to.col=5;
assert.ok(auditSavedStrict(badWire,input).failures.some(
  x=>x.startsWith("NONVERTICAL_")));

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
