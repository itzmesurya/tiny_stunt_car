from machine import Pin
from utime import sleep_ms

# Motor control pins
LF = Pin(5,  Pin.OUT)   # Left  Forward
LB = Pin(18, Pin.OUT)   # Left  Backward
RF = Pin(19, Pin.OUT)   # Right Forward
RB = Pin(23, Pin.OUT)   # Right Backward

def stop_all():
    LF.off(); LB.off()
    RF.off(); RB.off()

# Make sure everything is off at start
stop_all()

print("=" * 46)
print("  TinyCar Stage 3 — Individual Motor Test")
print("  Each motor spins 10s then 3s gap")
print("  Note direction of each motor carefully")
print("=" * 46)

sleep_ms(2000)   # 2 second pause before starting

# ── TEST 1 ───────────────────────────────────
print("\nTEST 1 — LF pin HIGH (should spin Left motor FORWARD)")
print("Observe LEFT motors now...")
LF.on(); LB.off(); RF.off(); RB.off()
sleep_ms(10000)
stop_all()
print("TEST 1 done — gap")
sleep_ms(3000)

# ── TEST 2 ───────────────────────────────────
print("\nTEST 2 — LB pin HIGH (should spin Left motor BACKWARD)")
print("Observe LEFT motors now...")
LF.off(); LB.on(); RF.off(); RB.off()
sleep_ms(10000)
stop_all()
print("TEST 2 done — gap")
sleep_ms(3000)

# ── TEST 3 ───────────────────────────────────
print("\nTEST 3 — RF pin HIGH (should spin Right motor FORWARD)")
print("Observe RIGHT motors now...")
LF.off(); LB.off(); RF.on(); RB.off()
sleep_ms(10000)
stop_all()
print("TEST 3 done — gap")
sleep_ms(3000)

# ── TEST 4 ───────────────────────────────────
print("\nTEST 4 — RB pin HIGH (should spin Right motor BACKWARD)")
print("Observe RIGHT motors now...")
LF.off(); LB.off(); RF.off(); RB.on()
sleep_ms(10000)
stop_all()
print("TEST 4 done — gap")
sleep_ms(3000)

# ── TEST 5 ───────────────────────────────────
print("\nTEST 5 — ALL FORWARD (LF + RF HIGH)")
print("Observe ALL motors now...")
LF.on(); LB.off(); RF.on(); RB.off()
sleep_ms(10000)
stop_all()
print("TEST 5 done — gap")
sleep_ms(3000)

# ── TEST 6 ───────────────────────────────────
print("\nTEST 6 — ALL BACKWARD (LB + RB HIGH)")
print("Observe ALL motors now...")
LF.off(); LB.on(); RF.off(); RB.on()
sleep_ms(10000)
stop_all()

print("\n" + "=" * 46)
print("  All tests complete!")
print("  Tell me the spin direction for each test")
print("  Use: CW (clockwise) or CCW (counterclockwise)")
print("  Or: toward you / away from you")
print("=" * 46)