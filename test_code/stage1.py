from machine import Pin
from utime import sleep_ms, ticks_ms, ticks_diff

LED    = Pin(2, Pin.OUT)
BUTTON = Pin(4, Pin.IN, Pin.PULL_UP)

print("=" * 38)
print("  TinyCar Stage 1 — Real Hardware")
print("  Watch LED blink 5x on boot")
print("  Then press button to toggle it")
print("=" * 38)

for i in range(5):
    LED.on();  sleep_ms(200)
    LED.off(); sleep_ms(200)
    print(f"Blink {i+1}/5")

print("Ready — press the button!")

led_state  = False
last_press = 0

while True:
    now = ticks_ms()
    if BUTTON.value() == 0 and ticks_diff(now, last_press) > 300:
        last_press = now
        led_state  = not led_state
        LED.value(led_state)
        print(f"Button pressed → LED {'ON' if led_state else 'OFF'}")
    sleep_ms(10)