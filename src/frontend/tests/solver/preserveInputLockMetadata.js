"use strict";

// The native optimiser clears movable components' solver-only `locked`
// field while searching. Reapply the original JSON's exact property presence
// and value when writing the saved result. This does not touch placements,
// definitions, netlists, wiring or the independent strict auditor.
function preserveInputLockMetadata(inputComponents, routedComponents) {
  const originalById = new Map(inputComponents.map(c => [c.id, c]));
  return routedComponents.map(component => {
    const original = originalById.get(component.id);
    if (!original) return component; // A missing/extra part fails independent audit.
    const saved = { ...component };
    if (Object.prototype.hasOwnProperty.call(original, "locked")) {
      saved.locked = original.locked;
    } else {
      delete saved.locked;
    }
    return saved;
  });
}

module.exports = { preserveInputLockMetadata };
