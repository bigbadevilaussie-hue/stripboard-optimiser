import { Board, BoardPosition, Component, ComponentDef, Cut, Net, NetAssignment } from "@/types";
import { resolveComponentDef } from "@/utils/resolveComponentDef";
import { AutoLayoutResult } from "./layoutTypes";
import { getFlexiblePinPositions } from "./boardLayout";
import { computeStripSegments, findSegmentIndex } from "./stripSegments";
import { computeConnectivity } from "./connectivity";
import { checkNetCompleteness } from "./netCompleteness";
import { collectBoardPins, collectOccupiedHoles } from "./boardPins";
import { holeKey } from "./keys";
import { flexWireObstacle, rigidBody } from "./partGeometry";
import { segmentIntersectsRect, wireCrossesBody, wireStackDepth, WireObstacles } from "./flexGeometry";

// Generic fixed-placement wire-column and drill-hole polish, after v5 finish.
// No part or USB motion, no extra rows/cols, no new or deleted nets.
// Enabled only by an explicit option while the validation run is in progress.
type Wire = AutoLayoutResult["wires"][number];
type Quality = {
  conflicts: number; incomplete: number; nonvertical: number;
  crossings: number; stacked: number; knife: number; wireLength: number;
};
export interface WirePolishStats {
  tried: number;
  accepted: number;
  columnsMoved: number;
  drillsRecovered: number;
  before: Quality;
  after: Quality;
}
export interface WirePolishOutcome { result: AutoLayoutResult; stats: WirePolishStats }

const wireLength = (w: Wire) => Math.hypot(w.from.row - w.to.row, w.from.col - w.to.col);
const inBoard = (p: BoardPosition, b: Board) =>
  p.row >= 0 && p.col >= 0 && p.row < b.rows && p.col < b.cols;

function placedComponents(components: Component[], result: AutoLayoutResult): Component[] {
  const placements = new Map(result.placements.map((p) => [p.componentId, p]));
  return components.map((c) => {
    const p = placements.get(c.id);
    return p ? { ...c, boardPos: p.boardPos,
      rotation: p.rotation ?? c.rotation,
      flexibleEndPos: p.flexibleEndPos ?? c.flexibleEndPos } : c;
  });
}
function obstaclesFor(comps: Component[], defs: ComponentDef[]): WireObstacles {
  const out: WireObstacles = { rects: [], bodies: [] };
  for (const c of comps) {
    if (!c.boardPos || c.boardExcluded) continue;
    const def = resolveComponentDef(c, defs);
    if (!def) continue;
    if (def.flexible) {
      const [p1, p2] = getFlexiblePinPositions(c, def);
      if (p1 && p2) out.bodies.push(flexWireObstacle(def, p1, p2));
    } else out.rects.push(rigidBody(def, c.boardPos, c.rotation));
  }
  return out;
}
function wireCrossings(w: Wire, obstacles: WireObstacles): number {
  let n = 0;
  for (const body of obstacles.rects)
    if (segmentIntersectsRect(w.from, w.to, body)) n++;
  for (const body of obstacles.bodies)
    if (wireCrossesBody(w.from, w.to, body)) n++;
  return n;
}
function evaluate(
  board: Board, comps: Component[], defs: ComponentDef[],
  nets: Net[], assignments: NetAssignment[],
  obs: WireObstacles, wires: Wire[], cuts: Cut[]
): Quality | null {
  if (wires.some((w) => !inBoard(w.from, board) || !inBoard(w.to, board))) return null;
  if (cuts.some((c) => !inBoard(c, board))) return null;
  const drilled = new Set(cuts.filter((c) => c.kind === "hole").map((c) => holeKey(c.row, c.col)));
  if (wires.some((w) => drilled.has(holeKey(w.from.row, w.from.col)) ||
    drilled.has(holeKey(w.to.row, w.to.col)))) return null;
  const routedBoard: Board = { ...board, cuts, wires: wires.map((w, i) => ({ ...w, id: "polish-" + i })) };
  const segs = computeStripSegments(routedBoard, comps, defs, assignments);
  const connectivity = computeConnectivity(segs, routedBoard.wires, routedBoard);
  const conflicts = connectivity.filter((g) => g.hasConflict).length;
  const incomplete = checkNetCompleteness(nets, assignments, segs, connectivity, comps, defs, routedBoard).length;
  let nonvertical = 0, crossings = 0, stacked = 0, len = 0;
  for (let i = 0; i < wires.length; i++) {
    const w = wires[i];
    if (w.from.col !== w.to.col) nonvertical++;
    crossings += wireCrossings(w, obs);
    if (wireStackDepth(w.from, w.to, wires.slice(0, i)) > 0) stacked++;
    len += wireLength(w);
  }
  return {
    conflicts, incomplete, nonvertical, crossings, stacked,
    knife: cuts.filter((c) => c.kind !== "hole").length,
    wireLength: Math.round(len * 1000) / 1000,
  };
}
function noRegression(a: Quality, b: Quality): boolean {
  return a.conflicts <= b.conflicts && a.incomplete <= b.incomplete &&
    a.nonvertical <= b.nonvertical && a.crossings <= b.crossings &&
    a.stacked <= b.stacked && a.knife <= b.knife;
}
function score(q: Quality): number {
  // Strict physical violations dominate extra wire length.
  return q.conflicts * 1e10 + q.incomplete * 1e9 + q.nonvertical * 1e7 +
    q.crossings * 1e6 + q.knife * 1e5 + q.stacked * 1e4 + q.wireLength;
}
function drillFreeCuts(
  board: Board, comps: Component[], defs: ComponentDef[],
  nets: Net[], assignments: NetAssignment[], obs: WireObstacles,
  wires: Wire[], cuts: Cut[], quality: Quality,
): { cuts: Cut[]; quality: Quality } {
  let activeCuts = cuts;
  let activeQuality = quality;
  const pins = collectBoardPins(board, comps, defs, assignments);
  const pinHoles = new Set(pins.map((p) => holeKey(p.row, p.col)));
  const endpoints = new Set(wires.flatMap((w) =>
    [holeKey(w.from.row, w.from.col), holeKey(w.to.row, w.to.col)]));
  for (let i = 0; i < activeCuts.length; i++) {
    if (activeCuts[i].kind === "hole") continue;
    const cut = activeCuts[i];
    for (const col of [cut.col, cut.col + 1]) {
      const pos = { row: cut.row, col };
      const key = holeKey(pos.row, pos.col);
      if (!inBoard(pos, board) || pinHoles.has(key) || endpoints.has(key)) continue;
      if (activeCuts.some((c, j) => j !== i && c.kind === "hole" && holeKey(c.row, c.col) === key)) continue;
      const next = activeCuts.map((c, j) => j === i ? { ...c, col, kind: "hole" as const } : c);
      const q = evaluate(board, comps, defs, nets, assignments, obs, wires, next);
      if (q && noRegression(q, activeQuality) && q.knife < activeQuality.knife) {
        activeCuts = next;
        activeQuality = q;
        break;
      }
    }
  }
  return { cuts: activeCuts, quality: activeQuality };
}

export function polishFixedBoardWires(
  originalBoard: Board, components: Component[], defs: ComponentDef[],
  nets: Net[], assignments: NetAssignment[], result: AutoLayoutResult,
  maxEvaluations = 6000,
  drilledCutsOnly = true,
): WirePolishOutcome {
  const emptyStats = (q: Quality): WirePolishStats => ({
    tried: 0, accepted: 0, columnsMoved: 0, drillsRecovered: 0,
    before: q, after: q,
  });
  const board: Board = { ...originalBoard,
    rows: result.boardSize?.rows ?? originalBoard.rows,
    cols: result.boardSize?.cols ?? originalBoard.cols, cuts: [], wires: [] };
  const comps = placedComponents(components, result);
  const obs = obstaclesFor(comps, defs);
  let wires = result.wires.map((w) => ({ from: { ...w.from }, to: { ...w.to } }));
  let cuts = result.cuts.map((c) => ({ ...c }));
  let quality = evaluate(board, comps, defs, nets, assignments, obs, wires, cuts);
  if (!quality || board.pattern || !wires.length || maxEvaluations <= 0) {
    const zero: Quality = { conflicts: 0, incomplete: 0, nonvertical: 0,
      crossings: 0, stacked: 0, knife: 0, wireLength: 0 };
    return { result, stats: emptyStats(quality ?? zero) };
  }
  const before = quality;
  let tried = 0, accepted = 0, columnsMoved = 0;
  // First take any safe drill upgrades that do not require moving a wire.
  if (drilledCutsOnly)
    ({ cuts, quality } = drillFreeCuts(board, comps, defs, nets, assignments, obs, wires, cuts, quality));
  for (let pass = 0; pass < 6 && tried < maxEvaluations; pass++) {
    const routed: Board = { ...board, cuts, wires: [] };
    const segs = computeStripSegments(routed, comps, defs, assignments);
    const pins = collectBoardPins(routed, comps, defs, assignments);
    const occupied = collectOccupiedHoles(routed, comps, defs, pins);
    const wireEnds = new Set(wires.flatMap((w) =>
      [holeKey(w.from.row, w.from.col), holeKey(w.to.row, w.to.col)]));
    let best: { wires: Wire[]; cuts: Cut[]; quality: Quality; index: number } | null = null;
    // Prioritise the wires causing physical violations and endpoints blocking
    // knife holes; the candidate is still validated against every net.
    const blockedCutHoles = new Set(cuts.filter((c) => c.kind !== "hole")
      .flatMap((c) => [holeKey(c.row, c.col), holeKey(c.row, c.col + 1)]));
    const order = wires.map((w, index) => {
      const bad = (w.from.col !== w.to.col ? 8 : 0) +
        wireCrossings(w, obs) * 4 +
        (wireStackDepth(w.from, w.to, wires.filter((_, i) => i !== index)) > 0 ? 8 : 0) +
        (blockedCutHoles.has(holeKey(w.from.row, w.from.col)) ||
         blockedCutHoles.has(holeKey(w.to.row, w.to.col)) ? 12 : 0);
      return { index, bad };
    }).sort((a, b) => b.bad - a.bad || a.index - b.index);
    for (const { index } of order) {
      if (tried >= maxEvaluations) break;
      const w = wires[index];
      if (w.from.row === w.to.row) continue;
      const si = findSegmentIndex(segs, w.from.row, w.from.col);
      const sj = findSegmentIndex(segs, w.to.row, w.to.col);
      if (si < 0 || sj < 0) continue;
      const lo = Math.max(segs[si].startCol, segs[sj].startCol);
      const hi = Math.min(segs[si].endCol, segs[sj].endCol);
      const cols = [];
      for (let col = lo; col <= hi; col++) if (col !== w.from.col || col !== w.to.col) cols.push(col);
      cols.sort((a, b) => Math.abs(a - w.from.col) + Math.abs(a - w.to.col) -
        (Math.abs(b - w.from.col) + Math.abs(b - w.to.col)));
      for (const col of cols) {
        if (tried >= maxEvaluations) break;
        const from = { row: w.from.row, col }, to = { row: w.to.row, col };
        const keyA = holeKey(from.row, col), keyB = holeKey(to.row, col);
        if (occupied.has(keyA) || occupied.has(keyB) ||
            (wireEnds.has(keyA) && keyA !== holeKey(w.from.row, w.from.col) && keyA !== holeKey(w.to.row, w.to.col)) ||
            (wireEnds.has(keyB) && keyB !== holeKey(w.from.row, w.from.col) && keyB !== holeKey(w.to.row, w.to.col))) continue;
        const nextWires = wires.map((x, i) => i === index ? { from, to } : x);
        tried++;
        let q = evaluate(board, comps, defs, nets, assignments, obs, nextWires, cuts);
        if (!q || !noRegression(q, quality)) continue;
        // Only re-run full cut-upgrade verification if this move actually
        // frees a flank of an existing knife. Cuts that could already be
        // drilled were handled once before the column search began.
        const freesKnife = drilledCutsOnly && cuts.some((cut) => cut.kind !== "hole" &&
          [cut.col, cut.col + 1].some((c) => {
            const k = holeKey(cut.row, c);
            return (k === holeKey(w.from.row, w.from.col) ||
              k === holeKey(w.to.row, w.to.col)) &&
              k !== keyA && k !== keyB;
          }));
        const upgraded = freesKnife
          ? drillFreeCuts(board, comps, defs, nets, assignments, obs, nextWires, cuts, q)
          : { cuts, quality: q };
        q = upgraded.quality;
        if (score(q) >= score(quality) - 1e-6) continue;
        if (!best || score(q) < score(best.quality) - 1e-6)
          best = { wires: nextWires, cuts: upgraded.cuts, quality: q, index };
      }
    }
    if (!best) break;
    wires = best.wires;
    cuts = best.cuts;
    quality = best.quality;
    accepted++;
    columnsMoved++;
  }
  const drillsRecovered = before.knife - quality.knife;
  if (!accepted && !drillsRecovered) return { result,
    stats: { tried, accepted, columnsMoved, drillsRecovered, before, after: before } };
  // Final independent recheck: all original electrical and physical defect
  // counts must be maintained or improved. A failed recheck returns untouched.
  const independentlyVerified = evaluate(board, comps, defs, nets, assignments, obs, wires, cuts);
  if (!independentlyVerified || !noRegression(independentlyVerified, before))
    return { result, stats: { tried, accepted: 0, columnsMoved: 0, drillsRecovered: 0, before, after: before } };
  // Update only finish messages we can prove have changed, without hiding any
  // placement, starvation, reachability or other solver issue.
  const staleWireIssue = /wire(s)? (could not be made straight and crossing-free|still run on top of another wire)/;
  const issues = result.issues.filter((x) => !staleWireIssue.test(x));
  const mess = independentlyVerified.nonvertical + independentlyVerified.crossings;
  if (mess) issues.push(`${mess} wire violations remain after fixed-board polish`);
  if (independentlyVerified.stacked) issues.push(`${independentlyVerified.stacked} wires still run on top of another wire`);
  return { result: { ...result, wires, cuts, issues },
    stats: { tried, accepted, columnsMoved, drillsRecovered, before, after: independentlyVerified } };
}
