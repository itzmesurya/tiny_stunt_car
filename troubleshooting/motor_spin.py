# Simple motor spin test — all motors for 5 seconds
from machine import Pin, PWM
from utime import sleep_ms

# Kill pins first
for pin_num in [5, 18, 19, 23]:
    Pin(pin_num, Pin.OUT).value(0)

LF = PWM(Pin(18), freq=1000)
LB = PWM(Pin(5),  freq=1000)
RF = PWM(Pin(23), freq=1000)
RB = PWM(Pin(19), freq=1000)

for p in [LF, LB, RF, RB]:
    p.duty_u16(0)

print("Spinning all motors for 5 seconds...")
LF.duty_u16(40000)
RF.duty_u16(40000)
sleep_ms(5000)

for p in [LF, LB, RF, RB]:
    p.duty_u16(0)
print("Done.")