# meta-touch-display

GNOME on the Raspberry Pi's 3.5" SPI touch screen, logged in automatically, with the **Camera** app (the detector's
live view) pinned in GNOME's dash. Image: `ros-touch-display-image` = `ros-detection-image` (no buzzer) + this layer.

| Path                                         | What it does                                                        |
|----------------------------------------------|---------------------------------------------------------------------|
| `conf/layer.conf`                            | Layer setup; deploys `overlays/piscreen.dtbo` to the boot partition |
| `recipes-bsp/bootfiles/rpi-config_git.bbappend` | `config.txt`: SPI on, `dtoverlay=piscreen,drm,rotate=0,invx`     |
| `recipes-bsp/touchscreen-calibration/`       | udev rule: libinput calibration so the pen reaches the screen edges |
| `recipes-gnome/touch-display-settings/`      | GNOME at 80% text, so dialogs (e.g. Power Off) fit the 480-pixel height; the dash: Camera, GNOME Web, Console |
| `recipes-gnome/gdm/`                         | `custom.conf`: automatic login as `pi`, Wayland                     |
| `recipes-gnome/gnome-shell/`, `gnome-settings-daemon/`, `evolution-data-server/`, `recipes-navigation/geoclue/` | Leave out printing, online accounts, ModemManager and GNOME Settings |
| `recipes-connectivity/networkmanager-wifi-config/` | NetworkManager runs Wi-Fi, pre-configured from `local.conf`; polkit rule for `pi` |
| `recipes-extended/timezone/`                 | Time zone `Europe/Kyiv`                                             |
| `recipes-apps/detection-camera/`             | Installs the Camera app from `apps/detection_camera`                |
| `recipes-core/images/ros-touch-display-image.bb` | The image: GNOME, apps (Web, Files, Text Editor, Console), NetworkManager, zram swap, user `pi`, 2 GiB free on the root partition |

## The screen

A generic "3.5inch RPi LCD (A)": ILI9486 panel, 320×480, with ADS7846/XPT2046 resistive touch, on pins 1–26.

| Signal          | GPIO |
|-----------------|------|
| SPI0 MOSI/MISO/SCLK | 10 / 9 / 11 |
| Panel chip select (CE0) | 8 |
| Touch chip select (CE1) | 7 |
| Touch interrupt | 17   |
| Backlight       | 22   |
| DC (data/command) | 24 |
| Reset           | 25   |

The kernel's `piscreen` overlay has this wiring. Its `drm` parameter selects the DRM driver (`ili9486.ko`), so GNOME
sees the panel as a normal display; Mesa's `kmsro` lets the Pi 5 GPU (`v3d`) render for it.

### Touch calibration (measured on the board)

- **Direction**: with `rotate=0` the touch is mirrored left/right against the picture, so the overlay gets `invx`.
- **Edges**: the sensor only reports about 330–3800 across and 410–3680 down (of 0–4095), so without correction the
  outer edge, e.g. a window's close button, can't be tapped. `99-touchscreen-calibration.rules` sets
  `LIBINPUT_CALIBRATION_MATRIX="1.077 0 -0.030 0 1.152 -0.075"` to stretch that onto the whole screen.
- To re-measure: `/usr/libexec/libinput/libinput-debug-events --device /dev/input/event5` (or `evtest`) over SSH
  while tapping the corners. Try a new matrix by editing the rule, then
  `udevadm control --reload && udevadm trigger --action=change --sysname-match=event5 && systemctl restart gdm`.

## Wi-Fi and time

- **Wi-Fi is run by NetworkManager** (only `wlan0`), so networks can be picked in GNOME's top-right menu. It starts
  with the network from `WIFI_SSID` / `WIFI_PASSWORD` in `local.conf` already set up
  (`networkmanager-wifi-config`), so SSH works on first boot. meta-rpi-base's `wifi-config`
  (`wpa_supplicant@wlan0`) is left out of this image: two managers on `wlan0` would fight. A polkit rule lets `pi`
  change networks without an admin password.
- **The wired port stays with `systemd-networkd`**: if Wi-Fi ever fails, a network cable still gets you in over SSH.
- Over SSH: `nmcli device wifi list`, `nmcli device wifi connect <ssid> password <password>`.
- **Time zone** is `Europe/Kyiv` (`recipes-extended/timezone/tzdata.bbappend`); the clock itself syncs over the
  internet (`systemd-timesyncd`).

## Apps in the dash

Camera (`apps/detection_camera`), GNOME Web (browser), Files (Nautilus), Text Editor (notes), Console (terminal). The
list is in `recipes-gnome/touch-display-settings/files/91_touch-display.gschema.override`.

## Why some GNOME parts are left out

- **GNOME Settings, online accounts, printing, ModemManager**: unusable at 320×480 or not on this board, and they add
  Samba and more, hours of build. (WebKitGTK is built anyway now, for GNOME Web.)

## Needs in the build directory

`DISTRO_FEATURES:append = " polkit pam"` in `conf/local.conf` (already in the template), and these layers in
`conf/bblayers.conf`: `meta-openembedded/meta-networking`, `meta-multimedia`, `meta-gnome`, and this layer.
