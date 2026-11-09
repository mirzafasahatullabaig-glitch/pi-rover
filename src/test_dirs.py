#!/usr/bin/env python3
# test_dirs.py — watch each motor/direction one at a time. run: python3 test_dirs.py
# Full power, 2.5s per phase, 1.5s pause. Server must be stopped first (fuser -k 5000/tcp).
import os, time
os.environ.setdefault("GPIOZERO_PIN_FACTORY", "lgpio")
from gpiozero import Motor

left  = Motor(forward=23, backward=24, enable=12, pwm=True)
right = Motor(forward=27, backward=22, enable=13, pwm=True)

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
