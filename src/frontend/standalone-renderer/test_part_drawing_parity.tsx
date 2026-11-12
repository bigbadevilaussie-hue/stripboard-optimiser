// Parity test: copied partDrawing() vs original partDrawing() for every placed
// component in motomix.json.

import * as fs from "fs";
import { DEFAULT_COMPONENTS } from "@/data/defaultComponents";
import { resolveComponentDef } from "@/utils/resolveComponentDef";
import { HOLE_SPACING, holeCenter } from "@/components/stripboard/boardLayout";
import { partDrawing as originalPartDrawing } from "@/components/stripboard/partDrawing";
import { partDrawing as copiedPartDrawing } from "./part_drawing";
import type { Component, ComponentDef } from "@/types";

const projectData = JSON.parse(fs.readFileSync("/Users/nick/Desktop/repo/moto14wires30cuts.json", "utf8"));
const componentDefs: ComponentDef[] = [...DEFAULT_COMPONENTS, ...(projectData.componentDefs ?? [])];
const components: Component[] = projectData.components ?? [];

function normalise(v: any): any {
  if (v === null || v === undefined) return v;
  if (typeof v === "number") return Number.isInteger(v) ? v : Math.round(v * 1e6) / 1e6;
  if (Array.isArray(v)) return v.map(normalise);
  if (typeof v === "object") {
    const out: any = {};
    for (const k of Object.keys(v).sort()) out[k] = normalise(v[k]);
    return out;
  }
  return v;
}

console.log("=== part_drawing parity: copied vs original ===\n");
const placed = components.filter((c) => c.boardPos !== null);
console.log(`Placed components: ${placed.length}\n`);

let pass = 0, fail = 0;
for (const c of placed) {
  const def = resolveComponentDef(c, componentDefs);
  if (!def) { console.log(`UNRESOLVED: ${c.label} (${c.defId})`); continue; }

  const at = (row: number, col: number) => holeCenter(row, col);
  const a = originalPartDrawing(def, c, at, HOLE_SPACING);
  const b = copiedPartDrawing(def, c, at, HOLE_SPACING);

  const na = JSON.stringify(normalise(a));
  const nb = JSON.stringify(normalise(b));

  if (na === nb) {
    console.log(`${c.label} (${def.id}): MATCH (${na.length} chars)`);
    pass++;
  } else {
    console.log(`${c.label} (${def.id}): DIFF`);
    let i = 0;
    while (i < na.length && i < nb.length && na[i] === nb[i]) i++;
    console.log(`  First diff at ${i}:`);
    console.log(`    Original: ...${na.slice(Math.max(0, i - 40), i + 60)}...`);
    console.log(`    Copied:   ...${nb.slice(Math.max(0, i - 40), i + 60)}...`);
    fail++;
  }
}

console.log(`\nResult: ${pass} match, ${fail} diff`);
process.exit(fail === 0 ? 0 : 1);
