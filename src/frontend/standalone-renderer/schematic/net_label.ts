function esc(s: string) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

const S = 1.5;

function textPlacement(kind: string, rotation: number) {
  const d = (kind === "gnd" ? 26 : 16) * S;
  const dir = kind === "gnd" ? 1 : -1;
  let x = 0, y = dir * d;
  for (let i = 0; i < rotation / 90; i++) [x, y] = [-y, x];
  const anchor = x > 1 ? "start" : x < -1 ? "end" : "middle";
  const baseline = y > 1 ? "hanging" : y < -1 ? "auto" : "central";
  return { x, y, anchor: anchor as "start" | "middle" | "end", baseline: baseline as "hanging" | "auto" | "central" };
}

export function draw_net_label(label: {
  kind: "gnd" | "power" | "label";
  name: string;
  pos: { x: number; y: number };
  rotation: 0 | 90 | 180 | 270;
}, color?: string): string {
  const stroke = color ?? "#111";
  const strokeWidth = 1.5;
  const tp = textPlacement(label.kind, label.rotation);
  const showName = label.kind !== "gnd" || label.name !== "GND";

  const chunks: string[] = [];
  chunks.push(`<g transform="translate(${label.pos.x},${label.pos.y})">`);

  chunks.push(
    `<g transform="rotate(${label.rotation}) scale(${S})" ` +
      `fill="none" stroke="${esc(stroke)}" stroke-width="${strokeWidth / S}" ` +
      `stroke-linecap="round" stroke-linejoin="round">`,
  );

  if (label.kind === "gnd") {
    chunks.push(`<line x1="0" y1="0" x2="0" y2="10" />`);
    chunks.push(`<line x1="-8" y1="10" x2="8" y2="10" />`);
    chunks.push(`<line x1="-5" y1="14" x2="5" y2="14" />`);
    chunks.push(`<line x1="-2" y1="18" x2="2" y2="18" />`);
  } else if (label.kind === "power") {
    chunks.push(`<line x1="0" y1="0" x2="0" y2="-10" />`);
    chunks.push(`<line x1="-7" y1="-10" x2="7" y2="-10" />`);
  } else {
    chunks.push(`<line x1="0" y1="0" x2="0" y2="-8" />`);
    const fill = color ?? "#fff";
    chunks.push(`<path d="M -4 -8 L 4 -8 L 4 -12 L -4 -12 Z" fill="${esc(fill)}" fill-opacity="0.35" />`);
  }
  chunks.push(`</g>`);

  if (showName) {
    chunks.push(
      `<text x="${tp.x}" y="${tp.y}" font-size="13" font-weight="600" ` +
        `text-anchor="${tp.anchor}" dominant-baseline="${tp.baseline}" ` +
        `font-family="system-ui,sans-serif" fill="#111" ` +
        `stroke="#fff" stroke-width="3" stroke-linejoin="round" paint-order="stroke">${esc(label.name)}</text>`,
    );
  }

  const c = color ?? "#111";
  chunks.push(`<circle r="2.5" fill="${esc(c)}" stroke="${esc(c)}" stroke-width="1.5" />`);
  chunks.push(`</g>`);
  return chunks.join("\n");
}
