#!/usr/bin/env python3
# test3b_person.py - HOG person detection on Pi camera frames.
# run: python3 test3b_person.py   (Ctrl-C to stop)
import time, cv2
from picamera2 import Picamera2

hog = cv2.HOGDescriptor()
hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

cam = Picamera2()
cam.configure(cam.create_preview_configuration(main={"format": "RGB888", "size": (640, 480)}))
cam.start(); time.sleep(1)

n = 0
try:
    while True:
        frame = cv2.cvtColor(cam.capture_array(), cv2.COLOR_RGB2BGR)
        # downscale for speed; HOG is slow at full res on the Pi CPU
        small = cv2.resize(frame, (320, 240))
        rects, _ = hog.detectMultiScale(small, winStride=(8, 8), scale=1.05)
        people = len(rects)
        print(f"people: {people}")
        if people:                       # save a labelled frame as proof
            sx, sy = 640/320, 480/240    # scale boxes back to full frame
            for (x, y, w, h) in rects:
                cv2.rectangle(frame, (int(x*sx), int(y*sy)),
                              (int((x+w)*sx), int((y+h)*sy)), (0, 255, 0), 2)
            cv2.imwrite(f"person_{n}.jpg", frame)
        n += 1
        time.sleep(0.1)
except KeyboardInterrupt:
    cam.stop(); print("done")
