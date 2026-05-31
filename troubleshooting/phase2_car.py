# ═══════════════════════════════════════════════════════════════
#  TinyCar — Phase 2 Car Diagnostic
#  MicroPython v1.28 · ESP32 DevKit v1
#
#  Receives BLE packets from remote.
#  Drives motors continuously while joystick held in direction.
#  Stops when joystick returns to centre.
#
#  Pin Map (confirmed correct 31 May 2026):
#    GPIO2  → Status LED (on = remote connected)
#    GPIO5  → DRV8833 IN1 — LF (Left  Forward)  ← swapped from GPIO18
#    GPIO18 → DRV8833 IN2 — LB (Left  Backward) ← swapped from GPIO5
#    GPIO19 → DRV8833 IN3 — RF (Right Backward)
#    GPIO23 → DRV8833 IN4 — RB (Right Forward)
#
#  Kill loop removed — was breaking PWM initialisation
# ═══════════════════════════════════════════════════════════════

import bluetooth
from machine import Pin, PWM
from micropython import const
from utime import sleep_ms

# ── STATUS LED ───────────────────────────────────────────────
STATUS = Pin(2, Pin.OUT)

# ── MOTOR PINS ───────────────────────────────────────────────
LF = PWM(Pin(5),  freq=1000)   # Left  Forward  — FL CCW = forward
LB = PWM(Pin(18), freq=1000)   # Left  Backward — FL CW  = reverse
RF = PWM(Pin(23), freq=1000)   # Right Forward  — FR CW  = forward
RB = PWM(Pin(19), freq=1000)   # Right Backward — FR CCW = reverse

for p in [LF, LB, RF, RB]:
    p.duty_u16(0)

# ── PARAMETERS ───────────────────────────────────────────────
ARC_THRESHOLD = 15
MIN_DUTY      = 50

# ── MOTOR CONTROL ────────────────────────────────────────────
def threshold(speed):
    if speed == 0: return 0
    sign   = 1 if speed > 0 else -1
    mapped = MIN_DUTY + int((abs(speed) / 100) * (100 - MIN_DUTY))
    return sign * min(100, mapped)

def pct_to_duty(pct):
    return int(abs(pct) / 100 * 65535)

def all_stop():
    for p in [LF, LB, RF, RB]:
        p.duty_u16(0)

def drive(l, r):
    tl = threshold(l)
    tr = threshold(r)
    dl = pct_to_duty(tl)
    dr = pct_to_duty(tr)

    if tl > 0:   LF.duty_u16(dl); LB.duty_u16(0)
    elif tl < 0: LF.duty_u16(0);  LB.duty_u16(dl)
    else:        LF.duty_u16(0);  LB.duty_u16(0)

    if tr > 0:   RF.duty_u16(dr); RB.duty_u16(0)
    elif tr < 0: RF.duty_u16(0);  RB.duty_u16(dr)
    else:        RF.duty_u16(0);  RB.duty_u16(0)

# ── DIRECTION CLASSIFIER ─────────────────────────────────────
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

_pending_l    = 0
_pending_r    = 0
_pending_flag = False
last_label    = ""

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
    global _pending_l, _pending_r, _pending_flag

    if event == _IRQ_CENTRAL_CONNECT:
        STATUS.on()
        print("Remote connected!\n")

    elif event == _IRQ_CENTRAL_DISCONNECT:
        STATUS.off()
        all_stop()
        print("Remote disconnected — motors stopped — re-advertising...")
        _advertise()

    elif event == _IRQ_GATTS_WRITE:
        buf = ble.gatts_read(rx_handle)
        l, r = _parse(buf)
        if l is not None:
            _pending_l    = l
            _pending_r    = r
            _pending_flag = True

ble.irq(_irq)

def _advertise():
    name = b"TinyCar"
    adv  = (
        b"\x02\x01\x06"
        + bytes([1 + len(name)]) + b"\x09" + name
    )
    ble.gap_advertise(100_000, adv)

def startup_blink(n=3):
    for _ in range(n):
        STATUS.on();  sleep_ms(150)
        STATUS.off(); sleep_ms(150)

print("=" * 52)
print("  TinyCar Phase 2 — Motor Drive Test")
print("  Hold joystick to spin — release to stop")
print("  LIFT CAR FIRST")
print("=" * 52)

startup_blink()
_advertise()
print("Advertising as TinyCar — waiting for remote...\n")

# ── MAIN LOOP ────────────────────────────────────────────────
while True:
    if _pending_flag:
        _pending_flag = False
        l     = _pending_l
        r     = _pending_r
        label = classify_direction(l, r)

        if label == "STOPPED":
            all_stop()
            if last_label != "STOPPED":
                print("Car    → STOPPED")
            last_label = label
        else:
            drive(l, r)
            if label != last_label:
                print(f"Car    → L:{l:+04d},R:{r:+04d}  │  {label}")
            last_label = label

    sleep_ms(10)