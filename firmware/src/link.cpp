#include "link.h"

#include <Arduino.h>
#include <RadioLib.h>
#include <SPI.h>
#include <mbedtls/aes.h>
#include <mbedtls/md.h>
#include <string.h>

#include "config.h"

// Packet formats (little-endian):
//
// Position, 30 bytes:
//   0     magic 0xF1
//   1     type 1
//   2-5   pair ID
//   6-9   sender ID
//   10-13 sequence number (boot count << 20 | packet count), never repeats
//   14-25 payload, AES-128-CTR with nonce = bytes 2-13:
//         lat (int32, 1e-7 deg), lon (int32), flags, satellites, HDOP x10, battery %
//   26-29 first 4 bytes of HMAC-SHA256(bytes 0-25)
//
// Pairing, 26 bytes, in clear:
//   0 magic, 1 type 2, 2-5 sender ID, 6-21 sender's random key half,
//   22-25 ID of the puck the sender has heard (0 = none yet)

namespace {

const uint8_t MAGIC = 0xF1;
const uint8_t TYPE_POSITION = 1;
const uint8_t TYPE_PAIR = 2;
const int POSITION_LEN = 30;
const int PAIR_LEN = 26;
const int PAYLOAD_LEN = 12;
const uint8_t FLAG_FIX = 1, FLAG_BEACON = 2, FLAG_LOW_BATTERY = 4;
const uint32_t PAIR_SEND_MS = 600;
const uint32_t PAIR_LINGER_MS = 2500;   // keep announcing after success so the other puck finishes too
const uint8_t COLOUR_COUNT = 6;

SPIClass loraSpi(FSPI);
SX1276 radio = new Module(PIN_LORA_NSS, PIN_LORA_DIO0, PIN_LORA_RST, PIN_LORA_DIO1, loraSpi);

volatile bool dio0Fired = false;
bool radioOk = false;
bool transmitting = false;
uint32_t txStartMs = 0;
uint32_t nextSendMs = 0;

uint32_t myId = 0;
uint32_t seqHigh = 0, seqCount = 0;
uint32_t lastPartnerSeq = 0;
Pairing pairing;
PartnerState partner;

// Pairing session
bool pairingActive = false;
PairResult pairStatus = PAIR_IDLE;
uint32_t pairStartMs = 0, pairDoneMs = 0;
uint8_t myHalf[16];
uint32_t candidateId = 0;
uint8_t candidateHalf[16];
Pairing newPairing;

void IRAM_ATTR onDio0() { dio0Fired = true; }

void put32(uint8_t *p, uint32_t v) {
  for (int i = 0; i < 4; i++) p[i] = v >> (8 * i);
}

uint32_t get32(const uint8_t *p) {
  return p[0] | (p[1] << 8) | (p[2] << 16) | ((uint32_t)p[3] << 24);
}

void sha256(const uint8_t *in, size_t len, uint8_t out[32]) {
  mbedtls_md(mbedtls_md_info_from_type(MBEDTLS_MD_SHA256), in, len, out);
}

void tag(const uint8_t *data, size_t len, uint8_t out[4]) {
  uint8_t mac[32];
  mbedtls_md_hmac(mbedtls_md_info_from_type(MBEDTLS_MD_SHA256), pairing.key + 16, 16, data, len, mac);
  memcpy(out, mac, 4);
}

// CTR mode is its own inverse.
void crypt(const uint8_t *nonce12, uint8_t *data, size_t len) {
  mbedtls_aes_context aes;
  mbedtls_aes_init(&aes);
  mbedtls_aes_setkey_enc(&aes, pairing.key, 128);
  uint8_t counter[16] = {0}, stream[16];
  size_t off = 0;
  memcpy(counter, nonce12, 12);
  mbedtls_aes_crypt_ctr(&aes, len, &off, counter, stream, data, data);
  mbedtls_aes_free(&aes);
}

Pairing derive(const uint8_t *material, size_t len, uint32_t partnerId) {
  Pairing p;
  uint8_t buf[64], h[32];
  memcpy(buf + 8, material, min(len, sizeof(buf) - 8));
  size_t n = 8 + min(len, sizeof(buf) - 8);
  memcpy(buf, "puck-key", 8);
  sha256(buf, n, p.key);
  memcpy(buf, "puck-id.", 8);
  sha256(buf, n, h);
  p.pairId = get32(h) | 1;   // never 0
  p.colour = h[4] % COLOUR_COUNT;
  p.partnerId = partnerId;
  p.paired = true;
  return p;
}

void startTx(const uint8_t *buf, int len) {
  if (radio.startTransmit(const_cast<uint8_t *>(buf), len) == RADIOLIB_ERR_NONE) {
    transmitting = true;
    txStartMs = millis();
  } else {
    radio.startReceive();
  }
}

void sendPosition(const Report &r) {
  uint8_t p[POSITION_LEN];
  p[0] = MAGIC;
  p[1] = TYPE_POSITION;
  put32(p + 2, pairing.pairId);
  put32(p + 6, myId);
  put32(p + 10, seqHigh | (seqCount++ & 0xFFFFF));
  uint8_t *d = p + 14;
  put32(d, (int32_t)lround(r.lat * 1e7));
  put32(d + 4, (int32_t)lround(r.lon * 1e7));
  d[8] = (r.fix ? FLAG_FIX : 0) | (r.beacon ? FLAG_BEACON : 0) | (r.lowBattery ? FLAG_LOW_BATTERY : 0);
  d[9] = r.sats;
  d[10] = (uint8_t)constrain(lroundf(r.hdop * 10), 0, 255);
  d[11] = r.batteryPct;
  crypt(p + 2, d, PAYLOAD_LEN);
  tag(p, 14 + PAYLOAD_LEN, p + 14 + PAYLOAD_LEN);
  startTx(p, POSITION_LEN);
}

void sendPair() {
  uint8_t p[PAIR_LEN];
  p[0] = MAGIC;
  p[1] = TYPE_PAIR;
  put32(p + 2, myId);
  memcpy(p + 6, myHalf, 16);
  put32(p + 22, candidateId);
  startTx(p, PAIR_LEN);
}

void onPosition(uint8_t *p, float rssi, float snr) {
  if (!pairing.paired || get32(p + 2) != pairing.pairId) return;
  uint32_t sender = get32(p + 6), seq = get32(p + 10);
  if (sender == myId) return;
  if (pairing.partnerId != 0 && sender != pairing.partnerId) return;
  uint8_t t[4];
  tag(p, 14 + PAYLOAD_LEN, t);
  uint8_t diff = 0;
  for (int i = 0; i < 4; i++) diff |= t[i] ^ p[14 + PAYLOAD_LEN + i];
  if (diff) return;
  // Drop replays.  After a reboot of this puck any sequence is accepted once.
  if (partner.heard && seq <= lastPartnerSeq) return;
  lastPartnerSeq = seq;

  uint8_t *d = p + 14;
  crypt(p + 2, d, PAYLOAD_LEN);
  Report &r = partner.report;
  r.lat = (int32_t)get32(d) * 1e-7;
  r.lon = (int32_t)get32(d + 4) * 1e-7;
  r.fix = d[8] & FLAG_FIX;
  r.beacon = d[8] & FLAG_BEACON;
  r.lowBattery = d[8] & FLAG_LOW_BATTERY;
  r.sats = d[9];
  r.hdop = d[10] / 10.0f;
  r.batteryPct = d[11];

  bool fresh = !partner.heard || millis() - partner.lastMs > PARTNER_LOST_MS;
  partner.rssi = fresh ? rssi : partner.rssi + 0.4f * (rssi - partner.rssi);
  partner.rssiSlow = fresh ? rssi : partner.rssiSlow + 0.1f * (rssi - partner.rssiSlow);
  partner.snr = snr;
  partner.heard = true;
  partner.lastMs = millis();
}

void onPair(const uint8_t *p, float rssi) {
  if (!pairingActive || pairStatus == PAIR_DONE || rssi < PAIRING_MIN_RSSI_DBM) return;
  uint32_t sender = get32(p + 2), heard = get32(p + 22);
  if (sender == myId || sender == 0) return;
  if (candidateId == 0) {
    candidateId = sender;
    memcpy(candidateHalf, p + 6, 16);
  }
  if (sender != candidateId || memcmp(candidateHalf, p + 6, 16) != 0) return;
  if (heard == myId && pairDoneMs == 0) {
    // Both sides know each other: key from both halves, lower ID first.
    uint8_t m[40];
    bool meFirst = myId < candidateId;
    put32(m + (meFirst ? 0 : 20), myId);
    memcpy(m + (meFirst ? 4 : 24), myHalf, 16);
    put32(m + (meFirst ? 20 : 0), candidateId);
    memcpy(m + (meFirst ? 24 : 4), candidateHalf, 16);
    newPairing = derive(m, sizeof(m), candidateId);
    pairDoneMs = millis();
  }
}

void handleRx() {
  uint8_t buf[64];
  size_t len = radio.getPacketLength();
  int state = radio.readData(buf, min(len, sizeof(buf)));
  float rssi = radio.getRSSI(), snr = radio.getSNR();
  radio.startReceive();
  if (state != RADIOLIB_ERR_NONE || len < 2 || buf[0] != MAGIC) return;
  if (buf[1] == TYPE_POSITION && len == POSITION_LEN) onPosition(buf, rssi, snr);
  if (buf[1] == TYPE_PAIR && len == PAIR_LEN) onPair(buf, rssi);
}

}  // namespace

bool linkBegin(uint32_t id, uint32_t bootCount) {
  myId = id;
  seqHigh = bootCount << 20;
  loraSpi.begin(PIN_LORA_SCK, PIN_LORA_MISO, PIN_LORA_MOSI, PIN_LORA_NSS);
  int state = radio.begin(LORA_FREQ_MHZ, LORA_BW_KHZ, LORA_SF, LORA_CR, LORA_SYNC_WORD, LORA_POWER_DBM, 8, 0);
  if (state != RADIOLIB_ERR_NONE) {
    Serial.printf("LoRa init failed: %d\n", state);
    return false;
  }
  radio.setCRC(true);
  radio.setPacketReceivedAction(onDio0);   // DIO0 = "RX done" while receiving, "TX done" while sending
  radio.startReceive();
  radioOk = true;
  nextSendMs = millis() + random(SEND_INTERVAL_MS);
  return true;
}

void linkSetPairing(const Pairing &p) {
  pairing = p;
  partner = PartnerState();
  lastPartnerSeq = 0;
}

const Pairing &linkPairing() { return pairing; }
const PartnerState &linkPartner() { return partner; }

void linkLoop(const Report &mine) {
  if (!radioOk) return;
  uint32_t now = millis();

  if (dio0Fired) {
    dio0Fired = false;
    if (transmitting) {
      radio.finishTransmit();
      transmitting = false;
      radio.startReceive();
    } else {
      handleRx();
    }
  }
  if (transmitting && now - txStartMs > 2000) {   // missed TX-done interrupt
    transmitting = false;
    radio.startReceive();
  }

  if (pairingActive) {
    if (pairDoneMs && now - pairDoneMs > PAIR_LINGER_MS) {
      pairingActive = false;
      pairStatus = PAIR_DONE;
      linkSetPairing(newPairing);
      return;
    }
    if (!pairDoneMs && now - pairStartMs > PAIRING_TIMEOUT_MS) {
      pairingActive = false;
      pairStatus = PAIR_TIMEOUT;
      return;
    }
  }

  if (transmitting || (int32_t)(now - nextSendMs) < 0) return;
  if (pairingActive) {
    sendPair();
    nextSendMs = now + PAIR_SEND_MS + random(-200, 200);
  } else if (pairing.paired) {
    sendPosition(mine);
    nextSendMs = now + SEND_INTERVAL_MS + random(-SEND_JITTER_MS, SEND_JITTER_MS);
  }
}

void linkStartPairing() {
  linkRandom(myHalf, sizeof(myHalf));
  candidateId = 0;
  pairDoneMs = 0;
  pairStartMs = millis();
  pairingActive = true;
  pairStatus = PAIR_SEARCHING;
  nextSendMs = millis();
}

void linkStopPairing() {
  pairingActive = false;
  pairStatus = PAIR_IDLE;
}

PairResult linkPairingStatus() {
  PairResult r = pairStatus;
  if (r == PAIR_DONE || r == PAIR_TIMEOUT) pairStatus = PAIR_IDLE;
  return r;
}

Pairing linkPairingFromSecret(const char *secret) {
  return derive((const uint8_t *)secret, strlen(secret), 0);
}

void linkRandom(uint8_t *out, int len) {
  for (int i = 0; i < len; i++) {
    uint8_t b = (uint8_t)esp_random();
    if (radioOk && !transmitting) b ^= radio.randomByte();
    out[i] = b;
  }
  if (radioOk && !transmitting) radio.startReceive();
}
