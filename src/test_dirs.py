#!/usr/bin/env python3
# test_dirs.py — watch each motor/direction one at a time. run: python3 test_dirs.py
# Full power, 2.5s per phase, 1.5s pause. Server must be stopped first (fuser -k 5000/tcp).
import os, time
os.environ.setdefault("GPIOZERO_PIN_FACTORY", "lgpio")
from gpiozero import Motor

# BTS7960 drivers (EN tied to 3.3V). forward=RPWM, backward=LPWM.
left  = Motor(forward=16, backward=12, pwm=True)  # pins swapped: left motor was wired reversed
right = Motor(forward=13, backward=26, pwm=True)

phases = [
    ("LEFT  forward",  left,  "forward"),
    ("LEFT  backward", left,  "backward"),
    ("RIGHT forward",  right, "forward"),
    ("RIGHT backward", right, "backward"),
]
try:
    for label, motor, direction in phases:
        print(f">>> {label}  (watch now)")
        getattr(motor, direction)(1.0)
        time.sleep(2.5)
        motor.stop()
        time.sleep(1.5)
finally:
    left.stop(); right.stop()
print("done")
