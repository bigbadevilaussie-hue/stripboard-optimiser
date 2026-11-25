"""Deterministic, source-controlled StripSolve icon artwork.

SVG is the master format: crisp at 24px, 48px and Retina resolutions.
No network, image-generation service or proprietary font is required.
"""
from __future__ import annotations

from html import escape

INK = "#19334d"
NAVY = "#183c59"
BLUE = "#257ac2"
CYAN = "#00b4d8"
TEAL = "#0d9488"
GREEN = "#16a34a"
COPPER = "#c87d4b"
CORAL = "#e85d4a"
AMBER = "#f59e0b"
ICE = "#e6f5ff"
WHITE = "#ffffff"

ICON_KEYS = (
    "load_json", "stop_solve", "pass_one", "pass_two", "component_side",
    "copper_side", "schematic", "open_solved", "exit", "fit_board",
)


def _path(d: str, *, color: str = NAVY, width: float = 2.6,
          fill: str = "none") -> str:
    return (f'<path d="{escape(d)}" fill="{fill}" stroke="{color}" '
            f'stroke-width="{width}" stroke-linecap="round" '
            'stroke-linejoin="round"/>')


def _circle(x, y, radius, fill=WHITE, stroke=TEAL, width=2):
    return (f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{width}"/>')


def _rect(x, y, w, h, r=3, fill=WHITE, stroke=NAVY, width=2):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>')


def _board(x=7, y=9, w=34, h=30):
    parts = [_rect(x, y, w, h, 4, "#efb38b", COPPER, 1.6)]
    for yy in (y+7, y+15, y+23):
        parts.append(_path(f"M{x+3} {yy} H{x+w-3}", color="#bf7040", width=3.2))
        for xx in (x+7, x+16, x+25):
            parts.append(_circle(xx, yy, 1.9, "#fff6ed", COPPER, 1))
    return "".join(parts)


def icon_svg(key: str) -> str:
    """Return a complete, valid 48x48 standalone SVG for a known button."""
    if key not in ICON_KEYS:
        raise KeyError(key)
    art = {
        "load_json": (
            _path("M10 4 H28 L37 13 V41 H10 Z", fill="#f3faff")
            + _path("M28 4 V13 H37", color=BLUE)
            + _path("M17 20 C13 20 13 24 17 24 C13 24 13 28 17 28", color=TEAL, width=2.5)
            + _path("M30 20 C34 20 34 24 30 24 C34 24 34 28 30 28", color=TEAL, width=2.5)
            + _circle(24, 34, 2.6, CYAN, BLUE, 1.2)
        ),
        "stop_solve": (
            _rect(6, 6, 36, 36, 11, "#fff0ed", CORAL, 2.4)
            + _path("M19 11 V23 M25 11 V23 M31 13 V23 M15 17 V27 "
                    "C15 35 20 38 26 38 C33 38 36 33 36 27 V21", color=CORAL, width=3)
            + _path("M14 28 L9 23", color=CORAL, width=3)
        ),
        "pass_one": (
            _circle(9, 36, 4, WHITE, TEAL, 2.7)
            + _circle(24, 23, 4, WHITE, BLUE, 2.7)
            + _circle(39, 11, 4, WHITE, CYAN, 2.7)
            + _path("M13 33 L20 27 M28 20 L35 14", color=BLUE, width=3.5)
            + _path("M7 10 H20 M7 16 H14", color=NAVY, width=2.2)
            + _path("M36 38 H43", color=NAVY, width=2.2)
        ),
        "pass_two": (
            _circle(9, 35, 4, WHITE, TEAL, 2.6)
            + _circle(23, 25, 4, WHITE, BLUE, 2.6)
            + _circle(39, 13, 4, WHITE, CYAN, 2.6)
            + _path("M13 32 L19 28 M27 22 L34 16", color=TEAL, width=3)
            + _path("M8 11 L17 11 L23 5 L31 5", color=NAVY, width=2)
            + _path("M17 8 L17 13", color=CORAL, width=2.5)
            + _path("M36 35 L41 40 L47 30", color=GREEN, width=2.8)
        ),
        "component_side": (
            _board()
            + _rect(15, 15, 18, 10, 2, "#426b81", NAVY, 1.4)
            + _path("M17 29 V35 M24 29 V35 M31 29 V35", color=TEAL, width=2.1)
        ),
        "copper_side": (
            _board()
            + _path("M11 17 H20 V26 H34 M12 32 H29 V22 H37", color=CYAN, width=2.7)
            + _circle(21, 17, 2, COPPER, NAVY, 1)
            + _circle(30, 32, 2, COPPER, NAVY, 1)
            + _path("M32 10 L40 18 M40 10 L32 18", color=CORAL, width=2.5)
        ),
        "schematic": (
            _path("M6 16 H17 L23 10 L29 16 H42 M6 33 H16 L22 27 H31 L36 33 H42",
                  color=NAVY, width=2.4)
            + _rect(17, 18, 14, 12, 2, "#e3f5ff", BLUE, 2)
            + _path("M20 22 H28 M20 26 H28", color=TEAL, width=2)
            + _circle(6, 16, 2.4, WHITE, BLUE, 1.5)
            + _circle(42, 33, 2.4, WHITE, BLUE, 1.5)
        ),
        "open_solved": (
            _path("M12 5 H29 L36 13 V39 H12 Z", fill="#e8f6ff")
            + _path("M29 5 V13 H36", color=BLUE)
            + _path("M15 30 L23 36 L35 20", color=GREEN, width=4)
            + _circle(17, 17, 2, COPPER, "#9b613c", 1)
            + _circle(25, 17, 2, COPPER, "#9b613c", 1)
        ),
        "exit": (
            _path("M25 7 H11 V41 H25", color=NAVY, width=3)
            + _path("M19 24 H42 M34 16 L42 24 L34 32", color=CORAL, width=4)
            + _circle(18, 31, 2, TEAL, TEAL, 1)
        ),
        "fit_board": (
            _rect(15, 15, 18, 18, 2, "#fff1e6", COPPER, 2)
            + _path("M7 18 V7 H18 M30 7 H41 V18 M41 30 V41 H30 M18 41 H7 V30",
                    color=BLUE, width=3)
            + _path("M18 19 H30 M18 25 H30 M18 30 H30", color=TEAL, width=1.7)
        ),
    }[key]
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" '
            'width="48" height="48">' + art + '</svg>')


def app_icon_svg() -> str:
    """Bright StripSolve squircle with copper strips and a bold routed S."""
    copper_strips = []
    for y in range(310, 745, 56):
        copper_strips.append(
            f'<rect x="248" y="{y}" width="528" height="26" rx="13" '
            'fill="url(#copper)" opacity=".9"/>'
        )
        for x in range(280, 745, 66):
            copper_strips.append(
                f'<circle cx="{x}" cy="{y+13}" r="8" '
                'fill="#fbfcff" stroke="#ad6d46" stroke-width="4"/>'
            )
    grid = []
    for x in range(206, 830, 83):
        grid.append(f'<path d="M{x} 186 V840" stroke="#bed8e8" stroke-width="2" opacity=".55"/>')
    for y in range(195, 830, 83):
        grid.append(f'<path d="M186 {y} H838" stroke="#bed8e8" stroke-width="2" opacity=".55"/>')
    circuit = ('M688 310 H473 Q367 310 367 413 Q367 500 475 515 '
               'L573 541 Q677 566 677 656 Q677 756 555 756 H335')
    copper_route = ('M698 346 H496 Q411 346 411 422 Q411 474 502 501 '
                    'L588 531 Q642 548 642 634 Q642 713 541 713 H321')
    traces = "".join([
        '<path d="M262 361 H341 M692 410 H784 M242 574 H348 '
        'M684 661 H796 M325 725 H250" stroke="#0c8e94" stroke-width="10" '
        'stroke-linecap="round" opacity=".9"/>',
        '<g fill="#e3fff9" stroke="#118f9e" stroke-width="7">',
        '<circle cx="262" cy="361" r="12"/><circle cx="784" cy="410" r="12"/>',
        '<circle cx="242" cy="574" r="12"/><circle cx="796" cy="661" r="12"/>',
        '<circle cx="250" cy="725" r="12"/></g>',
    ])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024"
viewBox="0 0 1024 1024">
<defs>
 <linearGradient id="ice" x1="0" y1="0" x2=".9" y2="1">
  <stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#d9effb"/>
 </linearGradient>
 <linearGradient id="copper" x1="0" x2="0" y1="0" y2="1">
  <stop offset="0" stop-color="#f5c49c"/><stop offset=".5" stop-color="#c87d4b"/>
  <stop offset="1" stop-color="#a85e38"/>
 </linearGradient>
 <linearGradient id="route" x1="0" x2="1" y1="0" y2="1">
  <stop offset="0" stop-color="#00cfe8"/><stop offset=".48" stop-color="#257ac2"/>
  <stop offset="1" stop-color="#0e9687"/>
 </linearGradient>
</defs>
<rect x="45" y="45" width="934" height="934" rx="230"
 fill="#6bb6d0" opacity=".32"/>
<rect x="70" y="65" width="884" height="884" rx="205"
 fill="url(#ice)" stroke="#68aecb" stroke-width="18"/>
<rect x="110" y="108" width="805" height="805" rx="167"
 fill="none" stroke="#eaffff" stroke-width="12"/>
<g>{''.join(grid)}</g>
<rect x="217" y="265" width="590" height="532" rx="56"
 fill="#fff5ed" opacity=".28"/>
<g>{''.join(copper_strips)}</g>
<g>{traces}</g>
<path d="{copper_route}" fill="none" stroke="#ac603b" stroke-width="94"
 stroke-linecap="round" stroke-linejoin="round" opacity=".6"/>
<path d="{circuit}" fill="none" stroke="#103955" stroke-width="128"
 stroke-linecap="round" stroke-linejoin="round"/>
<path d="{circuit}" fill="none" stroke="url(#route)" stroke-width="101"
 stroke-linecap="round" stroke-linejoin="round"/>
<path d="{circuit}" fill="none" stroke="#9ceffd" stroke-width="10"
 stroke-linecap="round" stroke-linejoin="round" opacity=".9"/>
<path d="{copper_route}" fill="none" stroke="#e9a06b" stroke-width="16"
 stroke-linecap="round" stroke-linejoin="round" opacity=".9"/>
<g fill="#e6fffc" stroke="#33bfc5" stroke-width="8">
 <circle cx="367" cy="413" r="17"/><circle cx="677" cy="656" r="17"/>
 <circle cx="555" cy="756" r="17"/><circle cx="688" cy="310" r="17"/>
</g>
</svg>'''
