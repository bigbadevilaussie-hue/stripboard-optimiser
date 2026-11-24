#!/usr/bin/env node
// Independent saved-board audit for the native ladder (NO solver invocation).
// Usage: node tests/solver/auditSavedStrict.js saved.json original-prepared-input.json
// Stack overlaps are allowed by default; electrical/geometry/vertical/body
// crossing/physical envelope and original locks remain mandatory.
const fs = require("node:fs");
const path = require("node:path");
const {DEFAULT_COMPONENTS, verify, checkGeometry, resolveComponentDef,
  boardLayout, flexGeometry} = require("./helpers.js");
const {metrics} = require("./metricsLib.js");
const {expandOffBoard} = require(path.join(__dirname,
  "out/components/stripboard/offBoard.js"));
const {packageBodyOutsideBoard} = require(path.join(__dirname,
  "out/components/stripboard/partGeometry.js"));

const asJson = (x) => JSON.stringify(x);
const point = (p) => !!p && Number.isInteger(p.row) &&
  Number.isInteger(p.col);
const inside = (p,b) => point(p) && p.row >= 0 && p.col >= 0 &&
  p.row < b.rows && p.col < b.cols;

function auditSavedStrict(saved, input, noStack = false) {
  const failures = [], warnings = [];
  const b = saved.board ?? {}, orig = input.board ?? {};
  if (b.rows !== orig.rows || b.cols !== orig.cols ||
      b.lockedRows !== orig.lockedRows || b.lockedCols !== orig.lockedCols ||
      !b.lockedRows || !b.lockedCols)
    failures.push("LOCKED_BOARD_CHANGED");
  if (!Number.isInteger(b.rows) || !Number.isInteger(b.cols) ||
      b.rows <= 0 || b.cols <= 0) return {valid:false, failures:["INVALID_BOARD"], warnings};
  if (asJson(input.nets ?? []) !== asJson(saved.nets ?? []) ||
      asJson(input.netAssignments ?? []) !== asJson(saved.netAssignments ?? []) ||
      asJson(input.componentDefs ?? []) !== asJson(saved.componentDefs ?? []))
    failures.push("PROJECT_NETLIST_OR_DEFINITIONS_CHANGED");
  if (input.board?.pattern !== b.pattern)
    failures.push("COPPER_PATTERN_CHANGED");
  const originalParts = input.components ?? [], savedParts = saved.components ?? [];
  const originalById = new Map(originalParts.map(c => [c.id,c]));
  const savedById = new Map(savedParts.map(c => [c.id,c]));
  if (savedById.size !== originalById.size || savedParts.length !== originalParts.length)
    failures.push("COMPONENT_COUNT_CHANGED");
  for (const c of originalParts) {
    const s = savedById.get(c.id);
    if (!s) { failures.push("MISSING_COMPONENT_" + c.id); continue; }
    for (const k of ["defId","offBoard","boardExcluded","value","package","footprintOverride"]) {
      if (asJson(c[k]) !== asJson(s[k]))
        failures.push("COMPONENT_DEFINITION_CHANGED_" + c.id + "_" + k);
    }
    if (c.locked && c.boardPos && (asJson(c.boardPos) !== asJson(s.boardPos) ||
        (c.rotation ?? 0) !== (s.rotation ?? 0) ||
        asJson(c.flexibleEndPos) !== asJson(s.flexibleEndPos)))
      failures.push("LOCKED_PART_MOVED_" + (c.label || c.id));
  }
  const wires = b.wires ?? [], cuts = b.cuts ?? [];
  for (let i=0;i<cuts.length;i++) {
    const cut=cuts[i];
    if (!inside(cut,b) || !["hole","between"].includes(cut.kind) ||
        (cut.kind === "between" && cut.col >= b.cols-1))
      failures.push("ILLEGAL_CUT_" + (i+1));
  }
  let nonvertical=0, stacks=0;
  for (let i=0;i<wires.length;i++) {
    const w=wires[i];
    if (!inside(w.from,b) || !inside(w.to,b))
      failures.push("WIRE_OFF_BOARD_" + (i+1));
    if (!point(w.from) || !point(w.to) ||
        w.from.row===w.to.row || w.from.col!==w.to.col) nonvertical++;
    if (point(w.from) && point(w.to) &&
        flexGeometry.wireStackDepth(w.from,w.to,wires.slice(0,i)) > 0) stacks++;
  }
  if (nonvertical) failures.push("NONVERTICAL_" + nonvertical);
  if (noStack && stacks) failures.push("STACKED_" + stacks);
  const defs = [...DEFAULT_COMPONENTS,...(saved.componentDefs ?? [])];
  const v = expandOffBoard(savedParts, defs, saved.netAssignments ?? []);
  const unplaced = v.components.filter(c => !c.boardExcluded && !c.boardPos);
  if (unplaced.length) failures.push("UNPLACED_" + unplaced.length);
  const missingDef = v.components.filter(c => !c.boardExcluded &&
    !resolveComponentDef(c,defs));
  if (missingDef.length) failures.push("UNRESOLVED_COMPONENT_DEFS_" + missingDef.length);
  if (missingDef.length) return {valid:false, failures, warnings};
  for (const c of v.components) {
    if (!c.boardPos || c.boardExcluded) continue;
    const def=resolveComponentDef(c,defs);
    for (const pin of boardLayout.getComponentPinPositions(c,def))
      if (!inside(pin,b)) failures.push("PIN_OFF_BOARD_" + (c.label||c.id));
    if (packageBodyOutsideBoard(b,c,def)) warnings.push("BODY_OVERHANG_" + (c.label||c.id));
  }
  // Same independent copper graph, net-completeness and exact obstacle checks
  // as the CLI, performed on the SAVED placements, not the old CLI flags.
  const electrical=verify(b,v.components,saved.nets ?? [],v.netAssignments,defs);
  const geometry=checkGeometry(b,v.components,defs);
  const m=metrics(b,v.components,defs,saved.nets ?? [],v.netAssignments);
  if (electrical.conflicts) failures.push("CONFLICTS_" + electrical.conflicts);
  if (electrical.incomplete.length) failures.push("INCOMPLETE_" + electrical.incomplete.length);
  if (geometry.length) failures.push("GEOMETRY_" + geometry.length);
  if (m.crossings) failures.push("BODY_CROSSINGS_" + m.crossings);
  return {
    valid: failures.length===0, failures:[...new Set(failures)],warnings,
    wires:wires.length,cuts:cuts.length,stacked:stacks,nonvertical,
    crossings:m.crossings,conflicts:electrical.conflicts,
    incomplete:electrical.incomplete.length,geometry:geometry.length,
    wireLength:Math.round(wires.reduce((s,w) => s+Math.hypot(
      w.to.row-w.from.row,w.to.col-w.from.col),0)*1000)/1000,
    unplaced:unplaced.map(c=>c.label||c.id),
  };
}
module.exports={auditSavedStrict};
if (require.main===module) {
  const [savedPath,inputPath]=process.argv.slice(2);
  if (!savedPath || !inputPath) {
    console.error("Usage: node tests/solver/auditSavedStrict.js saved.json original-input.json");
    process.exit(64);
  }
  try {
    const result=auditSavedStrict(JSON.parse(fs.readFileSync(savedPath,"utf8")),
      JSON.parse(fs.readFileSync(inputPath,"utf8")),false);
    process.stdout.write(JSON.stringify(result)+"\n");
    if (!result.valid) process.exitCode=2;
  } catch(error) {
    process.stderr.write("AUDIT_ERROR: "+String(error)+"\n");
    process.exitCode=3;
  }
}
