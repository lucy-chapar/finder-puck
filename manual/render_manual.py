"""
Pictures for the build guide: the cover, one card per part and one exploded view per step, plus
the zoomed call-outs.  Needs the FreeCAD GUI (it opens a window and closes it when done):

    open -n -a /Applications/FreeCAD.app --args /abs/path/to/manual/render_manual.py

Writes manual/img/*.png and img/scenes.json (the pixel position of every named anchor in
every picture), then img/render.done.  Nothing in the case document is saved.
"""

import json
import math
import os
import sys
import time
import traceback

import FreeCAD
import FreeCADGui
import Part

try:
    MANUAL = os.path.dirname(os.path.abspath(__file__))
except NameError:
    MANUAL = os.path.join(os.getcwd(), "manual")
PUCK = os.path.dirname(MANUAL)
CASE = os.path.join(PUCK, "case")
IMG = os.path.join(MANUAL, "img")
sys.path.insert(0, CASE)
sys.path.insert(0, MANUAL)
import build_case as bc          # noqa: E402  (parameters only; it does not build when imported)
import manual_steps as ms        # noqa: E402

V = FreeCAD.Vector
CX, CY = bc.CX, bc.CY
T = bc.T_BOARD

STEP_W, STEP_H = 1800, 1575     # a little taller than 4:3: the step pages are portrait
CARD = 800
MAG = 720

STYLES = {
    "grey": ((0.62, 0.63, 0.64), 0), "dark": ((0.33, 0.34, 0.36), 0), "teal": ((0.11, 0.66, 0.78), 0),
    "orange": ((0.95, 0.38, 0.05), 0), "brass": ((0.74, 0.62, 0.32), 0), "glass": ((0.80, 0.88, 0.92), 55),
    "trans": ((0.85, 0.88, 0.86), 40), "black": ((0.10, 0.10, 0.11), 0), "panel": ((0.05, 0.10, 0.08), 0),
    "foam": ((0.80, 0.80, 0.78), 0), "white": ((0.92, 0.92, 0.92), 0),
    "pcb": ((0.16, 0.19, 0.18), 0), "parts": ((0.74, 0.75, 0.76), 0), "tealglass": ((0.11, 0.66, 0.78), 60),
    "amber": ((0.85, 0.62, 0.25), 20), "red": ((0.80, 0.15, 0.12), 0),
}
REAL = {
    "Shell": "black", "Plate": "black", "Ring": "black", "Bezel": "trans", "Cap": "orange",
    "Board": "dark", "Panel": "panel", "Crystal": "glass", "Battery": "foam", "Motor": "grey", "Antenna": "brass",
    "Index": "orange", "Cord": "orange", "FoamRing": "foam", "Gasket": "foam", "Pad": "foam", "Sheet": "amber",
    "FPCflat": "brass", "FPCfold": "brass", "MotorLead": "red", "Pigtail": "black", "BattLead": "red",
    "Seal": "black", "ORing": "red", "Door": "black", "DoorGasket": "foam", "SwitchPlug": "black",
    "CrystalGasket": "black", "LidGasket": "black",
}
for i in range(1, 5):
    REAL["Bolt%d" % i] = "orange"
    REAL["Insert%d" % i] = "brass"
    REAL["Washer%d" % i] = "white"
EDGE = (0.13, 0.13, 0.14)


def log(msg):
    with open(os.path.join(IMG, "render.log"), "a") as f:
        f.write(msg + "\n")


def at(angle, r, z):
    x, y = bc.at(angle, r)
    return V(x, y, z)


def pt(x, y, z):
    """Board coordinates (Y down) to a case point."""
    return V(x, -y, z)


# --- Helper solids that are not in the case document --------------------------------------

def wire(points, r=0.6):
    """A round wire along a polyline (cylinders with spheres at the joints)."""
    shape = None
    for a, b in zip(points, points[1:]):
        d = b - a
        if d.Length < 1e-6:
            continue
        seg = Part.makeCylinder(r, d.Length, a, d)
        shape = seg if shape is None else shape.fuse(seg)
        shape = shape.fuse(Part.makeSphere(r, b))
    return shape


def make_helpers(doc):
    s = bc.sector
    # Foam under the ring: one C-shaped piece, open from the ESP32 gap round to the chin gap.
    foam = bc.annulus(bc.R_WALL0 + bc.PANEL_CLEAR, bc.R_WALL1, 0.0, 0.5)
    foam = foam.cut(s(bc.R_LEDGE0, bc.R_WALL1_TOP + 1, bc.WALL_GAPS[0][0], bc.WALL_GAPS[1][1], -1, 1))
    gasket = bc.annulus(16.25, 17.5, bc.Z_PANEL_TOP, bc.Z_CRYSTAL)
    pad = Part.makeBox(34.5, 52.0, 0.5, V(CX - 17.25, CY - 26.0, bc.Z_FLOOR))
    sheet = Part.makeBox(36.0, 52.0, 0.2, V(CX - 18.0, CY - 26.0, bc.Z_FLOOR + 0.5 + 5.3))
    chin = CY - bc.PANEL["chin_reach"] + bc.BY            # case y of the chin end (-20.3)
    pads_y = -(bc.F["fpc_tab"][1] + 1.4)                  # the pad row, board y 52 -> case y -52
    # Drawn 0.4 mm thick (the real flex is 0.1) so it survives the renderer's depth offset on the board.
    flat = Part.makeBox(9.0, 7.5, 0.4, V(CX - 4.5, chin - 4.2, 0.0))           # tail, out past the chin
    for i in range(12):                                                      # the 12 fingers on the pads
        x = CX + (i - 5.5) * 0.7
        flat = flat.fuse(Part.makeBox(0.4, 2.6, 0.4, V(x - 0.2, pads_y - 1.3, 0.0)))
    fold = Part.makeBox(9.0, 0.4, bc.LEDGE_Z - 0.4, V(CX - 4.5, chin - 0.4, 0.4))
    fold = fold.fuse(Part.makeBox(9.0, 6.0, 0.4, V(CX - 4.5, chin - 0.4, 0.0)))
    # Leads: motor up through H5; antenna pigtail along the floor and, with the battery lead, up through the notch.
    h5 = bc.pt(*bc.F["motor"]["lead_hole"])
    j5 = bc.pt(*bc.F["motor"]["connector"])
    j4 = bc.pt(*bc.F["antenna"]["ufl"])
    j2 = bc.pt(*bc.F["battery_connector"]["center"])
    z_motor_top = bc.Z_FLOOR - 0.6 + bc.F["motor"]["thickness"]
    motor_lead = wire([V(MOTOR[0], MOTOR[1], z_motor_top), V(h5[0], h5[1], -5.0), V(h5[0], h5[1], 1.5),
                       V(j5[0] - 1.5, j5[1], 2.0)], 0.45)
    a0 = bc.FLEX_ARC[0]
    angle, width, depth = bc.BATT_NOTCH
    notch = at(angle, bc.R_BOARD - depth / 2, -4.5)
    pigtail = wire([at(a0, bc.R_IN - 0.4, -6.5), at(a0 - 20, bc.R_IN - 1.2, -7.0), at(a0 - 45, bc.R_IN - 1.5, -7.0),
                    V(notch.x + 0.8, notch.y, -6.5), V(notch.x + 0.8, notch.y, 2.0), V(j4[0] + 0.3, j4[1] - 1.2, 2.6)], 0.55)
    batt_lead = wire([V(CX + 6.0, CY - 25.5, -4.5), V(notch.x - 4.0, notch.y + 1.5, -4.5), V(notch.x, notch.y, -4.5),
                      V(notch.x, notch.y, 2.0), V(j2[0] + 1.5, j2[1] - 5.6, 3.0)], 0.6)
    # Cord: through the chord bore and a half loop outside at 6 o'clock.
    half = math.sqrt(bc.R_OUT ** 2 - bc.LANYARD_R ** 2)
    yb = CY - bc.LANYARD_R
    loop = Part.makeTorus(half, 1.25, V(CX, yb, bc.LANYARD_Z), V(0, 0, 1), -180, 180, 180)
    loop.rotate(V(CX, yb, bc.LANYARD_Z), V(0, 0, 1), 180)
    cord = loop.fuse(Part.makeCylinder(1.25, 2 * half, V(CX - half, yb, bc.LANYARD_Z), V(1, 0, 0)))
    for name, shape in (("FoamRing", foam), ("Gasket", gasket), ("Pad", pad), ("Sheet", sheet), ("FPCflat", flat),
                        ("FPCfold", fold), ("Cord", cord), ("MotorLead", motor_lead), ("Pigtail", pigtail),
                        ("BattLead", batt_lead)):
        o = doc.addObject("Part::Feature", name)
        o.Shape = shape
    doc.recompute()


# --- Scene definitions -------------------------------------------------------------------
# A scene: dict(show={name: style}, move={name: Placement}, anchors={name: V}, view, W, H)
# Assembly states, in build order.

def state(upto):
    order = [
        ("Shell",), ("Insert1", "Insert2", "Insert3", "Insert4"), ("Motor", "Antenna", "Pigtail"),
        ("Pad", "Battery", "Sheet", "BattLead"), ("Board", "MotorLead"), ("FoamRing", "Ring"), ("Panel", "FPCfold"),
        ("Gasket", "Crystal", "CrystalGasket"), ("Cap", "ORing"), ("Bezel", "LidGasket"),
        ("Seal", "Door", "DoorGasket", "Plate") + tuple("Washer%d" % i for i in range(1, 5)) + tuple("Bolt%d" % i for i in range(1, 5)),
        ("Index", "Cord", "SwitchPlug"),
    ]
    show = {}
    for group in order[:upto + 1]:
        for n in group:
            show[n] = "dark" if n == "Board" else "grey"
    return show


def lift(dz):
    return FreeCAD.Placement(V(0, 0, dz), FreeCAD.Rotation())


def shift(dx, dy, dz=0):
    return FreeCAD.Placement(V(dx, dy, dz), FreeCAD.Rotation())


def tilt(angle):
    """Rotate the panel about the hinge line at its chin end (case y of the chin, Z 0)."""
    chin = CY - bc.PANEL["chin_reach"] + bc.BY
    return FreeCAD.Placement(V(0, 0, 0), FreeCAD.Rotation(V(1, 0, 0), angle), V(CX, chin, 0.0))


BOLT_XY = [bc.pt(x, y) for x, y in bc.BOLTS["points"]]
LED_XY = [bc.pt(x, y) for x, y in bc.LEDS["points"]]
BTN = bc.pt(*bc.BUTTON["center"])
MOTOR = bc.pt(*bc.MOTOR_POCKET)
ANT = bc.at((bc.FLEX_ARC[0] + bc.FLEX_ARC[1]) / 2, bc.R_IN - 0.5)
F = bc.F
CHIN = CY - bc.PANEL["chin_reach"] + bc.BY
HALF = math.sqrt(bc.R_OUT ** 2 - bc.LANYARD_R ** 2)


def scenes():
    S = {}
    # Cover and the parts cards.
    cover = {n: REAL[n] for n in state(11)}
    cover["Board"] = "dark"
    S["cover"] = dict(show=cover, view="iso", W=STEP_W, H=STEP_H)
    S["face"] = dict(show=cover, view="top", W=STEP_W, H=STEP_H)
    cards = {
        "card_shell": {"Shell": "grey"}, "card_plate": {"Plate": "grey"}, "card_ring": {"Ring": "grey"},
        "card_bezel": {"Bezel": "trans"}, "card_cap": {"Cap": "orange"}, "card_board": {"Board": "dark"},
        "card_panel": {"Panel": "panel", "FPCflat": "brass"}, "card_crystal": {"Crystal": "glass"},
        "card_battery": {"Battery": "foam"}, "card_motor": {"Motor": "grey"}, "card_antenna": {"Antenna": "brass"},
        "card_bolt": {"Bolt1": "orange"}, "card_insert": {"Insert1": "brass"}, "card_index": {"Index": "orange"},
        "card_foamring": {"FoamRing": "foam"}, "card_gasket": {"Gasket": "foam"}, "card_pad": {"Pad": "foam"},
        "card_sheet": {"Sheet": "amber"}, "card_cord": {"Cord": "orange"},
        "card_seal": {"Seal": "foam"}, "card_washer": {"Washer1": "white"}, "card_oring": {"ORing": "red"},
        "card_door": {"Door": "grey"}, "card_doorgasket": {"DoorGasket": "foam"}, "card_swplug": {"SwitchPlug": "grey"},
        "card_crystalgasket": {"CrystalGasket": "foam"}, "card_lidgasket": {"LidGasket": "foam"},
    }
    for name, show in cards.items():
        S[name] = dict(show=show, view="iso", W=CARD, H=CARD)
    S["card_shell"]["view"] = "iso_top"
    S["card_plate"]["view"] = "iso_top"
    S["card_index"]["move"] = {}
    S["card_crystalgasket"]["view"] = "iso_top"
    S["card_lidgasket"]["view"] = "iso_top"

    # Step 1: inserts into the shell.
    dz = 22.0
    s = dict(show=state(0), move={}, anchors={}, view="iso", W=STEP_W, H=STEP_H)
    for i, (px, py) in enumerate(BOLT_XY, 1):
        s["show"]["Insert%d" % i] = "teal"
        s["move"]["Insert%d" % i] = lift(dz)
        s["anchors"]["ins%d_from" % i] = V(px, py, -T - bc.INSERT_L + dz - 0.5)
        s["anchors"]["ins%d_to" % i] = V(px, py, -T + 0.3)
    S["s01"] = s
    S["s01_mag"] = dict(show=state(1), at=V(BOLT_XY[2][0], BOLT_XY[2][1], -T), height=13.0)
    # Step 2: motor and antenna (the pigtail is drawn once the antenna is in).
    dz = 16.0
    s = dict(show=state(1), move={"Motor": lift(dz), "Antenna": lift(dz)}, anchors={}, view="iso", W=STEP_W, H=STEP_H)
    s["show"].update(Motor="teal", Antenna="teal")
    s["anchors"]["motor_from"] = V(MOTOR[0], MOTOR[1], bc.Z_FLOOR - 0.6 + dz - 0.5)
    s["anchors"]["motor_to"] = V(MOTOR[0], MOTOR[1], bc.Z_FLOOR - 0.3)
    s["anchors"]["ant_from"] = V(ANT[0], ANT[1], bc.FLEX_Z[0] + dz - 0.5)
    s["anchors"]["ant_to"] = V(ANT[0], ANT[1], (bc.FLEX_Z[0] + bc.FLEX_Z[1]) / 2)
    S["s02"] = s
    S["s02_mag"] = dict(show=state(2), at=V(MOTOR[0], MOTOR[1], bc.Z_FLOOR), height=18.0)
    # Step 3: pad, battery, insulation sheet.
    s = dict(show=state(2), move={"Pad": lift(8.0), "Battery": lift(20.0), "Sheet": lift(32.0), "BattLead": lift(20.0)},
             anchors={}, view="iso", W=STEP_W, H=STEP_H)
    s["show"].update(Pad="teal", Battery="teal", Sheet="teal", BattLead="red")
    s["anchors"]["pad_from"] = V(CX - 12, CY - 20, bc.Z_FLOOR + 8.0 - 0.5)
    s["anchors"]["pad_to"] = V(CX - 12, CY - 20, bc.Z_FLOOR + 0.2)
    s["anchors"]["batt_from"] = V(CX + 10, CY + 10, bc.Z_FLOOR + 0.5 + 20.0 - 0.5)
    s["anchors"]["batt_to"] = V(CX + 10, CY + 10, bc.Z_FLOOR + 0.8)
    s["anchors"]["sheet_from"] = V(CX - 10, CY + 18, bc.Z_FLOOR + 5.8 + 32.0 - 0.3)
    s["anchors"]["sheet_to"] = V(CX - 10, CY + 18, bc.Z_FLOOR + 6.0)
    S["s03"] = s
    # Step 4: board over the three leads.
    dz = 26.0
    s = dict(show=state(3), move={"Board": lift(dz)}, anchors={}, view="iso", W=STEP_W, H=STEP_H)
    s["show"].update(Board="dark", MotorLead="teal", Pigtail="teal", BattLead="teal")
    s["anchors"]["board_from"] = V(CX, CY - 30, -T + dz - 0.5)
    s["anchors"]["board_to"] = V(CX, CY - 30, -T + 0.3)
    h5 = bc.pt(*F["motor"]["lead_hole"])
    s["anchors"]["lead_hole"] = V(h5[0], h5[1], -T + 1.0)
    s["anchors"]["batt_notch"] = at(bc.BATT_NOTCH[0], bc.R_BOARD - 0.8, -T + 1.0)
    S["s04"] = s
    leads = dict(state(4), MotorLead="teal", Pigtail="teal", BattLead="teal")
    S["s04_mag_h5"] = dict(show=leads, at=V(h5[0], h5[1], 0.0), height=14.0)
    S["s04_mag_notch"] = dict(show=leads, at=at(bc.BATT_NOTCH[0], bc.R_BOARD - 0.8, -1.0), height=16.0, view="top")
    # Step 5: connect motor and antenna.
    s = dict(show=state(4), move={}, anchors={}, view="iso", W=STEP_W, H=STEP_H)
    j5 = pt(F["motor"]["connector"][0], F["motor"]["connector"][1], 2.0)
    j4 = pt(F["antenna"]["ufl"][0], F["antenna"]["ufl"][1], 1.5)
    j2 = pt(F["battery_connector"]["center"][0], F["battery_connector"]["center"][1], 3.0)
    s["anchors"].update(j5=j5, j4=j4)
    S["s05"] = s
    S["s05_mag_j5"] = dict(show=dict(state(4), MotorLead="teal"), at=j5, height=12.0)
    S["s05_mag_j4"] = dict(show=dict(state(4), Pigtail="teal"), at=j4, height=10.0)
    # Step 6: foam ring and ring.
    s = dict(show=state(4), move={"FoamRing": lift(10.0), "Ring": lift(22.0)}, anchors={}, view="iso", W=STEP_W, H=STEP_H)
    s["show"].update(FoamRing="teal", Ring="teal")
    s["anchors"]["foam_from"] = at(160, 18.3, 10.0 - 0.3)
    s["anchors"]["foam_to"] = at(160, 18.3, 0.5)
    s["anchors"]["ring_from"] = at(20, 18.4, 22.0 + 0.1)
    s["anchors"]["ring_to"] = at(20, 18.4, 0.8)
    s["anchors"]["ring_gap"] = at(270, 18.4, 22.0 + 2.0)
    S["s06"] = s
    S["s06_mag"] = dict(show=state(5), at=at(270, 18.0, 2.0), height=20.0)
    # Step 7: solder the panel standing on its chin.
    s = dict(show=state(5), move={"Panel": tilt(80)}, anchors={}, view="iso", W=STEP_W, H=STEP_H)
    s["show"].update(Panel="tealglass", FPCflat="teal")     # see-through, so the flex on the pads shows
    s["anchors"]["fpc_from"] = V(CX, CY - 16.0, 9.0)
    s["anchors"]["fpc_to"] = V(CX, CY - 16.0, 0.6)
    S["s07"] = s
    # Seen from straight above with the panel hidden: the 12 fingers on the pads, the two locating holes.
    mag = dict(show=state(5), move={}, at=V(CX, CY - 18.0, 0.0), height=16.0, view="top")
    mag["show"]["FPCflat"] = "teal"
    S["s07_mag"] = mag
    # Step 8: fold the panel down.
    s = dict(show=state(5), move={"Panel": tilt(45)}, anchors={}, view="iso", W=STEP_W, H=STEP_H)
    s["show"].update(Panel="teal", FPCflat="teal")
    s["anchors"]["fold_from"] = V(CX, CHIN + 38 * math.cos(math.radians(45)) - 4.75 * math.sin(math.radians(45)),
                                  38 * math.sin(math.radians(45)) + 4.75 * math.cos(math.radians(45)))
    s["anchors"]["fold_to"] = V(CX, CY + 16.0, bc.Z_PANEL_TOP + 0.5)
    S["s08"] = s
    # Step 9: plug in the battery (only now).
    s = dict(show=state(6), move={}, anchors={}, view="iso", W=STEP_W, H=STEP_H)
    s["show"]["BattLead"] = "teal"
    jb = bc.pt(*F["battery_connector"]["center"])
    nt = at(bc.BATT_NOTCH[0], bc.R_BOARD - bc.BATT_NOTCH[2] / 2, 4.0)
    s["anchors"]["blead_from"] = V(nt.x, nt.y, 4.0)
    s["anchors"]["blead_to"] = V(jb[0] + 1.0, jb[1] - 5.0, 3.5)
    s["anchors"]["j2"] = j2
    S["s09"] = s
    S["s09_mag_j2"] = dict(show=dict(state(6), BattLead="teal"), at=j2, height=14.0)
    # Step 10: gasket, crystal and the crystal's gasket.
    s = dict(show=state(6), move={"Gasket": lift(9.0), "Crystal": lift(18.0), "CrystalGasket": lift(27.0)},
             anchors={}, view="iso", W=STEP_W, H=STEP_H)
    s["show"].update(Gasket="teal", Crystal="teal", CrystalGasket="teal")
    s["anchors"]["gasket_from"] = at(160, 17.0, bc.Z_PANEL_TOP + 9.0 - 0.3)
    s["anchors"]["gasket_to"] = at(160, 17.0, bc.Z_PANEL_TOP + 0.4)
    s["anchors"]["crystal_from"] = at(20, 17.5, bc.Z_CRYSTAL + 18.0 - 0.3)
    s["anchors"]["crystal_to"] = at(20, 17.5, bc.Z_CRYSTAL + 0.4)
    s["anchors"]["cgasket_from"] = at(200, 18.1, bc.Z_CRYSTAL_TOP + 27.0 - 0.3)
    s["anchors"]["cgasket_to"] = at(200, 18.1, bc.Z_LIP0 + 18.0 + 0.4)
    S["s10"] = s
    # Step 11: cap, before the bezel (its flange is captive under the bezel's sleeve).
    s = dict(show=state(7), move={"Cap": lift(20.0), "ORing": lift(20.0)}, anchors={}, view="iso", W=STEP_W, H=STEP_H)
    s["show"].update(Cap="teal", ORing="red")
    s["anchors"]["cap_from"] = V(BTN[0], BTN[1], 4.0 + 20.0 - 0.5)
    s["anchors"]["cap_to"] = V(BTN[0], BTN[1], bc.BUTTON["stem_height"] + 0.3)
    S["s11"] = s
    S["s11_mag"] = dict(show=state(8), at=V(BTN[0], BTN[1], 6.0), height=16.0)
    # Step 12: bezel, with the lid gasket stuck on its flange.
    s = dict(show=state(8), move={"Bezel": lift(20.0), "LidGasket": lift(20.0)}, anchors={}, view="iso", W=STEP_W, H=STEP_H)
    s["show"].update(Bezel="teal", LidGasket="foam")
    s["anchors"]["bezel_from"] = at(0, 20.5, bc.PIPE_Z0 + 20.0 - 0.3)
    s["anchors"]["bezel_to"] = at(0, 20.5, bc.Z_FACE + 0.3)
    s["anchors"]["pipe"] = V(LED_XY[3][0], LED_XY[3][1], 3.0)
    S["s12"] = s
    S["s12_mag"] = dict(show=state(9), at=V(LED_XY[3][0], LED_XY[3][1], 3.5), height=14.0)
    # Step 13: test before the plate goes on.
    s = dict(show=state(9), move={}, anchors={}, view="iso", W=STEP_W, H=STEP_H)
    s["anchors"]["sw_from"] = at(F["power_switch"]["angle"], 48.0, 1.0)
    s["anchors"]["sw_to"] = at(F["power_switch"]["angle"], bc.R_OUT + 0.5, 1.0)
    s["anchors"]["usb_from"] = at(F["usb"]["angle"], 50.0, 1.5)
    s["anchors"]["usb_to"] = at(F["usb"]["angle"], bc.R_OUT + 0.5, 1.5)
    S["s13"] = s
    # Step 14: plate and bolts.
    dzp, dzb = 24.0, 52.0
    dzs = 8.0
    out_door = bc.at(F["usb"]["angle"], 12.0)                 # the door (with its gasket) drawn out from its pocket
    mv_door = shift(out_door[0] - CX, out_door[1] - CY)
    s = dict(show=state(9), move={"Plate": lift(dzp), "Seal": lift(dzs), "Door": mv_door, "DoorGasket": mv_door},
             anchors={}, view="iso", W=STEP_W, H=STEP_H)
    s["show"].update(Plate="teal", Seal="teal", Door="teal", DoorGasket="teal")
    s["anchors"]["door_from"] = at(F["usb"]["angle"], bc.DOOR_IN + bc.DOOR_T + 12.0, 1.5)
    s["anchors"]["door_to"] = at(F["usb"]["angle"], bc.DOOR_IN + bc.DOOR_T + 0.5, 1.5)
    s["anchors"]["seal_from"] = at(200, bc.R_OUT - 0.7, bc.Z_SPLIT + dzs - 0.3)
    s["anchors"]["seal_to"] = at(200, bc.R_OUT - 0.7, bc.Z_SPLIT + 0.3)
    s["anchors"]["plate_from"] = at(270, 34.0, bc.Z_SPLIT + dzp - 0.5)
    s["anchors"]["plate_to"] = at(270, 34.0, bc.Z_SPLIT + 0.4)
    zh = bc.Z_FACE - (bc.HEAD_H - bc.HEAD_PROUD)
    for i, (px, py) in enumerate(BOLT_XY, 1):
        s["show"]["Bolt%d" % i] = "teal"
        s["move"]["Bolt%d" % i] = lift(dzb)
        s["show"]["Washer%d" % i] = "teal"
        s["move"]["Washer%d" % i] = lift(dzb - 4.0)
        s["anchors"]["bolt%d_from" % i] = V(px, py, zh - bc.BOLT_L + dzb - 0.5)
        s["anchors"]["bolt%d_to" % i] = V(px, py, bc.Z_FACE + dzp + 0.3)
    S["s14"] = s
    S["s14_mag"] = dict(show=state(10), at=V(BOLT_XY[1][0], BOLT_XY[1][1], bc.Z_FACE), height=11.0)
    # Step 15: index stub and cord.
    out_sw = bc.at(F["power_switch"]["angle"], 14.0)            # the switch plug drawn pulled out of its slot
    mv_sw = shift(out_sw[0] - CX, out_sw[1] - CY)
    s = dict(show=state(10), move={"Index": lift(12.0), "Cord": shift(0, -16.0), "SwitchPlug": mv_sw},
             anchors={}, view="iso", W=STEP_W, H=STEP_H)
    s["show"].update(Index="teal", Cord="teal", SwitchPlug="teal")
    s["anchors"]["swplug_from"] = at(F["power_switch"]["angle"], bc.R_OUT + 13.0, 0.6)
    s["anchors"]["swplug_to"] = at(F["power_switch"]["angle"], bc.R_OUT + 0.2, 0.6)
    s["anchors"]["index_from"] = V(CX, CY + bc.INDEX_R, bc.Z_FACE - bc.INDEX_DEPTH + 12.0 - 0.4)
    s["anchors"]["index_to"] = V(CX, CY + bc.INDEX_R, bc.Z_FACE + 0.3)
    s["anchors"]["cord_from"] = V(CX - HALF, CY - bc.LANYARD_R - 16.0 + 1.5, bc.LANYARD_Z)
    s["anchors"]["cord_to"] = V(CX - HALF - 0.5, CY - bc.LANYARD_R - 0.5, bc.LANYARD_Z)
    S["s15"] = s
    S["s15_mag"] = dict(show=state(11), at=V(CX, CY + bc.INDEX_R, bc.Z_FACE), height=11.0)
    # Step 16: switch on, charge, mark.
    s = dict(show=state(11), move={}, anchors={}, view="iso", W=STEP_W, H=STEP_H)
    s["anchors"]["sw_from"] = at(F["power_switch"]["angle"], 48.0, 1.0)
    s["anchors"]["sw_to"] = at(F["power_switch"]["angle"], bc.R_OUT + 0.5, 1.0)
    s["anchors"]["usb_from"] = at(F["usb"]["angle"], 50.0, 1.5)
    s["anchors"]["usb_to"] = at(F["usb"]["angle"], bc.R_OUT + 0.5, 1.5)
    S["s16"] = s
    return S


SCENES = scenes()


# --- Rendering ---------------------------------------------------------------------------

def main():
    os.makedirs(IMG, exist_ok=True)
    for f in ("render.log", "render.done"):
        if os.path.exists(os.path.join(IMG, f)):
            os.remove(os.path.join(IMG, f))
    FreeCAD.ParamGet("User parameter:BaseApp/Preferences/View").SetInt("AntiAliasing", 4)
    # Standard views animate by default; a picture saved mid-turn would be neither top nor isometric.
    FreeCAD.ParamGet("User parameter:BaseApp/Preferences/View").SetBool("UseNavigationAnimations", False)
    FreeCAD.ParamGet("User parameter:BaseApp/Preferences/View").SetBool("UseAutoRotation", False)
    doc = FreeCAD.openDocument(os.path.join(CASE, "finder_puck_case.FCStd"))
    make_helpers(doc)
    FreeCADGui.activateWorkbench("PartWorkbench")
    gdoc = FreeCADGui.ActiveDocument
    view = gdoc.ActiveView
    view.setCameraType("Orthographic")
    cam = view.getCameraNode()
    names = [o.Name for o in doc.Objects]
    # Shapes carry their own placement when they are assigned (the board sits 1.6 mm down that way);
    # the scene moves are applied on top of it, never instead of it.
    BASE = {n: doc.getObject(n).Placement for n in names}
    try:
        from pivy import coin
        rm = view.getViewer().getSoRenderManager()
        rm.setAutoClipping(coin.SoRenderManager.NO_AUTO_CLIPPING)
        log("render manager autoclip now %s" % rm.getAutoClipping())
    except Exception as e:
        log("auto clipping stays on: %s" % e)

    # "Flat Lines" pushes filled faces back so edges draw on top; FreeCAD's default amount lets a part
    # up to a millimetre behind a face bleed through it (the GPS module under the plate's 0.6 mm skin).
    try:
        from pivy import coin
        sa = coin.SoSearchAction()
        sa.setType(coin.SoPolygonOffset.getClassTypeId())
        sa.setInterest(coin.SoSearchAction.ALL)
        sa.setSearchingAll(True)
        seen = set()
        for n in names:
            sa.apply(gdoc.getObject(n).RootNode)
            for path in sa.getPaths():
                node = coin.cast(path.getTail(), "SoPolygonOffset")
                if n not in seen:
                    log("%s polygon offset factor %.2f units %.2f" % (n, node.factor.getValue(), node.units.getValue()))
                    seen.add(n)
                node.factor.setValue(0.3)
                node.units.setValue(0.3)
    except Exception as e:
        log("polygon offset unchanged: %s" % e)
    only = None
    if os.path.exists(os.path.join(IMG, "only.txt")):
        only = set(open(os.path.join(IMG, "only.txt")).read().split())
    # The populated board: dark substrate, light parts (per-face colours, shaded without edges).
    board = doc.getObject("Board")
    BOARD_FACES = []
    for f in board.Shape.Faces:
        b = f.BoundBox
        BOARD_FACES.append(STYLES["pcb"][0] if (b.ZMax <= 0.02 and b.ZMin >= -T - 0.02) else STYLES["parts"][0])

    def settle(n=4):
        for _ in range(n):
            FreeCADGui.updateGui()
            time.sleep(0.08)

    def apply(show, move):
        for n in names:
            vo = gdoc.getObject(n)
            obj = doc.getObject(n)
            vis = n in show
            vo.Visibility = vis
            if vis:
                col, tr = STYLES[show[n]]
                # the populated board has thousands of tiny edges: shade it without lines
                vo.DisplayMode = "Shaded" if n in ("Board", "FPCflat", "FPCfold") else "Flat Lines"
                vo.ShapeColor = col
                if n == "Board":
                    vo.DiffuseColor = BOARD_FACES
                vo.LineColor = EDGE
                vo.LineWidth = 1.5
                vo.Transparency = tr
            obj.Placement = move.get(n, FreeCAD.Placement()).multiply(BASE[n])
        doc.recompute()

    def project(p, W, H):
        qx, qy = cam_coords(p)
        h = cam.height.getValue()
        aspect = float(W) / H
        u = 0.5 + qx / (h * aspect)
        v = 0.5 - qy / h
        return [round(u * W, 1), round(v * H, 1)]

    def look(view_name):
        {"iso": view.viewIsometric, "top": view.viewTop, "bottom": view.viewBottom,
         "front": view.viewFront, "iso_top": view.viewIsometric}[view_name]()
        settle(10)                       # let any view animation finish before framing

    def cam_coords(p, depth=False):
        from pivy import coin
        pos = cam.position.getValue()
        inv = cam.orientation.getValue().inverse()
        src = coin.SbVec3f(p.x - pos[0], p.y - pos[1], p.z - pos[2])
        try:
            q = inv.multVec(src)
        except TypeError:
            q = coin.SbVec3f()
            inv.multVec(src, q)
        return (q[0], q[1], -q[2]) if depth else (q[0], q[1])

    def clip(show):
        """Near/far planes hugging the visible parts.  Coin offsets filled faces behind their edges
        by an amount that scales with the depth range; with automatic planes a 0.6 mm skin lets
        the part behind it bleed through."""
        bb = None
        for n in show:
            b = doc.getObject(n).Shape.BoundBox
            bb = b if bb is None else bb.united(b)
        ds = [cam_coords(V(x, y, z), True)[2] for x in (bb.XMin, bb.XMax) for y in (bb.YMin, bb.YMax)
              for z in (bb.ZMin, bb.ZMax)]
        cam.nearDistance.setValue(max(0.1, min(ds) - 1.0))
        cam.farDistance.setValue(max(ds) + 1.0)

    def frame(show, W, H, air=1.06):
        """Point the camera at the visible parts and set its height so they just fill the picture."""
        bb = None
        for n in show:
            b = doc.getObject(n).Shape.BoundBox
            bb = b if bb is None else bb.united(b)
        corners = [V(x, y, z) for x in (bb.XMin, bb.XMax) for y in (bb.YMin, bb.YMax) for z in (bb.ZMin, bb.ZMax)]
        xs, ys = zip(*[cam_coords(c) for c in corners])
        aspect = float(W) / H
        h = max(max(ys) - min(ys), (max(xs) - min(xs)) / aspect) * air
        # recentre: move the camera within its own plane so the box centre projects to the middle
        dirv = view.getViewDirection()
        centre = bb.Center
        p = centre - dirv * 200.0
        cam.position.setValue(p.x, p.y, p.z)
        cam.height.setValue(h)

    out = {}
    settle(8)
    for name, sc in SCENES.items():
        if only and name not in only:
            continue
        t0 = time.time()
        if "at" in sc:        # magnifier: a zoomed crop of a state (no fitAll: its animation would move the camera back)
            apply(sc["show"], sc.get("move", {}))
            look(sc.get("view", "iso"))
            dirv = view.getViewDirection()
            p = sc["at"] - dirv * 150.0
            cam.position.setValue(p.x, p.y, p.z)
            cam.height.setValue(sc["height"])
            clip(sc["show"])
            settle(10)
            fname = name + ".png"
            view.saveImage(os.path.join(IMG, fname), MAG, MAG, "White")
            out[name] = dict(file=fname, W=MAG, H=MAG, anchors={})
        else:
            apply(sc["show"], sc.get("move", {}))
            look(sc["view"])
            settle()
            view.fitAll()
            settle()
            W, H = sc["W"], sc["H"]
            settle(6)                    # fitAll animates; let it finish before taking over the camera
            frame(sc["show"], W, H)
            clip(sc["show"])
            settle(6)
            fname = name + ".png"
            view.saveImage(os.path.join(IMG, fname), W, H, "White")
            anchors = {k: project(v, W, H) for k, v in sc.get("anchors", {}).items()}
            out[name] = dict(file=fname, W=W, H=H, anchors=anchors,
                             cam=dict(height=cam.height.getValue(), pos=list(cam.position.getValue().getValue())))
        log("%-16s %.1fs" % (name, time.time() - t0))
    path = os.path.join(IMG, "scenes.json")
    if only and os.path.exists(path):
        merged = json.load(open(path))
        merged.update(out)
        out = merged
    with open(path, "w") as f:
        json.dump(out, f, indent=1, sort_keys=True)
    apply({}, {})
    for n in ("FoamRing", "Gasket", "Pad", "Sheet", "FPCflat", "FPCfold", "Cord", "MotorLead", "Pigtail", "BattLead"):
        doc.removeObject(n)
    FreeCAD.closeDocument(doc.Name)


try:
    main()
    open(os.path.join(IMG, "render.done"), "w").write("ok\n")
except Exception:
    os.makedirs(IMG, exist_ok=True)
    log(traceback.format_exc())
    open(os.path.join(IMG, "render.done"), "w").write("error\n")
FreeCADGui.getMainWindow().close()
