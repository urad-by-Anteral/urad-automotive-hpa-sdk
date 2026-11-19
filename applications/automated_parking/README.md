# Automated Parking

Short and long range obstacle detection for parking with the uRAD Automotive HPA
(AWR1843), based on the **Automated Parking** lab of the TI Radar Toolbox
4.00.00.05 and the `urad-parking` client of
[urad-mmwave](https://github.com/urad-by-Anteral/urad-mmwave-core).

One radar covers **two zones at once** thanks to an *advanced frame* with
two subframes:

| Subframe | Zone | Antennas | Output |
|---|---|---|---|
| 0 — **long range 2D** | 0-50 m | TX0 + TX2 (the azimuth pair) | X-Y point cloud: vehicles and pedestrians approaching |
| 1 — **short range 3D** | 0-10 m | TX0, TX2 and TX1 (elevation) | X-Y-Z point cloud: kerbs, posts and low obstacles close to the vehicle, with their height |

Typical use cases: parking assistance and automated parking, low-speed
manoeuvring, and obstacle detection around slow vehicles or machinery.

## 1. How it works

The firmware is the mmWave SDK demo (built by TI for this lab) running the
full detection chain on the chip — range and Doppler FFTs, CFAR, angle of
arrival — once per subframe, and it streams each subframe as its own packet
in the standard mmWave SDK format, with the subframe number in the header.
`urad-parking` separates the two zones, decodes the points (position,
radial velocity, SNR and noise), the range profile of each subframe and the
nearest obstacle of the short range zone.

The HPA has the AWR1843BOOST antenna layout: 4 RX in a horizontal line, TX0 and TX2 extending the azimuth aperture (8 virtual antennas, ≈ 14°) and TX1 raised for elevation. The long range subframe uses the azimuth pair; the short range one adds TX1 for the height of each point (≈ 57°).

## 2. Required firmware

Flash `xwr18xx_mmw_demo_boost.bin` (from this repository's [Releases](../../../../releases); TI
prebuilt binary, unmodified) with TI **UniFlash**:

1. Put the board in **flashing mode** with the DIP switch (chapter 3 of the
   [uRAD Automotive HPA user manual](../../docs/user-manual-en.pdf)).
2. In UniFlash select the AWR1843 device, set the **control port**
   (*Enhanced* CP2105 port) in *Settings & Utilities*, load the `.bin` in
   *Program* and click *Load Image*.
3. Put the board back in **functional mode** and press the reset button.

## 3. Installation and usage

```bash
pip install "urad-mmwave[gui] @ git+https://github.com/urad-by-Anteral/urad-mmwave-core.git"
```

Identify the two COM ports of the board (Windows Device Manager: the
*Enhanced* CP2105 port is the control port, the *Standard* one the data
port) and run from this folder:

```bash
# Live views of both zones and the range profiles
urad-parking --config config_radar.json --control-port COM8 --data-port COM7 --gui

# Console only for 60 s
urad-parking --config config_radar.json --duration 60

# Raspberry Pi single UART, resetting the radar through GPIO 5 first
urad-parking --config config_radar.json --single-port /dev/serial0 --gpio-reset-pin 5
```

| Option | Description |
|---|---|
| `-c`, `--config FILE` | JSON configuration (serial ports and chirp file). Required |
| `--control-port`, `--data-port`, `--single-port` | Override the serial ports |
| `--chirp FILE` | Use another chirp configuration |
| `--output-dir DIR` | Where the output files are written (default `./output`) |
| `--no-save` | Disable file output |
| `--print-points` | Print every detected point |
| `--gui` | Live views (requires the `gui` extra) |
| `--duration SECONDS`, `--max-frames N` | Stop automatically (ignored with `--gui`; each subframe counts as one frame) |
| `--gpio-reset-pin PIN` | Reset the radar through a GPIO before configuring (Raspberry Pi) |

The console prints one line per subframe:

```
2D 50 m  frame 120: 14 points
3D 10 m  frame 120: 26 points, nearest obstacle 2.25 m
```

### Live view (`--gui`)

- **Long range 2D**: top view up to 50 m (the 10 m short range zone is
  outlined), marker size proportional to the SNR.
- **Short range 3D**: top view up to 10 m with every point colored by its
  height (blue below −1 m, green around 0.5 m, red above 2 m) and the
  nearest obstacle drawn as a red arc with its distance.
- **Range profiles** of both subframes at zero Doppler, in meters.

## 4. Radar configuration

[`config_radar.json`](config_radar.json) sets the serial ports and points
to [`chirp_config/automated_parking.cfg`](chirp_config/automated_parking.cfg),
TI's configuration for the AWR1843BOOST, unchanged:

| | Long range 2D (subframe 0) | Short range 3D (subframe 1) |
|---|---|---|
| Chirp | 77 GHz, 15 MHz/µs, 128 samples at 6.2 Msps | 77 GHz, 50 MHz/µs, 128 samples at 3.6 Msps |
| Maximum range (CFAR field of view) | 50 m | 0.25-8.6 m |
| Range bin | 0.48 m | 0.084 m |
| Transmitters | TX0 + TX2 (the azimuth pair) | TX0, TX2 and TX1 (elevation) |
| Doppler field of view | ±10.6 m/s | ±7.1 m/s |
| Loops / period | 128 loops, 50 ms | 128 loops, 50 ms |

The configuration uses the mmWave SDK *advanced frame* commands
(`dfeDataOutputMode 3`, `advFrameCfg`, `subFrameCfg`) and per-subframe
`cfarCfg`, `cfarFovCfg` and `guiMonitor` lines; all of them are documented
in the TI mmWave SDK user guide.

## 5. Output files

Unless `--no-save` is given, two files are appended under `--output-dir`, in
the classic uRAD point cloud format (one line per frame: `x y z v snr noise`
per point, then the host epoch timestamp; frames without points are not
written):

| File | Content |
|---|---|
| `LongRange.txt` | Long range 2D subframe (z is 0) |
| `ShortRange.txt` | Short range 3D subframe, with the height of each point |

### Programmatic use

```python
from urad_mmwave.apps.automated_parking import (
    SUBFRAME_SHORT_RANGE, nearest_obstacle, parking_frames,
)
from urad_mmwave.config import load_config
from urad_mmwave.radar import RadarSession

config = load_config("config_radar.json")
with RadarSession(config) as session:
    for frame in parking_frames(session.packets(), config.packet):
        if frame.subframe == SUBFRAME_SHORT_RANGE:
            print(frame.frame_number, nearest_obstacle(frame.points))
```

## 6. UART protocol (for integrators)

Standard mmWave SDK 3.x output format at 921600 baud: 40-byte header (sync
word `02 01 04 03 06 05 08 07`, version, total packet length, platform,
frame number, CPU time, number of points, number of TLVs, **subframe
number**), then the TLVs. Each subframe is a separate packet:

| TLV | Content | Subframes |
|---|---|---|
| 1 | Detected points: x, y, z, v (4 × float32) | both |
| 7 | Side info: SNR and noise per point (2 × uint16, 0.1 dB) | both |
| 2 | Range profile at zero Doppler (uint16 per range bin, log2 magnitude in Q9) | both |
| 3 | Noise profile | short range |
| 6 | Statistics | both |

## 7. Troubleshooting

- **"The radar did not respond to any of the configuration commands"**:
  wrong control port, the board is in flashing mode, or another firmware is
  flashed (this configuration needs `xwr18xx_mmw_demo_boost.bin`).
- **Only one zone appears**: check that the chirp file is
  `automated_parking.cfg` (two subframes) and not the out-of-box profile.
- **Permanent points from the ground or the bumper**: lower the mounting
  height or tilt the radar up a few degrees; in the short range view, the
  height color tells floor reflections (blue) from real obstacles.
- **Raspberry Pi: permission or port errors**: enable the hardware UART
  (`/dev/serial0`), disable the serial console, and run with a user in the
  `dialout`/`gpio` groups.

Links: TI Automated Parking user guide (TI Resource Explorer → Radar
Toolbox → Automotive_ADAS_and_Parking → automated_parking),
[TI mmWave SDK](https://www.ti.com/tool/MMWAVE-SDK) user guide (configuration
commands and output format), [uRAD Automotive HPA user manual](../../docs/user-manual-en.pdf),
[urad-mmwave-core](https://github.com/urad-by-Anteral/urad-mmwave-core).

## Credits

Based on the **Automated Parking** lab of the TI Radar Toolbox
**4.00.00.05** (Texas Instruments). The firmware binary and the chirp
configuration are TI's, redistributed unmodified with TI's authorization and
subject to the TI license. The uRAD client code (`urad-parking` in
[urad-mmwave-core](https://github.com/urad-by-Anteral/urad-mmwave-core)) is
released under the MIT License by Anteral.
