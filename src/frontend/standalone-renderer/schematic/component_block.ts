import { draw_symbol } from "./draw_symbol";
import { getSymbolBounds } from "./symbol_geometry";

function esc(s: string) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function draw_component(comp: any, def: any, symbol: any, pinColors: Record<string, string>) {
  const x = comp.schematicPos?.x ?? 0;
  const y = comp.schematicPos?.y ?? 0;
  const rotation = (comp.schematicRotation ?? 0) as 0 | 90 | 180 | 270;
  const mirrored = !!comp.schematicMirrored;

  const pinNames: Record<string, string> = {};
  if (Array.isArray(def?.pins)) {
    for (const p of def.pins) {
      if (p && typeof p === "object" && p.id != null) pinNames[p.id] = p.name ?? p.id;
    }
  }

  const body = draw_symbol({
    symbol, rotation, mirrored, pinColors, pinNames,
    pinLabelOffsets: comp.pinLabelOffsets ?? {},
  });

  const bounds = getSymbolBounds(symbol, rotation, mirrored);
  const off = comp.labelOffset ?? { x: 0, y: 0 };
  const labelX = (bounds.minX + bounds.maxX) / 2 + off.x;
  const labelY = bounds.minY - 6 - (symbol.labelYOffset ?? 0) + off.y;
  const hasCustomOffset = off.x !== 0 || off.y !== 0;

  const chunks: string[] = [`<g transform="translate(${x},${y})">`, body];

  if (hasCustomOffset && comp.label) {
    chunks.push(`<line x1="0" y1="0" x2="${labelX}" y2="${labelY}" stroke="#999" stroke-width="0.8" stroke-dasharray="2 2" />`);
  }

  if (comp.label) {
    const allowsValue = def?.hasValue ?? false;
    let tspans = `<tspan x="${labelX}">${esc(comp.label)}</tspan>`;
    if (allowsValue && comp.value) {
      tspans += `<tspan x="${labelX}" dy="1.2em" font-weight="400" fill-opacity="0.7">${esc(comp.value)}</tspan>`;
    }
    if (comp.offBoard && !comp.boardExcluded) {
      tspans += `<tspan x="${labelX}" dy="1.2em" font-size="9" font-weight="400" font-style="italic" fill-opacity="0.7">off board</tspan>`;
    }
    chunks.push(`<text x="${labelX}" y="${labelY}" text-anchor="middle" font-size="12" font-weight="600" font-family="system-ui,sans-serif" fill="#111" stroke="#fff" stroke-width="3" stroke-linejoin="round" paint-order="stroke">${tspans}</text>`);
  }
  chunks.push(`</g>`);
  return chunks.join("\n");
}
