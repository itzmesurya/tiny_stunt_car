# TinyCar Stage 3 — Joystick + Motors integrated
# All components on one ESP32

from machine import Pin, PWM, ADC
from utime import sleep_ms, ticks_ms, ticks_diff

# ── STATUS + BUTTON ──────────────────────────
STATUS = Pin(2, Pin.OUT)
BUTTON = Pin(4, Pin.IN, Pin.PULL_UP)

# ── MOTORS ───────────────────────────────────
LF = Pin(5,  Pin.OUT)
LB = Pin(18, Pin.OUT)
RF = Pin(19, Pin.OUT)
RB = Pin(23, Pin.OUT)

def set_motor_simple(fwd, rev, speed):
    """Simple HIGH/LOW motor control."""
    if speed > 0:    fwd.on();  rev.off()
    elif speed < 0:  fwd.off(); rev.on()
    else:            fwd.off(); rev.off()

def drive(l, r):
    set_motor_simple(LF, LB, l)
    set_motor_simple(RF, RB, r)

def stop():
    drive(0, 0)

# ── JOYSTICK ─────────────────────────────────
JOY_X = ADC(Pin(34)); JOY_X.atten(ADC.ATTN_11DB)
JOY_Y = ADC(Pin(35)); JOY_Y.atten(ADC.ATTN_11DB)

DEAD = 30

print("Calibrating joystick — don't touch it...")
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
    print("STUNT: Zigzag!")
    STATUS.on()
    for _ in range(4):
        drive(100, 30); sleep_ms(250)
        drive(30, 100); sleep_ms(250)
    stop(); STATUS.off()

def stunt_donut():
    print("STUNT: Reverse donut!")
    STATUS.on()
    drive(-100, -20); sleep_ms(1200)
    stop(); STATUS.off()

STUNTS = [stunt_spinout, stunt_boost, stunt_zigzag, stunt_donut]

# ── MAIN ─────────────────────────────────────
print("=" * 48)
print("  TinyCar Stage 3 — Joystick + Motors")
print("  Joystick → drives all 4 motors")
print("  Button   → cycles through stunts")
print("=" * 48)

for _ in range(3):
    STATUS.on(); sleep_ms(150)
    STATUS.off(); sleep_ms(150)
print("Ready!\n")

stunt_idx  = 0
last_btn   = 0
last_print = 0
prev_l = prev_r = 999

while True:
    now = ticks_ms()

    # Button → stunt
    if BUTTON.value() == 0 and ticks_diff(now, last_btn) > 400:
        last_btn = now
        STUNTS[stunt_idx]()
        stunt_idx = (stunt_idx + 1) % len(STUNTS)
        prev_l = prev_r = 999

    # Joystick → motors
    l, r = read_joystick()
    drive(l, r)

    # Serial output
    if ticks_diff(now, last_print) > 200:
        last_print = now
        if l != prev_l or r != prev_r:
            prev_l, prev_r = l, r
            if l == 0 and r == 0:
                print("STOPPED")
            else:
                print(f"L:{l:+4d}%  R:{r:+4d}%")

    sleep_ms(20)