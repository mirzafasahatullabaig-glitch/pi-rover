#!/usr/bin/env python3
# web_person.py - live MJPEG stream of SSD person detection in a browser.
# open http://<pi-ip>:8000/  from any device on the LAN.
import os, time, cv2
from picamera2 import Picamera2
from flask import Flask, Response

CONF, PERSON = 0.5, 15
ROTATE = True       # camera is mounted sideways; rotate frames upright
HOLD = 4            # keep last detection for N detect-cycles (debounce flicker)
DETECT_EVERY = 3    # run SSD every Nth frame; reuse boxes between -> ~3x less CPU

_M = "models" if os.path.exists("models/deploy.prototxt") else "."  # repo layout, else cwd (Pi ~)
net = cv2.dnn.readNetFromCaffe(f"{_M}/deploy.prototxt", f"{_M}/mobilenet_iter_73000.caffemodel")
cam = Picamera2()
cam.configure(cam.create_preview_configuration(main={"format": "RGB888", "size": (640, 480)}))
cam.start(); time.sleep(1)

app = Flask(__name__)

def frames():
    last_box, last_conf, age = None, 0.0, HOLD + 1  # memory of the last detection
    fnum = 0
    while True:
        frame = cv2.cvtColor(cam.capture_array(), cv2.COLOR_RGB2BGR)
        if ROTATE:
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        h, w = frame.shape[:2]
        fnum += 1
        if fnum % DETECT_EVERY == 0:   # only infer on every Nth frame to spare CPU
            blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)),
                                         0.007843, (300, 300), 127.5)
            net.setInput(blob); det = net.forward()
            best = 0.0
            for i in range(det.shape[2]):
                c = float(det[0, 0, i, 2])
                if int(det[0, 0, i, 1]) == PERSON and c > CONF and c > best:
                    best = c
                    last_box = (det[0, 0, i, 3:7] * [w, h, w, h]).astype(int)
            if best:                   # fresh detection: refresh memory
                last_conf, age = best, 0
            else:
                age += 1               # no detection this cycle: age the memory
        if last_box is not None and age <= HOLD:
            x1, y1, x2, y2 = last_box
            live = age == 0            # solid green if live, dim + HOLD if remembered
            col = (0, 255, 0) if live else (0, 160, 0)
            label = f"person {last_conf:.2f}" if live else "person (hold)"
            cv2.rectangle(frame, (x1, y1), (x2, y2), col, 2)
            cv2.putText(frame, label, (x1, max(y1-6, 12)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 2)
        ok, jpg = cv2.imencode(".jpg", frame)
        if ok:
            yield (b"--f\r\nContent-Type: image/jpeg\r\n\r\n" + jpg.tobytes() + b"\r\n")

@app.route("/")
def index():
    return '<html><body style="margin:0;background:#111;display:flex;' \
           'justify-content:center;align-items:center;height:100vh">' \
           '<img src="/stream" style="max-width:100%;max-height:100vh"></body></html>'

@app.route("/stream")
def stream():
    return Response(frames(), mimetype="multipart/x-mixed-replace; boundary=f")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
