#!/usr/bin/env python3
"""
Generate the "finder puck" as a KiCad 7 project.

Two pucks find each other at a festival without phones: each one has GPS, a
compass, and a LoRa radio, swaps positions with its partner, and shows an
arrow plus the distance on a 1.3" OLED.  Four bright LEDs strobe as a beacon
for the last few metres and a vibration motor gives a pulse you can feel.

The board is meant for factory assembly (JLCPCB/PCBWay).  Run with KiCad's
bundled Python, which provides the pcbnew module:

    /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
        tools/generate_puck.py

Shared helpers (footprint writer, stock symbol extraction, netlist parsing)
come from tools/kicad_helpers.py, vendored from the Digital Sand carrier board generator.
"""

import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import kicad_helpers as gk  # noqa: E402

NAME = "finder_puck"
SCH_FILE = os.path.join(PROJ, NAME + ".kicad_sch")
PCB_FILE = os.path.join(PROJ, NAME + ".kicad_pcb")
PRO_FILE = os.path.join(PROJ, NAME + ".kicad_pro")
LIB_DIR = os.path.join(PROJ, "lib")
SYM_LIB = os.path.join(LIB_DIR, "finder_puck.kicad_sym")
FP_LIB = os.path.join(LIB_DIR, "finder_puck.pretty")
LIB = "FinderPuck"

TITLE = "Finder Puck"
DATE = "2026-10-19"
REV = "0.1"

f, q = gk.f, gk.q


def uid(key):
    return gk.uid("puck:" + key)


# ---------------------------------------------------------------------------
# Parts and connections.  Every pin listed gets that net; every pin left out
# gets a no-connect flag.  Net names are what the schematic labels say.
# ---------------------------------------------------------------------------

R0402 = "Resistor_SMD:R_0402_1005Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"

GND = "GND"
V3 = "+3V3"

ESP32_PINS = [  # ESP32-S3-WROOM-1 pad, name, ERC type
    (1, "GND", "power_in"), (2, "3V3", "power_in"), (3, "EN", "input"),
    (4, "IO4", "bidirectional"), (5, "IO5", "bidirectional"), (6, "IO6", "bidirectional"),
    (7, "IO7", "bidirectional"), (8, "IO15", "bidirectional"), (9, "IO16", "bidirectional"),
    (10, "IO17", "bidirectional"), (11, "IO18", "bidirectional"), (12, "IO8", "bidirectional"),
    (13, "IO19/USB_D-", "bidirectional"), (14, "IO20/USB_D+", "bidirectional"),
    (15, "IO3", "bidirectional"), (16, "IO46", "bidirectional"), (17, "IO9", "bidirectional"),
    (18, "IO10", "bidirectional"), (19, "IO11", "bidirectional"), (20, "IO12", "bidirectional"),
    (21, "IO13", "bidirectional"), (22, "IO14", "bidirectional"), (23, "IO21", "bidirectional"),
    (24, "IO47", "bidirectional"), (25, "IO48", "bidirectional"), (26, "IO45", "bidirectional"),
    (27, "IO0", "bidirectional"), (28, "IO35", "bidirectional"), (29, "IO36", "bidirectional"),
    (30, "IO37", "bidirectional"), (31, "IO38", "bidirectional"), (32, "IO39", "bidirectional"),
    (33, "IO40", "bidirectional"), (34, "IO41", "bidirectional"), (35, "IO42", "bidirectional"),
    (36, "RXD0", "bidirectional"), (37, "TXD0", "bidirectional"), (38, "IO2", "bidirectional"),
    (39, "IO1", "bidirectional"), (40, "GND", "power_in"), (41, "GND", "power_in"),
]

PARTS = [
    # ref, lib_id, value, footprint, {pin: net}
    ("U1", LIB + ":ESP32-S3-WROOM-1", "ESP32-S3-WROOM-1-N8", "RF_Module:ESP32-S3-WROOM-1", {
        1: GND, 40: GND, 41: GND, 2: V3, 3: "EN",
        4: "LORA_DIO0", 5: "LORA_DIO1", 10: "GPS_RX", 11: "GPS_TX", 12: "SDA", 17: "SCL",
        13: "USB_DN", 14: "USB_DP", 18: "LORA_NSS", 19: "LORA_MOSI", 20: "LORA_SCK",
        21: "LORA_MISO", 22: "LORA_RST", 27: "BTN", 31: "ESP_LED", 7: "MOTOR",   # IO39 has a reset pull-up (MTCK): no loads
        38: "IMU_INT", 39: "BAT_SENSE",
        # Round LCD on its own SPI host (SPI3 through the GPIO matrix).
        23: "LCD_DC", 24: "LCD_RST", 25: "LCD_BL", 33: "ESP_LCD_SCK", 34: "ESP_LCD_MOSI", 35: "LCD_CS",
        6: "CHG_SENSE", 8: "VBUS_SENSE", 36: "U0RXD", 37: "U0TXD"}),
    ("U2", "RF_Module:RFM95W-915S2", "RFM95W-915S2", "RF_Module:HOPERF_RFM9XW_SMD", {
        1: GND, 8: GND, 10: GND, 2: "LORA_MISO", 3: "LORA_MOSI", 4: "LORA_SCK",
        5: "LORA_NSS", 6: "LORA_RST", 9: "LORA_ANT", 13: V3, 14: "LORA_DIO0", 15: "LORA_DIO1"}),
    ("U3", "RF_GPS:SAM-M8Q", "SAM-M10Q", "RF_GPS:ublox_SAM-M8Q", {
        1: GND, 4: GND, 5: GND, 6: GND, 10: GND, 11: GND, 15: GND, 16: GND, 20: GND,
        2: V3, 3: V3, 17: V3, 13: "GPS_TX", 14: "GPS_RX"}),
    ("U4", "Sensor_Motion:LIS3DH", "LIS3DH", "Package_LGA:LGA-16_3x3mm_P0.5mm_LayoutBorder3x5y", {
        1: V3, 14: V3, 8: V3, 5: GND, 10: GND, 12: GND, 7: GND,
        4: "SCL", 6: "SDA", 11: "IMU_INT"}),
    ("U5", "Sensor_Magnetic:LIS2MDL", "LIS2MDL", "Package_LGA:LGA-12_2x2mm_P0.5mm", {
        9: V3, 10: V3, 3: V3, 6: GND, 8: GND, 1: "SCL", 4: "SDA", 5: "MAG_C1"}),
    ("U6", "Battery_Management:MCP73831-2-OT", "MCP73831-2-OT", "Package_TO_SOT_SMD:SOT-23-5", {
        1: "CHG_STAT", 2: GND, 3: "VBAT", 4: "VBUS", 5: "CHG_PROG"}),
    ("U7", "Regulator_Linear:AP2112K-3.3", "AP2112K-3.3", "Package_TO_SOT_SMD:SOT-23-5", {
        1: "VSYS", 3: "VSYS", 2: GND, 5: V3}),
    ("Q1", "Transistor_FET:AO3400A", "AO3400A", "Package_TO_SOT_SMD:SOT-23", {
        1: "MOTOR_G", 2: GND, 3: "MOTOR_N"}),
    ("D1", "Device:D", "1N4148W", "Diode_SMD:D_SOD-123", {1: "VSYS", 2: "MOTOR_N"}),
    ("D2", "Device:LED", "Red charge", "LED_SMD:LED_0603_1608Metric", {1: "CHG_STAT", 2: "CHG_LED"}),
    ("LED1", LIB + ":WS2812B-2020", "WS2812B-2020", "LED_SMD:LED_WS2812B-2020_PLCC4_2.0x2.0mm", {
        3: "LED_DIN", 1: "LED_D1", 4: "VSYS", 2: GND}),
    ("LED2", LIB + ":WS2812B-2020", "WS2812B-2020", "LED_SMD:LED_WS2812B-2020_PLCC4_2.0x2.0mm", {
        3: "LED_D1", 1: "LED_D2", 4: "VSYS", 2: GND}),
    ("LED3", LIB + ":WS2812B-2020", "WS2812B-2020", "LED_SMD:LED_WS2812B-2020_PLCC4_2.0x2.0mm", {
        3: "LED_D2", 1: "LED_D3", 4: "VSYS", 2: GND}),
    ("LED4", LIB + ":WS2812B-2020", "WS2812B-2020", "LED_SMD:LED_WS2812B-2020_PLCC4_2.0x2.0mm", {
        3: "LED_D3", 4: "VSYS", 2: GND}),
    ("J1", "Connector:USB_C_Receptacle_USB2.0", "USB-C", "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12", {
        "A4": "VBUS", "A9": "VBUS", "B4": "VBUS", "B9": "VBUS",
        "A1": GND, "A12": GND, "B1": GND, "B12": GND, "S1": GND,
        "A5": "CC1", "B5": "CC2", "A6": "USB_DP", "B6": "USB_DP", "A7": "USB_DN", "B7": "USB_DN"}),
    ("J2", "Connector_Generic:Conn_01x02", "LiPo 1S", "Connector_JST:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal", {
        1: "VBAT", 2: GND}),
    # 1.28" 240x240 GC9A01 round IPS panel (QDtech TFT1281 / ZJY128R-IG01 class); its 12-pin
    # 0.7 mm FPC folds under the glass and is soldered to these pads by hand.
    ("J3", "Connector_Generic:Conn_01x12", "GC9A01 1.28in round LCD", LIB + ":LCD_FPC_12P_P0.70mm_Solder", {
        1: GND, 2: "BL_K", 3: "BL_A", 4: V3, 5: GND, 6: GND, 7: "LCD_DC", 8: "LCD_CS",
        9: "LCD_SCK", 10: "LCD_MOSI", 11: "LCD_RST", 12: GND}),
    ("J4", "Connector:Conn_Coaxial", "U.FL 915MHz", "Connector_Coaxial:U.FL_Hirose_U.FL-R-SMT-1_Vertical", {
        1: "LORA_ANT", 2: GND}),
    ("J5", "Connector_Generic:Conn_01x02", "Vibration motor", "Connector_JST:JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal", {
        1: "VSYS", 2: "MOTOR_N"}),
    ("SW1", "Switch:SW_Push", "Button (top, 5 mm stem)", "Button_Switch_SMD:SW_SPST_PTS645", {1: "BTN", 2: GND}),
    # The slide switch only pulls Q3's gate down (PCM12 contacts are rated 0.3 A); Q3 carries the load.
    ("SW2", "Switch:SW_SPDT", "Power", "Button_Switch_SMD:SW_SPDT_PCM12", {1: GND, 2: "PWR_G"}),
    ("Q3", "Transistor_FET:AO3401A", "AO3401A", "Package_TO_SOT_SMD:SOT-23", {
        1: "PWR_G", 2: "VBAT", 3: "VSYS"}),
    ("R1", "Device:R", "10k", R0402, {1: V3, 2: "EN"}),
    ("R2", "Device:R", "10k", R0402, {1: V3, 2: "BTN"}),
    ("R3", "Device:R", "4.7k", R0402, {1: V3, 2: "SDA"}),
    ("R4", "Device:R", "4.7k", R0402, {1: V3, 2: "SCL"}),
    ("R5", "Device:R", "5.1k", R0402, {1: "CC1", 2: GND}),
    ("R6", "Device:R", "5.1k", R0402, {1: "CC2", 2: GND}),
    ("R7", "Device:R", "3.3k", R0402, {1: "CHG_PROG", 2: GND}),       # ~300 mA: keeps the SOT-23-5 out of thermal fold-back
    ("R8", "Device:R", "1k", R0402, {1: "VBUS", 2: "CHG_LED"}),
    ("R9", "Device:R", "100k", R0402, {1: "VSYS", 2: "BAT_SENSE"}),
    ("R10", "Device:R", "100k", R0402, {1: "BAT_SENSE", 2: GND}),
    ("R11", "Device:R", "100", R0402, {1: "MOTOR", 2: "MOTOR_G"}),
    ("R12", "Device:R", "100k", R0402, {1: "MOTOR_G", 2: GND}),
    # Backlight: two parallel white LEDs (Vf ~3.0 V) fed from the battery rail through R13,
    # switched low-side by Q2 with PWM on LCD_BL.  Fed from VSYS, not +3V3, so the PWM
    # ripple stays off the rail that feeds the radio and GPS.
    ("Q2", "Transistor_FET:AO3400A", "AO3400A", "Package_TO_SOT_SMD:SOT-23", {
        1: "BL_G", 2: GND, 3: "BL_K"}),
    ("R13", "Device:R", "27", "Resistor_SMD:R_0805_2012Metric", {1: "VSYS", 2: "BL_A"}),
    ("R14", "Device:R", "1k", R0402, {1: "LCD_BL", 2: "BL_G"}),
    ("R15", "Device:R", "100k", R0402, {1: "BL_G", 2: GND}),
    ("R16", "Device:R", "10k", R0402, {1: V3, 2: "LCD_CS"}),
    ("R17", "Device:R", "10k", R0402, {1: V3, 2: "LCD_RST"}),
    ("R18", "Device:R", "33", R0402, {1: "ESP_LCD_SCK", 2: "LCD_SCK"}),
    ("R19", "Device:R", "33", R0402, {1: "ESP_LCD_MOSI", 2: "LCD_MOSI"}),
    ("R20", "Device:R", "100k", R0402, {1: "CHG_STAT", 2: "CHG_SENSE"}),
    ("R21", "Device:R", "150k", R0402, {1: "CHG_SENSE", 2: GND}),      # STAT sits at VBUS when full: divide it to 3 V
    ("R22", "Device:R", "100k", R0402, {1: "VBAT", 2: "PWR_G"}),       # Q3 off until the switch grounds its gate
    ("R23", "Device:R", "10k", R0402, {1: V3, 2: "LORA_NSS"}),         # radio deselected while the ESP32 boots
    ("R24", "Device:R", "220", R0402, {1: "ESP_LED", 2: "LED_DIN"}),
    ("R25", "Device:R", "100k", R0402, {1: "VBUS", 2: "VBUS_SENSE"}),  # USB present: 3 V at 5 V in
    ("R26", "Device:R", "150k", R0402, {1: "VBUS_SENSE", 2: GND}),
    ("C1", "Device:C", "1uF 10V X5R", C0402, {1: "EN", 2: GND}),
    ("C2", "Device:C", "10uF 10V X5R", C0805, {1: V3, 2: GND}),
    ("C3", "Device:C", "100nF 16V X7R", C0402, {1: V3, 2: GND}),
    ("C4", "Device:C", "4.7uF 10V X5R", C0603, {1: "VBUS", 2: GND}),
    ("C5", "Device:C", "4.7uF 10V X5R", C0603, {1: "VBAT", 2: GND}),
    ("C6", "Device:C", "4.7uF 10V X5R", C0603, {1: "VSYS", 2: GND}),
    ("C7", "Device:C", "10uF 10V X5R", C0805, {1: V3, 2: GND}),
    ("C8", "Device:C", "100nF 16V X7R", C0402, {1: V3, 2: GND}),
    ("C9", "Device:C", "10uF 10V X5R", C0805, {1: V3, 2: GND}),
    ("C10", "Device:C", "100nF 16V X7R", C0402, {1: V3, 2: GND}),
    ("C11", "Device:C", "100nF 16V X7R", C0402, {1: V3, 2: GND}),
    ("C12", "Device:C", "100nF 16V X7R", C0402, {1: V3, 2: GND}),
    ("C13", "Device:C", "220nF 16V X7R", C0402, {1: "MAG_C1", 2: GND}),       # LIS2MDL asks for 220 nF on C1
    ("C14", "Device:C", "100nF 16V X7R", C0402, {1: "BAT_SENSE", 2: GND}),
    ("C15", "Device:C", "10uF 10V X5R", C0805, {1: "VSYS", 2: GND}),
    ("C16", "Device:C", "100nF 16V X7R", C0402, {1: "VSYS", 2: GND}),
    ("C17", "Device:C", "1uF 10V X5R", C0603, {1: V3, 2: GND}),
    ("C18", "Device:C", "100nF 16V X7R", C0402, {1: V3, 2: GND}),
    # One decoupling capacitor beside each WS2812B.
    ("C19", "Device:C", "100nF 16V X7R", C0402, {1: "VSYS", 2: GND}),
    ("C20", "Device:C", "100nF 16V X7R", C0402, {1: "VSYS", 2: GND}),
    ("C21", "Device:C", "100nF 16V X7R", C0402, {1: "VSYS", 2: GND}),
    ("C22", "Device:C", "100nF 16V X7R", C0402, {1: "VSYS", 2: GND}),
    # UART0 test pads (boot log) and the four through-PCB mounting holes (pads tied to ground).
    ("TP1", "Connector:TestPoint", "U0TXD", "TestPoint:TestPoint_Pad_D1.0mm", {1: "U0TXD"}),
    ("TP2", "Connector:TestPoint", "U0RXD", "TestPoint:TestPoint_Pad_D1.0mm", {1: "U0RXD"}),
    ("H1", "Mechanical:MountingHole_Pad", "M2.5", "MountingHole:MountingHole_2.7mm_M2.5_Pad", {1: GND}),
    ("H2", "Mechanical:MountingHole_Pad", "M2.5", "MountingHole:MountingHole_2.7mm_M2.5_Pad", {1: GND}),
    ("H3", "Mechanical:MountingHole_Pad", "M2.5", "MountingHole:MountingHole_2.7mm_M2.5_Pad", {1: GND}),
    ("H4", "Mechanical:MountingHole_Pad", "M2.5", "MountingHole:MountingHole_2.7mm_M2.5_Pad", {1: GND}),
    # The coin motor's lead comes up from the shell floor through this hole, next to J5.
    ("H5", "Mechanical:MountingHole", "Motor lead", LIB + ":Hole_2.5mm_NPTH", {}),
]

# Parts that exist on the board but are not placed by the assembler.
NOT_ASSEMBLED = ("J3", "TP1", "TP2", "H1", "H2", "H3", "H4", "H5")

POWER_NETS = {GND: "power:GND", V3: "power:+3V3", "VBUS": "power:VBUS",
              "VBAT": LIB + ":VBAT", "VSYS": LIB + ":VSYS"}
FLAGGED = ["VBUS", "VSYS", GND]   # VBAT is driven by the charger, +3V3 by the regulator


# ---------------------------------------------------------------------------
# Symbol library
# ---------------------------------------------------------------------------

def esp32_symbol():
    n = "ESP32-S3-WROOM-1"
    left, right = ESP32_PINS[:20], ESP32_PINS[20:]
    top = 2.54 * 11
    s = "  (symbol %s (pin_names (offset 1.016)) (in_bom yes) (on_board yes)\n" % q(n)
    s += gk.lib_prop("Reference", "U", 0, top + 1.27)
    s += gk.lib_prop("Value", n, 0, -top - 1.27)
    s += gk.lib_prop("Footprint", "RF_Module:ESP32-S3-WROOM-1", 0, -top - 3.81, hide=True)
    s += gk.lib_prop("Datasheet",
                     "https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf",
                     0, 0, hide=True)
    s += gk.lib_prop("ki_keywords", "ESP32-S3 WiFi BLE module", 0, 0, hide=True)
    s += gk.lib_prop("ki_description", "ESP32-S3 module with PCB antenna, pins in pad order", 0, 0, hide=True)
    s += ('    (symbol "%s_0_1"\n      (rectangle (start -12.7 %s) (end 12.7 %s)\n'
          "        (stroke (width 0.254) (type default))\n        (fill (type background))\n      )\n    )\n"
          % (n, f(top), f(-top)))
    s += '    (symbol "%s_1_1"\n' % n
    for i, (num, name, ptype) in enumerate(left):
        s += gk.lib_pin(ptype, -15.24, top - 2.54 - i * 2.54, 0, name, num)
    for i, (num, name, ptype) in enumerate(right):
        s += gk.lib_pin(ptype, 15.24, top - 2.54 - i * 2.54, 180, name, num)
    s += "    )\n  )\n"
    return s


def ws2812_symbol():
    n = "WS2812B-2020"
    s = "  (symbol %s (pin_names (offset 0.254)) (in_bom yes) (on_board yes)\n" % q(n)
    s += gk.lib_prop("Reference", "LED", 6.35, 6.35, justify="left")
    s += gk.lib_prop("Value", n, 6.35, -6.35, justify="left")
    s += gk.lib_prop("Footprint", "LED_SMD:LED_WS2812B-2020_PLCC4_2.0x2.0mm", 0, -8.89, hide=True)
    s += gk.lib_prop("Datasheet", "https://cdn-shop.adafruit.com/product-files/4684/4684_WS2812B-2020_V1.3_EN.pdf",
                     0, 0, hide=True)
    s += gk.lib_prop("ki_description", "RGB LED with integrated controller, 2.0 x 2.0 mm", 0, 0, hide=True)
    s += ('    (symbol "%s_0_1"\n      (rectangle (start -5.08 5.08) (end 5.08 -5.08)\n'
          "        (stroke (width 0.254) (type default))\n        (fill (type background))\n      )\n    )\n" % n)
    s += '    (symbol "%s_1_1"\n' % n
    s += gk.lib_pin("input", -7.62, 0, 0, "DIN", 3)
    s += gk.lib_pin("output", 7.62, 0, 180, "DOUT", 1)
    s += gk.lib_pin("power_in", 0, 7.62, 270, "VDD", 4)
    s += gk.lib_pin("power_in", 0, -7.62, 90, "GND", 2)
    s += "    )\n  )\n"
    return s


def power_symbol(name):
    return gk.stock_block("power", "+BATT").replace("+BATT", name)


def flatten(lib, name):
    """Stock symbol text, with a derived ('extends') symbol merged into its parent."""
    text = open(os.path.join(gk.STOCK_SYM, lib + ".kicad_sym")).read()
    block = gk.stock_block(lib, name)
    m = re.search(r'\(extends "([^"]+)"\)', block)
    if not m:
        return block
    base = gk.stock_block(lib, m.group(1))
    base = base.replace('(symbol "%s"' % m.group(1), '(symbol "%s"' % name)
    base = base.replace('(symbol "%s_' % m.group(1), '(symbol "%s_' % name)
    for key in ("Value", "Footprint", "Datasheet", "ki_description", "ki_keywords", "ki_fp_filters"):
        dm = re.search(r'\(property "%s" "((?:[^"\\]|\\.)*)"' % key, block)
        if dm:
            base = re.sub(r'(\(property "%s" )"(?:[^"\\]|\\.)*"' % key,
                          lambda mm: mm.group(1) + '"' + dm.group(1).replace("\\", "\\\\") + '"', base, count=1)
    return base


# 1.28" GC9A01 panel FPC, from the QDtech TFT1281 / DisplayModule DM-TFTR128-446 drawing:
# 12 fingers at 0.7 mm pitch (7.7 mm span), 0.35 mm wide, 2.0 mm long, two dia 1.0 mm
# locating holes 10.0 mm apart, tail 12.24 mm from the glass edge, folded under the glass.
FPC_PITCH, FPC_PINS = 0.70, 12
FPC_PAD = (0.40, 2.60)            # a little longer than the 2.0 mm fingers for drag soldering
FPC_HOLE_X, FPC_HOLE_Y, FPC_HOLE_D = 5.0, 3.0, 1.1   # panel drawing: holes ~3 mm behind the finger centreline
FPC_PIN1_RIGHT = True             # pin 1 on +X when the tail enters from +Y and folds toward -Y


def lcd_fpc_footprint():
    """Solder pads for the folded panel FPC.  Rotation 0: tail arrives from +Y, tab points to -Y."""
    gk.FP_LIB = FP_LIB
    fp = gk.Footprint(
        "LCD_FPC_12P_P0.70mm_Solder",
        "Hand-solder pads for a 12-pin 0.7 mm pitch LCD FPC (1.28in GC9A01 round panel, "
        "QDtech TFT1281 / ZJY128R-IG01). Pin 1 on +X; two dia 1.0 mm FPC locating holes.",
        "FPC 0.7mm 12 pin solder GC9A01 1.28 round LCD")
    span = FPC_PITCH * (FPC_PINS - 1)
    for i in range(1, FPC_PINS + 1):
        x = span / 2 - FPC_PITCH * (i - 1)
        if not FPC_PIN1_RIGHT:
            x = -x
        fp.body.append('  (pad %s smd rect (at %s 0) (size %s %s) (layers "F.Cu" "F.Mask") (tstamp %s))\n' % (
            q(str(i)), f(x), f(FPC_PAD[0]), f(FPC_PAD[1]), uid("fpcpad%d" % i)))
    for x in (-FPC_HOLE_X, FPC_HOLE_X):
        fp.body.append('  (pad "" np_thru_hole circle (at %s %s) (size %s %s) (drill %s) (layers "*.Cu" "*.Mask") (tstamp %s))\n' % (
            f(x), f(FPC_HOLE_Y), f(FPC_HOLE_D), f(FPC_HOLE_D), f(FPC_HOLE_D), uid("fpchole%s" % x)))
    # Folded tab (11.4 mm wide contact end) and where the fold meets the glass edge.
    fp.rect(-5.7, -1.4, 5.7, 3.6, "F.Fab", 0.1)
    fp.line(-5.12, 4.2, 5.12, 4.2, "F.Fab", 0.1)
    fp.text("user", "FPC FOLD / GLASS EDGE", 0, 5.0, "F.Fab", size=0.7, thick=0.1)
    fp.rect(-6.0, -1.9, 6.0, 2.8, "F.CrtYd", 0.05)
    p1 = span / 2 if FPC_PIN1_RIGHT else -span / 2
    fp.text("user", "1", p1 + 1.3, 1.9, "F.SilkS", size=0.8, thick=0.15)      # between the pad ends and the holes
    fp.text("user", "12", -p1 - 1.5, 1.9, "F.SilkS", size=0.8, thick=0.15)
    fp.text("reference", "REF**", 0, -3.4, "F.SilkS", size=0.8, thick=0.15)
    fp.text("value", "LCD_FPC_12P_P0.70mm_Solder", 0, 6.2, "F.Fab", size=0.7, thick=0.1)
    fp.write()
    path = os.path.join(FP_LIB, "LCD_FPC_12P_P0.70mm_Solder.kicad_mod")
    text = open(path).read().replace("(attr through_hole)", "(attr smd exclude_from_pos_files exclude_from_bom)")
    open(path, "w").write(text)


def hole_footprint():
    """A plain 2.5 mm hole for a wire or coax with a courtyard that only covers the hole itself
    (KiCad's MountingHole footprints reserve room for a screw head)."""
    gk.FP_LIB = FP_LIB
    fp = gk.Footprint("Hole_2.5mm_NPTH", "2.5 mm unplated hole for a lead or pigtail", "hole npth 2.5mm")
    fp.body.append('  (pad "" np_thru_hole circle (at 0 0) (size 2.5 2.5) (drill 2.5) (layers "*.Cu" "*.Mask") (tstamp %s))\n' % uid("hole25"))
    fp.rect(-1.65, -1.65, 1.65, 1.65, "F.CrtYd", 0.05)
    fp.text("reference", "REF**", 0, -2.6, "F.Fab", size=0.7, thick=0.1)
    fp.text("value", "Hole_2.5mm_NPTH", 0, 2.6, "F.Fab", size=0.7, thick=0.1)
    fp.write()
    path = os.path.join(FP_LIB, "Hole_2.5mm_NPTH.kicad_mod")
    text = open(path).read().replace("(attr through_hole)", "(attr exclude_from_pos_files exclude_from_bom)")
    open(path, "w").write(text)


def write_libraries():
    os.makedirs(FP_LIB, exist_ok=True)
    lcd_fpc_footprint()
    hole_footprint()
    custom = {
        LIB + ":ESP32-S3-WROOM-1": esp32_symbol(),
        LIB + ":WS2812B-2020": ws2812_symbol(),
        LIB + ":VBAT": power_symbol("VBAT"),
        LIB + ":VSYS": power_symbol("VSYS"),
    }
    with open(SYM_LIB, "w") as fh:
        fh.write("(kicad_symbol_lib (version 20220914) (generator kicad_symbol_editor)\n")
        for text in custom.values():
            fh.write(text)
        fh.write(")\n")
    with open(os.path.join(PROJ, "sym-lib-table"), "w") as fh:
        fh.write('(sym_lib_table\n  (lib (name "%s")(type "KiCad")(uri "${KIPRJMOD}/lib/finder_puck.kicad_sym")'
                 '(options "")(descr "Finder puck symbols"))\n)\n' % LIB)
    with open(os.path.join(PROJ, "fp-lib-table"), "w") as fh:
        fh.write('(fp_lib_table\n  (lib (name "%s")(type "KiCad")(uri "${KIPRJMOD}/lib/finder_puck.pretty")'
                 '(options "")(descr "Finder puck footprints"))\n)\n' % LIB)
    libs = dict(custom)
    for _, lib_id, _, _, _ in PARTS:
        if lib_id not in libs:
            lib, name = lib_id.split(":")
            libs[lib_id] = flatten(lib, name)
    for lib_id in ("power:GND", "power:+3V3", "power:VBUS", "power:PWR_FLAG"):
        lib, name = lib_id.split(":")
        libs[lib_id] = gk.stock_block(lib, name)
    return libs


# ---------------------------------------------------------------------------
# Schematic: every connected pin gets a short stub with a net label or power
# symbol, so the drawing reads by name rather than by wires.
# ---------------------------------------------------------------------------

class LabelSchematic(gk.Schematic):
    POWER_UP = ("power:+3V3", "power:VBUS", LIB + ":VBAT", LIB + ":VSYS")

    def __init__(self, libs):
        super().__init__(libs)
        self.root = uid("sch:root")
        self.lib_pin_dirs = {}
        self.lib_nc_pins = {}
        for lib_id, text in libs.items():
            dirs, nc = {}, set()
            for m in re.finditer(r'\(pin (\S+) \S+ \(at [-\d.]+ [-\d.]+ ([-\d.]+)\).*?\(number "([^"]+)"', text, re.S):
                dirs.setdefault(m.group(3), int(float(m.group(2))))
                if m.group(1) == "no_connect":
                    nc.add(m.group(3))
            self.lib_pin_dirs[lib_id] = dirs
            self.lib_nc_pins[lib_id] = nc

    def _u(self, kind):
        self.n += 1
        return uid("sch:%s:%d" % (kind, self.n))

    def label(self, name, x, y, ang=0):
        just = {0: "left bottom", 90: "left bottom", 180: "right bottom", 270: "right bottom"}[ang]
        self.items.append(
            "  (label %s (at %s %s %d)\n    (effects (font (size 1.27 1.27)) (justify %s))\n    (uuid %s)\n  )\n"
            % (q(name), f(x), f(y), ang, just, self._u("label")))

    def power_at(self, net, x, y, d):
        """Power symbol at (x, y) with its graphic pointing along d (schematic direction)."""
        lib_id = POWER_NETS[net]
        up = net != GND
        rot = {(0, -1): 0, (-1, 0): 90, (0, 1): 180, (1, 0): 270}[d] if up else \
            {(0, 1): 0, (1, 0): 90, (0, -1): 180, (-1, 0): 270}[d]
        self.power(lib_id, x, y, rot)

    def pin_out(self, placed, lib_id, num):
        """Pin end point and outward direction in schematic coordinates."""
        x, y = placed.pin(num)
        ang = self.lib_pin_dirs[lib_id][num]
        # A pin at angle a points from its end towards the body; outward is the opposite.
        ox, oy = {0: (-1, 0), 90: (0, -1), 180: (1, 0), 270: (0, 1)}[ang]
        dx, dy = gk.sch_xform(ox, oy, placed.ang)
        return x, y, (int(round(dx)), int(round(dy)))

    def connect_all(self, placed, lib_id, nets):
        groups = {}   # (point) -> stacked pins share one stub
        flagged = set()
        for num in self.lib_pins[lib_id]:
            key = int(num) if num.isdigit() else num
            x, y, d = self.pin_out(placed, lib_id, num)
            if key not in nets:
                # Stacked pins take a single flag; pins already typed no-connect need none.
                if (x, y) not in flagged and num not in self.lib_nc_pins[lib_id]:
                    self.noconn(x, y)
                    flagged.add((x, y))
                continue
            groups.setdefault((x, y, d), nets[key])
        # Neighbouring pins on the same side with the same power net share one symbol.
        power = {}
        for (x, y, d), net in groups.items():
            if net in POWER_NETS:
                power.setdefault((net, d, y if d[0] == 0 else x), []).append((x, y))
            else:
                ex, ey = x + d[0] * 2.54, y + d[1] * 2.54
                self.wire((x, y), (ex, ey))
                self.label(net, ex, ey, {(1, 0): 0, (-1, 0): 180, (0, -1): 90, (0, 1): 270}[d])
        for (net, d, _), pts in power.items():
            along = 0 if d[0] == 0 else 1      # coordinate that varies along the side
            pts.sort(key=lambda p: p[along])
            ends = []
            for x, y in pts:
                ex, ey = x + d[0] * 2.54, y + d[1] * 2.54
                self.wire((x, y), (ex, ey))
                ends.append((ex, ey))
            runs = [[ends[0]]]
            for e in ends[1:]:
                if abs(e[along] - runs[-1][-1][along]) <= 7.62 + 1e-6:
                    runs[-1].append(e)
                else:
                    runs.append([e])
            for run in runs:
                for a, b in zip(run, run[1:]):
                    self.wire(a, b)
                for e in run[1:-1]:
                    self.junction(*e)
                self.power_at(net, run[0][0], run[0][1], d)

    def junction(self, x, y):
        self.items.append("  (junction (at %s %s) (diameter 0) (color 0 0 0 0)\n    (uuid %s)\n  )\n"
                          % (f(x), f(y), self._u("junction")))

    def write(self, paper="A2"):
        with open(SCH_FILE, "w") as fh:
            fh.write("(kicad_sch (version 20230121) (generator eeschema)\n\n")
            fh.write("  (uuid %s)\n\n" % self.root)
            fh.write('  (paper "%s")\n\n' % paper)
            fh.write("  (title_block\n    (title %s)\n    (date %s)\n    (rev %s)\n"
                     "    (comment 1 %s)\n    (comment 2 %s)\n  )\n\n" % (
                         q(TITLE), q(DATE), q(REV),
                         q("Two pucks point at each other: GPS + compass + LoRa, round radar screen"),
                         q("ESP32-S3-WROOM-1, RFM95W 915 MHz, SAM-M10Q, LIS3DH + LIS2MDL, GC9A01 round LCD, 1S LiPo")))
            fh.write("  (lib_symbols\n")
            for lib_id in sorted(self.libs):
                short = lib_id.split(":")[1]
                fh.write(self.libs[lib_id].replace('(symbol "%s" ' % short, '(symbol "%s" ' % lib_id, 1))
            fh.write("  )\n\n")
            fh.writelines(self.items)
            fh.writelines(self.symbols)
            fh.write('\n  (sheet_instances\n    (path "/" (page "1"))\n  )\n)\n')


def grid(v):
    return round(v / 2.54) * 2.54


def label_room(sch, lib_id, nets, side):
    """Width needed beside the symbol for stubs, labels and sideways power symbols."""
    longest = 4
    for num in sch.lib_pins[lib_id]:
        key = int(num) if num.isdigit() else num
        if sch.lib_pin_dirs[lib_id][num] == side and key in nets:
            longest = max(longest, len(nets[key]))
    return 2.54 + 1.0 * longest + 4.0


def build_schematic(libs):
    gk.SCH_FILE, gk.NAME = SCH_FILE, NAME
    sch = LabelSchematic(libs)
    order = ["U1", "U2", "U3", "U4", "U5", "U6", "U7", "J1", "J3", "SW2", "J2", "J4",
             "LED1", "LED2", "LED3", "LED4", "Q1", "Q2", "Q3", "D1", "J5", "SW1", "D2",
             "TP1", "TP2", "H1", "H2", "H3", "H4", "H5"] + \
        ["R%d" % i for i in range(1, 27)] + ["C%d" % i for i in range(1, 23)]
    parts = {p[0]: p for p in PARTS}
    x0, x_max = 22.86, 570.0
    x, y, row_h = x0, 33.02, 0
    prev_small = None
    for ref in order:
        _, lib_id, value, footprint, nets = parts[ref]
        pins = list(sch.lib_pins[lib_id].values())
        xs, ys = [p[0] for p in pins] or [0.0], [p[1] for p in pins] or [0.0]   # H5 has no pins
        small = max(abs(v) for v in xs) < 1          # two-pin parts drawn vertically
        if prev_small is not None and small != prev_small:
            x, y, row_h = x0, y + row_h, 0           # passives start their own row
        prev_small = small
        if small:
            left, right, w, h = 0, 0, 22.86, 33.02
        else:
            left = label_room(sch, lib_id, nets, 0)      # pins pointing right sit on the left side
            right = label_room(sch, lib_id, nets, 180)
            w = left + (max(xs) - min(xs)) + right + 6
            h = (max(ys) - min(ys)) + 26
        if x + w > x_max:
            x, y, row_h = x0, y + row_h, 0
        px, py = grid(x + left - min(xs) + (7.62 if small else 0)), grid(y + (12.7 if small else 10.16) + max(ys))
        if small:
            fields = {"Reference": (2.54, -1.27, "left"), "Value": (2.54, 1.27, "left")}
        else:
            fields = {"Reference": (0, -max(ys) - 10.16, None), "Value": (0, -min(ys) + 10.16, None)}
        placed = sch.place(lib_id, ref, value, px, py, 0, footprint=footprint, fields=fields)
        sch.connect_all(placed, lib_id, nets)
        x += w
        row_h = max(row_h, h)
    y += row_h + 7.62
    complete_x = x0
    sch.text(
        "FINDER PUCK\n"
        "ESP32-S3 swaps GPS positions with its partner over LoRa (RFM95W, 915 MHz), reads heading\n"
        "from LIS2MDL + LIS3DH, and draws a radar arrow and distance on a 1.28in round GC9A01 LCD (J3).\n"
        "LCD: own SPI host, SCK IO40, MOSI IO41, CS IO42, D/C IO21, RST IO47, backlight PWM IO48 -> Q2.\n"
        "LED1-LED4 strobe as a beacon; the motor pulses faster as the partner gets closer.\n"
        "Power: 1S LiPo on J2, charged from USB-C by U6 (state on IO6, USB on IO15); SW2 turns on Q3, which feeds VSYS; U7 makes 3.3 V.\n"
        "Flash over USB-C (native USB). Hold SW1 (IO0) while plugging in to force download mode.\n"
        "J3 pin 1 is on the 3 o'clock side after the FPC folds under the glass: CONFIRM on a sample panel.",
        grid(complete_x), grid(y), size=1.27)
    # ERC: supplies that come from off-board or through the power switch.
    for i, net in enumerate(FLAGGED):
        fx, fy = grid(complete_x + 190 + i * 15.24), grid(y + 12.7)
        sch.power(POWER_NETS[net], fx, fy, 0)
        sch.power("power:PWR_FLAG", fx, fy, 180 if net != GND else 0)
    sch.write()
    return sch


def check_netlist(sch):
    netlist = os.path.join(tempfile.gettempdir(), NAME + ".net")
    gk.run([gk.KICAD_CLI, "sch", "export", "netlist", "-o", netlist, SCH_FILE])
    pads, nets, comps = gk.read_netlist(netlist)
    ok = True
    for ref, _, _, _, want in PARTS:
        for pin, net in want.items():
            got = pads.get((ref, str(pin)), (None,))[0]
            expect = net if net in POWER_NETS else "/" + net
            if got != expect:
                print("MISMATCH %s.%s: want %s got %s" % (ref, pin, expect, got))
                ok = False
    for name, members in nets.items():
        if name.startswith("unconnected-"):
            continue
        if len(members) < 2:
            print("SINGLE-PIN NET %s %s" % (name, members))
            ok = False
    if not ok:
        sys.exit("schematic does not match PARTS")
    print("netlist OK: %d nets, %d pads" % (len(nets), len(pads)))
    return pads, comps


def main():
    libs = write_libraries()
    sch = build_schematic(libs)
    pads, comps = check_netlist(sch)
    if "--sch-only" in sys.argv:
        return
    import puck_board
    puck_board.build(pads, comps, sch.uuids)


if __name__ == "__main__":
    main()
