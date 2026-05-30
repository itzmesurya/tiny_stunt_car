# ═══════════════════════════════════════════════════════════════
#  TinyCar — Car BLE Receiver
#  MicroPython v1.28 · ESP32 DevKit v1
#
#  GATT server — advertises as 'TinyCar', receives joystick
#  packets from the remote ESP32 over BLE UART service.
#
#  Usage in main.py:
#    from car_ble_receiver import BLERemote
#    ble_remote = BLERemote()
#    ...
#    if ble_remote.connected:
#        l, r = ble_remote.get_drive()
#
#  Packet format received: "L:+085,R:-032"
# ═══════════════════════════════════════════════════════════════

import bluetooth
from micropython import const

_IRQ_CENTRAL_CONNECT    = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE        = const(3)

# Standard Nordic UART Service UUIDs — must match remote_main.py exactly
_UART_UUID = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
_TX_UUID   = bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")

_TX_CHAR = (
    _TX_UUID,
    bluetooth.FLAG_WRITE | bluetooth.FLAG_WRITE_NO_RESPONSE,
)

_UART_SERVICE = (_UART_UUID, (_TX_CHAR,),)


class BLERemote:
    def __init__(self):
        self._ble = bluetooth.BLE()
        self._ble.active(True)
        self._ble.irq(self._irq)
        ((self._rx_handle,),) = self._ble.gatts_register_services(
            (_UART_SERVICE,)
        )
        self._left      = 0
        self._right     = 0
        self._connected = False
        self._advertise()
        print("BLE: advertising as 'TinyCar'")

    def _advertise(self):
        name = b"TinyCar"
        adv  = (
            b"\x02\x01\x06"
            + bytes([1 + len(name)]) + b"\x09" + name
        )
        try:
            self._ble.gap_advertise(100_000, adv)
        except OSError:
            pass   # BLE stack briefly busy after disconnect — safe to ignore

    def _irq(self, event, data):
        if event == _IRQ_CENTRAL_CONNECT:
            self._connected = True
            print("BLE: remote connected!")
        elif event == _IRQ_CENTRAL_DISCONNECT:
            self._connected = False
            self._left = self._right = 0
            print("BLE: remote disconnected — motors stopped")
            self._advertise()
        elif event == _IRQ_GATTS_WRITE:
            buf = self._ble.gatts_read(self._rx_handle)
            self._parse(buf)

    def _parse(self, buf):
        try:
            s     = buf.decode()
            parts = s.split(",")
            self._left  = int(parts[0].split(":")[1])
            self._right = int(parts[1].split(":")[1])
        except:
            pass

    def get_drive(self):
        return self._left, self._right

    @property
    def connected(self):
        return self._connected