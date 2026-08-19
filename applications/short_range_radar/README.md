# Short Range Radar

Zone-based object detection for the uRAD Automotive HPA, running on the
out-of-box firmware (`out_of_box_1843_isk.bin`). Detections are accumulated
on a polar grid (range rings × azimuth sectors) and a zone alarm is raised
after several consecutive hits — see
[`python/object_detector.py`](python/object_detector.py).

## Desktop GUI

[`gui/short_range_radar_GUI.py`](gui/short_range_radar_GUI.py) provides a
PyQt5 interface (Qt Designer layout in `gui/resources/ui/`) with live view,
recording and playback of captures.

```bash
pip install pyserial numpy pyqtgraph PyQt5
cd gui
python short_range_radar_GUI.py
```

> Run it from the `gui/` directory — the UI and image resources are loaded
> with relative paths.

## Command line scripts

[`python/`](python) contains the standalone scripts
(`short_range_radar_USB.py`, `short_range_radar_single_UART.py`): edit the
port names at the top of the file and run. These scripts predate the shared
[urad-mmwave](https://github.com/urad-by-Anteral/urad-mmwave-core) SDK and will be
migrated to it in a future release.

## Documentation

[`docs/`](docs) contains the user guide (EN/ES).
