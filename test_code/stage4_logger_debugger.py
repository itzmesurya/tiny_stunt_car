# TinyCar Stage 4 — Stunt Debug Logger
# Drop this into your stage4.py to replace the stunt functions
# Logs every motor command with timestamp and duty %

from machine import Pin, PWM, ADC, SoftI2C
from utime import sleep_ms, ticks_ms, ticks_diff

STATUS = Pin(2, Pin.OUT)
BUTTON = Pin(4, Pin.IN, Pin.PULL_UP)

LF = PWM(Pin(5),  freq=1000)
LB = PWM(Pin(18), freq=1000)
RF = PWM(Pin(19), freq=1000)
RB = PWM(Pin(23), freq=1000)

MIN_DUTY = 50

def threshold(speed):
    if speed == 0: return 0
    sign = 1 if speed > 0 else -1
    mapped = MIN_DUTY + int((abs(speed) / 100) * (100 - MIN_DUTY))
    return sign * min(100, mapped)

def set_motor(fwd, rev, speed):
    duty = int(abs(speed) / 100 * 65535)
    if speed > 0:   fwd.duty_u16(duty); rev.duty_u16(0)
    elif speed < 0: fwd.duty_u16(0);    rev.duty_u16(duty)
    else:           fwd.duty_u16(0);    rev.duty_u16(0)

def drive(l, r, log=False, label=""):
    tl = threshold(l)
    tr = threshold(r)
    set_motor(LF, LB, tl)
    set_motor(RF, RB, tr)
    if log:
        ldir = "FWD" if tl > 0 else ("BCK" if tl < 0 else "STP")
        rdir = "FWD" if tr > 0 else ("BCK" if tr < 0 else "STP")
        print(f"  {label:<20} LF/LB={ldir} {abs(tl):3d}%   RF/RB={rdir} {abs(tr):3d}%")

def stop(label="STOP"):
    drive(0, 0, log=True, label=label)

# ── JOYSTICK ─────────────────────────────────────────────────
JOY_X = ADC(Pin(34)); JOY_X.atten(ADC.ATTN_11DB)
JOY_Y = ADC(Pin(35)); JOY_Y.atten(ADC.ATTN_11DB)
DEAD  = 30

print("Calibrating joystick...")
sleep_ms(300)
cx = cy = 0
for _ in range(20):
    cx += JOY_X.read(); cy += JOY_Y.read(); sleep_ms(15)
CX = cx // 20; CY = cy // 20
print(f"Centre → X={CX}  Y={CY}\n")

def dz(v):
    if abs(v) < DEAD: return 0
    s = 1 if v > 0 else -1
    return s * min(100, int((abs(v) - DEAD) * 100 // (100 - DEAD)))

def read_joystick():
    rx = ry = 0
    for _ in range(5): rx += JOY_X.read(); ry += JOY_Y.read()
    x = max(-100, min(100, int(-((rx//5 - CX)*100/2047))))
    y = max(-100, min(100, int((ry//5 - CY)*100/2047)))
    return max(-100,min(100,dz(y)+dz(x))), max(-100,min(100,dz(y)-dz(x)))

# ── TCS34725 ─────────────────────────────────────────────────
TCS_ADDR=0x29; TCS_CMD=0x80; TCS_ENABLE=0x00
TCS_ATIME=0x01; TCS_CONTROL=0x0F; TCS_CDATA=0x14

i2c = SoftI2C(sda=Pin(21), scl=Pin(22), freq=400000)

def tcs_write(reg, val):
    i2c.writeto_mem(TCS_ADDR, TCS_CMD|reg, bytes([val]))

def tcs_read16(reg):
    d = i2c.readfrom_mem(TCS_ADDR, TCS_CMD|reg, 2)
    return d[0]|(d[1]<<8)

def tcs_init():
    tcs_write(TCS_ENABLE, 0x03)
    tcs_write(TCS_ATIME,  0xD5)
    tcs_write(TCS_CONTROL,0x00)
    sleep_ms(120)
    print("TCS34725 initialised")

def tcs_read():
    clear = tcs_read16(TCS_CDATA)
    if clear == 0: return 0,0,0,0
    r = min(255, int(tcs_read16(TCS_CDATA+2)*255/clear))
    g = min(255, int(tcs_read16(TCS_CDATA+4)*255/clear))
    b = min(255, int(tcs_read16(TCS_CDATA+6)*255/clear))
    return r,g,b,clear

def classify_color(r, g, b, clear):
    if clear < 20:                                  return None
    if max(r,g,b) < 40:                            return None
    if r > 170 and g < 60  and b < 60:             return "RED"
    if r > 120 and g > 70  and b < 50 and r > g:   return "YELLOW"
    if g > 100 and g > r   and g > b*2:            return "GREEN"
    if r > 100 and g > 60 and abs(g-b) < 15 \
        and r > g and r < 140 and clear > 150:    return "PURPLE"
    if r > 150 and g > 150 and b > 150:            return "WHITE"
    return None

# ── STUNTS WITH FULL LOGGING ──────────────────────────────────
def stunt_spinout():
    print("\n┌─ SPINOUT ──────────────────────────────")
    STATUS.on()
    for i in range(3):
        print(f"│ Cycle {i+1}/3:")
        drive(100, -100, log=True, label=f"  Phase A (fwd/back)")
        sleep_ms(300)
        drive(-100, 100, log=True, label=f"  Phase B (back/fwd)")
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

COLOR_STUNT = {
    "RED":    stunt_spinout,
    "YELLOW": stunt_donut,
    "GREEN":  stunt_zigzag,
    "PURPLE": stunt_boost,
    "WHITE":  stunt_brake,
}
MANUAL_STUNTS = [stunt_spinout, stunt_boost, stunt_zigzag,
                 stunt_donut,   stunt_brake]

# ── MAIN ─────────────────────────────────────────────────────
print("=" * 50)
print("  TinyCar Stage 4 — Stunt Debug Mode")
print("  Every motor command logged to console")
print("=" * 50)

tcs_init()
for _ in range(3):
    STATUS.on(); sleep_ms(150); STATUS.off(); sleep_ms(150)
print("Ready!\n")

stunt_idx      = 0
last_btn       = 0
last_color_chk = 0
last_stunt_t   = -3000
COOLDOWN       = 3000
last_summary   = ""

while True:
    now = ticks_ms()

    if BUTTON.value()==0 and ticks_diff(now, last_btn)>400:
        last_btn = now
        MANUAL_STUNTS[stunt_idx]()
        stunt_idx = (stunt_idx+1) % len(MANUAL_STUNTS)

    if ticks_diff(now, last_color_chk) > 120:
        last_color_chk = now
        r,g,b,clear = tcs_read()
        colour = classify_color(r,g,b,clear)
        summary = f"RGB({r:3d},{g:3d},{b:3d}) clr={clear:4d} → {colour or '---'}"
        if summary != last_summary:
            last_summary = summary
            print(summary)
        if colour and ticks_diff(now, last_stunt_t) >= COOLDOWN:
            last_stunt_t = now
            COLOR_STUNT[colour]()

    l, r = read_joystick()
    drive(l, r)
    sleep_ms(20)