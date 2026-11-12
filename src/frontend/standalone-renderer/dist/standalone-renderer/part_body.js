"use strict";
// Pure SVG-string port of PartBody from components/stripboard/partDrawing.tsx.
// No React, no JSX. Returns an SVG fragment string.
Object.defineProperty(exports, "__esModule", { value: true });
exports.renderPartBody = renderPartBody;
const packageBodies_1 = require("../components/stripboard/packageBodies.js");
function esc(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
function num(n) {
    return Number.isInteger(n) ? String(n) : n.toFixed(4).replace(/0+$/, "").replace(/\.$/, "");
}
function renderPartBody(drawing, opts) {
    const { mono, outline, outlineWidth, fill, strokeWidth, dashed } = opts;
    if (drawing.pieces) {
        const paper = (mark) => {
            if (!mono)
                return "";
            const f = mark ? "#000" : "#fff";
            const fo = mark ? 1 : 0.8;
            return ` fill="${f}" fill-opacity="${fo}" stroke="${esc(outline)}" stroke-width="${num(outlineWidth)}"`;
        };
        const parts = [];
        for (const piece of drawing.pieces) {
            if (piece.t === "line") {
                const stroke = mono ? outline : piece.stroke;
                parts.push(`<line x1="${num(piece.x1)}" y1="${num(piece.y1)}" x2="${num(piece.x2)}" y2="${num(piece.y2)}" stroke="${esc(stroke)}" stroke-width="${num(piece.sw)}" stroke-linecap="round" />`);
            }
            else if (piece.t === "arc") {
                const stroke = mono ? outline : piece.stroke;
                parts.push(`<path d="${esc(piece.d)}" fill="none" stroke="${esc(stroke)}" stroke-width="${num(piece.sw)}" />`);
            }
            else if (piece.t === "body") {
                const fillAttrs = mono ? "" : ` fill="${esc(piece.fill)}" fill-opacity="${packageBodies_1.BODY_OPACITY}"`;
                const strokeAttrs = mono ? "" : ` stroke="${esc(outline)}" stroke-width="${num(outlineWidth)}"`;
                parts.push(`<path d="${esc(piece.d)}"${fillAttrs}${strokeAttrs}${paper()} stroke-linejoin="round" />`);
            }
            else if (piece.t === "circle") {
                const fillAttrs = mono ? "" : ` fill="${esc(piece.fill)}" fill-opacity="${packageBodies_1.BODY_OPACITY}"`;
                const strokeAttrs = mono ? "" : (piece.outline ? ` stroke="${esc(outline)}" stroke-width="${num(outlineWidth)}"` : ` stroke="none" stroke-width="0"`);
                parts.push(`<circle cx="${num(piece.cx)}" cy="${num(piece.cy)}" r="${num(piece.rad)}"${fillAttrs}${strokeAttrs}${paper()} />`);
            }
            else if (piece.t === "rect") {
                if (mono && piece.band)
                    continue;
                const fillAttrs = mono ? "" : ` fill="${esc(piece.fill)}" fill-opacity="${packageBodies_1.BODY_OPACITY}"`;
                const strokeAttrs = mono ? "" : (piece.outline ? ` stroke="${esc(outline)}" stroke-width="${num(outlineWidth)}"` : ` stroke="none" stroke-width="0"`);
                parts.push(`<rect x="${num(piece.x)}" y="${num(piece.y)}" width="${num(piece.w)}" height="${num(piece.h)}" rx="${num(piece.r)}"${fillAttrs}${strokeAttrs}${paper(piece.mark)} />`);
            }
        }
        return `<g transform="${esc(drawing.transform)}">${parts.join("")}</g>`;
    }
    if (!drawing.outline)
        return "";
    const { box, path, marker } = drawing.outline;
    const s = drawing.scale;
    const sw = strokeWidth * s;
    const parts = [];
    if (box) {
        const dashAttr = dashed ? ` stroke-dasharray="${num(4 * s)} ${num(3 * s)}"` : "";
        const transformAttr = box.transform ? ` transform="${esc(box.transform)}"` : "";
        parts.push(`<rect x="${num(box.x)}" y="${num(box.y)}" width="${num(box.width)}" height="${num(box.height)}" rx="${num(3 * s)}"${transformAttr} fill="${esc(fill)}" stroke="${esc(outline)}" stroke-width="${num(sw)}"${dashAttr} />`);
    }
    if (path) {
        parts.push(`<path d="${esc(path)}" fill="${esc(fill)}" stroke="${esc(outline)}" stroke-width="${num(sw)}" />`);
    }
    if (marker) {
        const markerSw = marker.filled ? sw : Math.max(s, sw * 0.67);
        const markerFill = marker.filled ? fill : "none";
        parts.push(`<path d="${esc(marker.d)}" fill="${esc(markerFill)}" stroke="${esc(outline)}" stroke-width="${num(markerSw)}" pointer-events="none" />`);
    }
    return `<g>${parts.join("")}</g>`;
}
