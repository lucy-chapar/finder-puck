#include "ui.h"

#define LGFX_USE_V1
#include <Arduino.h>
#include <LovyanGFX.hpp>

#include "config.h"

static_assert(LCD_SPI_HZ == 80000000 || LCD_SPI_HZ == 40000000 || LCD_SPI_HZ == 20000000,
              "LCD_SPI_HZ: use 80, 40 or 20 MHz; 26.67 and 13.33 MHz have harmonics on GPS L1");

namespace {

#ifndef UI_PREVIEW   // tools/preview_ui draws the screens on a computer without the panel
class Lcd : public lgfx::LGFX_Device {
  lgfx::Panel_GC9A01 panel;
  lgfx::Bus_SPI bus;
  lgfx::Light_PWM light;

 public:
  Lcd() {
    auto b = bus.config();
    b.spi_host = SPI3_HOST;   // LoRa has SPI2 on IO10-IO14
    b.spi_mode = 0;
    b.freq_write = LCD_SPI_HZ;
    b.freq_read = 16000000;
    b.spi_3wire = false;
    b.use_lock = true;
    b.dma_channel = SPI_DMA_CH_AUTO;
    b.pin_sclk = PIN_LCD_SCK;
    b.pin_mosi = PIN_LCD_MOSI;
    b.pin_miso = -1;          // write-only panel
    b.pin_dc = PIN_LCD_DC;
    bus.config(b);
    panel.setBus(&bus);

    auto p = panel.config();
    p.pin_cs = PIN_LCD_CS;
    p.pin_rst = PIN_LCD_RST;
    p.pin_busy = -1;
    p.panel_width = p.memory_width = 240;
    p.panel_height = p.memory_height = 240;
    p.offset_rotation = 0;
    p.readable = false;
    p.invert = true;
    p.rgb_order = false;
    p.bus_shared = false;
    panel.config(p);

    auto l = light.config();
    l.pin_bl = PIN_LCD_BL;
    l.invert = false;
    l.freq = 20000;
    l.pwm_channel = 7;
    light.config(l);
    panel.setLight(&light);

    setPanel(&panel);
  }
};

Lcd lcd;
lgfx::LGFX_Sprite canvas(&lcd);
#else
lgfx::LGFX_Sprite canvas;
#endif
bool ready = false;

void present() {
#ifndef UI_PREVIEW
  canvas.pushSprite(0, 0);
#endif
}

const int CX = 120, CY = 120;
const int RING = 108;   // outer ring radius = the current scale

const uint16_t BG = lgfx::color565(0x0A, 0x2A, 0x14);
const uint16_t GRID = lgfx::color565(0x1E, 0x5C, 0x32);
const uint16_t GRID_DIM = lgfx::color565(0x14, 0x40, 0x22);
const uint16_t TEXT = lgfx::color565(0x7C, 0xF0, 0x9C);
const uint16_t TEXT_DIM = lgfx::color565(0x3C, 0x9C, 0x5A);
const uint16_t ORANGE = lgfx::color565(0xFF, 0xB4, 0x00);
const uint16_t ORANGE_DIM = lgfx::color565(0x80, 0x5A, 0x00);
const uint16_t RED = lgfx::color565(0xFF, 0x30, 0x20);
const uint16_t YELLOW = lgfx::color565(0xFF, 0xE0, 0x40);

// My angles: degrees clockwise from 12 o'clock.  LovyanGFX arcs: clockwise from 3 o'clock.
float arcAngle(float deg) { return deg - 90; }

void polar(float deg, float r, int &x, int &y, int cx = CX, int cy = CY) {
  float a = deg * PI / 180;
  x = cx + lroundf(r * sinf(a));
  y = cy - lroundf(r * cosf(a));
}

void text(const char *s, int x, int y, const lgfx::IFont *font, uint16_t colour,
          lgfx::textdatum_t datum = lgfx::middle_center) {
  canvas.setFont(font);
  canvas.setTextColor(colour);
  canvas.setTextDatum(datum);
  canvas.drawString(s, x, y);
}

float scaleFor(float d) { return d <= 50 ? 50 : d <= 500 ? 500 : 5000; }

void drawRadar(float scaleM, float northDeg, bool showNorth) {
  canvas.fillScreen(BG);
  for (int i = 1; i <= 3; i++) canvas.drawCircle(CX, CY, RING * i / 3, i == 3 ? GRID : GRID_DIM);
  canvas.drawFastHLine(CX - RING, CY, 2 * RING, GRID_DIM);
  canvas.drawFastVLine(CX, CY - RING, 2 * RING, GRID_DIM);
  if (scaleM > 0) {
    char buf[8];
    if (scaleM < 1000) snprintf(buf, sizeof(buf), "%dm", (int)scaleM);
    else snprintf(buf, sizeof(buf), "%dkm", (int)(scaleM / 1000));
    text(buf, CX + RING - 4, CY - 3, &lgfx::fonts::Font0, TEXT_DIM, lgfx::bottom_right);   // outer ring's range
  }
  if (showNorth) {
    int x, y;
    polar(northDeg, RING, x, y);
    canvas.fillCircle(x, y, 7, BG);
    text("N", x, y, &lgfx::fonts::Font2, TEXT);
  }
}

// Searching sweep: a fading wedge going round once every 4 s.
void drawSweep() {
  float a = (millis() % 4000) * 360.0f / 4000;
  const uint16_t shades[] = {lgfx::color565(0x1A, 0x6A, 0x36), lgfx::color565(0x14, 0x4E, 0x28),
                             lgfx::color565(0x10, 0x3A, 0x1E)};
  for (int i = 0; i < 3; i++)
    canvas.fillArc(CX, CY, RING - 1, 0, arcAngle(a - 12 * (i + 1)), arcAngle(a - 12 * i), shades[i]);
  int x, y;
  polar(a, RING - 1, x, y);
  canvas.drawLine(CX, CY, x, y, TEXT_DIM);
}

// 60 px arrow centred on (cx, cy).
void drawArrow(int cx, int cy, float deg, bool hollow, uint16_t colour) {
  const int8_t shape[7][2] = {{0, -36}, {18, -10}, {7, -10}, {7, 24}, {-7, 24}, {-7, -10}, {-18, -10}};
  const float s = sinf(deg * PI / 180), c = cosf(deg * PI / 180);
  int x[7], y[7];
  for (int i = 0; i < 7; i++) {
    x[i] = cx + lroundf(shape[i][0] * c - shape[i][1] * s);
    y[i] = cy + lroundf(shape[i][0] * s + shape[i][1] * c);
  }
  if (hollow) {
    for (int i = 0; i < 7; i++) {
      int j = (i + 1) % 7;
      canvas.drawWideLine(x[i], y[i], x[j], y[j], 1.5f, colour);
    }
    return;
  }
  canvas.fillTriangle(x[0], y[0], x[1], y[1], x[6], y[6], colour);
  canvas.fillTriangle(x[2], y[2], x[3], y[3], x[4], y[4], colour);
  canvas.fillTriangle(x[2], y[2], x[4], y[4], x[5], y[5], colour);
}

void drawDistance(float d, uint16_t colour) {
  char num[8];
  const char *unit = "m";
  if (d < 1000) snprintf(num, sizeof(num), "%d", (int)lroundf(d));
  else if (d < 10000) snprintf(num, sizeof(num), "%.1f", d / 1000), unit = "km";
  else snprintf(num, sizeof(num), "%d", min((int)(d / 1000), 999)), unit = "km";
  canvas.setFont(&lgfx::fonts::Font7);   // 7-segment, 48 px
  int w = canvas.textWidth(num);
  int x = CX - 8;
  text(num, x, 172, &lgfx::fonts::Font7, colour);
  text(unit, x + w / 2 + 3, 194, &lgfx::fonts::Font2, colour, lgfx::bottom_left);
}

void drawBattery(int x, int y, const UiState &s) {
  bool blink = s.batteryLow && !s.charging && (millis() / 500) % 2;
  uint16_t c = s.batteryLow && !s.charging ? RED : TEXT;
  if (!blink) {
    canvas.drawRect(x, y, 20, 10, c);
    canvas.fillRect(x + 20, y + 3, 2, 4, c);
    int pct = s.charging ? (millis() / 400) % 5 * 25 : s.batteryPct;   // fills up while charging
    canvas.fillRect(x + 2, y + 2, (pct * 16 + 50) / 100, 6, c);
  }
  if (s.charging) {   // lightning bolt
    canvas.fillTriangle(x + 27, y - 1, x + 24, y + 6, x + 28, y + 5, YELLOW);
    canvas.fillTriangle(x + 27, y + 4, x + 31, y + 4, x + 26, y + 11, YELLOW);
  }
}

void drawStatusTop(const UiState &s) {
  char buf[12];
  if (!s.gpsAlive) snprintf(buf, sizeof(buf), "GPS?");
  else if (!s.fix) snprintf(buf, sizeof(buf), "no fix %d", s.sats);
  else snprintf(buf, sizeof(buf), "%d sat", s.sats);
  canvas.fillRoundRect(60, 22, 120, 16, 8, BG);
  text(buf, 100, 30, &lgfx::fonts::Font2, s.fix ? TEXT : TEXT_DIM);
  drawBattery(134, 25, s);
}

void drawStatusBottom(const UiState &s) {
  if (!s.status && !s.partnerBeacon) return;
  char buf[32];
  snprintf(buf, sizeof(buf), "%s%s%s", s.partnerBeacon ? "* " : "", s.status ? s.status : "",
           s.partnerBeacon ? " *" : "");
  canvas.setFont(&lgfx::fonts::Font2);
  int w = canvas.textWidth(buf) + 12;
  canvas.fillRoundRect(CX - w / 2, 204, w, 18, 9, BG);
  text(buf, CX, 213, &lgfx::fonts::Font2, s.partnerBeacon ? ORANGE : TEXT);
}

void drawFind(const UiState &s) {
  float scale = s.distance ? scaleFor(s.distanceM) : 0;
  drawRadar(scale, s.northDeg, !s.northUp);
  if (s.screen == SCREEN_SEARCHING) drawSweep();
  if (s.arrow && s.distance && !s.arrowHollow) {   // partner blip at its true range
    int x, y;
    polar(s.arrowDeg, min(s.distanceM / scale, 1.0f) * RING, x, y);
    canvas.fillCircle(x, y, 5, ORANGE);
    canvas.drawCircle(x, y, 8, ORANGE_DIM);
  }
  if (s.arrow) drawArrow(CX, 92, s.arrowDeg, s.arrowHollow, s.arrowHollow ? ORANGE_DIM : ORANGE);
  else if (s.screen == SCREEN_SEARCHING) text("Searching", CX, 92, &lgfx::fonts::FreeSansBold12pt7b, TEXT);
  if (s.distance) drawDistance(s.distanceM, s.arrowHollow ? ORANGE_DIM : ORANGE);
  if (s.northUp && s.arrow) text("N-up", CX, 132, &lgfx::fonts::Font0, TEXT_DIM);
  drawStatusTop(s);
  drawStatusBottom(s);
}

void drawHotCold(const UiState &s) {
  drawRadar(0, 0, false);
  // Signal gauge round the edge, clockwise from 1 o'clock to 11 o'clock (the
  // gap at the top leaves room for the status row).
  float f = constrain((s.rssi + 125) / 80, 0.0f, 1.0f);
  canvas.fillArc(CX, CY, 116, 108, arcAngle(40), arcAngle(320), GRID_DIM);
  if (f > 0) canvas.fillArc(CX, CY, 116, 108, arcAngle(40), arcAngle(40 + 280 * f), ORANGE);
  text(s.ownFix ? "Partner: no GPS" : "No GPS fix", CX, 62, &lgfx::fonts::Font2, TEXT);
  const char *word = s.rssi > -60 ? "HOT" : s.rssi > -80 ? "WARM" : s.rssi > -100 ? "COOL" : "COLD";
  canvas.fillRoundRect(CX - 70, CY - 22, 140, 44, 10, BG);
  text(word, CX, CY, &lgfx::fonts::FreeSansBold18pt7b, s.rssi > -80 ? ORANGE : TEXT);
  char buf[24];
  const char *trend = s.rssiTrend > 2 ? "warmer" : s.rssiTrend < -2 ? "colder" : "steady";
  snprintf(buf, sizeof(buf), "%s  %d dBm", trend, (int)s.rssi);
  text(buf, CX, 160, &lgfx::fonts::Font2, TEXT);
  drawStatusTop(s);
}

void drawPairing() {
  drawRadar(0, 0, false);
  drawSweep();
  canvas.fillRoundRect(CX - 90, CY - 34, 180, 68, 12, BG);
  text("Pairing", CX, CY - 14, &lgfx::fonts::FreeSansBold12pt7b, ORANGE);
  text("hold the other puck", CX, CY + 8, &lgfx::fonts::Font2, TEXT);
  text("next to this one", CX, CY + 24, &lgfx::fonts::Font2, TEXT);
}

void drawCalibrate(const UiState &s) {
  canvas.fillScreen(BG);
  canvas.fillArc(CX, CY, 116, 106, 0, 360, GRID_DIM);
  if (s.calProgress > 0) canvas.fillArc(CX, CY, 116, 106, arcAngle(0), arcAngle(3.6f * s.calProgress), ORANGE);
  text("Compass", CX, 72, &lgfx::fonts::FreeSansBold12pt7b, ORANGE);
  text("Wave in a figure-8,", CX, 108, &lgfx::fonts::Font2, TEXT);
  text("turn it over and back", CX, 126, &lgfx::fonts::Font2, TEXT);
  char buf[12];
  snprintf(buf, sizeof(buf), "%lus", (unsigned long)s.calSeconds);
  text(buf, CX, 160, &lgfx::fonts::Font4, TEXT_DIM);
}

void drawMessage(const char *title, const char *line1, const char *line2, uint16_t colour) {
  canvas.fillScreen(BG);
  canvas.drawCircle(CX, CY, RING, GRID);
  text(title, CX, 92, &lgfx::fonts::FreeSansBold12pt7b, colour);
  if (line1) text(line1, CX, 128, &lgfx::fonts::Font2, TEXT);
  if (line2) text(line2, CX, 146, &lgfx::fonts::Font2, TEXT);
}

void drawOverlays(const UiState &s) {
  if (s.hint) {
    canvas.setFont(&lgfx::fonts::Font2);
    int w = canvas.textWidth(s.hint) + 20;
    canvas.fillRoundRect(CX - w / 2, 196, w, 24, 12, ORANGE);
    text(s.hint, CX, 208, &lgfx::fonts::Font2, BG);
  } else if (s.toast) {
    canvas.setFont(&lgfx::fonts::FreeSans9pt7b);
    int w = max(canvas.textWidth(s.toast) + 28, 120);
    canvas.fillRoundRect(CX - w / 2, CY - 18, w, 36, 10, BG);
    canvas.drawRoundRect(CX - w / 2, CY - 18, w, 36, 10, ORANGE);
    text(s.toast, CX, CY, &lgfx::fonts::FreeSans9pt7b, TEXT);
  }
}

}  // namespace

#ifdef UI_PREVIEW
bool uiBegin() {
  canvas.setColorDepth(16);
  ready = canvas.createSprite(240, 240) != nullptr;
  return ready;
}
void uiPower(bool) {}
void uiPreviewPixel(int x, int y, uint8_t rgb[3]) {
  auto c = canvas.readPixelRGB(x, y);
  rgb[0] = c.R8();
  rgb[1] = c.G8();
  rgb[2] = c.B8();
}
#else
bool uiBegin() {
  lcd.init();
  lcd.setRotation(LCD_ROTATION);
  lcd.setBrightness(0);
  lcd.fillScreen(BG);
  canvas.setColorDepth(16);
  // 240 x 240 x 2 = 115 kB; the N8 module has no PSRAM, so fall back to 8-bit colour if it won't fit.
  if (!canvas.createSprite(240, 240)) {
    canvas.setColorDepth(8);
    if (!canvas.createSprite(240, 240)) return false;
  }
  ready = true;
  lcd.setBrightness(LCD_BRIGHTNESS);
  return true;
}

void uiPower(bool on) {
  if (on) {
    lcd.wakeup();
    lcd.setBrightness(LCD_BRIGHTNESS);
  } else {
    lcd.setBrightness(0);
    lcd.sleep();
  }
}
#endif

void uiDraw(const UiState &s) {
  if (!ready) return;
  switch (s.screen) {
    case SCREEN_NOT_PAIRED: drawMessage("Not paired", "Hold the button 2 s", "on both pucks", ORANGE); break;
    case SCREEN_FIND:
    case SCREEN_SEARCHING: drawFind(s); break;
    case SCREEN_HOT_COLD: drawHotCold(s); break;
    case SCREEN_PAIRING: drawPairing(); break;
    case SCREEN_CALIBRATE: drawCalibrate(s); break;
    case SCREEN_BATTERY: drawMessage("Battery low!", "Charge over USB-C", nullptr, RED); break;
  }
  drawOverlays(s);
  present();
}

void uiBoot(const char *label, uint32_t id, const char *problems, bool buildTimePairing) {
  if (!ready) return;
  char title[24], idText[16];
  snprintf(title, sizeof(title), "Finder puck %s", label);
  snprintf(idText, sizeof(idText), "ID %08lX", (unsigned long)id);
  drawMessage(title, idText, problems[0] ? problems : (buildTimePairing ? "build-time pairing" : nullptr),
              problems[0] ? RED : ORANGE);
  present();
}
