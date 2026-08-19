# Firmware

Prebuilt firmware binaries for the uRAD Automotive HPA (AWR1843 ISK) are
published as assets of this repository's [Releases](../../../releases) — they
are not stored in the git history.

| Binary | Application | Notes |
|---|---|---|
| `out_of_box_1843_isk.bin` | Out-of-box demo & Short Range Radar | Point cloud streaming; used with [urad-mmwave](https://github.com/urad-by-Anteral/urad-mmwave-core) |

## Flashing

1. Install [TI UniFlash](https://www.ti.com/tool/UNIFLASH).
2. Put the board in flashing mode (see the
   [user manual](../docs/user-manual-en.pdf) for the SOP jumper settings).
3. Load the `.bin` as *meta image* and flash.
4. Restore the functional mode jumpers and power-cycle the board.

The firmware images are built from the Texas Instruments mmWave SDK and are
redistributed for use with uRAD hardware, subject to the applicable TI
license terms.
