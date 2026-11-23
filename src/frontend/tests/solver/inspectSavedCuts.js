#!/usr/bin/env node
// Inspect preexisting saved projects; does not run a solve, modify a board,
// or require any circuit-specific fixture. Compile TS solver outputs first.
const fs = require("fs");
const path = require("path");
const { DEFAULT_COMPONENTS } = require("./helpers.js");
const { auditKnifeCuts } = require("./knifeCutAudit.js");
const { expandOffBoard } = require(path.join(__dirname, "out/components/stripboard/offBoard.js"));

const files = process.argv.slice(2);
if (!files.length) {
  console.error("Usage: node tests/solver/inspectSavedCuts.js <saved-project.json> [...]");
  process.exit(64);
}
for (const f of files) {
  const d = JSON.parse(fs.readFileSync(f, "utf8"));
  const defs = [...DEFAULT_COMPONENTS, ...(d.componentDefs ?? [])];
  const expanded = expandOffBoard(d.components, defs, d.netAssignments ?? []);
  const report = auditKnifeCuts(d.board, expanded.components, defs, expanded.netAssignments, d.nets ?? []);
  console.log("\n🔬 " + path.basename(f) + " | 🔪 knife cuts: " + report.length);
  for (const c of report) {
    const nearest = (x) => x ? x.component + "." + x.pin + " [" + x.net + "] @" + x.col : "BOARD EDGE";
    console.log("  🔪 row " + c.row + ", between " + c.col + " and " + (c.col + 1) +
      " | " + (c.forcedByAdjacentPins ? "FORCED by adjacent different-net pins" : "NOT forced by directly adjacent pins"));
    console.log("     nearest pins: " + nearest(c.nearestLeft) + " ↔ " + nearest(c.nearestRight));
    for (const flank of c.flanks) {
      console.log("     hole " + flank.col + ": " +
        (flank.basicDrillCandidate ? "possible drill candidate" : "blocked") +
        (flank.pins.length ? " | pins " + flank.pins.map(nearest).join(", ") : "") +
        (flank.wireEndpoints.length ? " | wire endpoints #" + flank.wireEndpoints.join(",") : ""));
    }
  }
  if (!report.length) console.log("  ✅ No knife cuts");
}
