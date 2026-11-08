#!/usr/bin/env python3
# test3c_person_ssd.py - MobileNet-SSD person detection on Pi camera (CPU, OpenCV dnn).
# needs: models/deploy.prototxt + models/mobilenet_iter_73000.caffemodel (bash scripts/get_model.sh)
# run: python3 test3c_person_ssd.py   (Ctrl-C to stop)
import os, time, cv2
from picamera2 import Picamera2

CONF = 0.5          # min confidence to count as a person
PERSON_CLASS = 15   # MobileNet-SSD VOC class id for "person"

_M = "models" if os.path.exists("models/deploy.prototxt") else "."  # repo layout, else cwd (Pi ~)
net = cv2.dnn.readNetFromCaffe(f"{_M}/deploy.prototxt", f"{_M}/mobilenet_iter_73000.caffemodel")

cam = Picamera2()
cam.configure(cam.create_preview_configuration(main={"format": "RGB888", "size": (640, 480)}))
cam.start(); time.sleep(1)

n = 0
try:
    while True:
        frame = cv2.cvtColor(cam.capture_array(), cv2.COLOR_RGB2BGR)
        h, w = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)),
                                     0.007843, (300, 300), 127.5)
        net.setInput(blob)
        det = net.forward()
        best = 0.0
        for i in range(det.shape[2]):
            conf = float(det[0, 0, i, 2])
            if int(det[0, 0, i, 1]) == PERSON_CLASS and conf > CONF:
                best = max(best, conf)
                x1, y1, x2, y2 = (det[0, 0, i, 3:7] * [w, h, w, h]).astype(int)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        if best:
            cv2.imwrite(f"ssd_{n}.jpg", frame)
            print(f"person {best:.2f}")
        else:
            print("no person")
        n += 1
except KeyboardInterrupt:
    cam.stop(); print("done")
