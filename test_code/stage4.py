# TinyCar Stage 4 — Color Sensor on real hardware
# TCS34725 on SDA=D21, SCL=D22

from machine import Pin, PWM, ADC, SoftI2C
from utime import sleep_ms, ticks_ms, ticks_diff

# ── STATUS + BUTTON ──────────────────────────
STATUS = Pin(2, Pin.OUT)
BUTTON = Pin(4, Pin.IN, Pin.PULL_UP)

# ── MOTORS (PWM) ─────────────────────────────
LF = PWM(Pin(5),  freq=1000)
LB = PWM(Pin(18), freq=1000)
RF = PWM(Pin(19), freq=1000)
RB = PWM(Pin(23), freq=1000)

def set_motor(fwd, rev, speed):
    duty = int(abs(speed) / 100 * 65535)
    if speed > 0:   fwd.duty_u16(duty); rev.duty_u16(0)
    elif speed < 0: fwd.duty_u16(0);    rev.duty_u16(duty)
    else:           fwd.duty_u16(0);    rev.duty_u16(0)

def drive(l, r):
    set_motor(LF, LB, l)
    set_motor(RF, RB, r)

def stop():
    drive(0, 0)

# ── JOYSTICK ─────────────────────────────────
JOY_X = ADC(Pin(34)); JOY_X.atten(ADC.ATTN_11DB)
JOY_Y = ADC(Pin(35)); JOY_Y.atten(ADC.ATTN_11DB)
DEAD  = 30

print("Calibrating joystick...")
sleep_ms(300)
cx = cy = 0
for _ in range(20):
    cx += JOY_X.read()
    cy += JOY_Y.read()
    sleep_ms(15)
CX = cx // 20
CY = cy // 20
print(f"Centre → X={CX}  Y={CY}")

def dz(v):
    if abs(v) < DEAD: return 0
    s = 1 if v > 0 else -1
    return s * min(100, int((abs(v) - DEAD) * 100 // (100 - DEAD)))

def read_joystick():
    rx = ry = 0
    for _ in range(5):
        rx += JOY_X.read()
        ry += JOY_Y.read()
    x = max(-100, min(100, int(-((rx // 5 - CX) * 100 / 2047))))
    y = max(-100, min(100, int((ry // 5 - CY) * 100 / 2047)))
    return max(-100, min(100, dz(y) + dz(x))), \
           max(-100, min(100, dz(y) - dz(x)))

# ── TCS34725 COLOR SENSOR ────────────────────
TCS_ADDR  = 0x29
TCS_CMD   = 0x80
TCS_ENABLE = 0x00
TCS_ATIME  = 0x01
TCS_CONTROL= 0x0F
TCS_CDATA  = 0x14

i2c = SoftI2C(sda=Pin(21), scl=Pin(22), freq=400000)

def tcs_write(reg, val):
    i2c.writeto_mem(TCS_ADDR, TCS_CMD | reg, bytes([val]))

def tcs_read16(reg):
    d = i2c.readfrom_mem(TCS_ADDR, TCS_CMD | reg, 2)
    return d[0] | (d[1] << 8)

def tcs_init():
    tcs_write(TCS_ENABLE,  0x03)
    tcs_write(TCS_ATIME,   0xD5)
    tcs_write(TCS_CONTROL, 0x00)
    sleep_ms(120)
    print("TCS34725 initialised")

def tcs_read():
    clear = tcs_read16(TCS_CDATA)
    if clear == 0:
        return 0, 0, 0, 0
    r = min(255, int(tcs_read16(TCS_CDATA + 2) * 255 / clear))
    g = min(255, int(tcs_read16(TCS_CDATA + 4) * 255 / clear))
    b = min(255, int(tcs_read16(TCS_CDATA + 6) * 255 / clear))
    return r, g, b, clear

# ── COLOR CLASSIFICATION ─────────────────────
def classify_color(r, g, b, clear):
    # Ignore readings with very low light — card being moved
    if clear < 20:                                  return None
    if max(r, g, b) < 40:                          return None

    # RED:    r≈198, g≈39,  b≈31   → r dominant, g+b very low
    if r > 170 and g < 60 and b < 60:              return "RED"

    # YELLOW: r≈135, g≈82,  b≈32   → r>g>b, b very low
    if r > 120 and g > 70 and b < 50 and r > g:    return "YELLOW"

    # GREEN:  r≈80,  g≈120, b≈43   → g dominant
    if g > 100 and g > r and g > b*2:              return "GREEN"

    # PURPLE: r≈118, g≈75,  b≈71   → r slightly highest, g≈b
    if r > 100 and g > 60 and abs(g-b) < 15 \
       and r > g and r < 140:                       return "PURPLE"

    return None

MIN_DUTY = 50   # minimum % to actually spin N20 at 3V3

def threshold(speed):
    """Remap speed so anything non-zero is at least MIN_DUTY."""
    if speed == 0: return 0
    sign = 1 if speed > 0 else -1
    mapped = MIN_DUTY + int((abs(speed) / 100) * (100 - MIN_DUTY))
    return sign * min(100, mapped)

def drive(l, r):
    set_motor(LF, LB, threshold(l))
    set_motor(RF, RB, threshold(r))

# ── STUNTS ───────────────────────────────────
def stunt_spinout():
    print("STUNT: Spinout!")
    STATUS.on()
    for _ in range(3):
        drive(100, -100); sleep_ms(300)
        drive(-100, 100); sleep_ms(300)
    stop(); STATUS.off()

def stunt_boost():
    print("STUNT: Boost!")
    STATUS.on()
    drive(100, 100); sleep_ms(800)
    stop(); STATUS.off()

def stunt_zigzag():
    for _ in range(4):
        drive(100, 40); sleep_ms(300)
        drive(40, 100); sleep_ms(300)
    stop()

def stunt_donut():
    drive(-100, -30); sleep_ms(1200)
    stop()

def stunt_brake():
    print("STUNT: Brake slide!")
    STATUS.on()
    drive(100, 100);  sleep_ms(400)
    drive(-80, -80);  sleep_ms(200)
    stop(); STATUS.off()

COLOR_STUNT = {
    "RED":    stunt_spinout,
    "GREEN":  stunt_zigzag,
    "YELLOW": stunt_donut,
    "WHITE":  stunt_brake,
    "PURPLE": stunt_boost,
}

MANUAL_STUNTS = [stunt_spinout, stunt_boost,
                 stunt_zigzag,  stunt_donut, stunt_brake]

# ── MAIN ─────────────────────────────────────
print("=" * 50)
print("  TinyCar Stage 4 — Color Sensor Live")
print("  Pass colored card under sensor")
print("  RED=spinout PURPLE=boost GREEN=zigzag")
print("  YELLOW=donut WHITE=brake slide")
print("  Button = manual stunt cycle")
print("=" * 50)

tcs_init()

for _ in range(3):
    STATUS.on(); sleep_ms(150)
    STATUS.off(); sleep_ms(150)
print("Ready!\n")

stunt_idx       = 0
last_btn        = 0
last_color_chk  = 0
last_stunt_time = -3000
COOLDOWN_MS     = 3000
last_color_print = ""

while True:
    now = ticks_ms()

    # Button → manual stunt
    if BUTTON.value() == 0 and ticks_diff(now, last_btn) > 400:
        last_btn = now
        MANUAL_STUNTS[stunt_idx]()
        stunt_idx = (stunt_idx + 1) % len(MANUAL_STUNTS)

    # Color sensor check every 120ms
    if ticks_diff(now, last_color_chk) > 120:
        last_color_chk = now
        r, g, b, clear = tcs_read()              # ← now 4 values
        colour  = classify_color(r, g, b, clear) # ← pass clear too
        summary = f"RGB({r:3d},{g:3d},{b:3d}) clear={clear:4d} → {colour if colour else '---'}"
        if summary != last_color_print:
            last_color_print = summary
            print(summary)
        if colour and ticks_diff(now, last_stunt_time) >= COOLDOWN_MS:
            last_stunt_time = now
            COLOR_STUNT[colour]()

    # Joystick → motors
    l, r = read_joystick()
    drive(l, r)

    sleep_ms(20)