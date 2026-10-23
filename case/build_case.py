"""
Case for the finder puck, built from the board's feature file.

A machined aluminium shell and four printed parts clamp together with four M2.5 screws that pass through the PCB:

  SHELL  (6061-T6, black anodised)  battery bay, motor pocket, tapped bolt bosses, cross-drilled lanyard hole,
                                switch slot, the OSHW logo V-carved into the back, and a notch from 1 to 4
                                o'clock (the antenna window) where its wall is cut down to the floor
  WINDOW (black)                the wall in that notch: plastic, so the LoRa flex antenna on its inside and the
                                USB-C door in it are not behind metal.  Pegs into the shell's floor locate it
  PLATE  (black)                bolt bosses with counterbored heads, covered sky window over the GPS patch,
                                button bore, charge-LED pipe bore, orange index dot at 12 o'clock, pocket for
                                the bezel flange and lid gasket.  Plastic: it is the GPS patch's radome
  RING   (black)                a short cup standing on the board: the panel's ledge.  Open
                                at 6 o'clock for the panel chin and FPC, low over the ESP32
  BEZEL  (translucent)          sits on the ring: crystal seat, the visible lip, the flange
                                the plate clamps, four light pipes down to the LEDs, a light
                                pipe up from the charge LED, and the button bore's sleeve
  CAP    (orange)               the single button, sealed by an O-ring in the bezel's sleeve
  DOOR   (black)                slides round the window over the USB-C opening; its gasket seals on a land
  SWITCH PLUG (TPU)             tethered cover for the switch slot

Aluminium blocks radio.  The GPS patch looks up through the plastic plate and the LoRa antenna out through the
plastic window, so every surface between an antenna and the sky is plastic; the build reports how close the
aluminium comes to each.  The shell is drawn for a 3-axis mill in three setups (top, back, side): no undercuts,
inside corners at least the radius of the tool that cuts them, the window's two ends 60 degree flanks.

The ring and bezel used to be one part, but a panel cannot be fitted into a cup that has a
ledge below it and a lip above it, so the stack is now: ring, panel, gasket, crystal, bezel.

Sealed to IP55 (dust protected, water jets): a closed-cell foam seal compressed between the rim of the shell and
window and the plate's skirt, a foam strip under the window (on the shell's flanks and the notch floor), nylon
washers under the bolt heads, an O-ring on the button cap, the USB-C door's gasket, the switch plug, and die-cut
foam gaskets under the bezel's lip (on the crystal) and on its flange (under the plate).  Nothing is glued: the lid
comes off with the four bolts.  Every path in ends at one of those (see "Sealing (IP55)" in the README).

Modelled hardware (not made): four M2.5 x 12 socket caps and their nylon washers, the
orange index stub, the panel, crystal, battery, motor, the flex antenna, the seam seal, the window gasket, the
button's O-ring and the door, crystal and lid gaskets (all drawn compressed).  Proxies (not in the board model
either) for the mated battery plug, the three cables through the board notch, the FPC fold, the
USB plug's overmold and the GPS module at its tolerance limits.  Every made part is checked
for interference against all of these, and every made-vs-other pair closer than REPORT_GAP is
listed with its nearest point.

Run with FreeCAD's console after regenerating the board:

    /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd case/build_case.py

Coordinates: X = board x, Y = -board y (KiCad's Y points down), Z = 0 at the PCB top.
Angles are degrees, 0 at 3 o'clock, counter-clockwise on the face (90 = 12 o'clock).
"""

import json
import math
import os
import re
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
WALL = 1.8
R_IN = R_BOARD + GAP             # 36.4
R_OUT = R_IN + WALL              # 38.2 -> 76.4 mm across
FLOOR = 1.8                      # leaves 1.4 mm under the 0.4 mm V-carve and 1.2 mm under the motor pocket
BAY = 6.3                        # 5.3 mm cell on 0.5 mm foam, 0.5 mm air above it
Z_FLOOR = -T_BOARD - BAY         # -7.9
Z_BOTTOM = Z_FLOOR - FLOOR       # -9.7
Z_SPLIT = 3.0                    # parting line
LEDGE_W = 2.0                    # the board rests on a 2 mm step: the bay below it is a smaller bore (no undercut)
R_BAY = R_IN - LEDGE_W           # 34.4
BOTTOM_R = 1.0                   # outer edge of the back, a corner-rounding cutter
# Shell-to-plate joint: the plate's skirt covers the whole rim (and the window's top); no lap lip, which would be
# an undercut in the aluminium.
SEAL_T, SEAL_INSET = 1.0, 0.05   # closed-cell foam seal on the rim, 1.0 mm thick ...
PLATE_GAP = 0.6                  # ... squeezed to the rim gap (40 %): the bosses are still the datum, not the rim
# Antenna window: between WINDOW (angles at the notch floor) the shell's wall is cut down to the floor, with
# FLANK degree flanks at the two ends (so the bolts' clamp squeezes the foam strip on them), and a plastic wall
# part fills it, SEAL_GAP clear of the shell all round.  It stands on two feet with pegs in the shell's floor.
WINDOW = (-38.0, 81.0)           # 4 o'clock to 12 o'clock: the USB-C door's pocket, the antenna, a few mm margin
FLANK = 60.0
SEAL_GAP = PLATE_GAP             # the window gasket (1.0 mm foam strip) squeezed to 0.6 mm, normal to each face
WINDOW_FEET = (-34.0, 77.0)      # feet on the floor inside the wall: angle; radial extent, width, height
FOOT_R0, FOOT_W, FOOT_H = 34.0, 4.0, 1.5
PEG_D, PEG_L, PEG_R = 2.0, 1.0, 35.2   # pegs under the feet, in 2.1 x 1.2 mm holes drilled in the floor
Z_FACE = 8.6                     # 0.6 mm over the board's 8.0, so every lid seal is a clamped gasket
SKIN = 1.6
Z_SKIN = Z_FACE - SKIN           # 7.0
# Bolts: M2.5 x 12 socket caps (anodised aluminium, head 4.5 x 2.5) through the PCB into threads tapped in the shell.
BOSS_R = BOLTS["boss_r"]         # 3.75 (the plate's bosses)
SHELL_BOSS_R = 3.25              # the shell's: 0.55 mm round the board's 5.4 mm pad, 1.4 mm from the antenna
BOSS_FILLET = 1.5                # where they run into the bay's wall: a 3 mm cutter
BOLT_CLEAR = 3.0
HEAD_D, HEAD_H, HEAD_PROUD = 4.5, 2.5, 0.2
BOLT_D, BOLT_L = 2.5, 12.0
SOCKET_AF, SOCKET_DEPTH = 2.0, 1.2
CBORE_D = 5.2
WASHER_D, WASHER_ID, WASHER_T = 5.0, 2.7, 0.5   # DIN 433 M2.5 nylon washer under each head: seals the bolt bore
TAP_DEPTH, TAP_DRILL, DRILL_DEPTH, TAP_SINK = 5.0, 2.05, 6.0, 0.3   # M2.5 thread (modelled at 2.5), drill, countersink
# Display stack.
LEDGE_Z = PANEL["ledge_z"]       # panel underside, 4.0
PANEL_T = PANEL["thickness"]     # 1.5
GASKET = 0.2                     # a 0.3 mm foam gasket, modelled compressed so the lip preloads it
Z_PANEL_TOP = LEDGE_Z + PANEL_T  # 5.5
Z_CRYSTAL = Z_PANEL_TOP + GASKET # 5.7
CRYSTAL_D, CRYSTAL_T = PANEL["crystal_dia"], PANEL["crystal_thickness"]   # 37.5 x 1.0
Z_CRYSTAL_TOP = Z_CRYSTAL + CRYSTAL_T   # 6.7
CRYSTAL_GASKET = 0.2             # a 0.3 mm die-cut foam ring on the glass under the lip, modelled compressed
CRYSTAL_GASKET_R = (17.6, 18.6)  # inside the lip's overlap of the glass (r 17.4-18.75), outside the panel's window
Z_LIP0 = Z_CRYSTAL_TOP + CRYSTAL_GASKET   # 6.9: lip underside
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
R_FLANGE1 = 26.0                 # bezel flange under the plate skin, all the way round (0.2 mm over a 6.8 mm GPS module)
Z_FLANGE0, Z_FLANGE1 = Z_SKIN, Z_SKIN + 0.5
# Lid gasket: a die-cut 0.3 mm foam sheet on the flange, squeezed between it and the plate's pocket ceiling.
# It rings the opening, with a lobe round the button bore and a tab round the charge-LED pipe.
LID_GASKET, LID_INSET = 0.2, 0.3 # modelled compressed; inset from the flange's edges (the pocket is as much outside them)
Z_POCKET = Z_FLANGE1 + LID_GASKET   # 7.7: pocket ceiling, 0.9 mm under the face
BUTTON_LOBE = 7.4                # flange lobe round the button, which carries the bore's sleeve
LOBE_HOLE = 5.6                  # the gasket's hole round the bore (bore radius 5.3): a 1.5 mm web to the lobe's edge
PIPE_D, PIPE_Z0 = 3.0, 1.2       # light pipes from 0.3 mm above the LEDs up into the flange
# Openings.
GPS_WINDOW = "skin"              # "skin" (0.9 mm cover over the patch) or "open" (hole to the sky)
GPS_COVER = Z_FACE - Z_POCKET    # 0.9
GPS_WIN = (27.25, 0.4, 44.75, 15.2)          # board coords of the thinned area, out to the wall (module top 6.35)
GPS_WIN_R = 2.0                  # keeps the window inside the plate wall; 1 mm from the patch corner to the step
INDEX_R, INDEX_D, INDEX_DEPTH = 34.7, 1.8, 0.6   # 12 o'clock mark: a glued 1.75 mm orange filament stub in a blind hole
USB_W, USB_Z0, USB_Z1 = 13.5, -1.8, 5.2      # 12.35 x 6.5 plug overmold, centred on the receptacle axis (Z 1.65-1.78)
SWITCH_W, SWITCH_Z0, SWITCH_Z1 = 7.0, -0.5, 1.8   # knob at Z 0.45-1.25: the slot stays in the shell, under the seal
SWITCH_RC = 1.0                              # its corners: a 2 mm cutter from the side
SCALLOP_W, SCALLOP_D, SCALLOP_RC = 10.0, 1.0, 2.0   # finger scallop outside the switch slot: the knob sits 0.7 mm in
SCALLOP_Z0, SCALLOP_Z1 = -4.0, 2.6          # below the rim, so the seal runs past it unbroken
# USB-C door: a curved door that slides round the window in a pocket, held by tongues in two grooves (the
# lower one in the window, the upper one in the plate, so the door is captive once the plate is on).  A
# die-cut 0.5 mm foam gasket on its inside rides 0.05 mm clear of the pocket floor, and in the closed
# position lands on a raised frame round the opening (two-step lead-in at its ends) and is squeezed 0.2 mm.
DOOR_FLOOR = 37.1                # pocket floor radius; the seam seal runs out to it here
DOOR_LAND = 37.35                # sealing land round the opening (lead-in step at DOOR_FLOOR + 0.12)
DOOR_LAND_W, DOOR_LEAD = 1.2, 0.25   # land width round the opening, lead-in step width
DOOR_GASKET = 0.5                # die-cut closed-cell foam, uncompressed
DOOR_IN, DOOR_T = DOOR_LAND + 0.3, 0.6   # door inner face (gasket squeezed 0.5 -> 0.3), thickness: outer face r 38.25
DOOR_EDGE = 0.4                  # door beyond the land on each side
DOOR_TONGUE = (37.2, 0.35)       # door tongues: inner radius, height into the grooves
DOOR_GROOVE = (DOOR_FLOOR, 37.75, 0.45)   # grooves: r0, r1, height
DOOR_CLEAR = 0.05                # door to pocket and groove faces
DOOR_TRAVEL = 24.5               # degrees from closed to open, clockwise (towards 4 o'clock)
DOOR_GRIP = (0.3, 3)             # grip ribs on the outside: height, count
# TPU plug (85A-95A) for the switch slot: a body pressed into the slot (PLUG_SQUEEZE oversize per side), a
# flange on the scallop floor, and a strap to a pin glued into a blind hole in the shell.
PLUG_SQUEEZE = 0.1
PLUG_FLANGE_T = 0.7
PLUG_STRAP_W = 3.0
PLUG_PIN_D, PLUG_PIN_L = 1.6, 1.0
SW_PLUG_IN = 36.6                            # body's inner face, 0.14 mm from the knob (r 36.46)
SW_PIN_Z = -2.9
BATT_NOTCH = F["notches"][0]                 # (angle, width, depth): the board is notched; the wall gets a shallow groove
# Lanyard: two 3 mm holes drilled square to the surface, one up from the back and one in from the side at
# 6 o'clock, meeting in a boss inside the wall; the cord goes in at the side and out at the back.
LANYARD_ANGLE, LANYARD_R, LANYARD_D, LANYARD_Z = 270.0, 35.3, 3.0, -6.2   # vertical hole's radius; side hole's Z
LANYARD_BOSS, LANYARD_TOP = 3.2, -3.6        # boss radius (about the vertical hole) and top, 2 mm under the board
LANYARD_SINK = 0.4                           # 45 degree countersink on both mouths
DRILL_TIP = 0.5 / math.tan(math.radians(59)) # 118 degree point, per mm of diameter
MOTOR_POCKET = F["motor"]["pocket"]
# 915 MHz adhesive flex antenna (2J 2JF0515P, 39.9 x 7 mm) stuck to the inside of the plastic window, just outside
# the board's edge: perpendicular to the ground plane instead of lying under it, and 2.5 mm above the aluminium floor.
FLEX_ARC, FLEX_Z, FLEX_T = (14, 77), (-5.4, 1.6), 0.2
BUTTON = F["button"]
CAP_D, CAP_BORE, CAP_PROUD, CAP_FLANGE_D = 10.0, 10.6, 1.5, 12.4
CAP_SOCKET, CAP_SOCKET_DEPTH = 3.7, 1.0     # pocket for the PTS645 stem
# The button bore continues down a sleeve under the bezel's lobe, and a 9 x 1 mm silicone O-ring in a groove on
# the cap seals against it (gland depth 0.8: 20 % squeeze).  The cap's flange stays captive under the sleeve.
SLEEVE_R, SLEEVE_Z0, SLEEVE_LEAD = 5.9, 5.2, 0.4   # outer radius, bottom, lead-in
ORING_GROOVE = (4.5, 6.0, 7.3)               # groove bottom radius, Z from, Z to (upper wall 45 degrees)
ORING_CS = 1.0
# Charge LED: a light pipe on a tab of the bezel's flange, up through the skin to the face.
LED_PIPE_D, LED_PIPE_BORE = 1.2, 1.4         # pipe, its bore in the skin
LED_FOOT_D, LED_FOOT_Z0 = 1.6, 1.45          # thicker below the flange, 0.3 mm over the LED (top at 1.15)
LED_TAB_W, LED_TAB_R = 4.0, 2.3              # tab width, round end about the pipe
# The back carries only the Open Source Hardware logo, V-carved with a 90 degree bit to a flat depth: 45 degree walls
# from the outline down to a flat floor, sharp outside corners.  Through the anodising it shows bare aluminium.
LOGO_SVG = os.path.join(CASE, "oshw_logo.svg")
LOGO_W, VCARVE_DEPTH = 22.0, 0.4
# Proxies for what the board model does not contain.
PH_PLUG, PH_MOUTH, PH_PLUG_OUT = (6.85, 5.8, 4.5), 4.4, 2.0   # PHR-2 housing (length, width, height); J2's mouth is 4.4 mm
                                             # along its +Y; the mated housing stands this far out of the mouth
NOTCH_CABLES = (3, 1.3, 1.6, -5.0, 3.5)      # through the board notch: count, dia, spacing, z0, z1 (2 x 28 AWG + the 1.37 pigtail)
USB_PLUG = (12.35, 6.5, 1.75, 15.0)          # plug overmold: width, height, axis Z, length out from the receptacle mouth
GPS_ENVELOPE = ((15.6, 15.6, 0.0, 6.8), (15.6, 16.0, 1.0, 2.1))   # (board X, board Y, z0, z1): the module at the data
                                 # sheet's limits (A, G and F max), plus the de-paneling tabs (L up to 0.3 mm per side along the
                                 # pin-1 row, radial here, at the corners of the PCB layer)
REPORT_GAP = 0.3                             # list every printed-vs-other pair closer than this
# Designed overlaps: the switch plug's body is PLUG_SQUEEZE oversize in its slot.  Listed as a "squeeze" line,
# not an interference; anything else that overlaps is.
SQUEEZE = {frozenset(("SwitchPlug", "Shell"))}
ALUMINIUM = ("Shell",)
EXCLUSIVE = {frozenset(("Door", "ProxyUSB")), frozenset(("DoorGasket", "ProxyUSB"))}   # the door is open whenever a cable is in


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


def local_box(angle, x0, x1, y0, y1, z0, z1, rc=0.0):
    """Box in the frame of a radial direction: x outward along angle, y counter-clockwise across it.  rc rounds the
    four edges that run along x: the corners a cutter coming in from the side leaves."""
    b = Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))
    if rc > 0.01:
        b = b.makeFillet(min(rc, (y1 - y0) / 2 - 0.01, (z1 - z0) / 2 - 0.01),
                         [e for e in b.Edges if abs(e.tangentAt(e.FirstParameter).x) > 0.99])
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


def largest_solid(shape):
    return max(shape.Solids, key=lambda s: s.Volume)


def round_outer(shape, r, z):
    """Round the circular outer edge of the shell's back (a corner-rounding cutter)."""
    edges = [e for e in shape.Edges if abs(e.BoundBox.ZMin - z) < 1e-3 and abs(e.BoundBox.ZMax - z) < 1e-3
             and e.BoundBox.XLength > 2 * R_OUT - 0.5]
    try:
        return shape.makeFillet(r, edges)
    except Exception:
        print("outer edge: NOT rounded  <-- CHECK")
        return shape


def chamfer_outer(shape, size, z):
    """Chamfer the circular outer edge of a printed part at height z: these edges print on the bed, where a
    fillet would start as an unsupported 90 degree overhang (best effort)."""
    try:
        edges = [e for e in shape.Edges if abs(e.BoundBox.ZMin - z) < 1e-3 and abs(e.BoundBox.ZMax - z) < 1e-3
                 and e.BoundBox.XLength > 2 * R_OUT - 0.5]
        if edges:
            return shape.makeChamfer(size, edges)
    except Exception:
        pass
    return shape


def drill(base, axis, d, depth, tip=True):
    """A drilled hole from base along axis (unit vector), d across and depth deep to the full diameter, with a
    118 degree point beyond that."""
    h = Part.makeCylinder(d / 2, depth, base, axis)
    if tip:
        h = h.fuse(Part.makeCone(d / 2, 0, d * DRILL_TIP, base + axis * depth, axis))
    return h


def countersink(mouth, axis, d, sink):
    """45 degree countersink at a hole's mouth: axis points into the part; starts 1 mm outside the surface."""
    return Part.makeCone(d / 2 + sink + 1.0, d / 2, sink + 1.0, mouth - axis * 1.0, axis)


# --- SVG logo ---------------------------------------------------------------

def svg_path_points(d, step=0.05):
    """Flatten an SVG path (M L H V C S Q A Z, absolute or relative) to closed polylines."""
    toks = re.findall(r"[MmLlHhVvCcSsQqAaZz]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?", d)
    polys, cur = [], []
    st = {"i": 0}
    x = y = sx = sy = 0.0
    cmd, last_ctrl = None, None

    def num():
        st["i"] += 1
        return float(toks[st["i"] - 1])

    def cubic(p0, p1, p2, p3):
        n = max(4, int(math.dist(p0, p3) / step) + 4)
        for k in range(1, n + 1):
            t = k / n
            u = 1 - t
            cur.append((u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
                        u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]))

    def arc_to(p0, rx, ry, phi, fa, fs, p1):
        """SVG elliptical arc, by the endpoint-to-centre conversion of the SVG spec (F.6.5)."""
        rx, ry = abs(rx), abs(ry)
        if rx == 0 or ry == 0:
            cur.append(p1)
            return
        c, s = math.cos(math.radians(phi)), math.sin(math.radians(phi))
        dx, dy = (p0[0] - p1[0]) / 2, (p0[1] - p1[1]) / 2
        x1, y1 = c * dx + s * dy, -s * dx + c * dy
        lam = x1 * x1 / (rx * rx) + y1 * y1 / (ry * ry)
        if lam > 1:
            rx, ry = rx * math.sqrt(lam), ry * math.sqrt(lam)
        k = math.sqrt(max(0.0, (rx * rx * ry * ry - rx * rx * y1 * y1 - ry * ry * x1 * x1) /
                          (rx * rx * y1 * y1 + ry * ry * x1 * x1)))
        k = -k if fa == fs else k
        cx1, cy1 = k * rx * y1 / ry, -k * ry * x1 / rx
        cx, cy = c * cx1 - s * cy1 + (p0[0] + p1[0]) / 2, s * cx1 + c * cy1 + (p0[1] + p1[1]) / 2
        a0 = math.atan2((y1 - cy1) / ry, (x1 - cx1) / rx)
        da = math.atan2((-y1 - cy1) / ry, (-x1 - cx1) / rx) - a0
        if fs and da < 0:
            da += 2 * math.pi
        if not fs and da > 0:
            da -= 2 * math.pi
        n = max(3, int(abs(da) * max(rx, ry) / step) + 3)
        for j in range(1, n + 1):
            a = a0 + da * j / n
            cur.append((cx + c * rx * math.cos(a) - s * ry * math.sin(a), cy + s * rx * math.cos(a) + c * ry * math.sin(a)))
        cur[-1] = p1

    while st["i"] < len(toks):
        if toks[st["i"]].isalpha():
            cmd = toks[st["i"]]
            st["i"] += 1
            if cmd in "Zz":
                if cur:
                    polys.append(cur)
                cur, (x, y), last_ctrl = [], (sx, sy), None
                continue
        rel, C = cmd.islower(), cmd.upper()
        ox, oy = (x, y) if rel else (0.0, 0.0)
        if C == "M":
            if cur:
                polys.append(cur)
            x, y = ox + num(), oy + num()
            sx, sy, cur, cmd, last_ctrl = x, y, [(x, y)], ("l" if rel else "L"), None
        elif C == "L":
            x, y = ox + num(), oy + num()
            cur.append((x, y))
            last_ctrl = None
        elif C == "H":
            x = (x if rel else 0.0) + num()
            cur.append((x, y))
            last_ctrl = None
        elif C == "V":
            y = (y if rel else 0.0) + num()
            cur.append((x, y))
            last_ctrl = None
        elif C in "CS":
            p1 = (2 * x - last_ctrl[0], 2 * y - last_ctrl[1]) if C == "S" and last_ctrl else (
                (x, y) if C == "S" else (ox + num(), oy + num()))
            p2, p3 = (ox + num(), oy + num()), None
            p3 = (ox + num(), oy + num())
            cubic((x, y), p1, p2, p3)
            (x, y), last_ctrl = p3, p2
        elif C == "Q":
            q, p3 = (ox + num(), oy + num()), None
            p3 = (ox + num(), oy + num())
            cubic((x, y), ((x + 2 * q[0]) / 3, (y + 2 * q[1]) / 3), ((p3[0] + 2 * q[0]) / 3, (p3[1] + 2 * q[1]) / 3), p3)
            (x, y), last_ctrl = p3, None
        elif C == "A":
            rx, ry, phi = num(), num(), num()
            fa, fs = int(num()), int(num())
            p1 = (ox + num(), oy + num())
            arc_to((x, y), rx, ry, phi, fa, fs, p1)
            (x, y), last_ctrl = p1, None
    if cur:
        polys.append(cur)
    return polys


def _douglas_peucker(pts, tol):
    a, b = pts[0], pts[-1]
    length = math.dist(a, b) or 1e-12
    dmax, k = 0.0, 0
    for i in range(1, len(pts) - 1):
        p = pts[i]
        d = abs((b[0] - a[0]) * (a[1] - p[1]) - (a[0] - p[0]) * (b[1] - a[1])) / length
        if d > dmax:
            dmax, k = d, i
    if dmax <= tol:
        return [a, b]
    return _douglas_peucker(pts[:k + 1], tol)[:-1] + _douglas_peucker(pts[k:], tol)


def _inset(poly, d):
    """Mitred inward offset of a counter-clockwise polygon, vertex for vertex."""
    out = []
    for i in range(len(poly)):
        a, b, c = poly[i - 1], poly[i], poly[(i + 1) % len(poly)]
        l1, l2 = math.dist(a, b), math.dist(b, c)
        n1 = (-(b[1] - a[1]) / l1, (b[0] - a[0]) / l1)
        n2 = (-(c[1] - b[1]) / l2, (c[0] - b[0]) / l2)
        k = 1 + n1[0] * n2[0] + n1[1] * n2[1]
        out.append((b[0] + d * (n1[0] + n2[0]) / k, b[1] + d * (n1[1] + n2[1]) / k))
    return out


def logo_outline():
    """The OSHW logo as one counter-clockwise polygon in case XY about (0, 0), LOGO_W across, as seen from the back
    (mirrored in X, keyhole towards 6 o'clock), simplified to 0.02 mm and cleared of the tiny corner arcs that a
    V-bit cannot follow anyway (those would fold over in the inset)."""
    d = re.search(r'\sd="([^"]+)"', open(LOGO_SVG).read()).group(1)
    raw = max(svg_path_points(d), key=len)
    xs, ys = [p[0] for p in raw], [p[1] for p in raw]
    s, mx, my = LOGO_W / (max(xs) - min(xs)), (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    poly = [(-(px - mx) * s, -(py - my) * s) for px, py in raw]
    if math.dist(poly[0], poly[-1]) < 1e-2:
        poly = poly[:-1]
    i = max(range(len(poly)), key=lambda j: poly[j][0])
    poly = poly[i:] + poly[:i]
    k = max(range(len(poly)), key=lambda j: math.dist(poly[0], poly[j]))
    ring = _douglas_peucker(poly[:k + 1], 0.02)[:-1] + _douglas_peucker(poly[k:] + [poly[0]], 0.02)[:-1]
    poly = []
    for p in ring:
        if not poly or math.dist(poly[-1], p) > 1e-4:
            poly.append(p)
    if sum(poly[i - 1][0] * poly[i][1] - poly[i][0] * poly[i - 1][1] for i in range(len(poly))) < 0:
        poly.reverse()
    while True:                              # drop vertices whose edges the inset would turn round
        ins = _inset(poly, VCARVE_DEPTH)
        n = len(poly)
        flipped = [i for i in range(n) if
                   (poly[(i + 1) % n][0] - poly[i][0]) * (ins[(i + 1) % n][0] - ins[i][0]) +
                   (poly[(i + 1) % n][1] - poly[i][1]) * (ins[(i + 1) % n][1] - ins[i][1]) <=
                   0.25 * math.dist(poly[i], poly[(i + 1) % n]) * math.dist(ins[i], ins[(i + 1) % n])]
        if not flipped:
            return poly, ins
        i = flipped[0]
        j = i if math.dist(poly[i - 1], poly[i]) < math.dist(poly[(i + 1) % n], poly[(i + 2) % n]) else (i + 1) % n
        del poly[j]


def oshw_vcarve():
    """The V-carved logo as a solid to cut from the back: a ruled loft from the outline on the surface to the outline
    inset by the depth on the flat floor (90 degree bit: 45 degree walls), on a prism below the surface."""
    poly, ins = logo_outline()
    w0 = Part.makePolygon([V(CX + x, CY + y, Z_BOTTOM) for x, y in poly + poly[:1]])
    w1 = Part.makePolygon([V(CX + x, CY + y, Z_BOTTOM + VCARVE_DEPTH) for x, y in ins + ins[:1]])
    return Part.makeLoft([w0, w1], True, True).fuse(Part.Face(w0).extrude(V(0, 0, -1)))


def write_logo_template(path):
    """1:1 SVG of the logo as it is carved, seen from the back, for the engraver."""
    poly, ins = logo_outline()
    m = 6.0
    w = LOGO_W + 2 * m
    def d(p):
        return "M " + " L ".join("%.3f %.3f" % (x + w / 2, -y + w / 2 + 6) for x, y in p) + " Z"
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%.1fmm" height="%.1fmm" viewBox="0 0 %.1f %.1f">' % (
        w + 40, w + 14, w + 40, w + 14),
        '<text x="2" y="4" font-family="sans-serif" font-size="2.5">Finder Puck back: OSHW logo, 1:1, seen from the '
        "back, centred on the case axis, 12 o'clock up</text>",
        '<text x="2" y="%.1f" font-family="sans-serif" font-size="2.2">V-carve with a 90 deg bit to a %.2f mm flat depth '
        '(outer line on the surface, inner line the floor)</text>' % (w + 11, VCARVE_DEPTH),
        '<path d="%s" fill="none" stroke="black" stroke-width="0.08"/>' % d(poly),
        '<path d="%s" fill="none" stroke="grey" stroke-width="0.05"/>' % d(ins),
        '<path d="M %.1f %.1f h 10" stroke="black" stroke-width="0.2"/><text x="%.1f" y="%.1f" font-family="sans-serif" '
        'font-size="2.2">10 mm</text>' % (w + 4, w / 2 + 6, w + 15, w / 2 + 6.8),
        "</svg>"]
    with open(path, "w") as f:
        f.write("\n".join(out) + "\n")


# --- Antenna window ---------------------------------------------------------

def _flank_side(end, grow):
    """Half-space on the window's side of one of its flanks (end 0: the clockwise end, 1: the counter-clockwise
    end), moved grow mm away from the window along the flank's normal (negative: into the window).  The flank is a
    plane through the radial line at the window's floor corner, leaning FLANK degrees from the horizontal, so a
    cutter on a radial axis machines it and the plate's clamp squeezes the strip on it."""
    sgn = 1 if end else -1                                   # the window lies on -sgn*y of this end's frame
    tilt = -sgn * (90.0 - FLANK)
    b = Part.makeBox(200, 200, 120, V(-100, -200 if end else 0, Z_FLOOR - 60))
    b.rotate(V(0, 0, Z_FLOOR), V(1, 0, 0), tilt)
    a = math.radians(tilt)
    b.translate(V(0, sgn * math.cos(a), sgn * math.sin(a)) * grow)
    b.rotate(V(0, 0, 0), V(0, 0, 1), WINDOW[end])
    b.translate(V(CX, CY, 0))
    return b


def window_region(grow=0.0, z0=Z_FLOOR, z1=Z_SPLIT + 5):
    """Everything between the two flanks, above z0, from r 30 out past the wall."""
    a0, a1 = WINDOW[0] - 30, WINDOW[1] + 30
    region = arc(30.0, R_OUT + 1, a0, a1, z0, z1)
    return region.common(_flank_side(0, grow)).common(_flank_side(1, grow))


def make_window():
    """The plastic wall in the shell's notch: SEAL_GAP above the floor and off both flanks, flush with the rim at the
    top, with the USB-C opening and the door's pocket and lower groove in it, and two feet with pegs inside."""
    w = annulus(R_IN, R_OUT, Z_FLOOR + SEAL_GAP, Z_SPLIT).common(window_region(-SEAL_GAP, Z_FLOOR - 1))
    for a in WINDOW_FEET:
        half = deg(FOOT_W / 2, R_IN)
        w = w.fuse([arc(FOOT_R0, R_IN + 0.01, a - half, a + half, Z_FLOOR, Z_FLOOR + FOOT_H),
                    cyl(PEG_D / 2, Z_FLOOR - PEG_L, Z_FLOOR + 0.01, *at(a, PEG_R))])
    w = w.cut(radial_box(F["usb"]["angle"], R_BOARD - 1.0, R_OUT + 2, USB_W, USB_Z0, USB_Z1))
    w = w.cut(door_pocket())
    return largest_solid(w.removeSplitter())


def make_window_gasket():
    """The foam strip under the window, on the shell's notch floor and up both flanks, drawn squeezed: what is left
    of the wall's band between the shell and the window."""
    band = annulus(R_IN + SEAL_INSET, R_OUT - SEAL_INSET, Z_FLOOR, Z_SPLIT).common(window_region(0.0))
    band = band.cut(window_region(-SEAL_GAP, Z_FLOOR + SEAL_GAP))
    return band.removeSplitter()


# --- Parts ------------------------------------------------------------------

def bay_cavity():
    """The battery bay below the board, a bore smaller than the one the board sits in: its wall runs round the bolt
    bosses and the lanyard boss with BOSS_FILLET inside corners."""
    cav = cyl(R_BAY, Z_FLOOR, -T_BOARD + 0.01)
    for x, y in BOLTS["points"]:
        cav = cav.cut(cyl(SHELL_BOSS_R, Z_FLOOR - 1, 1, *pt(x, y)))
    cav = cav.cut(cyl(LANYARD_BOSS, Z_FLOOR - 1, LANYARD_TOP, *at(LANYARD_ANGLE, LANYARD_R)))
    cav = cav.removeSplitter()
    corners = [e for e in cav.Edges if e.BoundBox.ZLength > 1.0 and e.BoundBox.XLength < 1e-3 and e.BoundBox.YLength < 1e-3]
    try:
        f = cav.makeFillet(BOSS_FILLET, corners)
        if f.isValid():
            return f
    except Exception:
        pass
    print("bay: %d inside corners NOT rounded  <-- CHECK" % len(corners))
    return cav


def make_shell():
    """Machined from 6061: from the top (bores, bay, bosses, tapped holes, notch, peg holes), from the back (outer
    radius, lanyard hole, logo) and from the side (switch slot, scallop, lanyard hole, tether pin hole, flanks)."""
    body = round_outer(cyl(R_OUT, Z_BOTTOM, Z_SPLIT), BOTTOM_R, Z_BOTTOM)
    body = body.cut(cyl(R_IN, -T_BOARD, Z_SPLIT + 1))
    body = body.cut(bay_cavity())
    body = body.cut(window_region(0.0))
    for x, y in BOLTS["points"]:                  # the boss in the window stands on its own
        body = body.fuse(cyl(SHELL_BOSS_R, Z_FLOOR - 0.01, -T_BOARD, *pt(x, y)))
    down = V(0, 0, -1)
    for x, y in BOLTS["points"]:
        px, py = pt(x, y)
        top = V(px, py, -T_BOARD)
        body = body.cut(cyl(BOLT_D / 2, -T_BOARD - TAP_DEPTH, -T_BOARD + 1, px, py))       # the thread, at its nominal size
        body = body.cut(drill(top, down, TAP_DRILL, DRILL_DEPTH))
        body = body.cut(countersink(top, down, BOLT_D, TAP_SINK))
    # Lanyard: up from the back and in from the side, meeting in the boss.
    lx, ly = at(LANYARD_ANGLE, LANYARD_R)
    up, mouth = V(0, 0, 1), V(lx, ly, Z_BOTTOM)
    body = body.cut(drill(mouth - up, up, LANYARD_D, LANYARD_Z + LANYARD_D / 2 - Z_BOTTOM + 1))
    body = body.cut(countersink(mouth, up, LANYARD_D, LANYARD_SINK))
    inward = V(-math.cos(math.radians(LANYARD_ANGLE)), -math.sin(math.radians(LANYARD_ANGLE)), 0)
    side = V(*at(LANYARD_ANGLE, R_OUT), LANYARD_Z)
    body = body.cut(drill(side - inward, inward, LANYARD_D, R_OUT - (LANYARD_R - LANYARD_D / 2) + 1))
    body = body.cut(countersink(side, inward, LANYARD_D, LANYARD_SINK))
    # Power switch knob, with a finger scallop on the outside so the knob can be reached.  Both stay below
    # the rim, so the seal is unbroken here.
    a = F["power_switch"]["angle"]
    body = body.cut(local_box(a, R_BOARD - 2.0, R_OUT + 2, -SWITCH_W / 2, SWITCH_W / 2, SWITCH_Z0, SWITCH_Z1, SWITCH_RC))
    body = body.cut(local_box(a, R_OUT - SCALLOP_D, R_OUT + 2, -SCALLOP_W / 2, SCALLOP_W / 2, SCALLOP_Z0, SCALLOP_Z1,
                              SCALLOP_RC))
    body = body.cut(radial_pin(a, R_OUT - SCALLOP_D - PLUG_PIN_L + 0.4, R_OUT, PLUG_PIN_D, SW_PIN_Z))
    # Battery lead: the board is notched here; the bay's wall gets a slot the cables stand in, floor to rim.
    angle, width, _ = BATT_NOTCH
    slot = Part.makeBox(R_IN + 0.3 - (R_BAY - 0.5), width, 2.0 - Z_FLOOR, V(R_BAY - 0.5, -width / 2, Z_FLOOR))
    slot = slot.makeFillet(1.5, [e for e in slot.Edges if abs(e.tangentAt(e.FirstParameter).z) > 0.99
                                 and e.BoundBox.XMin > R_BAY])
    slot.rotate(V(0, 0, 0), V(0, 0, 1), angle)
    slot.translate(V(CX, CY, 0))
    body = body.cut(slot)
    # Motor pocket: a shallow recess in the floor.  Holes for the window's pegs.
    mx, my = pt(*MOTOR_POCKET)
    body = body.cut(cyl(F["motor"]["dia"] / 2 + 0.3, Z_FLOOR - 0.6, Z_FLOOR + 0.01, mx, my))
    for a in WINDOW_FEET:
        body = body.cut(cyl(PEG_D / 2 + 0.05, Z_FLOOR - PEG_L - 0.2, Z_FLOOR + 0.01, *at(a, PEG_R)))
    # The OSHW logo on the back.
    body = body.cut(oshw_vcarve())
    return largest_solid(body.removeSplitter())


def make_plate():
    body = cyl(R_OUT, Z_SPLIT + PLATE_GAP, Z_FACE)
    body = chamfer_outer(body, 1.0, Z_FACE)
    # Hollow: the skirt over the rim seal, then the inner wall up to the skin.
    body = body.cut(cyl(R_IN, Z_SPLIT - 1, Z_SKIN))
    # Bosses down to the PCB top, bolt bores and counterbores.
    for x, y in BOLTS["points"]:
        px, py = pt(x, y)
        body = body.fuse(cyl(BOSS_R, 0.0, Z_SKIN + 0.01, px, py))
    for x, y in BOLTS["points"]:
        px, py = pt(x, y)
        body = body.cut(cyl(BOLT_CLEAR / 2, -1, Z_FACE + 1, px, py))
        body = body.cut(cyl(CBORE_D / 2, Z_FACE - (HEAD_H - HEAD_PROUD) - WASHER_T, Z_FACE + 1, px, py))
    # Bezel: opening through the face and the pocket for its flange and the lid gasket on it.
    body = body.cut(cyl(R_OPENING, Z_SKIN - 1, Z_FACE + 1))
    body = body.cut(annulus(R_OPENING - 0.5, R_FLANGE1 + LID_INSET, Z_SKIN - 1, Z_POCKET).fuse(
        flange_extras(LID_INSET, Z_SKIN - 1, Z_POCKET)))
    # GPS sky window: the skin thins to a cover over the patch (or opens, if GPS_WINDOW == "open").
    if GPS_WINDOW == "open":
        body = body.cut(board_rect(*GPS_WIN, Z_SKIN - 1, Z_FACE + 1, GPS_WIN_R))
    else:
        body = body.cut(board_rect(*GPS_WIN, Z_SKIN - 1, Z_FACE - GPS_COVER, GPS_WIN_R))
    # 12 o'clock index: blind hole for the orange stub.
    body = body.cut(cyl(INDEX_D / 2, Z_FACE - INDEX_DEPTH, Z_FACE + 1, CX, CY + INDEX_R))
    # Button bore through the skin (the bezel's sleeve continues it), the charge-LED pipe's bore, and a dimple
    # that marks the ON end of the switch slot.
    bx, by = pt(*BUTTON["center"])
    body = body.cut(cyl(CAP_BORE / 2, Z_SKIN - 1, Z_FACE + 1, bx, by))
    dx, dy = pt(*F["charge_led"]["center"])
    body = body.cut(cyl(LED_PIPE_BORE / 2, Z_SKIN - 1, Z_FACE + 1, dx, dy))
    ox, oy = at(F["power_switch"]["angle"] - 6, R_IN - 1.9)
    body = body.cut(cyl(0.6, Z_FACE - 0.3, Z_FACE + 1, ox, oy))
    # The USB-C opening continues up from the window through the skirt, with the door's pocket and upper groove
    # round it.
    body = body.cut(radial_box(F["usb"]["angle"], R_BOARD - 1.0, R_OUT + 2, USB_W, USB_Z0, USB_Z1))
    body = body.cut(door_pocket())
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


def flange_extras(grow, z0, z1):
    """The bezel flange's lobe round the button and its tab out to the charge LED, grown by grow (the plate's
    pocket) or shrunk (the lid gasket)."""
    bx, by = pt(*BUTTON["center"])
    dx, dy = pt(*F["charge_led"]["center"])
    a = math.degrees(math.atan2(dy - CY, dx - CX))
    tab = radial_box(a, R_FLANGE1 - 1.0, math.hypot(dx - CX, dy - CY), LED_TAB_W + 2 * grow, z0, z1)
    return cyl(BUTTON_LOBE + grow, z0, z1, bx, by).fuse([tab, cyl(LED_TAB_R + grow, z0, z1, dx, dy)])


def make_bezel():
    """Translucent bezel: crystal seat, flared lip, clamp flange, skirt around the ring, light pipes, and the
    button bore's sleeve."""
    body = annulus(R_BEZEL_IN, R_BEZEL1, Z_CRYSTAL, Z_LIP0)
    lip = annulus(WINDOW_D / 2, R_LIP1, Z_LIP0, Z_FACE + LIP_PROUD)
    flange = annulus(R_BEZEL1 - 0.01, R_FLANGE1, Z_FLANGE0, Z_FLANGE1).fuse(flange_extras(0.0, Z_FLANGE0, Z_FLANGE1))
    skirt = annulus(R_SKIRT0, R_BEZEL1, Z_SKIRT0, Z_CRYSTAL + 0.01)
    for a0, a1 in WALL_GAPS:
        if a0 != 145:   # the panel chin passes under the skirt at 6 o'clock
            skirt = skirt.cut(sector(R_SKIRT0 - 0.5, R_BEZEL1 + 0.5, a0, a1, Z_SKIRT0 - 1, Z_CRYSTAL + 1))
    bezel = body.fuse([lip, flange, skirt])
    for x, y in LEDS["points"]:
        px, py = pt(x, y)
        bezel = bezel.fuse(cyl(PIPE_D / 2, PIPE_Z0, Z_FLANGE0 + 0.01, px, py))
    # Charge-LED pipe: up through the skin to the face, thicker below the flange.
    dx, dy = pt(*F["charge_led"]["center"])
    bezel = bezel.fuse([cyl(LED_PIPE_D / 2, Z_FLANGE1 - 0.01, Z_FACE, dx, dy),
                        cyl(LED_FOOT_D / 2, LED_FOOT_Z0, Z_FLANGE0 + 0.01, dx, dy)])
    # Over the GPS module (up to 6.8 mm tall, edge at r 19.2 at its widest) nothing of the bezel beyond r 18.7
    # comes below the flange (Z 7.0): no seat wall or skirt.
    bezel = bezel.cut(sector(R_BEZEL_GPS, R_FLANGE1 + 1, GPS_CLEAR_ARC[0], GPS_CLEAR_ARC[1], Z_SKIRT0 - 1, Z_FLANGE0))
    # The button bore down a sleeve under the lobe: the O-ring's bore, with a lead-in at its mouth.
    bx, by = pt(*BUTTON["center"])
    bezel = bezel.fuse(cyl(SLEEVE_R, SLEEVE_Z0, Z_FLANGE0 + 0.01, bx, by))
    bezel = bezel.cut(cyl(CAP_BORE / 2, SLEEVE_Z0 - 1, Z_FACE + 1, bx, by))
    bezel = bezel.cut(Part.makeCone(CAP_BORE / 2 + SLEEVE_LEAD, CAP_BORE / 2, SLEEVE_LEAD, V(bx, by, SLEEVE_Z0)))
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


def make_index():
    return cyl(1.75 / 2, Z_FACE - INDEX_DEPTH, Z_FACE, CX, CY + INDEX_R)


def make_washer(px, py):
    z1 = Z_FACE - (HEAD_H - HEAD_PROUD)
    return annulus(WASHER_ID / 2, WASHER_D / 2, z1 - WASHER_T, z1, px, py)


def make_seal():
    """The foam seal on the rim of the shell and the window, drawn squeezed to the rim gap.  At the door it is
    trimmed to the pocket floor and the land, and it stops at the USB-C opening's sides."""
    seal = annulus(R_IN + SEAL_INSET, R_OUT - SEAL_INSET, Z_SPLIT, Z_SPLIT + PLATE_GAP)
    seal = seal.cut(door_pocket())
    return seal.cut(radial_box(F["usb"]["angle"], R_BOARD - 1.0, R_OUT + 2, USB_W, Z_SPLIT - 1, Z_SPLIT + 2))


def make_crystal_gasket():
    """The die-cut foam ring between the glass and the bezel lip, drawn squeezed."""
    return annulus(*CRYSTAL_GASKET_R, Z_CRYSTAL_TOP, Z_LIP0)


def make_lid_gasket():
    """The die-cut foam sheet on the bezel flange, drawn squeezed to the plate's pocket ceiling: a ring round the
    opening, a lobe round the button bore (open to the opening across the bore, so no thin bridge is left), and a
    tab round the charge-LED pipe."""
    z0, z1 = Z_FLANGE1, Z_POCKET
    g = cyl(R_FLANGE1 - LID_INSET, z0, z1).fuse(flange_extras(-LID_INSET, z0, z1))
    g = g.cut(cyl(R_OPENING + LID_INSET, z0 - 1, z1 + 1))
    bx, by = pt(*BUTTON["center"])
    g = g.cut(cyl(LOBE_HOLE, z0 - 1, z1 + 1, bx, by))
    g = g.cut(radial_box(math.degrees(math.atan2(by - CY, bx - CX)), R_OPENING, math.hypot(bx - CX, by - CY),
                         2 * LOBE_HOLE, z0 - 1, z1 + 1))
    dx, dy = pt(*F["charge_led"]["center"])
    return g.cut(cyl(LED_PIPE_BORE / 2 + 0.2, z0 - 1, z1 + 1, dx, dy)).removeSplitter()


def make_oring():
    """The button's O-ring, drawn squeezed: groove bottom to the bore, at the bottom of the groove."""
    bx, by = pt(*BUTTON["center"])
    rg, g0, _ = ORING_GROOVE
    return annulus(rg, CAP_BORE / 2, g0, g0 + math.pi / 4 * ORING_CS ** 2 / (CAP_BORE / 2 - rg), bx, by)


def arc(r0, r1, a0, a1, z0, z1, steps=None):
    """Annular sector with true circular faces (the door's parts slide on each other, so polygon chords
    would leave slivers between them)."""
    c = Part.makeCylinder(r1, z1 - z0, V(CX, CY, z0), V(0, 0, 1), a1 - a0)
    if r0 > 0:
        c = c.cut(Part.makeCylinder(r0, z1 - z0 + 2, V(CX, CY, z0 - 1)))
    c.rotate(V(CX, CY, 0), V(0, 0, 1), a0)
    return c


def deg(mm, r=R_OUT):
    return math.degrees(mm / r)


def door_extent():
    """Angular half-widths at the wall: the land round the opening, the gasket, the door."""
    land = deg(USB_W / 2 + DOOR_LAND_W)
    door = deg(USB_W / 2 + DOOR_LAND_W + DOOR_EDGE)
    return land, door


def door_z():
    """Z ranges: land (and gasket), door body, pocket."""
    land = (USB_Z0 - DOOR_LAND_W, USB_Z1 + DOOR_LAND_W)
    door = (land[0] - 0.2, land[1] + 0.2)
    return land, door, (door[0] - DOOR_CLEAR, door[1] + DOOR_CLEAR)


def door_land():
    """The raised sealing frame round the opening, with a lead-in step at its two ends."""
    a = F["usb"]["angle"]
    land_h, _ = door_extent()
    (z0, z1), _, _ = door_z()
    step = deg(DOOR_LEAD)
    frame = arc(DOOR_FLOOR - 0.5, DOOR_LAND, a - land_h + step, a + land_h - step, z0, z1, steps=40)
    frame = frame.fuse(arc(DOOR_FLOOR - 0.5, DOOR_FLOOR + 0.12, a - land_h, a + land_h, z0, z1, steps=40))
    return frame.cut(radial_box(a, R_BOARD - 1.0, R_OUT + 2, USB_W, USB_Z0, USB_Z1))


def door_pocket():
    """What the window and the plate lose for the door: the pocket over its whole travel and the two grooves,
    less the sealing land."""
    a = F["usb"]["angle"]
    _, door_h = door_extent()
    _, _, (pz0, pz1) = door_z()
    a0, a1 = a - door_h - DOOR_TRAVEL - deg(DOOR_CLEAR), a + door_h + deg(DOOR_CLEAR)
    g0, g1, gh = DOOR_GROOVE
    pocket = arc(DOOR_FLOOR, R_OUT + 1, a0, a1, pz0, pz1, steps=80)
    pocket = pocket.fuse([arc(g0, g1, a0, a1, pz1 - 0.01, pz1 + gh, steps=80),
                          arc(g0, g1, a0, a1, pz0 - gh, pz0 + 0.01, steps=80)])
    return pocket.cut(door_land())


def make_door(travel=0.0):
    """The USB-C door, closed (travel 0) or slid open by travel degrees."""
    a = F["usb"]["angle"] - travel
    _, door_h = door_extent()
    _, (z0, z1), _ = door_z()
    r_t, h_t = DOOR_TONGUE
    body = arc(DOOR_IN, DOOR_IN + DOOR_T, a - door_h, a + door_h, z0, z1, steps=40)
    tongues = [arc(r_t, DOOR_IN + 0.01, a - door_h, a + door_h, z1 - 0.01, z1 + h_t, steps=40),
               arc(r_t, DOOR_IN + 0.01, a - door_h, a + door_h, z0 - h_t, z0 + 0.01, steps=40)]
    ribs = []
    gh, n = DOOR_GRIP
    for k in range(n):                               # vertical grip ribs, 2 mm apart, in the middle third
        ak = a + deg(2.0 * (k - (n - 1) / 2))
        ribs.append(arc(DOOR_IN + DOOR_T - 0.01, DOOR_IN + DOOR_T + gh, ak - deg(0.3), ak + deg(0.3),
                           z0 + 2.0, z1 - 2.0, steps=2))
    return body.fuse(tongues + ribs).removeSplitter()


def make_door_gasket(travel=0.0):
    """The die-cut foam frame on the door's inside, drawn squeezed onto the land (closed)."""
    a = F["usb"]["angle"] - travel
    land_h, _ = door_extent()
    (z0, z1), _, _ = door_z()
    r0 = DOOR_LAND if travel == 0 else DOOR_IN - DOOR_GASKET
    frame = arc(r0, DOOR_IN, a - land_h, a + land_h, z0, z1, steps=40)
    hole = arc(r0 - 1, DOOR_IN + 1, a - deg(USB_W / 2 + 0.1), a + deg(USB_W / 2 + 0.1), USB_Z0 - 0.1, USB_Z1 + 0.1)
    return frame.cut(hole)


def make_switch_plug():
    """TPU cover for the switch slot, sitting in the finger scallop: body in the slot (clear of the knob), a
    flange on the scallop's flat floor, a ridge for a fingernail, and a strap to a pin below the slot."""
    a, s = F["power_switch"]["angle"], PLUG_SQUEEZE
    x_floor = R_OUT - SCALLOP_D
    w2 = SWITCH_W / 2
    fw = SCALLOP_W / 2 - 0.2
    xo = x_floor + PLUG_FLANGE_T - 0.1
    body = local_box(a, SW_PLUG_IN, x_floor + 0.01, -w2 - s, w2 + s, SWITCH_Z0 - s, SWITCH_Z1 + s, SWITCH_RC + s)
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


def write_gasket_template(path):
    """1:1 SVG cutting template for the die-cut gaskets, seen from the face: the lid gasket, the crystal ring and
    the door frame (flat; it bends round the door when stuck on).  Print at 100 % and check the 50 mm bar."""
    paths, x_off = [], 0.0

    def outline(face, dx, dy):
        d = []
        for w in face.Wires:
            pts = w.discretize(Deflection=0.01)
            d.append("M " + " L ".join("%.3f %.3f" % (p.x - CX + dx, -(p.y - CY) + dy) for p in pts) + " Z")
        return " ".join(d)

    def top(shape):
        z = shape.BoundBox.ZMax
        return [f for f in shape.Faces if abs(f.BoundBox.ZMin - z) < 1e-6 and abs(f.BoundBox.ZMax - z) < 1e-6][0]

    lid = make_lid_gasket()
    bb = lid.BoundBox
    x_lid, y_lid = 10 - (bb.XMin - CX), 24 + (bb.YMax - CY)
    paths.append(("lid gasket", outline(top(lid), x_lid, y_lid), x_lid + 22, y_lid + 26))
    r = CRYSTAL_GASKET_R[1]
    x_cr, y_cr = x_lid + (bb.XMax - CX) + 10 + r, y_lid
    paths.append(("crystal gasket", outline(top(make_crystal_gasket()), x_cr, y_cr), x_cr, y_cr + r + 6))
    w, h = USB_W + 2 * DOOR_LAND_W, (USB_Z1 - USB_Z0) + 2 * DOOR_LAND_W
    hw, hh = USB_W + 0.2, (USB_Z1 - USB_Z0) + 0.2
    x0, y0 = x_cr + r + 10, y_cr - h / 2
    d = "M %.3f %.3f h %.3f v %.3f h %.3f Z " % (x0, y0, w, h, -w)
    d += "M %.3f %.3f h %.3f v %.3f h %.3f Z" % (x0 + (w - hw) / 2, y0 + (h - hh) / 2, hw, hh, -hw)
    paths.append(("door gasket", d, x0 + w / 2, y0 + h + 6))
    width, height = x0 + w + 10, y_lid + (bb.YMax - bb.YMin) / 2 + 16
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%.1fmm" height="%.1fmm" viewBox="0 0 %.1f %.1f">' % (
        width, height, width, height),
        '<text x="10" y="7" font-family="sans-serif" font-size="3.5">Finder Puck gaskets, 1:1, seen from the face</text>',
        '<text x="10" y="11.5" font-family="sans-serif" font-size="3">Lid and crystal: 0.3 mm closed-cell foam; '
        'door: 0.5 mm</text>',
        '<path d="M 10 16 h 50" stroke="black" stroke-width="0.3"/>'
        '<text x="62" y="17" font-family="sans-serif" font-size="3">50 mm</text>']
    for name, d, tx, ty in paths:
        out.append('<path d="%s" fill="none" stroke="black" stroke-width="0.1" fill-rule="evenodd"/>' % d)
        out.append('<text x="%.1f" y="%.1f" font-family="sans-serif" font-size="3" text-anchor="middle">%s</text>' % (
            tx, ty, name))
    out.append("</svg>")
    with open(path, "w") as f:
        f.write("\n".join(out) + "\n")


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
    if GPS_WINDOW == "open":
        print("GPS_WINDOW = open: the sky window is a hole, so the case is NOT sealed (IP55 needs the skin)  <-- CHECK")
    doc = FreeCAD.newDocument("finder_puck_case")
    board = Part.read(os.path.join(MECH, NAME + ".step"))
    board.translate(V(0, 0, -T_BOARD))     # KiCad exports the PCB with its underside at Z 0
    shapes = {
        "Board": board,
        "Panel": make_panel(), "Crystal": make_crystal(), "Battery": make_battery(),
        "Motor": make_motor(), "Antenna": make_antenna(),
        "Shell": make_shell(), "Window": make_window(), "Plate": make_plate(), "Ring": make_ring(), "Bezel": make_bezel(),
        "Cap": make_cap(), "Door": make_door(), "SwitchPlug": make_switch_plug(),
        "Index": make_index(), "Seal": make_seal(), "WindowGasket": make_window_gasket(), "CrystalGasket": make_crystal_gasket(), "LidGasket": make_lid_gasket(), "ORing": make_oring(), "DoorGasket": make_door_gasket(),
        "ProxyPlug": make_ph_plug(), "ProxyCables": make_notch_cables(), "ProxyFold": make_fpc_fold(),
        "ProxyUSB": make_usb_overmold(), "ProxyGPS": make_gps_envelope(),
    }
    for i, (x, y) in enumerate(BOLTS["points"]):
        px, py = pt(x, y)
        shapes["Bolt%d" % (i + 1)] = make_bolt(px, py)
        shapes["Washer%d" % (i + 1)] = make_washer(px, py)
    objs = {}
    for name, shape in shapes.items():
        o = doc.addObject("Part::Feature", name)
        o.Shape = shape
        objs[name] = o

    # Interference: the made parts (the machined shell, the printed rest) against everything they must clear.
    printed = ("Shell", "Window", "Plate", "Ring", "Bezel", "Cap", "Door", "SwitchPlug")
    hardware = tuple(n for n in shapes if n.startswith(("Bolt", "Washer"))) + ("Index", "Seal", "WindowGasket", "ORing",
                                                                              "DoorGasket", "CrystalGasket", "LidGasket")
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
            if flag or not other.startswith(("Bolt", "Washer")):
                print("overlap %-10s vs %-11s %8.3f mm^3%s" % (part, other, vol, flag))
            near = min_distance(objs[part].Shape, objs[other].Shape, REPORT_GAP)
            if near:
                kind = other.rstrip("0123456789")      # Bolt1..4 and Washer1..4 collapse into one line each
                key = (part, kind, round(near[0], 3))
                close.setdefault(key, [near[1], 0])[1] += 1
    # Clearances: every printed-vs-other pair closer than REPORT_GAP, tightest first.  Contacts are the
    # designed seats (board on the bay's step, panel on ring, crystal under lip, flange under skin, bosses on the PCB).
    for (part, kind, d), (p, n) in sorted(close.items(), key=lambda kv: kv[0][2]):
        print("gap %-10s vs %-11s %6.3f mm at (%6.1f, %6.1f, %5.1f)%s" % (
            part, kind + ("x%d" % n if n > 1 else ""), d, p.x, p.y, p.z, "  contact" if d < 1e-3 else ""))
    # The door slid open: it must clear everything in its pocket and uncover the plug overmold.
    opened = make_door(DOOR_TRAVEL).fuse(make_door_gasket(DOOR_TRAVEL))
    for other in ("Window", "Plate", "Seal", "ProxyUSB"):
        common = opened.common(objs[other].Shape)
        vol = common.Volume if not common.isNull() else 0.0
        flag = "" if vol < 0.001 else "  <-- CHECK"
        bad += 1 if flag else 0
        near = min_distance(opened, objs[other].Shape, 1.0)
        print("door open vs %-9s %8.3f mm^3, nearest %s%s" % (other, vol, "%.3f mm" % near[0] if near else "> 1 mm", flag))
    # Radio: how close the aluminium comes to the antenna and to the GPS module (at its limits), and how much of the
    # window gasket and rim seal there is to cut.
    for name in ("Antenna", "ProxyGPS"):
        near = min_distance(objs["Shell"].Shape, objs[name].Shape, 20.0)
        print("rf: aluminium to %-8s %s" % (name.replace("Proxy", ""), "%.1f mm at (%.1f, %.1f, %.1f)" % (
            near[0], near[1].x, near[1].y, near[1].z) if near else "> 20 mm"))
    wg = objs["WindowGasket"].Shape
    r_mid = (R_IN + R_OUT) / 2
    print("window gasket: %.0f mm of 1.0 mm foam strip, %.1f mm wide, along the notch floor and up both flanks "
          "(%d solid(s), %.1f mm^3 squeezed)" % (
              math.radians(WINDOW[1] - WINDOW[0]) * r_mid + 2 * (Z_SPLIT - Z_FLOOR) / math.sin(math.radians(FLANK)),
              R_OUT - R_IN - 2 * SEAL_INSET, len(wg.Solids), wg.Volume))
    print("case: %.1f mm across, %.1f mm tall (face at Z %.1f, bottom at Z %.1f); %d interference(s); "
          "%d pair(s) closer than %.1f mm" % (
              2 * R_OUT, Z_FACE - Z_BOTTOM, Z_FACE, Z_BOTTOM, bad, len(close), REPORT_GAP))

    out = os.path.join(CASE, NAME + "_case.FCStd")
    if os.path.exists(out):
        os.remove(out)
    doc.saveAs(out)
    # 0.01 mm deflection, so fine fillets mesh cleanly; every STL must come out closed and free of self-intersections.
    for name in printed:
        mesh = MeshPart.meshFromShape(Shape=objs[name].Shape, LinearDeflection=0.01,
                                      AngularDeflection=math.radians(8), Relative=False)
        mesh.write(os.path.join(CASE, "%s_%s.stl" % (NAME, name.lower())))
        crossings = len(mesh.getSelfIntersections())
        flag = "" if mesh.isSolid() and not crossings else "  <-- CHECK"
        print("mesh %-10s %6d facets, %s, %d self-intersection(s)%s" % (
            name, mesh.CountFacets, "closed" if mesh.isSolid() else "NOT closed", crossings, flag))
    Import.export([objs[n] for n in printed], os.path.join(CASE, NAME + "_case.step"))
    write_gasket_template(os.path.join(CASE, NAME + "_gaskets.svg"))
    write_logo_template(os.path.join(CASE, NAME + "_logo_vcarve.svg"))
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
