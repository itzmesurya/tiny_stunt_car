# ═══════════════════════════════════════════════════════════════
#  TinyCar — Stage 4 Complete Car Firmware
#  MicroPython v1.28 · ESP32 DevKit v1
#
#  All systems integrated and calibrated:
#    ✅ TCS34725 colour sensor — 5 colours calibrated
#    ✅ 4× N20 motors via DRV8833 — all directions confirmed
#    ✅ Joystick steering — dead zone 30%, axes corrected
#    ✅ 5 colour-triggered stunts with 3s cooldown
#    ✅ 5 manual stunts via button cycle
#    ✅ PWM motor control with minimum threshold
#    ✅ Full stunt debug logging
#
#  Pin Map (confirmed correct 31 May 2026):
#    GPIO2  → Status LED (green, 330Ω to GND)
#    GPIO4  → Mode button (to GND, internal pull-up)
#    GPIO5  → DRV8833 IN1 — LF (Left  Forward)  ← swapped from GPIO18
#    GPIO18 → DRV8833 IN2 — LB (Left  Backward) ← swapped from GPIO5
#    GPIO19 → DRV8833 IN3 — RB (Right Backward)
#    GPIO23 → DRV8833 IN4 — RF (Right Forward)
#    GPIO21 → TCS34725 SDA
#    GPIO22 → TCS34725 SCL
#    GPIO34 → Joystick VRx (HORZ)
#    GPIO35 → Joystick VRy (VERT)
#
#  DRV8833 wiring:
#    VCC → VIN on ESP32
#    GND → GND rail
#    SLEEP → 3V3 rail (must be HIGH or motors won't move)
#    OUT1/OUT2 → FL + RL in parallel (white→OUT1, black→OUT2)
#    OUT3/OUT4 → FR + RR in parallel (white→OUT3, black→OUT4)
#
#  Colour → Stunt map:
#    RED    → Spinout
#    YELLOW → Reverse donut
#    GREEN  → Zigzag
#    PURPLE → Boost
#    BLUE   → Brake slide
# ═══════════════════════════════════════════════════════════════

from machine import Pin, PWM, ADC, SoftI2C
from utime import sleep_ms, ticks_ms, ticks_diff

# ── STATUS LED + BUTTON ──────────────────────────────────────
STATUS = Pin(2, Pin.OUT)
BUTTON = Pin(4, Pin.IN, Pin.PULL_UP)

# ── MOTOR DRIVER (DRV8833) ───────────────────────────────────
LF = PWM(Pin(5),  freq=1000)   # Left  Forward  — FL CCW = forward
LB = PWM(Pin(18), freq=1000)   # Left  Backward — FL CW  = reverse
RF = PWM(Pin(23), freq=1000)   # Right Forward  — FR CW  = forward
RB = PWM(Pin(19), freq=1000)   # Right Backward — FR CCW = reverse

for p in [LF, LB, RF, RB]:
    p.duty_u16(0)

MIN_DUTY = 50

def threshold(speed):
    if speed == 0: return 0
    sign   = 1 if speed > 0 else -1
    mapped = MIN_DUTY + int((abs(speed) / 100) * (100 - MIN_DUTY))
    return sign * min(100, mapped)

def set_motor(fwd, rev, speed):
    duty = int(abs(speed) / 100 * 65535)
    if speed > 0:   fwd.duty_u16(duty); rev.duty_u16(0)
    elif speed < 0: fwd.duty_u16(0);    rev.duty_u16(duty)
    else:           fwd.duty_u16(0);    rev.duty_u16(0)

def drive(l, r, log=False, label=""):
    tl = threshold(l)
    tr = threshold(r)
    set_motor(LF, LB, tl)
    set_motor(RF, RB, tr)
    if log:
        ldir = "FWD" if tl > 0 else ("BCK" if tl < 0 else "STP")
        rdir = "FWD" if tr > 0 else ("BCK" if tr < 0 else "STP")
        print(f"  {label:<22} LF/LB={ldir} {abs(tl):3d}%   RF/RB={rdir} {abs(tr):3d}%")

def stop(label="STOP"):
    drive(0, 0, log=True, label=label)

# ── JOYSTICK ─────────────────────────────────────────────────
JOY_X = ADC(Pin(34)); JOY_X.atten(ADC.ATTN_11DB)
JOY_Y = ADC(Pin(35)); JOY_Y.atten(ADC.ATTN_11DB)

DEAD_ZONE = 30

def _dz(v):
    if abs(v) < DEAD_ZONE: return 0
    s = 1 if v > 0 else -1
    return s * min(100, int((abs(v) - DEAD_ZONE) * 100 // (100 - DEAD_ZONE)))

def calibrate_joystick():
    print("Calibrating joystick — don't touch it...")
    sleep_ms(300)
    cx = cy = 0
    for _ in range(20):
        cx += JOY_X.read()
        cy += JOY_Y.read()
        sleep_ms(15)
    cx //= 20; cy //= 20
    print(f"Centre → X={cx}  Y={cy}  (ideal 2047)")
    return cx, cy

def read_joystick(cx, cy):
    rx = ry = 0
    for _ in range(5):
        rx += JOY_X.read()
        ry += JOY_Y.read()
    x = max(-100, min(100, int(((rx//5 - cx) * 100 / 2047))))
    y = max(-100, min(100, int(((ry//5 - cy) * 100 / 2047))))
    l = max(-100, min(100, _dz(y) + _dz(x)))
    r = max(-100, min(100, _dz(y) - _dz(x)))
    return l, r

# ── TCS34725 COLOUR SENSOR ───────────────────────────────────
TCS_ADDR    = 0x29
TCS_CMD     = 0x80
TCS_ENABLE  = 0x00
TCS_ATIME   = 0x01
TCS_CONTROL = 0x0F
TCS_CDATA   = 0x14

i2c = SoftI2C(sda=Pin(21), scl=Pin(22), freq=400_000)

def _tcs_write(reg, val):
    i2c.writeto_mem(TCS_ADDR, TCS_CMD | reg, bytes([val]))

def _tcs_read16(reg):
    d = i2c.readfrom_mem(TCS_ADDR, TCS_CMD | reg, 2)
    return d[0] | (d[1] << 8)

def tcs_init():
    _tcs_write(TCS_ENABLE,  0x03)
    _tcs_write(TCS_ATIME,   0xD5)
    _tcs_write(TCS_CONTROL, 0x00)
    sleep_ms(120)
    print("TCS34725 initialised")

def tcs_read():
    clear = _tcs_read16(TCS_CDATA)
    if clear == 0:
        return 0, 0, 0, 0
    r = min(255, int(_tcs_read16(TCS_CDATA + 2) * 255 / clear))
    g = min(255, int(_tcs_read16(TCS_CDATA + 4) * 255 / clear))
    b = min(255, int(_tcs_read16(TCS_CDATA + 6) * 255 / clear))
    return r, g, b, clear

# ── COLOUR CLASSIFICATION ────────────────────────────────────
def classify_color(r, g, b, clear):
    if clear < 20:                                          return None
    if max(r, g, b) < 40:                                  return None
    if r > 170 and g < 60  and b < 60 and clear > 80:     return "RED"
    if r > 120 and g > 70  and b < 50 and r > g:          return "YELLOW"
    if g > 100 and g > r   and g > b * 2:                 return "GREEN"
    if r > 100 and g > 60  and abs(g - b) < 15 \
       and r > g and r < 140 and clear > 150:              return "PURPLE"
    if r < 80  and g > 85  and b > 85 \
       and abs(g - b) < 20 and clear > 150:               return "BLUE"
    return None

# ── STUNT LIBRARY ────────────────────────────────────────────
def stunt_spinout():
    print("\n┌─ SPINOUT ──────────────────────────────")
    STATUS.on()
    for i in range(3):
        print(f"│ Cycle {i+1}/3:")
        drive(100, -100, log=True, label="  Phase A — fwd/back")
        sleep_ms(300)
        drive(-100, 100, log=True, label="  Phase B — back/fwd")
        sleep_ms(300)
    stop("  Final stop")
    STATUS.off()
    print("└────────────────────────────────────────\n")

def stunt_boost():
    print("\n┌─ BOOST ─────────────────────────────────")
    STATUS.on()
    drive(100, 100, log=True, label="  Full forward")
    sleep_ms(800)
    stop("  Final stop")
    STATUS.off()
    print("└────────────────────────────────────────\n")

def stunt_zigzag():
    print("\n┌─ ZIGZAG ────────────────────────────────")
    STATUS.on()
    for i in range(4):
        print(f"│ Arc {i+1}/4:")
        drive(100, 40, log=True, label="  Left arc")
        sleep_ms(300)
        drive(40, 100, log=True, label="  Right arc")
        sleep_ms(300)
    stop("  Final stop")
    STATUS.off()
    print("└────────────────────────────────────────\n")

def stunt_donut():
    print("\n┌─ REVERSE DONUT ─────────────────────────")
    STATUS.on()
    drive(-100, -50, log=True, label="  Tight reverse arc")
    sleep_ms(1200)
    stop("  Final stop")
    STATUS.off()
    print("└────────────────────────────────────────\n")

def stunt_brake():
    print("\n┌─ BRAKE SLIDE ───────────────────────────")
    STATUS.on()
    drive(100, 100, log=True, label="  Run up")
    sleep_ms(400)
    drive(-80, -80, log=True, label="  Hard brake")
    sleep_ms(200)
    stop("  Final stop")
    STATUS.off()
    print("└────────────────────────────────────────\n")

COLOR_STUNT = {
    "RED":    stunt_spinout,
    "YELLOW": stunt_donut,
    "GREEN":  stunt_zigzag,
    "PURPLE": stunt_boost,
    "BLUE":   stunt_brake,
}

MANUAL_STUNTS = [
    stunt_spinout,
    stunt_boost,
    stunt_zigzag,
    stunt_donut,
    stunt_brake,
]

def startup_blink(n=3):
    for _ in range(n):
        STATUS.on();  sleep_ms(150)
        STATUS.off(); sleep_ms(150)

# ── MAIN ─────────────────────────────────────────────────────
print("=" * 52)
print("  TinyCar Stage 4 — Complete Car Firmware")
print("  5 colours · 5 stunts · joystick steering")
print("=" * 52)

CX, CY = calibrate_joystick()
tcs_init()
startup_blink()

print("\nColour → Stunt map:")
print("  RED    → Spinout")
print("  YELLOW → Reverse donut")
print("  GREEN  → Zigzag")
print("  PURPLE → Boost")
print("  BLUE   → Brake slide")
print("\nButton → Manual stunt cycle")
print("Ready!\n")

stunt_idx        = 0
last_btn         = 0
last_color_chk   = 0
last_stunt_time  = -3000
COOLDOWN_MS      = 3000
last_color_print = ""

while True:
    now = ticks_ms()

    if BUTTON.value() == 0 and ticks_diff(now, last_btn) > 400:
        last_btn = now
        print(f"Button → manual stunt #{stunt_idx + 1}")
        MANUAL_STUNTS[stunt_idx]()
        stunt_idx = (stunt_idx + 1) % len(MANUAL_STUNTS)

    if ticks_diff(now, last_color_chk) > 120:
        last_color_chk = now
        r, g, b, clear = tcs_read()
        colour  = classify_color(r, g, b, clear)
        summary = f"RGB({r:3d},{g:3d},{b:3d}) clr={clear:4d} → {colour or '---'}"
        if summary != last_color_print:
            last_color_print = summary
            print(summary)
        if colour and ticks_diff(now, last_stunt_time) >= COOLDOWN_MS:
            last_stunt_time = now
            print(f"Colour trigger: {colour}")
            COLOR_STUNT[colour]()

    l, r = read_joystick(CX, CY)
    drive(l, r)

    sleep_ms(20)