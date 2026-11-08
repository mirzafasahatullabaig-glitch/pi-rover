#!/usr/bin/env python3
# test2_sonar.py — run: python3 test2_sonar.py  (Ctrl-C to stop)
import os, time
os.environ.setdefault("GPIOZERO_PIN_FACTORY", "lgpio")
from gpiozero import DistanceSensor

sonar = DistanceSensor(echo=6, trigger=5, max_distance=2.0)
try:
    while True:
        print(f"{sonar.distance*100:6.1f} cm")
        time.sleep(0.3)
except KeyboardInterrupt:
    print("\ndone")
