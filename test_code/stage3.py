# TinyCar Stage 3 — Motor Test
# Tests all 4 motors via DRV8833
# LF=D5, LB=D18, RF=D19, RB=D23
# EEP must be connected to 3V3

from machine import Pin, PWM
from utime import sleep_ms

# Status LED
STATUS = Pin(2, Pin.OUT)

# Motor driver pins
LF = PWM(Pin(5),  freq=1000)
LB = PWM(Pin(18), freq=1000)
RF = PWM(Pin(19), freq=1000)
RB = PWM(Pin(23), freq=1000)

def set_motor(fwd, rev, speed):
    """speed: -100 to +100"""
    duty = int(abs(speed) / 100 * 1023)
    if speed > 0:   fwd.duty(duty); rev.duty(0)
    elif speed < 0: fwd.duty(0);    rev.duty(duty)
    else:           fwd.duty(0);    rev.duty(0)

def drive(l, r):
    set_motor(LF, LB, l)
    set_motor(RF, RB, r)

def stop():
    drive(0, 0)
    STATUS.off()

print("=" * 44)
print("  TinyCar Stage 3 — Motor Test")
print("  Watch all 4 motors respond")
print("=" * 44)

# Startup blink
for _ in range(3):
    STATUS.on(); sleep_ms(150)
    STATUS.off(); sleep_ms(150)

print("\nTest 1 — FORWARD (all motors forward)")
STATUS.on()
drive(100, 100)
sleep_ms(2000)
stop()
sleep_ms(500)

print("Test 2 — REVERSE (all motors backward)")
STATUS.on()
drive(-100, -100)
sleep_ms(2000)
stop()
sleep_ms(500)

print("Test 3 — SPIN RIGHT (left fwd, right back)")
STATUS.on()
drive(100, -100)
sleep_ms(2000)
stop()
sleep_ms(500)

print("Test 4 — SPIN LEFT (left back, right fwd)")
STATUS.on()
drive(-100, 100)
sleep_ms(2000)
stop()
sleep_ms(500)

print("Test 5 — SLOW FORWARD at 40% speed")
STATUS.on()
drive(40, 40)
sleep_ms(2000)
stop()
sleep_ms(500)

print("\nAll tests done!")
print("Check each test:")
print("  Test 1 → all 4 wheels forward")
print("  Test 2 → all 4 wheels backward")
print("  Test 3 → left wheels fwd, right wheels back")
print("  Test 4 → left wheels back, right wheels fwd")
print("  Test 5 → all 4 wheels slow forward")