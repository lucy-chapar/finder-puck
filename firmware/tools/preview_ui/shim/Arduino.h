// Just enough of Arduino.h to compile src/ui.cpp on a computer.
#pragma once
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <algorithm>

extern uint32_t previewMillis;
inline uint32_t millis() { return previewMillis; }
using std::max;
using std::min;
template <class T, class L, class H>
inline T constrain(T x, L lo, H hi) { return x < lo ? lo : x > hi ? hi : x; }
#ifndef PI
#define PI 3.14159265358979f
#endif
