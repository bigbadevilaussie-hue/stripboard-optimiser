#!/usr/bin/env node
// Generic read-only copper corridor diagnosis for a named net in saved layouts.
const fs=require("fs"),path=require("path");
const {computeStripSegments,computeConnectivity,boardLayout,resolveComponentDef,
  flexGeometry,partGeometry}=require("./helpers.js");
const {collectBoardPins,collectOccupiedHoles}=require(path.join(
  __dirname,"out/components/stripboard/boardPins.js"));
const {findSegmentIndex}=require(path.join(
  __dirname,"out/components/stripboard/stripSegments.js"));
const {expandOffBoard}=require(path.join(
  __dirname,"out/components/stripboard/offBoard.js"));
const {DEFAULT_COMPONENTS}=require("./helpers.js");
const argv=process.argv.slice(2), ni=argv.indexOf("--net");
const name=ni<0?null:argv[ni+1];
const files=argv.filter((s,i)=>ni<0 || (i!==ni && i!==ni+1));
if(!files.length){console.error("Usage: node inspectNetCorridors.js file.json [...] --net netName");process.exit(64)}
for(const file of files){
  const d=JSON.parse(fs.readFileSync(file,"utf8"));
  const defs=[...DEFAULT_COMPONENTS,...(d.componentDefs||[])];
  const v=expandOffBoard(d.components,defs,d.netAssignments||[]);
  const comps=v.components,asg=v.netAssignments,b=d.board;
  if(b.pattern){console.log("⚠️ Patterned board: horizontal-strip corridor audit skipped");continue}
  const nets=d.nets.filter(n=>!name||n.name===name||n.id===name);
  const segs=computeStripSegments(b,comps,defs,asg), conn=computeConnectivity(segs,b.wires,b);
  const groupOf=new Map();
  conn.forEach((g,gi)=>g.segmentIndices.forEach(si=>groupOf.set(si,gi)));
  const occupied=collectOccupiedHoles(b,comps,defs,collectBoardPins(b,comps,defs,asg));
  const used=new Set((b.wires||[]).flatMap(w=>[w.from,w.to].map(p=>p.row+":"+p.col)));
  const rects=[], bodies=[];
  for(const c of comps){
    if(!c.boardPos||c.boardExcluded)continue;
    const def=resolveComponentDef(c,defs);
    if(!def)continue;
    if(def.flexible){
      const [a,z]=boardLayout.getFlexiblePinPositions(c,def);
      if(a&&z)bodies.push(partGeometry.flexWireObstacle(def,a,z));
    }else rects.push(partGeometry.rigidBody(def,c.boardPos,c.rotation));
  }
  const geomClean=(a,z)=>!rects.some(r=>flexGeometry.segmentIntersectsRect(a,z,r)) &&
    !bodies.some(r=>flexGeometry.wireCrossesBody(a,z,r)) &&
    !flexGeometry.wireStackDepth(a,z,b.wires||[]);
  console.log("\n🔬 "+path.basename(file)+" | "+b.rows+"x"+b.cols);
  for(const net of nets){
    const owners=new Map();
    const original=asg.filter(a=>a.netId===net.id);
    for(const a of original){
      const c=comps.find(c=>c.id===a.componentId);
      if(!c||!c.boardPos||c.boardExcluded)continue;
      const def=resolveComponentDef(c,defs);
      if(!def)continue;
      const p=boardLayout.getComponentPinPositions(c,def).find(p=>p.pinId===a.pinId);
      if(!p)continue;
      const si=findSegmentIndex(segs,p.row,p.col),gi=groupOf.get(si);
      if(gi===undefined)continue;
      if(!owners.has(gi))owners.set(gi,[]);
      const pin=def.pins.find(x=>x.id===a.pinId);
      owners.get(gi).push({part:c.label||c.id,pin:pin?.name||a.pinId,row:p.row,col:p.col});
    }
    const clusters=[...owners].map(([gi,pins],i)=>{
      const holes=[];
      for(const si of conn[gi].segmentIndices){
        const s=segs[si];
        for(let col=s.startCol;col<=s.endCol;col++){
          const row=s.row,k=row+":"+col;
          if(row>=0&&row<b.rows&&col>=0&&col<b.cols&&!occupied.has(k)&&!used.has(k))
            holes.push({row,col});
        }
      }
      return {id:i+1,pins,holes,cols:[...new Set(holes.map(h=>h.col))]};
    });
    console.log("   🔌 "+net.name+" | "+clusters.length+" connected pin group(s)");
    for(const c of clusters){
      const desc=c.pins.map(p=>p.part+"."+p.pin+"@("+p.row+","+p.col+")").join("; ");
      console.log("      GROUP "+c.id+": "+desc+" | "+c.holes.length+" free solder holes");
    }
    for(let i=0;i<clusters.length;i++)for(let j=i+1;j<clusters.length;j++){
      const a=clusters[i],z=clusters[j],shared=a.cols.filter(col=>z.cols.includes(col));
      let clean=[];
      for(const col of shared){
        const ah=a.holes.filter(h=>h.col===col),zh=z.holes.filter(h=>h.col===col);
        let shortest=null;
        for(const from of ah)for(const to of zh){
          if(from.row===to.row||!geomClean(from,to))continue;
          const len=Math.abs(to.row-from.row);
          if(!shortest||len<shortest.len)shortest={from,to,len};
        }
        if(shortest)clean.push({col,...shortest});
      }
      clean.sort((x,y)=>x.len-y.len);
      console.log("      ↕️ GROUP "+a.id+"↔"+z.id+": shared free cols="+shared.length+
        ", clean vertical candidates="+clean.length+
        (clean.length?" | best="+JSON.stringify(clean[0]):""));
    }
  }
}
