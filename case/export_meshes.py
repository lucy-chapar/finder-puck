"""
Export every solid of the case assembly as a fine STL for the Blender render (render_blender.py).

    MESH_DIR=<out dir> /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd case/export_meshes.py

Writes <out dir>/<Name>.stl for every non-proxy object in finder_puck_case.FCStd (default case/blender_mesh),
plus bbox.json listing each part's extent.  Coordinates are the assembly's (mm, Z 0 = top of the PCB).
"""

import json
import math
import os

import FreeCAD
import MeshPart

CASE = os.path.dirname(os.path.abspath(__file__))
out = os.environ.get("MESH_DIR") or os.path.join(CASE, "blender_mesh")
os.makedirs(out, exist_ok=True)

# The board is a big compound of components: a coarser mesh keeps it to a few hundred thousand triangles.
FINE = dict(LinearDeflection=0.01, AngularDeflection=math.radians(3), Relative=False)
COARSE = dict(LinearDeflection=0.03, AngularDeflection=math.radians(8), Relative=False)

doc = FreeCAD.openDocument(os.path.join(CASE, "finder_puck_case.FCStd"))
bbox = {}
for obj in doc.Objects:
    if obj.Name.startswith("Proxy") or not hasattr(obj, "Shape") or obj.Shape.isNull():
        continue
    mesh = MeshPart.meshFromShape(Shape=obj.Shape, **(COARSE if obj.Name == "Board" else FINE))
    path = os.path.join(out, obj.Name + ".stl")
    mesh.write(path)
    b = obj.Shape.BoundBox
    bbox[obj.Name] = [b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax]
    print("%-10s %8d facets  bbox x %6.1f..%6.1f y %6.1f..%6.1f z %6.1f..%6.1f" % (
        obj.Name, mesh.CountFacets, b.XMin, b.XMax, b.YMin, b.YMax, b.ZMin, b.ZMax))
json.dump(bbox, open(os.path.join(out, "bbox.json"), "w"), indent=1)
FreeCAD.closeDocument(doc.Name)
print("wrote", out)
