# Medium Range Radar (MRR)

Long-range detection and tracking of vehicles and obstacles for the uRAD
Automotive HPA, using the TI Medium Range Radar firmware
(`xwr18xx_mrr_demo.bin` ([Releases](../../../../releases)), from the
TI Radar Toolbox 4.00.00.05), with the `urad-mrr` client of
[urad-mmwave](https://github.com/urad-by-Anteral/urad-mmwave-core).

The firmware time-multiplexes **two radar modes in one frame** ("advanced
frame" with two subframes), so a single sensor simultaneously provides:

| Subframe | Mode | Max range | Range resolution | Max velocity | Outputs |
|---|---|---|---|---|---|
| 0 — **MRR** (Medium Range Radar) | 3 TX beamforming, velocity disambiguation | ~120 m | ~0.7 m | ~150 km/h | Detected points + tracked objects (EKF) |
| 1 — **USRR** (Ultra Short Range Radar) | 3 TX TDM-MIMO, 12 virtual antennas | ~30 m | ~4.3 cm | ~36 km/h | Dense point cloud + DBSCAN clusters + parking assist border |

Typical use cases: forward collision awareness and adaptive-cruise-style
object tracking (MRR subframe), cross-traffic and vulnerable road user
detection, automated parking and obstacle proximity mapping (USRR
subframe).

TI designed this demo for the AWR1843BOOST evaluation board. The uRAD
Automotive HPA has the same antenna layout — 4 RX in a horizontal line,
TX0 and TX2 extending the azimuth aperture and TX1 raised for elevation,
so the USRR subframe synthesizes 8 azimuth + 4 elevation virtual antennas —
and, like the AWR1843BOOST RevB, it supplies the RF section at **1.0 V**,
which the MRR subframe needs to transmit with the three TX at once (the
firmware enables the RF LDO bypass for it).

## 1. How it works

Processing chain (runs on the on-chip C674x DSP; summary of the TI user
guide):

1. **Range FFT** per chirp, per RX antenna (1D processing).
2. **Doppler FFT** per range bin (2D processing), producing the
   range-velocity matrix.
3. **CFAR detection** in both the Doppler and range directions, plus peak
   grouping and SNR/magnitude pruning against ground clutter.
4. **Direction of arrival** (azimuth, and elevation in the USRR subframe)
   to place each detection in X-Y-Z.
5. **Velocity disambiguation** (MRR subframe only): the subframe contains
   *fast* and *slow* chirps with slightly different repetition periods;
   combining both velocity estimates through the Chinese remainder theorem
   extends the maximum unambiguous velocity to ~150 km/h.
6. **Clustering** (DBSCAN) groups the detected points into rectangles
   (center + half-extents). USRR clusters are streamed out; in cross-traffic
   scenes they outline vehicles crossing the field of view.
7. **Tracking** (MRR subframe): an Extended Kalman Filter with states
   [x, y, vx, vy] and measurements [range, radial velocity, sin(azimuth)],
   fed by the strongest object of each cluster. Tracked objects are
   streamed out with position, velocity vector and cluster size.
8. **Parking assist** (USRR subframe): the nearest obstruction distance in
   32 azimuth sectors (bins of sin(azimuth) across the full field of view,
   clamped to 20 m), forming a "parking border" arc.

## 2. Required firmware

Flash `xwr18xx_mrr_demo.bin` ([Releases](../../../../releases)), the
unmodified TI prebuilt binary, with TI **UniFlash**:

1. Put the board in **flashing mode** with the DIP switch (chapter 3 of the
   [uRAD Automotive HPA user manual](../../docs/user-manual-en.pdf)).
2. In UniFlash select the AWR1843 device, set the **control port**
   (*Enhanced* CP2105 port) in *Settings & Utilities*, load the `.bin` in
   *Program* and click *Load Image*.
3. Put the board back in **functional mode** and press the reset button.

To go back to the general point cloud demo or the Short Range Radar, flash
`out_of_box_1843_isk.bin` again.

## 3. Configuration and start-up

**There is no `.cfg` chirp file for this application.** The RF
configuration is compiled into the firmware. The prebuilt binary uses:

| Compiled-in choice | Value | Source (TI Radar Toolbox 4.00.00.05) |
|---|---|---|
| Operation mode | MRR + USRR subframes (2 subframes per frame) | `SUBFRAME_CONF_MRR_USRR` in `src/common/mrr_config_consts.h` |
| MRR chirp design | 120 m variant | `MRR_RANGE_120m` → `mrr_config_chirp_design_MRR120.h` |
| USRR chirp design | 30 m variant | `mrr_config_chirp_design_USRR30.h` |
| Frame periodicity | 30 ms MRR + 30 ms USRR (~16.7 Hz per subframe) | chirp design headers |

The firmware does not start by itself. It exposes a minimal command line
on the **control port** (115200 baud) and `urad-mrr` sends:

1. `advFrameCfg` — loads the compiled-in advanced frame configuration;
2. `sensorStart` — starts transmitting.

Detection data then flows on the **data port** (921600 baud).

**Stopping.** The firmware's `sensorStop` stops the transmission but leaves
the sensor flagged as running, so a later `sensorStart` is ignored until
the radar is reset. For that reason `urad-mrr` **leaves the sensor running
when it exits**: you can run it again straight away (on a running sensor
both start commands are no-ops). Use `--stop-on-exit` to stop the
transmission instead; the next run then needs a reset (USB replug, reset
button, or `--gpio-reset-pin` on Raspberry Pi).

To change the compiled-in configuration (MRR-only or USRR-only modes, the
80 m MRR design, the USRR20/USRR50 designs, detection thresholds), edit the
headers under
`source/ti/examples/Automotive_ADAS_and_Parking/medium_range_radar/src/`
of the TI Radar Toolbox and rebuild the firmware in Code Composer Studio —
see the "Demo Configuration" and "Building from Source Code" sections of
the TI user guide.

## 4. Running the client

```bash
pip install "urad-mmwave[gui] @ git+https://github.com/urad-by-Anteral/urad-mmwave-core.git"
```

Identify the two COM ports of the board (Windows Device Manager: the
*Enhanced* CP2105 port is the control port, the *Standard* one the data
port; on Linux usually `/dev/ttyUSB0` and `/dev/ttyUSB1`):

```bash
# Live view; ports from the command line or from config_radar.json
urad-mrr --control-port COM8 --data-port COM7 --gui
urad-mrr --config config_radar.json --gui

# Console only for 60 s, then stop the transmission
urad-mrr --config config_radar.json --duration 60 --stop-on-exit

# Raspberry Pi single UART, resetting the radar through GPIO 5 first
urad-mrr --single-port /dev/serial0 --gpio-reset-pin 5
```

| Flag | Meaning |
|---|---|
| `-c, --config PATH` | JSON profile ([`config_radar.json`](config_radar.json)) with the `control_serial` and `data_serial` ports. |
| `--control-port PORT` | Control port (115200 baud), used to start the sensor. |
| `--data-port PORT` | Data port (921600 baud). |
| `--single-port PORT` | One shared port for control and data (Raspberry Pi single-UART adapter). |
| `--no-start` | Do not send the start commands (the sensor is already running). |
| `--stop-on-exit` | Stop the transmission on exit (a reset is then needed before the next run). |
| `--baudrate N` | Data UART baud rate (default 921600, fixed by the firmware). |
| `--output-dir DIR` | Directory for the output text files (default `./output`). |
| `--no-save` | Disable all file output. |
| `--gui` | Live top-view window (requires the `gui` extra). |
| `--duration SECONDS` | Stop after this many seconds (ignored with `--gui`). |
| `--max-frames N` | Stop after N frames (each subframe counts as one frame). |
| `--gpio-reset-pin PIN` | BCM pin to reset the chip before starting (Raspberry Pi). |
| `-v, --verbose` | Debug logging (shows the radar's answers to the start commands). |

For programmatic use, iterate
`urad_mmwave.apps.medium_range_radar.stream("COM8", "COM7")` or decode
packets with `parse_frame` — see the module docstring for the frame model.

## 5. GUI

`--gui` opens a live top view (X-Y plane, radar at the origin looking up
the Y axis) drawing both subframes together:

- **Green dots** — MRR subframe detected points (long range).
- **Blue dots** — USRR subframe detected points (short range, dense).
- **Gray rectangles** — USRR DBSCAN clusters (center ± half-extents).
- **Orange squares** — MRR tracked objects, each with an orange **velocity
  vector** (the line covers the distance the object travels in 1 s) and a
  dashed box showing the associated cluster size.
- **Red arc** — parking assist border: the nearest obstruction per azimuth
  sector; sectors at exactly 20 m are free space (the firmware's clamp
  value).

The window title shows the live counts. Points, clusters and tracked
objects refresh at the subframe rate (~16 Hz each).

## 6. Output

### Console

One line per received frame:

```
MRR   points:  12  trackers: 2
USRR  points: 240  clusters: 5
```

### Files (disable with `--no-save`)

Appended in `--output-dir`, one line per frame with the host epoch
timestamp as the last value (frames with no data are skipped):

| File | Line content |
|---|---|
| `PointCloud.txt` | `subframe` (0 = MRR, 1 = USRR) then `x y z doppler peak_val` per point, then timestamp |
| `Trackers.txt` | `x y vx vy x_size y_size` per tracked object (MRR frames), then timestamp |
| `Clusters.txt` | `x_center y_center x_size y_size` per cluster (USRR frames), then timestamp |
| `ParkingAssist.txt` | 32 ranges in meters, one per azimuth bin (USRR frames), then timestamp |

Units: meters and m/s; negative doppler = approaching the radar.

### UART protocol (for integrators)

Little-endian binary stream on the data UART at **921600 baud**. Each
packet: 8-byte sync word `02 01 04 03 06 05 08 07`, then a 32-byte header,
then the TLVs, then `0x0F` padding up to a 32-byte multiple.

Header after the sync word (`uint32` each): `version`, `total_packet_len`,
`platform`, `frame_number`, `time_cpu_cycles`, `num_detected_obj`,
`num_tlvs`, `subframe_number`. **`subframe_number` selects the content: 0 =
MRR subframe, 1 = USRR subframe.**

Each TLV: `uint32 type`, `uint32 length` (length excludes this 8-byte
header), then a 4-byte descriptor `uint16 num_elements`, `uint16 q_format`
(7: divide the fixed-point values by 2^7 = 128), then the elements:

| Type | Name | Subframe | Element (little-endian) | Element size |
|---|---|---|---|---|
| 1 | Detected points | both | `int16 speed` (m/s·2^q), `uint16 peak_val`, `int16 x, y, z` (m·2^q) | 10 B |
| 2 | Clusters | USRR | `int16 x_center, y_center, x_size, y_size` (m·2^q; sizes are half-extents) | 8 B |
| 3 | Tracked objects | MRR | `int16 x, y, vx, vy` (m·2^q, m/s·2^q), `int16 x_size, y_size` (m·2^q) | 12 B |
| 4 | Parking assist | USRR | `uint16 range` (m·2^q) per azimuth bin, 32 bins | 2 B |

Parking assist bin layout: bins quantize sin(azimuth) over [-1, 1); bins
0…15 cover sin(azimuth) ∈ [0, 1) (boresight to the right), bins 16…31
cover [-1, 0) (left of boresight). A bin equal to 20 m (the maximum) means
no obstruction in that sector.

A TLV is present only when it has content (e.g. no tracked-objects TLV
when nothing is tracked); a frame can carry zero TLVs. TLV types 2–4
collide with the numbering of the standard out-of-box demo (range profile,
noise profile, azimuth heatmap) — **do not** decode this stream with an
out-of-box parser.

## 7. Troubleshooting

- **"The radar did not answer 'advFrameCfg'"** — wrong control port, the
  board is in flashing mode, or a different firmware is flashed. Swap the
  two ports if unsure; check the DIP switch and press reset.
- **No packets / timeout after ~30 s** — the sensor was stopped with
  `--stop-on-exit` (or by another tool) and the firmware cannot restart it:
  reset the radar and run again. Also check the data port.
- **Resynchronization warnings or implausible lengths** — baud rate
  mismatch (the firmware transmits at 921600) or a host UART that cannot
  sustain 921600 baud reliably (some USB-serial adapters and long cables
  drop bytes; the parser resynchronizes on the next frame).
- **Angles with a constant offset** — the firmware carries range bias and
  RX phase compensation values measured by TI; the "Range Bias and Rx
  Channel Gain/Offset Measurement and Compensation" section of the TI user
  guide describes how to measure them on a given board and rebuild the
  firmware.
- **Nothing detected at long range** — the MRR subframe is tuned for
  vehicle-sized targets (~10 m² RCS at 120 m); pedestrians and small
  objects are only visible much closer. Indoor tests mostly exercise the
  USRR subframe.

Links: TI Medium Range Radar user guide (TI Resource Explorer → Radar
Toolbox → Automotive_ADAS_and_Parking → medium_range_radar),
[TI Radar Toolbox](https://www.ti.com/tool/RADAR-TOOLBOX),
[uRAD Automotive HPA user manual](../../docs/user-manual-en.pdf),
[urad-mmwave-core](https://github.com/urad-by-Anteral/urad-mmwave-core).

## Credits

Based on the **Medium Range Radar** example of the TI Radar Toolbox
**4.00.00.05** (Texas Instruments). The firmware binary is redistributed
unmodified with TI's authorization and remains subject to the TI license.
The uRAD client code (`urad-mrr` in
[urad-mmwave-core](https://github.com/urad-by-Anteral/urad-mmwave-core)) is
released under the MIT License by Anteral.
