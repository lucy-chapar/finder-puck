"""
Board half of the finder puck generator: placement, outline, planes, routing
with Freerouting, zone fill, DRC and fabrication outputs.

Called from generate_puck.py; run that script rather than this one.
"""

import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [_HERE]
import kicad_helpers as gk  # noqa: E402
import generate_puck as gp  # noqa: E402

OX, OY = 100.0, 100.0
RADIUS = 36.0                   # round board, 72 mm across
CX = CY = RADIUS                # centre, in board coordinates
BOARD_W = BOARD_H = 2 * RADIUS  # bounding box
THICKNESS = 1.6

FREEROUTING = os.environ.get("FREEROUTING_JAR", "")

# Clock positions on the face: 12 o'clock is board y = 0 (away from the body), 3 o'clock is +x.
# Angles below are in degrees, 0 at 3 o'clock, counter-clockwise on the face (90 = 12 o'clock).
import math


def at_angle(angle, r):
    a = math.radians(angle)
    return CX + r * math.cos(a), CY - r * math.sin(a)


# 1.28" round panel (TFT1281 / ZJY128R-IG01): a 35.6 mm backlight circle with a 2.5 mm chin
# on the FPC side (38.1 mm overall), 1.5 mm thick, active circle 32.4 mm.  The panel rests on
# a ring ledge PANEL_LEDGE_Z above the board so the ESP32 can (3.1 mm) fits under it; the FPC
# exits at 6 o'clock, folds under the glass and comes down to J3 on the board.
PANEL = {
    "center": [CX, CY], "outline_dia": 35.6, "glass_dia": 35.2, "active_dia": 32.4,
    "chin_width": 14.0, "chin_reach": 56.3, "thickness": 1.5, "fpc_angle": 270,
    "ledge_z": 4.0, "fold_bump": 0.45, "under_panel_r": 17.8, "max_height_under": 3.5,
    "crystal_dia": 37.5, "crystal_thickness": 1.0, "window_dia": 34.8,
}
RING_WALL = (17.9, 19.0)                     # the panel ring's wall stands on the board here (0.85 mm printed)
RING_WALL_GAPS = ((145, 215), (243, 297))    # ESP32 body, and the FPC/chin at 6 o'clock
BOLT_R, BOLT_ANGLES = 31.5, (45, 135, 225, 315)
BOLT_HOLE, BOLT_PAD, BOSS_R = 2.8, 5.4, 4.0   # M2.5 through the PCB (0.15 radial play); 8 mm case bosses
# Notches in the board edge (angle, width, depth): the battery lead and the antenna pigtail come up through the first.
NOTCHES = [(304, 6.0, 1.5)]      # two 28 AWG battery wires and the U.FL pigtail side by side
LED_R, LED_ANGLES = 22.0, (225, 135, 45, 315)  # chain order LED1..LED4, clockwise from lower-left
FPC_TAB = (29.8, 50.6, 42.2, 56.3)          # folded 12 mm FPC and panel chin lie flat here: no parts
MOTOR_POCKET = (62.0, 27.0)                  # coin motor on the shell floor (3 o'clock crescent)

# ref: (x, y, rotation) in mm from the top-left of the board's bounding box.
PLACEMENT = {
    # Modules: GPS patch at 12 o'clock under an open sky window; ESP32 radial at 9 o'clock
    # with its PCB antenna on the rim; LoRa module under the panel; USB-C mouth at 3 o'clock.
    "U3": (36.0, 9.0, 180),   # UART pads toward the ESP32 side; corners 0.4 mm inside the edge
    "U1": (14.25, 36.0, 90),
    "U2": (40.5, 36.0, 0),
    "J1": (68.15, 36.0, 90),
    "J4": (56.0, 47.5, 0),    # outside the ring wall; rotation chosen so pad 1 faces U2's ANT pad
    # Panel FPC pads 3.6 mm inboard of the glass chin; the face button at 6 o'clock.
    "J3": (36.0, 52.0, 0),
    "SW1": (36.0, 64.0, 0),
    # Battery lead out at about 290 degrees, power switch knob at 245, motor connector at 2 o'clock
    # next to its lead hole; the motor itself sits on the shell floor.
    "J2": (47.0, 60.5, 0),    # 5.6 mm from the wall so the PH plug fits in front of it
    "SW2": (21.9, 66.2, -25), # as far out as the edge clearance allows: the knob reaches the wall
    "J5": (63.5, 22.5, 0),
    "H5": (56.5, 23.0, 0),
    # Power FET and its pull-up between the radio and the USB-C; the switch only drives the gate.
    "Q3": (58.0, 37.5, 0), "R22": (58.0, 34.8, 0),
    # Beacon LEDs on the diagonals just outside the diffuser ring wall.
    "LED1": at_angle(LED_ANGLES[0], LED_R) + (0,),
    "LED2": at_angle(LED_ANGLES[1], LED_R) + (0,),
    "LED3": at_angle(LED_ANGLES[2], LED_R) + (0,),
    "LED4": at_angle(LED_ANGLES[3], LED_R) + (0,),
    # Compass away from the motor, LED chain and power parts; accelerometer under the panel.
    "U5": (20.5, 11.5, 0), "C12": (23.5, 11.5, 0), "C13": (18.0, 8.5, 0),
    "U4": (28.0, 48.5, 0), "C11": (31.0, 47.0, 0),
    "R3": (31.0, 49.5, 0), "R4": (33.0, 49.5, 0),
    # Through-PCB bolts.
    "H1": at_angle(45, BOLT_R) + (0,), "H2": at_angle(135, BOLT_R) + (0,),
    "H3": at_angle(225, BOLT_R) + (0,), "H4": at_angle(315, BOLT_R) + (0,),
    # Charger, regulator and USB parts in the lower-right pocket.
    "U6": (61.0, 47.5, 0), "U7": (62.5, 52.5, 0),
    "C4": (65.5, 46.5, 0), "C5": (58.6, 52.5, 0), "C6": (60.3, 50.0, 0), "C7": (66.5, 50.3, 0),
    "R7": (61.0, 44.0, 0), "R8": (65.5, 44.5, 0), "R20": (58.5, 44.0, 0), "D2": (64.5, 42.5, 0),
    "R21": (56.0, 42.0, 0), "R25": (58.5, 40.5, 0), "R26": (58.5, 42.2, 0),
    "R5": (61.5, 41.0, 0), "R6": (62.0, 29.5, 0),   # beside, not in front of, the USB-C tail row
    # Motor driver next to J5.
    "Q1": (58.5, 27.5, 0), "D1": (58.5, 31.0, 0), "R11": (55.5, 27.5, 90), "R12": (55.5, 29.5, 90),
    # Backlight driver left of the FPC tab; VSYS bulk caps right of it.
    "Q2": (23.0, 55.5, 0), "R13": (27.6, 56.5, 0), "R14": (20.5, 55.5, 90), "R15": (20.5, 58.0, 90),
    "C15": (44.8, 48.7, 0), "C16": (48.5, 54.0, 0),
    # LCD supply and pull-ups under the panel, above the tab.
    "C17": (35.5, 47.5, 0), "C18": (38.0, 47.5, 0), "R16": (40.0, 47.5, 0), "R17": (42.0, 47.5, 0),
    "R23": (34.0, 45.8, 0),
    # LED data series resistor on the way from the ESP32; one decoupling cap 6 degrees from each LED.
    "R24": (29.5, 29.0, 0),
    "C19": (18.4, 49.2, 0), "C20": (18.4, 22.8, 0), "C21": (49.2, 18.4, 0), "C22": (55.0, 51.5, 0),
    # ESP32 support: EN, decoupling, battery sense, LCD series resistors, UART test pads.
    "R1": (11.0, 47.5, 0), "C1": (13.5, 47.5, 0), "C2": (10.0, 50.5, 0), "C3": (13.0, 50.5, 0),
    "R9": (9.5, 25.0, 0), "R10": (9.5, 23.0, 0), "C14": (9.5, 21.0, 0),
    "R18": (18.6, 24.8, 0), "R19": (16.1, 24.8, 0),
    "TP1": (12.5, 20.5, 0), "TP2": (12.5, 23.0, 0),
    "R2": (30.0, 59.5, 0),
    # Radio decoupling under the panel, GPS decoupling beside the module.
    "C8": (51.0, 35.0, 90), "C9": (51.0, 38.5, 90), "C10": (25.0, 7.0, 0),
}

# Component heights (mm above the board) for the case and the under-panel check.
HEIGHTS = {
    "ESP32-S3-WROOM-1": 3.1, "ublox_SAM-M8Q": 6.35, "HOPERF_RFM9XW_SMD": 2.2,
    "USB_C_Receptacle_HRO_TYPE-C-31-M-12": 3.3, "JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal": 4.5,
    "JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal": 2.9, "U.FL_Hirose_U.FL-R-SMT-1_Vertical": 1.9,
    "SW_SPST_PTS645": 5.0, "SW_SPDT_PCM12": 2.5, "SOT-23": 1.1, "SOT-23-5": 1.1,
    "LGA-16_3x3mm_P0.5mm_LayoutBorder3x5y": 1.0, "LGA-12_2x2mm_P0.5mm": 1.0,
    "R_0402_1005Metric": 0.5, "C_0402_1005Metric": 0.5, "C_0603_1608Metric": 0.8,
    "R_0805_2012Metric": 0.6, "C_0805_2012Metric": 1.3, "LED_WS2812B-2020_PLCC4_2.0x2.0mm": 0.9,
    "D_SOD-123": 1.1, "LED_0603_1608Metric": 0.8, "LCD_FPC_12P_P0.70mm_Solder": 0.5,
}

# 3D models: (file in lib/3dmodels, offset mm, rotation deg) per footprint name.  The
# KiCad-library model drops in as is; the SparkFun ones need the offsets their own footprints use.
MODELS = {
    "ESP32-S3-WROOM-1": ("ESP32-S3-WROOM-1.step", (0, 0, 0), (0, 0, 0)),
    "ublox_SAM-M8Q": ("ublox_SAM-M8Q.step", (-7.65, 7.65, 0), (-90, 0, 0)),
    "USB_C_Receptacle_HRO_TYPE-C-31-M-12": ("USB_C_Receptacle_HRO_TYPE-C-31-M-12.step", (0, -1.09, 0), (-90, 0, 0)),
    "LED_WS2812B-2020_PLCC4_2.0x2.0mm": ("LED_WS2812B-2020_PLCC4_2.0x2.0mm.step", (0, 0, 0), (0, 0, 180)),
    "HOPERF_RFM9XW_SMD": ("HOPERF_RFM9XW_SMD.step", (0, 0, 0), (0, 0, 0)),
    "JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal": ("JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal.step", (0, 0, 0), (0, 0, 0)),
    "JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal": ("JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal.step", (0, 0, 0), (0, 0, 0)),
    "LCD_FPC_12P_P0.70mm_Solder": ("LCD_FPC_12P_P0.70mm_Solder.step", (0, 0, 0), (0, 0, 0)),
}

NETCLASSES = {
    "Default": {"track_width": 0.2, "clearance": 0.15},
    "Power": {"track_width": 0.5, "clearance": 0.2, "nets": ["VBUS", "VBAT", "VSYS"]},
    "Supply3V3": {"track_width": 0.35, "clearance": 0.15, "nets": ["+3V3"]},
    "RF": {"track_width": 0.35, "clearance": 0.4, "nets": ["/LORA_ANT"]},    # ~52 ohm on JLC's 7628 stack-up; 0.4 keeps signals off the feed (U.FL pads are 0.45 apart)
}


def P(x, y):
    import pcbnew
    return pcbnew.VECTOR2I(pcbnew.FromMM(OX + x), pcbnew.FromMM(OY + y))


def footprint_lib(fp_id):
    lib, name = fp_id.split(":")
    path = gp.FP_LIB if lib == gp.LIB else os.path.join(gk.STOCK_FP, lib + ".pretty")
    return path, name


def notch_span(angle, width):
    """Angular half-width (degrees) of a notch of the given width at the board edge."""
    return math.degrees(math.asin(width / 2 / RADIUS))


def in_notch(x, y, margin=0.0):
    """True if board point (x, y) lies in one of the edge notches, widened by margin."""
    for angle, width, depth in NOTCHES:
        a = math.radians(angle)
        ux, uy = math.cos(a), -math.sin(a)            # outward unit vector (board Y points down)
        dx, dy = x - CX, y - CY
        radial = dx * ux + dy * uy
        tangent = -dx * uy + dy * ux
        if radial >= RADIUS - depth - margin and abs(tangent) <= width / 2 + margin:
            return True
    return False


def outline_pts(n=720):
    """The round edge with its notches, counter-clockwise on the face."""
    pts = []
    for k in range(n):
        a = 360.0 * k / n
        skip = False
        for angle, width, depth in NOTCHES:
            half = notch_span(angle, width)
            if abs((a - angle + 180) % 360 - 180) <= half:
                skip = True
                if abs((a - (angle - half) + 180) % 360 - 180) < 360.0 / n:   # entering the notch
                    pts += [at_angle(angle - half, RADIUS), at_angle(angle - half, RADIUS - depth),
                            at_angle(angle + half, RADIUS - depth), at_angle(angle + half, RADIUS)]
        if not skip:
            pts.append(at_angle(a, RADIUS))
    return pts


def add_outline(board):
    import pcbnew
    c = pcbnew.PCB_SHAPE(board)
    c.SetShape(pcbnew.SHAPE_T_POLY)
    c.SetFilled(False)
    pts = [P(x, y) for x, y in outline_pts()]
    c.SetPolyPoints(pts)
    c.SetLayer(pcbnew.Edge_Cuts)
    c.SetWidth(pcbnew.FromMM(0.1))
    board.Add(c)


def circle_pts(r, n=96):
    import math
    return [(CX + r * math.cos(2 * math.pi * k / n), CY + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def inside(v, margin):
    """True if board point v (internal units) is at least `margin` mm inside the edge."""
    import pcbnew
    x, y = pcbnew.ToMM(v.x) - OX, pcbnew.ToMM(v.y) - OY
    dx, dy = x - CX, y - CY
    return (dx * dx + dy * dy) ** 0.5 <= RADIUS - margin and not in_notch(x, y, margin)


def add_edge_keepout(board, width=0.45):
    """No tracks or vias within `width` of the edge (Freerouting ignores KiCad's edge clearance)."""
    import pcbnew
    ko = pcbnew.ZONE(board)
    ko.SetIsRuleArea(True)
    layers = pcbnew.LSET()
    for layer in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
        layers.AddLayer(layer)
    ko.SetLayerSet(layers)
    ko.SetZoneName("EDGE_KEEPOUT")
    ko.SetDoNotAllowTracks(True)
    ko.SetDoNotAllowVias(True)
    ko.SetDoNotAllowCopperPour(False)
    ko.SetDoNotAllowPads(False)
    ko.SetDoNotAllowFootprints(False)
    o = ko.Outline()
    o.NewOutline()
    for x, y in ((-1, -1), (BOARD_W + 1, -1), (BOARD_W + 1, BOARD_H + 1), (-1, BOARD_H + 1)):
        o.Append(pcbnew.FromMM(OX + x), pcbnew.FromMM(OY + y))
    o.NewHole()
    for x, y in circle_pts(RADIUS - width):
        o.Append(pcbnew.FromMM(OX + x), pcbnew.FromMM(OY + y), 0, 0)
    board.Add(ko)
    for n, (angle, w, depth) in enumerate(NOTCHES):
        a = math.radians(angle)
        ux, uy = math.cos(a), -math.sin(a)
        tx, ty = -uy, ux
        r0, r1, hw = RADIUS - depth - width, RADIUS + 1.0, w / 2 + width
        pts = [(CX + r0 * ux - hw * tx, CY + r0 * uy - hw * ty), (CX + r1 * ux - hw * tx, CY + r1 * uy - hw * ty),
               (CX + r1 * ux + hw * tx, CY + r1 * uy + hw * ty), (CX + r0 * ux + hw * tx, CY + r0 * uy + hw * ty)]
        rule_area(board, "NOTCH_KEEPOUT_%d" % (n + 1), pts,
                  (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu), tracks=True, vias=True)


def add_zone(board, net, layer, name, priority=0):
    import pcbnew
    MM = pcbnew.FromMM
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(net)
    z.SetZoneName(name)
    z.SetAssignedPriority(priority)
    z.SetLocalClearance(MM(0.2))
    z.SetMinThickness(MM(0.2))
    z.SetThermalReliefGap(MM(0.3))
    z.SetThermalReliefSpokeWidth(MM(0.3))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    o = z.Outline()
    o.NewOutline()
    for x, y in circle_pts(RADIUS + 0.5):
        o.Append(pcbnew.FromMM(OX + x), pcbnew.FromMM(OY + y))
    board.Add(z)


def add_text(board, txt, x, y, size, layer, angle=0, mirrored=False):
    import pcbnew
    t = pcbnew.PCB_TEXT(board)
    t.SetText(txt)
    t.SetPosition(P(x, y))
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(size), pcbnew.FromMM(size)))
    t.SetTextThickness(pcbnew.FromMM(0.15))
    t.SetTextAngleDegrees(angle)
    t.SetMirrored(mirrored)
    board.Add(t)


STOCK_3D = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels"
LOCAL_3D = os.path.join(gp.LIB_DIR, "3dmodels")


def use_local_models(fp, name):
    """Point a footprint at the project 3D model when MODELS lists one and the file exists."""
    import pcbnew
    if name not in MODELS:
        return
    fname, off, rot = MODELS[name]
    if not os.path.exists(os.path.join(LOCAL_3D, fname)):
        return
    models = fp.Models()
    if len(models) == 0:
        m = pcbnew.FP_3DMODEL()
        models.push_back(m)
    m = models[0]                      # index: iterating the SWIG vector yields copies
    m.m_Filename = "${KIPRJMOD}/lib/3dmodels/" + fname
    m.m_Offset = pcbnew.VECTOR3D(*off)
    m.m_Rotation = pcbnew.VECTOR3D(*rot)
    m.m_Scale = pcbnew.VECTOR3D(1, 1, 1)


def add_shape(board, layer, kind, a, b=None, mid=None, width=0.1):
    import pcbnew
    sh = pcbnew.PCB_SHAPE(board)
    sh.SetShape(kind)
    if kind == pcbnew.SHAPE_T_ARC:
        sh.SetArcGeometry(P(*a), P(*mid), P(*b))
    else:
        sh.SetStart(P(*a))
        sh.SetEnd(P(*b))
    sh.SetLayer(layer)
    sh.SetWidth(pcbnew.FromMM(width))
    board.Add(sh)
    return sh


def add_panel_outline(board):
    """Where the panel, its chin and the folded FPC lie, for reference while routing."""
    import pcbnew
    r = PANEL["outline_dia"] / 2
    for layer in (pcbnew.Cmts_User, pcbnew.F_Fab):
        add_shape(board, layer, pcbnew.SHAPE_T_CIRCLE, (CX, CY), (CX + r, CY))
    add_shape(board, pcbnew.Cmts_User, pcbnew.SHAPE_T_CIRCLE, (CX, CY), (CX + PANEL["active_dia"] / 2, CY))
    hw = PANEL["chin_width"] / 2
    y1 = PANEL["chin_reach"]
    y0 = CY + (r * r - hw * hw) ** 0.5
    for a, b in (((CX - hw, y0), (CX - hw, y1)), ((CX - hw, y1), (CX + hw, y1)), ((CX + hw, y1), (CX + hw, y0))):
        add_shape(board, pcbnew.Cmts_User, pcbnew.SHAPE_T_SEGMENT, a, b)
    x0, t0, x1, t1 = FPC_TAB
    for a, b in (((x0, t0), (x1, t0)), ((x1, t0), (x1, t1)), ((x1, t1), (x0, t1)), ((x0, t1), (x0, t0))):
        add_shape(board, pcbnew.Cmts_User, pcbnew.SHAPE_T_SEGMENT, a, b)
    add_text(board, "1.28in GC9A01 panel (on ring ledge, Z %.1f)" % PANEL["ledge_z"], CX, CY - 6, 1.0, pcbnew.Cmts_User)
    add_text(board, "folded FPC", CX, t1 - 1.2, 0.8, pcbnew.Cmts_User)
    for a in BOLT_ANGLES:
        x, y = at_angle(a, BOLT_R)
        add_shape(board, pcbnew.Cmts_User, pcbnew.SHAPE_T_CIRCLE, (x, y), (x + BOSS_R, y))


def rule_area(board, name, pts, layers, tracks=False, vias=False, pour=False, footprints=False):
    import pcbnew
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    ls = pcbnew.LSET()
    for layer in layers:
        ls.AddLayer(layer)
    z.SetLayerSet(ls)
    z.SetZoneName(name)
    z.SetDoNotAllowTracks(tracks)
    z.SetDoNotAllowVias(vias)
    z.SetDoNotAllowCopperPour(pour)
    z.SetDoNotAllowFootprints(footprints)
    z.SetDoNotAllowPads(False)
    o = z.Outline()
    o.NewOutline()
    for x, y in pts:
        o.Append(pcbnew.FromMM(OX + x), pcbnew.FromMM(OY + y))
    board.Add(z)
    return z


def annulus_sector(r0, r1, a0, a1, step=4):
    """Polygon of the ring r0..r1 between angles a0 and a1 (degrees, counter-clockwise)."""
    pts = []
    n = max(2, int((a1 - a0) / step) + 1)
    for k in range(n + 1):
        pts.append(at_angle(a0 + (a1 - a0) * k / n, r1))
    for k in range(n, -1, -1):
        pts.append(at_angle(a0 + (a1 - a0) * k / n, r0))
    return pts


def add_rule_areas(board):
    import pcbnew
    cu = (pcbnew.F_Cu, pcbnew.B_Cu)
    # No signal traces under the GPS module on the outer layers (its ground is the In1 plane).
    x, y, _ = PLACEMENT["U3"]
    h = 5.8   # the pad ring is at 6.6, so the module's own escape stubs and vias stay legal
    rule_area(board, "GPS_NO_TRACES", [(x - h, y - h), (x + h, y - h), (x + h, y + h), (x - h, y + h)],
              cu, tracks=True, vias=True)
    # The case bosses (7.5 mm) press on the bolt pads: nothing may straddle the boss edge.
    for i, a in enumerate(BOLT_ANGLES):
        bx, by = at_angle(a, BOLT_R)
        pts = [(bx + (BOSS_R + 0.35) * math.cos(math.radians(t)), by + (BOSS_R + 0.35) * math.sin(math.radians(t)))
               for t in range(0, 360, 10)]
        inner = [(bx + (BOSS_R + 0.05) * math.cos(math.radians(t)), by + (BOSS_R + 0.05) * math.sin(math.radians(t)))
                 for t in range(350, -10, -10)]
        z = rule_area(board, "BOSS_%d" % (i + 1), pts, cu, footprints=True)
        o = z.Outline()
        o.NewHole()
        for px, py in inner:
            o.Append(pcbnew.FromMM(OX + px), pcbnew.FromMM(OY + py), 0, 0)
    # The panel ring's wall stands on the board: no parts under it except in its gaps and where
    # the GPS module reaches under its top (70-110 deg; the wall is thinner there).
    r0, r1 = RING_WALL[0] + 0.05, RING_WALL[1] + 0.1
    gaps = sorted(list(RING_WALL_GAPS) + [(70, 110)])
    sectors = [(gaps[i][1], gaps[(i + 1) % len(gaps)][0] + (360 if i == len(gaps) - 1 else 0)) for i in range(len(gaps))]
    for i, (a0, a1) in enumerate(sectors):
        rule_area(board, "RING_WALL_%d" % (i + 1), annulus_sector(r0, r1, a0, a1), (pcbnew.F_Cu,), footprints=True)


def back_copper(board):
    """Exposed copper on the back: via rings and back-side pads, as (x, y, radius) in board mm."""
    import pcbnew
    items = []
    for t in board.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            p = t.GetPosition()
            items.append((pcbnew.ToMM(p.x) - OX, pcbnew.ToMM(p.y) - OY, pcbnew.ToMM(t.GetWidth()) / 2))
    for pad in board.GetPads():
        if pad.IsOnLayer(pcbnew.B_Cu):
            p = pad.GetPosition()
            items.append((pcbnew.ToMM(p.x) - OX, pcbnew.ToMM(p.y) - OY, max(pcbnew.ToMM(pad.GetSize().x), pcbnew.ToMM(pad.GetSize().y)) / 2))
    return items


def clear_of(copper, x, y, margin, boxes=()):
    if any(x0 - margin <= x <= x1 + margin and y0 - margin <= y <= y1 + margin for x0, y0, x1, y1 in boxes):
        return False
    return all((x - cx) ** 2 + (y - cy) ** 2 >= (r + margin) ** 2 for cx, cy, r in copper)


def add_back_art(board, boxes=()):
    """Radar dial on the back silkscreen, drawn after routing: rings, ticks and a crosshair in short
    segments that skip the vias, pads and text they would otherwise cross (silk may not sit on open
    copper or other silk)."""
    import pcbnew
    copper = back_copper(board)
    margin = 0.45

    def seg(a, b, width):
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        if all(clear_of(copper, px, py, margin, boxes) for px, py in (a, b, mid)):
            add_shape(board, pcbnew.B_SilkS, pcbnew.SHAPE_T_SEGMENT, a, b, width=width)
    for r in (10.0, 20.0, 28.0):
        n = int(2 * math.pi * r / 1.0)                    # about 1 mm per segment
        pts = [(CX + r * math.cos(2 * math.pi * k / n), CY + r * math.sin(2 * math.pi * k / n)) for k in range(n + 1)]
        for a, b in zip(pts, pts[1:]):
            seg(a, b, 0.3)
    for k in range(12):
        a = math.radians(k * 30)
        inner, outer = (26.6, 28.0) if k % 3 else (25.6, 28.0)
        seg((CX + inner * math.cos(a), CY - inner * math.sin(a)), (CX + outer * math.cos(a), CY - outer * math.sin(a)), 0.3)
    for a, b in (((CX - 9.0, CY), (CX + 9.0, CY)), ((CX, CY - 9.0), (CX, CY + 9.0))):
        for k in range(6):
            p0 = (a[0] + (b[0] - a[0]) * k / 6, a[1] + (b[1] - a[1]) * k / 6)
            p1 = (a[0] + (b[0] - a[0]) * (k + 1) / 6, a[1] + (b[1] - a[1]) * (k + 1) / 6)
            seg(p0, p1, 0.25)


def back_text(board, txt, x, y, size, copper, boxes):
    """Back-silk text, nudged up or down (up to 4 mm) until no via, pad or earlier text lies under it.
    Returns the box it took (board mm) so the dial art can keep off it."""
    import pcbnew
    for sz in (size, max(0.8, size * 0.85)):          # never below the 0.8 mm silk minimum
        w, h = 1.0 * sz * len(txt) / 2 + 0.5, sz / 2 + 0.3
        xs = [x - w + 0.5 * k for k in range(int(2 * w / 0.5) + 1)]      # every 0.5 mm: vias are 0.5 wide
        for dy in [0] + [s * k * 0.5 for k in range(1, 13) for s in (1, -1)]:
            for dx in (0, 2.0, -2.0, 4.0, -4.0):
                xx, yy = x + dx, y + dy
                pts = [xx - w + 0.5 * k for k in range(int(2 * w / 0.5) + 1)]
                if all(clear_of(copper, px, py, 0.25, boxes) for px in pts for py in (yy - h, yy, yy + h)):
                    add_text(board, txt, xx, yy, sz, pcbnew.B_SilkS, mirrored=True)
                    return (xx - w, yy - h, xx + w, yy + h)
    print("back silk '%s' sits on copper somewhere; placed anyway" % txt)
    w, h = 1.0 * size * len(txt) / 2 + 0.5, size / 2 + 0.3
    add_text(board, txt, x, y, size, pcbnew.B_SilkS, mirrored=True)
    return (x - w, y - h, x + w, y + h)


def footprint_height(fp):
    return HEIGHTS.get(fp.GetFPIDAsString().split(":")[1], 1.0)


def check_layout(board):
    """Mechanical rules DRC cannot express: height under the panel and a clear FPC tab."""
    import pcbnew
    problems = []
    x0, y0, x1, y1 = FPC_TAB
    on_board = {fp.GetReference() for fp in board.GetFootprints()}
    for ref in PLACEMENT:
        if ref not in on_board:
            problems.append("%s is placed but is not in PARTS" % ref)
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        fp.BuildCourtyardCaches()
        bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
        l, t = pcbnew.ToMM(bb.GetLeft()) - OX, pcbnew.ToMM(bb.GetTop()) - OY
        r, b = pcbnew.ToMM(bb.GetRight()) - OX, pcbnew.ToMM(bb.GetBottom()) - OY
        if ref == "U1":   # courtyard includes the antenna keep-out; use the module body
            x, y, _ = PLACEMENT["U1"]
            l, t, r, b = x - 12.75, y - 9.0, x + 12.75, y + 9.0
        corners = [(l, t), (r, t), (l, b), (r, b)]
        r_max = max(((cx - CX) ** 2 + (cy - CY) ** 2) ** 0.5 for cx, cy in corners)
        if ref not in ("J1", "SW2") and r_max > RADIUS:   # USB-C shell and switch knob overhang by design
            problems.append("%s courtyard reaches r %.2f, past the board edge" % (ref, r_max))
        inside = any(((cx - CX) ** 2 + (cy - CY) ** 2) ** 0.5 < PANEL["under_panel_r"] for cx, cy in corners)
        if inside and footprint_height(fp) > PANEL["max_height_under"]:
            problems.append("%s is %.1f mm tall under the panel" % (ref, footprint_height(fp)))
        if ref != "J3" and l < x1 and r > x0 and t < y1 and b > y0:
            problems.append("%s lies under the folded FPC tab" % ref)
        if ref not in ("H1", "H2", "H3", "H4"):
            for a in BOLT_ANGLES:
                bx, by = at_angle(a, BOLT_R)
                dx = max(l - bx, 0, bx - r)
                dy = max(t - by, 0, by - b)
                if (dx * dx + dy * dy) ** 0.5 < BOSS_R:
                    problems.append("%s is under case boss at %d deg" % (ref, a))
    if problems:
        sys.exit("layout check failed:\n  " + "\n  ".join(problems))
    print("layout check OK")


def place(pads, comps, uuids):
    import pcbnew
    for path in (gp.PCB_FILE, gp.PRO_FILE):
        if os.path.exists(path):
            os.remove(path)
    board = pcbnew.NewBoard(gp.PCB_FILE)
    board.SetCopperLayerCount(4)
    tb = board.GetTitleBlock()
    tb.SetTitle(gp.TITLE)
    tb.SetDate(gp.DATE)
    tb.SetRevision(gp.REV)
    tb.SetComment(0, "4-layer 1.6 mm: F.Cu signals, In1 GND, In2 +3V3, B.Cu signals")
    ds = board.GetDesignSettings()
    MM = pcbnew.FromMM
    ds.SetBoardThickness(MM(1.6))
    ds.m_MinClearance = MM(0.15)
    ds.m_TrackMinWidth = MM(0.15)
    ds.m_ViasMinSize = MM(0.45)
    ds.m_MinThroughDrill = MM(0.2)
    ds.m_ViasMinAnnularWidth = MM(0.1)
    ds.m_HoleClearance = MM(0.2)
    ds.m_HoleToHoleMin = MM(0.25)
    ds.m_CopperEdgeClearance = MM(0.3)
    ds.m_SilkClearance = 0
    ds.m_MinSilkTextHeight = MM(0.8)
    ds.m_MinSilkTextThickness = MM(0.15)
    ds.m_SolderMaskExpansion = 0
    ds.m_SolderMaskMinWidth = 0
    ds.m_AllowSoldermaskBridgesInFPs = True
    if hasattr(ds, "m_TentVias"):
        ds.m_TentVias = True       # keeps the back-silk dial off exposed via rings
    ds.SetAuxOrigin(P(0, 0))
    ds.SetGridOrigin(P(0, 0))

    nets = {}
    for name in sorted({v[0] for v in pads.values()}):
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        nets[name] = ni

    for ref, lib_id, value, fp_id, _ in gp.PARTS:
        libpath, name = footprint_lib(fp_id)
        fp = pcbnew.FootprintLoad(libpath, name)
        if fp is None:
            sys.exit("footprint not found: " + fp_id)
        fp.SetFPIDAsString(fp_id)
        use_local_models(fp, name)
        fp.SetReference(ref)
        fp.SetValue(comps[ref]["value"])
        x, y, rot = PLACEMENT[ref]
        fp.SetPosition(P(x, y))
        fp.SetOrientationDegrees(rot)
        fp.SetPath(pcbnew.KIID_PATH("/" + uuids[ref]))
        fp.SetProperty("Sheetfile", gp.NAME + ".kicad_sch")
        fp.SetProperty("Sheetname", "")
        board.Add(fp)
        for pad in fp.Pads():
            key = (ref, pad.GetNumber())
            if key in pads:
                net, func, ptype = pads[key]
                pad.SetNet(nets[net])
                pad.SetPinFunction(func)
                pad.SetPinType(ptype)
        if ref == "J1":
            for pad in fp.Pads():
                if pad.GetNumber() == "S1":   # shell tabs: solid to ground for strength
                    pad.SetZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
        if ref == "U1":
            # The stock antenna keep-out lists F.Cu, In1 and B.Cu only; keep the 3.3 V plane out as well.
            for z in fp.Zones():
                if z.GetIsRuleArea():
                    ls = z.GetLayerSet()
                    ls.AddLayer(pcbnew.In2_Cu)
                    z.SetLayerSet(ls)
            # The module's thermal vias come with 0.2 mm drills; 0.25 matches the rest of the board.
            for pad in fp.Pads():
                if 0 < pad.GetDrillSize().x < pcbnew.FromMM(0.25):
                    pad.SetDrillSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.25), pcbnew.FromMM(0.25)))
        if ref == "J4":
            # Turn the U.FL so its signal pad faces U2's antenna pad and its ground pads do not sit in between.
            ant = board.FindFootprintByReference("U2").FindPadByNumber("9").GetPosition()
            best = None
            for deg in (0, 90, 180, 270):
                fp.SetOrientationDegrees(deg)
                d1 = dist(fp.FindPadByNumber("1").GetPosition(), ant)
                dg = min(dist(p.GetPosition(), ant) for p in fp.Pads() if p.GetNumber() != "1")
                if d1 < dg and (best is None or d1 < best[0]):
                    best = (d1, deg)
            fp.SetOrientationDegrees(best[1])
        if ref in ("J1", "U3", "SW2"):
            # Their silkscreen outlines would touch the board edge; all sit under the case anyway.
            for item in list(fp.GraphicalItems()):
                if item.GetLayer() == pcbnew.F_SilkS:
                    fp.Remove(item)
        # References live on the fab layer; the silkscreen carries user-facing labels.
        fp.Reference().SetLayer(pcbnew.F_Fab)

    add_outline(board)
    add_edge_keepout(board)
    add_rule_areas(board)          # before the fan-out, so its vias respect the GPS keep-out
    preroute_antenna(board)
    # In1 is a ground plane and In2 a 3.3 V plane; every SMD pad on those nets
    # gets its own via, so the router only has to handle signals.
    add_zone(board, nets["GND"], pcbnew.In1_Cu, "GND_IN1")
    add_zone(board, nets["+3V3"], pcbnew.In2_Cu, "3V3_IN2")
    fanout(board, ("GND", "+3V3"))

    add_panel_outline(board)
    check_layout(board)

    pcbnew.SaveBoard(gp.PCB_FILE, board)


def dist(a, b):
    return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5


def preroute_antenna(board):
    """The LoRa feed: one straight, locked top-layer track from U2's ANT pad to the U.FL, so the
    auto-router cannot take it through vias or across the 3.3 V plane.  No vias may land beside it
    or around the U.FL's signal pad (the fan-out and Freerouting both respect the rule areas)."""
    import pcbnew
    a = board.FindFootprintByReference("U2").FindPadByNumber("9")
    b = board.FindFootprintByReference("J4").FindPadByNumber("1")
    ax, ay = pcbnew.ToMM(a.GetPosition().x) - OX, pcbnew.ToMM(a.GetPosition().y) - OY
    bx, by = pcbnew.ToMM(b.GetPosition().x) - OX, pcbnew.ToMM(b.GetPosition().y) - OY
    ux, uy = bx - ax, by - ay
    L = math.hypot(ux, uy)
    ux, uy = ux / L, uy / L
    nx, ny, hw = -uy, ux, 1.0
    band = [(ax - nx * hw, ay - ny * hw), (bx - nx * hw, by - ny * hw), (bx + nx * hw, by + ny * hw), (ax + nx * hw, ay + ny * hw)]
    cu = (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)
    rule_area(board, "LORA_FEED_NO_VIAS", band, cu, vias=True)
    ring = [(bx + 2.6 * math.cos(math.radians(t)), by + 2.6 * math.sin(math.radians(t))) for t in range(0, 360, 15)]
    rule_area(board, "UFL_NO_VIAS", ring, cu, vias=True)
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(a.GetPosition())
    t.SetEnd(b.GetPosition())
    t.SetWidth(pcbnew.FromMM(NETCLASSES["RF"]["track_width"]))
    t.SetLayer(pcbnew.F_Cu)
    t.SetNet(a.GetNet())
    t.SetLocked(True)
    board.Add(t)
    print("LoRa feed: %.1f mm on F.Cu" % (dist(a.GetPosition(), b.GetPosition()) / 1e6))


def seg_dist(a, b, p):
    """Distance from point p to segment a-b."""
    dx, dy = b.x - a.x, b.y - a.y
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0.0, min(1.0, ((p.x - a.x) * dx + (p.y - a.y) * dy) / L))
    return ((a.x + t * dx - p.x) ** 2 + (a.y + t * dy - p.y) ** 2) ** 0.5


def seg_seg(a, b, c, d):
    """Distance between segments a-b and c-d (zero if they cross)."""
    def cross(o, p, q):
        return (p.x - o.x) * (q.y - o.y) - (p.y - o.y) * (q.x - o.x)
    if (cross(a, b, c) * cross(a, b, d) < 0) and (cross(c, d, a) * cross(c, d, b) < 0):
        return 0.0
    return min(seg_dist(a, b, c), seg_dist(a, b, d), seg_dist(c, d, a), seg_dist(c, d, b))


VIA_SIZE, VIA_DRILL = 0.5, 0.25
FANOUT_CLEARANCE = 0.16


def fanout(board, net_names):
    """Drop a via next to every SMD pad on the plane nets, with a short stub."""
    import math
    import pcbnew
    MM = pcbnew.FromMM
    pads = list(board.GetPads())
    keepouts = [z.Outline() for fp in board.GetFootprints() for z in fp.Zones()
                if z.GetIsRuleArea() and z.GetDoNotAllowVias()]
    keepouts += [z.Outline() for z in board.Zones() if z.GetIsRuleArea() and z.GetDoNotAllowVias()]
    fixed = [(t.GetStart(), t.GetEnd(), t.GetWidth(), t.GetNetname())
             for t in board.GetTracks() if t.Type() == pcbnew.PCB_TRACE_T]   # the pre-routed feed
    placed = []    # (net, shape) of vias and stubs already added
    failed = []
    for pad in pads:
        net = pad.GetNetname()
        if net not in net_names or pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
            continue
        if not pad.IsOnLayer(pcbnew.F_Cu):
            continue
        c = pad.GetPosition()
        bb = pad.GetBoundingBox()
        half = max(bb.GetWidth(), bb.GetHeight()) / 2
        stub_w = min(MM(0.25), min(pad.GetSize().x, pad.GetSize().y))
        best = None
        r = half + MM(0.45)
        while r <= half + MM(2.2) and best is None:
            for k in range(16):
                a = k * math.pi / 8
                v = pcbnew.VECTOR2I(int(c.x + r * math.cos(a)), int(c.y + r * math.sin(a)))
                if not inside(v, 0.9):
                    continue
                if any(k_.Contains(v) for k_ in keepouts):
                    continue
                via = pcbnew.SHAPE_CIRCLE(v, MM(VIA_SIZE / 2))
                stub = pcbnew.SHAPE_SEGMENT(c, v, stub_w)
                ok = True
                for other in pads:
                    if other is pad:
                        continue
                    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
                        if not other.IsOnLayer(layer):
                            continue
                        shape = other.GetEffectiveShape(layer)
                        gap = 0.3 if other.GetNetname() == "/LORA_ANT" else FANOUT_CLEARANCE
                        if shape.Collide(via, MM(gap)):
                            ok = False
                            break
                        if layer == pcbnew.F_Cu and other.GetNetname() != net and \
                                shape.Collide(stub, MM(FANOUT_CLEARANCE)):
                            ok = False
                            break
                    if not ok:
                        break
                if ok:
                    for fs, fe, fw, fnet in fixed:
                        gap = MM(0.3)
                        if seg_dist(fs, fe, v) < MM(VIA_SIZE / 2) + fw / 2 + gap or \
                                (fnet != net and seg_seg(fs, fe, c, v) < fw / 2 + stub_w / 2 + gap):
                            ok = False
                            break
                if ok:
                    clr = MM(FANOUT_CLEARANCE)
                    for pnet, pv, pc, pw in placed:
                        # pv: earlier via centre; (pc, pv, pw): its stub from the pad centre
                        if dist(pv, v) < MM(VIA_SIZE + 0.3):
                            ok = False
                        elif pnet != net and (
                                seg_dist(pc, pv, v) < MM(VIA_SIZE / 2) + pw / 2 + clr or
                                seg_dist(c, v, pv) < MM(VIA_SIZE / 2) + stub_w / 2 + clr or
                                seg_seg(pc, pv, c, v) < pw / 2 + stub_w / 2 + clr):
                            ok = False
                        if not ok:
                            break
                if ok:
                    best = (v, via, stub)
                    break
            r += MM(0.15)
        if best is None:
            failed.append("%s.%s" % (pad.GetParent().GetReference(), pad.GetNumber()))
            continue
        v, via_shape, stub_shape = best
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(c)
        t.SetEnd(v)
        t.SetWidth(stub_w)
        t.SetLayer(pcbnew.F_Cu)
        t.SetNet(pad.GetNet())
        t.SetLocked(True)
        board.Add(t)
        via = pcbnew.PCB_VIA(board)
        via.SetPosition(v)
        via.SetWidth(MM(VIA_SIZE))
        via.SetDrill(MM(VIA_DRILL))
        via.SetNet(pad.GetNet())
        via.SetLocked(True)
        board.Add(via)
        placed.append((net, v, c, stub_w))
    print("fan-out: %d vias%s" % (len(placed), ("; no room for " + ", ".join(failed)) if failed else ""))


def configure_project():
    pro = json.load(open(gp.PRO_FILE))
    classes = pro["net_settings"]["classes"]
    default = classes[0]
    default.update({"track_width": NETCLASSES["Default"]["track_width"],
                    "clearance": NETCLASSES["Default"]["clearance"],
                    "via_diameter": 0.5, "via_drill": 0.25})
    out, patterns = [default], []
    for name, spec in NETCLASSES.items():
        if name == "Default":
            continue
        c = dict(default)
        c.update({"name": name, "track_width": spec["track_width"], "clearance": spec["clearance"]})
        out.append(c)
        patterns += [{"netclass": name, "pattern": n} for n in spec["nets"]]
    pro["net_settings"]["classes"] = out
    pro["net_settings"]["netclass_patterns"] = patterns
    rules = pro["board"]["design_settings"]["rules"]
    rules.update({"min_clearance": 0.15, "min_track_width": 0.15, "min_via_diameter": 0.45,
                  "min_through_hole_diameter": 0.2, "min_via_annular_width": 0.1,
                  "min_hole_clearance": 0.2, "min_hole_to_hole": 0.25,
                  "min_copper_edge_clearance": 0.3, "min_silk_clearance": 0.0,
                  "min_text_height": 0.8, "min_text_thickness": 0.15})
    json.dump(pro, open(gp.PRO_FILE, "w"), indent=2, sort_keys=True)


def drc(board, label):
    import pcbnew
    report = os.path.join(tempfile.gettempdir(), gp.NAME + "_drc.txt")
    pcbnew.WriteDRCReport(board, report, pcbnew.EDA_UNITS_MILLIMETRES, True)
    text = open(report).read()
    counts = {}
    for kind in re.findall(r"^\[(\w+)\]", text, re.M):
        counts[kind] = counts.get(kind, 0) + 1
    env_only = counts.pop("lib_footprint_issues", 0)
    unconnected = re.search(r"Found (\d+) unconnected", text)
    print("DRC %s: %s; unconnected=%s (%d lib_footprint_issues ignored)" % (
        label, ", ".join("%s=%d" % kv for kv in sorted(counts.items())) or "no violations",
        unconnected.group(1) if unconnected else "?", env_only))
    return counts, text


def build(pads, comps, uuids):
    place(pads, comps, uuids)
    configure_project()
    # KiCad keeps the project it created in memory, so the routing, fill and DRC
    # steps run in a fresh process that reads the updated .kicad_pro.
    subprocess.run([sys.executable, os.path.abspath(__file__)] + sys.argv[1:], check=True)


SILK = [
    # text, x, y, size, angle  (assembly aids; the face is covered by the dial plate)
    ("+", 46.0, 65.6, 1.0, 0), ("-", 48.0, 65.6, 1.0, 0), ("BATT", 41.6, 58.5, 0.8, 90),
    ("MOTOR", 63.5, 18.6, 0.8, 0), ("ANT", 55.8, 44.6, 0.8, 0),
    ("ON", 18.0, 61.5, 0.8, 0),
    ("TX RX", 12.5, 18.3, 0.8, 0),
]
BACK_SILK = [
    ("FINDER PUCK", CX, 47.0, 1.5),
    ("1 [ ]    2 [ ]", CX, 52.0, 1.0),
    ("v%s  %s" % (gp.REV, gp.DATE[:7]), CX, 54.5, 0.8),
]


def route(board):
    """Auto-route with Freerouting: inner layers are ground planes, signals use F/B."""
    import pcbnew
    jar = FREEROUTING
    if not jar or not os.path.exists(jar):
        sys.exit("set FREEROUTING_JAR to freerouting-1.9.0.jar to route the board")
    work = tempfile.mkdtemp(prefix=gp.NAME + "_route_")
    dsn, ses = os.path.join(work, "board.dsn"), os.path.join(work, "board.ses")
    pcbnew.ExportSpecctraDSN(board, dsn)
    text = open(dsn).read()
    for layer in ("In1.Cu", "In2.Cu"):
        text = re.sub(r"(\(layer %s\s*\(type )signal" % re.escape(layer), r"\1power", text)
    # Freerouting rounds coordinates; route 3 um wider than KiCad checks so it never undercuts.
    text = re.sub(r"\(clearance ([\d.]+)", lambda m: "(clearance %.1f" % (float(m.group(1)) + 3), text)
    open(dsn, "w").write(text)
    # -da turns off Freerouting's usage analytics.  Version 1.9 needs its window.
    subprocess.run(["java", "-jar", jar, "-da", "-de", dsn, "-do", ses, "-mp", "80"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not os.path.exists(ses):
        sys.exit("Freerouting produced no session file")
    import_session(board, ses)
    shutil.rmtree(work)


def import_session(board, ses):
    """Add Freerouting's wires and vias.  (pcbnew.ImportSpecctraSES only works inside the editor.)"""
    import pcbnew
    tree = gk.parse_sexpr(open(ses).read())
    routes = next(c for c in tree if isinstance(c, list) and c[0] == "routes")
    res = next(c for c in routes if isinstance(c, list) and c[0] == "resolution")
    per_um = float(res[2])

    def nm(v, flip=False):
        return int(round(float(v) / per_um * 1000)) * (-1 if flip else 1)

    vias = {}
    for c in routes:
        if isinstance(c, list) and c[0] == "library_out":
            for ps in c[1:]:
                if isinstance(ps, list) and ps[0] == "padstack":
                    m = re.search(r"_(\d+):(\d+)_um", ps[1])
                    vias[ps[1]] = (int(m.group(1)) * 1000, int(m.group(2)) * 1000)
    layers = {board.GetLayerName(i): i for i in range(pcbnew.PCB_LAYER_ID_COUNT)}
    network = next(c for c in routes if isinstance(c, list) and c[0] == "network_out")
    added = [0, 0]
    for net_node in network[1:]:
        net = board.FindNet(net_node[1])
        for item in net_node[2:]:
            if item[0] == "wire":
                path = next(c for c in item[1:] if isinstance(c, list) and c[0] == "path")
                layer, width, coords = layers[path[1]], nm(path[2]), path[3:]
                pts = [(nm(coords[i]), nm(coords[i + 1], True)) for i in range(0, len(coords) - 1, 2)]
                for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                    t = pcbnew.PCB_TRACK(board)
                    t.SetStart(pcbnew.VECTOR2I(x1, y1))
                    t.SetEnd(pcbnew.VECTOR2I(x2, y2))
                    t.SetWidth(width)
                    t.SetLayer(layer)
                    t.SetNet(net)
                    board.Add(t)
                    added[0] += 1
            elif item[0] == "via":
                size, drill = vias[item[1]]
                v = pcbnew.PCB_VIA(board)
                v.SetPosition(pcbnew.VECTOR2I(nm(item[2]), nm(item[3], True)))
                v.SetWidth(size)
                v.SetDrill(drill)
                v.SetNet(net)
                board.Add(v)
                added[1] += 1
    print("imported %d track segments, %d vias" % tuple(added))


def check_routing(board):
    """What the router and the fills must respect: the LoRa feed stays a single top-layer track
    and nothing but air sits under the ESP32's antenna on any copper layer."""
    import pcbnew
    problems = []
    feed = [t for t in board.GetTracks() if t.GetNetname().lstrip("/") == "LORA_ANT"]
    if len(feed) != 1 or feed[0].Type() == pcbnew.PCB_VIA_T or feed[0].GetLayer() != pcbnew.F_Cu:
        problems.append("the LoRa feed is not a single F.Cu track (%d items)" % len(feed))
    else:
        a = board.FindFootprintByReference("U2").FindPadByNumber("9").GetPosition()
        b = board.FindFootprintByReference("J4").FindPadByNumber("1").GetPosition()
        ends = {(feed[0].GetStart().x, feed[0].GetStart().y), (feed[0].GetEnd().x, feed[0].GetEnd().y)}
        if ends != {(a.x, a.y), (b.x, b.y)} or feed[0].GetWidth() != pcbnew.FromMM(NETCLASSES["RF"]["track_width"]):
            problems.append("the LoRa feed does not run pad to pad at the RF width")
    hits = 0
    xs = [1.6 + 0.5 * k for k in range(12)]           # the module's antenna strip, x 1.5-7.5
    for z in board.Zones():
        if z.GetIsRuleArea():
            continue
        for px in xs:
            for py in range(13, 60, 1):
                for layer in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
                    if z.IsOnLayer(layer) and z.HitTestFilledArea(layer, P(px, py)):
                        hits += 1
    strip = pcbnew.BOX2I(P(0.0, 12.0), pcbnew.VECTOR2I(pcbnew.FromMM(7.5), pcbnew.FromMM(48.0)))
    for t in board.GetTracks():
        if t.GetBoundingBox().Intersects(strip):
            problems.append("%s on the ESP32 antenna strip" % t.GetNetname())
    if hits:
        problems.append("copper fill under the ESP32 antenna at %d sample points" % hits)
    if problems:
        sys.exit("routing check failed:\n  " + "\n  ".join(sorted(set(problems))))
    print("routing check OK")


def verify_rules(board):
    """The router and DRC read net classes from the project file; refuse to run on defaults."""
    import pcbnew
    ds = board.GetDesignSettings()
    d = ds.m_NetSettings.m_DefaultNetClass
    want = NETCLASSES["Default"]
    got = (round(pcbnew.ToMM(d.GetClearance()), 3), round(pcbnew.ToMM(d.GetTrackWidth()), 3),
           round(pcbnew.ToMM(d.GetViaDrill()), 3), round(pcbnew.ToMM(ds.m_MinThroughDrill), 3))
    expect = (want["clearance"], want["track_width"], 0.25, 0.2)
    classes = sorted(str(k) for k in ds.m_NetSettings.m_NetClasses.keys())
    if got != expect or classes != sorted(k for k in NETCLASSES if k != "Default"):
        sys.exit("design rules not loaded from %s: got %s, classes %s. Re-run the generator; do not run "
                 "other KiCad scripts in this folder while it works." % (gp.PRO_FILE, got, classes))
    print("design rules OK: clearance %.2f, track %.2f, via drill %.2f, classes %s" % (got[0], got[1], got[2], ", ".join(classes)))


def finish():
    import pcbnew
    board = pcbnew.LoadBoard(gp.PCB_FILE)
    verify_rules(board)
    if "--place-only" in sys.argv:
        counts, text = drc(board, "placement")   # KiCad 7 can only run DRC once per process
        with open(os.path.join(tempfile.gettempdir(), gp.NAME + "_drc_place.txt"), "w") as fh:
            fh.write(text)
        return
    # Freerouting's result varies between runs; retry until every connection is made.
    placed = os.path.join(tempfile.gettempdir(), gp.NAME + "_placed.kicad_pcb")
    shutil.copy(gp.PCB_FILE, placed)
    for attempt in range(1, 8):
        if attempt > 1:
            # Reload from the project path: a board loaded from elsewhere gets default design rules.
            shutil.copy(placed, gp.PCB_FILE)
            board = pcbnew.LoadBoard(gp.PCB_FILE)
            verify_rules(board)
        route(board)
        gnd = board.FindNet("GND")
        add_zone(board, gnd, pcbnew.F_Cu, "GND_TOP", priority=0)
        add_zone(board, gnd, pcbnew.B_Cu, "GND_BOTTOM", priority=0)
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        board.BuildConnectivity()
        missing = board.GetConnectivity().GetUnconnectedCount(False)
        print("routing attempt %d: %d unconnected" % (attempt, missing))
        if missing == 0:
            break
    os.remove(placed)
    check_routing(board)
    for txt, x, y, size, angle in SILK:
        add_text(board, txt, x, y, size, pcbnew.F_SilkS, angle)
    copper = back_copper(board)
    boxes = []
    for txt, x, y, size in BACK_SILK:
        box = back_text(board, txt, x, y, size, copper, boxes)
        if box:
            boxes.append(box)
    add_back_art(board, boxes)
    pcbnew.SaveBoard(gp.PCB_FILE, board)
    configure_project()          # SaveBoard rewrites the project file; put our rules back
    counts, text = drc(board, "routed")
    with open(os.path.join(tempfile.gettempdir(), gp.NAME + "_drc_routed.txt"), "w") as fh:
        fh.write(text)
    write_features(board)

    export_outputs()


# Manufacturer part numbers for the assembly BOM, and the LCSC numbers that are known
# (check every one against JLCPCB's catalogue before ordering: basic/extended status moves).
MPN = {
    "U1": "Espressif ESP32-S3-WROOM-1-N8", "U2": "HopeRF RFM95W-915S2", "U3": "u-blox SAM-M10Q-00B",
    "U4": "ST LIS3DHTR", "U5": "ST LIS2MDLTR", "U6": "Microchip MCP73831T-2ACI/OT",
    "U7": "Diodes AP2112K-3.3TRG1", "Q1": "AOS AO3400A", "Q2": "AOS AO3400A", "Q3": "AOS AO3401A",
    "D1": "1N4148W", "D2": "Hubei KENTO KT-0603R", "LED": "Worldsemi WS2812B-2020-V6", "J1": "HRO TYPE-C-31-M-12",
    "J2": "JST S2B-PH-SM4-TB", "J4": "Hirose U.FL-R-SMT-1(10)", "J5": "JST SM02B-SRSS-TB",
    "SW1": "C&K PTS645SL50SMTR92LFS", "SW2": "C&K PCM12SMTR",
}
LCSC = {
    "U1": "C2913198", "U3": "C5443880", "U4": "C15134", "U5": "C919695", "U6": "C424093", "U7": "C51118",
    "Q1": "C20917", "Q2": "C20917", "Q3": "C15127", "D1": "C81598", "D2": "C2286", "J1": "C165948",
    "J2": "C295747", "J4": "C88373", "J5": "C160402",
    "SW1": "C221877", "SW2": "C221841", "LED": "C52917434",   # the V6 WS2812B-2020 also runs from 3.3 V (extended part)
}
# Passives by value and package (checked on jlcpcb.com/partdetail 2026-10-20).  Samsung MLCCs and
# UNI-ROYAL 1% resistors, all JLCPCB basic parts except where noted; a higher voltage rating is fine.
PASSIVES = {
    ("100nF 16V X7R", "C_0402_1005Metric"): ("Samsung CL05B104KO5NNNC", "C1525"),
    ("220nF 16V X7R", "C_0402_1005Metric"): ("Samsung CL05B224KO5NNNC", "C16772"),
    ("1uF 10V X5R", "C_0402_1005Metric"): ("Samsung CL05A105KA5NQNC (25 V)", "C52923"),
    ("1uF 10V X5R", "C_0603_1608Metric"): ("Samsung CL10A105KB8NNNC (50 V)", "C15849"),
    ("4.7uF 10V X5R", "C_0603_1608Metric"): ("Samsung CL10A475KO8NNNC (16 V)", "C19666"),
    ("10uF 10V X5R", "C_0805_2012Metric"): ("Samsung CL21A106KAYNNNE (25 V)", "C15850"),
    ("10k", "R_0402_1005Metric"): ("UNI-ROYAL 0402WGF1002TCE", "C25744"),
    ("100", "R_0402_1005Metric"): ("UNI-ROYAL 0402WGF1000TCE", "C25076"),
    ("33", "R_0402_1005Metric"): ("UNI-ROYAL 0402WGF330JTCE", "C25105"),
    ("150k", "R_0402_1005Metric"): ("UNI-ROYAL 0402WGF1503TCE", "C25755"),    # extended: no basic 150k 0402
    ("220", "R_0402_1005Metric"): ("UNI-ROYAL 0402WGF2200TCE", "C25091"),
    ("4.7k", "R_0402_1005Metric"): ("UNI-ROYAL 0402WGF4701TCE", "C25900"),
    ("5.1k", "R_0402_1005Metric"): ("UNI-ROYAL 0402WGF5101TCE", "C25905"),
    ("3.3k", "R_0402_1005Metric"): ("UNI-ROYAL 0402WGF3301TCE", "C25890"),
    ("1k", "R_0402_1005Metric"): ("UNI-ROYAL 0402WGF1001TCE", "C11702"),
    ("100k", "R_0402_1005Metric"): ("UNI-ROYAL 0402WGF1003TCE", "C25741"),
    ("27", "R_0805_2012Metric"): ("UNI-ROYAL 0805W8F270JT5E", "C17594"),      # extended: no basic 27 ohm 0805 1%
}
# JLCPCB's zero-rotation reference differs from KiCad's for these packages.  The values are the
# matching lines of JLCKicadTools' cpl_rotations_db.csv (^SOT-23 -90, ^USB_C_Receptacle_HRO_TYPE-C-31-M-12 180,
# ^LED_WS2812B-2020_PLCC4_2.0x2.0mm 90, ^JST_PH_S 180; checked 2026-10-20, the tool is since deprecated in
# favour of JLCPCB's Fabrication Toolkit, which carries the same table), added to KiCad's rotation for
# top-side parts, as that tool does.  The table has no line for the JST SH: 180 is assumed because KiCad
# draws both horizontal JST footprints the same way (tails at -Y, mouth at +Y).  Confirm pin 1 of every
# polarised part in the JLCPCB preview on the first order; U2, U3, U4, U5 and J5 have no entry and need
# the same look.
ROTATION_FIX = {
    "SOT-23": -90, "SOT-23-5": -90, "USB_C_Receptacle_HRO_TYPE-C-31-M-12": 180,
    "LED_WS2812B-2020_PLCC4_2.0x2.0mm": 90, "JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal": 180,
    "JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal": 180,   # not in the table: by analogy with the PH, unconfirmed
}


MECH_DIR = os.path.join(gp.PROJ, "mech")


def write_features(board):
    """Everything the case generator needs, in mm from the board's top-left (Y down)."""
    import pcbnew
    os.makedirs(MECH_DIR, exist_ok=True)
    parts = {}
    for fp in board.GetFootprints():
        fp.BuildCourtyardCaches()
        cy = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
        pos = fp.GetPosition()
        parts[fp.GetReference()] = {
            "x": pcbnew.ToMM(pos.x) - OX, "y": pcbnew.ToMM(pos.y) - OY,
            "rot": fp.GetOrientationDegrees(), "height": footprint_height(fp),
            "footprint": fp.GetFPIDAsString(),
            "courtyard": [pcbnew.ToMM(cy.GetLeft()) - OX, pcbnew.ToMM(cy.GetTop()) - OY,
                          pcbnew.ToMM(cy.GetRight()) - OX, pcbnew.ToMM(cy.GetBottom()) - OY],
        }
    u1 = PLACEMENT["U1"]
    data = {
        "board": {"center": [CX, CY], "radius": RADIUS, "thickness": THICKNESS},
        "panel": PANEL,
        "fpc_tab": list(FPC_TAB),
        "ring_wall": {"r0": RING_WALL[0], "r1": RING_WALL[1], "gaps": [list(g) for g in RING_WALL_GAPS]},
        "bolts": {"r": BOLT_R, "angles": list(BOLT_ANGLES), "hole": BOLT_HOLE, "pad": BOLT_PAD,
                  "boss_r": BOSS_R, "points": [list(at_angle(a, BOLT_R)) for a in BOLT_ANGLES]},
        "leds": {"r": LED_R, "angles": list(LED_ANGLES),
                 "points": [list(at_angle(a, LED_R)) for a in LED_ANGLES]},
        "button": {"ref": "SW1", "center": list(PLACEMENT["SW1"][:2]), "stem_height": HEIGHTS["SW_SPST_PTS645"],
                   "body": 6.0},
        "power_switch": {"ref": "SW2", "center": list(PLACEMENT["SW2"][:2]), "angle": 245,
                         "knob_r": round(math.hypot(PLACEMENT["SW2"][0] - CX, PLACEMENT["SW2"][1] - CY) + 3.1, 2),
                         "height": HEIGHTS["SW_SPDT_PCM12"]},
        "usb": {"ref": "J1", "center": list(PLACEMENT["J1"][:2]), "angle": 0, "mouth_x": PLACEMENT["J1"][0] + 3.65,
                "shell_w": 8.94, "shell_h": 3.26},
        "battery_connector": {"ref": "J2", "center": list(PLACEMENT["J2"][:2]), "exit_angle": 290,
                              "height": HEIGHTS["JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal"]},
        "motor": {"connector": list(PLACEMENT["J5"][:2]), "lead_hole": list(PLACEMENT["H5"][:2]),
                  "pocket": list(MOTOR_POCKET), "dia": 10.0, "thickness": 3.4},
        "notches": [list(n) for n in NOTCHES],
        "antenna": {"ufl": list(PLACEMENT["J4"][:2]), "pigtail_notch": NOTCHES[0][0],
                    "flex_wall_arc": [15, 90]},
        "gps": {"center": list(PLACEMENT["U3"][:2]), "size": 15.5, "height": HEIGHTS["ublox_SAM-M8Q"]},
        "esp32": {"center": [u1[0], u1[1]], "body": [25.5, 18.0], "antenna_strip_x_max": 7.5,
                  "height": HEIGHTS["ESP32-S3-WROOM-1"]},
        "magnetometer": {"center": list(PLACEMENT["U5"][:2])},
        "charge_led": {"center": list(PLACEMENT["D2"][:2])},
        "test_pads": [list(PLACEMENT["TP1"][:2]), list(PLACEMENT["TP2"][:2])],
        "parts": parts,
    }
    with open(os.path.join(MECH_DIR, gp.NAME + "_features.json"), "w") as fh:
        json.dump(data, fh, indent=1, sort_keys=True)


HAND_SOLDERED = gp.NOT_ASSEMBLED   # panel FPC pads, test pads and mounting holes: not placed


def export_outputs():
    import csv
    docs, fab = os.path.join(gp.PROJ, "docs"), os.path.join(gp.PROJ, "fab")
    os.makedirs(docs, exist_ok=True)
    os.makedirs(fab, exist_ok=True)
    gk.run([gk.KICAD_CLI, "sch", "export", "pdf", "-o", os.path.join(docs, "schematic.pdf"), gp.SCH_FILE])
    work = tempfile.mkdtemp(prefix=gp.NAME + "_gerbers_")
    # Gerbers, drills and the CPL all use the drill/place origin (the board's top-left corner).
    gk.run([gk.KICAD_CLI, "pcb", "export", "gerbers", "-o", work + "/",
            "-l", "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts",
            "--subtract-soldermask", "--use-drill-file-origin", gp.PCB_FILE])
    gk.run([gk.KICAD_CLI, "pcb", "export", "drill", "-o", work + "/", "--format", "excellon", "--drill-origin", "plot",
            "--excellon-separate-th", "--generate-map", "--map-format", "pdf", gp.PCB_FILE])
    with zipfile.ZipFile(os.path.join(fab, gp.NAME + "_gerbers.zip"), "w", zipfile.ZIP_DEFLATED) as zf:
        for name in sorted(os.listdir(work)):
            zf.write(os.path.join(work, name), name)
    shutil.rmtree(work)
    # Pick-and-place, in the column names JLCPCB expects.
    pos = os.path.join(tempfile.gettempdir(), gp.NAME + "_pos.csv")
    gk.run([gk.KICAD_CLI, "pcb", "export", "pos", "-o", pos, "--format", "csv", "--units", "mm",
            "--side", "front", "--use-drill-file-origin", gp.PCB_FILE])
    rows = list(csv.DictReader(open(pos)))
    fp_of = {ref: fp_id.split(":")[1] for ref, _, _, fp_id, _ in gp.PARTS}
    with open(os.path.join(fab, gp.NAME + "_cpl.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for r in rows:
            if r["Ref"] in HAND_SOLDERED:
                continue
            rot = (float(r["Rot"]) + ROTATION_FIX.get(fp_of[r["Ref"]], 0)) % 360
            w.writerow([r["Ref"], r["PosX"] + "mm", r["PosY"] + "mm", "Top", "%g" % rot])
    os.remove(pos)
    # BOM grouped by value and footprint.
    groups = {}
    for ref, _, value, fp_id, _ in gp.PARTS:
        if ref in HAND_SOLDERED:
            continue
        groups.setdefault((value, fp_id.split(":")[1]), []).append(ref)
    with open(os.path.join(fab, gp.NAME + "_bom.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Comment", "Designator", "Footprint", "Quantity", "Manufacturer part", "LCSC Part #"])
        for (value, fp), refs in sorted(groups.items(), key=lambda kv: kv[1][0]):
            key = "LED" if refs[0].startswith("LED") else refs[0]
            mpn, lcsc = PASSIVES.get((value, fp), (MPN.get(key, ""), LCSC.get(key, "")))
            w.writerow([value, ",".join(refs), fp, len(refs), mpn, lcsc])
    for side, copper, silk, mirror in (
            ("front", "F.Cu,F.Mask,Edge.Cuts", "F.SilkS", False),
            ("back", "B.Cu,B.Mask,Edge.Cuts", "B.SilkS", True)):
        parts = []
        for tag, layers in (("cu", copper), ("silk", silk)):
            svg = os.path.join(docs, "pcb-%s-%s.svg" % (side, tag))
            cmd = [gk.KICAD_CLI, "pcb", "export", "svg", "-o", svg, "-l", layers,
                   "--page-size-mode", "2", "--exclude-drawing-sheet"] + (["--mirror"] if mirror else [])
            gk.run(cmd + [gp.PCB_FILE])
            parts.append(svg)
        base, top = open(parts[0]).read(), open(parts[1]).read()
        body = top[top.index(">", top.index("<svg")) + 1:top.rindex("</svg>")]
        svg = os.path.join(docs, "pcb-%s.svg" % side)
        open(svg, "w").write(base[:base.rindex("</svg>")] + body + "</svg>\n")
        for part in parts:
            os.remove(part)
        if shutil.which("rsvg-convert"):
            subprocess.run(["rsvg-convert", "-z", "6", "-b", "white", "-o", svg[:-4] + ".png", svg], check=True)
            os.remove(svg)
    # 3D model of the populated board for the FreeCAD case (origin = board top-left).
    gk.run([gk.KICAD_CLI, "pcb", "export", "step", "--subst-models", "--drill-origin", "-f",
            "-o", os.path.join(MECH_DIR, gp.NAME + ".step"), gp.PCB_FILE])
    prl = os.path.join(gp.PROJ, gp.NAME + ".kicad_prl")
    if os.path.exists(prl):
        os.remove(prl)


if __name__ == "__main__":
    finish()
