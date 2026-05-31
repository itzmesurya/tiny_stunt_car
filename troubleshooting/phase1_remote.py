# ═══════════════════════════════════════════════════════════════
#  TinyCar — Phase 1 Remote Diagnostic
#  MicroPython v1.28 · ESP32 DevKit v1
#
#  Prints every joystick packet with human-readable direction.
#  Only prints when direction or values change — no console spam.
#
#  Pin Map:
#    GPIO2  → Status LED (on = BLE connected)
#    GPIO34 → Joystick VRx (HORZ)
#    GPIO35 → Joystick VRy (VERT)
# ═══════════════════════════════════════════════════════════════

import bluetooth
from machine import Pin, ADC
from utime import sleep_ms, ticks_ms, ticks_diff

# ── STATUS LED ───────────────────────────────────────────────
STATUS = Pin(2, Pin.OUT)

# ── JOYSTICK ─────────────────────────────────────────────────
JOY_X = ADC(Pin(34)); JOY_X.atten(ADC.ATTN_11DB)
JOY_Y = ADC(Pin(35)); JOY_Y.atten(ADC.ATTN_11DB)

DEAD_ZONE = 30

def calibrate_joystick():
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

def _dz(v):
    if abs(v) < DEAD_ZONE: return 0
    s = 1 if v > 0 else -1
    return s * min(100, int((abs(v) - DEAD_ZONE) * 100 // (100 - DEAD_ZONE)))

def read_joystick(cx, cy):
    rx = ry = 0
    for _ in range(5):
        rx += JOY_X.read()
        ry += JOY_Y.read()
    x = max(-100, min(100, int(((rx//5 - cx) * 100 / 2047))))
    y = max(-100, min(100, int(  (ry//5 - cy) * 100 / 2047)))
    l = max(-100, min(100, _dz(y) + _dz(x)))
    r = max(-100, min(100, _dz(y) - _dz(x)))
    return l, r

# ── DIRECTION CLASSIFIER ─────────────────────────────────────
ARC_THRESHOLD = 15   # L/R difference below this = pure fwd/rev

def classify_direction(l, r):
    if l == 0 and r == 0:
        return "STOPPED"
    # Pure spins — one side clearly opposite
    if l < 0 and r > 0:
        return "SPIN LEFT"
    if l > 0 and r < 0:
        return "SPIN RIGHT"
    # Forward family
    if l > 0 and r > 0:
        diff = l - r
        if abs(diff) < ARC_THRESHOLD:
            return "FORWARD"
        elif diff > 0:
            return "FWD + RIGHT arc"
        else:
            return "FWD + LEFT arc"
    # Reverse family
    if l < 0 and r < 0:
        diff = abs(l) - abs(r)
        if abs(diff) < ARC_THRESHOLD:
            return "REVERSE"
        elif diff > 0:
            return "REV + LEFT arc"
        else:
            return "REV + RIGHT arc"
    return "UNKNOWN"

# ── MAC + BLE ─────────────────────────────────────────────────
CAR_MAC = "5a:36:94:df:94:8c"

def mac_str_to_bytes(mac_str):
    parts = mac_str.split(":")
    return bytes(reversed([int(p, 16) for p in parts]))

def mac_bytes_to_str(mac_bytes):
    return ":".join(f"{b:02x}" for b in reversed(mac_bytes))

UART_SERVICE_UUID = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
UART_RX_UUID      = bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")

ble          = bluetooth.BLE()
ble.active(True)

_connected   = False
_connecting  = False
_conn_handle = None
_rx_handle   = None

def _ble_irq(event, data):
    global _connected, _connecting, _conn_handle, _rx_handle

    if event == 5:   # _IRQ_SCAN_RESULT
        addr_type, addr, adv_type, rssi, adv_data = data
        found_mac = mac_bytes_to_str(bytes(addr))
        if found_mac == CAR_MAC and not _connecting:
            _connecting = True
            print(f"Found car: {found_mac}  RSSI={rssi}dBm")
            ble.gap_connect(addr_type, addr)

    elif event == 6:   # _IRQ_SCAN_DONE
        if not _connected and not _connecting:
            print("Car not found — retrying in 2s...")
            sleep_ms(2000)
            start_scan()

    elif event == 7:   # _IRQ_PERIPHERAL_CONNECT
        conn_handle, addr_type, addr = data
        _conn_handle = conn_handle
        _connected   = True
        _connecting  = False
        STATUS.on()
        print("Connected! Discovering services...")
        ble.gattc_discover_services(_conn_handle)

    elif event == 8:   # _IRQ_PERIPHERAL_DISCONNECT
        _connected   = False
        _connecting  = False
        _conn_handle = None
        _rx_handle   = None
        STATUS.off()
        print("Disconnected — scanning again...")
        sleep_ms(1000)
        start_scan()

    elif event == 9:   # _IRQ_GATTC_SERVICE_RESULT
        conn_handle, start_handle, end_handle, uuid = data
        if uuid == UART_SERVICE_UUID:
            ble.gattc_discover_characteristics(conn_handle, start_handle, end_handle)

    elif event == 11:   # _IRQ_GATTC_CHARACTERISTIC_RESULT
        conn_handle, def_handle, value_handle, properties, uuid = data
        if uuid == UART_RX_UUID:
            _rx_handle = value_handle
            print(f"RX handle={_rx_handle}  — ready to send")
            print("Connected to TinyCar!\n")

    elif event == 17:
        pass

ble.irq(_ble_irq)

def start_scan():
    print(f"Scanning for {CAR_MAC} ...")
    ble.gap_scan(5000, 30000, 30000, True)

def send_packet(l, r):
    if not _connected or _rx_handle is None or _conn_handle is None:
        return
    packet = f"L:{l:+04d},R:{r:+04d}"
    try:
        ble.gattc_write(_conn_handle, _rx_handle, packet.encode(), 0)
    except OSError:
        pass

# ── STARTUP ──────────────────────────────────────────────────
def startup_blink(n=3):
    for _ in range(n):
        STATUS.on();  sleep_ms(150)
        STATUS.off(); sleep_ms(150)

# ── MAIN ─────────────────────────────────────────────────────
print("=" * 52)
print("  TinyCar Phase 1 — Remote Diagnostic")
print(f"  Target car: {CAR_MAC}")
print("=" * 52)

CX, CY = calibrate_joystick()
startup_blink()
start_scan()

# ── MAIN LOOP ────────────────────────────────────────────────
last_send      = 0
last_label     = ""
last_l         = None
last_r         = None
SEND_MS        = 50      # 20Hz send rate
PRINT_CHANGE   = True    # only print on change

while True:
    now = ticks_ms()

    if _connected and ticks_diff(now, last_send) >= SEND_MS:
        last_send = now
        l, r = read_joystick(CX, CY)
        label = classify_direction(l, r)

        # Send packet regardless
        send_packet(l, r)

        # Print only when direction label or values change
        # STOPPED only prints once on transition — not repeatedly
        if label != last_label or l != last_l or r != last_r:
            if label == "STOPPED" and last_label == "STOPPED":
                pass   # already printed STOPPED once — suppress repeats
            else:
                print(f"Remote → L:{l:+04d},R:{r:+04d}  │  {label}")
            last_label = label
            last_l     = l
            last_r     = r

    sleep_ms(10)