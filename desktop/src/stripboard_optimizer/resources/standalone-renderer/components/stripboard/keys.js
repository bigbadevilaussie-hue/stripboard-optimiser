"use strict";
// Canonical map/set key builders shared by the solver modules. The formats
// are load-bearing wherever a key is built in one place and probed in
// another, so build keys through these helpers instead of inline templates.
Object.defineProperty(exports, "__esModule", { value: true });
exports.pinKey = exports.holeKey = void 0;
/** Key for a board hole. */
const holeKey = (row, col) => `${row},${col}`;
exports.holeKey = holeKey;
/** Key for a component pin (net lookup maps). */
const pinKey = (componentId, pinId) => `${componentId}:${pinId}`;
exports.pinKey = pinKey;
