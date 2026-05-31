# ═══════════════════════════════════════════════════════════════
#  TinyCar — Phase 1 Car Diagnostic
#  MicroPython v1.28 · ESP32 DevKit v1
#
#  Receives BLE packets from remote and prints them with
#  human-readable direction label. NO motors driven.
#  Use this to verify signal integrity before touching motors.
#
#  Pin Map:
#    GPIO2 → Status LED (on = remote connected)
# ═══════════════════════════════════════════════════════════════

import bluetooth
from machine import Pin
from micropython import const
from utime import sleep_ms

# ── STATUS LED ───────────────────────────────────────────────
STATUS = Pin(2, Pin.OUT)

# ── DIRECTION CLASSIFIER ─────────────────────────────────────
# Identical logic to remote — so both consoles should always agree
ARC_THRESHOLD = 15

def classify_direction(l, r):
    if l == 0 and r == 0:
        return "STOPPED"
    if l < 0 and r > 0:
        return "SPIN LEFT"
    if l > 0 and r < 0:
        return "SPIN RIGHT"
    if l > 0 and r > 0:
        diff = l - r
        if abs(diff) < ARC_THRESHOLD:
            return "FORWARD"
        elif diff > 0:
            return "FWD + RIGHT arc"
        else:
            return "FWD + LEFT arc"
    if l < 0 and r < 0:
        diff = abs(l) - abs(r)
        if abs(diff) < ARC_THRESHOLD:
            return "REVERSE"
        elif diff > 0:
            return "REV + LEFT arc"
        else:
            return "REV + RIGHT arc"
    return "UNKNOWN"

# ── BLE GATT SERVER ──────────────────────────────────────────
_IRQ_CENTRAL_CONNECT    = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE        = const(3)

_UART_UUID = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
_TX_UUID   = bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")

_TX_CHAR      = (_TX_UUID, bluetooth.FLAG_WRITE | bluetooth.FLAG_WRITE_NO_RESPONSE,)
_UART_SERVICE = (_UART_UUID, (_TX_CHAR,),)

ble = bluetooth.BLE()
ble.active(True)

((rx_handle,),) = ble.gatts_register_services((_UART_SERVICE,))

last_label = ""
last_l     = None
last_r     = None

def _parse(buf):
    try:
        s     = buf.decode()
        parts = s.split(",")
        l = int(parts[0].split(":")[1])
        r = int(parts[1].split(":")[1])
        return l, r
    except:
        return None, None

def _irq(event, data):
    global last_label, last_l, last_r

    if event == _IRQ_CENTRAL_CONNECT:
        STATUS.on()
        print("Remote connected!\n")

    elif event == _IRQ_CENTRAL_DISCONNECT:
        STATUS.off()
        last_label = ""
        last_l     = None
        last_r     = None
        print("Remote disconnected — re-advertising...")
        _advertise()

    elif event == _IRQ_GATTS_WRITE:
        buf = ble.gatts_read(rx_handle)
        l, r = _parse(buf)
        if l is None:
            return

        label = classify_direction(l, r)

        # Print only on change — STOPPED prints once then suppressed
        if label != last_label or l != last_l or r != last_r:
            if label == "STOPPED" and last_label == "STOPPED":
                pass
            else:
                print(f"Car    → L:{l:+04d},R:{r:+04d}  │  {label}")
            last_label = label
            last_l     = l
            last_r     = r

ble.irq(_irq)

def _advertise():
    name = b"TinyCar"
    adv  = (
        b"\x02\x01\x06"
        + bytes([1 + len(name)]) + b"\x09" + name
    )
    ble.gap_advertise(100_000, adv)

# ── STARTUP ──────────────────────────────────────────────────
def startup_blink(n=3):
    for _ in range(n):
        STATUS.on();  sleep_ms(150)
        STATUS.off(); sleep_ms(150)

print("=" * 52)
print("  TinyCar Phase 1 — Car Diagnostic")
print("  NO motors — signal verification only")
print("=" * 52)

startup_blink()
_advertise()
print("Advertising as TinyCar — waiting for remote...\n")