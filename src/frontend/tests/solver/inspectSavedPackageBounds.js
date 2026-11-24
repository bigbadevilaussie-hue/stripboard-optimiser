#!/usr/bin/env node
// Read-only physical-package boundary audit of an existing saved JSON.
// No annealing, edits, or electrical PASS claims. Compile tests/solver/tsconfig first.
const fs = require("node:fs");
const path = require("node:path");
const { DEFAULT_COMPONENTS, checkGeometry, resolveComponentDef } = require("./helpers.js");
const { packageBodyOutsideBoard } = require(path.join(__dirname,
  "out/components/stripboard/partGeometry.js"));
const { expandOffBoard } = require(path.join(__dirname,
  "out/components/stripboard/offBoard.js"));

const filenames = process.argv.slice(2);
if (!filenames.length) {
  console.error("Usage: node tests/solver/inspectSavedPackageBounds.js <saved-project.json> [...]");
  process.exit(64);
}
for (const filename of filenames) {
  const data = JSON.parse(fs.readFileSync(filename,"utf8"));
  const defs = [...DEFAULT_COMPONENTS,...(data.componentDefs ?? [])];
  const view = expandOffBoard(data.components, defs, data.netAssignments ?? []);
  const faults = [];
  for (const c of view.components) {
    if (!c.boardPos || c.boardExcluded) continue;
    const def = resolveComponentDef(c,defs);
    if (!def) continue;
    if (packageBodyOutsideBoard(data.board,c,def)) {
      faults.push(c);
    }
  }
  console.log("🔬 " + path.basename(filename) + " | board " +
    data.board.rows + "×" + data.board.cols);
  for (const c of faults) {
    console.log("⚠️ BODY OVERHANG " + (c.label || c.id) +
      (c.value ? " ("+c.value+")" : "") + " @ row " + c.boardPos.row +
      ", col " + c.boardPos.col +
      (c.flexibleEndPos ? " → row "+c.flexibleEndPos.row+", col "+c.flexibleEndPos.col : ""));
  }
  const all = checkGeometry(data.board,view.components,defs);
  console.log(faults.length ? "⚠️ " + faults.length + " build warnings for package-body overhang" :
    "✅ No package-body overhang warnings");
  console.log("Geometry findings: " + all.length);
  if (all.length) for (const s of all.slice(0,25)) console.log("  - " + s);
  if (all.length) process.exitCode = 2; // warnings alone are nonfatal
}
