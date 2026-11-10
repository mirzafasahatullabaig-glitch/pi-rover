#!/usr/bin/env python3
# drive.py — WASD remote control from this Windows PC. Talks to robot_server.py on the Pi.
# run: python3 drive.py [pi_ip]   (or set PI_IP env var; arg wins)
# Keys: W forward  S reverse  A left  D right  +/- speed up/down  Q quit
# HOLD a move key to keep moving; release to stop. (Relies on OS key-repeat while held.)
import os, sys, time, urllib.request, urllib.error, msvcrt

PI_IP = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PI_IP", "ROVER_IP_HERE")
BASE = f"http://{PI_IP}:5000/move/"

KEYS = {"w": "forward", "s": "reverse", "a": "left", "d": "right"}

TICK = 0.15          # how often we (re)send the held command; < server DEADMAN_S (0.4s)
RELEASE_S = 0.30     # no key-repeat for this long => treat key as released, stop
# shortcut: release is inferred from key-repeat gaps, upgrade to real keyup if we add a GUI/pygame

def send(action):
    try:
        return urllib.request.urlopen(BASE + action, timeout=1).read().decode()
    except urllib.error.HTTPError as e:
        return "  BLOCKED by obstacle" if e.code == 409 else f"  ! {action} failed: {e}"
    except Exception as e:
        return f"  ! {action} failed: {e}"

print(f"Driving {PI_IP}  |  hold W/A/S/D to move, release to stop, Q quit")
action = "stop"
last_key = 0.0
last_send = 0.0
try:
    while True:
        now = time.monotonic()
        # drain any pending keypresses (OS repeats these while a key is held)
        while msvcrt.kbhit():
            ch = msvcrt.getwch().lower()
            if ch == "q":
                raise KeyboardInterrupt
            if ch in ("+", "="):          # '=' is unshifted '+'
                print(send("faster"))
            elif ch == "-":
                print(send("slower"))
            elif ch in KEYS:
                action = KEYS[ch]
                last_key = now
        # no repeat seen recently => key released => stop
        if action != "stop" and now - last_key > RELEASE_S:
            action = "stop"
        # keep the Pi's deadman fed while moving; send stop transitions once
        if action != "stop" and now - last_send >= TICK:
            r = send(action); last_send = now
            if r and r != "OK":
                print(r)
        elif action == "stop" and last_send != 0.0:
            send("stop"); last_send = 0.0
            print("stop")
        time.sleep(0.02)
except KeyboardInterrupt:
    pass
finally:
    send("stop")
    print("stopped, bye")
