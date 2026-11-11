# Deploy: no more IP / server-restart mess

Two pieces make the rover "just work":

## 1. PC side — one launcher, no IP
Run `rover.bat` (repo root) or `python src\drive.py`. It finds the Pi by its
mDNS name `raspberrypi.local` and resolves it to IPv4 automatically, so the
Pi's floating DHCP address never matters. Pass an IP/host as an arg to override.

## 2. Pi side — server auto-starts on boot (install once)
Installs `robot_server.py` as a systemd service that starts on boot and
restarts if it crashes — no more manual `ssh … setsid python3 …`, and it can't
be reaped by a closing ssh session. The `ExecStartPre` frees :5000 first.

Copy `rover.service` to the Pi and run, on the Pi (needs sudo):

```bash
scp deploy/rover.service altaf@raspberrypi.local:/tmp/
ssh altaf@raspberrypi.local
sudo mv /tmp/rover.service /etc/systemd/system/rover.service
sudo systemctl daemon-reload
sudo fuser -k 5000/tcp                 # drop any hand-launched server
sudo systemctl enable --now rover
systemctl status rover --no-pager      # should show active (running)
```

After this, the server is always up after a reboot. Logs: `journalctl -u rover -f`.
Stop/start manually: `sudo systemctl stop|start|restart rover`.
