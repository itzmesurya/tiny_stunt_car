from machine import Pin, PWM
from utime import sleep_ms

# Control pins
LF = Pin(5,  Pin.OUT)   # Left Forward  — plain GPIO first
LB = Pin(18, Pin.OUT)   # Left Backward

print("Test 1 — Motor A forward (LF=HIGH, LB=LOW)")
LF.on()
LB.off()
sleep_ms(2000)

print("Test 2 — Stop")
LF.off()
LB.off()
sleep_ms(1000)

print("Test 3 — Motor A reverse (LF=LOW, LB=HIGH)")
LF.off()
LB.on()
sleep_ms(2000)

print("Test 4 — Stop")
LF.off()
LB.off()

print("Done — did motor spin?")