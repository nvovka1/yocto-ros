# Camera (detection_camera)

A small GNOME app that shows the detector's live view, the camera frame with the detection boxes, on the
Raspberry Pi's 3.5" touch screen. It is the **Camera** icon in GNOME's dash.

It reads the MJPEG stream that `object_detector` already serves (`http://127.0.0.1:8080/stream`, see
`ros2_ws/src/object_detector/object_detector/preview_server.py`), so it needs no ROS. While the detector is starting
or restarting it shows "Waiting for camera…" and reconnects by itself. Closing the window closes the connection, and
the detector stops drawing preview frames.

| File                                         | What it is                                          |
|----------------------------------------------|-----------------------------------------------------|
| `detection_camera/mjpeg_stream.py`           | Splits the MJPEG stream into JPEG frames            |
| `detection_camera/frame_receiver.py`         | Background connection with reconnect and stop       |
| `detection_camera/app.py`                    | The GTK 4 window                                    |
| `detection-camera`                           | Launcher, installed as `/usr/bin/detection-camera`  |
| `data/io.github.nvovka1.DetectionCamera.*`   | GNOME desktop entry and icon                        |

The image recipe is `meta-touch-display/recipes-apps/detection-camera`.

## Tests (on the PC)

```bash
pip install pytest
python -m pytest apps/detection_camera
```

## Run on a PC against the board

Needs Python with PyGObject and GTK 4 (Linux):

```bash
cd apps/detection_camera
DETECTION_CAMERA_URL=http://192.168.0.101:8080/stream python3 -m detection_camera.app
```

The stream URL comes from `DETECTION_CAMERA_URL` (default `http://127.0.0.1:8080/stream`).
