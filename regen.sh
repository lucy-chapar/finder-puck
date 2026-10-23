#!/bin/sh
# Rebuild the finder puck end to end: board (KiCad) -> 3D export -> case (FreeCAD) -> previews -> build guide.
#   FREEROUTING_JAR=/path/to/freerouting-1.9.0.jar ./regen.sh             # board + case + previews
#   ./regen.sh --case-only                                                # case only, from the last board export
set -e
cd "$(dirname "$0")"
KICAD_PY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
FREECADCMD=/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd

if [ "$1" != "--case-only" ]; then
    "$KICAD_PY" -u tools/generate_puck.py
fi
"$FREECADCMD" case/build_case.py 2>&1 | grep -E "overlap|squeeze|door open|gap |lanyard|mesh |case:|CHECK|wrote|Error|Traceback"
rm -rf case/__pycache__
# Previews need the FreeCAD GUI; it opens and closes a window.
open -n -a /Applications/FreeCAD.app --args "$PWD/case/render_case.py"
# Build guide: the pictures (FreeCAD GUI again), then the PDF (Google Chrome, headless).
rm -f manual/img/render.done
open -n -a /Applications/FreeCAD.app --args "$PWD/manual/render_manual.py"
while [ ! -f manual/img/render.done ]; do sleep 2; done
grep -q ok manual/img/render.done || { cat manual/img/render.log; exit 1; }
python3 manual/build_manual.py
