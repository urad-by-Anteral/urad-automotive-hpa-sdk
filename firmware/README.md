# Firmware

Prebuilt firmware binaries for the uRAD Automotive HPA (AWR1843 ISK) are
published as assets of this repository's [Releases](../../../releases) — they
are not stored in the git history.

| Binary | Application | Notes |
|---|---|---|
| `out_of_box_1843_isk.bin` | Out-of-box demo & Short Range Radar | Point cloud streaming; used with [urad-mmwave](https://github.com/urad-by-Anteral/urad-mmwave-core) |
| `xwr18xx_mrr_demo.bin` | [Medium Range Radar](../applications/medium_range_radar) | TI Radar Toolbox 4.00.00.05 prebuilt binary, unmodified; compiled-in MRR (120 m) + USRR (30 m) configuration, used with `urad-mrr` |
| `xwr18xx_mmw_demo_boost.bin` | [Automated Parking](../applications/automated_parking) | TI Radar Toolbox 4.00.00.05 prebuilt binary for the AWR1843BOOST antenna layout, unmodified; used with `urad-parking` |

## Flashing

1. Install [TI UniFlash](https://www.ti.com/tool/UNIFLASH).
2. Put the board in flashing mode (see the
   [user manual](../docs/user-manual-en.pdf) for the DIP switch settings).
3. Load the `.bin` as *meta image* and flash.
4. Restore the functional mode and press the reset button.

The firmware images are built from the Texas Instruments mmWave SDK and are
redistributed for use with uRAD hardware, subject to the applicable TI
license terms.
