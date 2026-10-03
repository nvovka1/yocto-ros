# yocto-ros

A custom Yocto (**scarthgap**) Linux for **Raspberry Pi 5**, with **ROS 2 Jazzy** added through a separate meta-layer.

- **Base OS** (`meta-rpi-base`): SSH, Wi-Fi, Python 3 + pip + PyYAML, systemd, avahi, i2c-tools, nano, htop.
- **ROS 2** (`meta-ros-demo`): ROS 2 core, the official Python demo nodes, and `counter_demo`, Python (rclpy)
  nodes that exchange a counter (`1, 2, 3, ...`) over the `/counter` topic. A `/counter/enable` service starts and
  stops the counter.

## Guides

1. [Part 1: base Raspberry Pi OS with Yocto](docs/01-raspberry-pi-base-os.md): WSL, host setup, layers, SSH, flashing.
2. [Part 2: ROS 2 and the counter demo](docs/02-ros2-counter-demo.md): ROS 2 on the PC, the nodes, the meta-layer, building, testing, releases.

## Layout

```
yocto-ros/
├── layers/                     external layers (git submodules, branch scarthgap)
│   ├── poky/
│   ├── meta-openembedded/
│   ├── meta-raspberrypi/
│   └── meta-ros/
├── meta-rpi-base/              our layer: base OS
│   ├── conf/layer.conf
│   ├── conf/templates/default/ local.conf / bblayers.conf for a new build directory
│   └── recipes-core/images/    rpi-base-image.bb
├── meta-ros-demo/              our layer: ROS 2 additions
│   ├── conf/layer.conf
│   ├── recipes-core/images/    ros-counter-image.bb (= rpi-base-image + ROS 2)
│   └── recipes-ros/            counter-demo (our nodes), ros-setup-profile (ROS env on login)
├── ros2_ws/src/counter_demo/   ROS 2 Python package (built with colcon on the PC and by BitBake for the image)
├── build_image.py              build an image (and copy it out for flashing) with one command
└── setup-environment.sh        source this to get a BitBake shell
```

## Images

| Image               | Layer           | Contents                         |
|---------------------|-----------------|----------------------------------|
| `rpi-base-image`    | `meta-rpi-base` | Base OS                          |
| `ros-counter-image` | `meta-ros-demo` | Base OS + ROS 2 + counter demo   |

## Nodes

| Executable           | What it does                                                                  |
|----------------------|-------------------------------------------------------------------------------|
| `counter_publisher`  | Publishes `std_msgs/UInt32` on `/counter` every second; serves `/counter/enable` (`std_srvs/SetBool`) |
| `counter_subscriber` | Logs every value received on `/counter`                                       |
| `counter_controller` | `counter_controller start` or `stop`: calls `/counter/enable` once and exits  |

## Quick start (Ubuntu 24.04 / WSL)

```bash
git clone --recurse-submodules https://github.com/nvovka1/yocto-ros.git
cd yocto-ros
python3 build_image.py                       # list the images
python3 build_image.py ros-counter-image     # or rpi-base-image for the base OS only
```

Or by hand: `source ./setup-environment.sh`, then `bitbake ros-counter-image`.

The image is written to `build/tmp/deploy/images/raspberrypi5/ros-counter-image-jazzy-raspberrypi5.rootfs.wic.xz`.

On the board (`ssh root@raspberrypi5.local`):

```bash
ros2 launch counter_demo counter_demo.launch.py
ros2 run counter_demo counter_controller stop
ros2 run counter_demo counter_controller start
```

Ready-made images are attached to [GitHub Releases](https://github.com/nvovka1/yocto-ros/releases).
