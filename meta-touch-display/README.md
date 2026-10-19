# meta-touch-display

GNOME on the Raspberry Pi's 3.5" SPI touch screen, logged in automatically, with the **Camera** app (the detector's
live view) pinned in GNOME's dash. Image: `ros-touch-display-image` = `ros-detection-image` (no buzzer) + this layer.

| Path                                         | What it does                                                        |
|----------------------------------------------|---------------------------------------------------------------------|
| `conf/layer.conf`                            | Layer setup; deploys `overlays/piscreen.dtbo` to the boot partition |
| `recipes-bsp/bootfiles/rpi-config_git.bbappend` | `config.txt`: SPI on, `dtoverlay=piscreen,drm,rotate=0,invx`     |
| `recipes-bsp/touchscreen-calibration/`       | udev rule: libinput calibration so the pen reaches the screen edges |
| `recipes-gnome/touch-display-settings/`      | GNOME at 80% text, so dialogs (e.g. Power Off) fit the 480-pixel height; the dash apps; the screen never blanks or locks; GNOME Web's home page; `GSK_RENDERER=cairo` (unverified, see below) |
| `recipes-kernel/linux/`                      | Patch: the panel driver reports about 30 Hz instead of 0.0065 Hz, so GNOME doesn't freeze windows |
| `recipes-gnome/gdm/`                         | `custom.conf`: automatic login as `pi`, Wayland                     |
| `recipes-gnome/gnome-shell/`, `gnome-settings-daemon/`, `evolution-data-server/`, `recipes-navigation/geoclue/` | Leave out printing, online accounts, ModemManager and GNOME Settings |
| `recipes-connectivity/networkmanager-wifi-config/` | NetworkManager runs Wi-Fi, pre-configured from `local.conf`; polkit rule for `pi`; time server for the clock |
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

### Windows froze for minutes: the panel's refresh rate (measured on the board)

- **Symptom**: the Camera app showed one still picture. It received every frame (74 in 16 s) but painted only 2, and
  nothing went to the panel; after about 165 s the picture started moving by itself.
- **Cause**: the `ili9486` driver builds its mode with `DRM_SIMPLE_MODE`, whose pixel clock is a 1 kHz placeholder.
  That makes the refresh rate 0.0065 Hz (GNOME logs `value "0.006510" ... for property 'refresh-rate'`), and GNOME's
  compositor waits about 154 s between frames.
- **Fix**: `recipes-kernel/linux/` patches the driver to report about 30 Hz (pixel clock 4608 kHz). Built, **not yet
  tested on the board**.
- Check: `cat /sys/bus/spi/devices/spi0.0/statistics/bytes_tx` twice, a few seconds apart, while the Camera app is
  open. A moving picture sends about 700–800 KB/s to the panel.
- **Unverified leftovers** from before the cause was found, to remove if the patch alone fixes it:
  `GSK_RENDERER=cairo` (`/etc/environment.d/90-touch-display.conf`, software drawing for GTK 4 apps; the picture
  froze with it too). The screen never blanking or locking (gschema override) is worth keeping anyway on a camera
  display.

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
  internet (`systemd-timesyncd`, from `pool.ntp.org`). The Pi has no clock battery, so it shows a stale date for the
  first seconds after boot. `networkmanager-wifi-config` sets the time server, and tells `systemd-networkd` that the
  unplugged cable port doesn't mean "offline". Without both, the clock is never set (systemd-networkd used to supply
  them when it ran Wi-Fi).

## Apps in the dash

Camera (`apps/detection_camera`), GNOME Web (browser, home page `https://uakino.best/`), Files (Nautilus), Text Editor
(notes), Console (terminal). The list and the home page are in
`recipes-gnome/touch-display-settings/files/91_touch-display.gschema.override`.

## Why some GNOME parts are left out

- **GNOME Settings, online accounts, printing, ModemManager**: unusable at 320×480 or not on this board, and they add
  Samba and more, hours of build. (WebKitGTK is built anyway now, for GNOME Web.)

## Needs in the build directory

`DISTRO_FEATURES:append = " polkit pam"` in `conf/local.conf` (already in the template), and these layers in
`conf/bblayers.conf`: `meta-openembedded/meta-networking`, `meta-multimedia`, `meta-gnome`, and this layer.
