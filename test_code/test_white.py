from machine import Pin, SoftI2C
from utime import sleep_ms

i2c = SoftI2C(sda=Pin(21), scl=Pin(22), freq=400000)

def w(reg, val): i2c.writeto_mem(0x29, 0x80|reg, bytes([val]))
def r16(reg):
    d = i2c.readfrom_mem(0x29, 0x80|reg, 2)
    return d[0]|(d[1]<<8)

w(0x00, 0x03); w(0x01, 0xD5); w(0x0F, 0x00)
sleep_ms(120)
print("Hold WHITE card close — steady readings:\n")

while True:
    c = r16(0x14)
    if c == 0: rv=gv=bv=0
    else:
        rv = min(255, int(r16(0x16)*255/c))
        gv = min(255, int(r16(0x18)*255/c))
        bv = min(255, int(r16(0x1A)*255/c))
    print(f"RGB({rv:3d},{gv:3d},{bv:3d})  clear={c}")
    sleep_ms(800)