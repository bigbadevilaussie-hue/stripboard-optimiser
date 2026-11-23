// Generic, read-only audit of knife cuts in a routed horizontal-strip board.
// No project names or footprint heuristics. The physical drill-upgrade
// planner has further constraints: this is an explanatory necessary-condition
// diagnostic, NOT an authority to rewrite a cut or declare it drillable.
const { boardLayout, resolveComponentDef } = require("./helpers.js");

function auditKnifeCuts(board, components, defs, assignments, nets) {
  const netByPin = new Map(assignments.map((a) => [a.componentId + ":" + a.pinId, a.netId]));
  const nameByNet = new Map(nets.map((n) => [n.id, n.name || n.id]));
  const pins = components.flatMap((comp) => {
    if (!comp.boardPos || comp.boardExcluded) return [];
    const def = resolveComponentDef(comp, defs);
    if (!def) return [];
    return boardLayout.getComponentPinPositions(comp, def).map((p) => {
      const netId = netByPin.get(comp.id + ":" + p.pinId);
      return { row: p.row, col: p.col, component: comp.label || comp.id,
        pinId: p.pinId, netId: netId || null,
        net: netId ? nameByNet.get(netId) || netId : "FLOATING",
        netKey: netId || "nc:" + comp.id + ":" + p.pinId };
    });
  });
  const wires = board.wires || [];
  const cutHoles = new Set((board.cuts || []).filter((c) => c.kind === "hole")
    .map((c) => c.row + ":" + c.col));
  const rowPins = (row) => pins.filter((p) => p.row === row);
  const publicPin = (p) => ({ component: p.component, pin: p.pinId,
    row: p.row, col: p.col, net: p.net });
  return (board.cuts || []).flatMap((cut, index) => {
    if (cut.kind === "hole") return [];
    const sameRow = rowPins(cut.row);
    const left = sameRow.filter((p) => p.col === cut.col);
    const right = sameRow.filter((p) => p.col === cut.col + 1);
    const forcedByAdjacentPins = left.some((a) => right.some((b) => a.netKey !== b.netKey));
    const nearLeft = sameRow.filter((p) => p.col <= cut.col)
      .sort((a, b) => b.col - a.col);
    const nearRight = sameRow.filter((p) => p.col >= cut.col + 1)
      .sort((a, b) => a.col - b.col);
    const flanks = [cut.col, cut.col + 1].map((col) => {
      const at = sameRow.filter((p) => p.col === col);
      const endpoints = wires.flatMap((w, i) =>
        [w.from, w.to].some((p) => p.row === cut.row && p.col === col) ? [i + 1] : []);
      return { row: cut.row, col, pins: at.map(publicPin), wireEndpoints: endpoints,
        alreadyDrilled: cutHoles.has(cut.row + ":" + col),
        // A pin- or endpoint-free flank is a *candidate*, not a guaranteed
        // safe drill. The exact upgrade planner checks copper availability.
        basicDrillCandidate: at.length === 0 && endpoints.length === 0 &&
          !cutHoles.has(cut.row + ":" + col) };
    });
    return [{
      cutIndex: index + 1, row: cut.row, col: cut.col,
      between: [{ row: cut.row, col: cut.col }, { row: cut.row, col: cut.col + 1 }],
      forcedByAdjacentPins,
      nearestLeft: nearLeft.length ? publicPin(nearLeft[0]) : null,
      nearestRight: nearRight.length ? publicPin(nearRight[0]) : null,
      leftPins: left.map(publicPin), rightPins: right.map(publicPin),
      flanks,
    }];
  });
}
module.exports = { auditKnifeCuts };
