"""
Printed case for the finder puck, built from the board's feature file.

Five printed parts clamp together with four M2.5 screws that pass through the PCB:

  SHELL  (bottom, black)        battery bay, motor pocket, flex antenna on the wall, heat-set inserts,
                                lanyard tunnel, USB-C / switch / lead notches, debossed
                                radar dial and name on the underside
  PLATE  (top, black)           bolt bosses with counterbored heads, covered sky window over
                                the GPS patch, button bore, charge-LED pinhole, orange index
                                dot at 12 o'clock, pocket for the bezel flange
  RING   (black)                a short cup standing on the board: the panel's ledge.  Open
                                at 6 o'clock for the panel chin and FPC, low over the ESP32
  BEZEL  (translucent)          sits on the ring: crystal seat, the visible lip, the flange
                                the plate clamps, and four light pipes down to the LEDs
  CAP    (orange)               the single button, sealed by an O-ring in a sleeve under the skin
  USB PLUG, SWITCH PLUG (TPU)   tethered covers that close the USB-C and switch openings

The ring and bezel used to be one part, but a panel cannot be fitted into a cup that has a
ledge below it and a lip above it, so the stack is now: ring, panel, gasket, crystal, bezel.

Sealed to IP55 (dust protected, water jets): a closed-cell foam seal compressed between the shell's
rim and the plate's skirt, nylon washers under the bolt heads, an O-ring on the button cap, the two
TPU plugs, and the crystal and bezel bonded with UV resin.  Every path in ends at one of those
(see "Sealing (IP55)" in the README).

Modelled hardware (not printed): four M2.5 x 12 socket caps, their nylon washers, four inserts, the
orange index stub, the panel, crystal, battery, motor, the flex antenna, the seam seal and the
button's O-ring (both drawn compressed).  Proxies (not in the board model
either) for the mated battery plug, the three cables through the board notch, the FPC fold, the
USB plug's overmold and the GPS module at its tolerance limits.  Every printed part is checked
for interference against all of these, and every printed-vs-other pair closer than REPORT_GAP is
listed with its nearest point.

Run with FreeCAD's console after regenerating the board:

    /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd case/build_case.py

Coordinates: X = board x, Y = -board y (KiCad's Y points down), Z = 0 at the PCB top.
Angles are degrees, 0 at 3 o'clock, counter-clockwise on the face (90 = 12 o'clock).
"""

import glob
import json
import math
import os
import sys

import FreeCAD
import Import
import Mesh
import MeshPart
import Part

V = FreeCAD.Vector

try:
    CASE = os.path.dirname(os.path.abspath(__file__))
except NameError:   # freecadcmd may not set __file__
    CASE = os.path.join(os.getcwd(), "case")
PUCK = os.path.dirname(CASE)
MECH = os.path.join(PUCK, "mech")
NAME = "finder_puck"

F = json.load(open(os.path.join(MECH, NAME + "_features.json")))
BX, BY = F["board"]["center"]
R_BOARD = F["board"]["radius"]
T_BOARD = F["board"]["thickness"]
CX, CY = BX, -BY
PANEL = F["panel"]
BOLTS = F["bolts"]
LEDS = F["leds"]


def pt(x, y):
    """Board point (mm, Y down) to case XY."""
    return x, -y


def at(angle, r):
    a = math.radians(angle)
    return CX + r * math.cos(a), CY + r * math.sin(a)


def fp_dir(ref, lx, ly):
    """A footprint-local vector (KiCad: Y down, rotation counter-clockwise on screen) as a case-XY vector."""
    th = math.radians(F["parts"][ref]["rot"])
    bx = lx * math.cos(th) + ly * math.sin(th)
    by = -lx * math.sin(th) + ly * math.cos(th)
    return bx, -by


# --- Parameters (mm) --------------------------------------------------------
GAP = 0.4                        # board edge to wall
WALL = 1.8                       # leaves a 0.8 mm plate skirt over the lap lip
R_IN = R_BOARD + GAP             # 36.4
R_OUT = R_IN + WALL              # 38.2 -> 76.4 mm across
FLOOR = 1.8                      # thick enough for the 0.4 mm deboss and the 0.6 mm pockets
BAY = 6.3                        # 5.3 mm cell on 0.5 mm foam, 0.5 mm air above it
Z_FLOOR = -T_BOARD - BAY         # -7.9
Z_BOTTOM = Z_FLOOR - FLOOR       # -9.7
Z_SPLIT = 3.0                    # parting line
LEDGE_W = 2.0                    # board rests on this rim; its underside is a 45 degree chamfer
# Shell-to-plate joint.  The lap lip stands inboard of the wall (its 45 degree underside overhangs the
# inside) so the plate skirt and the seal under it get 1.5 mm of the wall's top.
R_LAP0, R_LAP1 = 35.8, 36.45     # lap lip, 0.3 mm outside the plate bosses (r 35.5)
LIP_T, LIP_H, LAP_GAP = R_LAP1 - R_LAP0, 1.5, 0.25   # 0.65 thick, 1.5 tall, 0.25 radial play to the skirt
R_SKIRT_IN = R_LAP1 + LAP_GAP    # 36.7: plate skirt 1.5 wide over the seal
SEAL_T, SEAL_INSET = 1.0, 0.05   # closed-cell foam seal on the shell rim, 1.0 mm thick ...
PLATE_GAP = 0.6                  # ... squeezed to the rim gap (40 %): the bosses are still the datum, not the rim
Z_FACE = 8.0
SKIN = 1.6
Z_SKIN = Z_FACE - SKIN           # 6.4
# Bolts: M2.5 x 12 socket caps (anodised aluminium, head 4.5 x 2.5) through the PCB into inserts.
BOSS_R = BOLTS["boss_r"]         # 3.75
BOLT_CLEAR = 3.0
HEAD_D, HEAD_H, HEAD_PROUD = 4.5, 2.5, 0.2
BOLT_D, BOLT_L = 2.5, 12.0
SOCKET_AF, SOCKET_DEPTH = 2.0, 1.2
CBORE_D = 5.2
WASHER_D, WASHER_ID, WASHER_T = 5.0, 2.7, 0.5   # DIN 433 M2.5 nylon washer under each head: seals the bolt bore
INSERT_D, INSERT_DEPTH = 4.2, 6.4   # hole for a Ruthex RX-M2.5x5.7, includes 0.2 mm FDM shrink
INSERT_SINK_D, INSERT_SINK = 4.6, 0.3    # room for the melt the insert pushes up
INSERT_OD, INSERT_L = 3.5, 5.7
# Display stack.
LEDGE_Z = PANEL["ledge_z"]       # panel underside, 4.0
PANEL_T = PANEL["thickness"]     # 1.5
GASKET = 0.2                     # a 0.3 mm foam gasket, modelled compressed so the lip preloads it
Z_PANEL_TOP = LEDGE_Z + PANEL_T  # 5.5
Z_CRYSTAL = Z_PANEL_TOP + GASKET # 5.7
CRYSTAL_D, CRYSTAL_T = PANEL["crystal_dia"], PANEL["crystal_thickness"]   # 37.5 x 1.0
Z_CRYSTAL_TOP = Z_CRYSTAL + CRYSTAL_T   # 6.7
WINDOW_D = min(PANEL["window_dia"], PANEL["glass_dia"] - 0.4)   # 34.8: the lip overlaps the glass by 0.2, hiding its edge
R_WALL0, R_WALL1 = F["ring_wall"]["r0"], F["ring_wall"]["r1"]   # 17.9, 18.6: footprint keep-out on the board
WALL_GAPS = F["ring_wall"]["gaps"]
PANEL_CLEAR = 0.25               # ring bore radius = R_WALL0 + this (FDM sliding fit)
RING_FOOT_Z = 0.25               # on a 0.5 mm foam ring, modelled half compressed: the stack is preloaded
R_LEDGE0 = 17.3                  # panel ledge, 0.5 mm under the glass edge
Z_WALL_STEP = 3.6                # above the tallest parts the ring wall thickens outward ...
R_WALL1_TOP = R_WALL1 + 0.3      # ... to this radius (19.3), the crystal's and bezel's seat
R_BEZEL_IN = CRYSTAL_D / 2 + 0.25          # 19.0, crystal seat
R_SKIRT0 = R_WALL1_TOP + 0.25              # bezel skirt around the ring top, 0.25 mm radial
R_BEZEL1 = R_SKIRT0 + 0.85                 # 20.4
Z_SKIRT0 = 4.6
GPS_CLEAR_ARC = (64, 116)        # the GPS module (edge at r 19.25, 6.35 tall) reaches under the ring top and bezel here
R_WALL_GPS = 18.6                # ring outer radius over that arc: a 0.45 mm (one perimeter) wall, 0.6 mm from a module at
                                 # its 15.6 mm maximum (SAM-M10Q data sheet UBX-22013293 table 19: A and G 15.4-15.6 over the
                                 # whole height, F 5.8-6.8; u-blox's STEP draws the patch 0.5 mm narrower, the drawing does not)
R_BEZEL_GPS = R_BEZEL_IN - 0.3   # 18.7: the bezel's GPS cut starts here, 0.5 mm from that module edge (r 19.2)
R_LIP1 = 21.7                    # flared lip: the visible translucent dial ring
LIP_PROUD = 0.0                  # lip top above the face: 1.5-2.0 makes the beacon visible from the side (see README)
R_OPENING = 22.0                 # plate opening (0.3 mm reveal around the lip)
R_FLANGE1 = 26.0                 # bezel flange under the plate skin
Z_FLANGE0, Z_FLANGE1 = Z_SKIN, Z_SKIN + 0.8
GPS_FLANGE_GAP = (60, 120)       # over the GPS module the flange is only 0.4 mm thick
PIPE_D, PIPE_Z0 = 3.0, 1.2       # light pipes from 0.3 mm above the LEDs up into the flange
# Openings.
GPS_WINDOW = "skin"              # "skin" (0.8 mm cover over the patch) or "open" (hole to the sky)
GPS_COVER = 0.8
GPS_WIN = (27.25, 0.4, 44.75, 15.2)          # board coords of the thinned area, out to the wall (module top 6.35)
GPS_WIN_R = 2.0                  # keeps the window inside the plate wall; 1 mm from the patch corner to the step
INDEX_R, INDEX_D, INDEX_DEPTH = 34.7, 1.8, GPS_COVER   # 12 o'clock mark: a glued 1.75 mm orange filament stub, through the cover
USB_W, USB_Z0, USB_Z1 = 13.5, -2.0, 5.5      # 12.35 x 6.5 plug overmold, centred on the receptacle axis (Z 1.65-1.78)
SWITCH_W, SWITCH_Z0, SWITCH_Z1 = 7.0, -0.5, 1.8   # knob at Z 0.45-1.25: the slot stays in the shell, under the seal
SCALLOP_W, SCALLOP_D = 10.0, 1.0            # finger scallop outside the switch slot: the knob sits 0.7 mm in
SCALLOP_Z0, SCALLOP_Z1 = -4.0, 2.6          # below the rim, so the seal runs past it unbroken
# TPU plugs (85A-95A) for the two openings: a body pressed into the opening (PLUG_SQUEEZE oversize per side),
# a flange on the outside, and a strap to a pin glued into a blind hole in the shell.
PLUG_SQUEEZE = 0.1
PLUG_FLANGE_T, PLUG_FLANGE_W = 0.7, 1.5      # flange thickness, and its overlap beyond the opening
PLUG_STRAP_W, PLUG_STRAP_T = 3.0, 0.6
PLUG_PIN_D, PLUG_PIN_L = 1.6, 1.0
USB_PLUG_IN = 36.3                           # body's inner face, 0.45 mm from the receptacle mouth (r 35.84)
USB_PIN_Z = -6.4
SW_PLUG_IN = 36.6                            # body's inner face, 0.14 mm from the knob (r 36.46)
SW_PIN_Z = -2.9
BATT_NOTCH = F["notches"][0]                 # (angle, width, depth): the board is notched; the wall gets a shallow groove
LANYARD_R, LANYARD_BORE, LANYARD_Z = 35.3, 2.8, -5.6   # 0.6 mm roof under the block top
LANYARD_BLOCK = (32.5, 244, 296)             # inner radius, start, end angle
LANYARD_MOUTH = 0.5                          # fillet on the two bore mouths (the bore leaves the wall at 16 degrees)
MOTOR_POCKET = F["motor"]["pocket"]
# 915 MHz adhesive flex antenna (48 x 7 mm class) stuck to the inside of the wall, just outside
# the board's edge: perpendicular to the ground plane instead of lying under it.
FLEX_ARC, FLEX_Z, FLEX_T = (15, 90), (-7.2, -0.2), 0.2
BUTTON = F["button"]
CAP_D, CAP_BORE, CAP_PROUD, CAP_FLANGE_D = 10.0, 10.6, 1.5, 12.4
CAP_SOCKET, CAP_SOCKET_DEPTH = 3.7, 1.0     # pocket for the PTS645 stem
# The button bore continues down a sleeve under the skin, and a 9 x 1 mm silicone O-ring in a groove on the
# cap seals against it (gland depth 0.8: 20 % squeeze).  The cap's flange stays captive under the sleeve.
SLEEVE_R, SLEEVE_Z0, SLEEVE_LEAD = 5.9, 5.2, 0.4   # outer radius (0.4 mm clear of the bezel lip), bottom, lead-in
ORING_GROOVE = (4.5, 6.0, 7.3)               # groove bottom radius, Z from, Z to (upper wall 45 degrees)
ORING_CS = 1.0
PINHOLE_D = 1.2
# Underside deboss.
DEBOSS_ART, DEBOSS_TEXT = 0.3, 0.4
TEXT_H = 3.5                                 # cap height; DejaVu Bold gives a 0.6 mm stroke
# Proxies for what the board model does not contain.
PH_PLUG, PH_MOUTH, PH_PLUG_OUT = (6.85, 5.8, 4.5), 4.4, 2.0   # PHR-2 housing (length, width, height); J2's mouth is 4.4 mm
                                             # along its +Y; the mated housing stands this far out of the mouth
NOTCH_CABLES = (3, 1.3, 1.6, -5.0, 3.5)      # through the board notch: count, dia, spacing, z0, z1 (2 x 28 AWG + the 1.37 pigtail)
USB_PLUG = (12.35, 6.5, 1.75, 15.0)          # plug overmold: width, height, axis Z, length out from the receptacle mouth
GPS_ENVELOPE = ((15.6, 15.6, 0.0, 6.8), (15.6, 16.0, 1.0, 2.1))   # (board X, board Y, z0, z1): the module at the data
                                 # sheet's limits (A, G and F max), plus the de-paneling tabs (L up to 0.3 mm per side along the
                                 # pin-1 row, radial here, at the corners of the PCB layer)
REPORT_GAP = 0.3                             # list every printed-vs-other pair closer than this
# Designed overlaps: the TPU plug bodies are PLUG_SQUEEZE oversize in their openings (and across the seal's
# ends).  These are listed as "squeeze" lines and are not interferences; anything else that overlaps is.
SQUEEZE = {frozenset(p) for p in (("UsbPlug", "Shell"), ("UsbPlug", "Plate"), ("UsbPlug", "Seal"),
                                  ("SwitchPlug", "Shell"))}
EXCLUSIVE = {frozenset(("UsbPlug", "ProxyUSB"))}     # the cover is off whenever a cable is in


def font_file():
    """The guide's font, vendored under manual/; FreeCAD's own DejaVu as a fallback."""
    mine = os.path.join(PUCK, "manual", "assets", "fonts", "DejaVuSans-Bold.ttf")
    if os.path.exists(mine):
        return mine
    res = os.path.dirname(FreeCAD.getResourceDir().rstrip("/"))      # .../Resources
    hits = glob.glob(os.path.join(res, "lib", "python3*", "site-packages", "matplotlib", "mpl-data", "fonts", "ttf",
                                  "DejaVuSans-Bold.ttf"))
    return hits[0] if hits else os.path.join(res, "fonts", "DejaVuSans.ttf")


# --- Solid helpers ---------------------------------------------------------

def cyl(r, z0, z1, x=CX, y=CY):
    return Part.makeCylinder(r, z1 - z0, V(x, y, z0))


def annulus(r0, r1, z0, z1, x=CX, y=CY):
    return cyl(r1, z0, z1, x, y).cut(cyl(r0, z0 - 1, z1 + 1, x, y))


def sector(r0, r1, a0, a1, z0, z1, steps=None):
    """Annular sector between angles a0 < a1 (degrees)."""
    if a1 <= a0:
        a1 += 360
    n = steps or max(3, int((a1 - a0) / 5) + 1)
    pts = [V(*at(a0 + (a1 - a0) * k / n, r1), z0) for k in range(n + 1)]
    pts += [V(*at(a0 + (a1 - a0) * k / n, r0), z0) for k in range(n, -1, -1)]
    pts.append(pts[0])
    face = Part.Face(Part.makePolygon(pts))
    return face.extrude(V(0, 0, z1 - z0))


def revolved(profile):
    """Solid of revolution about the case axis from an (r, z) polygon."""
    pts = [V(CX + r, CY, z) for r, z in profile]
    pts.append(pts[0])
    face = Part.Face(Part.makePolygon(pts))
    return face.revolve(V(CX, CY, 0), V(0, 0, 1), 360)


def radial_box(angle, r0, r1, width, z0, z1):
    b = Part.makeBox(r1 - r0, width, z1 - z0, V(r0, -width / 2, z0))
    b.rotate(V(0, 0, 0), V(0, 0, 1), angle)
    b.translate(V(CX, CY, 0))
    return b


def local_box(angle, x0, x1, y0, y1, z0, z1):
    """Box in the frame of a radial direction: x outward along angle, y counter-clockwise across it."""
    b = Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))
    b.rotate(V(0, 0, 0), V(0, 0, 1), angle)
    b.translate(V(CX, CY, 0))
    return b


def radial_pin(angle, r0, r1, dia, z):
    """Cylinder along the radial direction at angle, from r0 out to r1, centred at height z."""
    c = Part.makeCylinder(dia / 2, r1 - r0, V(r0, 0, z), V(1, 0, 0))
    c.rotate(V(0, 0, 0), V(0, 0, 1), angle)
    c.translate(V(CX, CY, 0))
    return c


def rounded_box(x0, y0, x1, y1, z0, z1, r):
    """Rectangle (case XY) extruded between z0 and z1, vertical corners rounded by r."""
    w, h = x1 - x0, y1 - y0
    box = Part.makeBox(w, h, z1 - z0, V(x0, y0, z0))
    r = min(r, w / 2 - 0.01, h / 2 - 0.01)
    if r > 0.05:
        try:
            box = box.makeFillet(r, [e for e in box.Edges if abs(e.tangentAt(e.FirstParameter).z) > 0.99])
        except Exception:
            pass
    return box


def board_rect(bx0, by0, bx1, by1, z0, z1, r=0.0):
    """Rectangle given in board coordinates (Y down)."""
    x0, y1 = pt(bx0, by0)
    x1, y0 = pt(bx1, by1)
    return rounded_box(x0, y0, x1, y1, z0, z1, r)


def hex_prism(af, z0, z1, x, y):
    r = af / math.sqrt(3)
    pts = [V(x + r * math.cos(math.radians(60 * k + 30)), y + r * math.sin(math.radians(60 * k + 30)), z0) for k in range(6)]
    pts.append(pts[0])
    return Part.Face(Part.makePolygon(pts)).extrude(V(0, 0, z1 - z0))


def text_solid(text, height, depth, x, y, font):
    """Debossed text as a solid (letters extruded by depth, z from 0), centred on (x, y) in the XY plane."""
    glyphs = Part.makeWireString(text, font, height, 0.0)
    faces = []
    for wires in glyphs:
        if not wires:                       # a space
            continue
        wires = sorted(wires, key=lambda w: -Part.Face(w).Area)
        try:
            faces.append(Part.Face(wires))
        except Exception:
            faces.append(Part.Face(wires[0]))
    shape = Part.makeCompound(faces)
    bb = shape.BoundBox
    shape.translate(V(x - (bb.XMin + bb.XMax) / 2, y - (bb.YMin + bb.YMax) / 2, 0))
    return Part.makeCompound([f.extrude(V(0, 0, depth)) for f in shape.Faces])


def largest_solid(shape):
    return max(shape.Solids, key=lambda s: s.Volume)


def chamfer_outer(shape, size, z):
    """Chamfer the circular outer edge of a shell at height z: these edges print on the bed, where a
    fillet would start as an unsupported 90 degree overhang (best effort)."""
    try:
        edges = [e for e in shape.Edges if abs(e.BoundBox.ZMin - z) < 1e-3 and abs(e.BoundBox.ZMax - z) < 1e-3
                 and e.BoundBox.XLength > 2 * R_OUT - 0.5]
        if edges:
            return shape.makeChamfer(size, edges)
    except Exception:
        pass
    return shape


def lanyard_mouths(body):
    """Fillet the two bore mouths.  The chord bore leaves the round wall at a grazing angle (16 degrees on
    the outer side), so without this each mouth is a knife edge that would saw the cord.  OCC's fillet is
    fragile on such edges: a result is accepted only if it is valid, adds nothing, removes a plausible
    volume and the feather sliver is gone."""
    edges = [e for e in body.Edges
             if abs(e.BoundBox.ZMin - LANYARD_Z) < LANYARD_BORE and abs(e.BoundBox.ZMax - LANYARD_Z) < LANYARD_BORE
             and all(abs(math.hypot(p.x - CX, p.y - CY) - R_OUT) < 0.02 for p in e.discretize(12))]
    y_gen = LANYARD_R + LANYARD_BORE / 2                             # the bore's outermost line, 36.7 from the axis
    x_probe = math.sqrt(R_OUT ** 2 - y_gen ** 2) - 0.6                # 0.6 mm in from the knife edge ...
    y_probe = (y_gen + math.sqrt(R_OUT ** 2 - x_probe ** 2)) / 2      # ... halfway through the sliver there
    probes = [V(CX + s * x_probe, CY - y_probe, LANYARD_Z) for s in (1, -1)]
    if len(edges) != 2 or not all(body.isInside(p, 1e-6, True) for p in probes):
        print("lanyard mouths: unexpected geometry (%d edges), not filleted  <-- CHECK" % len(edges))
        return body
    for r in (LANYARD_MOUTH, LANYARD_MOUTH - 0.05, LANYARD_MOUTH + 0.1, LANYARD_MOUTH - 0.2):
        try:
            f = body.makeFillet(r, edges)
            if (f.isValid() and f.cut(body).Volume < 0.01 and 0 < body.cut(f).Volume < 100
                    and not any(f.isInside(p, 1e-6, True) for p in probes)):
                print("lanyard mouths: %.2f mm fillet" % r)
                return f
        except Exception:
            pass
    print("lanyard mouths: NOT filleted (OCC refused every radius)  <-- CHECK")
    return body


# --- Parts ------------------------------------------------------------------

def underside_art(font):
    """Radar dial and name, drawn as seen from below (mirrored in X), as solids from Z_BOTTOM up."""
    art = []
    for r in (20.0, 28.0):
        art.append(annulus(r - 0.25, r + 0.25, 0, DEBOSS_ART, 0, 0))
    for k in range(12):
        a = math.radians(30 * k)
        tick = Part.makeBox(1.5, 0.5, DEBOSS_ART, V(28.5, -0.25, 0))
        tick.rotate(V(0, 0, 0), V(0, 0, 1), 30 * k)
        art.append(tick)
    art.append(text_solid("FINDER PUCK", TEXT_H, DEBOSS_TEXT, 0, 3.0, font))
    # "1 [ ]  2 [ ]": tick one with a paint pen so the two pucks can be told apart.
    art.append(text_solid("1", TEXT_H, DEBOSS_TEXT, -8.0, -6.0, font))
    art.append(text_solid("2", TEXT_H, DEBOSS_TEXT, 3.5, -6.0, font))
    for x in (-3.5, 8.0):
        box = Part.makeBox(4.0, 4.0, DEBOSS_TEXT, V(x - 2.0, -8.0, 0))
        art.append(box.cut(Part.makeBox(2.8, 2.8, DEBOSS_TEXT + 1, V(x - 1.4, -7.4, -0.5))))
    comp = Part.makeCompound(art)
    m = FreeCAD.Matrix()
    m.A11 = -1.0                                   # mirror X: it is read from below
    comp = comp.transformGeometry(m)
    comp.translate(V(CX, CY, Z_BOTTOM))
    return comp


def make_shell(font):
    body = cyl(R_OUT, Z_BOTTOM, Z_SPLIT)
    body = chamfer_outer(body, 0.8, Z_BOTTOM)
    body = body.cut(cyl(R_IN, Z_FLOOR, Z_SPLIT + 1))
    # Lap lip at the inner edge of the wall top, overhanging the inside on a 45 degree underside; the
    # rest of the wall top (R_LAP1 to R_OUT) is the seal's seat.
    under = R_IN - R_LAP0
    body = body.fuse(revolved([(R_LAP0, Z_SPLIT + LIP_H), (R_LAP1, Z_SPLIT + LIP_H), (R_LAP1, Z_SPLIT - under - 0.01),
                               (R_IN + 0.01, Z_SPLIT - under - 0.01), (R_LAP0, Z_SPLIT)]))
    # The lip is left out over the GPS module's corners (data-sheet maximum) and over the board notch, where
    # the battery wires and the pigtail stand.
    z_top = Z_SPLIT + LIP_H + 1
    a0, a1 = GPS_CLEAR_ARC
    body = body.cut(sector(R_LAP0 - 1.0, R_IN, a0, a1, Z_SPLIT - under - 1, z_top).fuse(
        sector(R_IN - 0.01, R_LAP1 + 0.02, a0, a1, Z_SPLIT, z_top)))
    a, w = BATT_NOTCH[0], BATT_NOTCH[1]
    body = body.cut(radial_box(a, R_LAP0 - 1.0, R_IN, w, Z_SPLIT - under - 1, z_top).fuse(
        radial_box(a, R_IN - 0.01, R_LAP1 + 0.02, w, Z_SPLIT, z_top)))
    # Rim ledge under the board, with a 45 degree underside so it prints without support.
    body = body.fuse(revolved([(R_IN - LEDGE_W, -T_BOARD), (R_IN + 0.01, -T_BOARD), (R_IN + 0.01, -T_BOARD - LEDGE_W)]))
    # Insert bosses up to the board underside.
    for x, y in BOLTS["points"]:
        px, py = pt(x, y)
        body = body.fuse(cyl(BOSS_R, Z_FLOOR, -T_BOARD, px, py))
    # Lanyard: inward thickening with a chord bore, both mouths fully outside the skin.
    r0, a0, a1 = LANYARD_BLOCK
    body = body.fuse(sector(r0, R_IN + 0.01, a0, a1, Z_FLOOR, -T_BOARD - LEDGE_W))
    half = math.sqrt(R_OUT ** 2 - (LANYARD_R - LANYARD_BORE / 2) ** 2) + 1.0
    bore = Part.makeCylinder(LANYARD_BORE / 2, 2 * half, V(CX - half, CY - LANYARD_R, LANYARD_Z), V(1, 0, 0))
    body = lanyard_mouths(body.cut(bore))
    # Insert holes, counter-sunk so the melt the insert pushes up stays below the board.
    for x, y in BOLTS["points"]:
        px, py = pt(x, y)
        body = body.cut(cyl(INSERT_D / 2, -T_BOARD - INSERT_DEPTH, -T_BOARD + 1, px, py))
        body = body.cut(cyl(INSERT_SINK_D / 2, -T_BOARD - INSERT_SINK, -T_BOARD + 1, px, py))
    # USB-C: notch through the wall, open to the parting line (the plate skirt closes it).
    body = body.cut(radial_box(F["usb"]["angle"], R_BOARD - 1.0, R_OUT + 2, USB_W, USB_Z0, Z_SPLIT + LIP_H + 1))
    # Power switch knob, with a finger scallop on the outside so the knob can be reached.  Both stay below
    # the rim, so the seal is unbroken here.
    body = body.cut(radial_box(F["power_switch"]["angle"], R_BOARD - 2.0, R_OUT + 2, SWITCH_W, SWITCH_Z0, SWITCH_Z1))
    body = body.cut(radial_box(F["power_switch"]["angle"], R_OUT - SCALLOP_D, R_OUT + 2, SCALLOP_W, SCALLOP_Z0, SCALLOP_Z1))
    # Blind holes for the two plug tethers' pins.
    body = body.cut(radial_pin(F["usb"]["angle"], R_OUT - PLUG_PIN_L, R_OUT + 1, PLUG_PIN_D, USB_PIN_Z))
    body = body.cut(radial_pin(F["power_switch"]["angle"], R_OUT - SCALLOP_D - PLUG_PIN_L + 0.4, R_OUT, PLUG_PIN_D, SW_PIN_Z))
    # Battery lead: the board is notched here; the ledge is cut and the wall gets a shallow groove.
    angle, width, _ = BATT_NOTCH
    body = body.cut(radial_box(angle, R_IN - LEDGE_W - 0.5, R_IN + 0.3, width, -4.0, 2.0))
    # Motor pocket: a shallow recess in the floor.
    mx, my = pt(*MOTOR_POCKET)
    body = body.cut(cyl(F["motor"]["dia"] / 2 + 0.3, Z_FLOOR - 0.6, Z_FLOOR + 0.01, mx, my))
    # The flex antenna passes the rim ledge on its way up the wall.
    body = body.cut(sector(R_IN - LEDGE_W - 0.5, R_IN + 0.05, FLEX_ARC[0] - 2, FLEX_ARC[1] + 2,
                           -T_BOARD - LEDGE_W - 0.5, -T_BOARD + 0.5, steps=80))
    # Radar dial and name on the underside.
    body = body.cut(underside_art(font))
    return largest_solid(body.removeSplitter())


def make_plate():
    body = cyl(R_OUT, Z_SPLIT + PLATE_GAP, Z_FACE)
    body = chamfer_outer(body, 1.0, Z_FACE)
    # Hollow: skirt over the shell lip, then the inner wall up to the skin.
    body = body.cut(cyl(R_SKIRT_IN, Z_SPLIT - 1, Z_SPLIT + LIP_H + 0.2))
    body = body.cut(cyl(R_IN, Z_SPLIT - 1, Z_SKIN))
    # Bosses down to the PCB top, bolt bores and counterbores.
    for x, y in BOLTS["points"]:
        px, py = pt(x, y)
        body = body.fuse(cyl(BOSS_R, 0.0, Z_SKIN + 0.01, px, py))
    for x, y in BOLTS["points"]:
        px, py = pt(x, y)
        body = body.cut(cyl(BOLT_CLEAR / 2, -1, Z_FACE + 1, px, py))
        body = body.cut(cyl(CBORE_D / 2, Z_FACE - (HEAD_H - HEAD_PROUD) - WASHER_T, Z_FACE + 1, px, py))
    # Bezel: opening through the face and the pocket for its flange.
    body = body.cut(cyl(R_OPENING, Z_SKIN - 1, Z_FACE + 1))
    body = body.cut(annulus(R_OPENING - 0.5, R_FLANGE1 + 0.3, Z_SKIN - 1, Z_FLANGE1))
    # GPS sky window: the skin thins to a cover over the patch (or opens, if GPS_WINDOW == "open").
    if GPS_WINDOW == "open":
        body = body.cut(board_rect(*GPS_WIN, Z_SKIN - 1, Z_FACE + 1, GPS_WIN_R))
    else:
        body = body.cut(board_rect(*GPS_WIN, Z_SKIN - 1, Z_FACE - GPS_COVER, GPS_WIN_R))
    # 12 o'clock index: blind hole for the orange stub.
    body = body.cut(cyl(INDEX_D / 2, Z_FACE - INDEX_DEPTH, Z_FACE + 1, CX, CY + INDEX_R))
    # Button bore down a sleeve under the skin (the O-ring's bore, with a lead-in at its mouth), the charge-LED
    # pinhole, and a dimple that marks the ON end of the switch slot.
    bx, by = pt(*BUTTON["center"])
    body = body.fuse(cyl(SLEEVE_R, SLEEVE_Z0, Z_FLANGE1 + 0.01, bx, by))
    body = body.cut(cyl(CAP_BORE / 2, SLEEVE_Z0 - 1, Z_FACE + 1, bx, by))
    body = body.cut(Part.makeCone(CAP_BORE / 2 + SLEEVE_LEAD, CAP_BORE / 2, SLEEVE_LEAD, V(bx, by, SLEEVE_Z0)))
    ox, oy = at(F["power_switch"]["angle"] - 6, R_IN - 1.9)
    body = body.cut(cyl(0.6, Z_FACE - 0.3, Z_FACE + 1, ox, oy))
    dx, dy = pt(*F["charge_led"]["center"])
    body = body.cut(cyl(PINHOLE_D / 2, Z_SKIN - 1, Z_FACE + 1, dx, dy))
    # The USB-C opening continues up through the skirt (the switch slot stays in the shell).
    body = body.cut(radial_box(F["usb"]["angle"], R_BOARD - 1.0, R_OUT + 2, USB_W, USB_Z0, USB_Z1))
    return largest_solid(body.removeSplitter())


def make_ring():
    """Lower ring: stands on a 0.3 mm foam ring on the board, carries the panel on its ledge."""
    z0 = RING_FOOT_Z
    r_in = R_WALL0 + PANEL_CLEAR                   # 18.15
    profile = [
        (r_in, z0), (R_WALL1, z0), (R_WALL1, Z_WALL_STEP),
        (R_WALL1_TOP, Z_WALL_STEP + (R_WALL1_TOP - R_WALL1)),      # 45 degree step outward
        (R_WALL1_TOP, Z_CRYSTAL), (r_in, Z_CRYSTAL),
        (r_in, LEDGE_Z), (R_LEDGE0, LEDGE_Z),
        (r_in, LEDGE_Z - (r_in - R_LEDGE0)),                       # 45 degree underside of the ledge
    ]
    ring = revolved(profile)
    # The GPS module reaches under the thicker top at 12 o'clock: the wall stays thin there.
    ring = ring.cut(sector(R_WALL_GPS, R_WALL1_TOP + 1, GPS_CLEAR_ARC[0], GPS_CLEAR_ARC[1], z0 - 1, Z_CRYSTAL + 1))
    for a0, a1 in WALL_GAPS:
        if a0 == 145:   # over the ESP32 can the ring starts at Z 3.6 (the ledge stays)
            ring = ring.cut(sector(R_LEDGE0 - 0.5, R_WALL1_TOP + 0.5, a0, a1, z0 - 1, Z_WALL_STEP))
        else:           # the panel chin and the FPC pass here
            ring = ring.cut(sector(R_LEDGE0 - 0.5, R_WALL1_TOP + 0.5, a0, a1, z0 - 1, Z_CRYSTAL + 1))
    return largest_solid(ring.removeSplitter())


def make_bezel():
    """Translucent bezel: crystal seat, flared lip, clamp flange, skirt around the ring, light pipes."""
    body = annulus(R_BEZEL_IN, R_BEZEL1, Z_CRYSTAL, Z_CRYSTAL_TOP)
    lip = annulus(WINDOW_D / 2, R_LIP1, Z_CRYSTAL_TOP, Z_FACE + LIP_PROUD)
    flange = annulus(R_BEZEL1 - 0.01, R_FLANGE1, Z_FLANGE0, Z_FLANGE1)
    # Over the GPS module (top at Z 6.35) only the upper 0.4 mm of the flange remains.
    flange = flange.cut(sector(R_BEZEL1 + 0.01, R_FLANGE1 + 1, GPS_FLANGE_GAP[0], GPS_FLANGE_GAP[1],
                               Z_FLANGE0 - 1, Z_CRYSTAL_TOP))
    skirt = annulus(R_SKIRT0, R_BEZEL1, Z_SKIRT0, Z_CRYSTAL + 0.01)
    for a0, a1 in WALL_GAPS:
        if a0 != 145:   # the panel chin passes under the skirt at 6 o'clock
            skirt = skirt.cut(sector(R_SKIRT0 - 0.5, R_BEZEL1 + 0.5, a0, a1, Z_SKIRT0 - 1, Z_CRYSTAL + 1))
    bezel = body.fuse([lip, flange, skirt])
    for x, y in LEDS["points"]:
        px, py = pt(x, y)
        bezel = bezel.fuse(cyl(PIPE_D / 2, PIPE_Z0, Z_FLANGE0 + 0.01, px, py))
    # The button cap and the plate's sleeve round it pass through the flange at 6 o'clock.
    bx, by = pt(*BUTTON["center"])
    bezel = bezel.cut(cyl(SLEEVE_R + 0.25, Z_FLANGE0 - 1, Z_FACE + 1, bx, by))
    # Over the GPS module (up to 6.8 mm tall, edge at r 19.2 at its widest) only the top 0.8 mm of the lip remains
    # beyond r 18.7: no seat wall, skirt or flange, so a tall module meets nothing below Z 7.2.
    bezel = bezel.cut(sector(R_BEZEL_GPS, R_FLANGE1 + 1, GPS_CLEAR_ARC[0], GPS_CLEAR_ARC[1], Z_SKIRT0 - 1, Z_FLANGE1))
    return largest_solid(bezel.removeSplitter())


def make_cap():
    bx, by = pt(*BUTTON["center"])
    z0 = BUTTON["stem_height"] - CAP_SOCKET_DEPTH          # 4.0: the stem sits in a pocket
    z_top = SLEEVE_Z0 - 0.1                                 # flange top 0.1 mm under the sleeve
    r, rf = CAP_D / 2, CAP_FLANGE_D / 2
    rg, g0, g1 = ORING_GROOVE
    profile = [(0, z0), (rf, z0), (rf, z_top), (r, z_top), (r, g0), (rg, g0), (rg, g1), (r, g1 + (r - rg)),
               (r, Z_FACE + CAP_PROUD), (0, Z_FACE + CAP_PROUD)]
    pts = [V(bx + rr, by, zz) for rr, zz in profile] + [V(bx, by, z0)]
    cap = Part.Face(Part.makePolygon(pts)).revolve(V(bx, by, 0), V(0, 0, 1), 360)
    try:
        top = [e for e in cap.Edges if abs(e.BoundBox.ZMin - (Z_FACE + CAP_PROUD)) < 1e-3]
        cap = cap.makeFillet(1.0, top)
    except Exception:
        pass
    s = CAP_SOCKET / 2
    cap = cap.cut(Part.makeBox(CAP_SOCKET, CAP_SOCKET, CAP_SOCKET_DEPTH + 0.01, V(bx - s, by - s, z0 - 0.01)))
    return cap


def make_panel():
    r = PANEL["outline_dia"] / 2
    disc = cyl(r, LEDGE_Z, Z_PANEL_TOP)
    hw = PANEL["chin_width"] / 2
    chin = board_rect(BX - hw, BY + r - 2.0, BX + hw, PANEL["chin_reach"], LEDGE_Z, Z_PANEL_TOP)
    return disc.fuse(chin)


def make_crystal():
    return cyl(CRYSTAL_D / 2, Z_CRYSTAL, Z_CRYSTAL_TOP)


def make_battery():
    # 503450-class cell, 34.5 x 52 x 5.3 mm, long axis 12-6 o'clock, under the board on foam.
    return Part.makeBox(34.5, 52.0, 5.3, V(CX - 17.25, CY - 26.0, Z_FLOOR + 0.5))


def make_motor():
    mx, my = pt(*MOTOR_POCKET)
    return cyl(F["motor"]["dia"] / 2, Z_FLOOR - 0.6, Z_FLOOR - 0.6 + F["motor"]["thickness"], mx, my)


def make_antenna():
    return sector(R_IN - FLEX_T, R_IN, FLEX_ARC[0], FLEX_ARC[1], FLEX_Z[0], FLEX_Z[1], steps=90)


def make_bolt(px, py):
    z_head = Z_FACE - (HEAD_H - HEAD_PROUD)
    bolt = cyl(HEAD_D / 2, z_head, z_head + HEAD_H, px, py)
    bolt = bolt.fuse(cyl(BOLT_D / 2, z_head - BOLT_L, z_head, px, py))
    return bolt.cut(hex_prism(SOCKET_AF, z_head + HEAD_H - SOCKET_DEPTH, z_head + HEAD_H + 1, px, py))


def make_insert(px, py):
    return annulus(BOLT_D / 2 - 0.2, INSERT_OD / 2, -T_BOARD - INSERT_L, -T_BOARD, px, py)


def make_index():
    return cyl(1.75 / 2, Z_FACE - INDEX_DEPTH, Z_FACE, CX, CY + INDEX_R)


def make_washer(px, py):
    z1 = Z_FACE - (HEAD_H - HEAD_PROUD)
    return annulus(WASHER_ID / 2, WASHER_D / 2, z1 - WASHER_T, z1, px, py)


def make_seal():
    """The foam seal on the shell rim, drawn squeezed to the rim gap; it stops at the USB-C opening's sides."""
    seal = annulus(R_SKIRT_IN + SEAL_INSET, R_OUT - SEAL_INSET, Z_SPLIT, Z_SPLIT + PLATE_GAP)
    return seal.cut(radial_box(F["usb"]["angle"], R_BOARD - 1.0, R_OUT + 2, USB_W, Z_SPLIT - 1, Z_SPLIT + 2))


def make_oring():
    """The button's O-ring, drawn squeezed: groove bottom to the bore, at the bottom of the groove."""
    bx, by = pt(*BUTTON["center"])
    rg, g0, _ = ORING_GROOVE
    return annulus(rg, CAP_BORE / 2, g0, g0 + math.pi / 4 * ORING_CS ** 2 / (CAP_BORE / 2 - rg), bx, by)


def make_usb_plug():
    """TPU cover for the USB-C opening: body pressed into the opening, a flange lying on the wall round it
    (across the seal's end), a grip, and a strap down to a pin glued into the shell."""
    a, s = F["usb"]["angle"], PLUG_SQUEEZE
    w2 = USB_W / 2
    body = local_box(a, USB_PLUG_IN, R_OUT + 0.01, -w2 - s, w2 + s, USB_Z0 - s, USB_Z1 + s)
    body = body.common(cyl(R_OUT + 0.005, USB_Z0 - 1, USB_Z1 + 1))
    z0, z1 = USB_Z0 - PLUG_FLANGE_W, USB_Z1 + PLUG_FLANGE_W
    ro = R_OUT + PLUG_FLANGE_T
    flange = annulus(R_OUT, ro, z0, z1).common(local_box(a, R_OUT - 3, ro + 1, -w2 - PLUG_FLANGE_W, w2 + PLUG_FLANGE_W, z0, z1))
    grip = annulus(ro - 0.01, ro + 0.7, 0.5, 2.0).common(local_box(a, R_OUT - 3, ro + 2, -3.0, 3.0, 0.0, 3.0))
    strap = annulus(R_OUT, R_OUT + PLUG_STRAP_T, USB_PIN_Z - PLUG_PIN_D / 2 - 0.4, z0 + 0.01).common(
        local_box(a, R_OUT - 3, ro + 1, -PLUG_STRAP_W / 2, PLUG_STRAP_W / 2, -20, 20))
    pin = radial_pin(a, R_OUT - PLUG_PIN_L, R_OUT + 0.3, PLUG_PIN_D, USB_PIN_Z)
    return body.fuse([flange, grip, strap, pin]).removeSplitter()


def make_switch_plug():
    """TPU cover for the switch slot, sitting in the finger scallop: body in the slot (clear of the knob), a
    flange on the scallop's flat floor, a ridge for a fingernail, and a strap to a pin below the slot."""
    a, s = F["power_switch"]["angle"], PLUG_SQUEEZE
    x_floor = R_OUT - SCALLOP_D
    w2 = SWITCH_W / 2
    fw = SCALLOP_W / 2 - 0.2
    xo = x_floor + PLUG_FLANGE_T - 0.1
    body = local_box(a, SW_PLUG_IN, x_floor + 0.01, -w2 - s, w2 + s, SWITCH_Z0 - s, SWITCH_Z1 + s)
    flange = local_box(a, x_floor, xo, -fw, fw, SWITCH_Z0 - 1.2, SCALLOP_Z1 - 0.1)
    ridge = local_box(a, xo - 0.01, xo + 0.4, -2.0, 2.0, SWITCH_Z1 - 0.2, SCALLOP_Z1 - 0.1)
    strap = local_box(a, x_floor, xo, -PLUG_STRAP_W / 2, PLUG_STRAP_W / 2, SW_PIN_Z - PLUG_PIN_D / 2 - 0.3, SWITCH_Z0 - 1.19)
    pin = radial_pin(a, x_floor - PLUG_PIN_L + 0.4, x_floor + 0.01, PLUG_PIN_D, SW_PIN_Z)
    return body.fuse([flange, ridge, strap, pin]).removeSplitter()


# --- Proxies ----------------------------------------------------------------

def make_ph_plug():
    """The mated PHR-2 housing, PH_PLUG_OUT beyond J2's mouth, pointing the way the footprint does."""
    length, width, height = PH_PLUG
    jx, jy = pt(*F["battery_connector"]["center"])
    dx, dy = fp_dir(F["battery_connector"]["ref"], 0.0, 1.0)
    box = Part.makeBox(length, width, height, V(PH_MOUTH + PH_PLUG_OUT - length, -width / 2, 0.0))
    box.rotate(V(0, 0, 0), V(0, 0, 1), math.degrees(math.atan2(dy, dx)))
    box.translate(V(jx, jy, 0))
    return box


def make_notch_cables():
    """The battery wires and the antenna pigtail standing side by side in the board notch."""
    n, dia, pitch, z0, z1 = NOTCH_CABLES
    angle, width, depth = BATT_NOTCH
    tx, ty = -math.sin(math.radians(angle)), math.cos(math.radians(angle))
    cx, cy = at(angle, R_BOARD - depth / 2)
    shapes = []
    for k in range(n):
        s = (k - (n - 1) / 2) * pitch
        shapes.append(cyl(dia / 2, z0, z1, cx + s * tx, cy + s * ty))
    return Part.makeCompound(shapes)


def make_fpc_fold():
    """The FPC's fold beyond the panel chin: a bump PANEL['fold_bump'] thick just under the glass."""
    r_chin = PANEL["chin_reach"] - BY
    half = math.degrees(math.asin(PANEL["chin_width"] / 2 / r_chin))
    a = PANEL["fpc_angle"]
    return sector(r_chin, r_chin + PANEL["fold_bump"], a - half, a + half, LEDGE_Z - PANEL["fold_bump"], LEDGE_Z)


def make_usb_overmold():
    """A USB-C plug's overmold, centred on the receptacle axis, from the receptacle mouth outward."""
    width, height, zc, length = USB_PLUG
    r0 = F["usb"]["mouth_x"] - BX
    return radial_box(F["usb"]["angle"], r0, r0 + length, width, zc - height / 2, zc + height / 2)


def make_gps_envelope():
    """The GPS module at its data-sheet limits: the full-height box plus the de-paneling tabs."""
    gx, gy = pt(*F["gps"]["center"])
    env = None
    for sx, sy, z0, z1 in GPS_ENVELOPE:
        box = Part.makeBox(sx, sy, z1 - z0, V(gx - sx / 2, gy - sy / 2, z0))
        env = box if env is None else env.fuse(box)
    return env.removeSplitter()


# --- Checks -----------------------------------------------------------------

def bb_gap(a, b):
    dx = max(0.0, a.XMin - b.XMax, b.XMin - a.XMax)
    dy = max(0.0, a.YMin - b.YMax, b.YMin - a.YMax)
    dz = max(0.0, a.ZMin - b.ZMax, b.ZMin - a.ZMax)
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def min_distance(a, b, limit):
    """(distance, point) between shapes a and b if they come closer than limit, else None.  Solid by solid
    and face by face with bounding-box culling: the populated board has 200 solids and 6000 faces."""
    best = None
    for sb in (b.Solids or [b]):
        faces = [f for f in a.Faces if bb_gap(f.BoundBox, sb.BoundBox) < limit]
        if not faces:
            continue
        bfaces = [f for f in sb.Faces if any(bb_gap(f.BoundBox, g.BoundBox) < limit for g in faces)]
        if not bfaces:
            continue
        d, pts, _ = Part.makeCompound(faces).distToShape(Part.makeCompound(bfaces))
        if best is None or d < best[0]:
            best = (d, pts[0][0])
            if d <= 1e-6:
                break
    return best if best and best[0] < limit else None


def main():
    font = font_file()
    if GPS_WINDOW == "open":
        print("GPS_WINDOW = open: the sky window is a hole, so the case is NOT sealed (IP55 needs the skin)  <-- CHECK")
    doc = FreeCAD.newDocument("finder_puck_case")
    board = Part.read(os.path.join(MECH, NAME + ".step"))
    board.translate(V(0, 0, -T_BOARD))     # KiCad exports the PCB with its underside at Z 0
    shapes = {
        "Board": board,
        "Panel": make_panel(), "Crystal": make_crystal(), "Battery": make_battery(),
        "Motor": make_motor(), "Antenna": make_antenna(),
        "Shell": make_shell(font), "Plate": make_plate(), "Ring": make_ring(), "Bezel": make_bezel(),
        "Cap": make_cap(), "UsbPlug": make_usb_plug(), "SwitchPlug": make_switch_plug(),
        "Index": make_index(), "Seal": make_seal(), "ORing": make_oring(),
        "ProxyPlug": make_ph_plug(), "ProxyCables": make_notch_cables(), "ProxyFold": make_fpc_fold(),
        "ProxyUSB": make_usb_overmold(), "ProxyGPS": make_gps_envelope(),
    }
    for i, (x, y) in enumerate(BOLTS["points"]):
        px, py = pt(x, y)
        shapes["Bolt%d" % (i + 1)] = make_bolt(px, py)
        shapes["Insert%d" % (i + 1)] = make_insert(px, py)
        shapes["Washer%d" % (i + 1)] = make_washer(px, py)
    objs = {}
    for name, shape in shapes.items():
        o = doc.addObject("Part::Feature", name)
        o.Shape = shape
        objs[name] = o

    # Interference: printed parts against everything they must clear.
    printed = ("Shell", "Plate", "Ring", "Bezel", "Cap", "UsbPlug", "SwitchPlug")
    hardware = tuple(n for n in shapes if n.startswith(("Bolt", "Insert", "Washer"))) + ("Index", "Seal", "ORing")
    proxies = tuple(n for n in shapes if n.startswith("Proxy"))
    bad = 0
    close = {}
    for i, part in enumerate(printed):
        others = ("Board", "Panel", "Crystal", "Battery", "Motor", "Antenna") + hardware + proxies + printed[i + 1:]
        for other in others:
            if frozenset((part, other)) in EXCLUSIVE:
                continue
            common = objs[part].Shape.common(objs[other].Shape)
            vol = common.Volume if not common.isNull() else 0.0
            if frozenset((part, other)) in SQUEEZE:
                flag = "" if vol >= 0.001 else "  <-- CHECK (no squeeze)"
                print("squeeze %-10s vs %-11s %8.3f mm^3%s" % (part, other, vol, flag))
                bad += 1 if flag else 0
                continue
            flag = "" if vol < 0.001 else "  <-- CHECK"
            if flag:
                bad += 1
            if flag or not other.startswith(("Bolt", "Insert", "Washer")):
                print("overlap %-10s vs %-11s %8.3f mm^3%s" % (part, other, vol, flag))
            near = min_distance(objs[part].Shape, objs[other].Shape, REPORT_GAP)
            if near:
                kind = other.rstrip("0123456789")      # Bolt1..4, Insert1..4 and Washer1..4 collapse into one line each
                key = (part, kind, round(near[0], 3))
                close.setdefault(key, [near[1], 0])[1] += 1
    # Clearances: every printed-vs-other pair closer than REPORT_GAP, tightest first.  Contacts are the
    # designed seats (board on ledge, panel on ring, crystal under lip, flange under skin, bosses on the PCB).
    for (part, kind, d), (p, n) in sorted(close.items(), key=lambda kv: kv[0][2]):
        print("gap %-10s vs %-11s %6.3f mm at (%6.1f, %6.1f, %5.1f)%s" % (
            part, kind + ("x%d" % n if n > 1 else ""), d, p.x, p.y, p.z, "  contact" if d < 1e-3 else ""))
    print("case: %.1f mm across, %.1f mm tall (face at Z %.1f, bottom at Z %.1f); %d interference(s); "
          "%d pair(s) closer than %.1f mm; font %s" % (
              2 * R_OUT, Z_FACE - Z_BOTTOM, Z_FACE, Z_BOTTOM, bad, len(close), REPORT_GAP, os.path.basename(font)))

    out = os.path.join(CASE, NAME + "_case.FCStd")
    if os.path.exists(out):
        os.remove(out)
    doc.saveAs(out)
    # 0.01 mm deflection: at 0.02 the mesher leaves sliver triangles that cross each other where the
    # lanyard fillets run tangent to the wall; every STL must come out closed and free of self-intersections.
    for name in printed:
        mesh = MeshPart.meshFromShape(Shape=objs[name].Shape, LinearDeflection=0.01,
                                      AngularDeflection=math.radians(8), Relative=False)
        mesh.write(os.path.join(CASE, "%s_%s.stl" % (NAME, name.lower())))
        crossings = len(mesh.getSelfIntersections())
        flag = "" if mesh.isSolid() and not crossings else "  <-- CHECK"
        print("mesh %-10s %6d facets, %s, %d self-intersection(s)%s" % (
            name, mesh.CountFacets, "closed" if mesh.isSolid() else "NOT closed", crossings, flag))
    Import.export([objs[n] for n in printed], os.path.join(CASE, NAME + "_case.step"))
    print("wrote", out)


# freecadcmd runs this file as module "build_case" (never "__main__"); the manual's render script
# imports it for the parameters, so only build when this file is the script being run.
if os.path.basename(sys.argv[-1] if sys.argv else "") == "build_case.py":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        raise
