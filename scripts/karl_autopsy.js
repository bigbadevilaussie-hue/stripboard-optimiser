#!/usr/bin/env node
"use strict";
// Read-only research: no decoder, no annealing, no writes to original boards.
// Usage: node /tmp/karl_autopsy.js REPO ARENA PREPARED_INPUT OUTPUT
const fs=require("node:fs"), path=require("node:path"), zlib=require("node:zlib"), crypto=require("node:crypto");
const [repo,arena,inputFile,out]=process.argv.slice(2).map(p=>path.resolve(p));
if(!repo||!arena||!inputFile||!out) throw Error("Usage: node script REPO ARENA PREPARED_INPUT OUTPUT");
if(fs.existsSync(out)) throw Error("Choose a new output directory");
const base=path.join(repo,"src/frontend/tests/solver");
const {auditSavedStrict}=require(path.join(base,"auditSavedStrict.js"));
const {DEFAULT_COMPONENTS,resolveComponentDef,boardLayout,partGeometry,flexGeometry,computeStripSegments}=require(path.join(base,"helpers.js"));
const {expandOffBoard}=require(path.join(base,"out/components/stripboard/offBoard.js"));
const {collectBoardPins,collectOccupiedHoles}=require(path.join(base,"out/components/stripboard/boardPins.js"));
const read=p=>JSON.parse(fs.readFileSync(p,"utf8"));
const input=read(inputFile), manifest=read(path.join(arena,"manifest.json"));
const key=p=>p.row+","+p.col, clone=x=>JSON.parse(JSON.stringify(x));
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
  const u=b.components.filter(c=>!c.offBoard&&!c.boardExcluded&&!c.boardPos).length;
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
  for(const c of cuts){if(!inside(c)){bad.push("cut outside board");continue;}if(c.kind==="hole")dr.add(idx(c));else if(c.kind===undefined||c.kind==="between")kn.add(idx(c));else bad.push("unsupported cut kind");}
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
function testGraph(){
  const b={board:{rows:2,cols:3,cuts:[{row:0,col:1,kind:"hole"}],wires:[]}};
  const pins=[{row:0,col:0,netId:"A"},{row:0,col:2,netId:"A"}];
  if(physicalGraph(b,pins).complete)throw Error("Graph selftest: split");
  b.board.wires=[{from:{row:0,col:0},to:{row:0,col:2}}];
  if(!physicalGraph(b,pins).complete)throw Error("Graph selftest: restored");
  b.board.wires[0].to.col=1;
  if(physicalGraph(b,pins).complete)throw Error("Graph selftest: drilled endpoint");
}
testGraph();
fs.mkdirSync(out);
const results=[],counts={boards:0,strict:0,graphDisagreement:0,singleOffender:0,directRescue:0,relayRescue:0,strictImproved:0,skipped:0};
function examine(b,info){
  if(b.board.rows!==24||b.board.cols!==56||b.board.pattern)return {...info,skipped:"not ordinary 24x56 strips"};
  const old=auditSavedStrict(b,input,false), ctx=context(b), graph=physicalGraph(b,ctx.pins), score=q3(b);
  const expected=info.status==="STRICT_PASS";
  if(old.valid!==expected||Math.abs(score.q-info.q)>0.011)throw Error("Archive replay differs: "+JSON.stringify(info));
  counts.boards++;if(old.valid)counts.strict++;
  if(graph.complete!==(old.incomplete===0&&old.conflicts===0&&old.unplaced.length===0))counts.graphDisagreement++;
  const result={...info,audit:old,graph,score,trials:0,method:null,best:null};
  // Only alter wires. Existing placements, cuts, netlist, locks stay byte-equivalent as JSON.
  const ws=b.board.wires;
  const bad=ws.map((w,i)=>({i,d:Number(w.from.col!==w.to.col||w.from.row===w.to.row),x:ctx.cross(w)})).filter(x=>x.d||x.x);
  if(bad.reduce((n,x)=>n+x.x,0)!==old.crossings)throw Error("Crossing predicate mismatch");
  let best=null,bestScore=null;
  function offer(wires,method,detail){
    const candidate={...b,board:{...b.board,wires}};
    result.trials++;
    const a=auditSavedStrict(candidate,input,false);
    if(!a.valid||!physicalGraph(candidate,ctx.pins).complete)return false;
    const q=q3(candidate);
    if(old.valid&&q.q<=score.q)return false;
    if(!bestScore||q.q>bestScore.q||(q.q===bestScore.q&&q.w<bestScore.w)){
      best=candidate;bestScore=q;result.method=method;result.best={score:q,detail,audit:a};
    }
    return true;
  }
  if(old.valid){
    for(let i=0;i<ws.length;i++)offer(ws.filter((_,j)=>j!==i),"redundant_wire",{i,old:ws[i]});
    // One-wire endpoint relocation, including stack reduction.
    for(let i=0;i<ws.length;i++)direct(i);
  }else if(graph.complete&&old.failures.length&&old.failures.every(x=>/^(NONVERTICAL|BODY_CROSSINGS)_\d+$/.test(x))&&bad.length===1){
    counts.singleOffender++;
    const i=bad[0].i;
    direct(i);
    if(!best)relay(i);
  }
  function endpoints(i){
    const oldWire=ws[i],a=ctx.at(oldWire.from),z=ctx.at(oldWire.to);
    const rest=ws.filter((_,j)=>j!==i),used=new Set(rest.flatMap(w=>[key(w.from),key(w.to)]));
    const free=p=>!ctx.occupied.has(key(p))&&!used.has(key(p));
    return {oldWire,a,z,rest,used,free};
  }
  function direct(i){
    const {oldWire,a,z,rest,free}=endpoints(i);
    if(a<0||z<0||a===z)return;
    const A=ctx.segments[a],Z=ctx.segments[z];
    if(A.row===Z.row)return;
    for(let c=Math.max(A.startCol,Z.startCol);c<=Math.min(A.endCol,Z.endCol);c++){
      const from={row:A.row,col:c},to={row:Z.row,col:c};
      if(!free(from)||!free(to)||ctx.cross({from,to}))continue;
      if(key(from)===key(oldWire.from)&&key(to)===key(oldWire.to))continue;
      const wire={...oldWire,from,to};
      const wires=ws.map((w,j)=>j===i?wire:w);
      if(old.valid&&q3({...b,board:{...b.board,wires}}).q<=score.q)continue;
      offer(wires,"direct_endpoint",{i,old:oldWire,new:wire});
    }
  }
  // Search every isolated, completely pinless existing strip as one relay.
  // No cut donation, no new cuts, no shared solder holes, no placement move.
  function relay(i){
    const {oldWire,a,z,rest,free}=endpoints(i);
    if(a<0||z<0||a===z)return;
    const A=ctx.segments[a],Z=ctx.segments[z],busy=new Set(ctx.pins.map(ctx.at));
    for(const w of rest){busy.add(ctx.at(w.from));busy.add(ctx.at(w.to));}
    const hop=(S,T)=>{
      const opts=[];
      if(S.row===T.row)return opts;
      for(let c=Math.max(S.startCol,T.startCol);c<=Math.min(S.endCol,T.endCol);c++){
        const w={from:{row:S.row,col:c},to:{row:T.row,col:c}};
        if(free(w.from)&&free(w.to)&&!ctx.cross(w))opts.push(w);
      }
      return opts;
    };
    for(let t=0;t<ctx.segments.length;t++){
      if(t===a||t===z||busy.has(t))continue;
      const T=ctx.segments[t];
      for(const w1 of hop(A,T))for(const w2 of hop(T,Z)){
        if(key(w1.to)===key(w2.from))continue;
        const id=sha(JSON.stringify([info.seed,info.moves,i,w1,w2])).slice(0,16);
        offer([...rest,{...oldWire,...w1},{...oldWire,id:"autopsy-"+id,...w2}],"one_empty_strip_relay",{i,old:oldWire,new:[w1,w2]});
      }
    }
  }
  if(best){
    if(old.valid)counts.strictImproved++;else if(result.method==="direct_endpoint")counts.directRescue++;else counts.relayRescue++;
    const f=info.moves+"_"+info.seed+"_"+result.method+".json";
    fs.writeFileSync(path.join(out,f),JSON.stringify(best,null,2)+"\n");
    result.repaired=f;
    console.log("💥",info.seed,info.moves,score.q,"→",bestScore.q,result.method,"STRICT");
  }
  return result;
}
for(const moves of manifest.budgets){
  const folder=String(moves/1000).padStart(4,"0")+"k";
  for(const [name,seed] of Object.entries(manifest.fighters)){
    const dir=path.join(arena,folder,name),r=read(path.join(dir,"result.json"));
    if(Number(r.seed)!==seed||Number(r.moves)!==moves)throw Error("Archive identity mismatch");
    const info={seed,moves,status:r.status,q:Number(r.q3)};
    if(!r.candidate_gz){counts.skipped++;results.push({...info,skipped:"no board"});continue;}
    const raw=fs.readFileSync(path.join(dir,r.candidate_gz)),b=JSON.parse(zlib.gunzipSync(raw));
    const result=examine(b,{...info,archiveSha256:sha(raw)});
    results.push(result);
    fs.writeFileSync(path.join(out,"report.tmp"),JSON.stringify({counts,results},null,2)+"\n");
    fs.renameSync(path.join(out,"report.tmp"),path.join(out,"report.json"));
    console.log("🔬",seed,moves,result.audit?.valid?"STRICT":"RAW","trials",result.trials??0);
  }
}
console.log(JSON.stringify(counts,null,2));
console.log("Report:",path.join(out,"report.json"));
