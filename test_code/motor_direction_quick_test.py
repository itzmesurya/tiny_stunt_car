from machine import Pin
from utime import sleep_ms

LF = Pin(5,  Pin.OUT)
LB = Pin(18, Pin.OUT)
RF = Pin(19, Pin.OUT)
RB = Pin(23, Pin.OUT)

def stop():
    LF.off(); LB.off(); RF.off(); RB.off()

stop()
sleep_ms(1000)

print("FORWARD TEST")
print("Left motors should spin CW")
print("Right motors should spin CCW")
print("If placed in car this should push FORWARD")
LF.on(); LB.off(); RF.off(); RB.on()
sleep_ms(8000)
stop()
sleep_ms(2000)

print("REVERSE TEST")
print("Left motors should spin CCW")
print("Right motors should spin CW")
LF.off(); LB.on(); RF.on(); RB.off()
sleep_ms(8000)
stop()

print("Done!")