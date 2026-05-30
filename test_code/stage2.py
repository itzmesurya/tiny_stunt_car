# TinyCar Stage 2 — Joystick on real hardware
# VRx → D34, VRy → D35, +5V → 3V3 rail, GND → GND rail

from machine import Pin, ADC
from utime import sleep_ms, ticks_ms, ticks_diff

LED    = Pin(2, Pin.OUT)
BUTTON = Pin(4, Pin.IN, Pin.PULL_UP)

JOY_X = ADC(Pin(34))
JOY_Y = ADC(Pin(35))
JOY_X.atten(ADC.ATTN_11DB)
JOY_Y.atten(ADC.ATTN_11DB)

DEAD = 30

# Calibrate resting position on boot
print("Calibrating — don't touch joystick...")
sleep_ms(300)
cx = cy = 0
for _ in range(20):
    cx += JOY_X.read()
    cy += JOY_Y.read()
    sleep_ms(15)
CX = cx // 20
CY = cy // 20
print(f"Centre → X={CX}  Y={CY}  (ideal 2047)")

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
    return max(-100, min(100, dz(y) + dz(x))), max(-100, min(100, dz(y) - dz(x)))

def direction(l, r):
    if l == 0 and r == 0:  return "STOPPED   "
    if l > 0  and r > 0:   return "FORWARD   "
    if l < 0  and r < 0:   return "REVERSE   "
    if l > 0  and r <= 0:  return "SPIN RIGHT"
    if l <= 0 and r > 0:   return "SPIN LEFT "
    return "TURNING   "

print("=" * 42)
print("  TinyCar Stage 2 — Joystick")
print("  Move joystick → see direction in console")
print("  Button → toggles LED")
print("=" * 42)

for _ in range(3):
    LED.on(); sleep_ms(150); LED.off(); sleep_ms(150)
print("Ready!\n")

led_state  = False
last_press = 0
last_print = 0
prev_l = prev_r = 999

while True:
    now = ticks_ms()

    if BUTTON.value() == 0 and ticks_diff(now, last_press) > 300:
        last_press = now
        led_state = not led_state
        LED.value(led_state)
        print(f"Button → LED {'ON' if led_state else 'OFF'}")

    l, r = read_joystick()

    if ticks_diff(now, last_print) > 200:
        last_print = now
        if l != prev_l or r != prev_r:
            prev_l, prev_r = l, r
            if l == 0 and r == 0:
                print("STOPPED")
            else:
                print(f"{direction(l,r)}  L:{l:+4d}%  R:{r:+4d}%")

    sleep_ms(20)