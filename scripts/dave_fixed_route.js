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

function reachability(board,ctx,edges,wires,reserveEnds){
  const g=copper(board,ctx.pins,wires);
  if(g.bad.length||g.shorts.length)throw Error("Invalid reachability baseline");
  const key=p=>p.row+","+p.col;
  const used=new Set(reserveEnds?wires.flatMap(w=>[key(w.from),key(w.to)]):[]);
  const groups=new Map(),adj=new Map();
  for(let row=0;row<board.rows;row++)for(let col=0;col<board.cols;col++){
    const p={row,col},i=g.idx(p);
    if(g.drilled.has(i))continue;
    const r=g.root(i);
    if(!groups.has(r))groups.set(r,{holes:0,free:[]});
    const x=groups.get(r);x.holes++;
    if(!used.has(key(p))&&!ctx.occupied.has(key(p)))x.free.push(p);
  }
  function add(a,b){if(!adj.has(a))adj.set(a,new Set());adj.get(a).add(b)}
  for(const e of edges){
    if(used.has(key(e.from))||used.has(key(e.to)))continue;
    const a=g.root(g.idx(e.from)),b=g.root(g.idx(e.to));
    if(a===b)continue;
    const na=g.labels.get(a),nb=g.labels.get(b);
    if(na!==undefined&&nb!==undefined&&na!==nb)continue;
    add(a,b);add(b,a);
  }
  const splits=g.split.map(([net,targets])=>{
    const components=[];
    const remaining=new Set(targets);
    while(remaining.size){
      const source=remaining.values().next().value;
      const queue=[source],dist=new Map([[source,0]]);
      for(let i=0;i<queue.length;i++){
        const a=queue[i];
        for(const b of adj.get(a)||[]){
          const n=g.labels.get(b);
          if(dist.has(b)||(n!==undefined&&n!==net))continue;
          dist.set(b,dist.get(a)+1);queue.push(b);
        }
      }
      const reached=[...targets].filter(t=>dist.has(t));
      reached.forEach(t=>remaining.delete(t));
      components.push({targets:reached,reachableGroups:dist.size,
                       maxDistanceFromSource:Math.max(...reached.map(t=>dist.get(t)))});
    }
    return {net,groups:[...targets].map(id=>({id,holes:groups.get(id).holes,
      free:groups.get(id).free,neighbors:(adj.get(id)||new Set()).size})),
      components,reachable:components.length===1};
  });
  return {reserveEnds,splitNets:splits.length,unreachableNets:splits.filter(s=>!s.reachable).length,
          zeroDegreeGroups:splits.reduce((n,s)=>n+s.groups.filter(g=>g.neighbors===0).length,0),splits};
}

function testReachability(){
  const p=(row,col)=>({row,col}),pin=(row,col,netKey)=>({row,col,netKey});
  const board={rows:3,cols:3,cuts:[]};
  const ctx={pins:[pin(0,0,"A"),pin(2,0,"A")],occupied:new Set(["0,0","2,0"]),cross:()=>false};
  const e=legalEdges(board,ctx);
  if(reachability(board,ctx,e,[],true).unreachableNets!==0)throw Error("Reachability positive test");
  if(reachability(board,ctx,[],[],true).unreachableNets!==1)throw Error("Reachability disconnected test");
  const retained=[{from:p(0,1),to:p(1,1)}];
  const narrow=e.filter(w=>w.from.col===1&&w.to.col===1);
  if(reachability(board,ctx,narrow,retained,true).unreachableNets!==1||
     reachability(board,ctx,narrow,retained,false).unreachableNets!==0)throw Error("Reachability reservation test");
  const other={...ctx,pins:[...ctx.pins,pin(1,0,"B")],occupied:new Set(["0,0","1,0","2,0"])};
  const relayOnly=legalEdges(board,other).filter(w=>w.to.row-w.from.row===1);
  if(reachability(board,other,relayOnly,[],false).unreachableNets!==1)throw Error("Reachability foreign-net relay test");
  return 4;
}

function groupRoute(board,ctx,edges,limits={}){
  const stateLimit=limits.states??512,branchLimit=limits.branches??16;
  const stats={states:0,queueCaps:0,stateCap:false,branchCaps:0,forwardPrunes:0,
    directJoins:0,branches:0,maxDepth:0,duplicateStates:0};
  const seen=new Set(),key=p=>p.row+","+p.col;
  function model(wires){
    const g=copper(board,ctx.pins,wires);
    if(g.bad.length||g.shorts.length)return {g,adj:new Map()};
    const used=new Set(wires.flatMap(w=>[key(w.from),key(w.to)])),adj=new Map();
    function add(a,z,from,to,len){
      if(!adj.has(a))adj.set(a,new Map());
      const score=len+2*Number(used.has(key(from)))+2*Number(used.has(key(to)));
      const old=adj.get(a).get(z);
      if(!old||score<old.score)adj.get(a).set(z,{g:z,from,to,len,score});
    }
    for(const e of edges){
      const a=g.root(g.idx(e.from)),z=g.root(g.idx(e.to));
      if(a===z)continue;
      const na=g.labels.get(a),nz=g.labels.get(z);
      if(na!==undefined&&nz!==undefined&&na!==nz)continue;
      add(a,z,e.from,e.to,e.len);add(z,a,e.to,e.from,e.len);
    }
    return {g,adj};
  }
  function reach(m,net,source,banned=new Set()){
    const queue=[source],prev=new Map([[source,null]]);
    for(let i=0;i<queue.length;i++){
      const a=queue[i];
      for(const e of m.adj.get(a)?.values()||[]){
        if(prev.has(e.g)||banned.has(e.g))continue;
        const label=m.g.labels.get(e.g);
        if(label!==undefined&&label!==net)continue;
        prev.set(e.g,{a,e});queue.push(e.g);
      }
    }
    return {prev,queue};
  }
  function pathTo(prev,target){
    const path=[];
    while(prev.get(target)){
      const {a,e}=prev.get(target);path.push(e);target=a;
    }
    return path.reverse();
  }
  function search(input,depth){
    if(stats.states>=stateLimit){stats.stateCap=true;return null}
    let wires=input.slice(),m=model(wires);
    if(m.g.bad.length||m.g.shorts.length){stats.forwardPrunes++;return null}
    stats.states++;stats.maxDepth=Math.max(stats.maxDepth,depth);
    // Joining two already-owned components of the same net cannot consume
    // neutral copper. Reusable endpoints are legal in the baseline policy.
    const parent=new Map();
    function root(x){while(parent.has(x))x=parent.get(x);return x}
    const direct=[];
    for(const [a,neighbors] of m.adj){
      const net=m.g.labels.get(a);
      if(net===undefined)continue;
      for(const [z,e] of neighbors)if(a<z&&m.g.labels.get(z)===net)direct.push({a,z,e});
    }
    direct.sort((a,b)=>a.e.score-b.e.score||a.a-b.a||a.z-b.z);
    for(const {a,z,e} of direct){
      const ar=root(a),zr=root(z);if(ar===zr)continue;
      parent.set(zr,ar);wires.push({from:e.from,to:e.to});stats.directJoins++;
    }
    if(parent.size)m=model(wires);
    if(m.g.bad.length||m.g.shorts.length){stats.forwardPrunes++;return null}
    if(m.g.complete)return wires;
    // Deduplicate by allocation of copper groups, not jumper endpoint choices.
    const groups=new Map();
    for(let r=0;r<board.rows;r++)for(let c=0;c<board.cols;c++){
      const i=m.g.idx({row:r,col:c});if(m.g.drilled.has(i))continue;
      const g=m.g.root(i);
      if(!groups.has(g))groups.set(g,[]);
      groups.get(g).push(i);
    }
    const signature=JSON.stringify([...groups.values()].sort((a,b)=>a[0]-b[0]));
    if(seen.has(signature)){stats.duplicateStates++;return null}
    seen.add(signature);
    // Forward checking across ALL split nets before allocating another relay.
    let choice=null;
    for(const [net,targets] of m.g.split){
      const first=targets.values().next().value,reachable=reach(m,net,first);
      if([...targets].some(t=>!reachable.prev.has(t))){
        stats.forwardPrunes++;return null;
      }
      for(const source of targets){
        const degree=m.adj.get(source)?.size||0;
        const slack=reachable.queue.length-targets.size;
        if(!choice||degree<choice.degree||(degree===choice.degree&&slack<choice.slack))
          choice={net,targets,source,degree,slack};
      }
    }
    if(!choice){stats.forwardPrunes++;return null}
    const {net,source,targets}=choice,paths=[],pathKeys=new Set();
    function offer(path){
      if(!path.length)return;
      const relays=path.slice(0,-1).map(e=>e.g);
      const sig=JSON.stringify([path.at(-1).g,...relays.slice().sort((a,b)=>a-b)]);
      if(pathKeys.has(sig))return;
      pathKeys.add(sig);
      paths.push({path,relays,cost:path.reduce((n,e)=>n+e.score,0)});
    }
    // One shortest connection to each target, with alternatives via every
    // distinct first relay and by excluding each relay of the shortest paths.
    const base=reach(m,net,source);
    for(const target of targets)if(target!==source&&base.prev.has(target))offer(pathTo(base.prev,target));
    for(const e of m.adj.get(source)?.values()||[]){
      if(m.g.labels.has(e.g))continue;
      const next=reach(m,net,e.g,new Set([source]));
      for(const target of targets)if(target!==source&&next.prev.has(target))
        offer([e,...pathTo(next.prev,target)]);
    }
    const initial=paths.slice().sort((a,b)=>a.path.length-b.path.length||a.cost-b.cost).slice(0,branchLimit);
    const bans=new Set(initial.flatMap(p=>p.relays));
    for(const ban of bans){
      const alt=reach(m,net,source,new Set([ban]));
      for(const target of targets)if(target!==source&&alt.prev.has(target))offer(pathTo(alt.prev,target));
    }
    paths.sort((a,b)=>a.relays.length-b.relays.length||a.cost-b.cost);
    if(paths.length>branchLimit)stats.branchCaps++;
    for(const p of paths.slice(0,branchLimit)){
      stats.branches++;
      const next=search([...wires,...p.path.map(e=>({from:e.from,to:e.to}))],depth+1);
      if(next)return next;
      if(stats.stateCap)break;
    }
    return null;
  }
  return {wires:search([],0),stats};
}

function testGroupRoute(){
  const p=(row,col)=>({row,col}),pin=(row,col,netKey)=>({row,col,netKey});
  const board={rows:6,cols:3,cuts:[]};
  const ctx={pins:[pin(0,0,"A"),pin(1,0,"A"),pin(2,0,"B"),pin(3,0,"B")],
             occupied:new Set(["0,0","1,0","2,0","3,0"]),cross:()=>false};
  const edge=(a,b)=>({from:p(Math.min(a,b),1),to:p(Math.max(a,b),1),len:Math.abs(a-b)});
  const e=[[0,4],[1,4],[0,5],[1,5],[2,4],[3,4]].map(([a,b])=>edge(a,b));
  const result=groupRoute(board,ctx,e);
  if(!result.wires||!copper(board,ctx.pins,result.wires).complete||result.wires.length!==4)throw Error("Group competition test");
  if(new Set(result.wires.flatMap(w=>[w.from.row+","+w.from.col,w.to.row+","+w.to.col])).size===8)throw Error("Expected legal same-net daisy chain");
  const impossible=groupRoute(board,ctx,e.filter(w=>w.to.row!==5));
  if(impossible.wires||!impossible.stats.forwardPrunes)throw Error("Exclusive relay competition test");
  const direct=groupRoute(board,ctx,[edge(0,1),edge(2,3)]);
  if(!direct.wires||direct.wires.length!==2||direct.stats.directJoins!==2)throw Error("Direct same-net test");
  const cap=groupRoute(board,ctx,e,{states:0});
  if(cap.wires||!cap.stats.stateCap)throw Error("Group state cap test");
  return 5;
}

function conflictRoute(board,ctx,edges,limits={}){
  const maxStates=limits.states??4096;
  const g=copper(board,ctx.pins,[]);
  const stats={states:0,stateCap:false,queueCaps:0,generated:0,duplicates:0,
    routeCalls:0,cacheHits:0,infeasibleBranches:0,conflictsResolved:0,
    maxFrontier:0,bestConflictPairs:null,exhausted:false};
  if(g.bad.length||g.shorts.length)throw Error("Invalid static copper graph");
  // Every group is a connected piece of fixed copper. An edge is one legal
  // vertical jumper. With stacking and same-net solder-hole reuse allowed,
  // endpoints are not exclusive resources; neutral copper ownership is.
  const adj=new Map();
  function add(a,z,from,to,len){
    if(!adj.has(a))adj.set(a,new Map());
    const old=adj.get(a).get(z);
    if(!old||len<old.len)adj.get(a).set(z,{g:z,from,to,len});
  }
  for(const e of edges){
    const a=g.root(g.idx(e.from)),z=g.root(g.idx(e.to));
    if(a===z)continue;
    const na=g.labels.get(a),nz=g.labels.get(z);
    if(na!==undefined&&nz!==undefined&&na!==nz)continue;
    add(a,z,e.from,e.to,e.len);add(z,a,e.to,e.from,e.len);
  }
  const neighbors=new Map([...adj].map(([id,ns])=>[id,[...ns.values()].sort((a,b)=>a.len-b.len||a.g-b.g)]));
  const nets=g.split.map(([net,targets])=>({net,targets:[...targets].sort((a,b)=>a-b)}));
  const caches=nets.map(()=>new Map());
  function routeNet(i,ban){
    const sig=[...ban].sort((a,b)=>a-b).join(",");
    if(caches[i].has(sig)){stats.cacheHits++;return caches[i].get(sig)}
    stats.routeCalls++;
    const {net,targets}=nets[i],connected=new Set([targets[0]]),remaining=new Set(targets.slice(1)),wires=[];
    // Grow a connected tree by shortest unweighted paths to the nearest
    // remaining terminal. This is a complete single-net connectivity test,
    // not a minimum Steiner-tree solver.
    while(remaining.size){
      const queue=[...connected],prev=new Map(queue.map(a=>[a,null]));
      let found;
      for(let j=0;j<queue.length&&found===undefined;j++){
        const a=queue[j];
        for(const e of neighbors.get(a)||[]){
          if(prev.has(e.g)||ban.has(e.g))continue;
          const label=g.labels.get(e.g);
          if(label!==undefined&&label!==net)continue;
          prev.set(e.g,{a,e});
          if(remaining.has(e.g)){found=e.g;break}
          queue.push(e.g);
        }
      }
      if(found===undefined){caches[i].set(sig,null);return null}
      let t=found;
      while(prev.get(t)){
        const {a,e}=prev.get(t);
        wires.push({from:e.from,to:e.to});connected.add(t);t=a;
      }
      remaining.delete(found);
    }
    const result={wires,relays:[...connected].filter(id=>!g.labels.has(id))};
    caches[i].set(sig,result);return result;
  }
  function competition(routes){
    const owners=new Map();
    for(let i=0;i<routes.length;i++)for(const id of routes[i].relays){
      if(!owners.has(id))owners.set(id,[]);
      owners.get(id).push(i);
    }
    const clashes=[...owners].filter(([,ns])=>ns.length>1)
      .sort((a,b)=>b[1].length-a[1].length||a[0]-b[0]);
    return {clashes,pairs:clashes.reduce((n,[,ns])=>n+ns.length*(ns.length-1)/2,0)};
  }
  const bans=nets.map(()=>new Set()),routes=nets.map((_,i)=>routeNet(i,bans[i]));
  if(routes.some(x=>x===null)){stats.exhausted=true;stats.infeasibleBranches++;return {wires:null,stats}}
  const stack=[{bans,routes,conflict:competition(routes)}],seen=new Set([JSON.stringify(bans.map(()=>[]))]);
  stats.generated=1;stats.maxFrontier=1;
  while(stack.length){
    if(stats.states>=maxStates){stats.stateCap=true;return {wires:null,stats}}
    const state=stack.pop();stats.states++;
    const {clashes,pairs}=state.conflict;
    stats.bestConflictPairs=stats.bestConflictPairs===null?pairs:Math.min(stats.bestConflictPairs,pairs);
    if(!clashes.length){
      const wires=state.routes.flatMap(r=>r.wires);
      if(!copper(board,ctx.pins,wires).complete)throw Error("Conflict route graph inconsistency");
      return {wires,stats};
    }
    const [relay,users]=clashes[0];
    stats.conflictsResolved++;
    const children=[];
    // Any feasible assignment must forbid this relay to at least one of
    // these two nets. Neither branch assumes which alternative path wins.
    for(const i of users.slice(0,2)){
      const nextBans=state.bans.slice();
      nextBans[i]=new Set([...nextBans[i],relay]);
      const signature=JSON.stringify(nextBans.map(x=>[...x].sort((a,b)=>a-b)));
      if(seen.has(signature)){stats.duplicates++;continue}
      seen.add(signature);
      const replacement=routeNet(i,nextBans[i]);
      if(!replacement){stats.infeasibleBranches++;continue}
      const nextRoutes=state.routes.slice();nextRoutes[i]=replacement;
      children.push({bans:nextBans,routes:nextRoutes,conflict:competition(nextRoutes)});
      stats.generated++;
    }
    // Depth-first, try lower-conflict child first, retain the other child.
    // There is no per-net path cap. Only the global state limit can truncate.
    children.sort((a,b)=>b.conflict.pairs-a.conflict.pairs||
      b.routes.reduce((n,r)=>n+r.wires.length,0)-a.routes.reduce((n,r)=>n+r.wires.length,0));
    stack.push(...children);stats.maxFrontier=Math.max(stats.maxFrontier,stack.length);
  }
  stats.exhausted=true;return {wires:null,stats};
}

function testConflictRoute(){
  const p=(row,col)=>({row,col}),pin=(row,col,netKey)=>({row,col,netKey});
  const board={rows:7,cols:3,cuts:[]};
  const ctx={pins:[pin(0,0,"A"),pin(1,0,"A"),pin(2,0,"B"),pin(3,0,"B")],
    occupied:new Set(["0,0","1,0","2,0","3,0"]),cross:()=>false};
  const edge=(a,b)=>({from:p(Math.min(a,b),1),to:p(Math.max(a,b),1),len:Math.abs(a-b)});
  const paths=[[0,4],[1,4],[0,5],[1,5],[2,4],[3,4]].map(([a,b])=>edge(a,b));
  const route=conflictRoute(board,ctx,paths);
  if(!route.wires||route.wires.length!==4||!copper(board,ctx.pins,route.wires).complete||
     !route.stats.conflictsResolved)throw Error("Conflict route alternative relay");
  const blocked=conflictRoute(board,ctx,paths.filter(e=>e.to.row!==5));
  if(blocked.wires||!blocked.stats.exhausted||blocked.stats.stateCap)throw Error("Exclusive relay proof");
  const cap=conflictRoute(board,ctx,paths,{states:0});
  if(cap.wires||!cap.stats.stateCap||cap.stats.exhausted)throw Error("Conflict search cap");
  const direct=conflictRoute(board,ctx,[edge(0,1),edge(2,3)]);
  if(!direct.wires||direct.wires.length!==2||direct.stats.conflictsResolved)throw Error("Direct connectivity");
  const floating={...ctx,pins:[...ctx.pins,pin(4,0,"nc:f")],occupied:new Set([...ctx.occupied,"4,0"])};
  const blockedFloat=conflictRoute(board,floating,paths);
  if(blockedFloat.wires||!blockedFloat.stats.exhausted)throw Error("Floating relay protection");
  const longBoard={rows:9,cols:3,cuts:[]},longCtx={pins:[pin(0,0,"A"),pin(8,0,"A")],occupied:new Set(["0,0","8,0"]),cross:()=>false};
  const long=conflictRoute(longBoard,longCtx,Array.from({length:8},(_,i)=>edge(i,i+1)));
  if(!long.wires||long.wires.length!==8)throw Error("No artificial hop cap");
  // Compare to an exhaustive three-way assignment of each neutral group:
  // A, B or unused, over a deterministic sample of 96 seven-vertex graphs.
  const pairs=[];
  for(let a=0;a<7;a++)for(let b=a+1;b<7;b++)pairs.push([a,b]);
  for(let k=0;k<96;k++){
    const es=pairs.filter((_,i)=>(((Math.imul(k+1,0x9e3779b1)^Math.imul(i+17,0x85ebca6b))>>>((i+k)%24))&3)===0);
    let feasible=false;
    for(let a=0;a<3&&!feasible;a++)for(let b=0;b<3&&!feasible;b++)for(let c=0;c<3&&!feasible;c++){
      const owners=[0,0,1,1,a,b,c];
      const connected=(net,start,end)=>{
        const seen=new Set([start]),q=[start];
        for(let i=0;i<q.length;i++)for(const [x,y] of es){
          const z=x===q[i]?y:y===q[i]?x:-1;
          if(z>=0&&owners[z]===net&&!seen.has(z)){seen.add(z);q.push(z)}
        }
        return seen.has(end);
      };
      feasible=connected(0,0,1)&&connected(1,2,3);
    }
    const actual=conflictRoute(board,ctx,es.map(([x,y])=>edge(x,y)));
    if(actual.stats.stateCap||!!actual.wires!==feasible||(!feasible&&!actual.stats.exhausted))
      throw Error("Conflict vs exhaustive assignment "+k);
  }
  return 7;
}

function cutPartition(cuts,cols){
  if(cuts.some(c=>c.kind==="hole"&&cols.includes(c.col)))return null;
  const boundaries=cuts.flatMap(c=>c.kind==="hole"?[c.col,c.col+1]:[c.col+1]);
  return cols.slice(1).map((col,i)=>boundaries.some(x=>cols[i]<x&&x<=col)?"1":"0").join("");
}

function cutVariants(board,pins){
  const variants=[];
  for(let i=0;i<board.cuts.length;i++){
    const cut=board.cuts[i],row=cut.row;
    const cols=[...new Set(pins.filter(p=>p.row===row).map(p=>p.col))].sort((a,b)=>a-b);
    const partition=cutPartition(board.cuts.filter(c=>c.row===row),cols);
    if(partition===null)throw Error("Original drilled pin");
    const max=cut.kind==="hole"?board.cols-1:board.cols-2;
    for(let col=0;col<=max;col++){
      if(col===cut.col||board.cuts.some((c,j)=>j!==i&&c.row===row&&c.col===col))continue;
      const replacement={...cut,col},cuts=board.cuts.map((c,j)=>j===i?replacement:c);
      if(cutPartition(cuts.filter(c=>c.row===row),cols)!==partition)continue;
      variants.push({i,old:cut,replacement,cuts,delta:Math.abs(col-cut.col)});
    }
  }
  return variants.sort((a,b)=>a.delta-b.delta||a.i-b.i||a.replacement.col-b.replacement.col);
}

function physicalEdges(board,ctx){
  // ctx is constructed without cuts, so old drill locations are not
  // permanently excluded. Candidate drills are filtered separately.
  const edges=[];
  for(let col=0;col<board.cols;col++){
    const free=[];
    for(let row=0;row<board.rows;row++){
      if(!ctx.occupied.has(row+","+col))free.push({row,col});
    }
    for(let i=0;i<free.length;i++)for(let j=i+1;j<free.length;j++){
      const from=free[i],to=free[j];
      if(!ctx.cross({from,to}))edges.push({from,to,len:to.row-from.row});
    }
  }
  return edges.sort((a,b)=>a.len-b.len||a.from.col-b.from.col||a.from.row-b.from.row);
}

function edgesForCuts(edges,cuts){
  const drilled=new Set(cuts.filter(c=>c.kind==="hole").map(c=>c.row+","+c.col));
  return edges.filter(e=>!drilled.has(e.from.row+","+e.from.col)&&!drilled.has(e.to.row+","+e.to.col));
}

function cutSlideRoute(board,ctx,edges,limits={}){
  const probeCap=limits.probes??512,deepCap=limits.deep??32,stateCap=limits.states??4096;
  const variants=cutVariants(board,ctx.pins),successful=[],pending=[];
  const stats={eligible:variants.length,probes:0,probeCap:false,deep:0,deepCap:false,
    immediate:0,provenInfeasible:0,capped:0,states:0,routeCalls:0};
  const trials=[];
  function run(v,cap,phase){
    const changed={...board,cuts:v.cuts};
    const route=conflictRoute(changed,ctx,edgesForCuts(edges,v.cuts),{states:cap});
    const detail={cutIndex:v.i,old:v.old,replacement:v.replacement,delta:v.delta,phase,
      status:route.wires?"ROUTED":route.stats.exhausted?"GRAPH_INFEASIBLE":"SEARCH_CAP",
      states:route.stats.states,bestConflictPairs:route.stats.bestConflictPairs,routeCalls:route.stats.routeCalls};
    trials.push(detail);stats.states+=route.stats.states;stats.routeCalls+=route.stats.routeCalls;
    if(route.wires)successful.push({v,wires:route.wires});
    else if(route.stats.exhausted)stats.provenInfeasible++;
    return route;
  }
  for(const v of variants.slice(0,probeCap)){
    stats.probes++;
    const result=run(v,1,"probe");
    if(result.wires)stats.immediate++;
    else if(result.stats.stateCap)pending.push({v,conflicts:result.stats.bestConflictPairs??Infinity});
  }
  stats.probeCap=stats.probes<variants.length;
  pending.sort((a,b)=>a.conflicts-b.conflicts||a.v.delta-b.v.delta||a.v.i-b.v.i||a.v.replacement.col-b.v.replacement.col);
  for(const {v} of pending.slice(0,deepCap)){
    stats.deep++;
    const result=run(v,stateCap,"deep");
    if(result.stats.stateCap)stats.capped++;
  }
  stats.deepCap=stats.deep<pending.length;
  return {successful,stats,trials};
}

function testCutSlideRoute(){
  const p=(row,col)=>({row,col}),pin=(row,col,netKey)=>({row,col,netKey});
  const board={rows:5,cols:5,cuts:[{row:4,col:3,kind:"between"}]};
  const ctx={pins:[pin(0,0,"A"),pin(1,0,"A"),pin(2,0,"B"),pin(3,0,"B")],
    occupied:new Set(["0,0","1,0","2,0","3,0"]),cross:()=>false};
  const edge=(a,b,col)=>({from:p(a,col),to:p(b,col),len:b-a});
  const edges=[edge(0,4,1),edge(1,4,1),edge(2,4,2),edge(3,4,2)];
  if(!conflictRoute(board,ctx,edges).stats.exhausted)throw Error("Original relay competition");
  const out=cutSlideRoute(board,ctx,edges,{probes:10,deep:10,states:128});
  if(!out.successful.some(x=>x.v.replacement.col===1&&copper({...board,cuts:x.v.cuts},ctx.pins,x.wires).complete))
    throw Error("One cut slide creates separate relays");
  if(cutPartition([{col:1,kind:"between"}],[0,4])!==cutPartition([{col:2,kind:"between"}],[0,4]))
    throw Error("Pin partition preservation");
  if(cutPartition([{col:1,kind:"between"}],[0,2,4])===cutPartition([{col:2,kind:"between"}],[0,2,4]))
    throw Error("Pin partition change");
  if(cutPartition([{col:2,kind:"hole"}],[0,2,4])!==null)throw Error("Drilled pin rejection");
  if(edgesForCuts(edges,[{row:4,col:1,kind:"hole"}]).length!==2)throw Error("Candidate drilled endpoints");
  if(physicalEdges(board,ctx).some(e=>ctx.occupied.has(e.from.row+","+e.from.col)||ctx.occupied.has(e.to.row+","+e.to.col)))
    throw Error("Occupied endpoints");
  if(!cutSlideRoute(board,ctx,edges,{probes:0,deep:0}).stats.probeCap)throw Error("Probe cap");
  return 8;
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

console.log("✅",selfTest()+testReachability()+testGroupRoute()+testConflictRoute()+testCutSlideRoute(),"synthetic routing assertions passed");
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
function inspectBoard(saved,input,info,diagnose=false,groupMode=false,conflictMode=false,cutMode=false){
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
  if(diagnose){
    row.reachability={
      retainedReserved:reachability(board,ctx,edges,good,true),
      retainedReusable:reachability(board,ctx,edges,good,false),
      allRipup:reachability(board,ctx,edges,[],false)
    };
    const names=new Map((saved.nets||[]).map(n=>[n.id,n.name]));
    for(const arm of Object.values(row.reachability))for(const n of arm.splits)n.name=names.get(n.net)||n.net;
    row.status="DIAGNOSED";
    row.wall_ms=performance.now()-started;
    console.log("🔬",info.seed,"| unreachable nets (reserved / reusable / full ripup)",
      ...Object.values(row.reachability).map(x=>x.unreachableNets));
    return {row};
  }
  if(cutMode){
    const bareCtx=context({...saved,board:{...board,cuts:[]}});
    const superset=physicalEdges(board,bareCtx);
    const slide=cutSlideRoute(board,bareCtx,superset);
    row.cutSlide={stats:slide.stats,trials:slide.trials,audits:[]};
    let best=null,bestQ=null;
    for(const {v,wires:rawWires} of slide.successful){
      const wires=rawWires.map((w,i)=>({...w,id:"dave-cut-"+sha(JSON.stringify([info.seed,v.i,v.replacement,i,w])).slice(0,20)}));
      const candidate={...saved,board:{...board,cuts:v.cuts,wires}};
      const audit=auditSavedStrict(candidate,input,false),q=q3(candidate),cc=context(candidate);
      const finalGraph=copper(candidate.board,cc.pins,wires);
      const freeEnds=wires.every(w=>[w.from,w.to].every(p=>!cc.occupied.has(key(p))));
      const clean=wires.every(w=>w.from.col===w.to.col&&w.from.row!==w.to.row&&!cc.cross(w));
      const uniqueIds=new Set(wires.map(w=>w.id)).size===wires.length;
      const accepted=audit.valid&&finalGraph.complete&&freeEnds&&clean&&uniqueIds;
      row.cutSlide.audits.push({cutIndex:v.i,old:v.old,replacement:v.replacement,audit,graph:graphReport(finalGraph),freeEnds,clean,uniqueIds,accepted,score:q});
      if(accepted&&(!bestQ||q.q>bestQ.q||(q.q===bestQ.q&&q.w<bestQ.w))){
        best=candidate;bestQ=q;row.after=q;row.method="single_cut_slide";row.cutChange={index:v.i,old:v.old,replacement:v.replacement};
      }
    }
    row.status=best?"STRICT_RESCUE":slide.successful.length?"AUDIT_REJECT":"NO_REPAIR";
    row.wall_ms=performance.now()-started;
    console.log("🔪",info.seed,"| probes",slide.stats.probes,"/",slide.stats.eligible,"| deep",slide.stats.deep,"| routed",slide.successful.length,"| accepted",row.cutSlide.audits.filter(x=>x.accepted).length);
    return {row,best};
  }
  let best=null,bestQ=null;
  for(const [name,initial] of (conflictMode?[["conflict_ripup",[]]]:groupMode?[["group_ripup",[]]]:[["retain_clean",good],["ripup_all",[]]])){
    const trialStart=performance.now();
    const route=conflictMode?conflictRoute(board,ctx,edges):groupMode?groupRoute(board,ctx,edges):boundedRoute(board,ctx,edges,initial);
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
    console.log("🔧",info.seed,name,arm.accepted?"STRICT":arm.found?"AUDIT REJECT":arm.stats.stateCap?"SEARCH CAP":arm.stats.exhausted?"GRAPH INFEASIBLE":"NO PATH",
                "states",arm.stats.states,"queue caps",arm.stats.queueCaps);
  }
  row.wall_ms=performance.now()-started;
  if(best)row.status="STRICT_RESCUE";
  else if(conflictMode){
    const arm=row.arms[0];
    row.status=arm.found?"AUDIT_REJECT":arm.stats.stateCap?"SEARCH_CAP":arm.stats.exhausted?"GRAPH_INFEASIBLE":"NO_REPAIR";
  }
  return {row,best};
}
function main(){
  const [runArg,outArg,...extra]=process.argv.slice(2);
  const diagnose=extra.length===1&&extra[0]==="--diagnose";
  const groupMode=extra.length===1&&extra[0]==="--group-route";
  const conflictMode=extra.length===1&&extra[0]==="--conflict-route";
  const cutMode=extra.length===1&&extra[0]==="--cut-slide";
  if(!runArg||!outArg||(extra.length&&!diagnose&&!groupMode&&!conflictMode&&!cutMode))throw Error("Usage: node scripts/dave_fixed_route.js CAMPAIGN NEW_REPORT_DIR [--diagnose|--group-route|--conflict-route|--cut-slide]");
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
  const work=(cutMode?chosen.filter(x=>[26,94].includes(x.seed)):chosen).map(info=>{
    const entry=bySeed.get(info.seed);
    if(!entry||entry.strictPass||entry.savedJson!==info.saved||entry.savedSha256!==info.sha256)throw Error("Seed identity mismatch");
    const raw=fs.readFileSync(path.join(root,entry.savedJson)),inputRaw=fs.readFileSync(path.join(root,entry.input));
    if(sha(raw)!==info.sha256||!Object.hasOwn(archive.input_hash_counts,sha(inputRaw)))throw Error("Board/input checksum mismatch "+info.seed);
    return {saved:JSON.parse(raw),input:JSON.parse(inputRaw),info};
  });
  fs.mkdirSync(out,{recursive:true});
  const report={sourceCampaign:root,sourceResultsSha256:sha(resultsRaw),sourceManifest:manifest,
    scriptSha256:sha(fs.readFileSync(__filename)),policy:{...(cutMode?{probes:512,deep:32,states:4096,endpointReuse:true,singleCutSameRowAndKind:true,pinPartitionPreserved:true}:conflictMode?{states:4096,endpointReuse:true,neutralRelayConflictSearch:true}:groupMode?{states:512,branches:16,endpointReuse:true,groupForwardCheck:true}:{states:128,hops:4,paths:8,queue:1200}),placementsFixed:true,cutsFixed:!cutMode,annealMoves:0,diagnoseOnly:diagnose,groupMode,conflictMode,cutMode},results:[]};
  const save=()=>{
    fs.writeFileSync(path.join(out,"report.tmp"),JSON.stringify(report,null,2)+"\n");
    fs.renameSync(path.join(out,"report.tmp"),path.join(out,"report.json"));
  };
  for(const item of work){
    console.log("🦈",item.info.seed,"|",item.info.offenders,"offending wires");
    const {row,best}=inspectBoard(item.saved,item.input,item.info,diagnose,groupMode,conflictMode,cutMode);
    if(best){
      row.saved="strict_seed_"+row.seed+".json";
      const raw=JSON.stringify(best,null,2)+"\n";
      fs.writeFileSync(path.join(out,row.saved),raw);row.savedSha256=sha(raw);
      console.log("💥 STRICT RESCUE",row.seed,"Q"+row.beforeQ.q,"→ Q"+row.after.q,row.after.w+"W/"+row.after.c+"C");
    }else if(!diagnose)console.log("❌",row.seed,row.status);
    report.results.push(row);save();
  }
  const count=report.results.filter(x=>x.status==="STRICT_RESCUE").length;
  if(diagnose){
    const lines=["# Dave fixed-cut reachability diagnosis","","No annealing or wire changes. Reachability ignores future endpoint competition, so an unreachable net is a certificate under this model; a reachable net is not proof of jointly routable nets.","",
      "| Seed | Retained (reserved) | Retained (reusable) | Full rip-up |","|---:|---:|---:|---:|",
      ...report.results.map(x=>"| "+x.seed+" | "+(x.reachability?.retainedReserved.unreachableNets??"n/a")+" | "+(x.reachability?.retainedReusable.unreachableNets??"n/a")+" | "+(x.reachability?.allRipup.unreachableNets??"n/a")+" |"),
      "","Cells are counts of nets whose terminal groups are disconnected. See report.json for net names, group coordinates, free attachment holes and disconnected clusters."];
    fs.writeFileSync(path.join(out,"report.md"),lines.join("\n")+"\n");
    console.log("🏁 Reachability diagnosis complete |",out);return;
  }
  const lines=["# Dave fixed-placement routing experiment","",cutMode?"Zero annealing; fixed components; at most one existing cut moved on its row, preserving cut kind/count and component pin partitions. Bounded probes and routing; NO_REPAIR is inconclusive.":"Zero annealing; fixed components and cuts. Repair search bounded. GRAPH_INFEASIBLE means the fixed-cut legal-edge model exhausted all relay-conflict assignments, not universal physical impossibility. SEARCH_CAP or NO_REPAIR is inconclusive.","",
      "| Seed | Result | Before Q3 | After Q3 | Method |","|---:|---|---:|---:|---|",
      ...report.results.map(x=>[x.seed,x.status,x.beforeQ.q,x.after?.q??"—",x.method??"—"].join(" | ")).map(s=>"| "+s+" |"),
      "","Strict rescues: "+count+"/"+work.length,"","Full independent copper graph and saved-board audit results in report.json."];
  fs.writeFileSync(path.join(out,"report.md"),lines.join("\n")+"\n");
  console.log("🏁",count+"/"+work.length,"STRICT RESCUES | zero annealing |",out);
}
main();
