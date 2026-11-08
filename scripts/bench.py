#!/usr/bin/env python3
# bench.py - measure fps + CPU for SSD-every-frame vs SSD-every-Nth-frame.
# run on the Pi: python3 bench.py
import os, time, cv2
from picamera2 import Picamera2

_M = "models" if os.path.exists("models/deploy.prototxt") else "."
net = cv2.dnn.readNetFromCaffe(f"{_M}/deploy.prototxt", f"{_M}/mobilenet_iter_73000.caffemodel")
cam = Picamera2()
cam.configure(cam.create_preview_configuration(main={"format": "RGB888", "size": (640, 480)}))
cam.start(); time.sleep(1)

def run(detect_every, seconds=8):
    frames = infers = 0
    t0 = time.time(); cpu0 = os.times()  # user+sys CPU of this process
    while time.time() - t0 < seconds:
        frame = cv2.rotate(cam.capture_array(), cv2.ROTATE_90_CLOCKWISE)
        frames += 1
        if frames % detect_every == 0:
            blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)),
                                         0.007843, (300, 300), 127.5)
            net.setInput(blob); net.forward()
            infers += 1
        cv2.imencode(".jpg", frame)       # same encode cost as the stream
    dt = time.time() - t0
    c1 = os.times()
    cpu = (c1.user - cpu0.user) + (c1.system - cpu0.system)
    return frames/dt, infers/dt, 100*cpu/dt   # fps, infer/s, %CPU of one core

for every in (1, 3):
    fps, ips, cpu = run(every)
    tag = "every frame " if every == 1 else f"every {every} frames"
    print(f"DETECT_EVERY={every} ({tag}): {fps:5.1f} fps, {ips:4.1f} infer/s, CPU {cpu:5.1f}% of 1 core")

cam.stop()
