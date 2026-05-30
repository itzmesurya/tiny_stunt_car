# ═══════════════════════════════════════════════════════════════
#  TinyCar — Remote Hardware Test Script
#  MicroPython v1.28 · ESP32 DevKit v1
#
#  Run this BEFORE flashing remote_main.py to confirm every
#  component is wired and responding correctly.
#
#  Tests (in order):
#    1. Status LED        — blinks 5× rapidly
#    2. 3V3 rail          — joystick VCC check via ADC read
#    3. Joystick VRx      — move left/right, watch console
#    4. Joystick VRy      — move forward/back, watch console
#    5. Pair button       — press button, watch console
#    6. BLE scan          — scans for TinyCar MAC, prints result
#
#  Each test prints PASS or FAIL with a reason.
#  Upload this as main.py, open REPL, press reset.
# ═══════════════════════════════════════════════════════════════

from machine import Pin, ADC
from utime import sleep_ms, ticks_ms, ticks_diff
import bluetooth

# ── PIN DEFINITIONS ──────────────────────────────────────────
STATUS = Pin(2, Pin.OUT)
BUTTON = Pin(4, Pin.IN, Pin.PULL_UP)
JOY_X  = ADC(Pin(34)); JOY_X.atten(ADC.ATTN_11DB)
JOY_Y  = ADC(Pin(35)); JOY_Y.atten(ADC.ATTN_11DB)

CAR_MAC = "30:76:f5:e7:69:04"

# ── HELPERS ──────────────────────────────────────────────────
def header(title):
    print()
    print("─" * 48)
    print(f"  TEST: {title}")
    print("─" * 48)

def passed(msg=""):
    print(f"  ✅  PASS  {msg}")

def failed(msg=""):
    print(f"  ❌  FAIL  {msg}")

def info(msg):
    print(f"  ℹ   {msg}")

# ═══════════════════════════════════════════════════════════════
#  TEST 1 — Status LED
# ═══════════════════════════════════════════════════════════════
header("Status LED (GPIO2)")
info("Watch for 5 rapid blinks on the green LED...")
sleep_ms(500)
for _ in range(5):
    STATUS.on();  sleep_ms(100)
    STATUS.off(); sleep_ms(100)
sleep_ms(200)
# We can't read back an output pin reliably, so ask the user
info("Did the LED blink 5 times?")
info("If yes → PASS. If no LED blinked → check 330Ω resistor and LED polarity.")
passed("LED blink sequence sent — verify visually")

# ═══════════════════════════════════════════════════════════════
#  TEST 2 — Joystick 3V3 rail (VCC check via resting ADC value)
# ═══════════════════════════════════════════════════════════════
header("Joystick VCC — 3V3 rail check")
info("Reading joystick at rest. Expect ~1800–2200 on both axes.")
info("A dead rail reads 0 or 4095 consistently.")

x_samples = [JOY_X.read() for _ in range(10)]
y_samples = [JOY_Y.read() for _ in range(10)]
x_avg = sum(x_samples) // 10
y_avg = sum(y_samples) // 10

info(f"VRx avg = {x_avg}  (samples: {x_samples})")
info(f"VRy avg = {y_avg}  (samples: {y_samples})")

x_ok = 500 < x_avg < 3500
y_ok = 500 < y_avg < 3500

if x_ok and y_ok:
    passed(f"VRx={x_avg} VRy={y_avg} — 3V3 rail healthy")
elif x_avg <= 10 or y_avg <= 10:
    failed("Readings near 0 — joystick VCC not connected to 3V3 pin")
elif x_avg >= 4085 or y_avg >= 4085:
    failed("Readings at max — joystick GND not connected")
else:
    failed(f"Unexpected values VRx={x_avg} VRy={y_avg} — check wiring")

# ═══════════════════════════════════════════════════════════════
#  TEST 3 — Joystick VRx (GPIO34, HORZ axis)
# ═══════════════════════════════════════════════════════════════
header("Joystick VRx — GPIO34 (left/right)")
info("Move joystick LEFT then RIGHT over the next 5 seconds.")
info("You should see the value drop then rise (or rise then drop).")

cx = JOY_X.read()
info(f"Centre reading: {cx}")

min_x = cx
max_x = cx
deadline = ticks_ms() + 5000
while ticks_diff(deadline, ticks_ms()) > 0:
    v = JOY_X.read()
    if v < min_x: min_x = v
    if v > max_x: max_x = v
    print(f"  VRx = {v:4d}", end="\r")
    sleep_ms(50)

print()
spread = max_x - min_x
info(f"Range seen: {min_x} – {max_x}  (spread={spread})")

if spread > 1500:
    passed(f"VRx responding — spread {spread} is good")
elif spread > 500:
    passed(f"VRx responding — spread {spread} (move joystick further for full range)")
else:
    failed(f"VRx barely moved (spread={spread}) — check GPIO34 → HORZ wiring")

# ═══════════════════════════════════════════════════════════════
#  TEST 4 — Joystick VRy (GPIO35, VERT axis)
# ═══════════════════════════════════════════════════════════════
header("Joystick VRy — GPIO35 (forward/back)")
info("Move joystick FORWARD then BACK over the next 5 seconds.")

cy = JOY_Y.read()
info(f"Centre reading: {cy}")

min_y = cy
max_y = cy
deadline = ticks_ms() + 5000
while ticks_diff(deadline, ticks_ms()) > 0:
    v = JOY_Y.read()
    if v < min_y: min_y = v
    if v > max_y: max_y = v
    print(f"  VRy = {v:4d}", end="\r")
    sleep_ms(50)

print()
spread = max_y - min_y
info(f"Range seen: {min_y} – {max_y}  (spread={spread})")

if spread > 1500:
    passed(f"VRy responding — spread {spread} is good")
elif spread > 500:
    passed(f"VRy responding — spread {spread} (move joystick further for full range)")
else:
    failed(f"VRy barely moved (spread={spread}) — check GPIO35 → VERT wiring")

# ═══════════════════════════════════════════════════════════════
#  TEST 5 — Pair button (GPIO4)
# ═══════════════════════════════════════════════════════════════
header("Pair button — GPIO4")
info("Press the pair button within the next 5 seconds...")

pressed_count = 0
last_state    = BUTTON.value()
deadline      = ticks_ms() + 5000
last_press    = 0

while ticks_diff(deadline, ticks_ms()) > 0:
    state = BUTTON.value()
    if state == 0 and last_state == 1 and ticks_diff(ticks_ms(), last_press) > 300:
        pressed_count += 1
        last_press = ticks_ms()
        info(f"Button press detected ({pressed_count})")
    last_state = state
    sleep_ms(20)

if pressed_count >= 1:
    passed(f"Button detected {pressed_count} press(es)")
elif pressed_count == 0:
    failed("No press detected — check button legs span centre gap, and GND wire")

# ═══════════════════════════════════════════════════════════════
#  TEST 6 — BLE scan for TinyCar
# ═══════════════════════════════════════════════════════════════
header("BLE scan — looking for TinyCar")
info(f"Scanning for {CAR_MAC} for 6 seconds...")
info("Make sure the car ESP32 is powered on and running car firmware.")

def mac_bytes_to_str(b):
    return ":".join(f"{x:02x}" for x in reversed(b))

ble         = bluetooth.BLE()
ble.active(True)

found       = False
found_rssi  = 0
all_found   = []

def _irq(event, data):
    global found, found_rssi
    if event == 5:   # _IRQ_SCAN_RESULT
        addr_type, addr, adv_type, rssi, adv_data = data
        mac = mac_bytes_to_str(bytes(addr))
        if mac not in all_found:
            all_found.append(mac)
        if mac == CAR_MAC:
            found      = True
            found_rssi = rssi
            ble.gap_scan(0)

ble.irq(_irq)
ble.gap_scan(6000, 30000, 30000, True)

# Wait for scan to finish (up to 7s)
deadline = ticks_ms() + 7000
while ticks_diff(deadline, ticks_ms()) > 0 and not found:
    sleep_ms(100)

ble.gap_scan(0)
ble.active(False)

if found:
    passed(f"TinyCar found at {CAR_MAC}  RSSI={found_rssi}dBm")
else:
    failed(f"TinyCar not found — is the car powered and advertising?")
    if all_found:
        info(f"Other BLE devices seen: {len(all_found)}")
        for m in all_found[:5]:
            info(f"  {m}")

# ═══════════════════════════════════════════════════════════════
#  SUMMARY
# ═══════════════════════════════════════════════════════════════
print()
print("═" * 48)
print("  Remote hardware test complete.")
print("  If all tests passed → flash remote_main.py")
print("═" * 48)