# yocto-ros

A custom Yocto (**scarthgap**) Linux for **Raspberry Pi 5**, with **ROS 2 Jazzy** added through a separate meta-layer.

- **Base OS** (`meta-rpi-base`): SSH, Wi-Fi, Python 3 + pip + PyYAML, systemd, avahi, i2c-tools, nano, htop.
- **ROS 2** (`meta-ros-demo`): ROS 2 core, the official Python demo nodes, and `counter_demo`, Python (rclpy)
  nodes that exchange a counter (`1, 2, 3, ...`) over the `/counter` topic. A `/counter/enable` service starts and
  stops the counter.
- **Object detection** (`meta-object-detection`): the Raspberry Pi camera (libcamera) and `object_detector`, which
  runs our own trained YOLO11 model on every frame and publishes the distance to the detected object on
  `/object_distance`.
- **Buzzer** (`meta-buzzer`): `buzzer_controller`, which listens to `/object_distance` and sounds a buzzer on
  GPIO 12, loud when the object is close and quieter the farther away it is. It goes silent when nothing is detected.

```
camera ──> object_detector ──/object_distance (metres)──> buzzer_controller ──PWM──> buzzer (GPIO 12)
           (YOLO11, OpenCV DNN)                           (closer = louder)
```

## Guides

1. [Part 1: base Raspberry Pi OS with Yocto](docs/01-raspberry-pi-base-os.md): WSL, host setup, layers, SSH, flashing.
2. [Part 2: ROS 2 and the counter demo](docs/02-ros2-counter-demo.md): ROS 2 on the PC, the nodes, the meta-layer, building, testing, releases.

## Layout

```
yocto-ros/
├── layers/                          external layers (git submodules, branch scarthgap)
│   ├── poky/
│   ├── meta-openembedded/
│   ├── meta-raspberrypi/
│   └── meta-ros/
├── meta-rpi-base/                   our layer: base OS
│   ├── conf/layer.conf
│   ├── conf/templates/default/      local.conf / bblayers.conf for a new build directory
│   └── recipes-core/images/         rpi-base-image.bb
├── meta-ros-demo/                   our layer: ROS 2 additions
│   ├── conf/layer.conf
│   ├── recipes-core/images/         ros-counter-image.bb (= rpi-base-image + ROS 2)
│   └── recipes-ros/                 counter-demo (our nodes), ros-setup-profile (ROS env on login)
├── meta-object-detection/           our layer: camera + object detection
│   ├── recipes-core/images/         ros-detection-image.bb (= ros-counter-image + detector)
│   ├── recipes-multimedia/          libpisp (Pi 5 ISP library), libcamera bbappend (Raspberry Pi fork, GStreamer element)
│   ├── recipes-bsp/bootfiles/       rpi-config bbappend: dtoverlay=imx219 (camera on CAM/DISP 1)
│   └── recipes-ros/                 object-detector (the node), object-detector-service (starts it at boot)
├── meta-buzzer/                     our layer: distance buzzer
│   ├── recipes-core/images/         ros-buzzer-image.bb (= ros-detection-image + buzzer)
│   ├── recipes-bsp/bootfiles/       rpi-config bbappend: hardware PWM on GPIO 12/13
│   └── recipes-ros/                 buzzer-controller (the node), buzzer-controller-service (starts it at boot)
├── ros2_ws/src/
│   ├── counter_demo/                ROS 2 Python packages, built with colcon on the PC and by BitBake for the image
│   ├── object_detector/             (models/my_model.onnx is the trained model)
│   └── buzzer_controller/
├── tools/export_model.py            convert the trained model (.pt) to ONNX for object_detector
├── build_image.py                   build an image (and copy it out for flashing) with one command
└── setup-environment.sh             source this to get a BitBake shell
```

## Images

Each image is the previous one plus one layer.

| Image                 | Layer                   | Contents                                          |
|-----------------------|-------------------------|---------------------------------------------------|
| `rpi-base-image`      | `meta-rpi-base`         | Base OS                                           |
| `ros-counter-image`   | `meta-ros-demo`         | Base OS + ROS 2 + counter demo                    |
| `ros-detection-image` | `meta-object-detection` | + camera and `object_detector`                    |
| `ros-buzzer-image`    | `meta-buzzer`           | + `buzzer_controller` (the full system)           |

## Nodes

| Executable           | What it does                                                                  |
|----------------------|-------------------------------------------------------------------------------|
| `counter_publisher`  | Publishes `std_msgs/UInt32` on `/counter` every second; serves `/counter/enable` (`std_srvs/SetBool`) |
| `counter_subscriber` | Logs every value received on `/counter`                                       |
| `counter_controller` | `counter_controller start` or `stop`: calls `/counter/enable` once and exits  |
| `object_detector`    | Camera → YOLO11 model → publishes `std_msgs/Float32` on `/object_distance` (metres) for every frame in which the object is seen |
| `buzzer_controller`  | Subscribes to `/object_distance` and drives the buzzer: louder when closer, silent 0.5 s after the last detection |

`object_detector` and `buzzer_controller` start at boot (`systemctl status object-detector buzzer-controller`),
like the counter demo.

## Quick start (Ubuntu 24.04 / WSL)

```bash
git clone --recurse-submodules https://github.com/nvovka1/yocto-ros.git
cd yocto-ros
python3 build_image.py                       # list the images
python3 build_image.py ros-buzzer-image      # full system; or ros-counter-image, rpi-base-image
```

Or by hand: `source ./setup-environment.sh`, then `bitbake ros-buzzer-image`.

The image is written to `build/tmp/deploy/images/raspberrypi5/ros-buzzer-image-jazzy-raspberrypi5.rootfs.wic.xz`.

A build directory created **before** these layers existed keeps its old `conf/bblayers.conf` (the template is only
copied once). Add the two layers to it once:

```bash
source ./setup-environment.sh
bitbake-layers add-layer ../meta-object-detection ../meta-buzzer
```

On the board (`ssh root@raspberrypi5.local`):

```bash
ros2 launch counter_demo counter_demo.launch.py
ros2 run counter_demo counter_controller stop
ros2 run counter_demo counter_controller start
```

Ready-made images are attached to [GitHub Releases](https://github.com/nvovka1/yocto-ros/releases).

## Object detection (`meta-object-detection`)

The camera is the one from the face-recognition project: a Raspberry Pi Camera v2 (IMX219) on the **CAM/DISP 1**
connector of the Pi 5 (`dtoverlay=imx219` in `config.txt`). For CAM/DISP 0, change the overlay to `imx219,cam0`.

libcamera is **Raspberry Pi's fork** (`v0.5.2+rpt20250903`, as in Raspberry Pi OS), not upstream libcamera: upstream
expects the camera device names of the mainline kernel and finds no camera with the Raspberry Pi 6.6 kernel. OpenCV
reads the camera through libcamera's GStreamer element (`libcamerasrc`), asking for BGR frames from the Pi 5 ISP.

The model is our own YOLO11n, trained with Ultralytics (`my_model.pt`, one class: `bibi`, 640 px). PyTorch does not
run on the image, so the model is shipped as ONNX (`ros2_ws/src/object_detector/models/my_model.onnx`) and run by
OpenCV's DNN module. The ONNX export gives the same boxes and scores as Ultralytics itself.

Measured on a Raspberry Pi 5 with 2 GB: about **5 frames/s**, and about 450 MB of RAM used for the whole system
(`ros2`, both nodes, the model). The node logs its frame rate every 10 s (`journalctl -u object-detector -f`).
Ultralytics' NCNN export would be faster on the Pi, but needs NCNN recipes that no layer provides yet.

After retraining, export the new model on the PC and rebuild the image:

```bash
pip install ultralytics onnx onnxslim
python tools/export_model.py C:/MyProjects/my_model/my_model.pt
```

The script prints the model's class names. If they changed, update `class_names` and `target_class` in
`ros2_ws/src/object_detector/config/object_detector.yaml`.

### Distance

The distance comes from the size of the box: twice as far away, the box covers a quarter of the area. So
`distance = reference_distance_m × √(reference_area_fraction / area)`, where `area` is the fraction of the frame the box
covers. The reference is one measurement of your own object:

1. Put the object 1 m from the camera.
2. On the board run `journalctl -u object-detector -f` and read `area 0.0xyz of the frame`.
3. Write that number to `reference_area_fraction` in `/opt/ros/jazzy/share/object_detector/config/object_detector.yaml`
   (or in the source YAML before building), then run `systemctl restart object-detector`.

Check it: `ros2 topic echo /object_distance`.

| Parameter (`object_detector.yaml`) | Default  | Meaning                                                  |
|------------------------------------|----------|----------------------------------------------------------|
| `source`                           | `camera` | or `file:/path/to/images` to test without a camera       |
| `frame_width` × `frame_height`     | 640×480  | capture size                                             |
| `target_class`                     | `bibi`   | class whose distance is published (empty = any class)  |
| `confidence_threshold`             | 0.5      | ignore weaker detections                                 |
| `reference_distance_m`             | 1.0      | distance calibration (see above)                         |
| `reference_area_fraction`          | 0.05     | distance calibration (see above)                         |

## Buzzer (`meta-buzzer`)

### Wiring

Use a **passive** buzzer (no built-in oscillator). Its loudness is set by the duty cycle of the PWM signal, from
50 % (loudest) down to almost 0. An **active** buzzer beeps at its own fixed tone and volume and cannot do this.

| Buzzer pin | Raspberry Pi 5 header           | Signal                                     |
|------------|---------------------------------|--------------------------------------------|
| `+` / `S`  | **physical pin 32 — GPIO 12**   | hardware PWM (RP1 PWM0, channel 0), 2 kHz  |
| `−` / GND  | **physical pin 34 — GND**       | (any GND pin: 6, 9, 14, 20, 25, 30, 34, 39)|

```
         3V3  (1)  (2)  5V
                 ...
      GPIO 6 (31)  (32) GPIO 12   <- buzzer +
     GPIO 13 (33)  (34) GND       <- buzzer -
```

- A small piezo buzzer or a buzzer module (KY-006 etc.) can be connected directly; a ~100 Ω resistor in series
  protects the pin.
- A magnetic (coil) buzzer draws ~30 mA, more than a GPIO pin should supply. Drive it through an NPN transistor:
  GPIO 12 → 1 kΩ → base (S8050 / 2N2222); emitter → GND; collector → buzzer `−`; buzzer `+` → 5 V (pin 2);
  a 1N4148 diode across the buzzer (cathode to 5 V).

`meta-buzzer` adds `dtoverlay=pwm-2chan,pin=12,func=4,pin2=13,func2=4` to `config.txt`, which routes GPIO 12
(and GPIO 13, physical pin 33, free for a second buzzer as `pwm_channel: 1`) to the hardware PWM. The node finds the
RP1 PWM chip under `/sys/class/pwm` by itself.

### Volume

| Distance                     | Volume                             |
|------------------------------|------------------------------------|
| ≤ `near_distance_m` (0.3 m)  | full                               |
| between near and far         | falls in a straight line           |
| ≥ `far_distance_m` (2.0 m)   | `min_volume` (5 %, quiet)          |
| nothing detected for 0.5 s   | off                                |

Change these in `/opt/ros/jazzy/share/buzzer_controller/config/buzzer_controller.yaml`, then `systemctl restart buzzer-controller`.
`frequency_hz` sets the pitch; most passive buzzers are loudest at 2–4 kHz.

Test the buzzer without the camera by publishing distances by hand:

```bash
systemctl stop object-detector
ros2 topic pub -r 5 /object_distance std_msgs/msg/Float32 "{data: 0.3}"   # loud
ros2 topic pub -r 5 /object_distance std_msgs/msg/Float32 "{data: 1.5}"   # quiet
```

## Changing things: rebuild the image or not?

The image has no package manager, so anything that adds or replaces **software** needs a rebuild. Anything that only
changes **files** of what is already installed can be changed on the board directly. A change made only on the board
is lost at the next flash, so make the same change in this repository as well.

| Change                                              | Rebuild? | On the board                                                                                  |
|-----------------------------------------------------|----------|-----------------------------------------------------------------------------------------------|
| Parameters: calibration, volume, thresholds, pitch  | No       | Edit `/opt/ros/jazzy/share/<package>/config/<package>.yaml`, `systemctl restart <service>`    |
| Retrained model                                     | No       | `tools/export_model.py` on the PC, copy the `.onnx` to `/opt/ros/jazzy/share/object_detector/models/my_model.onnx`, restart |
| Python code of `object_detector` / `buzzer_controller` | No (to try it) | Copy the `.py` over the one in `/opt/ros/jazzy/lib/python3.12/site-packages/<package>/`, restart |
| `config.txt` line using an overlay already on the boot partition | No | Edit `/boot/config.txt`, reboot                                                     |
| New overlay (`dtoverlay=` not yet in `/boot/overlays/`) | Yes  | Add it to `RPI_KERNEL_DEVICETREE_OVERLAYS` (see `meta-buzzer/conf/layer.conf`)                |
| New ROS package, new node, new Python or system library | Yes  |                                                                                               |
| Kernel, libcamera, OpenCV, other recipes            | Yes      |                                                                                               |

`<service>` is `object-detector` or `buzzer-controller`; `<package>` is `object_detector` or `buzzer_controller`.

Copy a file from Windows to the board with `scp`, for example:

```powershell
scp ros2_ws/src/object_detector/models/my_model.onnx root@raspberrypi5.local:/opt/ros/jazzy/share/object_detector/models/
```

If `scp` fails with an SFTP error, add `-O` (the older copy protocol).

Rebuilds are incremental: BitBake only rebuilds the recipes that changed (the sstate cache keeps the rest), so after
the first build a change to our layers usually takes minutes, not hours.

## Troubleshooting

| Problem                                         | Check                                                                 |
|-------------------------------------------------|-----------------------------------------------------------------------|
| `object-detector` keeps restarting              | `journalctl -u object-detector`; `cam --list` must show the camera (ribbon cable, port) |
| `cam --list` shows no cameras                   | `dmesg \| grep -iE "imx219\|cfe"`: no `imx219` line = cable/port (CAM/DISP 1, contacts facing the right way) |
| `cam --list` shows no cameras, `imx219` is in `dmesg` | `LIBCAMERA_LOG_LEVELS=*:DEBUG cam --list`; "Unable to acquire a CFE instance" = upstream libcamera instead of the Raspberry Pi fork |
| `libcamerasrc ... not-negotiated`               | The camera pipeline must ask for a processed format (`format=BGR`); without one it gets the raw Bayer stream |
| No `/object_distance` messages                  | Object not recognised: lower `confidence_threshold`, check the light  |
| Distance is wrong                               | Redo the calibration (`reference_area_fraction`)                     |
| `No PWM chip for 1f00098000.pwm`                | `grep pwm /boot/config.txt`; `ls -l /sys/class/pwm/`; set `pwm_chip` by hand |
| Buzzer clicks but has no tone / no volume change| It is an active buzzer; use a passive one                             |

## Raspberry Pi 5 pitfalls

The first image built fine but neither the camera nor the buzzer worked on the board. Five separate problems, each
hiding the next one. The fixes are in the layers and code; this is why they are there, so they are not "simplified" away.

1. **libcamera did not recognise the camera.** The kernel saw it (`imx219` driver loaded), but `cam --list` was empty
   and `LIBCAMERA_LOG_LEVELS=*:DEBUG cam --list` said `Unable to acquire a CFE instance`. Upstream libcamera (the
   recipe in meta-ros) looks for the camera device nodes by their **mainline kernel** names, `rp1-cfe-fe-config`
   (hyphens). The Raspberry Pi 6.6 kernel calls them `rp1-cfe-fe_config` (underscores), so nothing matched.
   *Fix:* `meta-object-detection/recipes-multimedia/libcamera/libcamera_%.bbappend` builds Raspberry Pi's libcamera fork,
   the one Raspberry Pi OS uses and the reason the camera worked there. Keep libcamera and the kernel matched: a newer
   kernel with the mainline driver would need upstream libcamera again.

2. **The camera delivered raw sensor data.** With the camera found, the GStreamer pipeline stopped with
   `not-negotiated`. Without a pixel format in the caps, `libcamerasrc` offered the sensor's raw Bayer stream
   (`SBGGR16`), which `videoconvert` cannot turn into an image.
   *Fix:* `DEFAULT_CAMERA_PIPELINE` in `frame_source.py` asks for `format=BGR`. The Pi 5 ISP then delivers finished
   colour frames, already in OpenCV's channel order.

3. **The PWM pin was never switched on.** `config.txt` had `dtoverlay=pwm-2chan,...`, but meta-raspberrypi only copies
   the overlays listed in `RPI_KERNEL_DEVICETREE_OVERLAYS` onto the boot partition, and `pwm-2chan.dtbo` is not in its
   list. The firmware skips an overlay it cannot find without any error, so no PWM device appeared.
   *Fix:* `meta-buzzer/conf/layer.conf` appends `overlays/pwm-2chan.dtbo` to that list. Any new `dtoverlay=` line
   needs the same.

4. **PWM settings written in the wrong order.** A freshly exported PWM channel has `period = 0`, and the kernel rejects
   every write (`EINVAL`) while the period is 0 or shorter than the duty cycle. The code set `duty_cycle` first.
   The unit tests did not notice because their fake sysfs accepted anything.
   *Fix:* `SysfsPwmBuzzer` writes the period first. The tests' fake sysfs now rejects writes the way the kernel does.

5. **Crashed services were not restarted.** `ros2 launch` exits with status 0 even when its node crashed, so
   `Restart=on-failure` never fired and the services stayed dead after the first error.
   *Fix:* `Restart=always` in `object-detector.service` and `buzzer-controller.service`.

Problems 1 and 2 only exist on real hardware, and 3 and 4 only show on the board, so debug them there:
`ssh root@<board>`, `journalctl -u <service>`, `cam --list`, `ls -l /sys/class/pwm/`. To try a Python fix without
rebuilding the image, copy the file over the installed one under `/opt/ros/jazzy/lib/python3.12/site-packages/<package>/`
and run `systemctl restart <service>`. Then put the fix in the source and rebuild.
