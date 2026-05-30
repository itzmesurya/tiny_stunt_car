from machine import Pin
from utime import ticks_ms, ticks_diff

BUTTON = Pin(4, Pin.IN, Pin.PULL_UP)
print("Press the button within 5 seconds...")

pressed = 0
last = 0
deadline = ticks_ms() + 5000
while ticks_diff(deadline, ticks_ms()) > 0:
    if BUTTON.value() == 0 and ticks_diff(ticks_ms(), last) > 300:
        pressed += 1
        last = ticks_ms()
        print(f"Press detected! ({pressed})")

if pressed:
    print("PASS")
else:
    print("FAIL — nothing detected")