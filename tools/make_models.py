"""
Simple body models (STEP) for footprints whose stock 3D model is missing from
the KiCad 7.0.7 library.  Run with FreeCAD's console:

    /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd tools/make_models.py

Boxes are in footprint coordinates with KiCad's model axes (Y up = PCB -Y).
Sizes come from the part datasheets; they are for case clearance, not looks.
"""

import os

import FreeCAD
import Import
import Part

# freecadcmd may not set __file__; fall back to running from the repository root.
try:
    PUCK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    PUCK = os.getcwd()
OUT = os.path.join(PUCK, "lib", "3dmodels")

# name: list of (x0, y0, x1, y1, z0, z1) in footprint/PCB coordinates (Y down).
# Parts with real models in lib/3dmodels (ESP32, GPS, USB-C, WS2812B) are not listed:
# this script must never overwrite those files.
MODELS = {
    # 16 x 16 mm module PCB with its shield can; overall height taken as 2.4 mm.
    "HOPERF_RFM9XW_SMD": [(-8.0, -8.0, 8.0, 8.0, 0.0, 1.0), (-6.8, -7.2, 6.8, 6.2, 1.0, 2.4)],
    # JST SH side-entry 2-pin, 4.0 x 4.25 x 2.9 mm, opening on +Y.
    "JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal": [(-2.0, -1.675, 2.0, 2.575, 0.0, 2.9)],
    "JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal": [(-4.0, -1.5, 4.0, 4.6, 0.0, 4.5)],
}


def main():
    os.makedirs(OUT, exist_ok=True)
    doc = FreeCAD.newDocument("models")
    for name, boxes in MODELS.items():
        solids = []
        for x0, y0, x1, y1, z0, z1 in boxes:
            # Model space has Y up, so the PCB rectangle flips about the X axis.
            solids.append(Part.makeBox(x1 - x0, y1 - y0, z1 - z0, FreeCAD.Vector(x0, -y1, z0)))
        shape = solids[0].fuse(solids[1:]) if len(solids) > 1 else solids[0]
        obj = doc.addObject("Part::Feature", name.replace("-", "_").replace(".", "_"))
        obj.Shape = shape
        path = os.path.join(OUT, name + ".step")
        if os.path.exists(path) and os.path.getsize(path) > 50000:
            raise SystemExit("refusing to overwrite a real model: " + path)
        Import.export([obj], path)
        print("wrote", path)
    FreeCAD.closeDocument(doc.Name)


main()
