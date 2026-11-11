@echo off
REM One-click rover drive. Finds the Pi by mDNS (raspberrypi.local), no IP needed.
REM Server auto-starts via the rover.service systemd unit on the Pi (survives reboots).
cd /d "%~dp0"
python src\drive.py %*
