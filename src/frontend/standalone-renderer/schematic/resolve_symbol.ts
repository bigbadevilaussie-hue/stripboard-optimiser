import { BUILTIN_DEFS } from "./builtin_defs";
import { getSymbolDef, createFootprintSymbol } from "@/data/symbolDefs";
import { DEFAULT_COMPONENTS } from "@/data/defaultComponents";

export function resolveDef(defId: string, projectDefs: any[]) {
  const fromProject = (projectDefs ?? []).find((d: any) => d.id === defId);
  if (fromProject) return fromProject;

  const fromDefault = (DEFAULT_COMPONENTS as any[])?.find((d: any) => d.id === defId);
  if (fromDefault && fromDefault.symbol) return fromDefault;

  const b = BUILTIN_DEFS[defId];
  if (b) {
    const pins = Array.isArray(b.pins)
      ? b.pins.map((p: any, i: number) =>
          typeof p === "string"
            ? { id: String(i + 1), name: p, offsetRow: i, offsetCol: 0 }
            : p,
        )
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

export function resolveSymbol(def: any) {
  if (!def || !def.symbol) return null;
  const fromLib = getSymbolDef(def.symbol);
  if (fromLib) return fromLib;
  if (def.symbol.startsWith("custom-footprint-") || def.symbol === "custom-footprint") {
    try {
      return createFootprintSymbol(def.pins || [], def.width || 2, def.height || 2);
    } catch { return null; }
  }
  return null;
}
