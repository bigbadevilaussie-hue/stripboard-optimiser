"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.resolveDef = resolveDef;
exports.resolveSymbol = resolveSymbol;
const builtin_defs_1 = require("./builtin_defs");
const symbolDefs_1 = require("../../data/symbolDefs.js");
const defaultComponents_1 = require("../../data/defaultComponents.js");
function resolveDef(defId, projectDefs) {
    const fromProject = (projectDefs ?? []).find((d) => d.id === defId);
    if (fromProject)
        return fromProject;
    const fromDefault = defaultComponents_1.DEFAULT_COMPONENTS?.find((d) => d.id === defId);
    if (fromDefault && fromDefault.symbol)
        return fromDefault;
    const b = builtin_defs_1.BUILTIN_DEFS[defId];
    if (b) {
        const pins = Array.isArray(b.pins)
            ? b.pins.map((p, i) => typeof p === "string"
                ? { id: String(i + 1), name: p, offsetRow: i, offsetCol: 0 }
                : p)
            : [];
        return {
            id: defId,
            name: b.name ?? defId,
            symbol: b.symbol,
            pins,
            width: b.width ?? 1,
            height: b.height ?? 1,
            hasValue: !!b.hasValue,
            labelPrefix: b.labelPrefix,
        };
    }
    return null;
}
function resolveSymbol(def) {
    if (!def || !def.symbol)
        return null;
    const fromLib = (0, symbolDefs_1.getSymbolDef)(def.symbol);
    if (fromLib)
        return fromLib;
    if (def.symbol.startsWith("custom-footprint-") || def.symbol === "custom-footprint") {
        try {
            return (0, symbolDefs_1.createFootprintSymbol)(def.pins || [], def.width || 2, def.height || 2);
        }
        catch {
            return null;
        }
    }
    return null;
}
