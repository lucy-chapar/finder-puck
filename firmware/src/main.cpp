// Finder puck: two paired pucks find each other in a crowd without phones.
//
// Each puck sends its GPS position to its partner over LoRa every ~1.5 s and
// shows a big arrow and the distance to the partner on a round radar screen,
// turned by a tilt-compensated compass.  The motor pulses faster as the partner gets
// closer.  The four LEDs strobe short-short-long in the pair's colour when
// either user presses the button or the two are within ~10 m.  Without a GPS
// fix the screen falls back to hot/cold from the LoRa signal strength.
//
// Button: press = beacon on/off (both pucks), double press = vibration on/off,
// hold 2 s = pairing, hold 5 s = compass calibration.
// Serial (USB, 115200): r = raw sensor stream, c = calibrate, p = pair,
// f = forget pairing, i = info.

#include <Adafruit_NeoPixel.h>
#include <Arduino.h>
#include <Preferences.h>
#include <TinyGPSPlus.h>
#include <Wire.h>
#include <driver/adc.h>
#include <esp_adc_cal.h>

#include "compass.h"
#include "config.h"
#include "link.h"
#include "ui.h"

#ifndef PUCK_LABEL
#define PUCK_LABEL ""
#endif
#ifndef PUCK_SECRET
#define PUCK_SECRET ""
#endif

static Adafruit_NeoPixel leds(LED_COUNT, PIN_LEDS, NEO_GRB + NEO_KHZ800);
static TinyGPSPlus gps;
static Preferences prefs;

// Beacon colours, picked per pair at pairing time.
static const uint32_t PAIR_COLOURS[] = {0xFF0060, 0x00FF40, 0x0080FF, 0xFFA000, 0xA000FF, 0x00FFFF};

enum Mode { MODE_FIND, MODE_PAIRING, MODE_CALIBRATE };
static Mode mode = MODE_FIND;

static uint32_t myId = 0;
static bool radioOk = false;
static bool hapticsOn = true;
static bool factoryPaired = false;

// Live values, refreshed in loop()
static float heading = 0;        // true heading of the screen's top, degrees
static bool headingOk = false;
static float batteryV = 4.0;
static uint8_t batteryPct = 100;
static bool charging = false;
static bool usbPower = false;   // USB plugged in (VBUS sense)
static uint32_t gpsLastByteMs = 0;

// Partner's last position with a fix, for the "lost partner" arrow
static bool lastKnownOk = false;
static double lastKnownLat = 0, lastKnownLon = 0;

static uint32_t beaconUntil = 0;   // local "find me" request
static bool beaconWasOn = false;
static uint32_t beaconStartMs = 0;

static uint32_t motorOffAt = 0;
static uint32_t nextPulseMs = 0;

static char toastText[24] = "";
static uint32_t toastUntil = 0;

static uint32_t calStartMs = 0;
static int calProgress = 0;

static bool rawStream = false;

// ---------------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------------

static void toast(const char *text, uint32_t ms = 1500) {
  strlcpy(toastText, text, sizeof(toastText));
  toastUntil = millis() + ms;
}

static void buzz(uint16_t ms) {
  if (!hapticsOn) return;
  digitalWrite(PIN_MOTOR, HIGH);
  motorOffAt = millis() + ms;
}

static bool batteryLow() { return batteryV < BATTERY_LOW_V; }
static bool batteryCritical() { return batteryV < BATTERY_CRITICAL_V; }

static uint8_t batteryPercent(float v) {
  static const float V[] = {3.30, 3.40, 3.50, 3.60, 3.65, 3.70, 3.75, 3.80, 3.90, 4.00, 4.10, 4.20};
  static const uint8_t P[] = {0, 2, 5, 12, 20, 30, 40, 50, 65, 78, 90, 100};
  if (v <= V[0]) return 0;
  for (int i = 1; i < 12; i++) {
    if (v < V[i]) return P[i - 1] + (P[i] - P[i - 1]) * (v - V[i - 1]) / (V[i] - V[i - 1]);
  }
  return 100;
}

static void readBattery() {
  float v = analogReadMilliVolts(PIN_BATTERY) * BATTERY_DIVIDER / 1000.0f;
  static bool first = true;
  batteryV = first ? v : batteryV + 0.2f * (v - batteryV);
  first = false;
  batteryPct = batteryPercent(batteryV);
}

// MCP73831 STAT reaches IO6 through R20 (100k) with R21 (150k) to ground: low while
// charging or with no USB, about 3 V once the cell is full.  IO15 sees VBUS through the
// same 100k/150k divider, so the two together tell charging, full and unplugged apart.
static void readCharging() {
  static bool init = false;
  if (!init) {
    pinMode(PIN_CHG_SENSE, INPUT);
    pinMode(PIN_VBUS_SENSE, INPUT);
    init = true;
  }
  usbPower = digitalRead(PIN_VBUS_SENSE);
  bool now = usbPower && !digitalRead(PIN_CHG_SENSE);
  static uint8_t onCount = 0, offCount = 0;   // needs 2 readings in a row to change
  if (now) offCount = 0, onCount = min(onCount + 1, 2);
  else onCount = 0, offCount = min(offCount + 1, 2);
  if (onCount >= 2) charging = true;
  if (offCount >= 2) charging = false;
}

static bool myFix() { return gps.location.isValid() && gps.location.age() < 5000; }

static bool partnerFresh() {
  const PartnerState &p = linkPartner();
  return p.heard && millis() - p.lastMs < PARTNER_LOST_MS;
}

// Distance and bearing to the partner, when both have a fix and the link is fresh.
static bool partnerVector(float &distanceM, float &bearingDeg) {
  const PartnerState &p = linkPartner();
  if (!myFix() || !partnerFresh() || !p.report.fix) return false;
  distanceM = TinyGPSPlus::distanceBetween(gps.location.lat(), gps.location.lng(), p.report.lat, p.report.lon);
  bearingDeg = TinyGPSPlus::courseTo(gps.location.lat(), gps.location.lng(), p.report.lat, p.report.lon);
  return true;
}

// ---------------------------------------------------------------------------
// Storage
// ---------------------------------------------------------------------------

static void savePairing(const Pairing &p) { prefs.putBytes("pairing", &p, sizeof(p)); }

static void loadSettings() {
  prefs.begin("puck", false);
  myId = prefs.getUInt("id", 0);
  if (myId == 0) {
    myId = esp_random() ^ (uint32_t)ESP.getEfuseMac();
    if (myId == 0) myId = 1;
    prefs.putUInt("id", myId);
  }
  hapticsOn = prefs.getBool("haptics", true);

  MagCal cal;
  if (prefs.getBytesLength("magcal") == sizeof(cal)) {
    prefs.getBytes("magcal", &cal, sizeof(cal));
    compassSetCal(cal);
  }
}

static void loadPairing() {
  Pairing p;
  if (prefs.getBytesLength("pairing") == sizeof(p)) prefs.getBytes("pairing", &p, sizeof(p));
  if (!p.paired && strlen(PUCK_SECRET) > 0) {
    p = linkPairingFromSecret(PUCK_SECRET);
    factoryPaired = true;
  }
  linkSetPairing(p);
}

// ---------------------------------------------------------------------------
// Modes
// ---------------------------------------------------------------------------

static void startPairing() {
  if (!radioOk) {
    toast("No radio!");
    return;
  }
  mode = MODE_PAIRING;
  linkStartPairing();
  buzz(150);
}

static void startCalibration() {
  if (!compassOk()) {
    toast("No compass!");
    return;
  }
  mode = MODE_CALIBRATE;
  compassCalStart();
  calStartMs = millis();
  calProgress = 0;
  buzz(150);
}

static void finishCalibration() {
  MagCal cal = compassCalFinish();
  mode = MODE_FIND;
  if (cal.valid) {
    prefs.putBytes("magcal", &cal, sizeof(cal));
    toast("Compass OK");
    buzz(300);
  } else {
    toast("Cal failed, retry", 2500);
  }
}

static void cancelMode() {
  if (mode == MODE_PAIRING) linkStopPairing();
  mode = MODE_FIND;
  toast("Cancelled");
}

static void forgetPairing() {
  prefs.remove("pairing");
  loadPairing();
  toast("Pairing cleared");
}

// ---------------------------------------------------------------------------
// Button
// ---------------------------------------------------------------------------

static bool buttonDown = false;
static uint32_t pressStartMs = 0;
static uint32_t lastChangeMs = 0;
static bool clickPending = false;
static uint32_t clickMs = 0;
static uint8_t holdStage = 0;   // 0 short, 1 pair, 2 calibrate (while held)

static void onShortPress() {
  if (mode != MODE_FIND) {
    cancelMode();
    return;
  }
  if (millis() < beaconUntil) {
    beaconUntil = 0;
    toast("Beacon off");
  } else {
    beaconUntil = millis() + BEACON_BUTTON_MS;
    toast("Beacon on");
  }
}

static void onDoublePress() {
  hapticsOn = !hapticsOn;
  prefs.putBool("haptics", hapticsOn);
  toast(hapticsOn ? "Vibration on" : "Vibration off");
  buzz(120);
}

static void updateButton() {
  uint32_t now = millis();
  bool down = digitalRead(PIN_BUTTON) == LOW;
  if (down != buttonDown && now - lastChangeMs > 30) {
    lastChangeMs = now;
    buttonDown = down;
    if (down) {
      pressStartMs = now;
      holdStage = 0;
    } else {
      uint32_t held = now - pressStartMs;
      if (held >= CAL_PRESS_MS) {
        startCalibration();
      } else if (held >= LONG_PRESS_MS) {
        if (mode == MODE_PAIRING) cancelMode();
        else startPairing();
      } else if (mode != MODE_FIND) {
        cancelMode();
      } else if (clickPending && now - clickMs < DOUBLE_CLICK_MS) {
        clickPending = false;
        onDoublePress();
      } else {
        clickPending = true;
        clickMs = now;
      }
    }
  }
  if (buttonDown) {
    uint32_t held = now - pressStartMs;
    uint8_t stage = held >= CAL_PRESS_MS ? 2 : held >= LONG_PRESS_MS ? 1 : 0;
    if (stage != holdStage) {
      holdStage = stage;
      buzz(40);   // tick so you can feel the thresholds
    }
  }
  if (clickPending && now - clickMs >= DOUBLE_CLICK_MS) {
    clickPending = false;
    onShortPress();
  }
}

// ---------------------------------------------------------------------------
// Beacon LEDs and vibration
// ---------------------------------------------------------------------------

static void updateBeacon(bool on) {
  uint32_t now = millis();
  if (on && !beaconWasOn) beaconStartMs = now;
  bool lit = false;
  if (on) {
    // short, short, long, pause: 1.5 s
    uint32_t t = (now - beaconStartMs) % 1500;
    lit = t < 80 || (t >= 200 && t < 280) || (t >= 400 && t < 800);
  }
  static bool wasLit = false;
  if (lit != wasLit || on != beaconWasOn) {
    uint32_t c = lit ? PAIR_COLOURS[linkPairing().colour % 6] : 0;
    for (int i = 0; i < LED_COUNT; i++) leds.setPixelColor(i, c);
    leds.show();
    wasLit = lit;
  }
  beaconWasOn = on;
}

// Pulse period in ms, or 0 for no pulses.
static uint32_t hapticPeriod(bool haveVector, float distance) {
  if (haveVector) {
    if (distance > HAPTIC_MAX_DISTANCE_M) return 0;
    float f = (constrain(distance, 5.0f, (float)HAPTIC_MAX_DISTANCE_M) - 5.0f) / (HAPTIC_MAX_DISTANCE_M - 5.0f);
    return HAPTIC_FAST_MS + f * (HAPTIC_SLOW_MS - HAPTIC_FAST_MS);
  }
  if (partnerFresh()) {   // no GPS: go by signal strength, -120 dBm slow .. -50 dBm fast
    float f = constrain((-50.0f - linkPartner().rssi) / 70.0f, 0.0f, 1.0f);
    return HAPTIC_FAST_MS + f * (HAPTIC_SLOW_MS - HAPTIC_FAST_MS);
  }
  return 0;
}

static void updateMotor(uint32_t period) {
  uint32_t now = millis();
  if (motorOffAt && (int32_t)(now - motorOffAt) >= 0) {
    digitalWrite(PIN_MOTOR, LOW);
    motorOffAt = 0;
  }
  if (period == 0 || mode != MODE_FIND) {
    nextPulseMs = now + 500;
    return;
  }
  if ((int32_t)(now - nextPulseMs) >= 0) {
    buzz(HAPTIC_PULSE_MS);
    nextPulseMs = now + period;
  }
  // Shorten the wait at once when the partner gets much closer.
  if ((int32_t)(nextPulseMs - now) > (int32_t)period) nextPulseMs = now + period;
}

// ---------------------------------------------------------------------------
// Screen
// ---------------------------------------------------------------------------

static bool screenOn = true;
static uint32_t lastMotionMs = 0;
static uint32_t faceDownSinceMs = 0;

// Pocket mode: screen off when face-down or still; on again when picked up.
static void updatePower() {
  uint32_t now = millis();
  bool want = true;
  if (compassOk() && mode == MODE_FIND) {
    float a[3], m[3];
    compassRaw(a, m);
    static float prev[3] = {0, 0, 0};
    float delta = fabsf(a[0] - prev[0]) + fabsf(a[1] - prev[1]) + fabsf(a[2] - prev[2]);
    for (int i = 0; i < 3; i++) prev[i] = a[i];
    if (delta > MOTION_G) lastMotionMs = now;
    if (a[2] > -0.6f) faceDownSinceMs = 0;
    else if (!faceDownSinceMs) faceDownSinceMs = now;
    bool faceDown = faceDownSinceMs && now - faceDownSinceMs > FACE_DOWN_MS;
    want = !faceDown && now - lastMotionMs < STILL_MS;
  }
  if (want != screenOn) {
    screenOn = want;
    uiPower(want);
  }
}

static void drawScreen() {
  uint32_t now = millis();
  const PartnerState &p = linkPartner();
  UiState s;
  s.gpsAlive = now - gpsLastByteMs < 3000;
  s.fix = s.ownFix = myFix();
  s.sats = gps.satellites.value();
  s.batteryPct = batteryPct;
  s.batteryLow = batteryLow();
  s.charging = charging;
  s.northUp = !headingOk;
  s.northDeg = headingOk ? 360.0f - heading : 0;
  s.partnerBeacon = partnerFresh() && p.report.beacon;
  char status[24] = "";

  float distance, bearing;
  if (batteryCritical() && !charging && (now / 2000) % 5 == 0) {
    s.screen = SCREEN_BATTERY;
  } else if (mode == MODE_PAIRING) {
    s.screen = SCREEN_PAIRING;
  } else if (mode == MODE_CALIBRATE) {
    s.screen = SCREEN_CALIBRATE;
    s.calProgress = calProgress;
    s.calSeconds = (now - calStartMs) / 1000;
  } else if (!linkPairing().paired) {
    s.screen = SCREEN_NOT_PAIRED;
  } else if (partnerVector(distance, bearing)) {
    s.screen = SCREEN_FIND;
    s.arrow = s.distance = true;
    s.arrowDeg = headingOk ? bearing - heading : bearing;
    s.distanceM = distance;
    // GPS error is a few metres per puck; below that the arrow is guesswork.
    float accuracy = 2.5f * (gps.hdop.hdop() + p.report.hdop);
    if (distance < accuracy) snprintf(status, sizeof(status), "+-%d m", (int)accuracy);
    else if (p.report.lowBattery) snprintf(status, sizeof(status), "partner battery low");
  } else if (!p.heard || !partnerFresh()) {
    s.screen = SCREEN_SEARCHING;
    if (p.heard && lastKnownOk && myFix()) {   // hollow arrow to where the partner was last seen
      s.arrow = s.arrowHollow = s.distance = true;
      s.distanceM = TinyGPSPlus::distanceBetween(gps.location.lat(), gps.location.lng(), lastKnownLat, lastKnownLon);
      float b = TinyGPSPlus::courseTo(gps.location.lat(), gps.location.lng(), lastKnownLat, lastKnownLon);
      s.arrowDeg = headingOk ? b - heading : b;
    }
    if (p.heard) snprintf(status, sizeof(status), "lost partner %lus", (unsigned long)((now - p.lastMs) / 1000));
    else snprintf(status, sizeof(status), "looking for partner");
  } else {
    s.screen = SCREEN_HOT_COLD;
    s.rssi = p.rssi;
    s.rssiTrend = p.rssi - p.rssiSlow;
  }
  if (status[0]) s.status = status;

  if (buttonDown && now - pressStartMs > 700)
    s.hint = holdStage == 2 ? "release: compass" : holdStage == 1 ? "release: pair" : "keep holding...";
  else if (now < toastUntil)
    s.toast = toastText;
  uiDraw(s);
}

// ---------------------------------------------------------------------------
// Serial debug commands
// ---------------------------------------------------------------------------

static void printInfo() {
  const Pairing &p = linkPairing();
  const PartnerState &ps = linkPartner();
  Serial.printf("puck %s id %08lX, paired %d (pair %08lX, partner %08lX, colour %d%s)\n", PUCK_LABEL,
                (unsigned long)myId, p.paired, (unsigned long)p.pairId, (unsigned long)p.partnerId, p.colour,
                factoryPaired ? ", build-time" : "");
  Serial.printf("gps fix %d sats %d hdop %.1f  lat %.6f lon %.6f\n", myFix(), (int)gps.satellites.value(),
                gps.hdop.hdop(), gps.location.lat(), gps.location.lng());
  Serial.printf("partner heard %d age %lums rssi %.0f snr %.1f fix %d\n", ps.heard,
                (unsigned long)(millis() - ps.lastMs), ps.rssi, ps.snr, ps.report.fix);
  Serial.printf("heading %.0f (ok %d, cal %d)  battery %.2fV %d%% charging %d  vibration %d  screen %d\n",
                heading, headingOk, compassCal().valid, batteryV, batteryPct, charging, hapticsOn, screenOn);
}

static void handleSerial() {
  while (Serial.available()) {
    switch (Serial.read()) {
      case 'r': rawStream = !rawStream; break;
      case 'c': startCalibration(); break;
      case 'p': startPairing(); break;
      case 'f': forgetPairing(); break;
      case 'i': printInfo(); break;
    }
  }
  static uint32_t lastRaw = 0;
  if (rawStream && millis() - lastRaw > 200) {
    lastRaw = millis();
    float a[3], m[3];
    compassRaw(a, m);
    Serial.printf("acc %6.2f %6.2f %6.2f g   mag %7.1f %7.1f %7.1f uT   heading %5.1f\n", a[0], a[1], a[2], m[0],
                  m[1], m[2], heading);
  }
}

// ---------------------------------------------------------------------------

void setup() {
  setCpuFrequencyMhz(80);
  Serial.begin(115200);

  pinMode(PIN_MOTOR, OUTPUT);
  digitalWrite(PIN_MOTOR, LOW);
  pinMode(PIN_BUTTON, INPUT_PULLUP);
  analogSetPinAttenuation(PIN_BATTERY, ADC_11db);

  leds.begin();
  leds.clear();
  leds.show();

  bool displayOk = uiBegin();
  Wire.begin(PIN_SDA, PIN_SCL, 400000);

  bool compassFound = compassBegin();
  loadSettings();   // after compassBegin so the calibration sticks
  Serial1.begin(GPS_BAUD, SERIAL_8N1, PIN_GPS_RX, PIN_GPS_TX);

  uint32_t boots = prefs.getUInt("boots", 0) + 1;
  prefs.putUInt("boots", boots);
  radioOk = linkBegin(myId, boots);
  loadPairing();
  readBattery();
  readCharging();

  char problems[32];
  snprintf(problems, sizeof(problems), "%s%s%s", radioOk ? "" : "LoRa? ", compassFound ? "" : "Compass? ",
           compassFound && !compassCal().valid ? "Calibrate compass" : "");
  uiBoot(PUCK_LABEL, myId, problems, factoryPaired);
  if (!displayOk) Serial.println("display: no memory for the frame buffer");
  printInfo();
  delay(1500);
}

void loop() {
  uint32_t now = millis();

  while (Serial1.available()) {
    gps.encode(Serial1.read());
    gpsLastByteMs = now;
  }

  Report mine;
  mine.fix = myFix();
  mine.lat = gps.location.lat();
  mine.lon = gps.location.lng();
  mine.sats = gps.satellites.value();
  mine.hdop = gps.hdop.isValid() ? gps.hdop.hdop() : 99;
  mine.beacon = now < beaconUntil;
  mine.batteryPct = batteryPct;
  mine.lowBattery = batteryLow();
  linkLoop(mine);

  switch (linkPairingStatus()) {
    case PAIR_DONE:
      savePairing(linkPairing());
      factoryPaired = false;
      lastKnownOk = false;
      mode = MODE_FIND;
      toast("Paired!", 2500);
      buzz(400);
      break;
    case PAIR_TIMEOUT:
      mode = MODE_FIND;
      toast("Nobody found", 2500);
      break;
    default: break;
  }

  static uint32_t lastSensorMs = 0;
  if (now - lastSensorMs >= 50) {   // 20 Hz, the magnetometer's rate
    lastSensorMs = now;
    if (mode == MODE_CALIBRATE) {
      calProgress = compassCalSample();
      uint32_t t = now - calStartMs;
      if ((t >= CAL_MIN_MS && calProgress >= 100) || t >= CAL_MAX_MS) finishCalibration();
    } else {
      float magHeading;
      headingOk = compassUpdate(magHeading);
      if (headingOk) heading = fmodf(magHeading + MAG_DECLINATION_DEG + 360.0f, 360.0f);
    }
    updatePower();
  }

  static uint32_t lastBatteryMs = 0;
  if (now - lastBatteryMs >= 2000) {
    lastBatteryMs = now;
    readBattery();
    readCharging();
  }

  // Remember where the partner was, and buzz when the link drops or comes back.
  const PartnerState &p = linkPartner();
  if (partnerFresh() && p.report.fix) {
    lastKnownOk = true;
    lastKnownLat = p.report.lat;
    lastKnownLon = p.report.lon;
  }
  static bool wasFresh = false;
  bool fresh = partnerFresh();
  if (fresh != wasFresh) {
    toast(fresh ? "Partner found" : "Lost partner", 2000);
    buzz(fresh ? 200 : 600);
    wasFresh = fresh;
  }

  float distance = 0, bearing = 0;
  bool vector = partnerVector(distance, bearing);
  bool beacon = mode == MODE_FIND && linkPairing().paired && !batteryCritical() &&
                (now < beaconUntil || (fresh && p.report.beacon) || (vector && distance < BEACON_DISTANCE_M) ||
                 (fresh && !vector && p.rssi > BEACON_RSSI_DBM));
  updateBeacon(beacon);
  updateMotor(hapticPeriod(vector, distance));

  updateButton();
  if (buttonDown) lastMotionMs = now;   // a press wakes the screen
  handleSerial();

  static uint32_t lastDrawMs = 0;
  if (screenOn && now - lastDrawMs >= 1000 / DISPLAY_FPS) {
    lastDrawMs = now;
    drawScreen();
  }
  delay(5);
}
