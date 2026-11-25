// GPL-3.0: port of KarloFunke/stripboard-editor at 21e2373f6e1da44ce017be234b2df04f42d3af30.
// StripboardCanvas, PlacedComponent, WireLine, CutMark and globals.css.
import type { Board, Component, ComponentDef, Net, NetAssignment } from "@/types";
import { DEFAULT_COMPONENTS } from "@/data/defaultComponents";
import { boardView } from "@/components/stripboard/offBoard";
import { computeStripSegments } from "@/components/stripboard/stripSegments";
import { computeConnectivity, getGroupForSegment, getGroupForWire } from "@/components/stripboard/connectivity";
import { computeWireLaneOffsets } from "@/components/stripboard/wireLanes";
import { HOLE_SPACING, HOLE_RADIUS, STRIP_HEIGHT, LABEL_FONT_SIZE, STRIP_COLOR, STRIP_CONFLICT_COLOR, holeCenter, boardRect, cutPoint } from "@/components/stripboard/boardLayout";
import { hasHole, joinsDown, joinsRight } from "@/components/stripboard/boardPattern";
import { resolveComponentDef } from "@/utils/resolveComponentDef";
import { partDrawing } from "./part_drawing";
import { renderPartBody } from "./part_body";

const esc=(s:string)=>s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
const n=(v:number)=>String(Math.round(v*10000)/10000);
const line=(x1:number,y1:number,x2:number,y2:number,a:string)=>`<line x1="${n(x1)}" y1="${n(y1)}" x2="${n(x2)}" y2="${n(y2)}" ${a}/>`;
const circle=(x:number,y:number,r:number,a:string)=>`<circle cx="${n(x)}" cy="${n(y)}" r="${r}" ${a}/>`;
const rect=(x:number,y:number,w:number,h:number,a:string)=>`<rect x="${n(x)}" y="${n(y)}" width="${n(w)}" height="${n(h)}" ${a}/>`;

export function renderWebPreview(project:any, highlight?:string):string {
  const board:Board=project.board;
  const defs:ComponentDef[]=[...DEFAULT_COMPONENTS,...(project.componentDefs??[])];
  const components:Component[]=project.components??[];
  const nets:Net[]=project.nets??[];
  const assignments:NetAssignment[]=project.netAssignments??[];
  const view=boardView(components,defs,assignments);
  const segments=computeStripSegments(board,view.components,defs,view.netAssignments);
  const conn=computeConnectivity(segments,board.wires,board);
  const colorOf=(id:string|undefined)=>nets.find(net=>net.id===id)?.color;
  const keys=new Set(board.cuts.map(c=>`${c.kind==="hole"?"h":c.kind==="below"?"v":"b"}:${c.row}:${c.col}`));
  const br=boardRect(board.rows,board.cols), p:string[]=[];
  p.push(rect(br.x,br.y,br.width,br.height,'rx="4" fill="#f0e6d4" stroke="#d8c8ab" stroke-width="1"'));
  // StripboardCanvas: each electrical segment is one translucent strip.
  for(const [i,s] of segments.entries()){
    const g=getGroupForSegment(conn,i);
    const hasNets=g?g.netIds.length>0:s.netIds.length>0;
    const color=g?.hasConflict?STRIP_CONFLICT_COLOR:g?.netIds.length===1?colorOf(g.netIds[0])??STRIP_COLOR:
      s.netIds.length>=2?STRIP_CONFLICT_COLOR:s.netIds.length===1?colorOf(s.netIds[0])??STRIP_COLOR:STRIP_COLOR;
    const holeCut=(r:number,c:number)=>keys.has(`h:${r}:${c}`);
    const down=s.endRow!==undefined;
    if(!down&&s.startCol===s.endCol&&holeCut(s.row,s.startCol))continue;
    const at=(k:number)=>down?holeCenter(k,s.startCol).y:holeCenter(s.row,k).x;
    const first=down?s.row:s.startCol,last=down?s.endRow!:s.endCol;
    const hole=(k:number)=>down?{row:k,col:s.startCol}:{row:s.row,col:k};
    const joins=(k:number)=>down?joinsDown(board,k,s.startCol):joinsRight(board,s.row,k);
    const knife=(k:number)=>keys.has(`${down?"v":"b"}:${hole(k).row}:${hole(k).col}`);
    const start=holeCut(hole(first-1).row,hole(first-1).col)&&joins(first-1)&&!knife(first-1);
    const end=holeCut(hole(last+1).row,hole(last+1).col)&&joins(last)&&!knife(last);
    const lo=start?at(first-1)+HOLE_RADIUS+1.5:at(first)-HOLE_SPACING*.4;
    const hi=end?at(last+1)-HOLE_RADIUS-1.5:at(last)+HOLE_SPACING*.4;
    const mid=down?holeCenter(0,s.startCol).x:holeCenter(s.row,0).y;
    const strip=(a:number,b:number,w:number,attrs:string)=>down?rect(mid-w/2,a,w,b-a,attrs):rect(a,mid-w/2,b-a,w,attrs);
    if(g?.hasConflict)p.push(strip(start?lo:at(first)-HOLE_SPACING*.5,end?hi:at(last)+HOLE_SPACING*.5,STRIP_HEIGHT*2,`fill="${STRIP_CONFLICT_COLOR}" opacity="0.3" rx="2"`));
    p.push(strip(lo,hi,STRIP_HEIGHT,`fill="${esc(color)}" opacity="${g?.hasConflict?0.8:hasNets?0.62:0.55}" rx="1"`));
  }
  for(let r=0;r<board.rows;r++){
    const c=holeCenter(r,0);
    p.push(`<text x="${c.x-30}" y="${c.y+4}" text-anchor="end" font-size="${LABEL_FONT_SIZE}" fill="#737373">${r+1}</text>`);
  }
  for(let col=0;col<board.cols;col++){
    const c=holeCenter(0,col);
    p.push(`<text x="${c.x}" y="${c.y-28}" text-anchor="middle" font-size="${LABEL_FONT_SIZE}" fill="#737373">${col+1}</text>`);
  }
  for(let r=0;r<board.rows;r++)for(let col=0;col<board.cols;col++){
    if(!hasHole(board,r,col))continue;
    const c=holeCenter(r,col);
    p.push(circle(c.x,c.y,HOLE_RADIUS,'fill="#ffffff" stroke="#d4d4d4" stroke-width="0.5"'));
  }
  let left=br.x-35,top=br.y-35,right=br.x+br.width+25,bottom=br.y+br.height+25;
  for(const comp of view.components){
    const def=resolveComponentDef(comp,defs);
    if(!def||!comp.boardPos)continue;
    const d=partDrawing(def,comp,holeCenter,HOLE_SPACING);
    if(!d)continue;
    const selected=comp.id===highlight;
    p.push(`<g data-web-component="${esc(comp.id)}"${selected?' data-web-selected="1"':''}>`,
      renderPartBody(d,{mono:false,outline:selected?"#113768":"#a3a3a3",outlineWidth:selected?0.26:0.12,
        fill:selected?"rgba(17,55,104,0.08)":"rgba(255,255,255,0.85)",strokeWidth:selected?1.5:1,dashed:true}));
    for(const pin of d.pins){
      const c=holeCenter(pin.row,pin.col);
      const a=view.netAssignments.find(a=>a.componentId===comp.id&&a.pinId===pin.pinId);
      const color=colorOf(a?.netId);
      p.push(circle(c.x,c.y,color?5:4.5,`fill="${esc(color??"#ffffff")}" stroke="${color?"#ffffff":"#d4d4d4"}" stroke-width="${color?1.5:0.5}"`));
      if(d.pinNames)p.push(`<text x="${c.x}" y="${c.y+10}" text-anchor="middle" font-size="6" fill="${d.pinOnDark?"#e8e8e8":"#525252"}" stroke="${d.pinOnDark?"rgba(0,0,0,0.6)":"#f0e6d4"}" stroke-width="1.6" paint-order="stroke" stroke-linejoin="round">${esc(def.pins.find(p=>p.id===pin.pinId)?.name??pin.pinId)}</text>`);
    }
    const x=d.label.x+(comp.boardLabelOffset?.x??0),y=d.label.y+(comp.boardLabelOffset?.y??0);
    const attrs=d.label.onBody?`dominant-baseline="central" fill="${d.label.onDark?"#f7f7f7":"#1a1a1a"}" stroke="${d.label.onDark?"rgba(0,0,0,0.6)":"rgba(255,255,255,0.8)"}" stroke-width="3" paint-order="stroke" stroke-linejoin="round"`:'fill="#171717"';
    p.push(`<text x="${n(x)}" y="${n(y)}" text-anchor="middle" font-size="11" font-weight="600" ${attrs}>${esc(comp.label)}`);
    if(project.showValuesOnBoard&&def.hasValue&&comp.value)p.push(`<tspan x="${n(x)}" dy="1.15em" font-weight="400" fill-opacity="0.7">${esc(String(comp.value))}</tspan>`);
    p.push("</text></g>");
    const a=holeCenter(d.bounds.minRow,d.bounds.minCol),b=holeCenter(d.bounds.maxRow,d.bounds.maxCol);
    left=Math.min(left,a.x-30,x-30);right=Math.max(right,b.x+30,x+30);
    top=Math.min(top,a.y-30,y-20);bottom=Math.max(bottom,b.y+30,y+20);
  }
  const offsets=computeWireLaneOffsets(board.wires,3.5);
  for(const w of board.wires){
    const a=holeCenter(w.from.row,w.from.col),b=holeCenter(w.to.row,w.to.col),o=offsets.get(w.id);
    const dx=o?.dx??0,dy=o?.dy??0,g=getGroupForWire(conn,w.id);
    const color=esc(g?.hasConflict?STRIP_CONFLICT_COLOR:g?.netIds.length===1?colorOf(g.netIds[0])??"#a3a3a3":"#a3a3a3");
    p.push(line(a.x+dx,a.y+dy,b.x+dx,b.y+dy,`stroke="${color}" stroke-width="2" stroke-linecap="round" opacity="0.8"`),
      circle(a.x+dx,a.y+dy,4.5,`fill="${color}"`),circle(b.x+dx,b.y+dy,4.5,`fill="${color}"`));
  }
  for(const [i,cut] of board.cuts.entries()){
    const c=cutPoint(cut),s=4,attrs='stroke="#dc2626" stroke-width="2" stroke-linecap="round"';
    p.push(`<g data-web-cut="${i+1}">`,line(c.x-s,c.y-s,c.x+s,c.y+s,attrs),line(c.x+s,c.y-s,c.x-s,c.y+s,attrs),"</g>");
  }
  return `<svg xmlns="http://www.w3.org/2000/svg" data-render-style="web" width="${n(right-left)}" height="${n(bottom-top)}" viewBox="${n(left)} ${n(top)} ${n(right-left)} ${n(bottom-top)}" font-family="Geist, Arial, sans-serif">${p.join("")}</svg>`;
}
