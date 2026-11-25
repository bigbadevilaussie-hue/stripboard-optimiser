"use strict";
const assert = require("node:assert/strict");
const { classifySavedAudit, classifyNativeDiagnostic, assertPolicy } = require("./candidatePolicy.js");
const { auditSavedStrict } = require("./auditSavedStrict.js");

const fake = (failures = []) => ({
  valid: failures.length === 0,
  failures,
  nonvertical: Number((failures.find((x) => x.startsWith("NONVERTICAL_")) ?? "0_0").split("_").at(-1)),
  crossings: Number((failures.find((x) => x.startsWith("BODY_CROSSINGS_")) ?? "0_0").split("_").at(-1)),
});
const strict = classifySavedAudit(fake(), "strict");
assert.equal(strict.status, "STRICT_PASS");
assert.equal(strict.buildReady, true);
assert.equal(strict.qualified, true);

const diagonal = fake(["NONVERTICAL_3"]);
assert.equal(classifySavedAudit(diagonal, "strict").qualified, false);
assert.deepEqual(
  [classifySavedAudit(diagonal, "diagonal").status,
    classifySavedAudit(diagonal, "diagonal").qualified],
  ["DIAG_PASS", true]
);
assert.equal(classifySavedAudit(diagonal, "diagonal").buildReady, false);

const crossing = fake(["NONVERTICAL_2", "BODY_CROSSINGS_6"]);
assert.equal(classifySavedAudit(crossing, "diagonal").qualified, false);
assert.equal(classifySavedAudit(crossing, "crossings").qualified, true);
assert.equal(classifySavedAudit(crossing, "crossings").status, "ROUTE_CANDIDATE");
assert.equal(classifySavedAudit(crossing, "archive").buildReady, false);

for (const problems of [
  ["INCOMPLETE_3", "NONVERTICAL_1"],
  ["CONFLICTS_1", "NONVERTICAL_1"],
  ["LOCKED_BOARD_CHANGED", "NONVERTICAL_1"],
  ["WIRE_OFF_BOARD_1", "NONVERTICAL_1"],
  ["PROJECT_NETLIST_OR_DEFINITIONS_CHANGED", "NONVERTICAL_1"],
  ["GEOMETRY_1", "NONVERTICAL_1"],
  ["UNPLACED_1", "NONVERTICAL_1"],
  ["MISSING_COMPONENT_a", "NONVERTICAL_1"],
  ["STACKED_1", "NONVERTICAL_1"],
  ["UNRECOGNISED_REASON", "NONVERTICAL_1"],
]) {
  const result = classifySavedAudit(fake(problems), "archive");
  assert.equal(result.qualified, false, problems.join(", "));
  assert.equal(result.archiveOnly, true);
  assert.equal(result.buildReady, false);
}
assert.equal(classifySavedAudit({valid:true,failures:["NONVERTICAL_1"],nonvertical:1,crossings:0},"diagonal").qualified,false);
assert.equal(classifySavedAudit({valid:false,failures:[],nonvertical:0,crossings:0},"diagonal").status,"AUDIT_ERROR");
assert.equal(classifySavedAudit({valid:false,failures:["NONVERTICAL_1"],nonvertical:0,crossings:0},"diagonal").status,"AUDIT_ERROR");
assert.equal(classifySavedAudit(null,"diagonal").status,"AUDIT_ERROR");
assert.throws(() => assertPolicy("anything"), RangeError);

const native = classifyNativeDiagnostic({
  strictValid:false,
  strictFailures:["NONVERTICAL_3","SLANTED_3","CROSSINGS_4","SOLVER_ISSUES"],
},"crossings");
assert.equal(native.prequalified,true);
assert.equal(native.needsSavedAudit,true);
assert.equal(classifyNativeDiagnostic({
  strictValid:false,strictFailures:["NONVERTICAL_3","SLANTED_3","CROSSINGS_4","SOLVER_ISSUES"],
},"diagonal").prequalified,false);
assert.equal(classifyNativeDiagnostic({
  strictValid:false,strictFailures:["INCOMPLETE_3","NONVERTICAL_3","SOLVER_ISSUES"],
},"archive").prequalified,false);

// Real copper connectivity fixture: diagonal link between two different
// copper rows, no body collision, 2 pins of the same net.
const p=(id,row)=>({ id,defId:"policy-pin",label:id,rotation:0,
  boardPos:{row,col:0},schematicPos:{x:0,y:0},schematicRotation:0 });
const input={
  board:{rows:4,cols:7,lockedRows:true,lockedCols:true,cuts:[],wires:[]},
  components:[p("a",0),p("b",3)],
  componentDefs:[{id:"policy-pin",name:"Pin",category:"generic",symbol:"x",
    width:1,height:1,pins:[{id:"1",name:"1",offsetRow:0,offsetCol:0}]}],
  nets:[{id:"A",name:"A",color:"#f00"}],
  netAssignments:[{componentId:"a",pinId:"1",netId:"A"},
    {componentId:"b",pinId:"1",netId:"A"}],
};
const saved=JSON.parse(JSON.stringify(input));
saved.board.wires=[{from:{row:0,col:4},to:{row:3,col:5}}];
const audited=auditSavedStrict(saved,input);
assert.equal(audited.valid,false,"diagonal remains non-build-ready");
assert.deepEqual(audited.failures,["NONVERTICAL_1"],JSON.stringify(audited));
assert.equal(classifySavedAudit(audited,"strict").qualified,false);
assert.equal(classifySavedAudit(audited,"diagonal").qualified,true);
const incomplete=JSON.parse(JSON.stringify(saved));
incomplete.board.wires=[];
assert.equal(classifySavedAudit(auditSavedStrict(incomplete,input),"crossings").qualified,false);

console.log("✅ Candidate policies: strict / diagonal / crossings / archive, hard blockers, native prefilter, real diagonal audit");
