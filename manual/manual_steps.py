"""
Content of the build guide: parts, tools and the assembly steps.

Shared by render_manual.py (FreeCAD, makes the pictures) and build_manual.py (lays out the PDF).
Scene names refer to render_manual.SCENES; anchor names are the points that script projects
into each picture so the layout can draw arrows and magnifier call-outs on top of it.
"""

TITLE = "Finder Puck"
SUBTITLE = "Build Guide"
VARIANT = "Round-screen puck, through-bolted"
VERSION = "0.4.0"
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
    "shell":   ("machined", "Shell", 1, "6061 aluminium, black anodised", "card_shell"),
    "window":  ("printed", "Antenna window", 1, "black", "card_window"),
    "plate":   ("printed", "Plate", 1, "black", "card_plate"),
    "ring":    ("printed", "Ring", 1, "black", "card_ring"),
    "bezel":   ("printed", "Bezel", 1, "clear resin", "card_bezel"),
    "cap":     ("printed", "Button cap", 1, "orange", "card_cap"),
    "door":    ("printed", "USB-C door", 1, "black", "card_door"),
    "swplug":  ("printed", "Switch plug", 1, "TPU 85A–95A, black", "card_swplug"),
    "board":   ("electronics", "Assembled board", 1, "factory-assembled PCB", "card_board"),
    "panel":   ("electronics", "Round display", 1, "1.28″ GC9A01, bare panel", "card_panel"),
    "crystal": ("electronics", "Crystal", 1, "Ø37.5 × 1.0 mm glass", "card_crystal"),
    "battery": ("electronics", "LiPo cell", 1, "503450, 28 AWG leads, JST PH", "card_battery"),
    "motor":   ("electronics", "Vibration motor", 1, "Ø10 mm coin, JST SH lead", "card_motor"),
    "antenna": ("electronics", "915 MHz antenna", 1, "adhesive flex 40 × 7 mm (2J 2JF0515P), U.FL", "card_antenna"),
    "bolt":    ("hardware", "Bolt M2.5 × 12", 4, "socket cap, aluminium (non-magnetic)", "card_bolt"),
    "index":   ("hardware", "Index stub", 1, "orange 1.75 mm filament, trim flush", "card_index"),
    "foamring": ("hardware", "Foam ring", 1, "0.5 mm firm foam (PORON 4701-50), Ø36.3–38 mm, open 10 to 5 o'clock", "card_foamring"),
    "gasket":  ("hardware", "Gasket", 1, "0.3 mm foam, Ø32.5–35 mm", "card_gasket"),
    "pad":     ("hardware", "Battery pad", 1, "0.5 mm foam, 34 × 50 mm", "card_pad"),
    "sheet":   ("hardware", "Insulation sheet", 1, "0.2 mm Kapton or PET, 36 × 52 mm", "card_sheet"),
    "cord":    ("hardware", "Cord", 1, "Ø2.5 mm, 300 mm", "card_cord"),
    "seal":    ("hardware", "Seam seal", 1, "1.0 mm closed-cell foam, Ø72.9–76.3 mm, open at 3 o'clock", "card_seal"),
    "windowgasket": ("hardware", "Window gasket", 1, "1.0 mm closed-cell foam strip, 1.7 × 87 mm", "card_windowgasket"),
    "washer":  ("hardware", "Washer M2.5", 4, "nylon DIN 433, 5 × 2.7 × 0.5 mm", "card_washer"),
    "oring":   ("hardware", "O-ring", 1, "9 × 1 mm silicone", "card_oring"),
    "doorgasket": ("hardware", "Door gasket", 1, "0.5 mm closed-cell foam frame, 15.9 × 9.4 mm, 13.7 × 7.2 mm hole", "card_doorgasket"),
    "crystalgasket": ("hardware", "Crystal gasket", 1, "0.3 mm closed-cell foam ring, Ø35.2–37.2 mm", "card_crystalgasket"),
    "lidgasket": ("hardware", "Lid gasket", 1, "0.3 mm closed-cell foam, cut from the template", "card_lidgasket"),
}
PART_GROUPS = (("machined", "Machined"), ("printed", "3D printed"), ("electronics", "Electronics"), ("hardware", "Hardware"))

# Tools: (group, name, icon).  Icons are drawn by build_manual.ICONS.
TOOLS = (
    ("required", "Soldering iron, fine tip", "iron"),
    ("required", "Solder and flux", "flux"),
    ("required", "Tweezers", "tweezers"),
    ("required", "Hex key 2 mm", "hexkey"),
    ("required", "Multimeter", "meter"),
    ("required", "Super glue", "glue"),
    ("required", "USB-C cable and a computer", "usb"),
    ("recommended", "Magnifier", "loupe"),
    ("recommended", "Isopropyl alcohol", "ipa"),
    ("recommended", "Kapton tape", "tape"),
    ("recommended", "Paint pen", "pen"),
    ("recommended", "Silicone grease", "flux"),
)
TOOL_GROUPS = (("required", "Required"), ("recommended", "Recommended"))

# Shown between Tools and step 1.
BEFORE = (
    ("Make", "The shell is CNC machined from 6061 and black anodised (the logo is V-grooved after anodising, so "
             "it shows bare metal). Print the antenna window upside down (rim on the bed), the ring upside down "
             "(top face on the bed), the plate face down, the cap pocket down; 0.2 mm layers, four walls. Print the "
             "bezel in clear resin: its flange cannot be bridged and its fits are 0.25 mm. Print the door standing on "
             "its edge and the switch plug in TPU, standing on its strap end."),
    ("Sealing", "The puck is built to IP55 (dust, water jets). That holds only with every seal in: the seam seal, "
                "the window gasket, "
                "a washer under each bolt head, the O-ring on the cap, the crystal and lid gaskets, the door slid shut "
                "and the switch plug pushed fully home. Cut the seam seal with a compass cutter; print "
                "case/finder_puck_gaskets.svg at 100 % and cut the lid, crystal and door gaskets along it."),
    ("Panel first", "Buy two panels. Before anything else, look at the flex: after it folds under the glass, pin 1 "
                    "must land on the 3 o'clock side of the board's pads. If yours is mirrored, the board needs "
                    "regenerating with FPC_PIN1_RIGHT flipped, not a different fold."),
    ("Battery", "The cell is live whatever the switch does. It is plugged in only after the soldering (step 9), "
                "and the insulation sheet goes on it before the board. Check the lead's polarity with the meter; "
                "many cells are wired the other way round."),
    ("Iron", "320 °C with plenty of flux for the 0.7 mm flex. Clean with alcohol."),
    ("Compass", "Keep steel away from the compass: aluminium bolts only, no steel screws or magnets near the puck."),
)

# Steps.  parts: (key, qty) shown in the step's parts box.  arrows: (from_anchor, to_anchor, style).
# mags: magnifier call-outs: (zoom scene, anchor it points at, corner, label).
# note: one short line under the picture when the picture cannot say it alone.
STEPS = (
    dict(scene="s01", parts=[("shell", 1), ("windowgasket", 1), ("window", 1)],
         arrows=[("wg_from", "wg_to", "straight"), ("win_from", "win_to", "straight")],
         mags=[("s01_mag", "flank", "tl", "")],
         note="Stick the foam strip along the floor of the notch and up both sloped ends, from rim to rim. Drop the window in: its two pegs go into the holes in the floor."),
    dict(scene="s02", parts=[("motor", 1), ("antenna", 1)],
         arrows=[("motor_from", "motor_to", "straight"), ("ant_from", "ant_to", "straight")],
         mags=[("s02_mag", "motor_to", "tl", "")],
         note="Motor in the pocket at 2 o'clock, lead up. Peel the flex antenna and press it to the inside of the plastic window, cable end at 3 o'clock, its lower edge level with the window's feet; run the pigtail along the floor to the notch at 5 o'clock."),
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
    dict(scene="s10", parts=[("gasket", 1), ("crystal", 1), ("crystalgasket", 1)],
         arrows=[("gasket_from", "gasket_to", "straight"), ("crystal_from", "crystal_to", "straight"),
                 ("cgasket_from", "cgasket_to", "straight")],
         mags=[],
         note="Blow the dust off the glass first. The crystal rests on the ring, not on the panel. Lay the crystal gasket on the glass's edge, centred, adhesive side up: it sticks to the bezel's lip and comes off with the lid."),
    dict(scene="s11", parts=[("cap", 1), ("oring", 1)],
         arrows=[("cap_from", "cap_to", "straight")],
         mags=[("s11_mag", "cap_to", "tl", "")],
         note="Roll the O-ring into the cap's groove and grease it. The square pocket in the cap fits the switch stem; a dot of glue in the pocket keeps it on. The cap goes on before the bezel, whose sleeve holds it."),
    dict(scene="s12", parts=[("bezel", 1), ("lidgasket", 1)],
         arrows=[("bezel_from", "bezel_to", "straight")],
         mags=[("s12_mag", "pipe", "tr", "")],
         note="Stick the lid gasket on the bezel's flange first: lobe round the button sleeve, tab on the charge-LED pipe. Lower the bezel straight down: the light pipes drop over the LEDs, the sleeve slides over the cap's O-ring, and the bezel seats over the ring and holds the crystal."),
    dict(scene="s13", parts=[],
         arrows=[("sw_from", "sw_to", "straight"), ("usb_from", "usb_to", "straight")],
         mags=[],
         note="Test before the plate goes on: plug in USB-C, flash the firmware, slide the switch toward the dot. The screen lights, the four LEDs strobe when you press the button, the motor ticks. Switch off again.", tool="usb"),
    dict(scene="s14", parts=[("seal", 1), ("door", 1), ("doorgasket", 1), ("plate", 1), ("washer", 4), ("bolt", 4)],
         arrows=[("seal_from", "seal_to", "straight"), ("door_from", "door_to", "straight"), ("plate_from", "plate_to", "straight")] + [("bolt%d_from" % i, "bolt%d_to" % i, "straight") for i in (1, 2, 3, 4)],
         mags=[("s14_mag", "bolt2_to", "tl", "")],
         note="Stick the seal on the rim of the shell and window, ends against the USB-C opening. Stick the gasket frame inside the door and hook the door into the window's groove, slid shut. Lower the plate, then the bolts on their washers: hand-tight, in a cross (aluminium sockets strip).", tool="hexkey"),
    dict(scene="s15", parts=[("index", 1), ("cord", 1), ("swplug", 1)],
         arrows=[("index_from", "index_to", "straight"), ("cord_from", "cord_to", "straight"),
                 ("swplug_from", "swplug_to", "straight")],
         mags=[("s15_mag", "index_to", "br", "")],
         note="Glue the orange stub into the blind hole at 12 o'clock and trim it flush. Glue the switch plug's pin into the hole under the slot and push the plug home. Thread the cord in at the side hole at 6 o'clock and out of the hole in the back (a loop of thin wire pulls it round the bend), then knot it.", tool="glue"),
    dict(scene="s16", parts=[],
         arrows=[("sw_from", "sw_to", "straight"), ("usb_from", "usb_to", "straight")],
         mags=[],
         note="Lift the switch plug and slide the switch toward the dot to switch on. Charge with the puck off and dry; the light just below 3 o'clock goes out when full. Shut the door and push the switch plug home before it gets wet. Mark it 1 or 2 on the back.", tool="pen"),
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
