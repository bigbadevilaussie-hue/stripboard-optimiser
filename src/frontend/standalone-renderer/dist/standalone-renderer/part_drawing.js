"use strict";
// Pure geometry port of partDrawing() from components/stripboard/partDrawing.tsx.
// No React, no JSX. Copy of the exact logic, verified against the original.
Object.defineProperty(exports, "__esModule", { value: true });
exports.partDrawing = partDrawing;
const boardLayout_1 = require("../components/stripboard/boardLayout.js");
const componentGlyphs_1 = require("../components/stripboard/componentGlyphs.js");
const packageBodies_1 = require("../components/stripboard/packageBodies.js");
const rigidBodies_1 = require("../components/stripboard/rigidBodies.js");
function partDrawing(def, component, at, pitch) {
    if (!component.boardPos)
        return null;
    const pins = (0, boardLayout_1.getComponentPinPositions)(component, def);
    const bounds = def.flexible
        ? (0, boardLayout_1.getFlexibleBounds)(component, def)
        : (0, boardLayout_1.getComponentBounds)(def, component.boardPos, component.rotation);
    const scale = pitch / boardLayout_1.HOLE_SPACING;
    const unit = pitch / packageBodies_1.MM_PER_HOLE;
    const pad = pitch * 0.4;
    const midRow = (bounds.minRow + bounds.maxRow) / 2;
    const midCol = (bounds.minCol + bounds.maxCol) / 2;
    const centre = at(midRow, midCol);
    const resolved = (0, packageBodies_1.resolvePackage)(def, component.value, component.package);
    const base = { pins, bounds, scale, pieces: null, transform: "", outline: null, pinNames: true, pinOnDark: false };
    if (resolved?.kind === "twoPin" && pins.length === 2) {
        const pkg = resolved.spec;
        const flip = (0, packageBodies_1.drawnReversed)(pkg, pins[0], pins[1]);
        const p1 = at(pins[flip ? 1 : 0].row, pins[flip ? 1 : 0].col);
        const p2 = at(pins[flip ? 0 : 1].row, pins[flip ? 0 : 1].col);
        const dx = p2.x - p1.x;
        const dy = p2.y - p1.y;
        const len = Math.sqrt(dx * dx + dy * dy);
        const spanMm = len / unit;
        const angle = Math.round((Math.atan2(dy, dx) * 180 * 1e4) / Math.PI) / 1e4;
        const cx = (p1.x + p2.x) / 2;
        const cy = (p1.y + p2.y) / 2;
        const alongBody = (0, packageBodies_1.bodyAnchor)(pkg, spanMm) * unit;
        return {
            ...base,
            pieces: (0, packageBodies_1.bodyPieces)(pkg, spanMm),
            transform: `translate(${cx} ${cy}) rotate(${angle}) scale(${unit})`,
            label: {
                x: cx + (len === 0 ? 0 : dx / len) * alongBody,
                y: cy + (len === 0 ? 0 : dy / len) * alongBody,
                onBody: true,
                onDark: (0, packageBodies_1.isDarkFill)(pkg.fill),
            },
            pinNames: !def.pins.every((p) => /^\d+$/.test(p.name)),
        };
    }
    if (resolved?.kind === "rigid") {
        const crowded = pins.some((p) => Math.hypot(p.col - midCol, p.row - midRow) < 0.6);
        return {
            ...base,
            pieces: (0, rigidBodies_1.rigidPieces)(resolved.spec, {
                pins: pins.map((p) => ({ x: (p.col - midCol) * packageBodies_1.MM_PER_HOLE, y: (p.row - midRow) * packageBodies_1.MM_PER_HOLE, id: p.pinId })),
                width: (bounds.maxCol - bounds.minCol + 1) * packageBodies_1.MM_PER_HOLE,
                height: (bounds.maxRow - bounds.minRow + 1) * packageBodies_1.MM_PER_HOLE,
                rotation: component.rotation,
            }),
            transform: `translate(${centre.x} ${centre.y}) scale(${unit})`,
            label: {
                x: centre.x,
                y: crowded ? at(bounds.minRow - 0.5, midCol).y : centre.y,
                onBody: true,
                onDark: !crowded && (0, packageBodies_1.isDarkFill)(resolved.spec.fill),
            },
            pinOnDark: !!resolved.spec.coversPins && (0, packageBodies_1.isDarkFill)(resolved.spec.fill),
        };
    }
    const pt = (p) => ({ ...at(p.row, p.col), id: p.pinId });
    const diag = def.flexible && pins.length === 2 ? (0, componentGlyphs_1.diagonalBody)(pt(pins[0]), pt(pins[1]), pad) : null;
    if (diag) {
        const a = pt(pins[0]), b = pt(pins[1]);
        return {
            ...base,
            outline: { box: diag, path: null, marker: null },
            label: { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 - pad - 4 * scale, onBody: false, onDark: false },
        };
    }
    const c1 = at(bounds.minRow, bounds.minCol), c2 = at(bounds.maxRow, bounds.maxCol);
    const x0 = Math.min(c1.x, c2.x) - pad, x1 = Math.max(c1.x, c2.x) + pad;
    const y0 = Math.min(c1.y, c2.y) - pad, y1 = Math.max(c1.y, c2.y) + pad;
    const box = { x: x0, y: y0, width: x1 - x0, height: y1 - y0 };
    const style = (0, componentGlyphs_1.bodyStyle)(def);
    let outline = { box, path: null, marker: null };
    if (style === "belly" && pins.length === 3) {
        outline = { box: null, path: (0, componentGlyphs_1.bellyPath)(pt(pins[0]), pt(pins[2]), pad), marker: null };
    }
    else if (style === "dip" && pins.length >= 4) {
        outline = { box, path: null, marker: { d: (0, componentGlyphs_1.dipNotch)(pins.map(pt), centre, pad), filled: false } };
    }
    else if (style === "board" && pins.length >= 4) {
        outline = { box, path: null, marker: { d: (0, componentGlyphs_1.usbPort)(pins.map(pt), centre, { x0, y0, x1, y1 }, unit), filled: true } };
    }
    return {
        ...base,
        outline,
        label: { x: (x0 + x1) / 2, y: y0 - 4 * scale, onBody: false, onDark: false },
    };
}
