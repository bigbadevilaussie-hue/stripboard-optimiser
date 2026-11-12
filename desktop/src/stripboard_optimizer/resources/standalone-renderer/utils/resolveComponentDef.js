"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.resolveComponentDef = resolveComponentDef;
// One resolved def per component object, so callers that key on the def (or
// memoise on it) see a stable identity for as long as the component and its
// base definition are unchanged.
const resolved = new WeakMap();
/**
 * Resolve the effective ComponentDef for a component instance: the base def,
 * with the component's footprint override merged in if it has one, and with
 * the value and package that decide how big its real body is.
 * A component with none of these gets the base def as-is.
 */
function resolveComponentDef(component, componentDefs) {
    const baseDef = componentDefs.find((d) => d.id === component.defId);
    if (!baseDef)
        return undefined;
    const override = component.footprintOverride;
    if (!override && !component.value && !component.package)
        return baseDef;
    const hit = resolved.get(component);
    if (hit && hit.base === baseDef)
        return hit.def;
    const def = {
        ...baseDef,
        ...(override
            ? { width: override.width, height: override.height, pins: override.pins, bodyCells: override.bodyCells }
            : {}),
        part: { value: component.value, package: component.package },
    };
    resolved.set(component, { base: baseDef, def });
    return def;
}
