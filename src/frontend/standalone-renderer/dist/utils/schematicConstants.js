"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.GRID_SIZE = void 0;
exports.snapToGrid = snapToGrid;
exports.pointKey = pointKey;
/** Grid size for the schematic canvas — all pin positions must be multiples of this */
exports.GRID_SIZE = 20;
/** Snap a value to the nearest grid point */
function snapToGrid(val) {
    return Math.round(val / exports.GRID_SIZE) * exports.GRID_SIZE;
}
/** Create a grid-aligned point key for spatial matching */
function pointKey(x, y) {
    return `${Math.round(x)},${Math.round(y)}`;
}
