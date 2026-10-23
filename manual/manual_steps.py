"""
Content of the build guide: parts, tools and the assembly steps.

Shared by render_manual.py (FreeCAD, makes the pictures) and build_manual.py (lays out the PDF).
Scene names refer to render_manual.SCENES; anchor names are the points that script projects
into each picture so the layout can draw arrows and magnifier call-outs on top of it.
"""

TITLE = "Finder Puck"
SUBTITLE = "Build Guide"
VARIANT = "Round-screen puck, through-bolted"
VERSION = "0.2.0"
BRAND = {
    "name": "RESEARCH + DESIRE",
    "logo": "assets/rad-logo.png",
    "support_label": "Support",
    "support": "support@researchanddesire.com",
    "docs_label": "Design files",
    "docs": "README.md in the finder-puck repository",
    "docs_url": None,       # a URL here also puts a QR code on the cover and back page
}

# Parts: key -> (group, display name, quantity, detail line, picture).
# Pictures are render_manual card scenes.
PARTS = {
    "shell":   ("printed", "Shell", 1, "black", "card_shell"),
    "plate":   ("printed", "Plate", 1, "black", "card_plate"),
    "ring":    ("printed", "Ring", 1, "black", "card_ring"),
    "bezel":   ("printed", "Bezel", 1, "clear resin", "card_bezel"),
    "cap":     ("printed", "Button cap", 1, "orange", "card_cap"),
    "usbplug": ("printed", "USB-C plug", 1, "TPU 85A–95A, black", "card_usbplug"),
    "swplug":  ("printed", "Switch plug", 1, "TPU 85A–95A, black", "card_swplug"),
    "board":   ("electronics", "Assembled board", 1, "factory-assembled PCB", "card_board"),
    "panel":   ("electronics", "Round display", 1, "1.28″ GC9A01, bare panel", "card_panel"),
    "crystal": ("electronics", "Crystal", 1, "Ø37.5 × 1.0 mm glass", "card_crystal"),
    "battery": ("electronics", "LiPo cell", 1, "503450, 28 AWG leads, JST PH", "card_battery"),
    "motor":   ("electronics", "Vibration motor", 1, "Ø10 mm coin, JST SH lead", "card_motor"),
    "antenna": ("electronics", "915 MHz antenna", 1, "adhesive flex 40 × 7 mm (2J 2JF0515P), U.FL", "card_antenna"),
    "bolt":    ("hardware", "Bolt M2.5 × 12", 4, "socket cap, aluminium (non-magnetic)", "card_bolt"),
    "insert":  ("hardware", "Heat-set insert M2.5", 4, "Ruthex RX-M2.5x5.7, 4 mm hole", "card_insert"),
    "index":   ("hardware", "Index stub", 1, "orange 1.75 mm filament, trim flush", "card_index"),
    "foamring": ("hardware", "Foam ring", 1, "0.5 mm, Ø36.3–38 mm, open 10 to 5 o'clock", "card_foamring"),
    "gasket":  ("hardware", "Gasket", 1, "0.3 mm foam, Ø32.5–35 mm", "card_gasket"),
    "pad":     ("hardware", "Battery pad", 1, "0.5 mm foam, 34 × 50 mm", "card_pad"),
    "sheet":   ("hardware", "Insulation sheet", 1, "0.2 mm Kapton or PET, 36 × 52 mm", "card_sheet"),
    "cord":    ("hardware", "Cord", 1, "Ø2.5 mm, 300 mm", "card_cord"),
    "seal":    ("hardware", "Seam seal", 1, "1.0 mm closed-cell foam, Ø73.5–76.3 mm, open at 3 o'clock", "card_seal"),
    "washer":  ("hardware", "Washer M2.5", 4, "nylon DIN 433, 5 × 2.7 × 0.5 mm", "card_washer"),
    "oring":   ("hardware", "O-ring", 1, "9 × 1 mm silicone", "card_oring"),
}
PART_GROUPS = (("printed", "3D printed"), ("electronics", "Electronics"), ("hardware", "Hardware"))

# Tools: (group, name, icon).  Icons are drawn by build_manual.ICONS.
TOOLS = (
    ("required", "Soldering iron, fine tip", "iron"),
    ("required", "Solder and flux", "flux"),
    ("required", "Tweezers", "tweezers"),
    ("required", "Hex key 2 mm", "hexkey"),
    ("required", "Multimeter", "meter"),
    ("required", "Super glue", "glue"),
    ("required", "USB-C cable and a computer", "usb"),
    ("required", "Clear UV resin and a UV torch", "uv"),
    ("recommended", "Magnifier", "loupe"),
    ("recommended", "Isopropyl alcohol", "ipa"),
    ("recommended", "Kapton tape", "tape"),
    ("recommended", "Paint pen", "pen"),
    ("recommended", "Silicone grease", "flux"),
)
TOOL_GROUPS = (("required", "Required"), ("recommended", "Recommended"))

# Shown between Tools and step 1.
BEFORE = (
    ("Print", "Shell upright, ring upside down (top face on the bed), plate face down, cap pocket down; 0.2 mm "
              "layers, four walls. Print the bezel in clear resin: its flange cannot be bridged and its fits are "
              "0.25 mm. Print the two plugs in TPU, standing on their strap ends. Print a hole coupon before "
              "trusting the insert holes."),
    ("Sealing", "The puck is built to IP55 (dust, water jets). That holds only with every seal in: the seam seal, "
                "a washer under each bolt head, the O-ring on the cap, UV resin round the crystal and the bezel, "
                "resin in the pinhole and both plugs pushed fully home. Cut the seam seal with a compass cutter."),
    ("Panel first", "Buy two panels. Before anything else, look at the flex: after it folds under the glass, pin 1 "
                    "must land on the 3 o'clock side of the board's pads. If yours is mirrored, the board needs "
                    "regenerating with FPC_PIN1_RIGHT flipped, not a different fold."),
    ("Battery", "The cell is live whatever the switch does. It is plugged in only after the soldering (step 9), "
                "and the insulation sheet goes on it before the board. Check the lead's polarity with the meter; "
                "many cells are wired the other way round."),
    ("Iron", "220 °C for the inserts, 320 °C with plenty of flux for the 0.7 mm flex. Clean with alcohol."),
    ("Compass", "Keep steel away from the compass: aluminium bolts only, no steel screws or magnets near the puck."),
)

# Steps.  parts: (key, qty) shown in the step's parts box.  arrows: (from_anchor, to_anchor, style).
# mags: magnifier call-outs: (zoom scene, anchor it points at, corner, label).
# note: one short line under the picture when the picture cannot say it alone.
STEPS = (
    dict(scene="s01", parts=[("shell", 1), ("insert", 4)],
         arrows=[("ins%d_from" % i, "ins%d_to" % i, "straight") for i in (1, 2, 3, 4)],
         mags=[("s01_mag", "ins3_to", "tl", "4×")],
         note="Heat-set with the iron at 220 °C until the insert is flush with the boss.", tool="iron"),
    dict(scene="s02", parts=[("motor", 1), ("antenna", 1)],
         arrows=[("motor_from", "motor_to", "straight"), ("ant_from", "ant_to", "straight")],
         mags=[("s02_mag", "motor_to", "tl", "")],
         note="Motor in the pocket at 2 o'clock, lead up. Peel the flex antenna and press it to the inside of the wall between 12 and 3 o'clock, cable end at 3 o'clock; run the pigtail along the floor to the notch at 5 o'clock."),
    dict(scene="s03", parts=[("pad", 1), ("battery", 1), ("sheet", 1)],
         arrows=[("pad_from", "pad_to", "straight"), ("batt_from", "batt_to", "straight"), ("sheet_from", "sheet_to", "straight")],
         mags=[],
         note="Pad first, the cell on it with its lead toward 5 o'clock, then the insulation sheet on top of the cell. Do not pinch the lead."),
    dict(scene="s04", parts=[("board", 1)],
         arrows=[("board_from", "board_to", "straight")],
         mags=[("s04_mag_h5", "lead_hole", "tr", "motor lead"), ("s04_mag_notch", "batt_notch", "tl", "battery lead + pigtail")],
         note="Feed the motor lead up through its hole, the battery lead and the antenna pigtail up through the 6 mm notch at 5 o'clock, then lower the board onto the rim."),
    dict(scene="s05", parts=[],
         arrows=[],
         mags=[("s05_mag_j5", "j5", "tr", "motor"), ("s05_mag_j4", "j4", "br", "antenna")],
         note="Plug the motor into its socket and click the pigtail onto the antenna socket. The battery stays unplugged until the panel is soldered."),
    dict(scene="s06", parts=[("foamring", 1), ("ring", 1)],
         arrows=[("foam_from", "foam_to", "straight"), ("ring_from", "ring_to", "straight")],
         mags=[("s06_mag", "ring_gap", "tr", "")],
         note="The opening in the ring faces the button (6 o'clock); the solder pads stay reachable through it."),
    dict(scene="s07", parts=[("panel", 1)],
         arrows=[("fpc_from", "fpc_to", "straight")],
         mags=[("s07_mag", "fpc_to", "tl", "pin 1 →")],
         note="Stand the panel on its chin and lay the flex on the pads: pin 1 on the right as you look from the button side (use the loupe). Tack both ends, solder the 12 fingers, clean with alcohol.", tool="iron"),
    dict(scene="s08", parts=[],
         arrows=[("fold_from", "fold_to", "curved")],
         mags=[],
         note="Fold the panel down onto the ledge. The flex bends once, under the glass; never crease it."),
    dict(scene="s09", parts=[],
         arrows=[("blead_from", "blead_to", "straight")],
         mags=[("s09_mag_j2", "j2", "tl", "battery  +  –")],
         note="Now plug in the battery. Check the lead with the meter first: + is marked on the board next to the socket.", tool="meter"),
    dict(scene="s10", parts=[("gasket", 1), ("crystal", 1)],
         arrows=[("gasket_from", "gasket_to", "straight"), ("crystal_from", "crystal_to", "straight")],
         mags=[],
         note="Blow the dust off the glass first. The crystal rests on the ring, not on the panel. Run a thin bead of UV resin round the crystal's top edge, but do not cure it yet."),
    dict(scene="s11", parts=[("bezel", 1)],
         arrows=[("bezel_from", "bezel_to", "straight")],
         mags=[("s11_mag", "pipe", "tr", "")],
         note="The four light pipes drop over the LEDs; the bezel seats over the ring and holds the crystal. Cure the resin through the clear lip with the UV torch.", tool="uv"),
    dict(scene="s12", parts=[("cap", 1), ("oring", 1)],
         arrows=[("cap_from", "cap_to", "straight")],
         mags=[("s12_mag", "cap_to", "tl", "")],
         note="Roll the O-ring into the cap's groove and grease it. The square pocket in the cap fits the switch stem; a dot of glue in the pocket keeps it on."),
    dict(scene="s13", parts=[],
         arrows=[("sw_from", "sw_to", "straight"), ("usb_from", "usb_to", "straight")],
         mags=[],
         note="Test before the plate goes on: plug in USB-C, flash the firmware, slide the switch toward the dot. The screen lights, the four LEDs strobe when you press the button, the motor ticks. Switch off again.", tool="usb"),
    dict(scene="s14", parts=[("seal", 1), ("plate", 1), ("washer", 4), ("bolt", 4)],
         arrows=[("seal_from", "seal_to", "straight"), ("plate_from", "plate_to", "straight")] + [("bolt%d_from" % i, "bolt%d_to" % i, "straight") for i in (1, 2, 3, 4)],
         mags=[("s14_mag", "bolt2_to", "tl", "")],
         note="Stick the seal on the shell rim, its ends against the USB-C opening. Run UV resin round the bezel where it meets the plate, lower the plate over the bezel and cap, then the bolts, each on a washer. Hand-tight only, in a cross: aluminium sockets strip. Cure through the lip.", tool="hexkey"),
    dict(scene="s15", parts=[("index", 1), ("cord", 1), ("usbplug", 1), ("swplug", 1)],
         arrows=[("index_from", "index_to", "straight"), ("cord_from", "cord_to", "straight"),
                 ("usbplug_from", "usbplug_to", "straight"), ("swplug_from", "swplug_to", "straight")],
         mags=[("s15_mag", "index_to", "br", "")],
         note="Glue the orange stub into the hole at 12 o'clock all round and trim it flush; fill the pinhole flush with UV resin and cure it. Glue each plug's pin into the hole under its opening and push the plugs home. Thread the cord in one mouth and out the other, then knot it.", tool="glue"),
    dict(scene="s16", parts=[],
         arrows=[("sw_from", "sw_to", "straight"), ("usb_from", "usb_to", "straight")],
         mags=[],
         note="Lift the switch plug and slide the switch toward the dot to switch on. Charge through USB-C with the puck off and dry; the pinhole LED goes out when the cell is full. Push both plugs fully home before the puck gets wet. Mark it 1 or 2 on the back with the paint pen.", tool="pen"),
)

# The last page before the back cover.
DONE = (
    ("Press", "Beacon on or off for 60 s: both pucks strobe so your friend can spot you."),
    ("Double press", "Vibration on or off (remembered)."),
    ("Hold 2 s, release", "Pairing mode. Hold again to cancel."),
    ("Hold 5 s, release", "Compass calibration: turn the puck through a slow figure of eight."),
)
DONE_TEXT = ("The orange dot is 12 o'clock. The arrow points at your partner and the blip sits at their range on "
             "the rings; the scale (50 m, 500 m, 5 km) is printed at 3 o'clock. While you hold the button the "
             "screen tells you what letting go will do.")
