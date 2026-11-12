export function draw_wire(wire: any, color?: string) {
  const stroke = color ?? "#555";
  return `<line x1="${wire.start.x}" y1="${wire.start.y}" x2="${wire.end.x}" y2="${wire.end.y}" stroke="${stroke}" stroke-width="1.5" stroke-linecap="round" />`;
}
