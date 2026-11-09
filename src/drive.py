#!/usr/bin/env python3
# drive.py — WASD remote control from this Windows PC. Talks to robot_server.py on the Pi.
# run: python3 drive.py [pi_ip]   (default IP below; override on the command line)
# Keys: W forward  S reverse  A left  D right  SPACE/other stop  Q quit
# Each key press sends ONE command; the Pi's deadman auto-stops ~0.4s later, so tap repeatedly to keep moving.
import sys, urllib.request, msvcrt

PI_IP = sys.argv[1] if len(sys.argv) > 1 else "192.168.0.243"
BASE = f"http://{PI_IP}:5000/move/"

KEYS = {"w": "forward", "s": "reverse", "a": "left", "d": "right"}

def send(action):
    try:
        urllib.request.urlopen(BASE + action, timeout=1).read()
    except urllib.error.HTTPError as e:
        if e.code == 409:
            print("  BLOCKED by obstacle")   # forward refused: something within STOP_CM
        else:
            print(f"  ! {action} failed: {e}")
    except Exception as e:
        print(f"  ! {action} failed: {e}")

print(f"Driving {PI_IP}  |  W/A/S/D move, SPACE stop, Q quit")
try:
    while True:
        ch = msvcrt.getwch().lower()
        if ch == "q":
            break
        action = KEYS.get(ch, "stop")
        print(action)
        send(action)
finally:
    send("stop")
    print("stopped, bye")
