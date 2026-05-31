# ═══════════════════════════════════════════════════════════════
#  TinyCar — Individual Motor Direction Test
#  MicroPython v1.28 · ESP32 DevKit v1
#
#  Tests each motor individually:
#    CW  for 100ms → 2s pause → CCW for 100ms → 2s pause
#
#  Order: FR → FL → RR → RL
#
#  Watch each wheel carefully — note which direction it spins
#  for CW and CCW commands so you can confirm or fix polarity.
# ═══════════════════════════════════════════════════════════════

from machine import Pin, PWM
from utime import sleep_ms

# ── KILL PINS BEFORE PWM INIT ────────────────────────────────
# Drive all motor pins LOW as plain GPIO first.
# Prevents ESP32 boot pulse on GPIO5 from spinning motors.
for pin_num in [5, 18, 19, 23]:
    p = Pin(pin_num, Pin.OUT)
    p.value(0)

# ── MOTOR PINS ───────────────────────────────────────────────
# LF = PWM(Pin(5),  freq=1000)   # Left  Forward  (Channel A)
# LB = PWM(Pin(18), freq=1000)   # Left  Backward (Channel A)
# RF = PWM(Pin(19), freq=1000)   # Right Forward  (Channel B)
# RB = PWM(Pin(23), freq=1000)   # Right Backward (Channel B)
# Swap LF ↔ LB and RF ↔ RB assignments
LF = PWM(Pin(18), freq=1000)   # was LB
LB = PWM(Pin(5),  freq=1000)   # was LF
RF = PWM(Pin(23), freq=1000)   # was RB
RB = PWM(Pin(19), freq=1000)   # was RF

# Zero immediately — before any sleep
for p in [LF, LB, RF, RB]:
    p.duty_u16(0)

FULL = 65535   # 100% duty

def all_stop():
    for p in [LF, LB, RF, RB]:
        p.duty_u16(0)

def test_motor(name, fwd_pin, rev_pin):
    print(f"\n── {name} ──────────────────────────")
    
    print(f"  {name} → CW  (fwd_pin HIGH)")
    fwd_pin.duty_u16(FULL)
    rev_pin.duty_u16(0)
    sleep_ms(100)
    all_stop()
    print(f"  {name} → stopped — observe & note direction")
    sleep_ms(2000)

    print(f"  {name} → CCW (rev_pin HIGH)")
    fwd_pin.duty_u16(0)
    rev_pin.duty_u16(FULL)
    sleep_ms(100)
    all_stop()
    print(f"  {name} → stopped — observe & note direction")
    sleep_ms(2000)

# ── RUN TEST ─────────────────────────────────────────────────
print("=" * 44)
print("  Motor Direction Test")
print("  Watch ONE wheel at a time")
print("  Lift car off the ground first!")
print("=" * 44)

sleep_ms(3000)   # time to lift the car

# Note: FR and FL share Channel B and Channel A respectively.
# This test fires each channel independently so you see
# BOTH motors on that side move together — that is correct
# since they are wired in parallel.

# Right side — Channel B (GPIO19, GPIO23)
test_motor("FR + RR  (Right side — Channel B)", RF, RB)

# Left side — Channel A (GPIO5, GPIO18)
test_motor("FL + RL  (Left side  — Channel A)", LF, LB)

print("\n✅  Test complete.")
print("   If any side spins the wrong direction,")
print("   swap white/black on that side's OUT terminals.")