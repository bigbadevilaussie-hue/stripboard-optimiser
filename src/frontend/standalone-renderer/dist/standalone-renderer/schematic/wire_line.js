"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.draw_wire = draw_wire;
function draw_wire(wire, color) {
    const stroke = color ?? "#555";
    return `<line x1="${wire.start.x}" y1="${wire.start.y}" x2="${wire.end.x}" y2="${wire.end.y}" stroke="${stroke}" stroke-width="1.5" stroke-linecap="round" />`;
}
