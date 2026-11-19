# uRAD Automotive HPA SDK

**Official SDK for the [uRAD](https://urad.es) Automotive HPA radar by
Anteral** — a 77 GHz mmWave evaluation board based on the Texas Instruments
**AWR1843** (ISK, high-performance antenna).

*Leer en [español](README.es.md).*

## Repository layout

| Directory | Contents |
|---|---|
| [`docs/`](docs) | User manual and Raspberry Pi adapter guide (EN/ES) |
| [`mechanical/`](mechanical) | 3D model of the board (STEP) |
| [`firmware/`](firmware) | Firmware flashing guide; binaries are in [Releases](../../releases) |
| [`applications/`](applications) | Product applications (short range radar, medium range radar) |

## Quick start (out-of-box demo)

1. Flash the out-of-box firmware (`out_of_box_1843_isk.bin` from
   [Releases](../../releases)) — see [`firmware/README.md`](firmware/README.md).
2. Install the [urad-mmwave](https://github.com/urad-by-Anteral/urad-mmwave-core) Python
   SDK:

   ```bash
   pip install git+https://github.com/urad-by-Anteral/urad-mmwave-core.git
   ```

3. Run the demo with this product's profile (identify your COM ports first):

   ```bash
   urad-mmwave --config profiles/automotive-hpa/config_radar.json --data-port COM7 --control-port COM8
   ```

   Add `--gui` for the live point cloud viewer. The full configuration
   reference and troubleshooting live in the
   [urad-mmwave-core](https://github.com/urad-by-Anteral/urad-mmwave-core) README.

## Applications

### Short Range Radar

Zone-based object detection: the point cloud is accumulated on a grid of
1 m rings by 30° sectors and a zone raises an alarm after several
consecutive hits. Runs on the same out-of-box firmware, with the
`urad-short-range-radar` client of urad-mmwave (live view with `--gui`,
replay of recordings with `--replay`):

```bash
urad-short-range-radar --config applications/short_range_radar/config_radar.json --gui
```

See [`applications/short_range_radar/`](applications/short_range_radar).

### Medium Range Radar

The TI Medium Range Radar firmware on the HPA: one frame alternates a long
range subframe (up to ~120 m, three TX beamforming, tracked objects) and an
ultra short range subframe (up to ~30 m, 3-TX MIMO point cloud, clusters and
parking assist border). Flash `xwr18xx_mrr_demo.bin` from the Releases and
run the `urad-mrr` client of urad-mmwave:

```bash
urad-mrr --config applications/medium_range_radar/config_radar.json --gui
```

See [`applications/medium_range_radar/`](applications/medium_range_radar).

## Texas Instruments resources

The TI documentation previously bundled with this SDK is available from TI:
the [mmWave SDK](https://www.ti.com/tool/MMWAVE-SDK) user guide (including
the out-of-box demo UART data format) and the
[TI Resource Explorer](https://dev.ti.com).

## License

Code and documentation authored by Anteral are released under the
[MIT License](LICENSE). Texas Instruments firmware and documentation remain
subject to their respective TI licenses.
