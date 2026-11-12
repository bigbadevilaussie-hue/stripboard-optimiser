export type Rotation = 0 | 90 | 180 | 270;
export interface Point { x: number; y: number; }

export function rotatePoint(x: number, y: number, rotation: Rotation): Point {
  switch (rotation) {
    case 90: return { x: -y, y: x };
    case 180: return { x: -x, y: -y };
    case 270: return { x: y, y: -x };
    default: return { x, y };
  }
}

export function transformPoint(x: number, y: number, rotation: Rotation, mirrored: boolean): Point {
  const mx = mirrored ? -x : x;
  return rotatePoint(mx, y, rotation);
}

export function getRotatedPinPositions(symbol: any, rotation: Rotation = 0, mirrored = false) {
  return symbol.pins.map((pin: any) => {
    const p = transformPoint(pin.stubEnd.x, pin.stubEnd.y, rotation, mirrored);
    return { pinId: pin.pinId, x: p.x, y: p.y };
  });
}

export function getSymbolBounds(symbol: any, rotation: Rotation = 0, mirrored = false) {
  const pts: Point[] = [{ x: 0, y: 0 }];
  for (const pin of symbol.pins ?? []) {
    pts.push(transformPoint(pin.stubStart.x, pin.stubStart.y, rotation, mirrored));
    pts.push(transformPoint(pin.stubEnd.x, pin.stubEnd.y, rotation, mirrored));
  }
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const p of pts) {
    if (p.x < minX) minX = p.x;
    if (p.y < minY) minY = p.y;
    if (p.x > maxX) maxX = p.x;
    if (p.y > maxY) maxY = p.y;
  }
  if (!isFinite(minX)) return { minX: -20, minY: -20, maxX: 20, maxY: 20, width: 40, height: 40 };
  return { minX, minY, maxX, maxY, width: maxX - minX, height: maxY - minY };
}

export function getPinLabelProps(
  attach: Point,
  side: "top" | "bottom" | "left" | "right",
  rotation: Rotation,
  mirrored = false,
  offset = 8,
): { x: number; y: number; anchor: "start" | "middle" | "end"; baseline: "auto" | "hanging" | "central" } {
  let effectiveSide = side;
  if (mirrored) {
    if (side === "left") effectiveSide = "right";
    else if (side === "right") effectiveSide = "left";
  }
  const sideOrder: Array<"top" | "right" | "bottom" | "left"> = ["top", "right", "bottom", "left"];
  const rotSteps = (rotation / 90) | 0;
  effectiveSide = sideOrder[(sideOrder.indexOf(effectiveSide) + rotSteps) % 4];
  const rp = transformPoint(attach.x, attach.y, rotation, mirrored);
  switch (effectiveSide) {
    case "top": return { x: rp.x, y: rp.y - offset, anchor: "middle", baseline: "auto" };
    case "bottom": return { x: rp.x, y: rp.y + offset + 2, anchor: "middle", baseline: "hanging" };
    case "left": return { x: rp.x - offset, y: rp.y, anchor: "end", baseline: "central" };
    case "right": return { x: rp.x + offset, y: rp.y, anchor: "start", baseline: "central" };
  }
}
