# Finder Puck

Two pocket pucks that find each other without phones: GPS, compass and a LoRa link, an arrow and the distance on a
1.28in round screen, a vibration motor and a four-LED beacon. The KiCad 7 board, printed case and build guide are at
the repo root; the ESP32-S3 firmware is in `firmware/`. See `README.md` and `firmware/README.md`.

Split out of evil-weather-machine on 2026-10-22. The board generator's KiCad helpers (schematic and footprint
writers, s-expression parser, netlist reading, kicad-cli wrapper) come from that project's carrier-board generator,
vendored as `tools/kicad_helpers.py`; its own Digital Sand paths are unused or overridden by `generate_puck.py`.

## Board, case and guide

- Generated, never edited by hand: the KiCad project files, `lib/finder_puck.*`, `fab/`, `mech/`, `docs/`, the case
  outputs in `case/` and the guide pictures in `manual/img/`. Change the scripts (`tools/`, `case/*.py`,
  `manual/*.py`, `regen.sh`) and regenerate. Hand-written: `README.md`, this file, the downloaded 3D models in
  `lib/3dmodels/`, the vendored logo path `case/oshw_logo.svg` and everything in `firmware/`.
- `tools/generate_puck.py` (parts, nets, the FPC footprint) and `tools/puck_board.py` (placement, rule areas, fan-out
  vias, routing, feature export, fab files) build the board with KiCad 7's bundled Python:
  `FREEROUTING_JAR=/path/to/freerouting-1.9.0.jar /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 tools/generate_puck.py`.
  `--sch-only` and `--place-only` stop early (`--place-only` leaves an unrouted board). Routing uses Freerouting
  1.9.0, which needs a window and Java 17+.
- `./regen.sh` (with `FREEROUTING_JAR` set) runs board, case, previews and guide; `./regen.sh --case-only` starts from
  the last board export.
- Expected board output: `netlist OK`, `LoRa feed: … on F.Cu`, `layout check OK`, `design rules OK`,
  `routing check OK`, then `DRC routed: no violations; unconnected=0`. The LoRa feed is pre-routed and locked; the
  outline is a polygon with a notch for the battery lead (`NOTCHES`).
- Routes differ between runs, so commit and tag (`order-1`, …) the exact `finder_puck.kicad_pcb`, `fab/` and `mech/`
  that go to the fab.
- Never run a second KiCad script here while the generator runs: `SaveBoard` rewrites `finder_puck.kicad_pro` and a
  concurrent run can leave it with default design rules (the build verifies them and stops).
- KiCad 7 runs DRC only once per process and caches project settings, so the board step re-launches itself.
- ERC: KiCad 7 has no command-line ERC; run Inspect → Electrical Rules Checker in Eeschema after schematic changes.
  Expected: 0 errors and 1 warning (U4 SDO/SA0 on GND, which carries a power flag). Eeschema rewrites
  `finder_puck.kicad_pro` when it quits and leaves `.kicad_prl` and `.lck` files: restore the project file with
  `git checkout finder_puck.kicad_pro` afterwards.
- Case: `case/build_case.py` (freecadcmd) builds the machined aluminium shell (black anodised, tapped M2.5 holes,
  V-carved OSHW logo, cross-drilled lanyard hole) and the printed antenna window, plate, ring, bezel, cap, sliding
  USB-C door and TPU switch plug, plus the bolts, washers, index stub, flex antenna, seam seal, window gasket,
  O-ring, door, crystal and lid gaskets and interference proxies as reference solids, from `mech/`, the 1:1 gasket
  template `case/finder_puck_gaskets.svg` and the 1:1 logo drawing `case/finder_puck_logo_vcarve.svg`. The shell
  must stay machinable on a 3-axis mill (no undercuts, inside radii at least the cutter's), and no aluminium may
  come between an antenna and the sky: the GPS looks up through the plastic plate, the LoRa flex sits on the
  plastic window (the `rf:` lines give the clearances). It must report 0 interferences, its `gap` lines (every
  made-vs-other pair under
  0.3 mm) must be designed seats only, its `squeeze` line (the switch plug's 0.1 mm press fit) non-zero, its `door open` lines
  free of overlap, and its `mesh`
  lines must say closed, 0 self-intersections. IP55 depends on every seal in README "Sealing (IP55)"; a change
  that opens a new path into the case (an opening across the seam, a through hole) needs a seal of its own, a clamped
  gasket or O-ring rather than glue (the lid must stay serviceable). The script only builds when run as `build_case.py` (freecadcmd never sets
  `__main__`); the renderers import it for the parameters. Previews need the FreeCAD GUI:
  `open -n -a FreeCAD --args <abs path>/case/render_case.py`.
- Build guide: `manual/manual_steps.py` is the content (parts, tools, steps), `manual/render_manual.py` makes the
  pictures in the FreeCAD GUI (`open -n -a FreeCAD --args <abs>/manual/render_manual.py`, writes `manual/img/` and
  `manual/img/render.done`), `manual/build_manual.py` lays out A4 HTML and prints `docs/finder_puck_build_guide.pdf`
  with headless Google Chrome. Arrows and call-outs are placed from anchor points the renderer projects into each
  picture. To re-render a few scenes, write their names into `manual/img/only.txt` before launching the renderer (it
  merges them into `scenes.json`). Objects in the FCStd carry base placements (the board sits 1.6 mm down that way),
  so scene moves are composed onto them; FreeCAD animates view changes, so the renderer settles before shots.
- Blender renders (`docs/finder_puck_render*.png`): `MESH_DIR=case/blender_mesh <freecadcmd> case/export_meshes.py`,
  then `/opt/homebrew/bin/blender -b --python case/render_blender.py -- hero,pair,back [samples] [width]`
  (Blender 3.5, Cycles on Metal works headless; 5-13 min a view at 512 samples / 2400 px, preview with `64 1200`).
  Light powers are a few watts because the scene is real scale. A flat crystal magnifies a strip light's reflection
  (~8 mm of glass per degree), so the hero rim light is placed ~2 deg under the camera's mirror angle.
  `case/blender_mesh/` is not committed.
- `tools/make_models.py` only generates the plain models (RFM95W, JST PH/SH) and refuses to overwrite the real
  downloaded ones. KiCad StepUp is symlinked into FreeCAD 1.1's `v1-1/Mod`, 3D path set to KiCad 7's models.

## Firmware

- `firmware/` is a PlatformIO project (ESP32-S3, Arduino, platform pinned to `espressif32@6.4.0`):
  `cd firmware && pio run` builds `puck_a` and `puck_b`; `pio run -e puck_a -t upload` flashes one puck.
- Pins in `firmware/src/config.h` must match `PARTS` in `tools/generate_puck.py`.
- Nothing has run on hardware yet; `firmware/README.md` lists what to check on the first boards.
