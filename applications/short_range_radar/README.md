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
| `--tx {1,2,3}` | product default | Number of transmitters: selects `short_range_radar_<N>tx.cfg` (section 5) |
| `--max-range METERS` | 6 | Maximum detection range, up to 10 m |
| `--fov {30,90,150}` | 150 | Field of view in degrees, centered on boresight |
| `--min-hits N` | 4 | Consecutive frames a zone must be hit to raise its alarm |
| `--replay-speed X` | 1 | Replay pace; `0` = as fast as possible |
| `--output-dir DIR` | `./output` | Where the output files are written (section 6) |
| `--no-save` | — | Disable file output |
| `--print-points` | — | Print every detected point |
| `--gui` | — | Live top view (requires the `gui` extra) |
| `--duration SECONDS`, `--max-frames N` | — | Stop automatically (ignored with `--gui`) |
| `--gpio-reset-pin PIN` | — | Reset the radar through a GPIO before configuring (Raspberry Pi) |

The console prints one line per frame with the number of points and, when
there are alarms, the number of detected zones, the nearest one and the
nearest detection of every sector (`-` = no alarm in that sector), plus a
line for every zone that switches on or off:

```
frame 412: 7 points, 2 zone(s) detected, nearest 1-2 m, -15..+15 deg | sectors [m]: -  -  1.42  2.31  -
  zone ON  1-2 m, -15..+15 deg
```

### Live view (`--gui`)

Top view in meters with the detection grid drawn in green (one arc per
meter and the sector boundaries inside the field of view) and the point
cloud in black, with the marker size proportional to the SNR. Every
detected zone is filled with a color that encodes proximity: **red** for
the nearest third of the monitored range, **orange** for the middle third
and **yellow** for the farthest. Each sector with an alarm shows the
distance to its nearest detection next to the outer arc. Close the window
to stop the radar.

## 5. Radar configuration and TX modes

[`config_radar.json`](config_radar.json) sets the serial ports and the
default chirp file. Each file is a regular out-of-box configuration;
choose the number of transmitters with `--tx`:

| `--tx` | File | Antennas used |
|---|---|---|
| 1 | [`short_range_radar_1tx.cfg`](chirp_config/short_range_radar_1tx.cfg) | TX0 + 4 RX |
| 2 (default) | [`short_range_radar_2tx.cfg`](chirp_config/short_range_radar_2tx.cfg) | TX0, TX2 (azimuth pair) + 4 RX |
| 3 | [`short_range_radar_3tx.cfg`](chirp_config/short_range_radar_3tx.cfg) | TX0, TX2 + TX1 (elevation) + 4 RX |

```bash
urad-short-range-radar --config config_radar.json --tx 1 --gui
```

### Antennas and angular resolution

The HPA has its **4 RX antennas in a horizontal line**, two **azimuth**
transmitters (TX0 and TX2) whose positions extend that line, and one
transmitter (TX1) raised in **elevation**. Adding TX2 doubles the azimuth
aperture — that is the "High Performance Azimuth" — and adding TX1 gives a
second row for elevation.

| Mode | Virtual array | Azimuth resolution | Elevation resolution |
|---|---|---|---|
| 1 TX | 4 in azimuth | ≈ 29° (4 antennas) | none (z = 0) |
| 2 TX | 8 in azimuth | **≈ 14°** (8 antennas) | none (z = 0) |
| 3 TX | 8 in azimuth + elevation row | ≈ 14° | ≈ 57° (2 rows) |

The 3 TX figures are those of the uRAD Automotive HPA datasheet (15° and
58°). The default is 2 TX: the finest azimuth at twice the maximum velocity
of 3 TX, since the zone detection does not use elevation.

Angular resolution at boresight is about 2/N radians (114.6°/N) for N
virtual antennas spaced λ/2 in that plane, and it widens as 1/cos θ away
from boresight (×2 at ±60°). The angle *accuracy* of a single target is
much better than the resolution; resolution is the separation needed to
see two targets of similar strength as two. The zone detection only uses
azimuth: elevation fills in z (useful to tell floor or ceiling reflections
apart), and without elevation z is always 0.

### Waveform

All three modes share one waveform, so the only difference between them is
the number of transmitters. It was chosen to give the **highest maximum
velocity that still covers 12 m with 5.9 cm range resolution** inside the
AWR1843 limits (checked with the TI mmWave Sensing Estimator 2.5.1):

| Parameter | Value | Why |
|---|---|---|
| Slope | 100 MHz/µs | chip maximum |
| Sampling | 256 complex samples at 10 Msps (25.6 µs) | 12 m needs fs ≥ slope/10 (max range = 0.8·fs·c/2·slope) |
| Ramp | idle 7 µs + ramp end 34 µs = **chirp period 41 µs** | ADC start 7 µs + 25.6 µs + 10-sample margin |
| RF | 77.0 → 80.4 GHz (2.56 GHz sampled) | within 76-81 GHz |
| Range | up to 12 m, resolution 5.9 cm | |
| Frame | 33.33 ms (30 fps); 64 loops with 1 TX, 32 loops with 2 or 3 TX | |

### Maximum velocity

With time-division MIMO the transmitters take turns, so the time between
two chirps of the *same* TX is N_TX × chirp period and the unambiguous
velocity is divided by the number of TX:

v_max = c / (4 · f_c · N_TX · T_c), with f_c = 78.98 GHz (centre of the sampled sweep) and T_c = 41 µs

| Mode | v_max (km/h) | Velocity resolution | Waveform limit (128 samples, 11.7 cm) |
|---|---|---|---|
| 1 TX | **±23.1 m/s** (83 km/h) | 0.72 m/s | ±34.4 m/s |
| 2 TX | **±11.6 m/s** (42 km/h) | 0.72 m/s | ±17.2 m/s |
| 3 TX | **±7.7 m/s** (28 km/h) | 0.48 m/s | ±11.5 m/s |

The last column is the ceiling of the chip for the same 12 m range: halving
the samples to 128 (11.7 cm range resolution) shortens the chirp to 27.8 µs.
Above v_max the Doppler wraps around. With 1 TX this only corrupts the
reported velocity; with 2 or 3 TX it also corrupts the **angle** (the
firmware compensates the TX phase with the wrong velocity), so fast targets
can land in the wrong sector. That is the price of the extra TX.

### Sensitivity

The short chirp samples 25.6 µs per chirp instead of the 192 µs of the
original Short Range Radar chirp, so each frame integrates less energy:
weak targets (a person at the far end of the grid) are detected at a
somewhat shorter distance. If the scene is slow and sensitivity matters
more than velocity, use
[`chirp_config/short_range_radar_legacy.cfg`](chirp_config/short_range_radar_legacy.cfg)
(1 TX, 20 MHz/µs, 384 samples at 2 Msps, 3.9 cm, ±4.55 m/s), the
configuration of the original scripts.

### Field of view

Before sending the file, `urad-short-range-radar` rewrites two lines from
the command line options, so the firmware only reports points inside the
monitored area:

- `aoaFovCfg -1 <-fov/2> <+fov/2> …` — azimuth limits.
- `cfarFovCfg -1 0 0 <max-range>` — range gate.

Any other out-of-box command (documented in the TI mmWave SDK user guide)
can be changed by editing a `.cfg` file or passing another one with
`--chirp`; keep an `aoaFovCfg` line and a range `cfarFovCfg` line in it.
All the files were checked with the TI mmWave Sensing Estimator 2.5.1
(xWR1843, board xWR1843BOOST): no out-of-bounds parameters.

## 6. Output files

Unless `--no-save` is given, four files are appended under `--output-dir`
(one line per frame, ending with the host epoch timestamp in seconds):

| File | Per-frame content |
|---|---|
| `PointCloud.txt` | For each point: x (m), y (m), z (m), v (m/s), SNR, noise (0.1 dB units) — then the timestamp. Frames without points are not written |
| `DetectedZones.txt` | 50 zone flags (0/1): the 10 × 5 grid flattened row by row, from the farthest ring (9–10 m) to the nearest (0–1 m), each row with sectors 0 to 4 (−75° to +75°) — then the timestamp |
| `SectorDistances.txt` | For each of the five sectors (−75° to +75°), the distance in meters to the nearest point in a **detected** zone of that sector, like a parking sensor; `-1` when the sector has no alarm — then the timestamp |
| `ZoneEvents.txt` | One line per zone that switches state: `timestamp ON\|OFF ring sector` (ring 0 = 0-1 m, sector 0 = −75…−45°) |

`PointCloud.txt` is the input of `--replay`; in replay mode it is not
written again, so the recording is never modified.

### Programmatic use

```python
from urad_mmwave.apps.short_range_radar import GridConfig, ZoneMonitor

monitor = ZoneMonitor(GridConfig(max_range=6, fov=150, min_hits=4))
result = monitor.update(points)  # points: (n, 6) array x, y, z, v, snr, noise
result.detected   # (10, 5) bool map of detected zones, ring 0 = 0-1 m
result.distances  # nearest detection per sector in meters (NaN = none)
for event in result.events:  # zones that switched on/off in this frame
    print("ON " if event.active else "OFF", event.label)
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
