from machine import Pin, SoftI2C

i2c = SoftI2C(sda=Pin(21), scl=Pin(22), freq=400000)
devices = i2c.scan()

if devices:
    for d in devices:
        print(f"I2C device found at address: {hex(d)}")
else:
    print("No I2C devices found — check wiring")