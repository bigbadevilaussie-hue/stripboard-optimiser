"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.STRIP_CONFLICT_COLOR = exports.STRIP_COLOR = exports.LABEL_FONT_SIZE = exports.STRIP_HEIGHT = exports.HOLE_RADIUS = exports.HOLE_SPACING = void 0;
exports.holeCenter = holeCenter;
exports.nearestHole = nearestHole;
exports.boardRect = boardRect;
exports.nearestCutTarget = nearestCutTarget;
exports.nearestPatternCut = nearestPatternCut;
exports.cutPoint = cutPoint;
exports.getRotatedPinPositions = getRotatedPinPositions;
exports.getRotatedBodyCells = getRotatedBodyCells;
exports.getComponentPinPositions = getComponentPinPositions;
exports.getFlexiblePinPositions = getFlexiblePinPositions;
exports.getFlexibleBounds = getFlexibleBounds;
exports.getComponentBounds = getComponentBounds;
// Grid constants
exports.HOLE_SPACING = 30;
exports.HOLE_RADIUS = 4.5;
const BOARD_PADDING = 60;
exports.STRIP_HEIGHT = 6;
exports.LABEL_FONT_SIZE = 11;
// Copper strip color — default values kept for JS logic (segment coloring).
// CSS variables --strip-color and --strip-conflict-color are used in SVG rendering.
exports.STRIP_COLOR = "#D4A853";
exports.STRIP_CONFLICT_COLOR = "#dc2626";
/** Convert grid coordinates to SVG pixel coordinates */
function holeCenter(row, col) {
    return {
        x: BOARD_PADDING + col * exports.HOLE_SPACING,
        y: BOARD_PADDING + row * exports.HOLE_SPACING,
    };
}
/** Snap SVG pixel coordinates to nearest hole, or null if out of bounds */
function nearestHole(svgX, svgY, rows, cols) {
    const col = Math.round((svgX - BOARD_PADDING) / exports.HOLE_SPACING);
    const row = Math.round((svgY - BOARD_PADDING) / exports.HOLE_SPACING);
    if (row < 0 || row >= rows || col < 0 || col >= cols)
        return null;
    return { row, col };
}
/**
 * The physical board: the laminate the holes are punched in, which runs a bit
 * past the outermost holes on every side.
 */
function boardRect(rows, cols) {
    const margin = exports.HOLE_SPACING * 0.6;
    return {
        x: BOARD_PADDING - margin,
        y: BOARD_PADDING - margin,
        width: (cols - 1) * exports.HOLE_SPACING + margin * 2,
        height: (rows - 1) * exports.HOLE_SPACING + margin * 2,
    };
}
/**
 * The cut position nearest a point, with no dead zone: either the hole itself
 * or the gap on whichever side is closer. Used by the cut tool, where
 * cuts are the only thing a click can mean.
 */
function nearestCutTarget(svgX, svgY, rows, cols) {
    const row = Math.round((svgY - BOARD_PADDING) / exports.HOLE_SPACING);
    if (row < 0 || row >= rows)
        return null;
    if (Math.abs(svgY - (BOARD_PADDING + row * exports.HOLE_SPACING)) > exports.HOLE_SPACING * 0.5)
        return null;
    const colFloat = (svgX - BOARD_PADDING) / exports.HOLE_SPACING;
    const hole = Math.round(colFloat);
    const gap = Math.floor(colFloat);
    if (Math.abs(colFloat - hole) <= Math.abs(colFloat - (gap + 0.5))) {
        return hole >= 0 && hole < cols ? { row, col: hole, kind: "hole" } : null;
    }
    return gap >= 0 && gap < cols - 1 ? { row, col: gap, kind: "between" } : null;
}
/**
 * The same for a board with a pattern, where copper may run down a column as
 * well: the nearest place a cut can go, of those the board has copper for.
 */
function nearestPatternCut(svgX, svgY, fits) {
    const rowFloat = (svgY - BOARD_PADDING) / exports.HOLE_SPACING;
    const colFloat = (svgX - BOARD_PADDING) / exports.HOLE_SPACING;
    const row = Math.round(rowFloat);
    const col = Math.round(colFloat);
    const candidates = [];
    for (let r = row - 1; r <= row + 1; r++) {
        for (let c = col - 1; c <= col + 1; c++) {
            candidates.push({ row: r, col: c, kind: "hole" }, { row: r, col: c, kind: "between" }, { row: r, col: c, kind: "below" });
        }
    }
    let best = null;
    let bestDist = exports.HOLE_SPACING * 0.75;
    for (const cut of candidates) {
        const p = cutPoint(cut);
        const dist = Math.hypot(p.x - svgX, p.y - svgY);
        if (dist < bestDist && fits(cut)) {
            best = cut;
            bestDist = dist;
        }
    }
    return best;
}
/** Where a cut sits: on its hole, or halfway to the next hole right or below. */
function cutPoint(cut) {
    return holeCenter(cut.row + (cut.kind === "below" ? 0.5 : 0), cut.col + (cut.kind === "hole" || cut.kind === "below" ? 0 : 0.5));
}
/** Get the bounding box max row/col for a component def (pins + body cells) */
function getDefMaxExtents(def) {
    const allRows = def.pins.map((p) => p.offsetRow);
    const allCols = def.pins.map((p) => p.offsetCol);
    if (def.bodyCells) {
        allRows.push(...def.bodyCells.map((c) => c.row));
        allCols.push(...def.bodyCells.map((c) => c.col));
    }
    return {
        maxRow: Math.max(...allRows),
        maxCol: Math.max(...allCols),
    };
}
/** Apply rotation to a single (row, col) offset */
function rotateOffset(r, c, rotation, maxRow, maxCol) {
    switch (rotation) {
        case 90:
            return { r: c, c: maxRow - r };
        case 180:
            return { r: maxRow - r, c: maxCol - c };
        case 270:
            return { r: maxCol - c, c: r };
        default:
            return { r, c };
    }
}
/** Get absolute board positions of all pins after applying rotation */
function getRotatedPinPositions(def, boardPos, rotation) {
    const { maxRow, maxCol } = getDefMaxExtents(def);
    return def.pins.map((pin) => {
        const rotated = rotateOffset(pin.offsetRow, pin.offsetCol, rotation, maxRow, maxCol);
        return {
            pinId: pin.id,
            row: boardPos.row + rotated.r,
            col: boardPos.col + rotated.c,
        };
    });
}
/** Get absolute board positions of all body cells after applying rotation */
function getRotatedBodyCells(def, boardPos, rotation) {
    if (!def.bodyCells || def.bodyCells.length === 0)
        return [];
    const { maxRow, maxCol } = getDefMaxExtents(def);
    return def.bodyCells.map((cell) => {
        const rotated = rotateOffset(cell.row, cell.col, rotation, maxRow, maxCol);
        return {
            row: boardPos.row + rotated.r,
            col: boardPos.col + rotated.c,
        };
    });
}
/** Get pin positions for any component — handles both flexible and fixed */
function getComponentPinPositions(comp, def) {
    if (!comp.boardPos)
        return [];
    if (def.flexible) {
        return getFlexiblePinPositions(comp, def);
    }
    return getRotatedPinPositions(def, comp.boardPos, comp.rotation);
}
/** Get pin positions for a flexible 2-pin component */
function getFlexiblePinPositions(comp, def) {
    if (!comp.boardPos)
        return [];
    const pin1Pos = comp.boardPos;
    const pin2Pos = comp.flexibleEndPos ?? {
        row: pin1Pos.row + (def.pins[1]?.offsetRow ?? 1),
        col: pin1Pos.col + (def.pins[1]?.offsetCol ?? 0),
    };
    return [
        { pinId: def.pins[0]?.id ?? "1", row: pin1Pos.row, col: pin1Pos.col },
        { pinId: def.pins[1]?.id ?? "2", row: pin2Pos.row, col: pin2Pos.col },
    ];
}
/** Get bounding box for a flexible 2-pin component */
function getFlexibleBounds(comp, def) {
    const pins = getFlexiblePinPositions(comp, def);
    if (pins.length < 2)
        return { minRow: 0, minCol: 0, maxRow: 0, maxCol: 0 };
    return {
        minRow: Math.min(pins[0].row, pins[1].row),
        minCol: Math.min(pins[0].col, pins[1].col),
        maxRow: Math.max(pins[0].row, pins[1].row),
        maxCol: Math.max(pins[0].col, pins[1].col),
    };
}
/** Get the bounding box of a component on the board (pins + body cells) */
function getComponentBounds(def, boardPos, rotation) {
    const pins = getRotatedPinPositions(def, boardPos, rotation);
    const bodyCells = getRotatedBodyCells(def, boardPos, rotation);
    const allRows = [...pins.map((p) => p.row), ...bodyCells.map((c) => c.row)];
    const allCols = [...pins.map((p) => p.col), ...bodyCells.map((c) => c.col)];
    return {
        minRow: Math.min(...allRows),
        minCol: Math.min(...allCols),
        maxRow: Math.max(...allRows),
        maxCol: Math.max(...allCols),
    };
}
