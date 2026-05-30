import bluetooth
from utime import ticks_ms, ticks_diff, sleep_ms

def mac_to_str(b):
    return ":".join(f"{x:02x}" for x in reversed(b))

CAR_MAC = "5a:36:94:df:94:8c"
found = False

def irq(event, data):
    global found
    if event == 5:
        addr_type, addr, adv_type, rssi, adv_data = data
        mac = mac_to_str(bytes(addr))
        if mac == CAR_MAC:
            found = True
            print(f"FOUND! {mac}  RSSI={rssi}dBm")
            ble.gap_scan(0)

ble = bluetooth.BLE()
ble.active(True)
ble.irq(irq)
print(f"Scanning for {CAR_MAC}...")
ble.gap_scan(8000, 30000, 30000, True)

deadline = ticks_ms() + 9000
while ticks_diff(deadline, ticks_ms()) > 0 and not found:
    sleep_ms(100)

ble.active(False)
print("PASS" if found else "FAIL — car not seen")