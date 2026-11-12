// Pure SVG-string port of StaticPart from components/stripboard/partDrawing.tsx.
// No React, no JSX. The caller provides the pinStyle callback.

import type { ComponentDef, Component } from "@/types";
import { partDrawing } from "./part_drawing";
import type { PinPosition } from "@/components/stripboard/boardLayout";
import { renderPartBody, type PartBodyOptions } from "./part_body";

export interface PinStyle {
  color: string | null;
  opacity?: number;
}

export interface StaticPartOptions {
  pinStyle: (pin: PinPosition) => PinStyle;
  pinNames: "auto" | "all" | "none";
  label?: string;
  bodyOptions: PartBodyOptions;
}

function esc(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function num(n: number): string {
  return Number.isInteger(n) ? String(n) : n.toFixed(4).replace(/0+$/, "").replace(/\.$/, "");
}

export function renderStaticPart(
  def: ComponentDef,
  component: Component,
  at: (row: number, col: number) => { x: number; y: number },
  pitch: number,
  opts: StaticPartOptions,
): string {
  const drawing = partDrawing(def, component, at, pitch);
  if (!drawing) return "";

  const s = drawing.scale;
  const named = opts.pinNames === "all" || (opts.pinNames === "auto" && drawing.pinNames);
  const parts: string[] = [];

  // The body
  parts.push(renderPartBody(drawing, opts.bodyOptions));

  // Pin circles
  for (const pin of drawing.pins) {
    const c = at(pin.row, pin.col);
    const { color, opacity } = opts.pinStyle(pin);
    const r = color ? 5 * s : 4.5 * s;
    const fill = color ?? "var(--hole-fill)";
    const stroke = color ? "var(--hole-fill)" : "var(--hole-stroke)";
    const sw = color ? 1.5 * s : 0.5 * s;
    const opacityAttr = opacity !== undefined ? ` opacity="${num(opacity)}"` : "";
    parts.push(
      `<g><circle cx="${num(c.x)}" cy="${num(c.y)}" r="${num(r)}" fill="${esc(fill)}" stroke="${esc(stroke)}" stroke-width="${num(sw)}"${opacityAttr} />`
    );

    if (named) {
      const pinName = def.pins.find((p) => p.id === pin.pinId)?.name ?? pin.pinId;
      const textFill = drawing.pinOnDark ? "#e8e8e8" : "var(--component-subtext)";
      const textStroke = drawing.pinOnDark ? "rgba(0,0,0,0.6)" : "var(--board-fill)";
      parts.push(
        `<text x="${num(c.x)}" y="${num(c.y + 10 * s)}" text-anchor="middle" font-size="${num(6 * s)}" fill="${esc(textFill)}" stroke="${esc(textStroke)}" stroke-width="${num(1.6 * s)}" paint-order="stroke" stroke-linejoin="round">${esc(pinName)}</text>`
      );
    }
    parts.push(`</g>`);
  }

  // Label
  if (opts.label !== undefined) {
    if (drawing.label.onBody) {
      const textFill = drawing.label.onDark ? "#f7f7f7" : "#1a1a1a";
      const textStroke = drawing.label.onDark ? "rgba(0,0,0,0.6)" : "rgba(255,255,255,0.8)";
      parts.push(
        `<text x="${num(drawing.label.x)}" y="${num(drawing.label.y)}" text-anchor="middle" dominant-baseline="central" font-size="${num(11 * s)}" font-weight="600" fill="${esc(textFill)}" stroke="${esc(textStroke)}" stroke-width="${num(3 * s)}" paint-order="stroke" stroke-linejoin="round">${esc(opts.label)}</text>`
      );
    } else {
      parts.push(
        `<text x="${num(drawing.label.x)}" y="${num(drawing.label.y)}" text-anchor="middle" font-size="${num(11 * s)}" font-weight="600" fill="var(--component-text)">${esc(opts.label)}</text>`
      );
    }
  }

  return `<g>${parts.join("")}</g>`;
}

import { findSegmentIndex, type StripSegment } from "@/components/stripboard/stripSegments";
import { getGroupForSegment, type ConnectedGroup } from "@/components/stripboard/connectivity";
import type { Net } from "@/types";

const CONFLICT = "#dc2626";

/** Derive a pinStyle callback from strip segments, connectivity, and nets.
 *  Matches PrintBoard.tsx's holeColor logic. */
export function makePinStyle(
  segments: StripSegment[],
  connectivity: ConnectedGroup[],
  nets: Net[],
): (pin: { row: number; col: number }) => PinStyle {
  return (pin) => {
    const si = findSegmentIndex(segments, pin.row, pin.col);
    if (si < 0) return { color: null };
    const group = getGroupForSegment(connectivity, si);
    if (!group || group.netIds.length === 0) return { color: null };
    if (group.hasConflict) return { color: CONFLICT };
    const net = nets.find((n) => n.id === group.netIds[0]);
    return { color: net?.color ?? null };
  };
}
