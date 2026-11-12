// Stage 4b: full-board parity between React PrintBoard (client render via
// jsdom) and the standalone renderStripboard().

import * as fs from "fs";
import * as React from "react";
import { JSDOM } from "jsdom";
import { useProjectStore } from "@/store/useProjectStore";
import PrintBoard from "@/components/print/PrintBoard";
import { renderStripboard } from "./render";

// Set up jsdom globals BEFORE importing react-dom/client
const dom = new JSDOM("<!DOCTYPE html><html><body><div id=\"root\"></div></body></html>", {
  pretendToBeVisual: true,
});
Object.defineProperty(global, "window", { value: dom.window, configurable: true, writable: true });
Object.defineProperty(global, "document", { value: dom.window.document, configurable: true, writable: true });
Object.defineProperty(global, "navigator", { value: dom.window.navigator, configurable: true });
Object.defineProperty(global, "HTMLElement", { value: dom.window.HTMLElement, configurable: true, writable: true });
Object.defineProperty(global, "SVGElement", { value: dom.window.SVGElement, configurable: true, writable: true });
(global as any).requestAnimationFrame = (cb: FrameRequestCallback) => setTimeout(cb, 0);
(global as any).cancelAnimationFrame = (id: number) => clearTimeout(id);
(global as any).IS_REACT_ACT_ENVIRONMENT = true;

const { createRoot } = require("react-dom/client");
const { act } = require("react");

const projectData = JSON.parse(fs.readFileSync("/Users/nick/Desktop/repo/moto14wires30cuts.json", "utf8"));

import { DEFAULT_COMPONENTS } from "@/data/defaultComponents";
const mergedDefs = [...DEFAULT_COMPONENTS, ...(projectData.componentDefs ?? [])];
useProjectStore.setState({
  board: projectData.board,
  components: projectData.components,
  componentDefs: mergedDefs,
  nets: projectData.nets ?? [],
  netAssignments: projectData.netAssignments ?? [],
});

function normalise(s: string): string {
  let out = s.replace(/\s+/g, " ").replace(/>\s+</g, "><").trim();
  out = out.replace(/<(line|circle|rect|path|polyline|polygon|ellipse)([^>]*?)\s*\/>/g, (_, tag, attrs) => `<${tag}${attrs}></${tag}>`);
  out = out.replace(/\s+>/g, ">");
  out = out.replace(/(="-?\d+\.\d{5,}")/g, (m) => {
    const v = parseFloat(m.slice(2, -1));
    return `="${v.toFixed(4).replace(/0+$/, "").replace(/\.$/, "")}"`;
  });
  // React does not emit xmlns on inline SVG; standalone does. Ignore it.
  out = out.replace(/\s*xmlns="[^"]*"/g, "");
  // Ignore Tailwind class attribute
  out = out.replace(/\s*class="[^"]*"/g, "");
  // Normalise rgb(r, g, b) to hex
  out = out.replace(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/g, (_, r, g, b) => {
    const h = (n: string) => parseInt(n, 10).toString(16).padStart(2, "0");
    return `#${h(r)}${h(g)}${h(b)}`;
  });
  // Normalise style="background: #fff" vs "#ffffff"
  out = out.replace(/background:\s*#([0-9a-f]{3})\b/g, (m, hex) => `background: #${hex[0]}${hex[0]}${hex[1]}${hex[1]}${hex[2]}${hex[2]}`);
  // Strip trailing semicolons inside style attributes
  out = out.replace(/style="([^"]*)"/g, (m, body) => `style="${body.replace(/;+\s*$/, "")}"`);
  return out;
}

async function renderClient(element: React.ReactElement): Promise<string> {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  await act(async () => {
    root.render(element);
  });
  const html = container.innerHTML;
  await act(async () => {
    root.unmount();
  });
  container.remove();
  return html;
}

function compare(label: string, reactSvg: string, standaloneSvg: string) {
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
    console.log(`    React:      ...${a.slice(Math.max(0, i - 60), i + 80)}...`);
    console.log(`    Standalone: ...${b.slice(Math.max(0, i - 60), i + 80)}...`);
    fs.writeFileSync("/tmp/board_react.svg", reactSvg);
    fs.writeFileSync("/tmp/board_standalone.svg", standaloneSvg);
  }
}

async function main() {
  console.log("=== Stage 4b: full-board parity (React client render vs standalone) ===\n");
  console.log(`Board: ${projectData.board.rows}x${projectData.board.cols}`);
  console.log(`Components: ${projectData.components.length}`);
  console.log(`Wires: ${projectData.board.wires.length}`);
  console.log(`Cuts: ${projectData.board.cuts.length}\n`);

  const options = { color: true, showLabels: true, showPinLabels: true };
  const standalone = renderStripboard(projectData, options);

  const reactPlace = await renderClient(
    React.createElement(PrintBoard, { variant: "place", showLabels: true, showPinLabels: true, color: true })
  );
  compare("place (top)", reactPlace, standalone.top);

  const reactCut = await renderClient(
    React.createElement(PrintBoard, { variant: "cut", showLabels: true, showPinLabels: true, color: true })
  );
  compare("cut (copper)", reactCut, standalone.copper);
}

main().catch((e) => { console.error(e); process.exit(1); });
