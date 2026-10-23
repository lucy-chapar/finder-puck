#pragma once

// Tilt-compensated compass: LIS3DH accelerometer (0x18) + LIS2MDL magnetometer
// (0x1E) on the shared I2C bus.  Wire must already be started.

struct MagCal {
  float offset[3] = {0, 0, 0};   // hard iron, uT, board frame
  float scale[3] = {1, 1, 1};    // simple soft-iron correction per axis
  bool valid = false;
};

bool compassBegin();             // false if either sensor doesn't answer
bool compassOk();

// Reads both sensors.  heading = where the top of the screen points, degrees
// clockwise from magnetic north, smoothed.  False if the sensors failed.
bool compassUpdate(float &heading);

// Latest board-frame readings (accel in g, mag in uT before calibration).
void compassRaw(float acc[3], float mag[3]);

void compassSetCal(const MagCal &cal);
const MagCal &compassCal();

// Calibration: start, then call compassCalSample() while the user waves the
// puck in a figure-eight.  It returns 0-100: how far each axis has swung
// compared with CAL_MIN_SPAN_UT.  compassCalFinish() applies and returns the
// new calibration (valid=false if the swing was too small).
void compassCalStart();
int compassCalSample();
MagCal compassCalFinish();
