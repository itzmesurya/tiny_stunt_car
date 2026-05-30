# TinyCar Command Reference

## Supported Platforms

### macOS
Serial ports:
- /dev/cu.usbserial-0001
- /dev/cu.usbserial-6

### Ubuntu
Serial ports:
- /dev/ttyUSB0
- /dev/ttyUSB1
- /dev/ttyACM0
- /dev/ttyACM1

---

# 1. USB Port Detection

## macOS

List ports:

ls /dev/cu.*

Find process holding port:

lsof | grep usbserial

Kill process:

kill -9 <PID>

Identify ESP32:

python3 -m esptool --port /dev/cu.usbserial-0001 chip_id

## Ubuntu

List ports:

ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null

Watch device appear:

dmesg -w

Identify ESP32:

python3 -m esptool --port /dev/ttyUSB0 chip_id

Find process holding port:

lsof /dev/ttyUSB0

Kill process:

kill -9 <PID>

---

# 2. Install Required Tools

## macOS

pip install esptool mpremote

## Ubuntu

sudo apt update

sudo apt install python3-pip

pip3 install esptool mpremote

Add user to dialout group:

sudo usermod -aG dialout $USER

logout/login

---

# 3. Flash MicroPython

## macOS

python3 -m esptool --port /dev/cu.usbserial-0001 erase_flash

python3 -m esptool --port /dev/cu.usbserial-0001 \
  --baud 460800 write_flash -z 0x1000 micropython.bin

## Ubuntu

python3 -m esptool --port /dev/ttyUSB0 erase_flash

python3 -m esptool --port /dev/ttyUSB0 \
  --baud 460800 write_flash -z 0x1000 micropython.bin

# Ubuntu Troubleshooting

## Permission Denied

sudo usermod -aG dialout $USER

logout/login

## Port Busy

lsof /dev/ttyUSB0

kill -9 <PID>

## Device Not Found

lsusb

dmesg | tail -50

ls /dev/ttyUSB* /dev/ttyACM*