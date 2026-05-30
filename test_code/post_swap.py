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

print("ALL FORWARD — all 4 wheels should spin same direction")
LF.on(); LB.off(); RF.on(); RB.off()
sleep_ms(5000)
stop()
sleep_ms(2000)

print("ALL BACKWARD — all 4 wheels should spin same direction")
LF.off(); LB.on(); RF.off(); RB.on()
sleep_ms(5000)
stop()

print("Done — did all 4 spin the same direction both times?")