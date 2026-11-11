#!/usr/bin/env python3
# robot_server.py — Flask remote control for the 4WD rover.
# Reuses the known-good gpiozero setup from test1_motors.py (NOT RPi.GPIO, which is dead on kernel 6.18).
# Serves a web button UI at / and a command API at /move/<action>; the PC WASD client (drive.py) uses the same API.
# run: python3 robot_server.py   -> open http://<pi>:5000
import os, threading
os.environ.setdefault("GPIOZERO_PIN_FACTORY", "lgpio")
from gpiozero import Motor, Robot, DistanceSensor
from flask import Flask, render_template_string

SPEED = 0.6          # power cap (0..1); adjust live via /move/faster|slower
SPEED_STEP = 0.2     # +/- per faster/slower
SPEED_MIN = 0.2      # below this the motors stall (L298N-era floor, still safe for BTS7960)
DEADMAN_S = 0.4      # auto-stop if no command within this window (lost-connection safety)
STOP_CM = 20.0       # refuse forward if an obstacle is closer than this

# BTS7960 drivers (EN tied to 3.3V). forward=RPWM, backward=LPWM.
left  = Motor(forward=12, backward=16, pwm=True)  # left wheel = pins 16/12, polarity flipped
right = Motor(forward=13, backward=26, pwm=True)  # right wheel = pins 26/13, polarity flipped
robot = Robot(left=left, right=right)
sonar = DistanceSensor(echo=6, trigger=5, max_distance=2.0)

app = Flask(__name__)
_timer = None

def _arm_deadman():
    # Any sustained motion auto-stops after DEADMAN_S unless another command refreshes it.
    global _timer
    if _timer:
        _timer.cancel()
    _timer = threading.Timer(DEADMAN_S, robot.stop)
    _timer.daemon = True
    _timer.start()

def distance_cm():
    # Median of 5 reads — raw HC-SR04 on software timing spikes (stuck-high, wild outliers),
    # a single bad read must not false-trigger or miss the auto-stop.
    reads = sorted(sonar.distance * 100 for _ in range(5))
    return reads[2]

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Pi 4WD Robot Remote</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { text-align: center; font-family: sans-serif; background: #222; color: #fff; margin-top: 50px; }
        h1 { color: #4CAF50; }
        .btn { font-size: 20px; padding: 20px 30px; margin: 10px; cursor: pointer; background: #333; color: white; border: 2px solid #4CAF50; border-radius: 10px; width: 120px; }
        .btn:active { background: #4CAF50; }
        .stop { border-color: #f44336; }
        .stop:active { background: #f44336; }
        .grid { display: inline-grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 20px; }
    </style>
</head>
<body>
    <h1>4WD Robot Controller</h1>
    <p>Speed: 60%</p>
    <div class="grid">
        <div></div>
        <button class="btn" onclick="sendCommand('forward')">FORWARD</button>
        <div></div>
        <button class="btn" onclick="sendCommand('left')">LEFT</button>
        <button class="btn stop" onclick="sendCommand('stop')">STOP</button>
        <button class="btn" onclick="sendCommand('right')">RIGHT</button>
        <div></div>
        <button class="btn" onclick="sendCommand('reverse')">REVERSE</button>
        <div></div>
    </div>
    <script>
        function sendCommand(cmd) {
            fetch('/move/' + cmd).then(response => response.text());
        }
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_PAGE)

@app.route("/distance")
def distance():
    return f"{distance_cm():.1f}"

@app.route("/move/<action>")
def move(action):
    global SPEED
    if action in ("faster", "slower"):
        SPEED = round(min(1.0, max(SPEED_MIN,
                       SPEED + (SPEED_STEP if action == "faster" else -SPEED_STEP))), 2)
        return f"SPEED {SPEED}"
    if action == "forward":
        if distance_cm() < STOP_CM:
            robot.stop()
            return "BLOCKED", 409
        robot.forward(SPEED); _arm_deadman()
    elif action == "reverse":
        robot.backward(SPEED); _arm_deadman()
    elif action == "left":
        robot.left(SPEED); _arm_deadman()
    elif action == "right":
        robot.right(SPEED); _arm_deadman()
    elif action == "stop":
        if _timer:
            _timer.cancel()
        robot.stop()
    else:
        return "unknown action", 400
    return "OK"

if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5000, debug=False)
    finally:
        robot.stop()
