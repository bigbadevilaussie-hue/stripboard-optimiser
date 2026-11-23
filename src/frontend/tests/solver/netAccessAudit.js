// Read-only, circuit-independent electrical net/corridor diagnostics.
// For an incomplete net, report each connected pin group, available copper
// attachment columns, and geometry-clean *candidate* vertical joins.
// These are necessary opportunities, NOT proof of a valid finishing route.
// Existing cut/wire placement is never modified.
const path = require("node:path");
const OUT = path.join(__dirname, "out");
const { computeStripSegments, computeConnectivity, boardLayout, resolveComponentDef,
  flexGeometry, partGeometry } = require("./helpers.js");
const { collectBoardPins, collectOccupiedHoles } =
  require(path.join(OUT, "components/stripboard/boardPins.js"));
const { findSegmentIndex } =
  require(path.join(OUT, "components/stripboard/stripSegments.js"));
const { holeKey } = require(path.join(OUT, "components/stripboard/keys.js"));

function auditNetAccess(board, components, defs, assignments, nets, netQuery) {
  if (board.pattern) return []; // these row/column tests assume horizontal strips
  const segments = computeStripSegments(board, components, defs, assignments);
  const wires = board.wires || [];
  const connected = computeConnectivity(segments, wires, board);
  const groupAtSegment = new Map();
  connected.forEach((g, gi) => g.segmentIndices.forEach((si) => groupAtSegment.set(si, gi)));
  const pins = collectBoardPins(board, components, defs, assignments);
  const occupied = collectOccupiedHoles(board, components, defs, pins);
  const takenWireEnds = new Set(wires.flatMap((w) =>
    [holeKey(w.from.row, w.from.col), holeKey(w.to.row, w.to.col)]));
  const nameOf = new Map(nets.map((n) => [n.id, n.name || n.id]));
  const componentOf = new Map(components.map((c) => [c.id, c]));
  const resolved = new Map(components.map((c) => [c.id, resolveComponentDef(c, defs)]));
  const obstacles = components.filter((c) => c.boardPos && !c.boardExcluded).flatMap((c) => {
    const def = resolved.get(c.id);
    if (!def) return [];
    if (def.flexible) {
      const [p1, p2] = boardLayout.getFlexiblePinPositions(c, def);
      if (!p1 || !p2) return [];
      const body = partGeometry.flexWireObstacle(def, p1, p2);
      return [(from, to) => flexGeometry.wireCrossesBody(from, to, body)];
    }
    const rect = partGeometry.rigidBody(def, c.boardPos, c.rotation ?? 0);
    return [(from, to) => flexGeometry.segmentIntersectsRect(from, to, rect)];
  });
  const cleanVertical = (from, to) =>
    from.col === to.col && from.row !== to.row &&
    !obstacles.some((hit) => hit(from, to)) &&
    flexGeometry.wireStackDepth(from, to, wires) === 0;
  const outputs = [];
  for (const net of nets) {
    if (netQuery && net.id !== netQuery && net.name !== netQuery) continue;
    const mine = assignments.filter((a) => a.netId === net.id &&
      !componentOf.get(a.componentId)?.boardExcluded);
    if (mine.length < 2) continue;
    const groupPins = new Map(), unplacedPins = [];
    for (const a of mine) {
      const c = componentOf.get(a.componentId), def = resolved.get(a.componentId);
      if (!c || !def) continue;
      const pin = def.pins.find((p) => p.id === a.pinId);
      const info = { component: c.label || c.id, pin: pin?.name || a.pinId,
        pinId: a.pinId, componentId: c.id, row: null, col: null };
      if (!c.boardPos) {
        unplacedPins.push(info);
        continue;
      }
      const p = boardLayout.getComponentPinPositions(c, def)
        .find((x) => x.pinId === a.pinId);
      if (!p) {
        unplacedPins.push(info);
        continue;
      }
      info.row = p.row;
      info.col = p.col;
      const si = findSegmentIndex(segments, p.row, p.col);
      const gi = groupAtSegment.get(si);
      if (gi === undefined) {
        unplacedPins.push(info);
        continue;
      }
      if (!groupPins.has(gi)) groupPins.set(gi, []);
      groupPins.get(gi).push(info);
    }
    if (groupPins.size < 2 && !unplacedPins.length && !netQuery) continue;
    const groups = [...groupPins].map(([gi, pinInfos], idx) => {
      // Already-connected copper sections can offer more free holes than
      // just the strip under a target pin. This includes existing net wires.
      const holes = [];
      for (const si of connected[gi].segmentIndices) {
        const seg = segments[si];
        for (let col = seg.startCol; col <= seg.endCol; col++) {
          const row = seg.row, k = holeKey(row, col);
          if (row < 0 || row >= board.rows || col < 0 || col >= board.cols) continue;
          if (!occupied.has(k) && !takenWireEnds.has(k))
            holes.push({ row, col });
        }
      }
      const columns = [...new Set(holes.map((h) => h.col))].sort((a, b) => a - b);
      return {
        group: idx + 1, connectedGroup: gi, pins: pinInfos,
        freeHoleCount: holes.length, freeColumns: columns,
        copperConflict: connected[gi].hasConflict,
        _holes: holes,
      };
    });
    let commonFreeColumns = [];
    if (groups.length) {
      commonFreeColumns = groups[0].freeColumns.filter((col) =>
        groups.slice(1).every((g) => g.freeColumns.includes(col)));
    }
    const pairwise = [];
    for (let i = 0; i < groups.length; i++) for (let j = i + 1; j < groups.length; j++) {
      const a = groups[i], b = groups[j];
      const common = a.freeColumns.filter((col) => b.freeColumns.includes(col));
      const direct = [], sample = [];
      for (const col of common) {
        const aa = a._holes.filter((h) => h.col === col);
        const bb = b._holes.filter((h) => h.col === col);
        let shortest = null;
        for (const from of aa) for (const to of bb) {
          if (!cleanVertical(from, to)) continue;
          const len = Math.abs(from.row - to.row);
          if (!shortest || len < shortest.length)
            shortest = { from, to, length: len };
        }
        if (shortest) {
          direct.push(col);
          if (sample.length < 3) sample.push({ col, ...shortest });
        }
      }
      pairwise.push({
        groups: [i + 1, j + 1],
        sharedFreeColumns: common,
        geometryCleanColumns: direct,
        examples: sample,
      });
    }
    outputs.push({
      netId: net.id, netName: nameOf.get(net.id),
      connectedGroups: groups.map(({ _holes, ...g }) => g),
      unplacedPins, commonFreeColumns, pairwise,
      // A candidate passes only a local geometrical check; adding it could
      // still break unrelated nets, cut constraints or no-stack invariants.
      assessment: "READ_ONLY_CANDIDATES_NOT_VERIFIED_ROUTES",
    });
  }
  return outputs;
}
module.exports = { auditNetAccess };
