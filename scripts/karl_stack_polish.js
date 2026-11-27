#!/usr/bin/env node
"use strict";
// Isolated strict stack-polish experiment. Original boards stay immutable.
// Geometry and graph helpers copied from the proven Karl autopsy at 11ec46f.
// No native search, no renderer rebuild, no production integration.
const fs=require("node:fs"),path=require("node:path"),zlib=require("node:zlib"),crypto=require("node:crypto");
const {performance}=require("node:perf_hooks");
const repo=path.resolve(__dirname,".."),base=path.join(repo,"src/frontend/tests/solver");
const {auditSavedStrict}=require(path.join(base,"auditSavedStrict.js"));
const {DEFAULT_COMPONENTS,resolveComponentDef,boardLayout,partGeometry,flexGeometry,computeStripSegments}=require(path.join(base,"helpers.js"));
const {expandOffBoard}=require(path.join(base,"out/components/stripboard/offBoard.js"));
const {collectBoardPins,collectOccupiedHoles}=require(path.join(base,"out/components/stripboard/boardPins.js"));
const key=p=>p.row+","+p.col,read=p=>JSON.parse(fs.readFileSync(p,"utf8"));
const sha=x=>crypto.createHash("sha256").update(x).digest("hex");
const q3=b=>{
  const ws=b.board.wires, cs=b.board.cuts, cover=new Map();
  let len=0,d=0,s=ws.length?1:0;
  for(const w of ws){
    len+=Math.hypot(w.from.row-w.to.row,w.from.col-w.to.col)*2.54;
    if(w.from.col!==w.to.col){d++;continue;}
    for(let r=Math.min(w.from.row,w.to.row);r<Math.max(w.from.row,w.to.row);r++){
      const k=r+","+w.from.col,n=(cover.get(k)||0)+1;cover.set(k,n);s=Math.max(s,n);
    }
  }
  const u=b.components.filter(c=>!c.offBoard&&!c.boardExcluded&&(!c.boardPos||typeof c.boardPos!=="object"||Array.isArray(c.boardPos))).length;
  return {q:Math.round(Math.max(0,100-.4*(.6*ws.length+.4*cs.length+.02*len+10*d+15*u+Math.max(0,s-1)**2))*100)/100,w:ws.length,c:cs.length,s,len};
};
function context(b){
  const defs=[...DEFAULT_COMPONENTS,...(b.componentDefs||[])];
  const v=expandOffBoard(b.components,defs,b.netAssignments||[]);
  const pins=collectBoardPins(b.board,v.components,defs,v.netAssignments);
  const occupied=collectOccupiedHoles(b.board,v.components,defs,pins);
  const rects=[],bodies=[];
  for(const c of v.components){
    if(!c.boardPos||c.boardExcluded)continue;
    const d=resolveComponentDef(c,defs);if(!d)throw Error("Missing definition");
    if(d.flexible){const [a,z]=boardLayout.getFlexiblePinPositions(c,d);if(a&&z)bodies.push(partGeometry.flexWireObstacle(d,a,z));}
    else rects.push(partGeometry.rigidBody(d,c.boardPos,c.rotation));
  }
  const cross=w=>rects.reduce((n,r)=>n+Number(flexGeometry.segmentIntersectsRect(w.from,w.to,r)),0)+bodies.reduce((n,x)=>n+Number(flexGeometry.wireCrossesBody(w.from,w.to,x)),0);
  const segments=computeStripSegments(b.board,v.components,defs,v.netAssignments);
  const at=p=>segments.findIndex(s=>s.row===p.row&&s.startCol<=p.col&&p.col<=s.endCol);
  return {pins,occupied,cross,segments,at};
}
// Independent horizontal copper graph. Uses repo pin transforms only.
// A drilled hole is REMOVED, not modelled as a singleton conductor.
function physicalGraph(b,pins){
  const {rows:R,cols:C,cuts,wires,pattern}=b.board;
  if(pattern)return {unsupported:"custom copper pattern"};
  const n=R*C,parent=Array.from({length:n},(_,i)=>i),dr=new Set(),kn=new Set(),bad=[];
  const inside=p=>Number.isInteger(p.row)&&Number.isInteger(p.col)&&p.row>=0&&p.row<R&&p.col>=0&&p.col<C;
  const idx=p=>p.row*C+p.col;
  const root=i=>{while(parent[i]!==i){parent[i]=parent[parent[i]];i=parent[i];}return i;};
  const join=(a,z)=>{a=root(a);z=root(z);if(a!==z)parent[a]=z;};
  for(const c of cuts){if(!inside(c)){bad.push("cut outside board");continue;}if(c.kind==="hole")dr.add(idx(c));else if(c.kind==null||c.kind==="between"){if(c.col>=C-1)bad.push("knife outside copper");else kn.add(idx(c));}else bad.push("unsupported cut kind");}
  for(let r=0;r<R;r++)for(let c=0;c<C-1;c++){const i=r*C+c;if(!dr.has(i)&&!dr.has(i+1)&&!kn.has(i))join(i,i+1);}
  for(const w of wires){
    if(!inside(w.from)||!inside(w.to)){bad.push("wire outside board");continue;}
    const a=idx(w.from),z=idx(w.to);
    if(dr.has(a)||dr.has(z)){bad.push("wire on drilled hole");continue;}join(a,z);
  }
  const byNet=new Map(),byRoot=new Map();
  for(const p of pins){
    if(!inside(p)||dr.has(idx(p))){bad.push("pin on absent copper");continue;}
    if(p.netId==null)continue;
    const r=root(idx(p));
    if(!byNet.has(p.netId))byNet.set(p.netId,new Set());
    if(!byRoot.has(r))byRoot.set(r,new Set());
    byNet.get(p.netId).add(r);byRoot.get(r).add(p.netId);
  }
  const split=[...byNet].filter(([,s])=>s.size>1).map(([n,s])=>({net:n,groups:s.size}));
  const shorts=[...byRoot.values()].filter(s=>s.size>1).map(s=>[...s]);
  return {bad,split,shorts,complete:bad.length===0&&split.length===0&&shorts.length===0};
}

// Lexicographic potential: maximum stack depth, then overlapping edge-pairs.
// Strictly decreasing potential permits plateau moves without cycling.
// Only move a wire between its original two copper strips.
function stackCost(wires){
  const cover=new Map();
  let depth=wires.length?1:0,pairs=0;
  for(const w of wires){
    if(w.from.col!==w.to.col||w.from.row===w.to.row)throw Error("Nonvertical wire in strict polish");
    for(let row=Math.min(w.from.row,w.to.row);row<Math.max(w.from.row,w.to.row);row++){
      const k=row+","+w.from.col,n=cover.get(k)||0;
      pairs+=n;cover.set(k,n+1);depth=Math.max(depth,n+1);
    }
  }
  return {depth,pairs};
}
const less=(a,b)=>a.depth<b.depth||(a.depth===b.depth&&a.pairs<b.pairs);
function polish(wires,ctx,maxMoves=64){
  let current=wires.slice(),cost=stackCost(current),steps=[],checks=0;
  while(steps.length<maxMoves&&cost.depth>1){
    let best=null;
    for(let i=0;i<current.length;i++){
      const w=current[i],a=ctx.at(w.from),z=ctx.at(w.to);
      if(a<0||z<0)throw Error("Missing original strip");
      const A=ctx.segments[a],Z=ctx.segments[z];
      const used=new Set(current.flatMap((x,j)=>i===j?[]:[key(x.from),key(x.to)]));
      const free=p=>!ctx.occupied.has(key(p))&&!used.has(key(p));
      for(let c=Math.max(A.startCol,Z.startCol);c<=Math.min(A.endCol,Z.endCol);c++){
        if(c===w.from.col)continue;
        const from={row:w.from.row,col:c},to={row:w.to.row,col:c};
        if(!free(from)||!free(to)||ctx.cross({from,to}))continue;
        const nw={...w,from,to},next=current.map((x,j)=>i===j?nw:x);
        checks++;
        const trial=stackCost(next);
        if(!less(trial,cost))continue;
        const shift=Math.abs(c-w.from.col);
        if(!best||less(trial,best.cost)||
          (trial.depth===best.cost.depth&&trial.pairs===best.cost.pairs&&shift<best.shift)){
          best={i,old:w,new:nw,wires:next,cost:trial,shift};
        }
      }
    }
    if(!best)break;
    steps.push({i:best.i,old:best.old,new:best.new,before:cost,after:best.cost});
    current=best.wires;cost=best.cost;
  }
  return {wires:current,cost,steps,checks,capHit:steps.length===maxMoves&&cost.depth>1};
}
function testPolish(){
  const segs=Array.from({length:7},(_,row)=>({row,startCol:0,endCol:4}));
  const ctx={at:p=>p.row,segments:segs,occupied:new Set(),cross:()=>false};
  const w=(id,a,b,c)=>({id,from:{row:a,col:c},to:{row:b,col:c}});
  const input=[w("a",0,6,1),w("b",1,5,1),w("c",2,4,1)];
  const before=JSON.stringify(input);
  const p=polish(input,ctx);
  if(p.cost.depth!==1||p.steps.length!==2||JSON.stringify(input)!==before)throw Error("Three-to-one stack test");
  if(JSON.stringify(p)!==JSON.stringify(polish(input,ctx)))throw Error("Determinism test");
  const blocked={...ctx,cross:x=>x.from.col!==1};
  if(polish(input,blocked).steps.length!==0)throw Error("Obstacle test");
  if(polish(input,ctx,1).cost.depth!==2)throw Error("Move cap test");
  const touch=[w("a",0,2,0),w("b",2,4,0)];
  if(stackCost(touch).depth!==1||polish(touch,ctx).steps.length)throw Error("Touching endpoint test");
}

testPolish();
if(process.argv.length!==3)throw Error("Usage: node scripts/karl_stack_polish.js NEW_OUTPUT_DIRECTORY");
const out=path.resolve(process.argv[2]),archive=path.join(repo,"research/karl-autopsy/20261127"),arena=path.join(repo,"research/mortal-kombat");
const inp=path.join(archive,"prepared_input.json"),input=read(inp),verification=read(path.join(archive,"verification.json")),manifest=read(path.join(arena,"manifest.json"));
const fingerprint=require("node:child_process").execFileSync(process.env.KARL_PYTHON||"python3",["-c","import hashlib,json,sys; print(hashlib.sha256(json.dumps(json.load(open(sys.argv[1])),sort_keys=True,ensure_ascii=False).encode('utf-8')).hexdigest())",inp],{encoding:"utf8"}).trim();
if(fingerprint!==manifest.input||fingerprint!==verification.input_sha256)throw Error("Prepared input mismatch");
fs.mkdirSync(out);
console.log("✅ Stack polish synthetic tests and prepared input fingerprint passed");
const results=[],counts={original:0,witness:0,improvedOriginal:0,improvedWitness:0,plateauOnly:0,fallback:0,capHit:0};
function saveReport(){
  fs.writeFileSync(path.join(out,"report.tmp"),JSON.stringify({inputFingerprint:fingerprint,counts,results},null,2)+"\n");
  fs.renameSync(path.join(out,"report.tmp"),path.join(out,"report.json"));
}
function run(b,info){
  const started=performance.now(),before=q3(b),ctx=context(b),oldAudit=auditSavedStrict(b,input,false);
  if(!oldAudit.valid||!physicalGraph(b,ctx.pins).complete||Math.abs(before.q-info.expectedQ)>0.011)throw Error("Baseline mismatch "+JSON.stringify(info));
  if(b.board.rows!==24||b.board.cols!==56||b.board.pattern)throw Error("Unsupported board");
  const p=polish(b.board.wires,ctx),candidate={...b,board:{...b.board,wires:p.wires}},after=q3(candidate);
  if(before.w!==after.w||before.c!==after.c||Math.abs(before.len-after.len)>1e-7||after.s>before.s)throw Error("Polish invariant");
  const changed=after.q>before.q;
  const audit=changed?auditSavedStrict(candidate,input,false):oldAudit;
  const graph=changed?physicalGraph(candidate,ctx.pins):physicalGraph(b,ctx.pins);
  const accept=changed&&audit.valid&&graph.complete;
  if(changed&&!accept)counts.fallback++;
  if(!changed&&p.steps.length)counts.plateauOnly++;
  if(p.capHit)counts.capHit++;
  counts[info.cohort]++;
  const result={...info,before,after:accept?after:before,attempted:after,beforeCost:stackCost(b.board.wires),afterCost:p.cost,steps:p.steps,checks:p.checks,capHit:p.capHit,accepted:accept,audit:accept?audit:oldAudit,attemptAudit:changed?audit:null,wall_ms:performance.now()-started};
  if(accept){
    counts[info.cohort==="original"?"improvedOriginal":"improvedWitness"]++;
    result.saved=info.name+".json";
    fs.writeFileSync(path.join(out,result.saved),JSON.stringify(candidate,null,2)+"\n");
  }
  results.push(result);saveReport();
  console.log(accept?"💥":"🔬",info.name,"Q"+before.q.toFixed(2)+" → Q"+result.after.q.toFixed(2),"S"+before.s+" → S"+result.after.s,"moves",p.steps.length,"checks",p.checks);
}
for(const moves of manifest.budgets){
  const folder=String(moves/1000).padStart(4,"0")+"k";
  for(const [name,seed] of Object.entries(manifest.fighters)){
    const dir=path.join(arena,folder,name),r=read(path.join(dir,"result.json"));
    if(r.status!=="STRICT_PASS")continue;
    const raw=fs.readFileSync(path.join(dir,r.candidate_gz));
    run(JSON.parse(zlib.gunzipSync(raw)),{cohort:"original",name:"original_"+seed+"_"+moves,expectedQ:Number(r.q3),archiveSha256:sha(raw)});
  }
}
for(const v of verification.verified){
  const raw=fs.readFileSync(path.join(archive,v.file));
  if(sha(raw)!==v.sha256)throw Error("Witness fingerprint mismatch "+v.file);
  run(JSON.parse(raw),{cohort:"witness",name:"witness_"+v.file.replace(/\.json$/,""),expectedQ:v.score.q,archiveSha256:sha(raw)});
}
if(counts.original!==25||counts.witness!==7)throw Error("Unexpected cohort sizes");
const best=Math.max(...results.map(r=>r.after.q));
console.log(JSON.stringify({...counts,bestQ3:best},null,2));
console.log("Report:",path.join(out,"report.json"));
