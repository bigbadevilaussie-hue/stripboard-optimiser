// Pure geometry port of partDrawing() from components/stripboard/partDrawing.tsx.
// No React, no JSX. Copy of the exact logic, verified against the original.

import type { Component, ComponentDef } from "@/types";
import { HOLE_SPACING, type PinPosition, getComponentBounds, getComponentPinPositions, getFlexibleBounds } from "@/components/stripboard/boardLayout";
import { bodyStyle, bellyPath, dipNotch, usbPort, diagonalBody } from "@/components/stripboard/componentGlyphs";
import { MM_PER_HOLE, type Piece, bodyAnchor, bodyPieces, drawnReversed, isDarkFill, resolvePackage } from "@/components/stripboard/packageBodies";
import { rigidPieces } from "@/components/stripboard/rigidBodies";

type Point = { x: number; y: number };

export interface PartDrawing {
  pins: PinPosition[];
  bounds: { minRow: number; minCol: number; maxRow: number; maxCol: number };
  scale: number;
  pieces: Piece[] | null;
  transform: string;
  outline: {
    box: { x: number; y: number; width: number; height: number; transform?: string } | null;
    path: string | null;
    marker: { d: string; filled: boolean } | null;
  } | null;
  label: { x: number; y: number; onBody: boolean; onDark: boolean };
  pinNames: boolean;
  pinOnDark: boolean;
}

export function partDrawing(
  def: ComponentDef,
  component: Component,
  at: (row: number, col: number) => Point,
  pitch: number,
): PartDrawing | null {
  if (!component.boardPos) return null;
  const pins = getComponentPinPositions(component, def);
  const bounds = def.flexible
    ? getFlexibleBounds(component, def)
    : getComponentBounds(def, component.boardPos, component.rotation);
  const scale = pitch / HOLE_SPACING;
  const unit = pitch / MM_PER_HOLE;
  const pad = pitch * 0.4;
  const midRow = (bounds.minRow + bounds.maxRow) / 2;
  const midCol = (bounds.minCol + bounds.maxCol) / 2;
  const centre = at(midRow, midCol);

  const resolved = resolvePackage(def, component.value, component.package);
  const base = { pins, bounds, scale, pieces: null, transform: "", outline: null, pinNames: true, pinOnDark: false };

  if (resolved?.kind === "twoPin" && pins.length === 2) {
    const pkg = resolved.spec;
    const flip = drawnReversed(pkg, pins[0], pins[1]);
    const p1 = at(pins[flip ? 1 : 0].row, pins[flip ? 1 : 0].col);
    const p2 = at(pins[flip ? 0 : 1].row, pins[flip ? 0 : 1].col);
    const dx = p2.x - p1.x;
    const dy = p2.y - p1.y;
    const len = Math.sqrt(dx * dx + dy * dy);
    const spanMm = len / unit;
    const angle = Math.round((Math.atan2(dy, dx) * 180 * 1e4) / Math.PI) / 1e4;
    const cx = (p1.x + p2.x) / 2;
    const cy = (p1.y + p2.y) / 2;
    const alongBody = bodyAnchor(pkg, spanMm) * unit;
    return {
      ...base,
      pieces: bodyPieces(pkg, spanMm),
      transform: `translate(${cx} ${cy}) rotate(${angle}) scale(${unit})`,
      label: {
        x: cx + (len === 0 ? 0 : dx / len) * alongBody,
        y: cy + (len === 0 ? 0 : dy / len) * alongBody,
        onBody: true,
        onDark: isDarkFill(pkg.fill),
      },
      pinNames: !def.pins.every((p) => /^\d+$/.test(p.name)),
    };
  }

  if (resolved?.kind === "rigid") {
    const crowded = pins.some((p) => Math.hypot(p.col - midCol, p.row - midRow) < 0.6);
    return {
      ...base,
      pieces: rigidPieces(resolved.spec, {
        pins: pins.map((p) => ({ x: (p.col - midCol) * MM_PER_HOLE, y: (p.row - midRow) * MM_PER_HOLE, id: p.pinId })),
        width: (bounds.maxCol - bounds.minCol + 1) * MM_PER_HOLE,
        height: (bounds.maxRow - bounds.minRow + 1) * MM_PER_HOLE,
        rotation: component.rotation,
      }),
      transform: `translate(${centre.x} ${centre.y}) scale(${unit})`,
      label: {
        x: centre.x,
        y: crowded ? at(bounds.minRow - 0.5, midCol).y : centre.y,
        onBody: true,
        onDark: !crowded && isDarkFill(resolved.spec.fill),
      },
      pinOnDark: !!resolved.spec.coversPins && isDarkFill(resolved.spec.fill),
    };
  }

  const pt = (p: PinPosition) => ({ ...at(p.row, p.col), id: p.pinId });
  const diag = def.flexible && pins.length === 2 ? diagonalBody(pt(pins[0]), pt(pins[1]), pad) : null;
  if (diag) {
    const a = pt(pins[0]), b = pt(pins[1]);
    return {
      ...base,
      outline: { box: diag, path: null, marker: null },
      label: { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 - pad - 4 * scale, onBody: false, onDark: false },
    };
  }

  const c1 = at(bounds.minRow, bounds.minCol), c2 = at(bounds.maxRow, bounds.maxCol);
  const x0 = Math.min(c1.x, c2.x) - pad, x1 = Math.max(c1.x, c2.x) + pad;
  const y0 = Math.min(c1.y, c2.y) - pad, y1 = Math.max(c1.y, c2.y) + pad;
  const box = { x: x0, y: y0, width: x1 - x0, height: y1 - y0 };
  const style = bodyStyle(def);
  let outline: PartDrawing["outline"] = { box, path: null, marker: null };
  if (style === "belly" && pins.length === 3) {
    outline = { box: null, path: bellyPath(pt(pins[0]), pt(pins[2]), pad), marker: null };
  } else if (style === "dip" && pins.length >= 4) {
    outline = { box, path: null, marker: { d: dipNotch(pins.map(pt), centre, pad), filled: false } };
  } else if (style === "board" && pins.length >= 4) {
    outline = { box, path: null, marker: { d: usbPort(pins.map(pt), centre, { x0, y0, x1, y1 }, unit), filled: true } };
  }
  return {
    ...base,
    outline,
    label: { x: (x0 + x1) / 2, y: y0 - 4 * scale, onBody: false, onDark: false },
  };
}
