#!/usr/bin/env python3
# explore.py - autonomous obstacle-avoid roaming.
# Drives forward with speed scaled to clearance; on a close obstacle it stops,
# scans left and right by pivoting, and turns toward whichever side is more open.
# Sonar is the hard safety stop. run: python3 explore.py   (Ctrl-C to stop)
import os, time, signal, sys
os.environ.setdefault("GPIOZERO_PIN_FACTORY", "lgpio")
from gpiozero import Motor, Robot, DistanceSensor

STOP_M   = 0.25   # closer than this -> stop and scan
SLOW_M   = 0.70   # start slowing down here
PIVOT_S  = 0.35   # how long to pivot while scanning each side
SETTLE_S = 0.15   # let the reading settle after a pivot before sampling

left  = Motor(forward=23, backward=24, enable=12, pwm=True)
right = Motor(forward=27, backward=22, enable=13, pwm=True)
robot = Robot(left=left, right=right)
sonar = DistanceSensor(echo=6, trigger=5, max_distance=2.0)

def cleanup(*_):
    robot.stop(); sys.exit(0)
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

def speed_for(d):
    """Full speed when clear (>=SLOW_M), 0 at STOP_M, linear between."""
    if d <= STOP_M: return 0.0
    if d >= SLOW_M: return 1.0
    return (d - STOP_M) / (SLOW_M - STOP_M)

def sample(n=3):
    """Median of a few readings in metres; robust to the odd bad ping."""
    xs = sorted(sonar.distance for _ in range(n))
    return xs[len(xs)//2]

def scan_and_turn():
    """Stop, look left and right, commit to the clearer side."""
    robot.stop(); time.sleep(0.1)
    robot.left(0.6);  time.sleep(PIVOT_S); robot.stop(); time.sleep(SETTLE_S)
    left_clear = sample()
    robot.right(0.6); time.sleep(2 * PIVOT_S); robot.stop(); time.sleep(SETTLE_S)  # swing past centre to the right
    right_clear = sample()
    # we are now pointing right; if left was clearer, swing back through centre to left
    if left_clear > right_clear:
        robot.left(0.6); time.sleep(2 * PIVOT_S)
    # else stay pointing right
    robot.stop(); time.sleep(0.05)

def main():
    while True:
        d = sample()
        if d <= STOP_M:
            scan_and_turn()
        else:
            robot.forward(speed_for(d))
        time.sleep(0.05)

if __name__ == "__main__":
    try:
        main()
    finally:
        robot.stop()
