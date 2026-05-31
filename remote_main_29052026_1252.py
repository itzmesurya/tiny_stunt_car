# ═══════════════════════════════════════════════════════════════
#  TinyCar — Remote ESP32 Firmware
#  MicroPython v1.28 · ESP32 DevKit v1
#
#  Connects to a SPECIFIC car by MAC address — safe to use
#  when multiple TinyCars are nearby. Only pairs with YOUR car.
#
#  Pin Map:
#    GPIO2  → Status LED (on = BLE connected)
#    GPIO4  → Pair button (GND, internal pull-up) — reserved
#    GPIO34 → Joystick VRx (HORZ) — X axis steering
#    GPIO35 → Joystick VRy (VERT) — Y axis speed
#
#  BLE:
#    Scans for CAR_MAC below — ignores all other TinyCar devices
#    Sends L/R packets every 50ms: "L:+085,R:-032"
#    Re-scans automatically on disconnect
#
#  ⚠  Change CAR_MAC to match YOUR car's MAC address.
#     Find it on the car console at boot, or in your progress doc.
# ═══════════════════════════════════════════════════════════════

import bluetooth
from machine import Pin, ADC
from utime import sleep_ms, ticks_ms, ticks_diff
import struct

# ── TARGET CAR MAC ───────────────────────────────────────────
# Only connect to this specific ESP32. Prevents pairing with
# another TinyCar in the room.
# Format: lowercase, colon-separated
CAR_MAC = "5a:36:94:df:94:8c"   # ← car's BLE MAC (confirmed)

# ── STATUS LED + BUTTON ──────────────────────────────────────
STATUS = Pin(2, Pin.OUT)
BUTTON = Pin(4, Pin.IN, Pin.PULL_UP)

# ── JOYSTICK ─────────────────────────────────────────────────
JOY_X = ADC(Pin(34)); JOY_X.atten(ADC.ATTN_11DB)   # HORZ (VRx)
JOY_Y = ADC(Pin(35)); JOY_Y.atten(ADC.ATTN_11DB)   # VERT (VRy)

DEAD_ZONE = 30   # % — calibrated for this joystick module

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
    """Apply dead zone and remap remaining range to 0-100%."""
    if abs(v) < DEAD_ZONE: return 0
    s = 1 if v > 0 else -1
    return s * min(100, int((abs(v) - DEAD_ZONE) * 100 // (100 - DEAD_ZONE)))

def read_joystick(cx, cy):
    """
    Returns (left%, right%) each -100 to +100.
    Differential steering: y+x → left wheel, y-x → right wheel.
    """
    rx = ry = 0
    for _ in range(5):   # 5-sample average kills ADC jitter
        rx += JOY_X.read()
        ry += JOY_Y.read()
    x = max(-100, min(100, int(((rx//5 - cx) * 100 / 2047))))
    y = max(-100, min(100, int(  (ry//5 - cy) * 100 / 2047)))
    l = max(-100, min(100, _dz(y) + _dz(x)))
    r = max(-100, min(100, _dz(y) - _dz(x)))
    return l, r

# ── MAC HELPERS ──────────────────────────────────────────────
def mac_str_to_bytes(mac_str):
    """Convert 'aa:bb:cc:dd:ee:ff' → bytes (reversed for BLE addr format)."""
    parts = mac_str.split(":")
    return bytes(reversed([int(p, 16) for p in parts]))

def mac_bytes_to_str(mac_bytes):
    """Convert BLE addr bytes → 'aa:bb:cc:dd:ee:ff' string."""
    return ":".join(f"{b:02x}" for b in reversed(mac_bytes))

TARGET_MAC_BYTES = mac_str_to_bytes(CAR_MAC)

# ── BLE GATT UUIDs (must match car firmware) ─────────────────
UART_SERVICE_UUID = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
UART_TX_UUID      = bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")  # car → remote (notify)
UART_RX_UUID      = bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")  # remote → car (write)

# ── BLE STATE ────────────────────────────────────────────────
ble          = bluetooth.BLE()
ble.active(True)

_connected   = False
_conn_handle = None
_rx_handle   = None   # write handle for sending to car

def _ble_irq(event, data):
    global _connected, _conn_handle, _rx_handle

    # ── Scan result received ─────────────────────────────────
    if event == 5:   # _IRQ_SCAN_RESULT
        addr_type, addr, adv_type, rssi, adv_data = data
        found_mac = mac_bytes_to_str(bytes(addr))
        if found_mac == CAR_MAC:
            print(f"Found target car: {found_mac}  RSSI={rssi}dBm")
            ble.gap_scan(0)                         # stop scanning (0 = immediate stop)
            ble.gap_connect(addr_type, addr)        # connect to it

    # ── Scan complete (timeout) ──────────────────────────────
    elif event == 6:   # _IRQ_SCAN_DONE
        if not _connected:
            print("Scan complete — car not found. Retrying in 2s...")
            sleep_ms(2000)
            start_scan()

    # ── Connected ────────────────────────────────────────────
    elif event == 7:   # _IRQ_PERIPHERAL_CONNECT
        conn_handle, addr_type, addr = data
        _conn_handle = conn_handle
        _connected   = True
        STATUS.on()
        print("Connected! Discovering services...")
        ble.gattc_discover_services(_conn_handle)

    # ── Disconnected ─────────────────────────────────────────
    elif event == 8:   # _IRQ_PERIPHERAL_DISCONNECT
        _connected   = False
        _conn_handle = None
        _rx_handle   = None
        STATUS.off()
        print("Disconnected — scanning again...")
        sleep_ms(1000)
        start_scan()

    # ── Service discovered ───────────────────────────────────
    elif event == 9:   # _IRQ_GATTC_SERVICE_RESULT
        conn_handle, start_handle, end_handle, uuid = data
        if uuid == UART_SERVICE_UUID:
            ble.gattc_discover_characteristics(conn_handle, start_handle, end_handle)

    # ── Characteristic discovered ────────────────────────────
    elif event == 11:   # _IRQ_GATTC_CHARACTERISTIC_RESULT
        conn_handle, def_handle, value_handle, properties, uuid = data
        if uuid == UART_RX_UUID:
            _rx_handle = value_handle
            print(f"Ready to send — RX handle={_rx_handle}")
            print("Connected to TinyCar!")

    # ── Write acknowledged (ignore) ──────────────────────────
    elif event == 17:   # _IRQ_GATTC_WRITE_DONE
        pass

ble.irq(_ble_irq)

def start_scan():
    """Scan for 5 seconds, 30ms interval, 30ms window, active scan."""
    print(f"Scanning for TinyCar at {CAR_MAC} ...")
    ble.gap_scan(5000, 30000, 30000, True)

def send_packet(l, r):
    """Format and write a L/R drive packet to the car."""
    if not _connected or _rx_handle is None or _conn_handle is None:
        return
    packet = f"L:{l:+04d},R:{r:+04d}"
    try:
        ble.gattc_write(_conn_handle, _rx_handle, packet.encode(), 0)
        # mode=0: write without response — no ACK needed, no EALREADY backlog
    except OSError:
        pass   # ignore all transient BLE write errors

# ── STARTUP ──────────────────────────────────────────────────
def startup_blink(n=3):
    for _ in range(n):
        STATUS.on();  sleep_ms(150)
        STATUS.off(); sleep_ms(150)

# ── MAIN ─────────────────────────────────────────────────────
print("=" * 52)
print("  TinyCar Remote Firmware")
print(f"  Target car MAC: {CAR_MAC}")
print("=" * 52)

CX, CY = calibrate_joystick()
startup_blink()
start_scan()

# ── MAIN LOOP ────────────────────────────────────────────────
last_send = 0
SEND_INTERVAL_MS = 50   # 20Hz packet rate

while True:
    now = ticks_ms()

    if _connected and ticks_diff(now, last_send) >= SEND_INTERVAL_MS:
        last_send = now
        l, r = read_joystick(CX, CY)
        send_packet(l, r)

    sleep_ms(10)