# Short Range Radar

Zone-based object detection for the uRAD Automotive HPA (AWR1843 ISK),
running on the out-of-box firmware (`out_of_box_1843_isk.bin`). The radar
streams a point cloud of CFAR detections; the host software accumulates the
detections on a polar grid (range rings × azimuth sectors) and raises a
**zone alarm** after several consecutive hits in the same zone.

Typical use cases: parking assistance and blind spot warnings, proximity
alarms around vehicles or machinery, perimeter/zone surveillance, and
obstacle detection for slow-moving platforms.

> **Software status:** the current software is a set of legacy standalone
> scripts plus a PyQt5 desktop GUI. They predate the shared
> [urad-mmwave](https://github.com/urad-by-Anteral/urad-mmwave-core) SDK
> and will be migrated to it (with a `urad-*` command-line client) in a
> future release. Until then there is no CLI — parameters are edited at
> the top of each script or selected in the GUI.

## How it works

1. The **out-of-box firmware** performs the full detection chain on-chip
   (range/Doppler FFTs, CFAR in range and Doppler, angle estimation) and
   streams the detected points over UART: for each point, its Cartesian
   position (x, y, z in meters), radial velocity (m/s) and — in a second
   TLV — SNR and noise level.
2. The host converts each point to polar coordinates (range, azimuth),
   keeps only the points inside the selected field of view and maximum
   range, and discretizes them onto a **detection grid** of 1 m range
   rings (up to 10) × five 30° azimuth sectors covering ±75° around
   boresight.
3. A zone accumulates one *hit* per frame that contains at least one point
   in it; a miss resets its counter. When a zone exceeds **3 consecutive
   hits** (i.e. ~4 frames ≈ 0.13 s at the 30 Hz frame rate) it is declared
   **detected** and the alarm for that zone is raised. This
   consecutive-hit filter suppresses isolated false detections. The logic
   lives in [`python/object_detector.py`](python/object_detector.py)
   (`ObjectDetecter`).

Unlike the TI Automotive Toolbox *Short Range Radar* lab (which uses a
dedicated `srrdemo` firmware with on-chip clustering and tracking on the
AWR1642), the uRAD application keeps the standard out-of-box firmware and
implements the zone logic on the host — simpler to modify and the same
firmware serves the general point cloud demo.

## Required firmware

Flash `out_of_box_1843_isk.bin` (from this repository's
[Releases](../../../../releases)) with TI UniFlash — the same binary used
by the out-of-box demo, so if you already ran that demo no reflash is
needed:

1. Install [TI UniFlash](https://www.ti.com/tool/UNIFLASH).
2. Put the board in **flashing mode** with the DIP/SOP switches — see
   chapter 3 of the [uRAD Automotive HPA user manual](../../docs/user-manual-en.pdf)
   and [`firmware/README.md`](../../firmware/README.md).
3. Load the `.bin` as *meta image 1* and flash.
4. Restore the **functional mode** switch position and power-cycle.

The out-of-box firmware supports reconfiguration at runtime: the software
sends `sensorStop` when it finishes and a new run simply sends a new
configuration — no reset between runs is required. If the radar ever gets
into a bad state, reset it (USB replug, reset button, or the RESET pin —
the single-UART script drives it via GPIO on Raspberry Pi).

## Radar configuration

There is no `.cfg` chirp file: the configuration commands are embedded in
the scripts/GUI and generated from two user parameters:

| Parameter | Values | Maps to |
|---|---|---|
| `max_azimuth` — field of view | 30, 90 or 150 (degrees) | `aoaFovCfg` (±15°, ±45° or ±75° around boresight) |
| `max_range` — maximum detection range | 4, 6, 8 or 10 (meters) | `cfarFovCfg` range gate |

Fixed chirp profile (hardcoded): start frequency 77 GHz, slope 20 MHz/µs,
384 samples per chirp at 2 Msps, 32 chirps per frame, frame period
33.33 ms (~30 fps), 1 Tx × 4 Rx, Doppler window ±4.68 m/s, static clutter
removal disabled. Any command of the out-of-box CLI (documented in the TI
mmWave SDK user guide) can be adjusted by editing the `commands` list in
the scripts.

## Desktop GUI

[`gui/short_range_radar_GUI.py`](gui/short_range_radar_GUI.py) provides a
PyQt5 interface (Qt Designer layout in `gui/resources/ui/`):

```bash
pip install pyserial numpy pyqtgraph PyQt5
cd gui
python short_range_radar_GUI.py
```

> Run it from the `gui/` directory — the UI and image resources are loaded
> with relative paths.

What you get:

- **Serial port selectors** (control and data) with refresh buttons, and
  dropdowns for the maximum range and field of view. Press **Run** to
  configure the radar and start; **Stop** sends `sensorStop` and closes
  the ports.
- **Live top view** (X/Y in meters): the detection grid is drawn as green
  arcs (one per 1 m ring) and sector lines matching the selected field of
  view; detected points are black dots.
- **Zone alarms**: a detected zone is filled with a color that encodes
  proximity — **red** (nearest third of the selected range), **orange**
  (middle third) or **yellow** (farthest third).
- **Recording**: enable *Save data* and choose a file to append every
  frame's point cloud (same text format as the scripts, see below).
- **Playback**: load a previously recorded file and replay it in the same
  view, without hardware.

## Command line scripts

[`python/`](python) contains the standalone scripts. Edit the constants at
the top of the file (ports, `max_azimuth`, `max_range`, output file names,
`savePointCloud` / `saveDetectionZones` / `printPointCloud` switches) and
run with Python 3 (`pip install pyserial numpy`):

- [`short_range_radar_USB.py`](python/short_range_radar_USB.py) — dual
  UART over USB (Windows/Linux): set `configPort_name` (control, 115200
  baud) and `dataPort_name` (data, 921600 baud) and run. In Windows Device
  Manager the board enumerates as two *Silicon Labs CP210x* ports:
  *Enhanced* is the control port, *Standard* the data port; on Linux,
  `/dev/ttyUSB0` (control) and `/dev/ttyUSB1` (data).
- [`short_range_radar_single_UART.py`](python/short_range_radar_single_UART.py)
  — Raspberry Pi single-UART variant (uRAD Raspberry Pi adapter): uses
  one port (`/dev/serial0`) for configuration and data, and resets the
  chip through GPIO 5 (BCM) via `gpiozero` before configuring (set
  `reset = False` to skip). Requires `pip install gpiozero`.

Both scripts print the number of detections per frame (and optionally each
point) and append two output files under `./output_files/` (create the
directory first; one line per frame, ending with the host epoch timestamp
in seconds):

| File | Per-frame content |
|---|---|
| `PointCloud.txt` | For each point: x (m), y (m), z (m), v (m/s), SNR, noise — then timestamp |
| `DetectedZones.txt` | 50 zone flags (0/1), the 10 × 5 detection grid flattened row-major: rows from the farthest ring (9–10 m) to the nearest (0–1 m), columns from −75° to +75° in 30° sectors — then timestamp |

## UART/TLV protocol (for integrators)

The out-of-box firmware output (mmWave SDK 3.x demo format, little-endian):
each frame starts with a 40-byte header — magic word
`02 01 04 03 06 05 08 07`, then version, total packet length, platform,
frame number, CPU time, number of detected objects, number of TLVs and
subframe number (8 × uint32) — followed by the TLVs. The scripts parse:

| TLV type | Content | Payload layout |
|---|---|---|
| 1 | Detected points | Per point: x, y, z, v — 4 × float32 (16 bytes) |
| 7 | Point side info | Per point: SNR uint16, noise uint16 (0.1 dB units, 4 bytes) |

The complete out-of-box TLV list (range profile, heatmaps, statistics…) is
documented in the TI mmWave SDK user guide.

## Troubleshooting

- **No data / script waits forever**: check the data port name and baud
  rate (921600); confirm the board is in functional mode and the firmware
  is the out-of-box image.
- **Configuration errors printed on the control port**: the radar may
  already be running — the scripts always start with `flushCfg`, but if
  the sensor was left started, reset the board and retry.
- **Constant alarms from static objects**: walls and fixtures inside the
  field of view produce permanent detections (clutter removal is disabled
  by default). Reduce `max_range`/`max_azimuth` to exclude them, or enable
  `clutterRemoval` in the command list (moving-object-only detection).
- **GUI cannot find its resources**: run it from the `gui/` directory.
- **Raspberry Pi: permission or port errors**: enable the hardware UART
  (`/dev/serial0`), disable the serial console, and run with a user in the
  `dialout`/`gpio` groups.

## Documentation and links

- [TI mmWave SDK](https://www.ti.com/tool/MMWAVE-SDK) user guide — the
  out-of-box demo CLI commands and full UART data format.
- [TI Radar Toolbox](https://www.ti.com/tool/RADAR-TOOLBOX) (browsable in
  the [TI Resource Explorer](https://dev.ti.com)) → *Automotive ADAS and
  Parking → Short Range Radar* — the TI lab that inspired this
  application.
- [uRAD Automotive HPA user manual](../../docs/user-manual-en.pdf)
  (flashing: chapter 3) and [Raspberry Pi adapter guide](../../docs/raspberry-pi-adapter-en.pdf).
- [urad-mmwave-core](https://github.com/urad-by-Anteral/urad-mmwave-core) —
  the shared Python SDK these scripts will be migrated to.

## Credits

Zone detection concept inspired by the **Short Range Radar** example of
the TI Radar Toolbox **4.00.00.05**; the application runs on the TI mmWave
SDK **out-of-box demo** firmware, redistributed with Texas Instruments'
authorization and subject to the applicable TI license terms. The uRAD
application code is released under the MIT License by Anteral.
