// Standalone stripboard renderer: takes a project JSON and returns two SVG
// strings (place = component side, cut = copper side).
// No React, no Zustand, no Next.js. Pure functions only.

import type { Board, Component, ComponentDef, Net, NetAssignment, Wire, Cut } from "@/types";
import { DEFAULT_COMPONENTS } from "@/data/defaultComponents";
import { boardView } from "@/components/stripboard/offBoard";
import { computeStripSegments, findSegmentIndex, type StripSegment } from "@/components/stripboard/stripSegments";
import { computeConnectivity, getGroupForSegment, getGroupForWire, type ConnectedGroup } from "@/components/stripboard/connectivity";
import { computeWireLaneOffsets } from "@/components/stripboard/wireLanes";
import { HOLE_SPACING, holeCenter } from "@/components/stripboard/boardLayout";
import { hasHole, joinsDown, joinsRight } from "@/components/stripboard/boardPattern";
import { resolveComponentDef } from "@/utils/resolveComponentDef";
import { makePinStyle } from "./static_part";
import { renderPartBody } from "./part_body";
import { partDrawing } from "./part_drawing";

const MM_PER_HOLE = 2.54;
const SCALE = MM_PER_HOLE / HOLE_SPACING;
const MARGIN = 40;
const COPPER = "#d9b368";
const CONFLICT = "#dc2626";

export interface RenderOptions {
  color?: boolean;
  showLabels?: boolean;
  showPinLabels?: boolean;
}

export interface RenderResult {
  top: string;
  copper: string;
}

function esc(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function num(n: number): string {
  return Number.isInteger(n) ? String(n) : n.toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
}

function renderBoard(projectData: any, variant: "place" | "cut", color: boolean, showLabels: boolean, showPinLabels: boolean): string {
  const board: Board = projectData.board;
  const components: Component[] = projectData.components ?? [];
  const nets: Net[] = projectData.nets ?? [];
  const netAssignments: NetAssignment[] = projectData.netAssignments ?? [];
  const componentDefs: ComponentDef[] = [...DEFAULT_COMPONENTS, ...(projectData.componentDefs ?? [])];

  const view = boardView(components, componentDefs, netAssignments);
  const boardComponents = view.components;
  const boardAssignments = view.netAssignments;

  const segments = computeStripSegments(board, boardComponents, componentDefs, boardAssignments);
  const connectivity = computeConnectivity(segments, board.wires, board);

  const groupColor = (group: ConnectedGroup | undefined): string | null => {
    if (!group || group.netIds.length === 0) return null;
    if (group.hasConflict) return CONFLICT;
    return nets.find((n) => n.id === group.netIds[0])?.color ?? null;
  };
  const holeColor = (row: number, col: number): string | null => {
    const si = findSegmentIndex(segments, row, col);
    return si < 0 ? null : groupColor(getGroupForSegment(connectivity, si));
  };

  const mirror = variant === "cut";
  const lastCol = board.cols - 1;
  const colX = (col: number) => holeCenter(0, mirror ? lastCol - col : col).x;
  const rowY = (row: number) => holeCenter(row, 0).y;

  const minX = holeCenter(0, 0).x;
  const maxX = holeCenter(0, lastCol).x;
  const minY = holeCenter(0, 0).y;
  const maxY = holeCenter(board.rows - 1, 0).y;
  const vbX = minX - MARGIN;
  const vbY = minY - MARGIN;
  const vbW = maxX - minX + MARGIN * 2;
  const vbH = maxY - minY + MARGIN * 2;

  const compStroke = mirror ? "#bbbbbb" : "#000000";

  // Holes
  const holes: string[] = [];
  for (let r = 0; r < board.rows; r++) {
    for (let c = 0; c < board.cols; c++) {
      if (!hasHole(board, r, c)) continue;
      const fill = color ? "#fff" : "none";
      const stroke = color ? "#8a6d2f" : "#000";
      const sw = color ? 0.8 : 1.2;
      holes.push(`<circle cx="${num(colX(c))}" cy="${num(rowY(r))}" r="4" fill="${fill}" stroke="${stroke}" stroke-width="${num(sw)}" />`);
    }
  }

  // Copper strips
  const copper: { from: [number, number]; to: [number, number] }[] = [];
  if (!board.pattern) {
    for (let r = 0; r < board.rows; r++) copper.push({ from: [r, 0], to: [r, lastCol] });
  } else {
    for (let r = 0; r < board.rows; r++) {
      for (let c = 0; c < board.cols; c++) {
        if (joinsRight(board, r, c) && !joinsRight(board, r, c - 1)) {
          let end = c + 1;
          while (joinsRight(board, r, end)) end++;
          copper.push({ from: [r, c], to: [r, end] });
        }
        if (joinsDown(board, r, c) && !joinsDown(board, r - 1, c)) {
          let end = r + 1;
          while (joinsDown(board, end, c)) end++;
          copper.push({ from: [r, c], to: [end, c] });
        }
      }
    }
  }
  const strips = copper.map(({ from, to }) => {
    const stroke = color ? COPPER : "#dddddd";
    const sw = color ? 12 : 2;
    const cap = color ? ` stroke-linecap="round"` : "";
    return `<line x1="${num(colX(from[1]))}" y1="${num(rowY(from[0]))}" x2="${num(colX(to[1]))}" y2="${num(rowY(to[0]))}" stroke="${stroke}" stroke-width="${num(sw)}"${cap} />`;
  });

  // Net-coloured strips (colour mode, non-mirror only)
  const netStrips: string[] = [];
  if (color && !mirror) {
    for (let i = 0; i < segments.length; i++) {
      const seg = segments[i];
      const c = groupColor(getGroupForSegment(connectivity, i));
      if (!c) continue;
      const end = seg.endRow !== undefined ? { row: seg.endRow, col: seg.startCol } : { row: seg.row, col: seg.endCol };
      netStrips.push(`<line x1="${num(colX(seg.startCol))}" y1="${num(rowY(seg.row))}" x2="${num(colX(end.col))}" y2="${num(rowY(end.row))}" stroke="${c}" stroke-width="5" stroke-linecap="round" />`);
    }
  }

  // Components — match PrintBoard.tsx's exact <g> nesting
  const pinStyle = makePinStyle(segments, connectivity, nets);
  const compParts: string[] = [];
  for (const comp of boardComponents) {
    const def = resolveComponentDef(comp, componentDefs);
    if (!def || !comp.boardPos) continue;

    const drawing = partDrawing(def, comp, (row, col) => holeCenter(row, col), HOLE_SPACING);
    if (!drawing) continue;

    const bodyOpts = {
      mono: !color || mirror,
      outline: drawing.pieces && color && !mirror ? "#333" : "#000",
      outlineWidth: 0.14,
      fill: "none",
      strokeWidth: mirror ? 1.5 : 3,
      dashed: false,
    };

    const bodySvg = renderPartBody(drawing, bodyOpts);

    const labelOff = comp.boardLabelOffset ?? { x: 0, y: 0 };
    const labelX = mirror ? minX + maxX - drawing.label.x - labelOff.x : drawing.label.x + labelOff.x;
    const labelY = drawing.label.y + labelOff.y;

    const mirrorAttrs = mirror
      ? ` transform="translate(${num(minX + maxX)} 0) scale(-1 1)" opacity="0.45"`
      : "";
    const bodyWrap = `<g${mirrorAttrs}>${bodySvg}</g>`;

    const pinsSvg: string[] = [];
    for (const p of drawing.pins) {
      const c = holeCenter(p.row, p.col);
      const style = pinStyle(p);
      const fill = mirror ? "none" : (color && style.color) || "#000";
      const stroke = color && !mirror ? "#fff" : compStroke;
      pinsSvg.push(`<circle cx="${num(colX(p.col))}" cy="${num(rowY(p.row))}" r="5" fill="${fill}" stroke="${stroke}" stroke-width="1.5" />`);
    }

    const pinNamesSvg: string[] = [];
    if (!mirror && showPinLabels && drawing.pinNames) {
      for (const p of drawing.pins) {
        const pinName = def.pins.find((pd) => pd.id === p.pinId)?.name;
        if (!pinName) continue;
        pinNamesSvg.push(`<text x="${num(colX(p.col))}" y="${num(rowY(p.row) + 7)}" text-anchor="middle" dominant-baseline="hanging" font-size="11" font-weight="600" fill="#000" stroke="#fff" stroke-width="3.5" paint-order="stroke" stroke-linejoin="round" style="user-select: none">${esc(pinName)}</text>`);
      }
    }

    const labelSvg = showLabels
      ? `<text x="${num(labelX)}" y="${num(labelY)}" text-anchor="middle"${drawing.label.onBody ? ' dominant-baseline="central"' : ""} font-size="16" font-weight="700" fill="${mirror ? "#666" : "#000"}" stroke="#fff" stroke-width="4" paint-order="stroke" stroke-linejoin="round">${esc(comp.label)}</text>`
      : "";

    compParts.push(`<g>${bodyWrap}${pinsSvg.join("")}${pinNamesSvg.join("")}${labelSvg}</g>`);
  }

  // Wires (non-mirror only)
  const wireParts: string[] = [];
  if (!mirror) {
    const laneOffsets = computeWireLaneOffsets(board.wires, 5);
    for (const w of board.wires) {
      const off = laneOffsets.get(w.id);
      const dx = off?.dx ?? 0;
      const dy = off?.dy ?? 0;
      const a = { x: colX(w.from.col) + dx, y: rowY(w.from.row) + dy };
      const b = { x: colX(w.to.col) + dx, y: rowY(w.to.row) + dy };
      const ink = (color && groupColor(getGroupForWire(connectivity, w.id))) || "#000";
      const casing = (off || color) ? `<line x1="${num(a.x)}" y1="${num(a.y)}" x2="${num(b.x)}" y2="${num(b.y)}" stroke="${color ? "#222" : "#fff"}" stroke-width="${color ? 5.5 : 7}" stroke-linecap="round" />` : "";
      wireParts.push(
        `<g>${casing}<line x1="${num(a.x)}" y1="${num(a.y)}" x2="${num(b.x)}" y2="${num(b.y)}" stroke="${ink}" stroke-width="4" stroke-linecap="round" /><circle cx="${num(a.x)}" cy="${num(a.y)}" r="5" fill="${ink}" /><circle cx="${num(b.x)}" cy="${num(b.y)}" r="5" fill="${ink}" /></g>`
      );
    }
  }

  // Cuts (mirror only)
  const cutParts: string[] = [];
  if (mirror) {
    for (const cut of board.cuts) {
      const cx = cut.kind === "hole" || cut.kind === "below" ? colX(cut.col) : (colX(cut.col) + colX(cut.col + 1)) / 2;
      const cy = cut.kind === "below" ? (rowY(cut.row) + rowY(cut.row + 1)) / 2 : rowY(cut.row);
      const s = 9;
      const stroke = color ? CONFLICT : "#000";
      cutParts.push(
        `<g stroke="${stroke}" stroke-width="5" stroke-linecap="round"><line x1="${num(cx - s)}" y1="${num(cy - s)}" x2="${num(cx + s)}" y2="${num(cy + s)}" /><line x1="${num(cx - s)}" y1="${num(cy + s)}" x2="${num(cx + s)}" y2="${num(cy - s)}" /></g>`
      );
    }
  }

  // Origin marker
  const ox = colX(0);
  const oy = rowY(0);
  const origin = `<g><path d="M ${num(ox - 16)} ${num(oy - 16)} l 14 0 l -14 14 z" fill="#000" /><text x="${num(ox)}" y="${num(oy - 22)}" text-anchor="middle" font-size="13" fill="#000">${mirror ? "Copper side · R0·C0" : "Top · R0·C0"}</text></g>`;

  const widthMm = (vbW * SCALE).toFixed(2);
  const heightMm = (vbH * SCALE).toFixed(2);

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${widthMm}mm" height="${heightMm}mm" viewBox="${num(vbX)} ${num(vbY)} ${num(vbW)} ${num(vbH)}" style="background: #fff">${strips.join("")}${netStrips.join("")}${holes.join("")}${compParts.join("")}${wireParts.join("")}${cutParts.join("")}${origin}</svg>`;
}

export function renderStripboard(projectData: any, options: RenderOptions = {}): RenderResult {
  const color = options.color ?? true;
  const showLabels = options.showLabels ?? true;
  const showPinLabels = options.showPinLabels ?? true;

  return {
    top: renderBoard(projectData, "place", color, showLabels, showPinLabels),
    copper: renderBoard(projectData, "cut", color, showLabels, showPinLabels),
  };
}
