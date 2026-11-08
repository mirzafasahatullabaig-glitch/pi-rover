#!/usr/bin/env python3
# test3_cam.py — run: python3 test3_cam.py
import time, cv2
from picamera2 import Picamera2

cam = Picamera2()
cam.configure(cam.create_preview_configuration(main={"format": "RGB888", "size": (640, 480)}))
cam.start(); time.sleep(1)

frame = cv2.cvtColor(cam.capture_array(), cv2.COLOR_RGB2BGR)
cv2.imwrite("cv_test.jpg", frame)
print("captured", frame.shape)     # expect (480, 640, 3)
cam.stop()
