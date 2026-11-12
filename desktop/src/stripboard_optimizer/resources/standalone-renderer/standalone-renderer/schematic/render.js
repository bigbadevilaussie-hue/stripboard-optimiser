"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.renderSchematic = renderSchematic;
const resolve_symbol_1 = require("./resolve_symbol");
const component_block_1 = require("./component_block");
const wire_line_1 = require("./wire_line");
const net_label_1 = require("./net_label");
const symbol_geometry_1 = require("./symbol_geometry");
function renderSchematic(projectData) {
    const comps = projectData.components ?? [];
    const defs = projectData.componentDefs ?? [];
    const nets = projectData.nets ?? [];
    const asg = projectData.netAssignments ?? [];
    const wires = projectData.schematicWires ?? [];
    const labels = projectData.netLabels ?? [];
    const netById = new Map(nets.map((n) => [n.id, n]));
    const netByName = new Map(nets.map((n) => [n.name, n]));
    const asgByPin = new Map();
    for (const a of asg)
        asgByPin.set(`${a.componentId}:${a.pinId}`, a.netId);
    // Spatial net map: rounded grid point -> netId.
    // Grid points are integer-valued in the JSON. Round both axes so pin ends
    // (which have been rotated) and wire ends (raw) both land on the same key.
    const pointToNet = new Map();
    const keyOf = (x, y) => `${Math.round(x)},${Math.round(y)}`;
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    const parts = [];
    // --- Pass 1: components. Seed pin endpoints into the spatial map. ---
    for (const c of comps) {
        const did = c.componentDefId || c.defId;
        const def = (0, resolve_symbol_1.resolveDef)(did, defs);
        const sym = (0, resolve_symbol_1.resolveSymbol)(def);
        if (!sym)
            continue;
        const cx = c.schematicPos?.x ?? 0;
        const cy = c.schematicPos?.y ?? 0;
        const rot = (c.schematicRotation ?? 0);
        const mir = !!c.schematicMirrored;
        const pinColors = {};
        for (const p of sym.pins) {
            const netId = asgByPin.get(`${c.id}:${p.pinId}`);
            if (netId) {
                const net = netById.get(netId);
                if (net && net.color)
                    pinColors[p.pinId] = net.color;
                const world = (0, symbol_geometry_1.transformPoint)(p.stubEnd.x, p.stubEnd.y, rot, mir);
                const k = keyOf(cx + world.x, cy + world.y);
                if (!pointToNet.has(k))
                    pointToNet.set(k, netId);
            }
        }
        parts.push((0, component_block_1.draw_component)(c, def, sym, pinColors));
        const b = (0, symbol_geometry_1.getSymbolBounds)(sym, rot, mir);
        if (cx + b.minX < minX)
            minX = cx + b.minX;
        if (cy + b.minY < minY)
            minY = cy + b.minY;
        if (cx + b.maxX > maxX)
            maxX = cx + b.maxX;
        if (cy + b.maxY > maxY)
            maxY = cy + b.maxY;
    }
    // --- Pass 2: net labels. Seed their connection points into the map. ---
    for (const lbl of labels) {
        const net = netByName.get(lbl.name);
        if (net) {
            const k = keyOf(lbl.pos.x, lbl.pos.y);
            if (!pointToNet.has(k))
                pointToNet.set(k, net.id);
        }
    }
    // --- Pass 3: wires. Resolve colour from either endpoint. ---
    for (const w of wires) {
        const netId = pointToNet.get(keyOf(w.start.x, w.start.y)) ??
            pointToNet.get(keyOf(w.end.x, w.end.y));
        const net = netId ? netById.get(netId) : null;
        const color = net && net.color ? net.color : undefined;
        parts.push((0, wire_line_1.draw_wire)(w, color));
        if (w.start.x < minX)
            minX = w.start.x;
        if (w.start.y < minY)
            minY = w.start.y;
        if (w.end.x > maxX)
            maxX = w.end.x;
        if (w.end.y > maxY)
            maxY = w.end.y;
    }
    // --- Pass 4: net label glyphs. ---
    for (const lbl of labels) {
        let color = "#333";
        const net = netByName.get(lbl.name);
        if (net && net.color)
            color = net.color;
        parts.push((0, net_label_1.draw_net_label)(lbl, color));
        if (lbl.pos.x < minX)
            minX = lbl.pos.x;
        if (lbl.pos.y < minY)
            minY = lbl.pos.y;
        if (lbl.pos.x > maxX)
            maxX = lbl.pos.x;
        if (lbl.pos.y > maxY)
            maxY = lbl.pos.y;
    }
    if (minX === Infinity) {
        minX = 0;
        minY = 0;
        maxX = 800;
        maxY = 600;
    }
    const margin = 50;
    minX -= margin;
    minY -= margin;
    maxX += margin;
    maxY += margin;
    const w = maxX - minX;
    const h = maxY - minY;
    return `<svg xmlns="http://www.w3.org/2000/svg" width="${w * 0.1}mm" height="${h * 0.1}mm" viewBox="${minX} ${minY} ${w} ${h}" style="background: #fff">${parts.join("")}</svg>`;
}
