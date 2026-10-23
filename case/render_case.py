"""
Preview images of the case.  Needs the FreeCAD GUI (it opens a window briefly):

    open -n -a /Applications/FreeCAD.app --args /abs/path/to/case/render_case.py
"""

import os
import time

import FreeCAD
import FreeCADGui

try:
    CASE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    CASE = os.path.join(os.getcwd(), "case")
DOCS = os.path.join(os.path.dirname(CASE), "docs")

doc = FreeCAD.openDocument(os.path.join(CASE, "finder_puck_case.FCStd"))
FreeCADGui.activateWorkbench("PartWorkbench")
view = FreeCADGui.ActiveDocument.ActiveView

# Black body, orange button, bolts and index, translucent bezel, dark panel, clear crystal.
ORANGE = ((0.95, 0.38, 0.05), 0)
COLORS = {
    "Shell": ((0.09, 0.09, 0.10), 0), "Plate": ((0.09, 0.09, 0.10), 0), "Ring": ((0.09, 0.09, 0.10), 0),
    "Bezel": ((0.85, 0.87, 0.84), 45), "Cap": ORANGE, "Index": ORANGE,
    "Board": ((0.08, 0.09, 0.08), 0), "Panel": ((0.03, 0.08, 0.05), 0), "Crystal": ((0.8, 0.9, 1.0), 80),
    "Battery": ((0.75, 0.72, 0.62), 0), "Motor": ((0.6, 0.6, 0.62), 0), "Antenna": ((0.8, 0.65, 0.2), 0),
}
for _i in range(1, 5):
    COLORS["Bolt%d" % _i] = ORANGE
    COLORS["Insert%d" % _i] = ((0.74, 0.62, 0.32), 0)
for name, (col, transp) in COLORS.items():
    vo = FreeCADGui.ActiveDocument.getObject(name)
    if vo:
        vo.ShapeColor = col
        vo.Transparency = transp


def settle():
    for _ in range(5):
        FreeCADGui.updateGui()
        time.sleep(0.1)


def shot(fname, visible, view_name, transp=None):
    for obj in doc.Objects:                 # everything else (the interference proxies) stays hidden
        name = obj.Name
        vo = FreeCADGui.ActiveDocument.getObject(name)
        if vo:
            vo.Visibility = name in visible
            if name in COLORS:
                vo.Transparency = COLORS[name][1]
    for name, t in (transp or {}).items():
        FreeCADGui.ActiveDocument.getObject(name).Transparency = t
    getattr(view, view_name)()
    if view_name == "viewBottom":      # FreeCAD flips about X; turn the puck over like a pancake instead
        view.viewRotateRight()
        view.viewRotateRight()
    settle()
    view.fitAll()
    settle()
    view.saveImage(os.path.join(DOCS, fname), 1400, 1050, "White")


os.makedirs(DOCS, exist_ok=True)
for _ in range(4):
    settle()
ALL = list(COLORS)
BOLTS = ["Bolt%d" % i for i in range(1, 5)]
CLOSED = ["Shell", "Plate", "Ring", "Bezel", "Cap", "Crystal", "Panel", "Index"] + BOLTS
shot("case-closed.png", CLOSED, "viewIsometric")
shot("case-side.png", CLOSED, "viewFront")
shot("case-face.png", CLOSED + ["Board"], "viewTop")
shot("case-inside.png", ALL, "viewIsometric", {"Plate": 75, "Shell": 0})
shot("case-stack.png", ["Board", "Panel", "Crystal", "Ring", "Bezel", "Cap", "Battery", "Motor", "Antenna"], "viewIsometric")
shot("case-shell.png", ["Shell", "Battery", "Motor", "Antenna"] + ["Insert%d" % i for i in range(1, 5)], "viewIsometric")
shot("case-back.png", ["Shell", "Plate"], "viewBottom")
FreeCAD.closeDocument(doc.Name)
FreeCADGui.getMainWindow().close()
