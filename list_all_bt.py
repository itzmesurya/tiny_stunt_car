import bluetooth
from utime import sleep_ms

def irq(event, data):
    if event == 5:
        addr_type, addr, adv_type, rssi, adv_data = data
        mac = ":".join(f"{x:02x}" for x in reversed(bytes(addr)))
        name = ""
        try:
            d = bytes(adv_data)
            i = 0
            while i < len(d):
                l = d[i]; t = d[i+1]
                if t == 0x09:
                    name = d[i+2:i+l+1].decode()
                i += l + 1
        except:
            pass
        print(f"{mac}  {name or '?'}")

ble = bluetooth.BLE()
ble.active(True)
ble.irq(irq)
ble.gap_scan(5000, 30000, 30000, True)
sleep_ms(6000)
ble.active(False)