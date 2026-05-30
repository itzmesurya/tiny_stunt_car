from machine import Pin
from utime import sleep_ms

BUTTON = Pin(4, Pin.IN, Pin.PULL_UP)

print("Reading button pin D4 every 500ms")
print("Should print 1 constantly when not pressed")
print("Should print 0 only when you press the button")
print("")

while True:
    print(f"D4 = {BUTTON.value()}")
    sleep_ms(500)