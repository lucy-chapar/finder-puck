"""Machine-shop files for the aluminium shell: the shell and the window as single-part STEP files in a shop frame,
and an A3 drawing of the shell (views, section, the dimensions that matter, threads, tolerances and finish).

Run with FreeCAD's console after build_case.py (it reads the assembly that build wrote):

    /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd case/shop_drawing.py

Shop frame: origin on the case axis at the back face, +Z up into the shell, +Y towards 12 o'clock.  Writes
case/finder_puck_{shell,window}_shop.step, case/finder_puck_shell_drawing.svg and, when Google Chrome (or $CHROME)
is there, case/finder_puck_shell_drawing.pdf.  Like build_case.py, it only runs when run as shop_drawing.py.
"""

import math
import os
import subprocess
import sys
import textwrap

import FreeCAD
import Part
import TechDraw

try:
    CASE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    CASE = os.path.join(os.getcwd(), "case")
sys.path.insert(0, CASE)
import build_case as bc          # noqa: E402  (parameters only; it does not build when imported)

V = FreeCAD.Vector
OUT = os.path.join(CASE, bc.NAME)
CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
SHIFT = V(-bc.CX, -bc.CY, -bc.Z_BOTTOM)
H = bc.Z_SPLIT - bc.Z_BOTTOM                      # 12.7: shell height
ZB = lambda z: z - bc.Z_BOTTOM                    # case Z to shop Z  # noqa: E731
SCALE = 1.3


def shop(label, doc):
    s = doc.getObjectsByLabel(label)[0].Shape.copy()
    s.translate(SHIFT)
    return s


# --- SVG helpers ------------------------------------------------------------
class View:
    """A view placed on the sheet: (h, v) model coordinates in the view plane, scaled about (cx, cy)."""

    def __init__(self, cx, cy, s=SCALE):
        self.cx, self.cy, self.s = cx, cy, s

    def p(self, h, v):
        return self.cx + self.s * h, self.cy - self.s * v


def polyline(view, pts, cls):
    d = " ".join("%s%.3f %.3f" % ("M" if i == 0 else "L", *view.p(*q)) for i, q in enumerate(pts))
    return '<path class="%s" d="%s"/>' % (cls, d)


def edges_svg(view, shape, to_hv, cls):
    out = []
    if shape is None or shape.isNull():
        return out
    for e in shape.Edges:
        n = 2 if isinstance(e.Curve, Part.Line) else max(8, int(e.Length / 0.3))
        out.append(polyline(view, [to_hv(q) for q in e.discretize(n)], cls))
    return out


def project(view, shape, direction, to_hv, hidden=False):
    r = TechDraw.projectEx(shape, direction)
    out = edges_svg(view, r[0], to_hv, "vis") + edges_svg(view, r[3], to_hv, "vis") + edges_svg(view, r[1], to_hv, "thin")
    if hidden:
        out += edges_svg(view, r[5], to_hv, "hid")
    return out


def text(x, y, s, size=3.0, anchor="start", cls="t"):
    s = s.replace("&", "&amp;").replace("<", "&lt;")
    return '<text class="%s" x="%.2f" y="%.2f" font-size="%.2f" text-anchor="%s">%s</text>' % (cls, x, y, size, anchor, s)


def dim_linear(view, a, b, off, label, vertical=False):
    """A dimension between model points a and b (h, v), its line offset by off (mm on the sheet)."""
    (x0, y0), (x1, y1) = view.p(*a), view.p(*b)
    out = []
    if vertical:
        x = max(x0, x1) + off if off > 0 else min(x0, x1) + off
        out += ['<path class="dim" d="M%.2f %.2f H%.2f M%.2f %.2f H%.2f"/>' % (x0, y0, x + 1.5 * math.copysign(1, off), x1, y1, x + 1.5 * math.copysign(1, off)),
                '<path class="dim" marker-start="url(#a)" marker-end="url(#a)" d="M%.2f %.2f V%.2f"/>' % (x, y0, y1)]
        ym = (y0 + y1) / 2
        out.append('<text class="t" font-size="2.8" text-anchor="middle" transform="translate(%.2f %.2f) rotate(-90)">%s</text>'
                   % (x - 1, ym, label))
    else:
        y = max(y0, y1) + off if off > 0 else min(y0, y1) + off
        out += ['<path class="dim" d="M%.2f %.2f V%.2f M%.2f %.2f V%.2f"/>' % (x0, y0, y + 1.5 * math.copysign(1, off), x1, y1, y + 1.5 * math.copysign(1, off)),
                '<path class="dim" marker-start="url(#a)" marker-end="url(#a)" d="M%.2f %.2f H%.2f"/>' % (x0, y, x1)]
        out.append(text((x0 + x1) / 2, y - 1, label, 2.8, "middle"))
    return out


def balloon(view, at_hv, dx, dy, n):
    """A numbered balloon (see the table) with its leader to a model point."""
    x, y = view.p(*at_hv)
    x1, y1 = x + dx, y + dy
    d = math.hypot(dx, dy)
    return ['<path class="dim" marker-start="url(#d)" d="M%.2f %.2f L%.2f %.2f"/>' % (x, y, x1 - dx / d * 2.4, y1 - dy / d * 2.4),
            '<circle class="dim" cx="%.2f" cy="%.2f" r="2.4"/>' % (x1, y1), text(x1, y1 + 0.95, str(n), 2.6, "middle", "b")]


def polar(a, r):
    return r * math.cos(math.radians(a)), r * math.sin(math.radians(a))


# --- The drawing ------------------------------------------------------------
NOTES = [
    "Material: 6061-T6 aluminium (bar or plate, 80 mm or more across, 14 mm or more thick).",
    "Finish: fine glass bead blast, then sulphuric anodise, black, sealed: MIL-A-8625 Type II class 2, 10-15 um. "
    "Dimensions apply after anodising (it adds about 0.01 mm a surface).",
    "Threads: mask from anodise or chase after. The seal faces (rim, notch floor, both flanks) are anodised like the "
    "rest; no masking.",
    "General tolerance ISO 2768-m (+/-0.1 mm here), angles +/-0.5 deg. Tighter where the table says.",
    "Inside corners take the radius of the tool shown: R1 switch slot, R1.5 bosses and cable slot, R2 scallop. "
    "Smallest tool 2 mm.",
    "Break outside edges 0.1-0.2 mm unless a radius is shown, flanks included. Deburr the inside of the lanyard bend: "
    "a cord runs over it.",
    "No undercuts. Setups: top, back, and two radial side stations at 245 and 270 deg (4th axis or an indexing "
    "fixture). The flanks are one pass each with a 60 deg chamfer mill (about 11 mm of flute) or a ball-end 3D pass.",
    "Engrave the logo after anodising (item 17), so it shows bare metal: 90 deg V-bit along the outline, a contour "
    "not a pocket, tip 0.3 mm deep, from finder_puck_logo_vgroove.svg, centred on the axis, 12 o'clock up seen from "
    "the back.",
    "The 3D model governs every dimension not shown: finder_puck_shell_shop.step, origin on the axis at the back "
    "face, +Y towards 12 o'clock.",
    "Cosmetic: the back and the outside wall are show faces, no clamp marks. Quantity 2; quote 5 as well.",
]


def rows():
    sw = bc.F["power_switch"]["angle"]
    return [
        ("", "Outside diameter", "Ø%.1f" % (2 * bc.R_OUT), "±0.05"),
        ("", "Height, back to rim", "%.1f" % H, "±0.05"),
        (1, "Board bore", "Ø%.1f, rim down to the ledge (%.1f)" % (2 * bc.R_IN, bc.Z_SPLIT + bc.T_BOARD), "±0.05"),
        (2, "Battery bay bore", "Ø%.1f, floor %.1f thick" % (2 * bc.R_BAY, bc.FLOOR), "±0.05"),
        (3, "Ledge (board seat)", "%.1f from back, %.1f wide; flat 0.05" % (ZB(-bc.T_BOARD), bc.LEDGE_W), "±0.05"),
        (4, "Bosses, 4x 45/135/225/315°", "Ø%.1f on r%.1f, top flush with ledge, R%.1f to wall" % (2 * bc.SHELL_BOSS_R, bc.BOLTS["r"], bc.BOSS_FILLET), "±0.05"),
        (5, "Threads, 4x", "M2.5x0.45-6H ↧%.0f, drill Ø%.2f ↧%.0f, 0.3 c'sink" % (bc.TAP_DEPTH, bc.TAP_DRILL, bc.DRILL_DEPTH), "blind"),
        (6, "Antenna notch", "%.0f° to %.0f° at the floor, wall cut to the floor" % bc.WINDOW, "±0.5°"),
        (7, "Notch flanks, 2x", "planes at %.0f° to the floor (60° chamfer mill)" % bc.FLANK, "±0.05"),
        (8, "Peg holes, 2x", "Ø%.1f ↧%.1f at %.0f° and %.0f°, r%.1f" % (bc.PEG_D + 0.1, bc.PEG_L + 0.2, bc.WINDOW_FEET[0], bc.WINDOW_FEET[1], bc.PEG_R), "±0.05"),
        (9, "Motor pocket", "Ø%.1f ↧0.6 in the floor" % (bc.F["motor"]["dia"] + 0.6), "±0.1"),
        (10, "Cable slot, %d°" % bc.BATT_NOTCH[0], "6.0 wide, bay floor to ledge, R1.5 corners", "±0.1"),
        (11, "Switch slot, %d°" % sw, "%.1f wide, R%.0f corners, R%.0f finger scallop" % (bc.SWITCH_W, bc.SWITCH_RC, bc.SCALLOP_RC), "±0.05"),
        (12, "Plug pin hole", "Ø%.1f blind, radial, in the scallop" % bc.PLUG_PIN_D, "±0.05"),
        (13, "Lanyard back hole", "Ø%.1f at r%.1f, 6 o'clock, blind" % (bc.LANYARD_D, bc.LANYARD_R), "±0.1"),
        (14, "Lanyard side hole", "Ø%.1f radial at 270°, %.1f from back" % (bc.LANYARD_D, ZB(bc.LANYARD_Z)), "±0.1"),
        (15, "Lanyard mouths", "%.1f x 45° c'sink; deburr the bend inside" % bc.LANYARD_SINK, ""),
        (16, "Back edge", "R%.0f" % bc.BOTTOM_R, "±0.2"),
        (17, "Logo (after anodise)", "90° V-groove along outline, 0.3 deep, %.0f wide" % bc.LOGO_W, "±0.05"),
    ]


def table(x0, y0):
    w = (7, 40, 70, 13)
    out = []
    for i, r in enumerate([("#", "Feature", "Size", "Tol.")] + rows()):
        y = y0 + i * 4.6
        cls = "tb" if i == 0 else "t"
        x = x0
        for c, wc in zip(r, w):
            out.append(text(x + 1, y + 3.3, str(c), 2.45, cls=cls))
            x += wc
        out.append('<path class="thin" d="M%.1f %.1f h%.1f"/>' % (x0, y + 4.6, sum(w)))
    out.append('<rect class="thin" x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="none"/>' % (x0, y0, sum(w), 4.6 * (len(rows()) + 1)))
    return out


def drawing(shell):
    svg = []
    r = bc.R_OUT * SCALE
    # Top view (looking down into the shell).
    top = View(64, 72)
    svg += project(top, shell, V(0, 0, 1), lambda q: (q.x, q.y))
    svg += dim_linear(top, (-bc.R_OUT, 0), (bc.R_OUT, 0), r + 6, "Ø%.1f" % (2 * bc.R_OUT))
    svg.append(text(64, 72 + r + 15, "TOP (into the shell)", 3.5, "middle", "tb"))
    for a, rr, dx, dy, n in ((45, bc.BOLTS["r"] + bc.SHELL_BOSS_R, 7, -7, 4), (135, bc.BOLTS["r"], 9, 6, 5),
                             (30, bc.R_IN + 0.9, 9, -3, 6), (bc.WINDOW[0], bc.R_IN + 0.9, 9, 3, 7),
                             (bc.WINDOW_FEET[1], bc.PEG_R, 6, -9, 8), (bc.BATT_NOTCH[0], bc.R_BAY - 1, -7, -7, 10),
                             (bc.F["power_switch"]["angle"], bc.R_OUT, -7, 7, 11)):
        svg += balloon(top, polar(a, rr), dx, dy, n)
    mx, my = bc.pt(*bc.MOTOR_POCKET)
    svg += balloon(top, (mx - bc.CX - 3, my - bc.CY - 3), -8, 5, 9)
    for a in (0, 90, 180, 270):
        x, y = top.p(*polar(a, bc.R_OUT + 3.5))
        svg.append(text(x, y + 1, {0: "3", 90: "12", 180: "9", 270: "6"}[a], 2.6, "middle", "c"))
    # Section line A-A through the axis, 12 to 6 o'clock.
    x0, y0 = top.p(0, bc.R_OUT + 8)
    x1, y1 = top.p(0, -bc.R_OUT - 1)
    svg.append('<path class="cl" d="M%.2f %.2f V%.2f"/>' % (x0, y0, y1))
    svg += [text(x0 + 1.5, y0 + 2, "A", 3.5, cls="tb"), text(x1 + 1.5, y1 + 1, "A", 3.5, cls="tb")]

    # Back view.
    back = View(184, 72)
    svg += project(back, shell, V(0, 0, -1), lambda q: (q.x, q.y))   # already mirrored
    svg.append(text(184, 72 + r + 15, "BACK (logo, lanyard)", 3.5, "middle", "tb"))
    svg += dim_linear(back, (-bc.LOGO_W / 2, 9), (bc.LOGO_W / 2, 9), -9, "%.0f" % bc.LOGO_W)
    svg += balloon(back, (bc.LOGO_W / 2 - 1.5, 2.5), 14, -6, 17)
    svg += balloon(back, (0, -bc.LANYARD_R), 9, -6, 13)
    svg += balloon(back, (bc.R_OUT * 0.7071, -bc.R_OUT * 0.7071), 7, 7, 16)
    for a in (0, 90, 180, 270):
        x, y = back.p(*polar(a, bc.R_OUT + 3.5))
        svg.append(text(x, y + 1, {0: "9", 90: "12", 180: "3", 270: "6"}[a], 2.6, "middle", "c"))

    # Section A-A: the half at X < 0, seen from +X (12 o'clock on the right).
    sec = View(64, 196)
    try:
        half = shell.common(Part.makeBox(100, 100, 40, V(-100, -50, -5)))
        if half.isNull() or half.Volume < 1:
            raise Part.OCCError("empty")
        svg += project(sec, half, V(1, 0, 0), lambda q: (-q.y, q.x))
    except Part.OCCError:
        print("CHECK: the shell is not a valid solid, so section A-A shows only the cut face")
    for w in shell.slice(V(1, 0, 0), 0.0):
        pts = [(q.y, q.z) for q in w.discretize(200)]
        d = " ".join("%s%.3f %.3f" % ("M" if i == 0 else "L", *sec.p(*q)) for i, q in enumerate(pts)) + " Z"
        svg.append('<path class="sec" d="%s"/>' % d)
    svg.append(text(64, 196 + 30, "SECTION A-A (through the axis; 6 o'clock left)", 3.5, "middle", "tb"))
    svg += dim_linear(sec, (-bc.R_OUT, 0), (-bc.R_OUT, H), -5, "%.1f" % H, vertical=True)
    svg += dim_linear(sec, (bc.R_OUT, 0), (bc.R_OUT, ZB(bc.Z_FLOOR)), 13, "%.1f" % bc.FLOOR, vertical=True)
    svg += dim_linear(sec, (bc.R_OUT, ZB(-bc.T_BOARD)), (bc.R_OUT, H), 5, "%.1f" % (bc.Z_SPLIT + bc.T_BOARD), vertical=True)
    svg += dim_linear(sec, (-bc.R_IN, H), (bc.R_IN, H), -8, "Ø%.1f" % (2 * bc.R_IN))
    svg += dim_linear(sec, (-bc.R_BAY, 0), (bc.R_BAY, 0), 8, "Ø%.1f" % (2 * bc.R_BAY))
    svg += balloon(sec, (-bc.R_IN, ZB(0.5)), 10, -12, 1)
    svg += balloon(sec, (bc.R_BAY, ZB(-4)), -10, 0, 2)
    svg += balloon(sec, (bc.R_IN - 1, ZB(-bc.T_BOARD)), -6, -10, 3)
    svg += balloon(sec, (-bc.R_OUT, ZB(bc.LANYARD_Z) - 1.5), -2, 12, 15)

    # Side view from 6 o'clock (the two side stations).
    side = View(184, 196)
    svg += project(side, shell, V(0, -1, 0), lambda q: (q.y, -q.x))
    svg.append(text(184, 196 + 30, "SIDE from 6 o'clock (stations 270° and 245°)", 3.5, "middle", "tb"))
    svg += balloon(side, (bc.LANYARD_D / 2, ZB(bc.LANYARD_Z)), 9, 9, 14)
    sx = bc.R_OUT * math.cos(math.radians(bc.F["power_switch"]["angle"]))
    svg += balloon(side, (sx, ZB(bc.SWITCH_Z1)), -6, -10, 11)
    svg += balloon(side, (sx, ZB(bc.SW_PIN_Z)), -8, 10, 12)

    # Notes, table, title block.
    xn = 262
    svg.append(text(xn, 16, "NOTES", 3.5, cls="tb"))
    y, k = 21.5, 0
    for n in NOTES:
        for j, line in enumerate(textwrap.wrap(n, 100)):
            k += j == 0
            svg.append(text(xn, y, ("%d. " % k if j == 0 else "    ") + line, 2.4))
            y += 3.6
    svg += table(xn, y + 2)
    tb = [("Part", "Finder Puck shell"), ("Material", "6061-T6, black anodised"), ("Qty", "2"),
          ("Scale", "%.1f:1 on A3" % SCALE), ("Units", "mm, all views at the same scale"),
          ("Source", "case/shop_drawing.py (do not edit by hand)")]
    for i, (k2, v) in enumerate(tb):
        svg += [text(xn + 1, 262 + i * 4.4, k2, 2.6, cls="tb"), text(xn + 22, 262 + i * 4.4, v, 2.7)]
    svg.append('<rect class="thin" x="%.1f" y="258" width="130" height="28" fill="none"/>' % (xn - 1))
    return svg


def write_gasket_dxf(path):
    """The flat gaskets as closed outlines in a DXF (R12) for a converter's knife or laser cutter, one layer per
    foam thickness: lid and crystal gaskets, the door frame (flat), the seam seal ring and the window strip."""
    def flat(shape):
        z = shape.BoundBox.ZMax
        f = [f for f in shape.Faces if abs(f.BoundBox.ZMin - z) < 1e-6 and abs(f.BoundBox.ZMax - z) < 1e-6][0]
        return [[(q.x - bc.CX, q.y - bc.CY) for q in w.discretize(Deflection=0.01)] for w in f.Wires]

    def rect(x, y, w, h):
        return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]

    w, h = bc.USB_W + 2 * bc.DOOR_LAND_W, (bc.USB_Z1 - bc.USB_Z0) + 2 * bc.DOOR_LAND_W
    hw, hh = bc.USB_W + 0.2, (bc.USB_Z1 - bc.USB_Z0) + 0.2
    strip = (math.radians(bc.WINDOW[1] - bc.WINDOW[0]) * (bc.R_IN + bc.R_OUT) / 2
             + 2 * (bc.Z_SPLIT - bc.Z_FLOOR) / math.sin(math.radians(bc.FLANK)))      # as build_case prints it
    parts = [
        ("FOAM_0.3", "lid gasket 0.3", flat(bc.make_lid_gasket()), (0, 0)),
        ("FOAM_0.3", "crystal gasket 0.3", flat(bc.make_crystal_gasket()), (55, 0)),
        ("FOAM_0.5", "door gasket 0.5", [rect(-w / 2, -h / 2, w, h), rect(-hw / 2, -hh / 2, hw, hh)], (92, 0)),
        ("FOAM_1.0", "seam seal 1.0", flat(bc.make_seal()), (0, -85)),
        ("FOAM_1.0", "window gasket 1.0", [rect(0, 0, round(strip), bc.R_OUT - bc.R_IN - 2 * bc.SEAL_INSET)], (45, -85)),
    ]
    out = ["0", "SECTION", "2", "HEADER", "9", "$INSUNITS", "70", "4", "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES"]
    for layer, name, wires, (ox, oy) in parts:
        for pts in wires:
            out += ["0", "POLYLINE", "8", layer, "66", "1", "70", "1"]
            for x, y in pts:
                out += ["0", "VERTEX", "8", layer, "10", "%.4f" % (x + ox), "20", "%.4f" % (y + oy), "30", "0"]
            out += ["0", "SEQEND", "8", layer]
        ys = [y for pts in wires for _, y in pts]
        xs = [x for pts in wires for x, _ in pts]
        out += ["0", "TEXT", "8", "LABELS", "10", "%.2f" % (ox + min(xs)), "20", "%.2f" % (oy + min(ys) - 5), "30", "0",
                "40", "2.5", "1", name]
    out += ["0", "ENDSEC", "0", "EOF"]
    with open(path, "w") as f:
        f.write("\n".join(out) + "\n")


CSS = """
.vis{fill:none;stroke:#000;stroke-width:0.35;stroke-linecap:round;stroke-linejoin:round}
.thin{fill:none;stroke:#000;stroke-width:0.15}
.hid{fill:none;stroke:#777;stroke-width:0.15;stroke-dasharray:1 0.6}
.sec{fill:url(#h);stroke:#000;stroke-width:0.4;fill-rule:evenodd}
.dim{fill:none;stroke:#1a4fb4;stroke-width:0.18}
.cl{fill:none;stroke:#b4321a;stroke-width:0.25;stroke-dasharray:6 1 1 1}
.t,.tb,.c,.b{font-family:Helvetica,Arial,sans-serif;fill:#000}
.tb,.b{font-weight:bold}
circle.dim{fill:#fff}
.b{fill:#1a4fb4}
.c{fill:#777}
"""


def main():
    doc = FreeCAD.openDocument(OUT + "_case.FCStd")
    shell, window = shop("Shell", doc), shop("Window", doc)
    for name, s in (("shell", shell), ("window", window)):
        s.exportStep(OUT + "_%s_shop.step" % name)
        print("wrote %s_%s_shop.step (%.0f mm^3, %s)" % (bc.NAME, name, s.Volume, "valid" if s.isValid() else "CHECK: not a valid solid"))
    write_gasket_dxf(OUT + "_gaskets.dxf")
    print("wrote %s_gaskets.dxf" % bc.NAME)
    body = "\n".join(drawing(shell))
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="420mm" height="297mm" viewBox="0 0 420 297">'
           '<style>%s</style><defs>'
           '<marker id="a" viewBox="0 0 6 6" refX="3" refY="3" markerWidth="5" markerHeight="5" orient="auto-start-reverse">'
           '<path d="M0 0 L6 3 L0 6 z" fill="#1a4fb4"/></marker>'
           '<marker id="d" viewBox="0 0 6 6" refX="3" refY="3" markerWidth="3" markerHeight="3"><circle cx="3" cy="3" r="2.5" fill="#1a4fb4"/></marker>'
           '<pattern id="h" width="1.2" height="1.2" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
           '<path d="M0 0 V1.2" stroke="#000" stroke-width="0.15"/></pattern></defs>'
           '<rect x="0" y="0" width="420" height="297" fill="#fff"/>'
           '<rect class="thin" x="6" y="6" width="408" height="285" fill="none"/>%s</svg>') % (CSS, body)
    with open(OUT + "_shell_drawing.svg", "w", encoding="utf-8") as f:
        f.write(svg)
    print("wrote %s_shell_drawing.svg" % bc.NAME)
    if os.path.exists(CHROME):
        html = OUT + "_shell_drawing.html"
        with open(html, "w", encoding="utf-8") as f:
            f.write('<!doctype html><html><head><meta charset="utf-8"><style>@page{size:420mm 297mm;margin:0}'
                    'body{margin:0}svg{display:block}</style></head><body>%s</body></html>' % svg)
        pdf = OUT + "_shell_drawing.pdf"
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
                        "--print-to-pdf=" + pdf, "file://" + html], capture_output=True)
        os.remove(html)
        print("wrote %s_shell_drawing.pdf" % bc.NAME if os.path.exists(pdf) else "CHECK: Chrome did not write the PDF")


if os.path.basename(sys.argv[-1] if sys.argv else "") == "shop_drawing.py":
    main()
