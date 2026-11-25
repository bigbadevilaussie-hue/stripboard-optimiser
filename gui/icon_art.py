"""StripSolve icon masters — polished copper / Arctic-Ice electrical identity.

SVG artwork is deterministic and independent of Qt. 48px toolbar SVGs are
rasterized at 24px by the GUI; the app SVG produces the 1024px master PNG.
"""
from __future__ import annotations

from html import escape

INK = "#17364d"
BLUE = "#2b7de9"
CYAN = "#00b4d8"
TEAL = "#0d9488"
GREEN = "#16a34a"
COPPER = "#c87d4b"
CORAL = "#e85d4a"
WHITE = "#ffffff"

ICON_KEYS = (
    "load_json", "stop_solve", "pass_one", "pass_two", "component_side",
    "copper_side", "schematic", "open_solved", "exit", "fit_board",
)

_DEFS = '''
<defs>
 <linearGradient id="board" x1="0" y1="0" x2="1" y2="1">
  <stop stop-color="#fff1dd"/><stop offset=".48" stop-color="#f2bf92"/>
  <stop offset="1" stop-color="#d99163"/>
 </linearGradient>
 <linearGradient id="copper" x1="0" y1="0" x2="0" y2="1">
  <stop stop-color="#ffddb5"/><stop offset=".25" stop-color="#eea66d"/>
  <stop offset=".58" stop-color="#bb6c41"/><stop offset="1" stop-color="#f5bd88"/>
 </linearGradient>
 <linearGradient id="trace" x1="0" y1="0" x2="1" y2="1">
  <stop stop-color="#3ff2f0"/><stop offset=".36" stop-color="#29b8df"/>
  <stop offset=".7" stop-color="#2778c6"/><stop offset="1" stop-color="#11b594"/>
 </linearGradient>
 <linearGradient id="ice" x1="0" y1="0" x2="1" y2="1">
  <stop stop-color="#ffffff"/><stop offset="1" stop-color="#d8f0fc"/>
 </linearGradient>
 <linearGradient id="chip" x1="0" y1="0" x2="1" y2="1">
  <stop stop-color="#526f82"/><stop offset=".5" stop-color="#24465f"/>
  <stop offset="1" stop-color="#102839"/>
 </linearGradient>
</defs>
'''


def _p(d, color=INK, width=2.3, fill="none"):
    return (f'<path d="{escape(d)}" fill="{fill}" stroke="{color}" '
            f'stroke-width="{width}" stroke-linecap="round" '
            'stroke-linejoin="round"/>')


def _r(x, y, w, h, rad=3, fill='url(#board)', stroke=INK, sw=2):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
            f'rx="{rad}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


def _c(x, y, rad=2.2, fill='#f1fcff', stroke='#8d624d', sw=1.6):
    return (f'<circle cx="{x}" cy="{y}" r="{rad}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


def _pcb(x=6, y=9, w=36, h=30, *, density=3):
    a = [_r(x, y, w, h, 4.2, 'url(#board)', '#966749', 1.8)]
    for n in range(density):
        yy = y + h * (n+1)/(density+1)
        a.append(_p(f'M{x+3} {yy} H{x+w-3}', 'url(#copper)', 3.5))
        for xx in [x+8, x+18, x+28]:
            if xx < x+w-3:
                a.append(_c(xx, yy, 2.1, '#fcffff', '#bd784f', 1.4))
    return ''.join(a)


def _via(x, y, fill='#bdf7f8'):
    return _c(x, y, 3.1, fill, '#0d8d9c', 1.8)+_c(x, y, 1.15, '#ffffff', '#e2fbff', .3)


def icon_svg(key: str) -> str:
    """Standalone, legible 48x48 icon in the approved blue/teal/copper system."""
    if key not in ICON_KEYS:
        raise KeyError(key)
    designs = {
        'load_json': (
            _p('M11 5 H28 L38 15 V40 Q38 43 35 43 H11 Q8 43 8 40 V8 Q8 5 11 5Z',
               '#234960', 2.3, 'url(#ice)')
            + _p('M28 5 V15 H38', '#2b7de9', 2.4)
            + _p('M18 21 C13 21 17 24 13 25 C17 26 13 29 18 30', '#2b7de9', 2.7)
            + _p('M28 21 C33 21 29 24 33 25 C29 26 33 29 28 30', '#2b7de9', 2.7)
            + _c(23,25,2.8,'url(#copper)','#955c39',1)
            + _p('M17 35 H30', '#0d9488', 2.7)
        ),
        'stop_solve': (
            _p('M16 5 H32 L43 16 V32 L32 43 H16 L5 32 V16Z', '#8c3b38', 2.4, '#f26954')
            + _p('M16 7 H31 L41 17', '#ffb49e', 2.5)
            + _r(16, 16, 16, 16, 3.5, '#fffaf8', '#943d3e', 2.6)
            + _p('M20 20 V28 M28 20 V28', '#e85d4a', 3)
        ),
        'pass_one': (
            _pcb(5,12,38,28, density=3)
            + _p('M10 32 H20 V22 H31', '#133e59', 5.5)
            + _p('M10 32 H20 V22 H31', 'url(#trace)', 3.7)
            + _via(10,32) + _via(31,22)
            + _c(36, 10, 9, '#2b7de9', '#ffffff', 1.9)
            + _p('M36 6 V14 M33.5 7 L36 6', 'white', 2.6)
        ),
        'pass_two': (
            _pcb(5,12,38,28, density=3)
            + _p('M9 33 H16 L24 21 H34', '#164b59', 5.4)
            + _p('M9 33 H16 L24 21 H34', 'url(#trace)', 3.6)
            + _via(9,33) + _via(34,21)
            + _p('M30 26 L35 21 L30 17', '#10a997', 2)
            + _c(36,10,9,'#0d9488','#ffffff',1.9)
            + _p('M32.4 7.5 Q36 5 39 8 Q38 10 32.5 14 H39', 'white',2.3)
        ),
        'component_side': (
            _pcb(5,8,38,32,density=4)
            + _r(16, 15, 16, 18, 3, 'url(#chip)', '#0e2839', 1.9)
            + ''.join(_p(f'M12 {yy} H16 M32 {yy} H36', '#e9f2f7',2.3)
                      for yy in (18,23,28))
            + _p('M20 19 H28', '#23c4de',2)
            + _c(20, 27,1.9,'#35c7b0','#0d9488',.7)
        ),
        'copper_side': (
            _pcb(5,8,38,32,density=4)
            + _p('M12 31 V21 H29 V16 H35', '#174b60',5)
            + _p('M12 31 V21 H29 V16 H35', '#0cc6d1',3.1)
            + _via(12,31) + _via(35,16)
            + _p('M21 25 L28 32 M28 25 L21 32', '#e85d4a',3.3)
        ),
        'schematic': (
            _p('M4 24 H13 L17 16 L22 32 L27 16 L31 24 H44', '#254f75',3.1)
            + _p('M21 10 H27 M24 6 V14 M18 38 H30 M24 34 V42', 'url(#copper)',2.9)
            + _via(6,24) + _via(42,24)
            + _p('M11 8 H16 M32 39 H37', '#0d9488',2.3)
        ),
        'open_solved': (
            _p('M11 5 H29 L38 14 V41 H11 Z', '#24495f',2.4,'url(#ice)')
            + _p('M29 5 V14 H38', '#2b7de9',2.1)
            + _p('M16 19 H30 M16 25 H25 M16 31 H24', 'url(#copper)',2.7)
            + _c(32,33,10,'#16a34a','#fffdf5',2.4)
            + _p('M27 33 L31 37 L38 28','white',3.3)
        ),
        'exit': (
            _r(7,5,25,38,4,'url(#ice)','#24495f',2.7)
            + _p('M17 13 H24 V35 H17', 'url(#copper)',2.8)
            + _c(26,26,1.7,'#cb8452','#9e613f',.8)
            + _p('M24 24 H43 M35 16 L43 24 L35 32', '#2b7de9',4)
        ),
        'fit_board': (
            _p('M17 5 H5 V17 M31 5 H43 V17 M5 31 V43 H17 M43 31 V43 H31',
               '#2b7de9',3.5)
            + _pcb(12,12,24,24,density=3)
            + _p('M22 20 L27 25 L22 30', '#0d9488',2.4)
        ),
    }
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" '
            'viewBox="0 0 48 48" fill="none" stroke-linecap="round" '
            'stroke-linejoin="round">'+_DEFS+designs[key]+'</svg>')


def app_icon_svg() -> str:
    """1024px squircle: blueprint, copper strips, and luminous multi-trace S."""
    strips = []
    for i in range(12):
        y = 278 + i * 44
        strips.append(
            f'<rect x="241" y="{y}" width="542" height="23" rx="11.5" '
            'fill="url(#app-copper)" opacity=".86"/>'
        )
        for x in range(262, 762, 44):
            strips.append(
                f'<circle cx="{x}" cy="{y+11}" r="7.4" '
                'fill="#f5faff" stroke="#c58a68" stroke-width="3"/>'
            )
    grid = ''.join(f'<path d="M{x} 155 V869"/>' for x in range(165,860,88)) + \
           ''.join(f'<path d="M155 {y} H869"/>' for y in range(165,860,88))
    # A continuous conductor, with angular, hexagonal turns (not a font S).
    spine = ('M613 346 L509 265 L387 353 L387 440 L469 513 '
             'L638 598 L638 692 L512 788 L384 689 L384 610')
    inner = ('M618 345 L509 284 L409 361 L409 432 L487 496 '
             'L616 601 L616 677 L513 756 L404 680 L404 620')
    # Copper companions follow the same board contour, not a generic S glyph.
    copper = ('M616 345 L510 282 L406 358 L406 438 L487 517 '
              'L619 600 L619 689 L511 771 L392 684 L392 619')
    nodes = [(509,265),(613,346),(387,440),(469,513),(638,598),
             (638,692),(512,788),(384,689)]
    pins = ''.join(
        f'<circle cx="{x}" cy="{y}" r="12" fill="url(#app-copper)" '
        'stroke="#8b4e2c" stroke-width="4"/>'
        f'<circle cx="{x}" cy="{y}" r="5" fill="#efffff"/>'
        for x,y in nodes
    )
    aux = [
        ('M314 330 H360 V382 H389','teal'),
        ('M238 438 H376','copper'),
        ('M316 522 H396 L433 493','teal'),
        ('M641 358 H732','copper'),
        ('M643 600 H748','teal'),
        ('M642 678 H738 L776 643','copper'),
        ('M514 789 V833','teal'),
        ('M378 716 H306 L266 748','copper'),
        ('M508 265 V233 H581 L604 205','teal'),
    ]
    aux_art = ''.join(
        f'<path d="{d}" fill="none" stroke="{INK if color=="teal" else "#a56945"}" '
        'stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/>'
        f'<path d="{d}" fill="none" stroke="{CYAN if color=="teal" else "url(#app-copper)"}" '
        'stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>'
        for d,color in aux
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024"
width="1024" height="1024">
<defs>
 <linearGradient id="app-ice" x1="0" x2="1" y1="0" y2="1">
  <stop stop-color="#ffffff"/><stop offset=".52" stop-color="#eff8ff"/>
  <stop offset="1" stop-color="#d4eaf7"/>
 </linearGradient>
 <linearGradient id="app-copper" x1="0" x2="0" y1="0" y2="1">
  <stop stop-color="#ffe5bd"/><stop offset=".3" stop-color="#ecad7f"/>
  <stop offset=".65" stop-color="#c87d4b"/><stop offset="1" stop-color="#ebae79"/>
 </linearGradient>
 <linearGradient id="route" x1="0" x2="1" y1="0" y2="1">
  <stop stop-color="#1de8ed"/><stop offset=".25" stop-color="#13b9d6"/>
  <stop offset=".55" stop-color="#266fc9"/><stop offset=".79" stop-color="#1278ba"/>
  <stop offset="1" stop-color="#11bd99"/>
 </linearGradient>
 <linearGradient id="app-edge" x1="0" x2="1" y1="0" y2="1">
  <stop stop-color="#c1ffff"/><stop offset=".5" stop-color="#60bcd8"/>
  <stop offset="1" stop-color="#17869c"/>
 </linearGradient>
 <filter id="bloom" x="-35%" y="-35%" width="170%" height="170%">
  <feGaussianBlur stdDeviation="12"/>
 </filter>
 <clipPath id="panel-clip"><rect x="130" y="133" width="764" height="755" rx="158"/></clipPath>
</defs>
<!-- cyan glass squircle, without a raster square background -->
<rect x="62" y="63" width="900" height="900" rx="210" fill="#36a8c8" opacity=".25"
 filter="url(#bloom)"/>
<rect x="62" y="60" width="900" height="900" rx="209" fill="url(#app-ice)"
 stroke="url(#app-edge)" stroke-width="21"/>
<rect x="82" y="79" width="860" height="862" rx="194" fill="none"
 stroke="#dffaff" stroke-width="11"/>
<rect x="126" y="130" width="772" height="760" rx="162" fill="none"
 stroke="#b2d1e0" stroke-width="2.8"/>
<g clip-path="url(#panel-clip)">
 <g stroke="#c0d9e8" stroke-width="2" opacity=".67" fill="none">{grid}</g>
 <g opacity=".68">{''.join(strips)}</g>
 <g fill="none" stroke="#a0cadd" stroke-width="3" opacity=".8">
  <path d="M140 490 H886 M140 552 H886"/>
 </g>
</g>
<!-- diagnostic trace branches and solder vias -->
<g>{aux_art}</g>
<g fill="#e4fff9" stroke="#108d9c" stroke-width="6">
 <circle cx="314" cy="330" r="10"/><circle cx="238" cy="438" r="10"/>
 <circle cx="316" cy="522" r="10"/><circle cx="732" cy="358" r="10"/>
 <circle cx="748" cy="600" r="10"/><circle cx="776" cy="643" r="10"/>
 <circle cx="514" cy="833" r="10"/><circle cx="266" cy="748" r="10"/>
 <circle cx="604" cy="205" r="10"/>
</g>
<!-- deep layered routing ribbon makes the central S legible as a chip icon -->
<path d="{spine}" fill="none" stroke="#10455b" stroke-width="123"
 stroke-linecap="round" stroke-linejoin="round" opacity=".2" filter="url(#bloom)"/>
<path d="{spine}" fill="none" stroke="#16364f" stroke-width="104"
 stroke-linecap="round" stroke-linejoin="round"/>
<path d="{spine}" fill="none" stroke="url(#route)" stroke-width="90"
 stroke-linecap="round" stroke-linejoin="round"/>
<path d="{spine}" fill="none" stroke="#65f6f1" stroke-width="8"
 stroke-linecap="round" stroke-linejoin="round" opacity=".7"/>
<path d="{inner}" fill="none" stroke="#0f4d70" stroke-width="24"
 stroke-linecap="round" stroke-linejoin="round"/>
<path d="{inner}" fill="none" stroke="#25adf2" stroke-width="12"
 stroke-linecap="round" stroke-linejoin="round"/>
<path d="{copper}" fill="none" stroke="#9b593a" stroke-width="17"
 stroke-linecap="round" stroke-linejoin="round" opacity=".9"/>
<path d="{copper}" fill="none" stroke="url(#app-copper)" stroke-width="12"
 stroke-linecap="round" stroke-linejoin="round"/>
<g>{pins}</g>
<g fill="#edfaff" stroke="#a36b44" stroke-width="5">
 <rect x="429" y="396" width="14" height="35" rx="4"/>
 <rect x="583" y="623" width="14" height="35" rx="4"/>
</g>
</svg>'''
