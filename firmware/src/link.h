#pragma once

#include <stdint.h>

// LoRa link between the two pucks: position packets (encrypted and
// authenticated with the pairing key) and the pairing handshake.

struct Pairing {
  bool paired = false;
  uint32_t partnerId = 0;   // 0 = accept any puck with this key (build-time pairing)
  uint32_t pairId = 0;      // sent in clear so pucks can skip other pairs' packets
  uint8_t key[32] = {0};    // AES-128 key, then HMAC key
  uint8_t colour = 0;       // index into the beacon colours
};

// What each puck tells the other every 1.5 s.
struct Report {
  bool fix = false;
  bool beacon = false;      // "find me": the sender's button beacon is on
  bool lowBattery = false;
  double lat = 0, lon = 0;
  uint8_t sats = 0;
  float hdop = 99;
  uint8_t batteryPct = 0;
};

struct PartnerState {
  bool heard = false;       // since boot
  uint32_t lastMs = 0;      // millis() of the last good packet
  Report report;
  float rssi = -130;        // dBm, smoothed
  float rssiSlow = -130;    // slower average, for "warmer / colder"
  float snr = 0;
};

enum PairResult { PAIR_IDLE, PAIR_SEARCHING, PAIR_DONE, PAIR_TIMEOUT };

bool linkBegin(uint32_t myId, uint32_t bootCount);
void linkSetPairing(const Pairing &p);
const Pairing &linkPairing();

// Call every loop.  `mine` is what goes out in the next position packet.
void linkLoop(const Report &mine);
const PartnerState &linkPartner();

void linkStartPairing();
void linkStopPairing();
PairResult linkPairingStatus();   // PAIR_DONE once: the new pairing is in linkPairing()

// Build-time pairing from a shared secret (PUCK_SECRET).
Pairing linkPairingFromSecret(const char *secret);

// Random bytes mixing esp_random() with radio noise.
void linkRandom(uint8_t *out, int len);
