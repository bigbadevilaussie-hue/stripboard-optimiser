"use strict";
// Impossible strict drill-only case: adjacent locked pins on one copper strip
// assigned different nets (including private floating terminals).
function lockedAdjacentDrillConflicts(components, defs, assignments, getPins, resolveDef) {
  const byTerminal = new Map(assignments.map(a => [a.componentId + ":" + a.pinId, a.netId]));
  const violations = [];
  for (const component of components) {
    if (!component.locked || !component.boardPos || component.boardExcluded || component.offBoard) continue;
    const def = resolveDef(component, defs);
    if (!def || def.flexible) continue;
    const pins = getPins(component, def);
    for (let i = 0; i < pins.length; i++) for (let j = i + 1; j < pins.length; j++) {
      const a = pins[i], b = pins[j];
      if (a.row !== b.row || Math.abs(a.col - b.col) !== 1) continue;
      const left = a.col < b.col ? a : b;
      const right = a.col < b.col ? b : a;
      const na = byTerminal.get(component.id + ":" + left.pinId);
      const nb = byTerminal.get(component.id + ":" + right.pinId);
      if (na && na === nb) continue;
      violations.push({
        component: component.label || component.id,
        row: left.row, leftCol: left.col, rightCol: right.col,
        pins: [left.pinId, right.pinId], nets: [na || "FLOATING", nb || "FLOATING"],
        reason: "ADJACENT_DIFFERENT_NET_PADS_REQUIRE_KNIFE_CUT"
      });
    }
  }
  return violations;
}
module.exports = { lockedAdjacentDrillConflicts };
