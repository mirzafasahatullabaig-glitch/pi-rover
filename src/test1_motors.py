#!/usr/bin/env python3
# test1_motors.py  — run: python3 test1_motors.py
import os, time
os.environ.setdefault("GPIOZERO_PIN_FACTORY", "lgpio")
from gpiozero import Motor, Robot

# BTS7960 drivers (EN tied to 3.3V). forward=RPWM, backward=LPWM.
left  = Motor(forward=12, backward=16, pwm=True)  # left wheel = pins 16/12, polarity flipped
right = Motor(forward=13, backward=26, pwm=True)  # right wheel = pins 26/13, polarity flipped
robot = Robot(left=left, right=right)

try:
    for name, action in [
        ("FORWARD half", lambda: robot.forward(0.5)),
        ("FORWARD full", lambda: robot.forward(1.0)),
        ("BACKWARD half", lambda: robot.backward(0.5)),
        ("TURN right",   lambda: robot.right(0.6)),
        ("TURN left",    lambda: robot.left(0.6)),
    ]:
        print(name); action(); time.sleep(1.5); robot.stop(); time.sleep(0.5)
finally:
    robot.stop()
print("done")
