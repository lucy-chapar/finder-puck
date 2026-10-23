#include "compass.h"

#include <Arduino.h>
#include <Wire.h>
#include <math.h>

#include "config.h"

namespace {

const uint8_t ACC_ADDR = 0x18;   // LIS3DH, SA0 tied to GND
const uint8_t MAG_ADDR = 0x1E;   // LIS2MDL

const int ACC_AXIS_MAP[3] = ACCEL_AXIS;
const int ACC_AXIS_SIGN[3] = ACCEL_SIGN;
const int MAG_AXIS_MAP[3] = MAG_AXIS;
const int MAG_AXIS_SIGN[3] = MAG_SIGN;

bool ok = false;
MagCal cal;
float acc[3], mag[3];             // board frame, raw
float headingSin = 0, headingCos = 1;
bool haveHeading = false;
float calMin[3], calMax[3];

bool writeReg(uint8_t addr, uint8_t reg, uint8_t value) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission() == 0;
}

bool readRegs(uint8_t addr, uint8_t reg, uint8_t *buf, uint8_t len) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(addr, len) != len) return false;
  for (uint8_t i = 0; i < len; i++) buf[i] = Wire.read();
  return true;
}

uint8_t readReg(uint8_t addr, uint8_t reg) {
  uint8_t v = 0;
  readRegs(addr, reg, &v, 1);
  return v;
}

void toBoard(const float in[3], const int map[3], const int sign[3], float out[3]) {
  for (int i = 0; i < 3; i++) out[i] = in[map[i]] * sign[i];
}

bool readSensors() {
  uint8_t b[6];
  // LIS3DH: set bit 7 of the register address to auto-increment.
  if (!readRegs(ACC_ADDR, 0x28 | 0x80, b, 6)) return false;
  float a[3];
  for (int i = 0; i < 3; i++) {
    int16_t v = (int16_t)(b[2 * i] | (b[2 * i + 1] << 8));
    a[i] = (v >> 4) * 0.001f;        // high-resolution mode, +-2 g: 1 mg per digit
  }
  if (!readRegs(MAG_ADDR, 0x68, b, 6)) return false;
  float m[3];
  for (int i = 0; i < 3; i++) {
    int16_t v = (int16_t)(b[2 * i] | (b[2 * i + 1] << 8));
    m[i] = v * 0.15f;                // 1.5 mG per digit = 0.15 uT
  }
  toBoard(a, ACC_AXIS_MAP, ACC_AXIS_SIGN, acc);
  toBoard(m, MAG_AXIS_MAP, MAG_AXIS_SIGN, mag);
  return true;
}

void cross(const float a[3], const float b[3], float out[3]) {
  out[0] = a[1] * b[2] - a[2] * b[1];
  out[1] = a[2] * b[0] - a[0] * b[2];
  out[2] = a[0] * b[1] - a[1] * b[0];
}

bool normalize(float v[3]) {
  float n = sqrtf(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]);
  if (n < 1e-6f) return false;
  for (int i = 0; i < 3; i++) v[i] /= n;
  return true;
}

}  // namespace

bool compassBegin() {
  ok = false;
  if (readReg(ACC_ADDR, 0x0F) != 0x33) return false;   // LIS3DH WHO_AM_I
  if (readReg(MAG_ADDR, 0x4F) != 0x40) return false;   // LIS2MDL WHO_AM_I
  ok = writeReg(ACC_ADDR, 0x20, 0x37) &&   // CTRL_REG1: 25 Hz, XYZ on
       writeReg(ACC_ADDR, 0x23, 0x88) &&   // CTRL_REG4: block update, +-2 g, high resolution
       writeReg(MAG_ADDR, 0x60, 0x84) &&   // CFG_REG_A: temperature compensation, 20 Hz, continuous
       writeReg(MAG_ADDR, 0x61, 0x02) &&   // CFG_REG_B: offset cancellation
       writeReg(MAG_ADDR, 0x62, 0x10);     // CFG_REG_C: block update
  return ok;
}

bool compassOk() { return ok; }

void compassRaw(float a[3], float m[3]) {
  for (int i = 0; i < 3; i++) {
    a[i] = acc[i];
    m[i] = mag[i];
  }
}

void compassSetCal(const MagCal &c) { cal = c; }
const MagCal &compassCal() { return cal; }

bool compassUpdate(float &heading) {
  if (!ok || !readSensors()) return false;

  float m[3];
  for (int i = 0; i < 3; i++) m[i] = (mag[i] - cal.offset[i]) * cal.scale[i];

  // The accelerometer reads +1 g "up" at rest, so down is the opposite way.
  // East = down x field, north = east x down; then project the screen's up
  // direction (+Y) onto them.  Works at any tilt short of pointing +Y at the ground.
  float down[3] = {-acc[0], -acc[1], -acc[2]};
  float east[3], north[3];
  if (!normalize(down)) return false;
  cross(down, m, east);
  if (!normalize(east)) return false;
  cross(east, down, north);
  float h = atan2f(east[1], north[1]);

  // Smooth on the unit circle so 359 -> 1 doesn't swing through 180.
  const float k = haveHeading ? 0.35f : 1.0f;
  headingSin += k * (sinf(h) - headingSin);
  headingCos += k * (cosf(h) - headingCos);
  haveHeading = true;
  heading = atan2f(headingSin, headingCos) * 180.0f / PI;
  if (heading < 0) heading += 360.0f;
  return true;
}

void compassCalStart() {
  for (int i = 0; i < 3; i++) {
    calMin[i] = 1e9f;
    calMax[i] = -1e9f;
  }
}

int compassCalSample() {
  if (!ok || !readSensors()) return 0;
  int worst = 100;
  for (int i = 0; i < 3; i++) {
    calMin[i] = min(calMin[i], mag[i]);
    calMax[i] = max(calMax[i], mag[i]);
    int pct = (int)(100.0f * (calMax[i] - calMin[i]) / CAL_MIN_SPAN_UT);
    worst = min(worst, pct);
  }
  return constrain(worst, 0, 100);
}

MagCal compassCalFinish() {
  MagCal c;
  float span[3], avg = 0;
  for (int i = 0; i < 3; i++) {
    span[i] = calMax[i] - calMin[i];
    if (span[i] < CAL_MIN_SPAN_UT) return c;   // valid stays false
    c.offset[i] = (calMax[i] + calMin[i]) / 2;
    avg += span[i] / 3;
  }
  for (int i = 0; i < 3; i++) c.scale[i] = avg / span[i];
  c.valid = true;
  cal = c;
  haveHeading = false;
  return c;
}
