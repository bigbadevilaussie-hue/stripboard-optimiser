// Stage 3b: StaticPart colour-mode parity with real connectivity-derived pinStyle.

import * as fs from "fs";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { DEFAULT_COMPONENTS } from "@/data/defaultComponents";
import { resolveComponentDef } from "@/utils/resolveComponentDef";
import { StaticPart } from "@/components/stripboard/partDrawing";
import { HOLE_SPACING, holeCenter } from "@/components/stripboard/boardLayout";
import { boardView } from "@/components/stripboard/offBoard";
import { computeStripSegments } from "@/components/stripboard/stripSegments";
import { computeConnectivity } from "@/components/stripboard/connectivity";
import type { Component, ComponentDef, Net } from "@/types";
import { renderStaticPart, makePinStyle } from "./static_part";

const projectData = JSON.parse(fs.readFileSync("/Users/nick/Desktop/repo/motomix.json", "utf8"));
const componentDefs: ComponentDef[] = [...DEFAULT_COMPONENTS, ...(projectData.componentDefs ?? [])];
const components: Component[] = projectData.components ?? [];
const nets: Net[] = projectData.nets ?? [];
const board = projectData.board;

// Board view (off-board parts expanded) — needed for segments/connectivity
const view = boardView(components, componentDefs, projectData.netAssignments ?? []);
const segments = computeStripSegments(board, view.components, componentDefs, view.netAssignments);
const connectivity = computeConnectivity(segments, board.wires, board);

// One pinStyle for both React and standalone
const pinStyle = makePinStyle(segments, connectivity, nets);

function normalise(s: string): string {
  let out = s.replace(/\s+/g, " ").replace(/>\s+</g, "><").trim();
  out = out.replace(/<(line|circle|rect|path|polyline|polygon|ellipse)([^>]*?)\s*\/>/g, (_, tag, attrs) => `<${tag}${attrs}></${tag}>`);
  out = out.replace(/\s+>/g, ">");
  out = out.replace(/(="-?\d+\.\d{5,}")/g, (m) => {
    const v = parseFloat(m.slice(2, -1));
    return `="${v.toFixed(4).replace(/0+$/, "").replace(/\.$/, "")}"`;
  });
  return out;
}

function compareColour(label: string, c: Component, def: ComponentDef) {
  const outline = "#333";
  const outlineWidth = 0.14;
  const strokeWidth = 3;

  const reactEl = React.createElement(StaticPart, {
    def, component: c, at: (row: number, col: number) => holeCenter(row, col), pitch: HOLE_SPACING,
    pinStyle, pinNames: "auto", label: c.label,
    outline, outlineWidth, strokeWidth,
  });
  const reactSvg = renderToStaticMarkup(reactEl);

  const standaloneSvg = renderStaticPart(def, c, (row, col) => holeCenter(row, col), HOLE_SPACING, {
    pinStyle, pinNames: "auto", label: c.label,
    bodyOptions: { mono: false, outline, outlineWidth, fill: "none", strokeWidth, dashed: false },
  });

  const a = normalise(reactSvg);
  const b = normalise(standaloneSvg);

  if (a === b) {
    console.log(`${label}: MATCH (${a.length} chars)`);
  } else {
    console.log(`${label}: DIFF`);
    console.log(`  React:      ${a.length} chars`);
    console.log(`  Standalone: ${b.length} chars`);
    let i = 0;
    while (i < a.length && i < b.length && a[i] === b[i]) i++;
    console.log(`  First diff at ${i}:`);
    console.log(`    React:      ...${a.slice(Math.max(0, i - 40), i + 60)}...`);
    console.log(`    Standalone: ...${b.slice(Math.max(0, i - 40), i + 60)}...`);
  }
}

console.log("=== Stage 3b: StaticPart colour-mode parity (real pinStyle) ===\n");
console.log(`Segments: ${segments.length}, groups: ${connectivity.length}, nets: ${nets.length}\n`);

const placed = components.filter((c) => c.boardPos !== null);
console.log(`Placed components: ${placed.length}\n`);

for (const c of placed) {
  const def = resolveComponentDef(c, componentDefs);
  if (!def) { console.log(`UNRESOLVED: ${c.label} (${c.defId})`); continue; }
  console.log(`--- ${c.label} (${def.id}) ---`);
  compareColour("colour, top (real pin colours)", c, def);
  console.log("");
}
