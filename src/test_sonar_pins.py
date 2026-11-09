#!/usr/bin/env python3
# test_sonar_pins.py — raw HC-SR04 pin check, bypassing gpiozero DistanceSensor.
# Confirms wiring: pulses TRIG (GPIO5), times the ECHO (GPIO6) return pulse directly.
# run: python3 test_sonar_pins.py   (Ctrl-C to stop)
import os, time
os.environ.setdefault("GPIOZERO_PIN_FACTORY", "lgpio")
from gpiozero import DigitalOutputDevice, DigitalInputDevice

TRIG = DigitalOutputDevice(5)
ECHO = DigitalInputDevice(6)
SPEED = 34300.0  # cm/s, speed of sound

def ping():
    TRIG.off(); time.sleep(0.05)
    TRIG.on();  time.sleep(0.00001)  # 10us trigger pulse
    TRIG.off()
    t0 = time.time()
    # wait for echo to go high (start), with timeout
    start = time.time()
    while ECHO.value == 0:
        start = time.time()
        if start - t0 > 0.05:
            return None  # no rising edge = ECHO never went high (wiring/divider)
    # wait for echo to go low (end)
    end = time.time()
    while ECHO.value == 1:
        end = time.time()
        if end - start > 0.05:
            return -1    # stuck high = ECHO wired wrong / divider missing
    return (end - start) * SPEED / 2.0  # cm

print("TRIG=GPIO5 ECHO=GPIO6  — waving something in front should change the number")
try:
    while True:
        d = ping()
        if d is None:
            print("no echo pulse  <- ECHO not returning (check ECHO wire / divider / TRIG)")
        elif d == -1:
            print("echo stuck high  <- ECHO wiring wrong")
        else:
            print(f"{d:6.1f} cm")
        time.sleep(0.4)
except KeyboardInterrupt:
    print("\nstopped")
