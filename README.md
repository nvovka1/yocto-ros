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
│   ├── recipes-multimedia/          libpisp (Pi 5 ISP library), libcamera bbappend (Pi 5 pipeline, GStreamer element)
│   ├── recipes-bsp/bootfiles/       rpi-config bbappend: camera_auto_detect=1
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

The camera is the one from the face-recognition project: a Raspberry Pi camera (IMX219) on either CSI port of the
Pi 5. The firmware finds it on its own (`camera_auto_detect=1`).

The model is our own YOLO11n, trained with Ultralytics (`my_model.pt`, one class: `bibi`, 640 px). PyTorch does not
run on the image, so the model is shipped as ONNX (`ros2_ws/src/object_detector/models/my_model.onnx`) and run by
OpenCV's DNN module. The ONNX export gives the same boxes and scores as Ultralytics itself. YOLO11n is small enough
for a 2 GB Pi 5; expect a few frames per second on the CPU. The capture is 640×480 to keep CPU and memory low.

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
3. Write that number to `reference_area_fraction` in `/usr/share/object_detector/config/object_detector.yaml`
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

Change these in `/usr/share/buzzer_controller/config/buzzer_controller.yaml`, then `systemctl restart buzzer-controller`.
`frequency_hz` sets the pitch; most passive buzzers are loudest at 2–4 kHz.

Test the buzzer without the camera by publishing distances by hand:

```bash
systemctl stop object-detector
ros2 topic pub -r 5 /object_distance std_msgs/msg/Float32 "{data: 0.3}"   # loud
ros2 topic pub -r 5 /object_distance std_msgs/msg/Float32 "{data: 1.5}"   # quiet
```

## Troubleshooting

| Problem                                         | Check                                                                 |
|-------------------------------------------------|-----------------------------------------------------------------------|
| `object-detector` keeps restarting              | `journalctl -u object-detector`; `cam --list` must show the camera (ribbon cable, port) |
| No `/object_distance` messages                  | Object not recognised: lower `confidence_threshold`, check the light  |
| Distance is wrong                               | Redo the calibration (`reference_area_fraction`)                     |
| `No PWM chip for 1f00098000.pwm`                | `grep pwm /boot/config.txt`; `ls -l /sys/class/pwm/`; set `pwm_chip` by hand |
| Buzzer clicks but has no tone / no volume change| It is an active buzzer; use a passive one                             |
