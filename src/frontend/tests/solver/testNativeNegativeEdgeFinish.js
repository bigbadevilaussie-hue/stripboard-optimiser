// End-to-end native Edge finish gate regression for negative locked BMS.
// Requires: npm run build:solver && npm run build:native && npm run build:native:edge
// This checks the TS final-physical-fit gate, not just C decoder placement.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const sourcePath = path.join(__dirname, "../../../../test-fixtures/masters/audio/audioex.json");
const source = JSON.parse(fs.readFileSync(sourcePath, "utf8"));
const bms = source.components.find(c => c.label === "BMS");
assert.ok(bms);
assert.deepEqual(bms.boardPos, {row:-2,col:24});
const trial = {
  ...source,
  board: {...source.board, cuts:[], wires:[], lockedRows:true, lockedCols:true},
  components: [{...bms, edge:true, slide:false, locked:true}],
  netAssignments: source.netAssignments.filter(a => a.componentId === bms.id),
};
const temp = fs.mkdtempSync(path.join(os.tmpdir(),"audioex-edge-finish-"));
try {
  const folder = path.join(temp,"input","projects");
  fs.mkdirSync(folder,{recursive:true});
  fs.writeFileSync(path.join(folder,"1.json"), JSON.stringify(trial));
  const savedPath=path.join(temp,"saved.json");
  const proc=spawnSync(process.execPath,[
    path.join(__dirname,"v5Solve.js"), "--data",path.join(temp,"input"),
    "--id","1","--seed","1","--moves","5000",
    "--native","1","--strict","1","--drilled","0","--nostack","0",
    "--drill-domain","0","--wire-polish","0",
    "--routing-preference","wires","--save",savedPath,
  ],{
    cwd:path.join(__dirname,"../.."),
    env:{...process.env,V5_NATIVE_LIB_DIR:path.join(__dirname,"native/build/edge")},
    encoding:"utf8",timeout:120000,
  });
  assert.ok(proc.status===0 || proc.status===2,
    "Unexpected native CLI failure: "+proc.status+" "+proc.stderr);
  const results=proc.stdout.split("\n").filter(s=>s.startsWith("{"));
  assert.ok(results.length, "Missing JSON diagnostic: "+proc.stdout);
  const result=JSON.parse(results[results.length-1]);
  assert.notEqual(result.unsolvedReason,"NO_FEASIBLE_PLACEMENT",
    "Native decoder must find an in-board anchored arrangement for this isolated BMS");
  assert.notEqual(result.unsolvedReason,"NO_PHYSICAL_FINISH",
    "TS physicalFit must not reject BMS body-only negative anchor");
  assert.ok(fs.existsSync(savedPath), "Missing saved diagnostic board");
  const saved=JSON.parse(fs.readFileSync(savedPath,"utf8"));
  const actual=saved.components.find(c=>c.id===bms.id);
  assert.ok(actual, "Saved BMS missing");
  assert.deepEqual(actual.boardPos,{row:-2,col:24});
  assert.equal(actual.locked,true);
  assert.equal(actual.edge,true);
  assert.equal(actual.slide,false);
  assert.equal(saved.board.rows,24);
  assert.equal(saved.board.cols,56);
  console.log("✅ Native AUDIOEX BMS finish gate: negative locked body anchor preserved");
} finally {
  fs.rmSync(temp,{recursive:true,force:true});
}
