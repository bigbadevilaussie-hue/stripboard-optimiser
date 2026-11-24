#!/usr/bin/env node
"use strict";
/**
 * 100-check read-only JSON + KiCad netlist preflight for the locked 24x56
 * Audio and Moto WR campaign. Node built-ins only; never starts the solver.
 * Hard FAIL = source contract defect. WARN = heuristic planning flag,
 * NOT evidence of an invalid circuit. It cannot certify physical routing.
 * Usage: node scripts/audit_100_audio_moto.js [--json] [--out FILE]
 */
const fs = require("node:fs");
const path = require("node:path");
function auditProject(data, netText, name) {
  const isObj=x=>x!==null&&typeof x==="object"&&!Array.isArray(x);
  const arr=x=>Array.isArray(x)?x:[];
  const uniq=x=>new Set(x).size===x.length;
  const integer=x=>Number.isInteger(x);
  const nonblank=x=>typeof x==="string"&&x.trim().length>0;
  const all=(xs,fn)=>xs.every(fn);
  const comp=arr(data.components), defs=arr(data.componentDefs), nets=arr(data.nets), asg=arr(data.netAssignments);
  const board=isObj(data.board)?data.board:{};
  const defById=new Map(defs.map(x=>[x.id,x]));
  const compById=new Map(comp.map(x=>[x.id,x]));
  const netById=new Map(nets.map(x=>[x.id,x]));
  const on=comp.filter(x=>!x.offBoard&&!x.boardExcluded), off=comp.filter(x=>x.offBoard||x.boardExcluded);
  const knownOn=on.filter(x=>defById.has(x.defId));
  const unknown=on.filter(x=>!defById.has(x.defId));
  const unknownCustom=unknown.filter(x=>String(x.defId).startsWith("custom-"));
  const wh=Number(board.rows)*Number(board.cols);
  const knownGross=knownOn.reduce((s,c)=>{const d=defById.get(c.defId);return s+d.width*d.height;},0);
  const knownBody=knownOn.reduce((s,c)=>s+arr(defById.get(c.defId).bodyCells).length,0);
  const knownPins=knownOn.reduce((s,c)=>s+arr(defById.get(c.defId).pins).length,0);
  const assignedKnown=asg.filter(a=>defById.has(compById.get(a.componentId)?.defId));
  const pinIds=d=>arr(d.pins).map(p=>String(p.id));
  const netCounts=new Map(nets.map(n=>[n.id,0]));
  const netComps=new Map(nets.map(n=>[n.id,new Set()]));
  for(const a of asg) {
    netCounts.set(a.netId,(netCounts.get(a.netId)||0)+1);
    if(netComps.has(a.netId)) netComps.get(a.netId).add(a.componentId);
  }
  const topNets=nets.map(n=>({name:n.name,pins:netCounts.get(n.id)||0,components:netComps.get(n.id)?.size||0})).sort((a,b)=>b.pins-a.pins);
  const netEdges=topNets.reduce((s,n)=>s+Math.max(0,n.pins-1),0);
  const jsonTriples=asg.map(a=>[netById.get(a.netId)?.name,compById.get(a.componentId)?.label,String(a.pinId)].join("\u0000"));
  const parts=String(netText).split(/\(net\s+\(code\s+"[^"]+"\)\s+\(name\s+"([^"]+)"\)/g);
  const netTriples=[],netBlockNames=[];
  for(let i=1;i<parts.length;i+=2) {
    const netname=parts[i]; netBlockNames.push(netname);
    for(const match of parts[i+1].matchAll(/\(node\s+\(ref\s+"([^"]+)"\)\s+\(pin\s+"([^"]+)"\)/g))netTriples.push([netname,match[1],match[2]].join("\u0000"));
  }
  const netNodesIn=new Set(netTriples), jsonNodesIn=new Set(jsonTriples);
  const sameSets = (a,b)=>a.size===b.size&&[...a].every(x=>b.has(x));
  const warnings=[];
  const checks=[];
  function check(id,group,title,ok,detail="",kind="hard") {
    checks.push({id,group,title,status:ok?"PASS":kind==="hard"?"FAIL":"WARN",detail});
  }
  function info(id,group,title,value){checks.push({id,group,title,status:"INFO",detail:String(value)});}
  function risk(id,title,ok,detail) {check(id,"Search pressure",title,ok,detail,"risk");}
  const rot=c=>integer(c.rotation??0)&&[0,90,180,270].includes(c.rotation??0);
  const validPos=c=>!c.boardPos||(integer(c.boardPos.row)&&integer(c.boardPos.col));
  const knownDefPins=assignedKnown.every(a=>pinIds(defById.get(compById.get(a.componentId).defId)).includes(String(a.pinId)));
  const placementWithin=on.filter(c=>c.boardPos&&defById.has(c.defId)).every(c=>{const d=defById.get(c.defId),swap=(c.rotation??0)%180!==0;const h=swap?d.width:d.height,w=swap?d.height:d.width;return c.boardPos.row>=0&&c.boardPos.col>=0&&c.boardPos.row+h<=board.rows&&c.boardPos.col+w<=board.cols;});
  const group="Project";
  check("A01",group,"Project root is JSON object",isObj(data));
  check("A02",group,"Project has nonempty name",nonblank(data.name));
  check("A03",group,"Project version is recorded",typeof data.version==="string"||typeof data.version==="number");
  check("A04",group,"Components field is an array",Array.isArray(data.components));
  check("A05",group,"Component definitions field is an array",Array.isArray(data.componentDefs));
  check("A06",group,"Nets field is an array",Array.isArray(data.nets));
  check("A07",group,"Net assignments field is an array",Array.isArray(data.netAssignments));
  check("A08",group,"Board field is an object",isObj(data.board));
  check("A09",group,"Schematic wires field is an array",Array.isArray(data.schematicWires));
  check("A10",group,"Project identity fields are serializable",(()=>{try{return JSON.stringify(data).length>0;}catch{return false;}})());
  check("B01","Board","Row count is positive integer",integer(board.rows)&&board.rows>0);
  check("B02","Board","Column count is positive integer",integer(board.cols)&&board.cols>0);
  check("B03","Board","Rows obey requested 24-row lock",board.rows===24,String(board.rows));
  check("B04","Board","Columns obey requested 56-column lock",board.cols===56,String(board.cols));
  check("B05","Board","Row lock is enabled",board.lockedRows===true);
  check("B06","Board","Column lock is enabled",board.lockedCols===true);
  check("B07","Board","Board has at least 1000 physical holes",wh>=1000,String(wh));
  check("B08","Board","Cuts are an array",Array.isArray(board.cuts));
  check("B09","Board","Wires are an array",Array.isArray(board.wires));
  check("B10","Board","Discovery input starts without copper edits",arr(board.cuts).length===0&&arr(board.wires).length===0,`${arr(board.cuts).length} cuts / ${arr(board.wires).length} wires`);
  check("C01","Components","Component list is not empty",comp.length>0,String(comp.length));
  check("C02","Components","Each component has an ID",all(comp,c=>nonblank(c.id)));
  check("C03","Components","Component IDs are unique",uniq(comp.map(c=>c.id)));
  check("C04","Components","Each component has a definition reference",all(comp,c=>nonblank(c.defId)));
  check("C05","Components","Each component has a label",all(comp,c=>nonblank(c.label)));
  check("C06","Components","Component labels are unique",uniq(comp.map(c=>c.label)));
  check("C07","Components","At least one part is assigned to the board",on.length>0,String(on.length));
  check("C08","Components","Off-board flags are booleans when present",all(comp,c=>["offBoard","boardExcluded"].every(k=>c[k]===undefined||typeof c[k]==="boolean")));
  check("C09","Components","No component uses duplicate ID+label pairs",uniq(comp.map(c=>`${c.id}|${c.label}`)));
  check("C10","Components","Every component rotation is a quarter turn",all(comp,rot));
  check("D01","Placement","Positions are null or integer row/column",all(comp,validPos));
  check("D02","Placement","No unplaced component is marked locked",all(comp,c=>!(c.locked&&!c.boardPos)));
  check("D03","Placement","No component is both edge and slide-locked",all(comp,c=>!(c.edge===true&&c.slide===true&&c.locked===true)),"Rigid edge+slide requires explicit review","risk");
  check("D04","Placement","Placed on-board embedded parts fit locked board",placementWithin);
  check("D05","Placement","Board positions use row and col keys",all(comp,c=>!c.boardPos||("row"in c.boardPos&&"col"in c.boardPos)));
  check("D06","Placement","No off-board component is fixed in-board",all(off,c=>!c.boardPos||c.offBoard),"Off-board placement requires review","risk");
  check("D07","Placement","Existing placed components have valid rotation",all(comp.filter(c=>c.boardPos),rot));
  check("D08","Placement","Component flags locked/edge/slide are booleans",all(comp,c=>["locked","edge","slide"].every(k=>c[k]===undefined||typeof c[k]==="boolean")));
  check("D09","Placement","No initial copper jumper is preset",arr(board.wires).length===0);
  check("D10","Placement","No initial copper cut is preset",arr(board.cuts).length===0);
  check("E01","Definitions","Embedded definition IDs are populated",all(defs,d=>nonblank(d.id)));
  check("E02","Definitions","Embedded definition IDs are unique",uniq(defs.map(d=>d.id)));
  check("E03","Definitions","Embedded definition names are populated",all(defs,d=>nonblank(d.name)));
  check("E04","Definitions","Widths are positive integers",all(defs,d=>integer(d.width)&&d.width>0));
  check("E05","Definitions","Heights are positive integers",all(defs,d=>integer(d.height)&&d.height>0));
  check("E06","Definitions","Pin lists are present",all(defs,d=>Array.isArray(d.pins)));
  check("E07","Definitions","Each embedded definition has at least one pad",all(defs,d=>arr(d.pins).length>0));
  check("E08","Definitions","Embedded pad IDs are nonblank",all(defs,d=>all(arr(d.pins),p=>nonblank(String(p.id??"")))));
  check("E09","Definitions","Embedded pad IDs are unique per definition",all(defs,d=>uniq(pinIds(d))));
  check("E10","Definitions","Every custom- ID used by a component resolves locally",unknownCustom.length===0,`${unknownCustom.length} missing custom definitions`);
  check("F01","Footprints","Embedded pad offsets are integer grid positions",all(defs,d=>all(arr(d.pins),p=>integer(p.offsetRow)&&integer(p.offsetCol))));
  check("F02","Footprints","Embedded pads lie inside their footprint",all(defs,d=>all(arr(d.pins),p=>p.offsetRow>=0&&p.offsetCol>=0&&p.offsetRow<d.height&&p.offsetCol<d.width)));
  check("F03","Footprints","No two pads occupy one footprint coordinate",all(defs,d=>uniq(arr(d.pins).map(p=>`${p.offsetRow},${p.offsetCol}`))));
  check("F04","Footprints","BodyCells are arrays when supplied",all(defs,d=>d.bodyCells===undefined||Array.isArray(d.bodyCells)));
  check("F05","Footprints","BodyCells use integer coordinates",all(defs,d=>all(arr(d.bodyCells),c=>integer(c.row)&&integer(c.col))));
  check("F06","Footprints","BodyCells lie inside footprint extents",all(defs,d=>all(arr(d.bodyCells),c=>c.row>=0&&c.col>=0&&c.row<d.height&&c.col<d.width)));
  check("F07","Footprints","BodyCells have no duplicate locations",all(defs,d=>uniq(arr(d.bodyCells).map(c=>`${c.row},${c.col}`))));
  check("F08","Footprints","Embedded footprints fit board dimensions unrotated",all(defs,d=>d.width<=board.cols&&d.height<=board.rows));
  check("F09","Footprints","Custom component pads referenced by nets actually exist",knownDefPins);
  check("F10","Footprints","Known on-board footprint gross area fits board as a lower bound",knownGross<=wh,`${knownGross}/${wh} known-only bounding-box hole-equivalents; omits built-ins`,"risk");
  check("G01","Nets","Net list is not empty",nets.length>0,String(nets.length));
  check("G02","Nets","Net IDs populated",all(nets,n=>nonblank(n.id)));
  check("G03","Nets","Net IDs unique",uniq(nets.map(n=>n.id)));
  check("G04","Nets","Net names populated",all(nets,n=>nonblank(n.name)));
  check("G05","Nets","Net names unique",uniq(nets.map(n=>n.name)));
  check("G06","Nets","Ground net exists",nets.some(n=>String(n.name).toUpperCase()==="GND"));
  check("G07","Nets","At least two nets used",topNets.filter(n=>n.pins).length>=2);
  check("G08","Nets","Every declared net has an assignment",topNets.every(n=>n.pins>0));
  check("G09","Nets","Net pin totals do not exceed assignments",topNets.reduce((s,n)=>s+n.pins,0)===asg.length);
  check("G10","Nets","Every used net has a component endpoint",nets.every(n=>netComps.get(n.id)?.size>0));
  check("H01","Assignments","At least one net pin is assigned",asg.length>0,String(asg.length));
  check("H02","Assignments","Every assignment has component ID",all(asg,a=>nonblank(a.componentId)));
  check("H03","Assignments","Every assignment has net ID",all(asg,a=>nonblank(a.netId)));
  check("H04","Assignments","Every assignment has pin ID",all(asg,a=>nonblank(String(a.pinId??""))));
  check("H05","Assignments","Every referenced component exists",all(asg,a=>compById.has(a.componentId)));
  check("H06","Assignments","Every referenced net exists",all(asg,a=>netById.has(a.netId)));
  check("H07","Assignments","No physical component-pin mapped twice",uniq(asg.map(a=>`${a.componentId}|${a.pinId}`)));
  check("H08","Assignments","No exact duplicate component-pin-net tuple",uniq(asg.map(a=>`${a.componentId}|${a.pinId}|${a.netId}`)));
  check("H09","Assignments","Embedded-component pin assignments resolve",knownDefPins);
  check("H10","Assignments","At least one assigned on-board component exists",asg.some(a=>on.some(c=>c.id===a.componentId)));
  check("I01","Netlist","Paired netlist text exists",nonblank(netText));
  check("I02","Netlist","KiCad export marker exists",/\(export\s+\(version\s+"E"\)/.test(netText));
  check("I03","Netlist","Design section exists",/\(design\s+\(source/.test(netText));
  check("I04","Netlist","Components section exists",/\(components\b/.test(netText));
  check("I05","Netlist","Nets section exists",/\(nets\b/.test(netText));
  check("I06","Netlist","Net parser found numbered net sections",netBlockNames.length>0,String(netBlockNames.length));
  check("I07","Netlist","Net parser found referenced pins",netTriples.length>0,String(netTriples.length));
  check("I08","Netlist","Netlist pins are unique",uniq(netTriples));
  check("I09","Netlist","JSON assignment triples are unique",uniq(jsonTriples));
  check("I10","Netlist","Exact KiCad-to-JSON (net,part,pin) parity",sameSets(netNodesIn,jsonNodesIn),`netlist ${netNodesIn.size}; JSON ${jsonNodesIn.size}; missing JSON ${[...netNodesIn].filter(x=>!jsonNodesIn.has(x)).length}; missing netlist ${[...jsonNodesIn].filter(x=>!netNodesIn.has(x)).length}`);
  risk("J01","On-board parts <=20 (planning threshold)",on.length<=20,`${on.length} on-board`);
  risk("J02","Assigned pins <=100 (planning threshold)",asg.length<=100,`${asg.length} pins`);
  risk("J03","Net count <=30 (planning threshold)",nets.length<=30,`${nets.length} nets`);
  risk("J04","Off-board parts <=8 (planning threshold)",off.length<=8,`${off.length} off-board`);
  risk("J05","Largest net <=20 pins (planning threshold)",(topNets[0]?.pins||0)<=20,`${topNets[0]?.name||"none"}: ${topNets[0]?.pins||0} pins`);
  risk("J06","Largest net spans <=20 components (planning threshold)",(topNets[0]?.components||0)<=20,`${topNets[0]?.name||"none"}: ${topNets[0]?.components||0} parts`);
  risk("J07","Built-in definitions needed for <=15 on-board parts",unknown.length<=15,`${unknown.length} parts require built-in library geometry`);
  risk("J08","Estimated net connection edges <=70 (planning threshold)",netEdges<=70,`${netEdges} abstract net edges (not routing lower bound)`);
  risk("J09","On-board custom gross area <=65% board (partial data)",wh>0&&knownGross/wh<=0.65,`${(knownGross/wh*100).toFixed(1)}% known custom rectangle gross area; incomplete coverage`);
  risk("J10","Custom largest width <= one-third of board columns",defs.every(d=>d.width<=board.cols/3),`largest embedded width ${Math.max(0,...defs.map(d=>d.width))} versus ${board.cols} cols`);
  if(checks.length!==100||new Set(checks.map(x=>x.id)).size!==100)throw Error(`Expected 100 independent checks, got ${checks.length}`);
  const totals={PASS:0,FAIL:0,WARN:0,INFO:0};for(const c of checks)totals[c.status]++;
  const metrics={boardRows:board.rows,boardCols:board.cols,onBoardParts:on.length,offBoardParts:off.length,components:comp.length,netCount:nets.length,assignedPins:asg.length,embeddedDefinitions:defs.length,onBoardWithEmbeddedFootprint:knownOn.length,onBoardWithBuiltinFootprint:unknown.length,missingCustomDefinitions:unknownCustom.length,knownGrossFootprintArea:knownGross,knownBodyCells:knownBody,knownPads:knownPins,knownGrossBoardFraction:+(knownGross/wh).toFixed(3),netEdgeProxy:netEdges,largestNet:topNets[0],topNets:topNets.slice(0,6),unplacedComponents:comp.filter(c=>!c.boardPos&&!c.offBoard&&!c.boardExcluded).length};
  return {circuit:name,counts:totals,checks,metrics,warnings:checks.filter(c=>c.status!=="PASS")};
}
function main(){
  const root=path.resolve(__dirname,"..");
  const args=process.argv.slice(2);
  if(args.some(a=>!["--json","--out"].includes(a)&&!args.includes("--out"))) throw Error("Usage: node scripts/audit_100_audio_moto.js [--json] [--out FILE]");
  const results=["audio","moto"].map(name=>{
    const base=path.join(root,"test-fixtures","masters",name,name);
    return auditProject(JSON.parse(fs.readFileSync(base+".json","utf8")),fs.readFileSync(base+".net","utf8"),name);
  });
  const result={schema:"audio-moto-preflight-100/v1",scope:"static JSON+KiCad audit only; native strict output certification requires saved-board auditor",results};
  const json=JSON.stringify(result,null,2)+"\n";
  const outIndex=args.indexOf("--out");
  if(outIndex>=0){
    if(!args[outIndex+1]) throw Error("--out requires a filename");
    fs.writeFileSync(args[outIndex+1],json);
  }
  if(args.includes("--json"))process.stdout.write(json);
  else for(const r of results) {
    console.log(`${r.circuit.toUpperCase()} | 100 checks | ${r.counts.PASS} PASS / ${r.counts.WARN} planning WARN / ${r.counts.FAIL} FAIL | ${r.metrics.onBoardParts} on-board parts, ${r.metrics.assignedPins} assigned pins, ${r.metrics.netEdgeProxy} net-edge proxy`);
    for(const w of r.warnings) console.log(`  ${w.id} [${w.status}] ${w.title}: ${w.detail}`);
  }
  if(results.some(r=>r.counts.FAIL>0))process.exitCode=1;
}
if(require.main===module)main();
module.exports={auditProject};
