#pragma once

#include <stdint.h>

// Round 240x240 GC9A01 radar display.  Everything is drawn into a full-screen
// sprite and pushed in one go, so there's no flicker.

enum Screen {
  SCREEN_NOT_PAIRED,
  SCREEN_FIND,        // arrow + distance
  SCREEN_SEARCHING,   // never heard the partner, or lost it (hollow arrow if a last position is known)
  SCREEN_HOT_COLD,    // partner heard, but someone has no GPS fix
  SCREEN_PAIRING,
  SCREEN_CALIBRATE,
  SCREEN_BATTERY,     // critical battery warning
};

struct UiState {
  Screen screen = SCREEN_FIND;

  // Arrow, degrees clockwise from 12 o'clock.  northUp: no compass, so the
  // arrow is relative to north instead of to where the puck points.
  bool arrow = false;
  bool arrowHollow = false;
  float arrowDeg = 0;
  bool northUp = false;
  float northDeg = 0;          // where north is on screen, if the compass works
  bool distance = false;
  float distanceM = 0;

  // Top status
  bool gpsAlive = true;
  bool fix = false;
  int sats = 0;
  uint8_t batteryPct = 100;
  bool batteryLow = false;
  bool charging = false;

  // Bottom status line, or null
  const char *status = nullptr;
  bool partnerBeacon = false;

  // Hot / cold
  bool ownFix = false;
  float rssi = -130;
  float rssiTrend = 0;

  int calProgress = 0;          // 0-100
  uint32_t calSeconds = 0;

  const char *toast = nullptr;  // centred message box
  const char *hint = nullptr;   // bottom pill while the button is held
};

bool uiBegin();                 // false if the frame buffer couldn't be allocated
void uiDraw(const UiState &s);
void uiBoot(const char *label, uint32_t id, const char *problems, bool buildTimePairing);
void uiPower(bool on);          // backlight + panel sleep
