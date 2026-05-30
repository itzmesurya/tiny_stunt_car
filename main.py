# ═══════════════════════════════════════════════════════════════
#  TinyCar — Stage 4 Complete Car Firmware
#  MicroPython v1.28 · ESP32 DevKit v1
#
#  All systems integrated and calibrated:
#    ✅ TCS34725 colour sensor — 5 colours calibrated
#    ✅ 4× N20 motors via DRV8833 — all directions confirmed
#    ✅ Joystick steering — dead zone 30%, axes corrected
#    ✅ 5 colour-triggered stunts with 3s cooldown
#    ✅ 5 manual stunts via button cycle
#    ✅ PWM motor control with minimum threshold
#    ✅ Full stunt debug logging
#
#  Pin Map:
#    GPIO2  → Status LED (green, 330Ω to GND)
#    GPIO4  → Mode button (to GND, internal pull-up)
#    GPIO5  → DRV8833 IN1 — LF (Left Forward)
#    GPIO18 → DRV8833 IN2 — LB (Left Backward)
#    GPIO19 → DRV8833 IN3 — RF (Right Forward)
#    GPIO23 → DRV8833 IN4 — RB (Right Backward)
#    GPIO21 → TCS34725 SDA
#    GPIO22 → TCS34725 SCL
#    GPIO34 → Joystick VRx (HORZ) — moves to remote after BLE split
#    GPIO35 → Joystick VRy (VERT) — moves to remote after BLE split
#
#  DRV8833 wiring:
#    VCC → 3V3 rail
#    GND → GND rail
#    EEP → leave unconnected (not needed for basic operation)
#    OUT1/OUT2 → Left motors in parallel
#    OUT3/OUT4 → Right motors in parallel
#
#  Colour → Stunt map (calibrated to real sensor readings):
#    RED    RGB(~198,~39,~31)  clr=300+   → Spinout
#    YELLOW RGB(~154,~76,~32)  clr=2000+  → Reverse donut
#    GREEN  RGB(~78,~125,~43)  clr=500+   → Zigzag
#    PURPLE RGB(~116,~78,~74)  clr=150+   → Boost
#    WHITE  RGB(~105,~94,~51)  clr=2000+  → Brake slide
# ═══════════════════════════════════════════════════════════════
from car_ble_receiver import BLERemote
from machine import Pin, PWM, ADC, SoftI2C
from utime import sleep_ms, ticks_ms, ticks_diff

# ── STATUS LED + BUTTON ──────────────────────────────────────
STATUS = Pin(2, Pin.OUT)
BUTTON = Pin(4, Pin.IN, Pin.PULL_UP)

# ── MOTOR DRIVER (DRV8833) ───────────────────────────────────
LF = PWM(Pin(5),  freq=1000)   # Left  Forward
LB = PWM(Pin(18), freq=1000)   # Left  Backward
RF = PWM(Pin(19), freq=1000)   # Right Forward
RB = PWM(Pin(23), freq=1000)   # Right Backward

# Minimum PWM threshold to overcome N20 gearbox stiction at 3.3V
# Motors below this duty cycle don't spin — threshold maps 0-100 → 50-100
MIN_DUTY = 50

def threshold(speed):
    """
    Remaps speed so any non-zero value is at least MIN_DUTY%.
    Prevents motors stalling at low PWM values under 3.3V power.
    Example: threshold(40) → 70%, threshold(100) → 100%, threshold(0) → 0%
    """
    if speed == 0: return 0
    sign  = 1 if speed > 0 else -1
    mapped = MIN_DUTY + int((abs(speed) / 100) * (100 - MIN_DUTY))
    return sign * min(100, mapped)

def set_motor(fwd, rev, speed):
    """Drive one motor pair. speed: -100 (full back) to +100 (full fwd)."""
    duty = int(abs(speed) / 100 * 65535)
    if speed > 0:   fwd.duty_u16(duty); rev.duty_u16(0)
    elif speed < 0: fwd.duty_u16(0);    rev.duty_u16(duty)
    else:           fwd.duty_u16(0);    rev.duty_u16(0)

def drive(l, r, log=False, label=""):
    """
    Drive both motor pairs with threshold applied.
    l, r: -100 to +100 (left and right wheel speed)
    log: if True prints motor command to console
    """
    tl = threshold(l)
    tr = threshold(r)
    set_motor(LF, LB, tl)
    set_motor(RF, RB, tr)
    if log:
        ldir = "FWD" if tl > 0 else ("BCK" if tl < 0 else "STP")
        rdir = "FWD" if tr > 0 else ("BCK" if tr < 0 else "STP")
        print(f"  {label:<22} LF/LB={ldir} {abs(tl):3d}%   RF/RB={rdir} {abs(tr):3d}%")

def stop(label="STOP"):
    drive(0, 0, log=True, label=label)

# ── JOYSTICK ─────────────────────────────────────────────────
# NOTE: After BLE split these pins move to the remote ESP32.
# The car will receive L/R values over BLE instead.
JOY_X = ADC(Pin(34)); JOY_X.atten(ADC.ATTN_11DB)   # HORZ (VRx)
JOY_Y = ADC(Pin(35)); JOY_Y.atten(ADC.ATTN_11DB)   # VERT (VRy)

DEAD_ZONE = 30   # % dead zone — calibrated for this joystick module

def _dz(v):
    """Apply dead zone and remap remaining range to 0-100%."""
    if abs(v) < DEAD_ZONE: return 0
    s = 1 if v > 0 else -1
    return s * min(100, int((abs(v) - DEAD_ZONE) * 100 // (100 - DEAD_ZONE)))

def calibrate_joystick():
    """Read resting position 20 times to establish true centre."""
    print("Calibrating joystick — don't touch it...")
    sleep_ms(300)
    cx = cy = 0
    for _ in range(20):
        cx += JOY_X.read()
        cy += JOY_Y.read()
        sleep_ms(15)
    cx //= 20; cy //= 20
    print(f"Centre → X={cx}  Y={cy}  (ideal 2047)")
    return cx, cy

def read_joystick(cx, cy):
    """
    Returns (left%, right%) each -100 to +100.
    X axis negated to match physical joystick orientation.
    Y axis: push away = forward, pull toward = reverse.
    Differential steering: y+x → left wheel, y-x → right wheel.
    """
    rx = ry = 0
    for _ in range(5):   # 5-sample average kills ADC jitter
        rx += JOY_X.read()
        ry += JOY_Y.read()
    x = max(-100, min(100, int(-((rx//5 - cx) * 100 / 2047))))
    y = max(-100, min(100, int(  (ry//5 - cy) * 100 / 2047)))
    l = max(-100, min(100, _dz(y) + _dz(x)))
    r = max(-100, min(100, _dz(y) - _dz(x)))
    return l, r

# ── TCS34725 COLOUR SENSOR ───────────────────────────────────
TCS_ADDR    = 0x29
TCS_CMD     = 0x80
TCS_ENABLE  = 0x00
TCS_ATIME   = 0x01
TCS_CONTROL = 0x0F
TCS_CDATA   = 0x14   # clear low byte (R at +2, G at +4, B at +6)

i2c = SoftI2C(sda=Pin(21), scl=Pin(22), freq=400_000)

def _tcs_write(reg, val):
    i2c.writeto_mem(TCS_ADDR, TCS_CMD | reg, bytes([val]))

def _tcs_read16(reg):
    d = i2c.readfrom_mem(TCS_ADDR, TCS_CMD | reg, 2)
    return d[0] | (d[1] << 8)

def tcs_init():
    _tcs_write(TCS_ENABLE,  0x03)   # power on + RGBC enable
    _tcs_write(TCS_ATIME,   0xD5)   # integration time ~101ms
    _tcs_write(TCS_CONTROL, 0x00)   # 1× gain
    sleep_ms(120)
    print("TCS34725 initialised")

def tcs_read():
    """
    Returns (r, g, b, clear) each 0-255 normalised against clear channel.
    Returns (0,0,0,0) if no light detected.
    """
    clear = _tcs_read16(TCS_CDATA)
    if clear == 0:
        return 0, 0, 0, 0
    r = min(255, int(_tcs_read16(TCS_CDATA + 2) * 255 / clear))
    g = min(255, int(_tcs_read16(TCS_CDATA + 4) * 255 / clear))
    b = min(255, int(_tcs_read16(TCS_CDATA + 6) * 255 / clear))
    return r, g, b, clear

# ── COLOUR CLASSIFICATION ────────────────────────────────────
# Thresholds calibrated from real sensor readings on real cards.
# Sensor held 2-3mm from card surface under room lighting.
#
# Calibration data:
#   RED:    RGB(197-222, 38-44,  31-38)  clr=117-809
#   YELLOW: RGB(126-157, 75-90,  32-38)  clr=85-3067
#   GREEN:  RGB(75-91,  118-127, 42-47)  clr=139-1597
#   PURPLE: RGB(115-137, 73-83,  71-82)  clr=201-898
#   WHITE:  RGB(105-109, 92-95,  51-52)  clr=3294-4597
#   NONE:   clear < 20 or max(r,g,b) < 40

def classify_color(r, g, b, clear):
    if clear < 20:                                          return None
    if max(r, g, b) < 40:                                  return None
    if r > 170 and g < 60  and b < 60:                    return "RED"
    if r > 120 and g > 70  and b < 50 and r > g:          return "YELLOW"
    if g > 100 and g > r   and g > b * 2:                 return "GREEN"
    if r > 100 and g > 60  and abs(g - b) < 15 \
       and r > g and r < 140 and clear > 150:              return "PURPLE"
    if r < 80  and g > 85  and b > 85 \
       and abs(g - b) < 20 and clear > 150:               return "BLUE"
    return None

# ── STUNT LIBRARY ────────────────────────────────────────────
def stunt_spinout():
    print("\n┌─ SPINOUT ──────────────────────────────")
    STATUS.on()
    for i in range(3):
        print(f"│ Cycle {i+1}/3:")
        drive(100, -100, log=True, label="  Phase A — fwd/back")
        sleep_ms(300)
        drive(-100, 100, log=True, label="  Phase B — back/fwd")
        sleep_ms(300)
    stop("  Final stop")
    STATUS.off()
    print("└────────────────────────────────────────\n")

def stunt_boost():
    print("\n┌─ BOOST ─────────────────────────────────")
    STATUS.on()
    drive(100, 100, log=True, label="  Full forward")
    sleep_ms(800)
    stop("  Final stop")
    STATUS.off()
    print("└────────────────────────────────────────\n")

def stunt_zigzag():
    print("\n┌─ ZIGZAG ────────────────────────────────")
    STATUS.on()
    for i in range(4):
        print(f"│ Arc {i+1}/4:")
        drive(100, 40, log=True, label="  Left arc")
        sleep_ms(300)
        drive(40, 100, log=True, label="  Right arc")
        sleep_ms(300)
    stop("  Final stop")
    STATUS.off()
    print("└────────────────────────────────────────\n")

def stunt_donut():
    print("\n┌─ REVERSE DONUT ─────────────────────────")
    STATUS.on()
    drive(-100, -50, log=True, label="  Tight reverse arc")
    sleep_ms(1200)
    stop("  Final stop")
    STATUS.off()
    print("└────────────────────────────────────────\n")

def stunt_brake():
    print("\n┌─ BRAKE SLIDE ───────────────────────────")
    STATUS.on()
    drive(100, 100, log=True, label="  Run up")
    sleep_ms(400)
    drive(-80, -80, log=True, label="  Hard brake")
    sleep_ms(200)
    stop("  Final stop")
    STATUS.off()
    print("└────────────────────────────────────────\n")

# Colour → stunt mapping
COLOR_STUNT = {
    "RED":    stunt_spinout,
    "YELLOW": stunt_donut,
    "GREEN":  stunt_zigzag,
    "PURPLE": stunt_boost,
    "BLUE":   stunt_brake,
}

# Manual button cycle order
MANUAL_STUNTS = [
    stunt_spinout,
    stunt_boost,
    stunt_zigzag,
    stunt_donut,
    stunt_brake,
]

# ── STARTUP ──────────────────────────────────────────────────
def startup_blink(n=3):
    for _ in range(n):
        STATUS.on();  sleep_ms(150)
        STATUS.off(); sleep_ms(150)

# ── MAIN ─────────────────────────────────────────────────────
print("=" * 52)
print("  TinyCar Stage 4 — Complete Car Firmware")
print("  5 colours · 5 stunts · joystick steering")
print("=" * 52)

# Initialise subsystems
    # CX, CY = calibrate_joystick()
tcs_init()
ble_remote = BLERemote()
startup_blink()

print("\nColour → Stunt map:")
print("  RED    → Spinout")
print("  YELLOW → Reverse donut")
print("  GREEN  → Zigzag")
print("  PURPLE → Boost")
print("  BLUE   → Brake slide")
print("\nButton → Manual stunt cycle")
print("Ready!\n")

# ── LOOP VARIABLES ───────────────────────────────────────────
stunt_idx        = 0
last_btn         = 0
last_color_chk   = 0
last_stunt_time  = -3000   # allows immediate first trigger
COOLDOWN_MS      = 3000    # 3 seconds between colour-triggered stunts
last_color_print = ""

# ── MAIN LOOP ────────────────────────────────────────────────
while True:
    now = ticks_ms()

    # ── 1. BUTTON — manual stunt cycle (highest priority) ────
    if BUTTON.value() == 0 and ticks_diff(now, last_btn) > 400:
        last_btn = now
        print(f"Button → manual stunt #{stunt_idx + 1}")
        MANUAL_STUNTS[stunt_idx]()
        stunt_idx = (stunt_idx + 1) % len(MANUAL_STUNTS)

    # ── 2. COLOUR SENSOR — check every 120ms ─────────────────
    if ticks_diff(now, last_color_chk) > 120:
        last_color_chk = now
        r, g, b, clear = tcs_read()
        colour  = classify_color(r, g, b, clear)
        summary = f"RGB({r:3d},{g:3d},{b:3d}) clr={clear:4d} → {colour or '---'}"

        # Only print when reading changes (reduce console spam)
        if summary != last_color_print:
            last_color_print = summary
            print(summary)

        # Trigger stunt if colour detected and cooldown expired
        if colour and ticks_diff(now, last_stunt_time) >= COOLDOWN_MS:
            last_stunt_time = now
            print(f"Colour trigger: {colour}")
            COLOR_STUNT[colour]()

    # ── 3. JOYSTICK — continuous motor control ───────────────
    # NOTE: This block is removed after BLE split.
    # Replace with: l, r = ble_remote.get_drive()
    if ble_remote.connected:
        l, r = ble_remote.get_drive()
        drive(l, r)

    sleep_ms(20)   # 50Hz main loop