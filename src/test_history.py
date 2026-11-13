#!/usr/bin/env python3
# Standalone check of the history logger's dedupe + rollover logic (no GPIO needed).
# Mirrors log_event() in robot_server.py; run: python3 test_history.py
import os, json, tempfile

def make_logger(path, max_bytes):
    last = [None]
    def log_event(action):
        if action == last[0]:
            return
        last[0] = action
        if os.path.exists(path) and os.path.getsize(path) >= max_bytes:
            os.replace(path, path + ".1")
        with open(path, "a") as f:
            f.write(json.dumps({"t": 0, "a": action, "cm": 50.0}) + "\n")
    return log_event

def lines(path):
    return sum(1 for _ in open(path))

def main():
    path = os.path.join(tempfile.mkdtemp(), "history.jsonl")
    log = make_logger(path, max_bytes=200)   # tiny cap to force a rollover

    log("forward"); log("forward"); log("forward")   # dedupe: repeats log once
    assert lines(path) == 1, "dedupe failed"

    log("left"); log("forward")                       # changed action logs again
    assert lines(path) == 3, "changed actions should each log"

    # Alternate two actions (never a repeat, so each logs) until the cap rolls over.
    i = 0
    while not os.path.exists(path + ".1"):
        log("left" if i % 2 == 0 else "right"); i += 1
        assert i < 100, "rollover never happened"
    assert os.path.getsize(path) < 200, "new file should be small after rollover"

    print("test_history OK")

if __name__ == "__main__":
    main()
