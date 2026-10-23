#!/bin/sh
# Renders the UI screens to docs/ui-preview.png.  Needs SDL2 (brew install sdl2)
# and a prior `pio run` so LovyanGFX is in .pio/libdeps.
set -e
cd "$(dirname "$0")/../.."
LGFX=.pio/libdeps/puck_a/LovyanGFX/src
OUT=.pio/preview_ui
mkdir -p "$OUT" docs
SRCS="$(ls $LGFX/lgfx/v1/*.cpp $LGFX/lgfx/v1/misc/*.cpp $LGFX/lgfx/v1/panel/Panel_Device.cpp \
  $LGFX/lgfx/v1/panel/Panel_FrameBufferBase.cpp $LGFX/lgfx/v1/platforms/sdl/*.cpp $LGFX/lgfx/v1/lgfx_fonts.cpp 2>/dev/null | sort -u)"
c++ -std=c++17 -O1 -w -DUI_PREVIEW -Itools/preview_ui/shim -Isrc -I$LGFX $(sdl2-config --cflags) \
  tools/preview_ui/preview_ui.cpp src/ui.cpp $SRCS \
  $LGFX/lgfx/utility/*.c $LGFX/lgfx/Fonts/efont/*.c $LGFX/lgfx/Fonts/IPA/*.c -Wl,-dead_strip $(sdl2-config --libs) -o "$OUT/preview_ui"
"$OUT/preview_ui" "$OUT/ui-preview.ppm"
sips -s format png "$OUT/ui-preview.ppm" --out docs/ui-preview.png >/dev/null
echo "wrote docs/ui-preview.png"
