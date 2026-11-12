// Test harness: compare standalone renderPartBody() against the original
// React PartBody output via renderToStaticMarkup. NOT part of the production
// renderer — this file is a test reference only.

import * as fs from "fs";
import * as path from "path";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { DEFAULT_COMPONENTS } from "@/data/defaultComponents";
import { resolveComponentDef } from "@/utils/resolveComponentDef";
import { partDrawing, PartBody } from "@/components/stripboard/partDrawing";
import { HOLE_SPACING, holeCenter } from "@/components/stripboard/boardLayout";
import type { Component, ComponentDef } from "@/types";
import { renderPartBody } from "./part_body";

const projectPath = "/Users/nick/Desktop/repo/motomix.json";
const projectData = JSON.parse(fs.readFileSync(projectPath, "utf8"));
const componentDefs: ComponentDef[] = [...DEFAULT_COMPONENTS, ...(projectData.componentDefs ?? [])];
const components: Component[] = projectData.components ?? [];

function pickComponent(predicate: (c: Component, def: ComponentDef) => boolean): { c: Component; def: ComponentDef } | null {
  for (const c of components) {
    if (!c.boardPos) continue;
    const def = resolveComponentDef(c, componentDefs);
    if (def && predicate(c, def)) return { c, def };
  }
  return null;
}

function compare(label: string, c: Component, def: ComponentDef, mirror: boolean, color: boolean) {
  const drawing = partDrawing(def, c, (row, col) => holeCenter(row, col), HOLE_SPACING);
  if (!drawing) {
    console.log(`${label}: no drawing (skipped)`);
    return;
  }

  // Reference: React PartBody via renderToStaticMarkup
  const reactEl = React.createElement(PartBody, {
    drawing,
    mono: !color || mirror,
    outline: drawing.pieces && color && !mirror ? "#333" : "#000",
    outlineWidth: 0.14,
    fill: "none",
    strokeWidth: mirror ? 1.5 : 3,
    dashed: false,
  });
  const reactSvg = renderToStaticMarkup(reactEl);

  // Standalone: renderPartBody
  const standaloneSvg = renderPartBody(drawing, {
    mono: !color || mirror,
    outline: drawing.pieces && color && !mirror ? "#333" : "#000",
    outlineWidth: 0.14,
    fill: "none",
    strokeWidth: mirror ? 1.5 : 3,
    dashed: false,
  });

  // Normalise: React adds attribute ordering and quoting differences; compare sorted attribute sets
  const normalise = (s: string): string => {
    let out = s
      .replace(/\s+/g, " ")
      .replace(/>\s+</g, "><")
      .trim();
    // Self-closing -> explicit close
    out = out.replace(/<(line|circle|rect|path|polyline|polygon|ellipse)([^>]*?)\s*\/>/g, (_, tag, attrs) => `<${tag}${attrs}></${tag}>`);
    out = out.replace(/\s+>/g, ">");
    // Round numeric attribute values to 4 decimals
    out = out.replace(/(="-?\d+\.\d{5,}")/g, (m) => {
      const v = parseFloat(m.slice(2, -1));
      return `="${v.toFixed(4).replace(/0+$/, "").replace(/\.$/, "")}"`;
    });
    return out;
  };
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
    const safeLabel = label.replace(/[^a-zA-Z0-9]/g, "_");
    const safeC = c.label.replace(/[^a-zA-Z0-9]/g, "_");
    require("fs").writeFileSync(`/tmp/cmp_${safeC}_${safeLabel}_react.svg`, reactSvg);
    require("fs").writeFileSync(`/tmp/cmp_${safeC}_${safeLabel}_standalone.svg`, standaloneSvg);
  }
}

console.log("=== Stage 2 comparison: PartBody vs renderPartBody ===\n");

const placed = components.filter((c) => c.boardPos !== null);
console.log(`Placed components: ${placed.length}\n`);

for (const c of placed) {
  const def = resolveComponentDef(c, componentDefs);
  if (!def) {
    console.log(`UNRESOLVED: ${c.label} (${c.defId})`);
    continue;
  }
  console.log(`--- ${c.label} (${def.id}) ---`);
  compare("colour, top", c, def, false, true);
  compare("mono, top", c, def, false, false);
  compare("mono, mirror", c, def, true, true);
  console.log("");
}
