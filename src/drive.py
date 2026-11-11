#!/usr/bin/env python3
# drive.py — WASD remote control from this Windows PC. Talks to robot_server.py on the Pi.
# run: python3 drive.py [pi_host]   (or set PI_IP env var; arg wins)
#   Default is the Pi's mDNS name, so you never chase its DHCP-floating IP.
# Keys: W forward  S reverse  A left  D right  +/- speed  E auto on/off  Q quit
# HOLD a move key to keep moving; release to stop. (Relies on OS key-repeat while held.)
import os, sys, socket, time, urllib.request, urllib.error, msvcrt

PI_HOST = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PI_IP", "raspberrypi.local")
# Resolve to IPv4: the server binds IPv4 only, but .local often resolves to IPv6 first.
try:
    PI_IP = socket.getaddrinfo(PI_HOST, 5000, socket.AF_INET)[0][4][0]
except socket.gaierror:
    sys.exit(f"Can't resolve {PI_HOST} — is the Pi on the network? Try passing its IP.")
BASE = f"http://{PI_IP}:5000/move/"

KEYS = {"w": "forward", "s": "reverse", "a": "left", "d": "right"}

TICK = 0.15          # how often we (re)send the held command; < server DEADMAN_S (0.4s)
RELEASE_S = 0.30     # no key-repeat for this long => treat key as released, stop
# shortcut: release is inferred from key-repeat gaps, upgrade to real keyup if we add a GUI/pygame

DIST_URL = f"http://{PI_IP}:5000/distance"

def send(action):
    try:
        return urllib.request.urlopen(BASE + action, timeout=1).read().decode()
    except urllib.error.HTTPError as e:
        return "  BLOCKED by obstacle" if e.code == 409 else f"  ! {action} failed: {e}"
    except Exception as e:
        return f"  ! {action} failed: {e}"

def front():
    try:
        return float(urllib.request.urlopen(DIST_URL, timeout=1).read())
    except Exception:
        return None

print(f"Driving {PI_IP}  |  hold W/A/S/D to move, release to stop, Q quit")
action = "stop"
last_key = 0.0
last_send = 0.0
last_dist = 0.0
auto = False
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
            elif ch == "e":               # toggle automatic roam
                auto = not auto
                try:
                    urllib.request.urlopen(f"http://{PI_IP}:5000/auto/{'on' if auto else 'off'}", timeout=1).read()
                except Exception as ex:
                    print("\n  ! auto toggle failed:", ex); auto = False
                print(f"\nAUTO {'ON' if auto else 'OFF'}")
            elif ch in KEYS:
                action = KEYS[ch]
                last_key = now
                auto = False              # a drive key hands control back (server also cancels auto)
        # no repeat seen recently => key released => stop
        if action != "stop" and now - last_key > RELEASE_S:
            action = "stop"
        # keep the Pi's deadman fed while moving; send stop transitions once
        if action != "stop" and now - last_send >= TICK:
            r = send(action); last_send = now
            if r and r != "OK":
                print("\n" + r)
        elif action == "stop" and last_send != 0.0:
            send("stop"); last_send = 0.0
            print("\nstop")
        # live front distance, rewriting one status line ~3x/sec
        if now - last_dist >= 0.33:
            d = front(); last_dist = now
            shown = f"{d:5.1f} cm" if d is not None else "  -- cm"
            mode = "AUTO" if auto else action
            print(f"\rfront: {shown}   [{mode}]   ", end="", flush=True)
        time.sleep(0.02)
except KeyboardInterrupt:
    pass
finally:
    send("stop")
    print("stopped, bye")
