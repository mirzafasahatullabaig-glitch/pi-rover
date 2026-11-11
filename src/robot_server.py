#!/usr/bin/env python3
# robot_server.py — Flask remote control for the 4WD rover.
# Reuses the known-good gpiozero setup from test1_motors.py (NOT RPi.GPIO, which is dead on kernel 6.18).
# Serves a web button UI at / and a command API at /move/<action>; the PC WASD client (drive.py) uses the same API.
# run: python3 robot_server.py   -> open http://<pi>:5000
import os, time, threading
os.environ.setdefault("GPIOZERO_PIN_FACTORY", "lgpio")
from gpiozero import Motor, Robot, DistanceSensor
from flask import Flask, render_template_string

SPEED = 0.6          # power cap (0..1); adjust live via /move/faster|slower
SPEED_STEP = 0.2     # +/- per faster/slower
SPEED_MIN = 0.2      # below this the motors stall (L298N-era floor, still safe for BTS7960)
DEADMAN_S = 0.4      # auto-stop if no command within this window (lost-connection safety)
STOP_CM = 20.0       # refuse forward if an obstacle is closer than this
# Automatic mode (obstacle-avoid roam), distances in cm to match distance_cm():
AUTO_STOP_CM = 25.0  # closer than this -> stop and scan
AUTO_SLOW_CM = 70.0  # start slowing from here
AUTO_SCAN_S = 5.0     # sweep each side this long, sampling for the clearest heading
AUTO_SCAN_SPEED = 0.6  # pivot power while scanning

# BTS7960 drivers (EN tied to 3.3V). forward=RPWM, backward=LPWM.
left  = Motor(forward=12, backward=16, pwm=True)  # left wheel = pins 16/12, polarity flipped
right = Motor(forward=13, backward=26, pwm=True)  # right wheel = pins 26/13, polarity flipped
robot = Robot(left=left, right=right)
sonar = DistanceSensor(echo=6, trigger=5, max_distance=2.0)

app = Flask(__name__)
_timer = None
_auto = False        # automatic-roam mode on/off

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

def distance_cm_fast():
    # Single read — for the scan sweep where we sample continuously and want it responsive.
    # Outliers just lose one candidate heading; not safety-critical like the forward stop.
    return sonar.distance * 100

def _auto_loop():
    # Roam: drive forward at a speed scaled to clearance; on a close obstacle,
    # stop, pivot-scan both sides, turn toward the more open one. Same logic as explore.py,
    # run in-process so it shares the one robot/sonar the server already owns.
    while _auto:
        d = distance_cm()
        if d <= AUTO_STOP_CM:
            robot.stop(); time.sleep(0.1)
            # Sweep 5s left then 5s right, sampling clearance the whole way.
            # Track the best (clearest) heading as a time-offset from the current pose.
            best_clear, best_t = d, 0.0
            # --- sweep left for AUTO_SCAN_S, remembering the clearest point ---
            t0 = time.monotonic(); robot.left(AUTO_SCAN_SPEED)
            while time.monotonic() - t0 < AUTO_SCAN_S and _auto:
                c = distance_cm_fast()
                if c > best_clear:                     # clearest heading so far, to our left
                    best_clear, best_t = c, -(time.monotonic() - t0)
                time.sleep(0.1)
            robot.stop(); time.sleep(0.15)
            left_end = time.monotonic() - t0           # ~AUTO_SCAN_S of left turn done
            # --- sweep right back through centre and 5s past it ---
            t1 = time.monotonic(); robot.right(AUTO_SCAN_SPEED)
            while time.monotonic() - t1 < left_end + AUTO_SCAN_S and _auto:
                c = distance_cm_fast()
                # right-of-start headings are positive offsets; centre is at t1+left_end
                off = (time.monotonic() - t1) - left_end
                if c > best_clear:
                    best_clear, best_t = c, off
                time.sleep(0.1)
            robot.stop(); time.sleep(0.15)
            if best_clear <= AUTO_STOP_CM:
                # nowhere clear in the whole sweep: back up and spin ~half a sweep to escape
                robot.backward(AUTO_SCAN_SPEED); time.sleep(0.4); robot.stop()
                if _auto:
                    robot.left(AUTO_SCAN_SPEED); time.sleep(AUTO_SCAN_S); robot.stop()
            else:
                # Now we're ~AUTO_SCAN_S to the right of start. Turn to face best_t.
                # Current heading offset = +AUTO_SCAN_S; rotate left by (AUTO_SCAN_S - best_t).
                turn_back = AUTO_SCAN_S - best_t
                if _auto and turn_back > 0:
                    robot.left(AUTO_SCAN_SPEED); time.sleep(turn_back)
            robot.stop(); time.sleep(0.1)
        else:
            # full speed when clear, tapering to 0 at AUTO_STOP_CM
            frac = 1.0 if d >= AUTO_SLOW_CM else (d - AUTO_STOP_CM) / (AUTO_SLOW_CM - AUTO_STOP_CM)
            robot.forward(round(SPEED_MIN + (SPEED - SPEED_MIN) * frac, 2))
        time.sleep(0.05)
    robot.stop()

def set_auto(on):
    global _auto
    if on and not _auto:
        _auto = True
        t = threading.Thread(target=_auto_loop, daemon=True); t.start()
    elif not on:
        _auto = False      # loop sees this, stops the robot and exits

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <title>Pi Rover</title>
    <meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no">
    <style>
        :root{
            --bg:#0f1115; --surface:#181b22; --surface-2:#20242e; --line:#2b3040;
            --ink:#eef1f6; --ink-2:#9aa3b2;
            --go:#3ddc84; --caution:#f5b300; --stop:#ff5a52; --auto:#4aa3ff;
        }
        *{box-sizing:border-box}
        body{margin:0; padding:16px; font-family:system-ui,sans-serif; background:var(--bg); color:var(--ink);
             -webkit-user-select:none; user-select:none; display:flex; flex-direction:column; align-items:center; gap:14px;}
        header{display:flex; align-items:center; gap:8px; font-weight:600; font-size:18px;}
        header .dot{width:10px; height:10px; border-radius:50%; background:var(--go); box-shadow:0 0 8px var(--go);}
        .card{width:100%; max-width:440px; background:var(--surface); border:1px solid var(--line);
              border-radius:16px; padding:14px;}
        #cam{width:100%; border-radius:12px; background:#000; aspect-ratio:3/4; object-fit:contain; display:block;}
        /* clearance meter: sequential go->caution->stop, labelled, not colour-alone */
        .meter-row{display:flex; align-items:baseline; justify-content:space-between; margin:12px 0 6px;}
        .meter-row .val{font-size:26px; font-weight:700; font-variant-numeric:tabular-nums;}
        .meter-row .val small{font-size:14px; color:var(--ink-2); font-weight:500;}
        .meter-row .lab{font-size:13px; color:var(--ink-2); text-transform:uppercase; letter-spacing:.06em;}
        .track{height:10px; border-radius:6px; background:var(--surface-2); overflow:hidden;}
        .fill{height:100%; width:0; border-radius:6px; transition:width .25s, background .25s;}
        .meta{display:flex; justify-content:space-between; margin-top:10px; font-size:13px; color:var(--ink-2);}
        .meta b{color:var(--ink); font-variant-numeric:tabular-nums;}
        .pad{display:grid; grid-template-columns:repeat(3,1fr); gap:10px;}
        .btn{appearance:none; font-size:16px; font-weight:600; padding:20px 0; border-radius:12px; cursor:pointer;
             color:var(--ink); background:var(--surface-2); border:1px solid var(--line); touch-action:none; transition:transform .05s, background .12s;}
        .btn:active{transform:scale(.96);}
        .btn.hot{background:var(--go); color:#06130b; border-color:transparent;}
        .btn.stop{color:var(--stop); border-color:var(--stop);}
        .btn.stop:active{background:var(--stop); color:#fff;}
        .btn.ghost{background:transparent;}
        .btn.auto{border-color:var(--auto); color:var(--auto);}
        .btn.auto.on{background:var(--auto); color:#04121f;}
        .sp{display:grid; grid-template-columns:1fr 1fr 1.3fr; gap:10px; margin-top:10px;}
        .hint{font-size:12px; color:var(--ink-2); text-align:center;}
    </style>
</head>
<body>
    <header><span class="dot" id="live"></span> Pi Rover</header>

    <div class="card">
        <img id="cam" alt="camera feed">
        <div class="meter-row">
            <div class="val"><span id="dist">--</span><small> cm</small></div>
            <div class="lab" id="clab">clearance</div>
        </div>
        <div class="track"><div class="fill" id="fill"></div></div>
        <div class="meta"><span>speed <b id="spd">60</b>%</span><span>mode <b id="mode">manual</b></span></div>
    </div>

    <div class="card">
        <div class="pad">
            <span></span>
            <button class="btn" data-m="forward">▲</button>
            <span></span>
            <button class="btn" data-m="left">◀</button>
            <button class="btn stop" data-m="stop">STOP</button>
            <button class="btn" data-m="right">▶</button>
            <span></span>
            <button class="btn" data-m="reverse">▼</button>
            <span></span>
        </div>
        <div class="sp">
            <button class="btn ghost" data-m="slower">– slow</button>
            <button class="btn ghost" data-m="faster">fast +</button>
            <button class="btn auto" id="autoBtn">AUTO</button>
        </div>
    </div>
    <div class="hint">hold a direction to drive · release to stop · keys W A S D / arrows · E = auto</div>

    <script>
        const $ = id => document.getElementById(id);
        $('cam').src = 'http://' + location.hostname + ':8000/stream';
        const KEYMAP = {w:'forward',s:'reverse',a:'left',d:'right',
                        ArrowUp:'forward',ArrowDown:'reverse',ArrowLeft:'left',ArrowRight:'right'};
        const C = getComputedStyle(document.documentElement);
        const GO=C.getPropertyValue('--go'), CAUTION=C.getPropertyValue('--caution'), STOP=C.getPropertyValue('--stop');
        let auto=false, online=true;

        function send(cmd){ return fetch('/move/'+cmd).then(r=>r.text()).then(t=>{
            if(t.startsWith('SPEED')) $('spd').textContent = Math.round(parseFloat(t.split(' ')[1])*100);
            mark(true);
        }).catch(()=>mark(false)); }
        function mark(ok){ if(ok!==online){ online=ok; $('live').style.background = ok?GO:STOP;
                           $('live').style.boxShadow = '0 0 8px '+(ok?GO:STOP); } }
        function setMode(){ $('mode').textContent = auto?'AUTO':'manual'; $('autoBtn').classList.toggle('on',auto); }
        function cancelAuto(){ if(auto){ auto=false; setMode(); fetch('/auto/off').catch(()=>{}); } }

        // Hold-to-drive: resend every 200ms so the server deadman (0.4s) never auto-stops mid-hold.
        let driveTimer=null, driving=null;
        function startDrive(m){ cancelAuto(); driving=m; send(m);
            clearInterval(driveTimer); driveTimer=setInterval(()=>send(m), 200); }
        function stopDrive(){ clearInterval(driveTimer); driveTimer=null; driving=null; send('stop'); }

        document.querySelectorAll('.btn[data-m]').forEach(b=>{
            const m=b.dataset.m;
            if(['faster','slower','stop'].includes(m)){ b.onclick=()=>{ if(m==='stop')stopDrive(); else {cancelAuto(); send(m);} }; return; }
            const start=e=>{ e.preventDefault(); b.classList.add('hot'); startDrive(m); };
            const end  =e=>{ e.preventDefault(); b.classList.remove('hot'); stopDrive(); };
            b.addEventListener('mousedown',start); b.addEventListener('mouseup',end); b.addEventListener('mouseleave',end);
            b.addEventListener('touchstart',start,{passive:false}); b.addEventListener('touchend',end); b.addEventListener('touchcancel',end);
        });
        $('autoBtn').onclick=()=>{ auto=!auto; setMode(); fetch('/auto/'+(auto?'on':'off')).catch(()=>mark(false)); };

        const held={};
        addEventListener('keydown',e=>{ if(e.key==='e'&&!held.e){held.e=1; $('autoBtn').click(); return;}
            const m=KEYMAP[e.key]; if(m&&!held[e.key]){ held[e.key]=1; startDrive(m);} });
        addEventListener('keyup',e=>{ if(e.key==='e')held.e=0;
            const m=KEYMAP[e.key]; if(m){ held[e.key]=0; stopDrive(); } });

        // clearance meter: 0..120cm -> 0..100% width; colour by status band, label states it too
        function paint(cm){
            const pct=Math.max(4,Math.min(100, cm/120*100));
            const f=$('fill'); f.style.width=pct+'%';
            let col,lab;
            if(cm<25){col=STOP;lab='blocked';} else if(cm<70){col=CAUTION;lab='caution';} else {col=GO;lab='clear';}
            f.style.background=col; $('clab').textContent=lab;
        }
        setInterval(()=>fetch('/distance').then(r=>r.text()).then(t=>{ $('dist').textContent=t; paint(parseFloat(t)); mark(true); })
                                          .catch(()=>mark(false)), 400);
        setMode();
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

@app.route("/auto/<state>")
def auto(state):
    if state not in ("on", "off"):
        return "use /auto/on or /auto/off", 400
    set_auto(state == "on")
    return f"AUTO {state}"

@app.route("/move/<action>")
def move(action):
    global SPEED
    if _auto and action not in ("faster", "slower"):
        set_auto(False)      # any manual drive command takes back control
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
