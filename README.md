# pi-rover

4WD Raspberry Pi 4B rover: L298N motor control, HC-SR04 sonar, Pi Camera (OV5647)
with live MobileNet-SSD person detection streamed to the browser.

Built and tested over SSH on a Pi 4B (Raspberry Pi OS, kernel 6.18, aarch64).

## Hardware

- Raspberry Pi 4B
- L298N dual H-bridge driving 2 motors per channel (left pair / right pair)
- 4x TT gear motors
- HC-SR04 ultrasonic sensor
- Pi Camera OV5647 (CSI ribbon)
- **Bonka LiPo** motor battery (2S, 7.4V) — a stiff pack; weak/sagging packs cause
  "one side spins, the other browns out" (see Troubleshooting).

## Wiring (BCM GPIO)

| Signal            | Device        | GPIO | Pi physical |
|-------------------|---------------|------|-------------|
| Left dir          | L298N IN1     | 23   | 16 |
| Left dir          | L298N IN2     | 24   | 18 |
| Right dir         | L298N IN3     | 27   | 13 |
| Right dir         | L298N IN4     | 22   | 15 |
| Left speed (PWM)  | L298N ENA     | 12   | 32 |
| Right speed (PWM) | L298N ENB     | 13   | 33 |
| Sonar trigger     | HC-SR04 TRIG  | 5    | 29 |
| Sonar echo        | HC-SR04 ECHO  | 6    | 31 (via divider) |
| Camera            | CSI ribbon    | —    | CSI port |

Power: motors from the LiPo (VS/+12V), Pi from its own USB-C, **grounds common**
(L298N GND tied to a Pi GND pin). Remove the ENA/ENB jumpers so PWM controls speed.
Keep the L298N 5V-enable jumper ON (its regulator runs off VS).

### HC-SR04 ECHO voltage divider (required)

ECHO outputs 5V; GPIO6 tolerates 3.3V only.

```
ECHO --[ 1k ]--+-- GPIO6
               |
             [ 2k ]
               |
              GND
```
5V * 2k/(1k+2k) = 3.33V. TRIG takes 3.3V from the Pi directly, no divider.

### Camera CSI

Power off. Lift the CSI latch (between HDMI and the 3.5mm jack), insert ribbon
**blue stripe toward the 3.5mm jack**, contacts toward HDMI, press latch down.
Verify: `rpicam-hello --list-cameras` should list `ov5647`.
(Note: this camera is mounted sideways; `web_person.py` rotates frames upright.)

## Setup (on the Pi)

```bash
sudo apt install -y python3-gpiozero python3-lgpio python3-picamera2 python3-opencv python3-flask
export GPIOZERO_PIN_FACTORY=lgpio
bash scripts/get_model.sh     # downloads the MobileNet-SSD model into models/
```

## Run

Each subsystem has a standalone test — bring them up one at a time.

| File | What it does |
|------|--------------|
| `src/test1_motors.py`      | Drive each direction; confirm wiring & PWM speed |
| `src/test2_sonar.py`       | Print HC-SR04 distance in cm |
| `src/test3_cam.py`         | Capture one OpenCV frame to a JPEG |
| `src/test3b_person.py`     | HOG person detection (weak; kept for reference) |
| `src/test3c_person_ssd.py` | MobileNet-SSD person detection (the good one) |
| `src/web_person.py`        | **Live person-detection stream** at `http://<pi-ip>:8000` |

```bash
export GPIOZERO_PIN_FACTORY=lgpio
python3 src/test1_motors.py        # rover up on a box, wheels free
python3 src/web_person.py          # then open http://<pi-ip>:8000
```

Stop the web stream: `pkill -f web_person.py`

## Status

- [x] Motors (4WD, ENA/ENB hardware PWM)
- [x] Camera + live web stream
- [x] Person detection (MobileNet-SSD, ~6 fps on the Pi 4 CPU)
- [ ] HC-SR04 sonar wired
- [ ] Integrated autonomous run (motors + sonar avoidance + vision)

## Troubleshooting (things that bit us)

- **Script prints `done`, no motion:** not code — power/ground. Check VS has 7-8V,
  L298N GND tied to Pi GND, motor leads tight in OUT terminals.
- **One side spins, other dead:** battery sagging under load. A stiff LiPo fixed it;
  an L298N also wastes ~2V as heat, so feed it 7-8V minimum.
- **`people: 0` / `no person` forever:** nothing in frame. Verify with a known person
  shot; SSD at 300x300 needs a visible body. HOG (`test3b`) is much weaker than SSD.
- **Camera view looks zoomed:** the OV5647 crops the sensor at 640x480; that's the
  mode, not the code. Full-sensor mode is wider but ~half the fps.

## Performance / heat

`web_person.py` runs SSD every `DETECT_EVERY` (=3) frames and reuses boxes between.
Benchmark on the Pi 4 (`python3 scripts/bench.py`): every-frame = 8 fps @ 355% CPU;
every-3rd = 16 fps @ 239% CPU. Raise `DETECT_EVERY` for less CPU/heat (laggier box).

Keeping cool: idle ~43C under the stream — no heatsink needed, but a passive heatsink
is cheap insurance in a closed chassis. The real limiter is **power, not heat**:
`vcgencmd get_throttled` showed `0x50000` (under-voltage HAS occurred). Use a solid
5V/3A USB-C supply for the Pi; under-voltage throttles the CPU regardless of temp.
