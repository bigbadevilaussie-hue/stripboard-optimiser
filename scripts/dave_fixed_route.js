#!/usr/bin/env node
"use strict";
// Standalone research repair, not a production solver change.
function copper(board,pins,wires) {
  const R=board.rows,C=board.cols,N=R*C, parent=Array.from({length:N},(_,i)=>i), bad=[];
  const idx=p=>p.row*C+p.col;
  const inside=p=>p&&Number.isInteger(p.row)&&Number.isInteger(p.col)&&p.row>=0&&p.row<R&&p.col>=0&&p.col<C;
  const root=i=>{while(parent[i]!==i){parent[i]=parent[parent[i]];i=parent[i];}return i};
  const join=(a,b)=>{a=root(a);b=root(b);if(a!==b)parent[b]=a};
  const drilled=new Set(),knife=new Set();
  if(board.pattern)throw Error("Custom copper unsupported");
  for(const c of board.cuts){
    if(!inside(c)){bad.push("cut outside");continue}
    if(c.kind==="hole")drilled.add(idx(c));
    else if((c.kind??"between")==="between"&&c.col<C-1)knife.add(idx(c));
    else bad.push("invalid cut");
  }
  for(let r=0;r<R;r++)for(let c=0;c<C-1;c++){
    const i=r*C+c;if(!drilled.has(i)&&!drilled.has(i+1)&&!knife.has(i))join(i,i+1);
  }
  for(const w of wires){
    if(!inside(w.from)||!inside(w.to)){bad.push("wire outside");continue}
    const a=idx(w.from),b=idx(w.to);
    if(drilled.has(a)||drilled.has(b)){bad.push("wire on drilled hole");continue}
    join(a,b);
  }
  const labels=new Map(),nets=new Map(),shorts=[];
  for(const p of pins){
    if(!inside(p)||drilled.has(idx(p))){bad.push("pin off copper");continue}
    if(typeof p.netKey!=="string"){bad.push("missing pin netKey");continue}
    const g=root(idx(p)),n=p.netKey;
    if(labels.has(g)&&labels.get(g)!==n)shorts.push([g,labels.get(g),n]);
    else labels.set(g,n);
    if(!nets.has(n))nets.set(n,new Set());
    nets.get(n).add(g);
  }
  const split=[...nets].filter(([,groups])=>groups.size>1);
  return {idx,root,labels,drilled,bad,shorts,split,complete:!bad.length&&!shorts.length&&!split.length};
}

function legalEdges(board,ctx){
  const g=copper(board,ctx.pins,[]);
  if(g.bad.length||g.shorts.length)throw Error("Invalid fixed copper");
  const edges=[];
  for(let col=0;col<board.cols;col++){
    const free=[];
    for(let row=0;row<board.rows;row++){
      const p={row,col};
      if(!g.drilled.has(g.idx(p))&&!ctx.occupied.has(row+","+col))free.push(p);
    }
    for(let i=0;i<free.length;i++)for(let j=i+1;j<free.length;j++){
      const from=free[i],to=free[j];
      if(!ctx.cross({from,to}))edges.push({from,to,len:to.row-from.row});
    }
  }
  return edges.sort((a,b)=>a.len-b.len||a.from.col-b.from.col||a.from.row-b.from.row);
}

function boundedRoute(board,ctx,edges,initial,limits={}){
  const maxStates=limits.states??128,maxHops=limits.hops??4,maxPaths=limits.paths??8,maxQueue=limits.queue??1200;
  const stats={states:0,pathSearches:0,queued:0,queueCaps:0,pathCaps:0,stateCap:false,deadEnds:0};
  const key=p=>p.row+","+p.col;
  const signature=ws=>ws.map(w=>[key(w.from),key(w.to)].sort().join(":")).sort().join("|");
  const seen=new Set();
  function search(wires){
    if(stats.states>=maxStates){stats.stateCap=true;return null}
    const sig=signature(wires);
    if(seen.has(sig))return null;
    seen.add(sig);stats.states++;
    const g=copper(board,ctx.pins,wires);
    if(g.bad.length||g.shorts.length){stats.deadEnds++;return null}
    if(g.complete)return wires;
    const used=new Set(wires.flatMap(w=>[key(w.from),key(w.to)])),adj=new Map();
    const add=(a,z,from,to,len)=>{
      if(!adj.has(a))adj.set(a,[]);
      adj.get(a).push({g:z,from,to,len});
    };
    for(const e of edges){
      if(used.has(key(e.from))||used.has(key(e.to)))continue;
      const a=g.root(g.idx(e.from)),z=g.root(g.idx(e.to));
      if(a===z)continue;
      const na=g.labels.get(a),nz=g.labels.get(z);
      if(na!==undefined&&nz!==undefined&&na!==nz)continue;
      add(a,z,e.from,e.to,e.len);add(z,a,e.to,e.from,e.len);
    }
    // Most constrained split copper group first. All path intermediates
    // must be pinless, or already belong to the same net.
    let chosen=null;
    for(const [net,groups] of g.split)for(const source of groups){
      const degree=(adj.get(source)||[]).length;
      if(!chosen||degree<chosen.degree)chosen={net,source,degree};
    }
    if(!chosen||!chosen.degree){stats.deadEnds++;return null}
    stats.pathSearches++;
    const {net,source}=chosen,queue=[{groups:[source],path:[],holes:new Set(),len:0}],paths=[];
    let cap=false;
    for(let cursor=0;cursor<queue.length&&paths.length<maxPaths;cursor++){
      const st=queue[cursor];
      if(st.path.length>=maxHops)continue;
      const at=st.groups[st.groups.length-1];
      for(const e of adj.get(at)||[]){
        if(st.groups.includes(e.g)||st.holes.has(key(e.from))||st.holes.has(key(e.to)))continue;
        const label=g.labels.get(e.g);
        if(label!==undefined&&label!==net)continue;
        const next=[...st.path,e],len=st.len+e.len;
        if(label===net){
          paths.push({path:next,len});
          if(paths.length>=maxPaths){stats.pathCaps++;break}
        }else if(next.length<maxHops){
          if(queue.length>=maxQueue){cap=true;continue}
          queue.push({groups:[...st.groups,e.g],path:next,len,holes:new Set([...st.holes,key(e.from),key(e.to)])});
        }
      }
    }
    stats.queued+=queue.length;
    if(cap)stats.queueCaps++;
    if(!paths.length){stats.deadEnds++;return null}
    paths.sort((a,b)=>a.path.length-b.path.length||a.len-b.len);
    for(const p of paths){
      const newWires=p.path.map(e=>({from:e.from,to:e.to}));
      const result=search([...wires,...newWires]);
      if(result)return result;
      if(stats.stateCap)break;
    }
    return null;
  }
  return {wires:search(initial),stats};
}

function selfTest(){
  const assert=(ok,msg)=>{if(!ok)throw Error("SELFTEST "+msg)};
  const p=(row,col)=>({row,col}), pin=(r,c,n)=>({...p(r,c),netKey:n});
  const ctx=(pins,cross=()=>false)=>({pins,occupied:new Set(pins.map(x=>x.row+","+x.col)),cross});
  const b={rows:4,cols:5,cuts:[{row:0,col:2,kind:"between"},{row:3,col:2,kind:"between"}]};
  let x=ctx([pin(0,0,"A"),pin(3,0,"A"),pin(0,4,"B"),pin(3,4,"B")]);
  let out=boundedRoute(b,x,legalEdges(b,x),[]);
  assert(out.wires&&copper(b,x.pins,out.wires).complete&&out.wires.length===2,"two nets");
  const relay={rows:3,cols:5,cuts:[{row:0,col:2,kind:"between"},{row:2,col:1,kind:"between"}]};
  x=ctx([pin(0,0,"A"),pin(2,4,"A")],w=>w.from.row===0&&w.to.row===2);
  out=boundedRoute(relay,x,legalEdges(relay,x),[]);
  assert(out.wires&&out.wires.length===2&&copper(relay,x.pins,out.wires).complete,"relay");
  assert(new Set(out.wires.flatMap(w=>[w.from.row+","+w.from.col,w.to.row+","+w.to.col])).size===4,"distinct solder holes");
  const blocked={rows:2,cols:4,cuts:[]};
  x=ctx([pin(0,0,"A"),pin(1,0,"A"),pin(1,3,"nc:1")]);
  assert(copper(blocked,x.pins,[]).shorts.length>0,"floating short");
  x=ctx([pin(0,0,"A"),pin(1,0,"A")],()=>true);
  assert(boundedRoute(blocked,x,legalEdges(blocked,x),[]).wires===null,"blocked path");
  x=ctx([pin(0,0,"A"),pin(1,0,"A")]);
  assert(boundedRoute(blocked,x,legalEdges(blocked,x),[],{states:0}).stats.stateCap,"state limit");
  const drill={rows:1,cols:3,cuts:[{row:0,col:1,kind:"hole"}]};
  assert(!copper(drill,[pin(0,0,"A"),pin(0,2,"A")],[]).complete,"drilled separation");
  assert(copper(drill,[pin(0,0,"A")],[{from:p(0,0),to:p(0,1)}]).bad.length>0,"drilled endpoint");
  return 8;
}

console.log("✅",selfTest(),"synthetic routing assertions passed");
if(process.argv.length===3&&process.argv[2]==="--self-test")process.exit(0);

const fs=require("node:fs"),path=require("node:path"),crypto=require("node:crypto");
const {performance}=require("node:perf_hooks");
const sha=x=>crypto.createHash("sha256").update(x).digest("hex");
const read=p=>JSON.parse(fs.readFileSync(p,"utf8"));
const key=p=>p.row+","+p.col;
const repo=path.resolve(__dirname,".."),base=path.join(repo,"src/frontend/tests/solver");
const {auditSavedStrict}=require(path.join(base,"auditSavedStrict.js"));
const {DEFAULT_COMPONENTS,resolveComponentDef,boardLayout,partGeometry,flexGeometry,computeStripSegments}=require(path.join(base,"helpers.js"));
const {expandOffBoard}=require(path.join(base,"out/components/stripboard/offBoard.js"));
const {collectBoardPins,collectOccupiedHoles}=require(path.join(base,"out/components/stripboard/boardPins.js"));

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


function graphReport(g){
  return {complete:g.complete,bad:g.bad,shorts:g.shorts,split:g.split.map(([net,groups])=>({net,groups:groups.size}))};
}
function inspectBoard(saved,input,info){
  const started=performance.now(),before=auditSavedStrict(saved,input,false),ctx=context(saved);
  const board=saved.board;
  if(board.rows!==24||board.cols!==56||board.pattern)throw Error("Unsupported board");
  const score=q3(saved),graph=copper(board,ctx.pins,board.wires);
  const bad=board.wires.map((w,i)=>({i,x:ctx.cross(w),d:w.from.col!==w.to.col||w.from.row===w.to.row})).filter(w=>w.x||w.d);
  const row={seed:info.seed,sourceSha256:info.sha256,before,beforeQ:score,graph:graphReport(graph),
             offenders:bad.map(w=>({wire:w.i+1,crossings:w.x,nonvertical:w.d})),arms:[],status:"NO_REPAIR"};
  if(!graph.complete||before.valid||!before.failures.length||
     !before.failures.every(x=>/^(NONVERTICAL|BODY_CROSSINGS)_\d+$/.test(x))||
     bad.reduce((s,w)=>s+w.x,0)!==before.crossings||
     JSON.stringify(bad.map(w=>w.i+1))!==JSON.stringify(info.ids)||
     Math.abs(score.q-info.q3)>0.011){
    row.status="BASELINE_REPLAY_MISMATCH";row.wall_ms=performance.now()-started;return {row};
  }
  const edges=legalEdges(board,ctx);
  row.legalEdges=edges.length;
  const badIds=new Set(bad.map(x=>x.i));
  const good=board.wires.filter((_,i)=>!badIds.has(i));
  let best=null,bestQ=null;
  for(const [name,initial] of [["retain_clean",good],["ripup_all",[]]]){
    const trialStart=performance.now();
    const route=boundedRoute(board,ctx,edges,initial);
    const arm={name,kept:initial.length,stats:route.stats,found:!!route.wires};
    row.arms.push(arm);
    if(route.wires){
      const wires=route.wires.map((w,i)=>i<initial.length?w:{...w,id:"dave-repair-"+sha(JSON.stringify([info.seed,name,i,w])).slice(0,20)});
      const candidate={...saved,board:{...board,wires}};
      const finalGraph=copper(board,ctx.pins,wires),audit=auditSavedStrict(candidate,input,false),q=q3(candidate);
      const freeEnds=wires.every(w=>[w.from,w.to].every(p=>!ctx.occupied.has(key(p))));
      const uniqueIds=new Set(wires.map(w=>w.id)).size===wires.length;
      const clean=wires.every(w=>w.from.col===w.to.col&&w.from.row!==w.to.row&&!ctx.cross(w));
      arm.audit=audit;arm.graph=graphReport(finalGraph);arm.score=q;arm.freeEnds=freeEnds;arm.uniqueIds=uniqueIds;arm.clean=clean;
      arm.accepted=audit.valid&&finalGraph.complete&&freeEnds&&uniqueIds&&clean;
      if(arm.accepted&&(!bestQ||q.q>bestQ.q||(q.q===bestQ.q&&q.w<bestQ.w))){
        best=candidate;bestQ=q;row.method=name;row.after=q;
      }
    }
    arm.wall_ms=performance.now()-trialStart;
    console.log("🔧",info.seed,name,arm.accepted?"STRICT":arm.found?"AUDIT REJECT":"NO PATH",
                "states",arm.stats.states,"queue caps",arm.stats.queueCaps);
  }
  row.wall_ms=performance.now()-started;
  if(best)row.status="STRICT_RESCUE";
  return {row,best};
}
function main(){
  const [runArg,outArg,...extra]=process.argv.slice(2);
  if(!runArg||!outArg||extra.length)throw Error("Usage: node scripts/dave_fixed_route.js CAMPAIGN NEW_REPORT_DIR");
  const root=path.resolve(runArg),out=path.resolve(outArg);
  if(out===root||out.startsWith(root+path.sep)||fs.existsSync(out))throw Error("Choose new output outside campaign");
  const archive=read(path.join(repo,"research/dave-sniff/20261127-orientation-pair/summary.json")).campaigns[1];
  const resultsRaw=fs.readFileSync(path.join(root,"results.json"));
  if(sha(resultsRaw)!==archive.result_sha256)throw Error("Campaign results hash mismatch");
  const manifest=read(path.join(root,"manifest.json"));
  if(JSON.stringify(manifest)!==JSON.stringify(archive.manifest))throw Error("Campaign manifest mismatch");
  const results=JSON.parse(resultsRaw).results,bySeed=new Map(results.map(e=>[e.seed,e]));
  const chosen=archive.near_misses;
  if(chosen.length!==5||JSON.stringify(chosen.map(x=>x.seed))!==JSON.stringify([26,94,20,21,40]))throw Error("Unexpected research cohort");
  const work=chosen.map(info=>{
    const entry=bySeed.get(info.seed);
    if(!entry||entry.strictPass||entry.savedJson!==info.saved||entry.savedSha256!==info.sha256)throw Error("Seed identity mismatch");
    const raw=fs.readFileSync(path.join(root,entry.savedJson)),inputRaw=fs.readFileSync(path.join(root,entry.input));
    if(sha(raw)!==info.sha256||!Object.hasOwn(archive.input_hash_counts,sha(inputRaw)))throw Error("Board/input checksum mismatch "+info.seed);
    return {saved:JSON.parse(raw),input:JSON.parse(inputRaw),info};
  });
  fs.mkdirSync(out,{recursive:true});
  const report={sourceCampaign:root,sourceResultsSha256:sha(resultsRaw),sourceManifest:manifest,
    scriptSha256:sha(fs.readFileSync(__filename)),policy:{states:128,hops:4,paths:8,queue:1200,placementsFixed:true,cutsFixed:true,annealMoves:0},results:[]};
  const save=()=>{
    fs.writeFileSync(path.join(out,"report.tmp"),JSON.stringify(report,null,2)+"\n");
    fs.renameSync(path.join(out,"report.tmp"),path.join(out,"report.json"));
  };
  for(const item of work){
    console.log("🦈",item.info.seed,"|",item.info.offenders,"offending wires");
    const {row,best}=inspectBoard(item.saved,item.input,item.info);
    if(best){
      row.saved="strict_seed_"+row.seed+".json";
      const raw=JSON.stringify(best,null,2)+"\n";
      fs.writeFileSync(path.join(out,row.saved),raw);row.savedSha256=sha(raw);
      console.log("💥 STRICT RESCUE",row.seed,"Q"+row.beforeQ.q,"→ Q"+row.after.q,row.after.w+"W/"+row.after.c+"C");
    }else console.log("❌",row.seed,row.status);
    report.results.push(row);save();
  }
  const count=report.results.filter(x=>x.status==="STRICT_RESCUE").length;
  const lines=["# Dave fixed-placement routing experiment","","Zero annealing; fixed components and cuts. Both repair arms bounded. No-path does not establish impossibility.","",
      "| Seed | Result | Before Q3 | After Q3 | Method |","|---:|---|---:|---:|---|",
      ...report.results.map(x=>[x.seed,x.status,x.beforeQ.q,x.after?.q??"—",x.method??"—"].join(" | ")).map(s=>"| "+s+" |"),
      "","Strict rescues: "+count+"/"+work.length,"","Full independent copper graph and saved-board audit results in report.json."];
  fs.writeFileSync(path.join(out,"report.md"),lines.join("\n")+"\n");
  console.log("🏁",count+"/"+work.length,"STRICT RESCUES | zero annealing |",out);
}
main();
