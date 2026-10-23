// Draws every screen of src/ui.cpp into one PNG sheet (docs/ui-preview.png) so the
// round-screen layout can be checked without hardware.  Run tools/preview_ui/build.sh.
#include <stdio.h>
#include <vector>

#include "../../src/ui.h"

uint32_t previewMillis = 0;
void uiPreviewPixel(int x, int y, uint8_t rgb[3]);

struct Shot {
  const char *name;
  UiState s;
  uint32_t ms;
};

int main(int argc, char **argv) {
  uiBegin();
  std::vector<Shot> shots;
  UiState s;

  s = UiState();
  s.screen = SCREEN_FIND; s.fix = true; s.sats = 11; s.batteryPct = 72;
  s.arrow = s.distance = true; s.arrowDeg = 35; s.distanceM = 142; s.northDeg = 300;
  shots.push_back({"find_142m", s, 0});

  s.distanceM = 8; s.arrowDeg = 200; s.status = "+-6 m"; s.partnerBeacon = true;
  shots.push_back({"find_close_beacon", s, 0});

  s = UiState();
  s.screen = SCREEN_FIND; s.fix = true; s.sats = 7; s.batteryPct = 15; s.batteryLow = true;
  s.arrow = s.distance = true; s.arrowDeg = 290; s.distanceM = 2350; s.northUp = true;
  shots.push_back({"find_km_northup_lowbatt", s, 0});

  s = UiState();
  s.screen = SCREEN_SEARCHING; s.fix = true; s.sats = 9; s.batteryPct = 60; s.charging = true;
  s.status = "looking for partner";
  shots.push_back({"searching_charging", s, 1300});

  s = UiState();
  s.screen = SCREEN_SEARCHING; s.fix = true; s.sats = 9; s.batteryPct = 60; s.northDeg = 80;
  s.arrow = s.arrowHollow = s.distance = true; s.arrowDeg = 120; s.distanceM = 380;
  s.status = "lost partner 47s";
  shots.push_back({"lost", s, 2600});

  s = UiState();
  s.screen = SCREEN_HOT_COLD; s.fix = false; s.sats = 3; s.batteryPct = 90; s.rssi = -72; s.rssiTrend = 4;
  shots.push_back({"hot_cold", s, 0});

  s = UiState(); s.screen = SCREEN_PAIRING; shots.push_back({"pairing", s, 700});
  s = UiState(); s.screen = SCREEN_CALIBRATE; s.calProgress = 64; s.calSeconds = 11;
  shots.push_back({"calibrate", s, 0});
  s = UiState(); s.screen = SCREEN_NOT_PAIRED; shots.push_back({"not_paired", s, 0});
  s = UiState(); s.screen = SCREEN_BATTERY; shots.push_back({"battery", s, 0});

  s = UiState();
  s.screen = SCREEN_FIND; s.fix = true; s.sats = 11; s.batteryPct = 72;
  s.arrow = s.distance = true; s.arrowDeg = 35; s.distanceM = 142; s.toast = "Partner found";
  shots.push_back({"toast", s, 0});
  s.toast = nullptr; s.hint = "release: pair";
  shots.push_back({"hold_hint", s, 0});

  const int cols = 4, rows = (shots.size() + cols - 1) / cols, W = 240, G = 8;
  const int SW = cols * (W + G) + G, SH = rows * (W + G) + G;
  std::vector<uint8_t> img(SW * SH * 3, 255);
  for (size_t i = 0; i < shots.size(); i++) {
    previewMillis = shots[i].ms;
    uiDraw(shots[i].s);
    int ox = G + (i % cols) * (W + G), oy = G + (i / cols) * (W + G);
    for (int y = 0; y < W; y++)
      for (int x = 0; x < W; x++) {
        float dx = x - 119.5f, dy = y - 119.5f;
        uint8_t *px = &img[((oy + y) * SW + ox + x) * 3];
        if (dx * dx + dy * dy > 120 * 120) { px[0] = px[1] = px[2] = 40; continue; }   // outside the round glass
        uiPreviewPixel(x, y, px);
      }
  }
  FILE *f = fopen(argc > 1 ? argv[1] : "ui-preview.ppm", "wb");
  fprintf(f, "P6 %d %d 255\n", SW, SH);
  fwrite(img.data(), 1, img.size(), f);
  fclose(f);
  for (auto &sh : shots) printf("%s\n", sh.name);
  return 0;
}
