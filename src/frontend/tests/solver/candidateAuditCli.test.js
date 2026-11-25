"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const {spawnSync} = require("node:child_process");

const cwd = __dirname;
const pin = (id,row) => ({
  id,defId:"candidate-pin",label:id,rotation:0,boardPos:{row,col:0},
  schematicPos:{x:0,y:0},schematicRotation:0,
});
const input={
  board:{rows:4,cols:7,lockedRows:true,lockedCols:true,cuts:[],wires:[]},
  components:[pin("a",0),pin("b",3)],
  componentDefs:[{id:"candidate-pin",name:"Pin",category:"generic",
    symbol:"x",width:1,height:1,pins:[{id:"1",name:"1",offsetRow:0,offsetCol:0}]}],
  nets:[{id:"A",name:"A",color:"#f00"}],
  netAssignments:[{componentId:"a",pinId:"1",netId:"A"},
    {componentId:"b",pinId:"1",netId:"A"}],
};

const dir=fs.mkdtempSync(path.join(os.tmpdir(),"candidate-audit-cli-"));
try {
  const inp=path.join(dir,"input.json"), saved=path.join(dir,"saved.json");
  fs.writeFileSync(inp,JSON.stringify(input));
  const diagonal=JSON.parse(JSON.stringify(input));
  diagonal.board.wires=[{from:{row:0,col:4},to:{row:3,col:5}}];
  fs.writeFileSync(saved,JSON.stringify(diagonal));
  const call=(extra)=>spawnSync(process.execPath,[
    path.join(cwd,"auditSavedStrict.js"),saved,inp,...extra,
  ],{encoding:"utf8",cwd});
  const strict=call([]);
  assert.equal(strict.status,2,strict.stderr);
  const strictData=JSON.parse(strict.stdout);
  assert.equal(strictData.valid,false);
  assert.equal(Object.hasOwn(strictData,"candidate"),false,"legacy JSON unchanged");

  const policy=call(["--candidate-policy","diagonal"]);
  assert.equal(policy.status,0,policy.stderr);
  const selected=JSON.parse(policy.stdout);
  assert.equal(selected.valid,false,"cannot claim a diagonal is build-ready");
  assert.equal(selected.candidate.status,"DIAG_PASS");
  assert.equal(selected.candidate.qualified,true);

  const rejected=call(["--candidate-policy","strict"]);
  assert.equal(rejected.status,2);
  assert.equal(JSON.parse(rejected.stdout).candidate.qualified,false);

  const invalidArg=call(["--candidate-policy","whatever"]);
  assert.equal(invalidArg.status,64);
  const nativeInvalid=spawnSync(process.execPath,[
    path.join(cwd,"v5Solve.js"),"--data",dir,"--id","1",
    "--strict","1","--candidate-policy","whatever",
  ],{encoding:"utf8",cwd});
  assert.equal(nativeInvalid.status,64,nativeInvalid.stderr);
  const nativeNeedsStrict=spawnSync(process.execPath,[
    path.join(cwd,"v5Solve.js"),"--data",dir,"--id","1",
    "--candidate-policy","diagonal",
  ],{encoding:"utf8",cwd});
  assert.equal(nativeNeedsStrict.status,64,nativeNeedsStrict.stderr);

  const incomplete=JSON.parse(JSON.stringify(input));
  fs.writeFileSync(saved,JSON.stringify(incomplete));
  const impossible=call(["--candidate-policy","archive"]);
  assert.equal(impossible.status,2,impossible.stderr);
  assert.equal(JSON.parse(impossible.stdout).candidate.qualified,false);
} finally {
  fs.rmSync(dir,{recursive:true,force:true});
}
console.log("✅ Saved audit CLI: strict exit unchanged, diagonal acceptance, hard failures and bad flags");
