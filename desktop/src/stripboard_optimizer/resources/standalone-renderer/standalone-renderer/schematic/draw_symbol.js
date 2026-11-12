"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.draw_symbol = draw_symbol;
const symbol_geometry_1 = require("./symbol_geometry");
function esc(s) {
    return String(s)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}
function draw_symbol(opts) {
    const { symbol, rotation = 0, mirrored = false, pinColors = {}, pinNames = {}, pinLabelOffsets = {}, showPinLabels = true, bodyStroke = "#111", bodyStrokeWidth = 1.5, } = opts;
    const chunks = [];
    const bodyT = [];
    if (rotation)
        bodyT.push(`rotate(${rotation})`);
    if (mirrored)
        bodyT.push(`scale(-1,1)`);
    const bodyTransform = bodyT.length ? ` transform="${bodyT.join(" ")}"` : "";
    chunks.push(`<g${bodyTransform} fill="none" stroke="${esc(bodyStroke)}" stroke-width="${bodyStrokeWidth}" stroke-linecap="round" stroke-linejoin="round">`);
    for (const bp of symbol.bodyPaths ?? []) {
        const d = typeof bp === "string" ? bp : bp.d;
        const rawFill = typeof bp === "string" ? undefined : bp.fill;
        const fill = rawFill === "currentColor" ? bodyStroke : (rawFill ?? "none");
        const stroke = typeof bp === "string" ? bodyStroke : (bp.stroke ?? bodyStroke);
        chunks.push(`<path d="${esc(d)}" fill="${esc(fill)}" stroke="${esc(stroke)}" />`);
    }
    for (const el of symbol.extraElements ?? []) {
        if (!el || typeof el === "string") {
            if (typeof el === "string")
                chunks.push(el);
            continue;
        }
        const p = el.props ?? {};
        if (el.type === "line") {
            chunks.push(`<line x1="${p.x1}" y1="${p.y1}" x2="${p.x2}" y2="${p.y2}" stroke="${esc(bodyStroke)}" stroke-width="1.2" stroke-linecap="round" />`);
        }
        else if (el.type === "circle") {
            const fill = p.fill === "currentColor" ? bodyStroke : (p.fill ?? "none");
            const sw = p.strokeWidth ?? 1.5;
            chunks.push(`<circle cx="${p.cx}" cy="${p.cy}" r="${p.r}" fill="${esc(String(fill))}" stroke="${esc(bodyStroke)}" stroke-width="${sw}" />`);
        }
        else if (el.type === "text") {
            const anchor = p.textAnchor ?? "middle";
            const child = p.children ?? "";
            chunks.push(`<text x="${p.x}" y="${p.y}" font-size="${p.fontSize ?? 10}" text-anchor="${esc(anchor)}" fill="${esc(bodyStroke)}">${esc(String(child))}</text>`);
        }
    }
    chunks.push(`</g>`);
    const labelOffset = symbol.pinLabelOffset ?? 8;
    for (const pin of symbol.pins ?? []) {
        const end = (0, symbol_geometry_1.transformPoint)(pin.stubEnd.x, pin.stubEnd.y, rotation, mirrored);
        const color = pinColors[pin.pinId];
        const hasNet = !!color;
        const fill = hasNet ? color : "#fff";
        const stroke = hasNet ? color : "#444";
        chunks.push(`<circle cx="${end.x}" cy="${end.y}" r="2.5" fill="${esc(fill)}" stroke="${esc(stroke)}" stroke-width="1.5" />`);
        if (showPinLabels && !symbol.hidePinLabels) {
            const name = pinNames[pin.pinId] ?? pin.defaultName;
            if (name) {
                const attach = pin.labelPos ?? pin.stubEnd;
                const lp = (0, symbol_geometry_1.getPinLabelProps)(attach, pin.side ?? "top", rotation, mirrored, labelOffset);
                const off = pinLabelOffsets[pin.pinId];
                const lx = lp.x + (off?.x ?? 0);
                const ly = lp.y + (off?.y ?? 0);
                chunks.push(`<text x="${lx}" y="${ly}" text-anchor="${lp.anchor}" dominant-baseline="${lp.baseline}" font-size="9" font-family="system-ui,sans-serif" fill="#333" stroke="#fff" stroke-width="3" stroke-linejoin="round" paint-order="stroke">${esc(name)}</text>`);
            }
        }
    }
    return chunks.join("\n");
}
