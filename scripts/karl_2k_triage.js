#!/usr/bin/env node
"use strict";
// Read-only 2k archive triage. No annealing, no repairs, no source rebuild.
const fs=require("node:fs"),path=require("node:path"),zlib=require("node:zlib"),crypto=require("node:crypto");
const cp=require("node:child_process"),{performance}=require("node:perf_hooks");
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

if(process.argv.length!==4)throw Error("Usage: node scripts/karl_2k_triage.js CAMPAIGN NEW_OUTPUT_DIRECTORY");
const campaign=path.resolve(process.argv[2]),out=path.resolve(process.argv[3]);
const manifest=read(path.join(campaign,"manifest.json"));
const inp=path.join(repo,"research/karl-autopsy/20261127/prepared_input.json");
const input=read(inp),py=process.env.KARL_PYTHON||"python3";
const readRows=String.raw`
import csv,hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1])
p=Path(sys.argv[2])
fp=hashlib.sha256(json.dumps(json.loads(p.read_text()),sort_keys=True,ensure_ascii=False).encode("utf-8")).hexdigest()
arms={}
for arm in ("A","C"):
    csvp=root/arm/"results.csv"
    raw=csvp.read_bytes()
    import io
    rows=list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    selected=[]
    for r in rows:
        if r.get("status")!="FAIL":
            continue
        failures=json.loads(r.get("audit_failures") or "[]")
        if failures and all(x.startswith(("NONVERTICAL_","BODY_CROSSINGS_")) for x in failures):
            selected.append({"seed":int(r["seed"]),"moves":int(r["moves"]),"failures":failures,"archive":r.get("candidate_gz","")})
    arms[arm]={"rows":len(rows),"csvSha256":hashlib.sha256(raw).hexdigest(),"seeds":[int(r["seed"]) for r in rows],"selected":selected}
print(json.dumps({"fingerprint":fp,"arms":arms}))
`;
const snap=JSON.parse(cp.execFileSync(py,["-c",readRows,campaign,inp],{encoding:"utf8",maxBuffer:8*1024*1024}));
if(snap.fingerprint!==manifest.input_sha256||manifest.moves!==2000)throw Error("Campaign input/budget mismatch");
for(const a of Object.values(snap.arms))if(new Set(a.seeds).size!==a.rows)throw Error("Duplicate seeds");
const aSeeds=new Set(snap.arms.A.seeds),paired=snap.arms.C.seeds.filter(s=>aSeeds.has(s)).length;
fs.mkdirSync(out);
const counts={},results=[];
function checkpoint(){
 const report={manifest,pairedSeeds:paired,counts,results,top:results.filter(x=>x.ok).sort((a,b)=>a.offenders.length-b.offenders.length||b.score.q-a.score.q||a.seed-b.seed).slice(0,20)};
 fs.writeFileSync(path.join(out,"report.tmp"),JSON.stringify(report,null,2)+"\n");
 fs.renameSync(path.join(out,"report.tmp"),path.join(out,"report.json"));
}
for(const [arm,a] of Object.entries(snap.arms)){
 const c=counts[arm]={rows:a.rows,csvSha256:a.csvSha256,eligible:a.selected.length,missing:0,replayMismatch:0,graphMismatch:0,ok:0,histogram:{},faultPairHistogram:{}};
 console.log("🔬 ARM",arm,"routing-only candidates",c.eligible);
 const root=path.join(campaign,arm);
 for(const row of a.selected){
   const rec={arm,seed:row.seed,moves:row.moves,archive:row.archive,originalFailures:row.failures,ok:false};
   if(row.moves!==2000)throw Error("Unexpected move budget");
   const p=path.resolve(root,row.archive);
   if(!row.archive||!p.startsWith(root+path.sep)||!fs.existsSync(p)||!fs.statSync(p).isFile()){c.missing++;rec.reason="archive missing or outside arm";results.push(rec);continue;}
   const raw=fs.readFileSync(p),b=JSON.parse(zlib.gunzipSync(raw)),ctx=context(b),audit=auditSavedStrict(b,input,false);
   rec.archiveSha256=sha(raw);rec.audit=audit;rec.score=q3(b);
   if(audit.valid||b.board.rows!==24||b.board.cols!==56||b.board.pattern||JSON.stringify([...audit.failures].sort())!==JSON.stringify([...row.failures].sort())){
     c.replayMismatch++;rec.reason="saved audit differs";results.push(rec);continue;
   }
   const g=physicalGraph(b,ctx.pins);
   if(!g.complete){c.graphMismatch++;rec.reason="copper graph disagreement";rec.graph=g;results.push(rec);continue;}
   rec.offenders=b.board.wires.map((w,i)=>({i,d:Number(w.from.col!==w.to.col||w.from.row===w.to.row),x:ctx.cross(w),wire:w})).filter(w=>w.d||w.x);
   if(rec.offenders.reduce((n,w)=>n+w.x,0)!==audit.crossings||rec.offenders.reduce((n,w)=>n+w.d,0)!==audit.nonvertical)throw Error("Offender count mismatch");
   rec.ok=true;c.ok++;
   const k=rec.offenders.length;
   c.histogram[k]=(c.histogram[k]||0)+1;
   const f=audit.nonvertical+"/"+audit.crossings;
   c.faultPairHistogram[f]=(c.faultPairHistogram[f]||0)+1;
   results.push(rec);
   if(c.ok%50===0)console.log("📊",arm,c.ok,"replayed");
 }
 checkpoint();
}
console.log("Paired seed IDs:",paired);
console.log(JSON.stringify(counts,null,2));
console.log("🎯 20 closest archived boards (distinct offending wires first, Q3 second; raw Q3 is NOT strict)");
for(const x of results.filter(x=>x.ok).sort((a,b)=>a.offenders.length-b.offenders.length||b.score.q-a.score.q||a.seed-b.seed).slice(0,20))
 console.log(x.arm,x.seed,"offenders",x.offenders.length,"D",x.audit.nonvertical,"X",x.audit.crossings,"raw Q"+x.score.q.toFixed(2));
console.log("Report:",path.join(out,"report.json"));
