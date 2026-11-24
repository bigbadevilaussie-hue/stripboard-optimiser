#!/usr/bin/env node
const assert = require("node:assert/strict");
const path = require("node:path");
const fixture = require(path.resolve(__dirname, "../../../../test-fixtures/masters/audio/audioex.json"));
const { DEFAULT_COMPONENTS, boardLayout, resolveComponentDef } = require("./helpers.js");
const { lockedAdjacentDrillConflicts } = require("./drilledFeasibility.js");
const defs = [...DEFAULT_COMPONENTS, ...fixture.componentDefs];
const failures = lockedAdjacentDrillConflicts(
  fixture.components, defs, fixture.netAssignments,
  boardLayout.getComponentPinPositions, resolveComponentDef);
const hits = failures.filter(x => x.component === "BMS" && x.row === 9);
assert.ok(hits.some(x => x.leftCol === 26 && x.rightCol === 27),
  "BMS 26/27 requires a between-hole knife cut");
assert.ok(hits.some(x => x.leftCol === 27 && x.rightCol === 28),
  "BMS 27/28 requires a between-hole knife cut");
assert.ok(hits.every(x => x.reason === "ADJACENT_DIFFERENT_NET_PADS_REQUIRE_KNIFE_CUT"));
assert.deepEqual(lockedAdjacentDrillConflicts([], defs, [], boardLayout.getComponentPinPositions,
  resolveComponentDef), []);
console.log("✅ AUDIOEX locked BMS drill-only impossibility preflight: PASS");
