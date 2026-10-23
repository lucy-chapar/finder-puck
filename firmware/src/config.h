#pragma once

// ---- Pins (tools/generate_puck.py, PARTS) -------------------------------
#define PIN_LORA_NSS 10
#define PIN_LORA_MOSI 11
#define PIN_LORA_SCK 12
#define PIN_LORA_MISO 13
#define PIN_LORA_RST 14
#define PIN_LORA_DIO0 4
#define PIN_LORA_DIO1 5
#define PIN_GPS_TX 17      // ESP32 -> GPS RXD
#define PIN_GPS_RX 18      // GPS TXD -> ESP32
#define PIN_SDA 8          // LIS3DH + LIS2MDL
#define PIN_SCL 9
#define PIN_IMU_INT 2      // LIS3DH INT1 (not used yet)
#define PIN_LEDS 38        // LED1-LED4 DIN
#define PIN_MOTOR 7        // AO3400A gate, high = motor on (IO39 has a reset pull-up: never use it for a load)
#define PIN_BUTTON 0       // SW1 to GND, 10k pull-up (also the boot button)
#define PIN_BATTERY 1      // VSYS through a 100k/100k divider
#define PIN_CHG_SENSE 6    // MCP73831 STAT through 100k/150k (R20/R21): high only when the cell is full
#define PIN_VBUS_SENSE 15  // VBUS through 100k/150k (R25/R26): high when USB is plugged in

// Round 240x240 GC9A01 LCD on its own SPI host (SPI3, through the GPIO matrix)
#define PIN_LCD_SCK 40
#define PIN_LCD_MOSI 41
#define PIN_LCD_CS 42      // 10k pull-up
#define PIN_LCD_DC 21
#define PIN_LCD_RST 47     // 10k pull-up
#define PIN_LCD_BL 48      // PWM to the backlight MOSFET; dark until driven

#define LED_COUNT 4
#define GPS_BAUD 9600      // SAM-M10Q factory default, NMEA

// ---- Radio ---------------------------------------------------------------------
// 915 MHz, SF9 / 125 kHz: about 200 ms on air per position packet and roughly
// 1-2 km range in a crowd with small antennas.  Check your local rules before
// changing frequency or power (US: 902-928 MHz ISM).
#define LORA_FREQ_MHZ 915.0
#define LORA_BW_KHZ 125.0
#define LORA_SF 9
#define LORA_CR 7          // 4/7
#define LORA_SYNC_WORD 0x12
#define LORA_POWER_DBM 17
#define SEND_INTERVAL_MS 1500   // plus or minus SEND_JITTER_MS so the two pucks don't keep colliding
#define SEND_JITTER_MS 300

// ---- Behaviour -----------------------------------------------------------------
#define PARTNER_LOST_MS 20000UL       // no packet for this long = "lost partner"
#define BEACON_DISTANCE_M 10.0        // strobe automatically when closer than this
#define BEACON_RSSI_DBM -55           // ...or, without GPS, when the signal is this strong
#define BEACON_BUTTON_MS 60000UL      // a button press keeps both beacons on this long
#define HAPTIC_MAX_DISTANCE_M 300.0   // no vibration further away than this
#define HAPTIC_SLOW_MS 4000           // pulse period at HAPTIC_MAX_DISTANCE_M
#define HAPTIC_FAST_MS 350            // pulse period at 5 m and closer
#define HAPTIC_PULSE_MS 70
#define PAIRING_TIMEOUT_MS 30000UL
#define PAIRING_MIN_RSSI_DBM -75      // pairing only accepts a puck that's right next to this one

// Button timings
#define LONG_PRESS_MS 2000            // release after 2 s = pairing mode
#define CAL_PRESS_MS 5000             // release after 5 s = compass calibration
#define DOUBLE_CLICK_MS 350           // two quick presses = vibration on/off

// ---- Display -------------------------------------------------------------------
// Which way up the picture is drawn (LovyanGFX setRotation, 0-3 quarter turns;
// sets the GC9A01 MADCTL).  12 o'clock on screen must be the GPS / sky-window side
// of the puck (the panel's FPC leaves at 6 o'clock).  UNVERIFIED: 0 assumes the
// panel's native top is opposite its FPC, as on most GC9A01 modules.
#define LCD_ROTATION 0
// SPI clock.  40 MHz is safe through the GPIO matrix; try 80 MHz once a board
// works.  Never 26.67 or 13.33 MHz: their harmonics land on GPS L1 (1575.42 MHz).
#define LCD_SPI_HZ 40000000
#define LCD_BRIGHTNESS 60        // backlight 0-255; dim by default, it's the biggest power draw
#define DISPLAY_FPS 8

// Pocket mode: backlight off and panel asleep when face-down or still.
#define FACE_DOWN_MS 1500        // screen down (Z < -0.6 g) this long
#define STILL_MS 60000UL         // no movement this long
#define MOTION_G 0.06            // change in acceleration that counts as movement

// ---- Compass -------------------------------------------------------------------
// Magnetic declination at the venue in degrees, east positive (look it up at
// https://www.ngdc.noaa.gov/geomag/calculators/magcalc.shtml).  Without it the
// arrow is off by that many degrees.  The bearing to the partner is from GPS,
// so it's relative to true north.
#define MAG_DECLINATION_DEG 0.0

// How each sensor's axes line up with the board.  Board frame: +X towards the
// right edge of the screen, +Y towards the top of the screen (the way the arrow
// points when the partner is straight ahead), +Z out of the screen.
// Entry i says which sensor axis (0=x 1=y 2=z) gives board axis i, and its sign.
// UNVERIFIED: check with the 'r' serial command once a board exists (README).
#define ACCEL_AXIS {0, 1, 2}
#define ACCEL_SIGN {1, 1, 1}
#define MAG_AXIS {0, 1, 2}
#define MAG_SIGN {1, 1, 1}

#define CAL_MIN_MS 15000          // figure-eight for at least this long
#define CAL_MAX_MS 45000
#define CAL_MIN_SPAN_UT 40.0      // each axis must swing at least this far (Earth's field is 25-65 uT)

// ---- Battery (1S LiPo, measured on VSYS) -----------------------------------------
#define BATTERY_DIVIDER 2.0
#define BATTERY_LOW_V 3.50        // warning icon
#define BATTERY_CRITICAL_V 3.35   // full-screen warning, beacon LEDs disabled
// Charging = USB present (IO15 high) and STAT low (IO6 low); full = both high.
