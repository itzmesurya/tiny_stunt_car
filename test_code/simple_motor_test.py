from machine import Pin, PWM
from utime import sleep_ms

LF = PWM(Pin(5),  freq=1000)
LB = PWM(Pin(18), freq=1000)
RF = PWM(Pin(19), freq=1000)
RB = PWM(Pin(23), freq=1000)

def set_motor(fwd, rev, speed):
    """speed: -100 to +100"""
    duty = int(abs(speed) / 100 * 65535)
    if speed > 0:   fwd.duty_u16(duty); rev.duty_u16(0)
    elif speed < 0: fwd.duty_u16(0);    rev.duty_u16(duty)
    else:           fwd.duty_u16(0);    rev.duty_u16(0)

def drive(l, r):
    set_motor(LF, LB, l)
    set_motor(RF, RB, r)

def stop():
    drive(0, 0)

print("Motor test — full forward 3 seconds")
drive(100, 100)
sleep_ms(3000)
stop()
print("Done — did motors spin?")