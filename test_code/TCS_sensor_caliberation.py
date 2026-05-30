from machine import Pin, SoftI2C
from utime import sleep_ms

TCS_ADDR   = 0x29
TCS_CMD    = 0x80
TCS_ENABLE = 0x00
TCS_ATIME  = 0x01
TCS_CONTROL= 0x0F
TCS_CDATA  = 0x14

i2c = SoftI2C(sda=Pin(21), scl=Pin(22), freq=400000)

def tcs_write(reg, val):
    i2c.writeto_mem(TCS_ADDR, TCS_CMD | reg, bytes([val]))

def tcs_read16(reg):
    d = i2c.readfrom_mem(TCS_ADDR, TCS_CMD | reg, 2)
    return d[0] | (d[1] << 8)

tcs_write(TCS_ENABLE,  0x03)
tcs_write(TCS_ATIME,   0xD5)
tcs_write(TCS_CONTROL, 0x00)
sleep_ms(120)
print("Sensor ready — hold each colour card close to sensor")
print("Readings every second\n")

while True:
    clear = tcs_read16(TCS_CDATA)
    if clear == 0:
        r = g = b = 0
    else:
        r = min(255, int(tcs_read16(TCS_CDATA + 2) * 255 / clear))
        g = min(255, int(tcs_read16(TCS_CDATA + 4) * 255 / clear))
        b = min(255, int(tcs_read16(TCS_CDATA + 6) * 255 / clear))
    print(f"RGB({r:3d},{g:3d},{b:3d})  clear={clear}")
    sleep_ms(1000)