"use strict";
// Pure SVG-string port of StaticPart from components/stripboard/partDrawing.tsx.
// No React, no JSX. The caller provides the pinStyle callback.
Object.defineProperty(exports, "__esModule", { value: true });
exports.renderStaticPart = renderStaticPart;
exports.makePinStyle = makePinStyle;
const part_drawing_1 = require("./part_drawing");
const part_body_1 = require("./part_body");
function esc(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
function num(n) {
    return Number.isInteger(n) ? String(n) : n.toFixed(4).replace(/0+$/, "").replace(/\.$/, "");
}
function renderStaticPart(def, component, at, pitch, opts) {
    const drawing = (0, part_drawing_1.partDrawing)(def, component, at, pitch);
    if (!drawing)
        return "";
    const s = drawing.scale;
    const named = opts.pinNames === "all" || (opts.pinNames === "auto" && drawing.pinNames);
    const parts = [];
    // The body
    parts.push((0, part_body_1.renderPartBody)(drawing, opts.bodyOptions));
    // Pin circles
    for (const pin of drawing.pins) {
        const c = at(pin.row, pin.col);
        const { color, opacity } = opts.pinStyle(pin);
        const r = color ? 5 * s : 4.5 * s;
        const fill = color ?? "var(--hole-fill)";
        const stroke = color ? "var(--hole-fill)" : "var(--hole-stroke)";
        const sw = color ? 1.5 * s : 0.5 * s;
        const opacityAttr = opacity !== undefined ? ` opacity="${num(opacity)}"` : "";
        parts.push(`<g><circle cx="${num(c.x)}" cy="${num(c.y)}" r="${num(r)}" fill="${esc(fill)}" stroke="${esc(stroke)}" stroke-width="${num(sw)}"${opacityAttr} />`);
        if (named) {
            const pinName = def.pins.find((p) => p.id === pin.pinId)?.name ?? pin.pinId;
            const textFill = drawing.pinOnDark ? "#e8e8e8" : "var(--component-subtext)";
            const textStroke = drawing.pinOnDark ? "rgba(0,0,0,0.6)" : "var(--board-fill)";
            parts.push(`<text x="${num(c.x)}" y="${num(c.y + 10 * s)}" text-anchor="middle" font-size="${num(6 * s)}" fill="${esc(textFill)}" stroke="${esc(textStroke)}" stroke-width="${num(1.6 * s)}" paint-order="stroke" stroke-linejoin="round">${esc(pinName)}</text>`);
        }
        parts.push(`</g>`);
    }
    // Label
    if (opts.label !== undefined) {
        if (drawing.label.onBody) {
            const textFill = drawing.label.onDark ? "#f7f7f7" : "#1a1a1a";
            const textStroke = drawing.label.onDark ? "rgba(0,0,0,0.6)" : "rgba(255,255,255,0.8)";
            parts.push(`<text x="${num(drawing.label.x)}" y="${num(drawing.label.y)}" text-anchor="middle" dominant-baseline="central" font-size="${num(11 * s)}" font-weight="600" fill="${esc(textFill)}" stroke="${esc(textStroke)}" stroke-width="${num(3 * s)}" paint-order="stroke" stroke-linejoin="round">${esc(opts.label)}</text>`);
        }
        else {
            parts.push(`<text x="${num(drawing.label.x)}" y="${num(drawing.label.y)}" text-anchor="middle" font-size="${num(11 * s)}" font-weight="600" fill="var(--component-text)">${esc(opts.label)}</text>`);
        }
    }
    return `<g>${parts.join("")}</g>`;
}
const stripSegments_1 = require("../components/stripboard/stripSegments.js");
const connectivity_1 = require("../components/stripboard/connectivity.js");
const CONFLICT = "#dc2626";
/** Derive a pinStyle callback from strip segments, connectivity, and nets.
 *  Matches PrintBoard.tsx's holeColor logic. */
function makePinStyle(segments, connectivity, nets) {
    return (pin) => {
        const si = (0, stripSegments_1.findSegmentIndex)(segments, pin.row, pin.col);
        if (si < 0)
            return { color: null };
        const group = (0, connectivity_1.getGroupForSegment)(connectivity, si);
        if (!group || group.netIds.length === 0)
            return { color: null };
        if (group.hasConflict)
            return { color: CONFLICT };
        const net = nets.find((n) => n.id === group.netIds[0]);
        return { color: net?.color ?? null };
    };
}
