"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.copperOf = copperOf;
exports.patternSize = patternSize;
exports.buildMap = buildMap;
exports.editableCopper = editableCopper;
exports.mapOf = mapOf;
exports.stripboardMap = stripboardMap;
exports.mapError = mapError;
exports.hasHole = hasHole;
exports.joinsRight = joinsRight;
exports.joinsDown = joinsDown;
exports.cutFits = cutFits;
exports.partOnBoard = partOnBoard;
exports.offHoles = offHoles;
exports.misfits = misfits;
const resolveComponentDef_1 = require("../../utils/resolveComponentDef.js");
const boardLayout_1 = require("./boardLayout");
const parsed = new WeakMap();
function copperOf(map) {
    let copper = parsed.get(map);
    if (!copper) {
        const { rows, cols } = patternSize(map);
        copper = { rows, cols, hole: new Uint8Array(rows * cols), right: new Uint8Array(rows * cols), down: new Uint8Array(rows * cols) };
        const { hole, right, down } = copper;
        for (let r = 0; r < rows; r++) {
            for (let c = 0; c < cols; c++)
                hole[r * cols + c] = map[r * 2][c * 2] === "o" ? 1 : 0;
        }
        for (let r = 0; r < rows; r++) {
            for (let c = 0; c < cols; c++) {
                const i = r * cols + c;
                right[i] = c < cols - 1 && map[r * 2][c * 2 + 1] === "-" ? 1 : 0;
                down[i] = r < rows - 1 && map[r * 2 + 1][c * 2] === "|" ? 1 : 0;
            }
        }
        parsed.set(map, copper);
    }
    return copper;
}
function patternSize(map) {
    return { rows: (map.length + 1) / 2, cols: (map[0].length + 1) / 2 };
}
/** The map of a board whose holes and copper the three functions describe. */
function buildMap(rows, cols, hole, right, down) {
    const map = [];
    for (let r = 0; r < rows; r++) {
        let line = "";
        let under = "";
        for (let c = 0; c < cols; c++) {
            line += hole(r, c) ? "o" : ".";
            under += r < rows - 1 && down(r, c) ? "|" : " ";
            if (c < cols - 1) {
                line += right(r, c) ? "-" : " ";
                under += " ";
            }
        }
        map.push(line);
        if (r < rows - 1)
            map.push(under);
    }
    return map;
}
/** A copy of a map's copper that may be changed, unlike the parsed one. */
function editableCopper(map) {
    const c = copperOf(map);
    return { rows: c.rows, cols: c.cols, hole: c.hole.slice(), right: c.right.slice(), down: c.down.slice() };
}
function mapOf(copper) {
    const { cols } = copper;
    return buildMap(copper.rows, cols, (r, c) => copper.hole[r * cols + c] === 1, (r, c) => copper.right[r * cols + c] === 1, (r, c) => copper.down[r * cols + c] === 1);
}
/** Plain stripboard as a map: every row one strip. */
function stripboardMap(rows, cols) {
    return buildMap(rows, cols, () => true, () => true, () => false);
}
/** What is wrong with a map, or null for one a board can use. */
function mapError(map) {
    if (!Array.isArray(map) || map.length === 0 || map.length % 2 === 0)
        return "A board map needs an odd number of lines";
    const width = map[0]?.length;
    if (typeof width !== "number" || width % 2 === 0)
        return "A board map needs lines of odd length";
    for (let i = 0; i < map.length; i++) {
        const line = map[i];
        if (typeof line !== "string" || line.length !== width)
            return "Every line of a board map must be equally long";
        const ok = i % 2 === 0 ? /^[o.]([- ][o.])*$/ : /^[| ]( [| ])*$/;
        if (!ok.test(line))
            return "A board map holds only o . - | and spaces";
    }
    return null;
}
const inBounds = (board, row, col) => row >= 0 && col >= 0 && row < board.rows && col < board.cols;
function hasHole(board, row, col) {
    if (!inBounds(board, row, col))
        return false;
    return !board.pattern || copperOf(board.pattern.map).hole[row * board.cols + col] === 1;
}
/** Copper joins this hole to the one on its right. */
function joinsRight(board, row, col) {
    if (!inBounds(board, row, col) || col >= board.cols - 1)
        return false;
    return !board.pattern || copperOf(board.pattern.map).right[row * board.cols + col] === 1;
}
/** Copper joins this hole to the one below it. */
function joinsDown(board, row, col) {
    if (!board.pattern || !inBounds(board, row, col) || row >= board.rows - 1)
        return false;
    return copperOf(board.pattern.map).down[row * board.cols + col] === 1;
}
/** Whether the board has copper where the cut would go. */
function cutFits(board, cut) {
    const { row, col } = cut;
    if (cut.kind === "below")
        return joinsDown(board, row, col);
    if (cut.kind !== "hole")
        return joinsRight(board, row, col);
    // A drill on a pad no copper leaves would cut nothing
    return hasHole(board, row, col) && (!board.pattern ||
        joinsRight(board, row, col) || joinsRight(board, row, col - 1) ||
        joinsDown(board, row, col) || joinsDown(board, row - 1, col));
}
/** A placed part lies on the board: its body and all its pins. */
function partOnBoard(board, comp, def) {
    if (!comp.boardPos)
        return true;
    if (!def.flexible) {
        const b = (0, boardLayout_1.getComponentBounds)(def, comp.boardPos, comp.rotation);
        if (b.minRow < 0 || b.minCol < 0 || b.maxRow >= board.rows || b.maxCol >= board.cols)
            return false;
    }
    return (0, boardLayout_1.getComponentPinPositions)(comp, def).every((p) => inBounds(board, p.row, p.col));
}
/**
 * Pins of placed parts and ends of wires where the board has no hole: they
 * may go there while being moved about, but connect to nothing and are
 * shown as wrong.
 */
function offHoles(board, components, componentDefs) {
    if (!board.pattern)
        return [];
    const out = [];
    for (const c of components) {
        const def = c.boardPos && (0, resolveComponentDef_1.resolveComponentDef)(c, componentDefs);
        if (!def)
            continue;
        for (const p of (0, boardLayout_1.getComponentPinPositions)(c, def))
            if (!hasHole(board, p.row, p.col))
                out.push({ row: p.row, col: p.col });
    }
    for (const w of board.wires) {
        for (const end of [w.from, w.to])
            if (!hasHole(board, end.row, end.col))
                out.push(end);
    }
    return out;
}
/** What cannot stay on a board: parts and wires off its edges (by id), and cuts where it has no copper. */
function misfits(board, components, componentDefs) {
    const parts = components.filter((c) => {
        const def = c.boardPos && (0, resolveComponentDef_1.resolveComponentDef)(c, componentDefs);
        return def && !partOnBoard(board, c, def);
    }).map((c) => c.id);
    const wires = board.wires
        .filter((w) => !inBounds(board, w.from.row, w.from.col) || !inBounds(board, w.to.row, w.to.col))
        .map((w) => w.id);
    const cuts = board.cuts.filter((c) => !cutFits(board, c));
    return { parts, wires, cuts };
}
