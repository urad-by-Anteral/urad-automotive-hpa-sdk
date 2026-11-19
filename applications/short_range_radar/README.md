# Short Range Radar

Zone-based object detection for the uRAD Automotive HPA (AWR1843 ISK),
running on the out-of-box firmware (`out_of_box_1843_isk.bin`). The radar
streams a point cloud of CFAR detections; the host accumulates the
detections on a polar grid (range rings × azimuth sectors) and raises a
**zone alarm** after several consecutive hits in the same zone.

Typical use cases: parking assistance and blind spot warnings, proximity
alarms around vehicles or machinery, perimeter/zone surveillance, and
obstacle detection for slow-moving platforms.

The client is `urad-short-range-radar`, part of the shared
[urad-mmwave](https://github.com/urad-by-Anteral/urad-mmwave-core) SDK.

## 1. How it works

1. The **out-of-box firmware** performs the full detection chain on-chip
   (range/Doppler FFTs, CFAR in range and Doppler, angle estimation) and
   streams the detected points over UART: for each point, its Cartesian
   position (x, y, z in meters), radial velocity (m/s) and — in a second
   TLV — SNR and noise level.
2. The host converts each point to polar coordinates and keeps the points
   inside the monitored area: in front of the radar, closer than
   `--max-range` and within the field of view (`--fov`). Azimuth is
   measured from boresight (+Y), positive towards +X — the right of an
   observer standing behind the radar.
3. The points are discretized onto a **detection grid** of 1 m range
   rings (up to 10) × five 30° azimuth sectors covering ±75° around
   boresight:

   | Sector | 0 | 1 | 2 | 3 | 4 |
   |---|---|---|---|---|---|
   | Azimuth | −75…−45° | −45…−15° | −15…+15° | +15…+45° | +45…+75° |

   A field of view of 150° uses the five sectors, 90° the three central
   ones and 30° only the central one.
4. A zone accumulates one *hit* per frame that contains at least one point
   in it; a frame without points in it resets its counter. When a zone has
   been hit in `--min-hits` consecutive frames (default **4**, ≈ 0.13 s at
   30 fps) it is declared **detected** and its alarm is raised. This
   consecutive-hit filter suppresses isolated false detections.

The application keeps the standard out-of-box firmware and implements the
zone logic on the host — simple to modify, and the same firmware serves the
general point cloud demo. (TI's own *Short Range Radar* lab uses a
dedicated firmware with on-chip clustering and tracking on the AWR1642.)
The same client serves the uRAD Automotive with its own chirp
configuration.

## 2. Required firmware

Flash `out_of_box_1843_isk.bin` (from this repository's
[Releases](../../../../releases)) with TI UniFlash — the same binary used
by the out-of-box demo, so if you already ran that demo no reflash is
needed:

1. Install [TI UniFlash](https://www.ti.com/tool/UNIFLASH).
2. Put the board in **flashing mode** with the DIP switch — see chapter 3
   of the [uRAD Automotive HPA user manual](../../docs/user-manual-en.pdf)
   and [`firmware/README.md`](../../firmware/README.md).
3. Load the `.bin` and flash.
4. Restore the **functional mode** switch position and press the reset
   button.

The out-of-box firmware accepts reconfiguration at runtime: every run
starts with `sensorStop` and sends the full configuration again, so no
reset between runs is needed.

## 3. Installation

```bash
pip install "urad-mmwave[gui] @ git+https://github.com/urad-by-Anteral/urad-mmwave-core.git"
```

Drop `[gui]` if you do not need the viewer. On Raspberry Pi add the `rpi`
extra for the GPIO reset (`urad-mmwave[gui,rpi]`).

## 4. Usage

Identify the two COM ports of the board (Windows Device Manager: the
*Enhanced* CP2105 port is the control port, the *Standard* one the data
port; on Linux usually `/dev/ttyUSB0` and `/dev/ttyUSB1`) and run from this
folder:

```bash
# Live view of the grid and the zone alarms, 6 m and 150 degrees (defaults)
urad-short-range-radar --config config_radar.json --control-port COM8 --data-port COM7 --gui

# Console only, 4 m and 90 degrees, stop after 60 s
urad-short-range-radar --config config_radar.json --max-range 4 --fov 90 --duration 60

# Raspberry Pi single UART, resetting the radar through GPIO 5 first
urad-short-range-radar --config config_radar.json --single-port /dev/serial0 --gpio-reset-pin 5

# Replay a recording without hardware (2x speed)
urad-short-range-radar --replay output/PointCloud.txt --gui --replay-speed 2
```

| Option | Default | Description |
|---|---|---|
| `-c`, `--config FILE` | — | JSON configuration (serial ports and chirp file). Required unless `--replay` |
| `--replay FILE` | — | Replay a recorded `PointCloud.txt` instead of reading the radar |
| `--control-port`, `--data-port`, `--single-port` | from the JSON | Override the serial ports |
| `--chirp FILE` | from the JSON | Use another chirp configuration |
| `--max-range METERS` | 6 | Maximum detection range, up to 10 m |
| `--fov {30,90,150}` | 150 | Field of view in degrees, centered on boresight |
| `--min-hits N` | 4 | Consecutive frames a zone must be hit to raise its alarm |
| `--replay-speed X` | 1 | Replay pace; `0` = as fast as possible |
| `--output-dir DIR` | `./output` | Where the output files are written |
| `--no-save` | — | Disable file output |
| `--print-points` | — | Print every detected point |
| `--gui` | — | Live top view (requires the `gui` extra) |
| `--duration SECONDS`, `--max-frames N` | — | Stop automatically (ignored with `--gui`) |
| `--gpio-reset-pin PIN` | — | Reset the radar through a GPIO before configuring (Raspberry Pi) |

The console prints one line per frame with the number of points and, when
there are alarms, the number of detected zones and the nearest one, e.g.
`frame 412: 7 points, 2 zone(s) detected, nearest 1-2 m, -15..+15 deg`.

### Live view (`--gui`)

Top view in meters with the detection grid drawn in green (one arc per
meter and the sector boundaries inside the field of view) and the point
cloud in black, with the marker size proportional to the SNR. Every
detected zone is filled with a color that encodes proximity: **red** for
the nearest third of the monitored range, **orange** for the middle third
and **yellow** for the farthest. Close the window to stop the radar.

## 5. Radar configuration

[`config_radar.json`](config_radar.json) sets the serial ports and points
to [`chirp_config/short_range_radar.cfg`](chirp_config/short_range_radar.cfg),
a regular out-of-box configuration: start frequency 77 GHz, slope
20 MHz/µs, 384 samples per chirp at 2 Msps (≈ 4 cm range resolution),
1 Tx × 4 Rx, 32 chirps per frame, frame period 33.33 ms (30 fps), Doppler
window ±4.68 m/s and static clutter removal disabled.

Before sending it, `urad-short-range-radar` rewrites two lines from the
command line options, so the firmware only reports points inside the
monitored area:

- `aoaFovCfg -1 <-fov/2> <+fov/2> …` — azimuth limits.
- `cfarFovCfg -1 0 0 <max-range>` — range gate.

Any other out-of-box command (documented in the TI mmWave SDK user guide)
can be changed by editing the `.cfg` file or passing another one with
`--chirp`; keep an `aoaFovCfg` line and a range `cfarFovCfg` line in it.

## 6. Output files

Unless `--no-save` is given, two files are appended under `--output-dir`
(one line per frame, ending with the host epoch timestamp in seconds):

| File | Per-frame content |
|---|---|
| `PointCloud.txt` | For each point: x (m), y (m), z (m), v (m/s), SNR, noise (0.1 dB units) — then the timestamp. Frames without points are not written |
| `DetectedZones.txt` | 50 zone flags (0/1): the 10 × 5 grid flattened row by row, from the farthest ring (9–10 m) to the nearest (0–1 m), each row with sectors 0 to 4 (−75° to +75°) — then the timestamp |

`PointCloud.txt` is the input of `--replay`; in replay mode only
`DetectedZones.txt` is written, so the recording is never modified.

### Programmatic use

```python
import numpy as np
from urad_mmwave.apps.short_range_radar import GridConfig, ZoneDetector

detector = ZoneDetector(GridConfig(max_range=6, fov=150, min_hits=4))
detected = detector.update(points)  # points: (n, 6) array x, y, z, v, snr, noise
for ring, sector in np.argwhere(detected):
    print(f"alarm in ring {ring} m, sector {sector}")
```

## 7. UART/TLV protocol (for integrators)

The out-of-box firmware output (mmWave SDK 3.x demo format, little-endian):
each frame starts with a 40-byte header — magic word
`02 01 04 03 06 05 08 07`, then version, total packet length, platform,
frame number, CPU time, number of detected objects, number of TLVs and
subframe number (8 × uint32) — followed by the TLVs. The client uses:

| TLV type | Content | Payload layout |
|---|---|---|
| 1 | Detected points | Per point: x, y, z, v — 4 × float32 (16 bytes) |
| 7 | Point side info | Per point: SNR uint16, noise uint16 (0.1 dB units, 4 bytes) |

The complete out-of-box TLV list (range profile, heatmaps, statistics…) is
documented in the TI mmWave SDK user guide.

## 8. Troubleshooting

- **"The radar did not respond to any of the configuration commands"**:
  wrong control port, or the board is in flashing mode — check the DIP
  switch and the port names.
- **No frames**: check the data port and that the firmware is the
  out-of-box image; reset the board and retry.
- **Permanent alarms from static objects**: walls and fixtures inside the
  field of view produce permanent detections (clutter removal is disabled
  in the supplied configuration). Reduce `--max-range` / `--fov` to exclude
  them, or set `clutterRemoval -1 1` in the `.cfg` file to detect moving
  objects only.
- **Isolated false alarms**: raise `--min-hits`.
- **Raspberry Pi: permission or port errors**: enable the hardware UART
  (`/dev/serial0`), disable the serial console, and run with a user in the
  `dialout`/`gpio` groups.

## 9. Documentation and links

- [TI mmWave SDK](https://www.ti.com/tool/MMWAVE-SDK) user guide — the
  out-of-box demo CLI commands and full UART data format.
- [TI Radar Toolbox](https://www.ti.com/tool/RADAR-TOOLBOX) (browsable in
  the [TI Resource Explorer](https://dev.ti.com)) → *Automotive ADAS and
  Parking → Short Range Radar* — the TI lab that inspired this
  application.
- [uRAD Automotive HPA user manual](../../docs/user-manual-en.pdf)
  (flashing: chapter 3) and [Raspberry Pi adapter guide](../../docs/raspberry-pi-adapter-en.pdf).
- [urad-mmwave-core](https://github.com/urad-by-Anteral/urad-mmwave-core) —
  client source, API reference and general troubleshooting.

## Credits

Zone detection concept inspired by the **Short Range Radar** example of
the TI Radar Toolbox **4.00.00.05**; the application runs on the TI mmWave
SDK **out-of-box demo** firmware, redistributed with Texas Instruments'
authorization and subject to the applicable TI license terms. The uRAD
application code is released under the MIT License by Anteral.
