"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.computeConnectivity = computeConnectivity;
exports.getGroupForSegment = getGroupForSegment;
exports.getGroupForWire = getGroupForWire;
const stripSegments_1 = require("./stripSegments");
const boardPattern_1 = require("./boardPattern");
// ── Union-Find ─────────────────────────────────────────
class UnionFind {
    constructor(size) {
        this.parent = Array.from({ length: size }, (_, i) => i);
        this.rank = new Array(size).fill(0);
    }
    find(x) {
        if (this.parent[x] !== x) {
            this.parent[x] = this.find(this.parent[x]);
        }
        return this.parent[x];
    }
    union(a, b) {
        const ra = this.find(a);
        const rb = this.find(b);
        if (ra === rb)
            return;
        if (this.rank[ra] < this.rank[rb]) {
            this.parent[ra] = rb;
        }
        else if (this.rank[ra] > this.rank[rb]) {
            this.parent[rb] = ra;
        }
        else {
            this.parent[rb] = ra;
            this.rank[ra]++;
        }
    }
    connected(a, b) {
        return this.find(a) === this.find(b);
    }
}
/**
 * Compute connected groups of strip segments bridged by wires. On a board
 * with a pattern (`board`), a wire with an end where it has no hole joins nothing.
 */
function computeConnectivity(segments, wires, board) {
    const n = segments.length;
    if (n === 0)
        return [];
    const uf = new UnionFind(n);
    const wireSegmentMap = [];
    // Copper that turns a corner is a run along a row and one down a column
    // sharing a hole: one piece of copper
    if (segments.some((s) => s.endRow !== undefined)) {
        const claimed = new Map();
        segments.forEach((s, i) => {
            for (let row = s.row; row <= (s.endRow ?? s.row); row++) {
                for (let col = s.startCol; col <= s.endCol; col++) {
                    const key = `${row},${col}`;
                    const other = claimed.get(key);
                    if (other === undefined)
                        claimed.set(key, i);
                    else
                        uf.union(other, i);
                }
            }
        });
    }
    for (const wire of wires) {
        if (board?.pattern && (!(0, boardPattern_1.hasHole)(board, wire.from.row, wire.from.col) || !(0, boardPattern_1.hasHole)(board, wire.to.row, wire.to.col)))
            continue;
        const fromIdx = (0, stripSegments_1.findSegmentIndex)(segments, wire.from.row, wire.from.col);
        const toIdx = (0, stripSegments_1.findSegmentIndex)(segments, wire.to.row, wire.to.col);
        if (fromIdx >= 0 && toIdx >= 0) {
            uf.union(fromIdx, toIdx);
            wireSegmentMap.push({ wireId: wire.id, fromIdx, toIdx });
        }
    }
    // Group segments by root
    const groups = new Map();
    for (let i = 0; i < n; i++) {
        const root = uf.find(i);
        if (!groups.has(root)) {
            groups.set(root, {
                segmentIndices: [],
                wireIds: [],
                netIds: [],
                hasConflict: false,
            });
        }
        groups.get(root).segmentIndices.push(i);
    }
    // Add wire IDs to groups
    for (const { wireId, fromIdx } of wireSegmentMap) {
        const root = uf.find(fromIdx);
        const group = groups.get(root);
        if (!group.wireIds.includes(wireId)) {
            group.wireIds.push(wireId);
        }
    }
    // Collect nets per group
    for (const group of groups.values()) {
        const netSet = new Set();
        for (const idx of group.segmentIndices) {
            for (const netId of segments[idx].netIds) {
                netSet.add(netId);
            }
        }
        group.netIds = Array.from(netSet);
        group.hasConflict = group.netIds.length >= 2;
    }
    return Array.from(groups.values());
}
// The board asks for every segment's and wire's group on each render, so
// each groups array gets an index the first time it is asked
const indexes = new WeakMap();
function indexOf(groups) {
    let index = indexes.get(groups);
    if (!index) {
        index = { bySegment: new Map(), byWire: new Map() };
        for (const g of groups) {
            for (const si of g.segmentIndices)
                index.bySegment.set(si, g);
            for (const w of g.wireIds)
                index.byWire.set(w, g);
        }
        indexes.set(groups, index);
    }
    return index;
}
/** Get the connected group that a given segment belongs to */
function getGroupForSegment(groups, segmentIndex) {
    return indexOf(groups).bySegment.get(segmentIndex);
}
/** Get the connected group for a wire */
function getGroupForWire(groups, wireId) {
    return indexOf(groups).byWire.get(wireId);
}
