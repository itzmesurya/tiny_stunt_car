from machine import Pin
from utime import sleep

led = Pin(2, Pin.OUT)   # GPIO2 = onboard blue LED on ESP32 DevKit v1

print("LED starts flashing...")
while True:
    try:
        led.toggle()
        sleep(1)
    except KeyboardInterrupt:
        break

led.off()
print("Finished.")