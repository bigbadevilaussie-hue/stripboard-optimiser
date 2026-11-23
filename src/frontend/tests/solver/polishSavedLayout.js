#!/usr/bin/env node
// Run the SAME generic v5 fixed-board local polish on an already saved board.
// Optional --out writes a NEW JSON. Never modifies the input file.
const fs = require("fs");
const path = require("path");
const { DEFAULT_COMPONENTS, verify, checkGeometry } = require("./helpers.js");
const { metrics } = require("./metricsLib.js");
const { expandOffBoard } = require(path.join(__dirname, "out/components/stripboard/offBoard.js"));
const { polishFixedBoardWires } = require(path.join(__dirname, "out/components/stripboard/wireColumnPolish.js"));
const files = process.argv.slice(2).filter((x) => x !== "--out");
const outAt = process.argv.indexOf("--out");
const out = outAt >= 0 ? process.argv[outAt + 1] : null;
if (outAt >= 0 && (!out || process.argv.length - 1 !== outAt + 1)) {
  console.error("Usage: node tests/solver/polishSavedLayout.js file.json [--out different.json]");
  process.exit(64);
}
if (files.length !== (out ? 2 : 1)) {
  console.error("Usage: node tests/solver/polishSavedLayout.js file.json [--out different.json]");
  process.exit(64);
}
const input = files[0];
const data = JSON.parse(fs.readFileSync(input, "utf8"));
const defs = [...DEFAULT_COMPONENTS, ...(data.componentDefs || [])];
const expanded = expandOffBoard(data.components, defs, data.netAssignments || []);
const board = data.board;
const baseline = {
  placements:[], cuts:board.cuts, wires:board.wires.map((w) => ({from:w.from,to:w.to})),
  issues:[], quality:0, starvedNetIds:[],
  boardSize:{rows:board.rows,cols:board.cols},
};
const verifyNow = (b) => {
  const e=verify(b,expanded.components,data.nets,expanded.netAssignments,defs);
  const m=metrics(b,expanded.components,defs,data.nets,expanded.netAssignments);
  const stacked=b.wires.filter((w,i) =>
    require("./helpers.js").flexGeometry.wireStackDepth(
      w.from,w.to,b.wires.slice(0,i))>0).length;
  return { conflicts:e.conflicts,incomplete:e.incomplete.length,
    geometry:checkGeometry(b,expanded.components,defs).length,
    offAxis:m.offAxisWires,
    nonvertical:b.wires.filter((w)=>w.from.col!==w.to.col).length,
    crossings:m.crossings,stacked,knife:b.cuts.filter((c)=>c.kind!=="hole").length,
    wires:b.wires.length,cuts:b.cuts.length,board:`${b.rows}x${b.cols}` };
};
const before=verifyNow(board);
const polished=polishFixedBoardWires(board,expanded.components,defs,
  data.nets,expanded.netAssignments,baseline);
const finalBoard={...board,cuts:polished.result.cuts,
  wires:polished.result.wires.map((w,i)=>({...w,id:board.wires[i]?.id||"p-"+i}))};
const after=verifyNow(finalBoard);
const critical=["conflicts","incomplete","geometry","nonvertical","crossings","stacked","knife"];
const regress=critical.filter((key)=>after[key]>before[key]);
if (after.board!==before.board) regress.push("board");
console.log("🔬 "+path.basename(input)+" | 24x56 if fixture locked, original dimensions otherwise");
console.log("🧷 BEFORE "+JSON.stringify(before));
console.log("✅ AFTER  "+JSON.stringify(after));
console.log("🛠️ LOCAL  "+JSON.stringify(polished.stats));
if (regress.length) {
  console.error("❌ INDEPENDENT REGRESSION: "+regress.join(", "));
  process.exit(2);
}
if (out) {
  if (path.resolve(input)===path.resolve(out)) {
    console.error("❌ Output must be different from input");
    process.exit(64);
  }
  fs.writeFileSync(out,JSON.stringify({...data,board:finalBoard},null,2)+"\n");
  console.log("💾 Wrote independent copy: "+out);
}
console.log(after.nonvertical===0 && after.crossings===0 && after.stacked===0 &&
  after.knife===0 && after.conflicts===0 && after.incomplete===0 &&
  after.geometry===0 ? "🏆 STRICT PHYSICAL PASS" : "🛠️ Improved/unchanged but NOT YET STRICT PASS");
