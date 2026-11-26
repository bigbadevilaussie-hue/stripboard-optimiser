#!/usr/bin/env node
// Read-only saved-board research. Does not run annealing or write archives.
// Usage: node scripts/sister_forensics.js /path/to/campaign [--all]
"use strict";
const fs=require("node:fs"), path=require("node:path"), zlib=require("node:zlib");
const assert=require("node:assert/strict");
const root=path.resolve(__dirname,"../src/frontend/tests/solver");
const out=path.join(root,"out/components/stripboard");
const {DEFAULT_COMPONENTS,verify,computeStripSegments,computeConnectivity,resolveComponentDef,boardLayout}=require(path.join(root,"helpers.js"));
const {expandOffBoard}=require(path.join(out,"offBoard.js"));
const {collectBoardPins,collectOccupiedHoles}=require(path.join(out,"boardPins.js"));
const {holeKey}=require(path.join(out,"keys.js"));
const {auditSavedStrict}=require(path.join(root,"auditSavedStrict.js"));
const [dir,mode]=process.argv.slice(2);
if (!dir || (mode && mode!=="--all")) throw Error("Usage: node scripts/sister_forensics.js CAMPAIGN [--all]");
const input=JSON.parse(fs.readFileSync(path.join(dir,"prepared_input.json"),"utf8"));
const queue=new Set([1,2,3,5,19,114,123,223,232,286,415,564,858]);
const key=p=>holeKey(p.row,p.col);
const bump=(m,k)=>m.set(k,(m.get(k)||0)+1);
const assigned=(as,c,p)=>as.find(a=>a.componentId===c.id&&a.pinId===p.pinId)?.netId;
function pinAccess(board,components,defs,as,target){
  const pins=collectBoardPins(board,components,defs,as);
  const occupied=collectOccupiedHoles(board,components,defs,pins);
  const segs=computeStripSegments(board,components,defs,as);
  const wires=board.wires.map((w,i)=>({...w,id:"diag"+i}));
  const groups=computeConnectivity(segs,wires,board);
  const def=resolveComponentDef(target,defs);
  return boardLayout.getComponentPinPositions(target,def).map(p=>{
    const si=segs.findIndex(s=>s.row===p.row&&s.startCol<=p.col&&s.endCol>=p.col);
    const s=segs[si];
    const g=groups.find(g=>g.segmentIndices.includes(si));
    const free=[];
    for(const i of g?.segmentIndices||[]){
      const t=segs[i];
      for(let col=t.startCol;col<=t.endCol;col++)
        if(!occupied.has(holeKey(t.row,col)))free.push({row:t.row,col});
    }
    const localFree=free.filter(h=>s&&h.row===s.row&&h.col>=s.startCol&&h.col<=s.endCol);
    return {pin:def.pins.find(d=>d.id===p.pinId)?.name||p.pinId,net:assigned(as,target,p),
      row:p.row,col:p.col,segment:s||null,localFree,groupFreeCount:free.length,
      wireEnds:board.wires.filter(w=>key(w.from)===key(p)||key(w.to)===key(p)).length,
      groupNets:g?.netIds||[],groupSegments:g?.segmentIndices.length||0};
  });
}
// An independent physical-hole graph for the ordinary horizontal copper board.
// This deliberately excludes drilled holes, rather than representing them as
// disconnected singleton segments as the repository helper does.
function graph(board,components,defs,as){
  if(board.pattern)throw Error("Patterned copper not supported by this diagnostic");
  const R=board.rows,C=board.cols,N=R*C;
  const parent=Array.from({length:N},(_,i)=>i);
  const at=p=>p.row*C+p.col;
  const inside=p=>Number.isInteger(p.row)&&Number.isInteger(p.col)&&p.row>=0&&p.row<R&&p.col>=0&&p.col<C;
  const removed=new Set(),cutRight=new Set();
  for(const c of board.cuts){
    if(!inside(c))throw Error("Off-board cut");
    if(c.kind==="hole")removed.add(at(c));
    else if((c.kind??"between")==="between"&&c.col<C-1)cutRight.add(at(c));
    else throw Error("Unsupported cut");
  }
  const find=x=>{while(parent[x]!==x){parent[x]=parent[parent[x]];x=parent[x];}return x;};
  function union(a,b){a=find(a);b=find(b);if(a===b)return false;parent[b]=a;return true;}
  let copper=N-removed.size;
  for(let row=0;row<R;row++)for(let col=0;col<C-1;col++){
    const i=row*C+col;
    if(!removed.has(i)&&!removed.has(i+1)&&!cutRight.has(i)&&union(i,i+1))copper--;
  }
  let effective=0,invalidWires=0;
  for(const w of board.wires){
    if(!inside(w.from)||!inside(w.to)||removed.has(at(w.from))||removed.has(at(w.to))){invalidWires++;continue;}
    if(union(at(w.from),at(w.to)))effective++;
  }
  const groups=new Map();
  for(let i=0;i<N;i++)if(!removed.has(i))groups.set(find(i),new Set());
  const pins=collectBoardPins(board,components,defs,as);
  let invalidPins=0;
  for(const p of pins){
    if(removed.has(at(p))){invalidPins++;continue;}
    if(p.netId)groups.get(find(at(p))).add(p.netId);
  }
  const incidence=new Map();let empty=0,excess=0;
  for(const ns of groups.values()){
    if(!ns.size)empty++;
    excess+=Math.max(0,ns.size-1);
    for(const n of ns)bump(incidence,n);
  }
  const deficit=[...incidence.values()].reduce((s,n)=>s+Math.max(0,n-1),0);
  assert.equal(groups.size,copper-effective);
  assert.equal(groups.size,incidence.size+deficit+empty-excess);
  return {copper,effective,invalidWires,invalidPins,groups:groups.size,
    presentNets:incidence.size,emptyGroups:empty,multiNetExcess:excess,deficit,
    cutAdjustment:R+board.cuts.length-copper,
    wireAdjustment:board.wires.length-effective};
}
function synthetic(){
  const gps=input.components.find(c=>c.label==="GPS");
  assert(gps,"Missing GPS fixture");
  const defs=[...DEFAULT_COMPONENTS,...(input.componentDefs||[])];
  const as=input.netAssignments.filter(a=>a.componentId===gps.id);
  const rows=[];
  for(const rotation of [0,90,180,270]){
    const c={...gps,rotation,boardPos:{row:8,col:8},locked:false};
    const board={rows:32,cols:56,cuts:[],wires:[]};
    const pins=collectBoardPins(board,[c],defs,as).sort((a,b)=>a.row-b.row||a.col-b.col);
    for(let i=1;i<pins.length;i++){
      const a=pins[i-1],b=pins[i];
      if(a.row===b.row&&b.col===a.col+1&&a.netKey!==b.netKey)
        board.cuts.push({row:a.row,col:a.col});
    }
    const access=pinAccess(board,[c],defs,as,c);
    for(const pin of access.filter(p=>p.pin==="RX"||p.pin==="TX")){
      const horizontal=rotation===0||rotation===180;
      assert(pin.segment,"Pin has no copper segment");
      if(horizontal){
        assert.equal(pin.segment.startCol,pin.segment.endCol);
        assert.equal(pin.localFree.length,0);
      }else assert(pin.localFree.length>0);
    }
    rows.push({rotation,cuts:board.cuts,pins:access.map(p=>({pin:p.pin,row:p.row,col:p.col,segment:p.segment,localFree:p.localFree.length}))});
  }
  return rows;
}
console.log(JSON.stringify({syntheticRotationProof:synthetic()},null,2));
const names=fs.readdirSync(path.join(dir,"candidates")).filter(n=>/^seed_\d+\.json\.gz$/.test(n)).sort();
const rotations=new Map(),netPairs=new Map(),graphPatterns=new Map();
let examined=0,errors=0;
for(const file of names){
  const seed=Number(file.match(/\d+/)[0]);
  if(mode!=="--all"&&!queue.has(seed))continue;
  try{
    const saved=JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(dir,"candidates",file))));
    const defs=[...DEFAULT_COMPONENTS,...(saved.componentDefs||[])];
    const v=expandOffBoard(saved.components,defs,saved.netAssignments);
    const b=saved.board,gps=v.components.find(c=>c.label==="GPS");
    assert(gps?.boardPos,"GPS unplaced or absent");
    const e=verify(b,v.components,saved.nets,v.netAssignments,defs);
    const a=auditSavedStrict(saved,input,false);
    const p=pinAccess(b,v.components,defs,v.netAssignments,gps);
    const gr=graph(b,v.components,defs,v.netAssignments);
    const names=e.incomplete.map(n=>n.netName).sort();
    bump(rotations,JSON.stringify({rotation:gps.rotation,incomplete:e.incomplete.length,gpsPair:names.includes("net25")&&names.includes("net29"),strict:a.valid}));
    bump(netPairs,JSON.stringify(names));
    const residual=b.rows+b.cuts.length-b.wires.length-e.incomplete.length;
    const explained=gr.presentNets+gr.emptyGroups-gr.multiNetExcess+(gr.deficit-e.incomplete.length)+gr.cutAdjustment-gr.wireAdjustment;
    assert.equal(residual,explained);
    bump(graphPatterns,JSON.stringify({residual,...gr}));
    examined++;
    if(queue.has(seed))console.log(JSON.stringify({seed,board:[b.rows,b.cols],rotation:gps.rotation,
      position:gps.boardPos,failures:a.failures,incomplete:e.incomplete,pins:p,graph:gr,residual,explained},null,2));
  }catch(e){errors++;console.error("ERROR",file,e.stack||String(e));}
}
const sorted=m=>[...m].sort((a,b)=>b[1]-a[1]).map(([k,n])=>({n,...{signature:JSON.parse(k)}}));
console.log(JSON.stringify({summary:{examined,errors,mode:mode||"queue",archiveSnapshot:names.length},
  rotations:sorted(rotations),incompleteSignatures:sorted(netPairs),graphPatterns:sorted(graphPatterns).slice(0,30)},null,2));
if(errors)process.exitCode=1;
