#!/usr/bin/env node
"use strict";
// Read-only research: no decoder, no annealing, no writes to original boards.
// Usage: node scripts/karl_autopsy.js REPO ARENA PREPARED_INPUT OUTPUT [--smoke]
const fs=require("node:fs"), path=require("node:path"), zlib=require("node:zlib"), crypto=require("node:crypto");
const args=process.argv.slice(2);
if(args.length<4||args.length>5||(args.length===5&&args[4]!=="--smoke")) throw Error("Usage: node script REPO ARENA PREPARED_INPUT OUTPUT [--smoke]");
const [repo,arena,inputFile,out]=args.slice(0,4).map(p=>path.resolve(p));
const smoke=args[4]==="--smoke";
const selected=new Set(["1216:280000","1216:350000","1216:360000","1216:490000","1216:450000","1859:500000"]);
if(fs.existsSync(out)) throw Error("Choose a new output directory");
const base=path.join(repo,"src/frontend/tests/solver");
const {auditSavedStrict}=require(path.join(base,"auditSavedStrict.js"));
const {DEFAULT_COMPONENTS,resolveComponentDef,boardLayout,partGeometry,flexGeometry,computeStripSegments}=require(path.join(base,"helpers.js"));
const {expandOffBoard}=require(path.join(base,"out/components/stripboard/offBoard.js"));
const {collectBoardPins,collectOccupiedHoles}=require(path.join(base,"out/components/stripboard/boardPins.js"));
const read=p=>JSON.parse(fs.readFileSync(p,"utf8"));
const input=read(inputFile), manifest=read(path.join(arena,"manifest.json"));
const key=p=>p.row+","+p.col;
const fingerprint=require("node:child_process").execFileSync(process.env.KARL_PYTHON||"python3",["-c","import hashlib,json,sys; print(hashlib.sha256(json.dumps(json.load(open(sys.argv[1])),sort_keys=True,ensure_ascii=False).encode(\"utf-8\")).hexdigest())",inputFile],{encoding:"utf8"}).trim();
if(fingerprint!==manifest.input) throw Error("Prepared input fingerprint mismatch: "+fingerprint);
console.log("✅ Prepared input fingerprint verified:",fingerprint);
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
function testGraph(){
  const b={board:{rows:2,cols:3,cuts:[{row:0,col:1,kind:"hole"}],wires:[]}};
  const pins=[{row:0,col:0,netId:"A"},{row:0,col:2,netId:"A"}];
  if(physicalGraph(b,pins).complete)throw Error("Graph selftest: split");
  b.board.wires=[{from:{row:0,col:0},to:{row:0,col:2}}];
  if(!physicalGraph(b,pins).complete)throw Error("Graph selftest: restored");
  b.board.wires[0].to.col=1;
  if(physicalGraph(b,pins).complete)throw Error("Graph selftest: drilled endpoint");
}
// Bounded search of simple copper-group paths. An intermediate strip must
// have distinct entry and departure solder holes. All proposed wires are
// vertical and obstacle-free; the full audit still decides acceptance.
function searchPaths(adj,source,target,maxHops=4,maxStates=20000,maxPaths=64){
  const queue=[{g:source,groups:[source],edges:[]}], paths=[];
  let cursor=0,expanded=0,truncated=false;
  while(cursor<queue.length){
    const state=queue[cursor++];expanded++;
    if(state.edges.length>=maxHops)continue;
    const arrival=state.edges.at(-1)?.to;
    for(const edge of adj.get(state.g)||[]){
      if(state.groups.includes(edge.g))continue;
      if(arrival&&key(arrival)===key(edge.from))continue;
      const edges=[...state.edges,edge];
      if(edge.g===target){
        paths.push(edges);
        if(paths.length>=maxPaths)return {paths,expanded,queued:queue.length,truncated:true};
      }else if(edges.length<maxHops){
        if(queue.length>=maxStates){truncated=true;continue;}
        queue.push({g:edge.g,groups:[...state.groups,edge.g],edges});
      }
    }
  }
  return {paths,expanded,queued:queue.length,truncated};
}
function testPaths(){
  const p=(r,c)=>({row:r,col:c});
  const adj=new Map([
    [0,[{g:1,from:p(0,0),to:p(1,0)}]],
    [1,[{g:2,from:p(1,0),to:p(2,0)},{g:2,from:p(1,1),to:p(2,1)}]],
    [2,[{g:3,from:p(2,2),to:p(3,2)}]]
  ]);
  const x=searchPaths(adj,0,3);
  if(x.paths.length!==1||x.paths[0].length!==3||x.paths[0][1].from.col!==1)throw Error("Multi-hop search selftest");
  if(searchPaths(adj,0,3,2).paths.length)throw Error("Hop limit selftest");
}
// Connect the two copper components left by removing the offending wire.
// Unlike the original repair, endpoint choices span EVERY existing strip
// connected to either side. Transit groups must be completely pinless.
// No component, cut, dimension, existing remaining wire or netlist is moved.
function netWide(b,ctx,i,limits={}){
  const ws=b.board.wires,old=ws[i],rest=ws.filter((_,j)=>j!==i);
  const ss=ctx.segments,parent=ss.map((_,i)=>i);
  const root=i=>{while(parent[i]!==i){parent[i]=parent[parent[i]];i=parent[i];}return i;};
  for(const w of rest){
    const a=ctx.at(w.from),z=ctx.at(w.to);
    if(a<0||z<0)throw Error("Wire endpoint has no copper segment");
    parent[root(a)]=root(z);
  }
  const aa=ctx.at(old.from),zz=ctx.at(old.to);
  if(aa<0||zz<0)return {reason:"missing original copper segment",paths:[]};
  const a=root(aa),z=root(zz);
  if(a===z)return {reason:"same connected group after removal",paths:[]};
  const pinGroups=new Set(ctx.pins.map(p=>ctx.at(p)).filter(i=>i>=0).map(root));
  const used=new Set(rest.flatMap(w=>[key(w.from),key(w.to)]));
  const allow=g=>g===a||g===z||!pinGroups.has(g);
  const byCol=Array.from({length:b.board.cols},()=>[]);
  const holesByGroup=new Map(), groupStrips=new Map();
  for(let i=0;i<ss.length;i++){
    const g=root(i);if(!allow(g))continue;
    groupStrips.set(g,(groupStrips.get(g)||0)+1);
    const seg=ss[i];
    for(let c=seg.startCol;c<=seg.endCol;c++){
      const p={row:seg.row,col:c};
      if(ctx.occupied.has(key(p))||used.has(key(p)))continue;
      byCol[c].push({g,p});
      holesByGroup.set(g,(holesByGroup.get(g)||0)+1);
    }
  }
  const adj=new Map();
  let pairChecks=0,blockedCrossing=0,cleanEdges=0,directEdges=0;
  const add=(g,edge)=>{if(!adj.has(g))adj.set(g,[]);adj.get(g).push(edge);};
  for(const col of byCol){
    for(let j=0;j<col.length;j++)for(let k=j+1;k<col.length;k++){
      const A=col[j],Z=col[k];
      if(A.g===Z.g||A.p.row===Z.p.row)continue;
      pairChecks++;
      if(ctx.cross({from:A.p,to:Z.p})){blockedCrossing++;continue;}
      const len=Math.abs(A.p.row-Z.p.row);
      add(A.g,{g:Z.g,from:A.p,to:Z.p,len});
      add(Z.g,{g:A.g,from:Z.p,to:A.p,len});
      cleanEdges++;
      if((A.g===a&&Z.g===z)||(A.g===z&&Z.g===a))directEdges++;
    }
  }
  for(const edges of adj.values())edges.sort((x,y)=>x.len-y.len||x.from.col-y.from.col||x.to.row-y.to.row);
  const found=searchPaths(adj,a,z,limits.hops??4,limits.states??20000,limits.paths??64);
  return {source:a,target:z,sourceStrips:groupStrips.get(a)||0,targetStrips:groupStrips.get(z)||0,
    sourceFree:holesByGroup.get(a)||0,targetFree:holesByGroup.get(z)||0,
    groups:groupStrips.size,groupsWithFree:holesByGroup.size,sourceCols:byCol.flatMap((hs,c)=>hs.some(h=>h.g===a)?[c]:[]),targetCols:byCol.flatMap((hs,c)=>hs.some(h=>h.g===z)?[c]:[]),pairChecks,blockedCrossing,cleanEdges,directEdges,
    sourceEdges:(adj.get(a)||[]).length,targetEdges:(adj.get(z)||[]).length,
    ...found};
}

// Preserve the partition of all anchored holes on a horizontal strip.
// A drilled hole may never land on an anchor. Empty copper can change
// ownership, but no two pin/wire anchors may gain or lose a copper link.
function anchorPartition(cuts,cols){
  if(cuts.some(c=>c.kind==="hole"&&cols.includes(c.col)))return null;
  const boundaries=cuts.flatMap(c=>c.kind==="hole"?[c.col,c.col+1]:[c.col+1]);
  return cols.slice(1).map((col,j)=>boundaries.some(x=>cols[j]<x&&x<=col)?"1":"0").join("");
}
function testCutPartition(){
  const cut=(col,kind="between")=>({row:0,col,kind});
  const anchors=[1,5,8];
  if(anchorPartition([cut(2)],anchors)!==anchorPartition([cut(4)],anchors))throw Error("Cut slide anchor preservation");
  if(anchorPartition([cut(2)],anchors)===anchorPartition([cut(6)],anchors))throw Error("Cut slide crossing anchor");
  if(anchorPartition([cut(5,"hole")],anchors)!==null)throw Error("Cut slide drilled anchor");
  if(anchorPartition([cut(3,"hole")],anchors)!==anchorPartition([cut(2,"hole")],anchors))throw Error("Drilled slide preservation");
}

testGraph();
testPaths();
testCutPartition();
console.log("✅ Copper graph, multi-hop and cut partition synthetic checks passed");
fs.mkdirSync(out);
const results=[],counts={boards:0,strict:0,graphDisagreement:0,singleOffender:0,directRescue:0,relayRescue:0,strictImproved:0,netWideRescue:0,cutSlideRescue:0,skipped:0};
function examine(b,info){
  if(b.board.rows!==24||b.board.cols!==56||b.board.pattern)return {...info,skipped:"not ordinary 24x56 strips"};
  const old=auditSavedStrict(b,input,false), ctx=context(b), graph=physicalGraph(b,ctx.pins), score=q3(b);
  const expected=info.status==="STRICT_PASS";
  if(old.valid!==expected||Math.abs(score.q-info.q)>0.011)throw Error("Archive replay differs: "+JSON.stringify(info));
  counts.boards++;if(old.valid)counts.strict++;
  if(graph.complete!==(old.incomplete===0&&old.conflicts===0&&old.unplaced.length===0))counts.graphDisagreement++;
  const result={...info,audit:old,graph,score,trials:0,method:null,best:null};
  if(graph.complete!==(old.incomplete===0&&old.conflicts===0&&old.unplaced.length===0)){result.skipped="electrical graph disagreement; manual investigation required";return result;}
  // Keep placements, netlist and locks fixed. Last resort moves one existing cut without changing its kind or count.
  const ws=b.board.wires;
  const bad=ws.map((w,i)=>({i,d:Number(w.from.col!==w.to.col||w.from.row===w.to.row),x:ctx.cross(w)})).filter(x=>x.d||x.x);
  result.offenders=bad.map(x=>({...x,wire:ws[x.i],strips:[ctx.segments[ctx.at(ws[x.i].from)],ctx.segments[ctx.at(ws[x.i].to)]]}));
  if(bad.reduce((n,x)=>n+x.x,0)!==old.crossings)throw Error("Crossing predicate mismatch");
  let best=null,bestScore=null;
  function offer(wires,method,detail,cuts=b.board.cuts){
    const candidate={...b,board:{...b.board,wires,cuts}};
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
    offer(ws.filter((_,j)=>j!==i),"redundant_wire",{i,old:ws[i]});
    direct(i);
    if(!best)relay(i);
    if(!best){
      const {paths,...diagnostics}=netWide(b,ctx,i);
      result.netWide={...diagnostics,paths:paths.length};
      for(const route of paths){
        const rest=ws.filter((_,j)=>j!==i);
        const replacements=route.map((e,j)=>({...ws[i],from:e.from,to:e.to,...(j?{id:"autopsy-"+sha(JSON.stringify([info.seed,info.moves,i,route,j])).slice(0,16)}:{})}));
        offer([...rest,...replacements],"net_wide_path",{i,old:ws[i],new:replacements});
      }
      console.log("🧬 Net-wide",info.seed,info.moves,JSON.stringify(result.netWide));
    }
    if(!best)cutSlide(i);
  }
  function cutSlide(i){
    const anchors=[...ctx.pins,...ws.flatMap(w=>[w.from,w.to])];
    const original=b.board.cuts;
    const stats={positions:0,anchorSafe:0,graphSafe:0,routeCandidates:0,withPath:0,accepted:0,searchTruncated:0,auditCapHit:false};
    const jobs=[];
    for(let j=0;j<original.length;j++){
      const cut=original[j],row=cut.row;
      const cols=[...new Set(anchors.filter(p=>p.row===row).map(p=>p.col))].sort((a,z)=>a-z);
      const rowCuts=original.filter(c=>c.row===row),signature=anchorPartition(rowCuts,cols);
      if(signature===null)continue;
      const max=cut.kind==="hole"?b.board.cols-1:b.board.cols-2;
      for(let col=0;col<=max;col++){
        if(col===cut.col||original.some((c,k)=>k!==j&&c.row===row&&c.col===col))continue;
        stats.positions++;
        const replacement={...cut,col};
        const cuts=original.map((c,k)=>k===j?replacement:c);
        if(anchorPartition(cuts.filter(c=>c.row===row),cols)!==signature)continue;
        stats.anchorSafe++;
        jobs.push({j,cut,replacement,cuts,delta:Math.abs(cut.col-col)});
      }
    }
    jobs.sort((x,y)=>x.delta-y.delta||x.j-y.j||x.replacement.col-y.replacement.col);
    for(const job of jobs){
      if(stats.routeCandidates>=256){stats.auditCapHit=true;break;}
      const shifted={...b,board:{...b.board,cuts:job.cuts}};
      if(!physicalGraph(shifted,ctx.pins).complete)continue;
      stats.graphSafe++;
      const changedCtx=context(shifted);
      const route=netWide(shifted,changedCtx,i,{hops:4,states:5000,paths:8});
      if(route.truncated)stats.searchTruncated++;
      if(!route.paths.length)continue;
      stats.withPath++;
      for(const pathEdges of route.paths){
        if(stats.routeCandidates>=256){stats.auditCapHit=true;break;}
        stats.routeCandidates++;
        const rest=ws.filter((_,j)=>j!==i);
        const replacements=pathEdges.map((e,j)=>({...ws[i],from:e.from,to:e.to,...(j?{id:"autopsy-"+sha(JSON.stringify([info.seed,info.moves,job.j,job.replacement,pathEdges,j])).slice(0,16)}:{})}));
        if(offer([...rest,...replacements],"cut_slide_path",{i,old:ws[i],new:replacements,cutIndex:job.j,oldCut:job.cut,newCut:job.replacement},job.cuts))stats.accepted++;
      }
    }
    result.cutSlide=stats;
    console.log("🔪 Cut slide",info.seed,info.moves,JSON.stringify(stats));
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
    if(old.valid)counts.strictImproved++;else if(result.method==="direct_endpoint")counts.directRescue++;else if(result.method==="one_empty_strip_relay")counts.relayRescue++;else if(result.method==="net_wide_path")counts.netWideRescue++;else if(result.method==="cut_slide_path")counts.cutSlideRescue++;else counts.redundantRescue=(counts.redundantRescue||0)+1;
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
    if(smoke&&!selected.has(seed+":"+moves))continue;
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
if(smoke&&results.length!==selected.size)throw Error("Missing smoke cases");
console.log(JSON.stringify(counts,null,2));
console.log("Report:",path.join(out,"report.json"));
