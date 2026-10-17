# GNOME desktop on the 3.5" touch screen, with a Camera app

Date: 2026-10-17

## Why

The Raspberry Pi 5 now detects an object with the camera (`object_detector`) and used to beep through a buzzer
(`meta-buzzer`). The buzzer is no longer wanted. Instead, the owner wants to **look at the detection on the Pi's own
3.5" touch screen**: a GNOME desktop with an app icon that opens the live camera frame with the detection boxes.

The detector stays as it is and keeps publishing `/object_distance`; the owner will build their own reaction to it
later. This work is only about the screen, the desktop and seeing the frame.

## Goals

1. The 3.5" SPI touch screen works: picture and touch pen, portrait, 320 × 480.
2. The Pi boots straight into a **GNOME** desktop on that screen, with no login screen (automatic login).
3. A **Camera** app shows up in GNOME's UI (the dash/favourites and the app grid) with its own icon. Tapping it opens a
   window with the live camera frame and the detection boxes, scaled to fit the screen. Closing it returns to the
   desktop.
4. A new image that contains all of this, built and running on the Pi.

## Non-goals

- No Firefox or any web browser.
- No distance/data app and no alert or sound. Only the frame for now.
- No changes to the detector's detection logic or to `/object_distance`.
- No HDMI monitor support work (it may keep working, but it's not a goal).

## Anti-goals (would be a failure even if it technically works)

- The desktop shows on HDMI or only over the network, but not on the 3.5" screen.
- A login screen or password prompt that has to be typed with the touch pen.
- The Camera app exists but you can't find and open it from GNOME's UI.
- The new image breaks the detector (it has to keep running and publishing as it does today).

## Current state (checked on the board over SSH, 2026-10-17)

- Board: **Raspberry Pi 5 Model B, 2 GB RAM**, Yocto **scarthgap**, kernel `6.6.63-v8-16k`, ROS 2 Jazzy.
  Reachable as `ssh root@192.168.0.101` (only access is SSH).
- Running image: `ros-buzzer-image`. `config.txt` has `vc4-kms-v3d`, `imx219`, and `pwm-2chan` on GPIO 12/13 (buzzer).
- Root partition (`mmcblk0p2`) is only ~860 MB and 62% full; the SD card is 64 GB.
- The screen is **not configured**: SPI is off and no display overlay is loaded. HDMI ports are disconnected.
- The kernel already ships the drivers the screen needs: DRM `ili9486` (`drivers/gpu/drm/tiny/ili9486.ko`) for the
  picture and `ads7846` for touch. The kernel source has the `piscreen` overlay, whose `drm` parameter switches it to the
  DRM driver (`compatible = "waveshare,rpi-lcd-35"`), but `piscreen.dtbo` is not deployed to `/boot/overlays` today.
- The screen is a generic "3.5inch RPi LCD (A)" clone (ILI9486 + XPT2046/ADS7846 touch) that sits on pins 1–26. Its pins
  (`piscreen` overlay): SPI0 (GPIO 7–11), touch IRQ GPIO 17, backlight GPIO 22, DC GPIO 24, reset GPIO 25. No clash with
  the buzzer pins (GPIO 12/13) or the camera (CSI).
- The detector already serves the frame with boxes as MJPEG: `http://<board>:8080/stream`
  (`multipart/x-mixed-replace; boundary=frame`, each part `--frame\r\nContent-Type: image/jpeg\r\nContent-Length: N\r\n\r\n<jpeg>\r\n`).
  It only draws and encodes frames while somebody is connected (`PreviewServer.has_viewers`). Source:
  `ros2_ws/src/object_detector/object_detector/preview_server.py`. Port is the `preview_port` parameter (8080).
- Builds run in WSL (Ubuntu 24.04) in a separate clone, `/home/vblahodyr/yocto-ros`, build dir `build/`, 16 cores, plenty
  of disk. The Windows repo `C:\MyProjects\yocto-ros` is where code is edited; the WSL clone is updated by copying files
  over (it is not a git pull). See the memory notes about WSL quoting and board file ownership.

## Decisions made with the owner

- **GNOME**, from upstream `meta-openembedded/meta-gnome` (already in the `layers/meta-openembedded` submodule;
  scarthgap = GNOME 46). Not a lighter desktop, even though GNOME is designed for bigger screens.
- **Automatic login straight into GNOME**, no login screen.
- **No Firefox.**
- **No buzzer** in the new image.
- **Our own new layer, `meta-touch-display`**, holds the screen setup, the Camera app and the image. The Camera app is a
  separate app that must appear in GNOME's UI.
- Portrait orientation, 320 wide × 480 tall (proposed by Claude, the owner did not object).

## Design

### Layers

- Add to `bblayers.conf` (both the template `meta-rpi-base/conf/templates/default/bblayers.conf.sample` and the existing
  WSL `build/conf/bblayers.conf`): `meta-openembedded/meta-gnome` and whatever other meta-openembedded sublayers GNOME
  needs. Known so far: `meta-gnome` depends on `meta-networking`; `gnome-shell` needs `pipewire` (in `meta-multimedia`).
  The builder finds the full set by parsing.
- New layer **`meta-touch-display`** at the repository root, same structure as `meta-object-detection`/`meta-buzzer`:
  `conf/layer.conf` (collection `touch-display-layer`, `LAYERSERIES_COMPAT = "scarthgap"`, `LAYERDEPENDS` on
  `gnome-layer`, `object-detection-layer` and the rest it uses).

### Image: `ros-touch-display-image`

In `meta-touch-display/recipes-core/images/`, `require recipes-core/images/ros-detection-image.bb` (the detector, without
the buzzer), then add:
- the GNOME desktop: GDM, gnome-session, gnome-shell and the minimum to make a usable desktop. Prefer something lean over
  the whole `packagegroup-gnome-desktop` if that one drags in a lot (e.g. `gnome-flashback`, `gnome-tweaks`, `gvfs` ftp/sftp);
  a terminal (`gnome-terminal` or `gnome-console`) is welcome but optional;
- the Camera app (below) and the screen configuration package (below);
- `SYSTEMD_DEFAULT_TARGET = "graphical.target"`;
- a bigger root file system: enough free space after GNOME is installed (target at least ~1.5 GB free). The SD card is
  64 GB, so size is not a constraint; the `.wic.xz` compresses the free space.
- Register the image in `build_image.py` (`IMAGES`) and in the README image table.

### Distro features

GNOME recipes require `x11 wayland opengl polkit pam systemd gobject-introspection-data`. Poky lacks at least `polkit`
and `pam`. These are global settings, so they go in `local.conf` (template `local.conf.sample` and the existing WSL
`build/conf/local.conf`), not in the layer. This rebuilds shared packages for every image built in that build directory;
that's accepted.

### Screen (picture + touch)

- Boot config through a `rpi-config_git.bbappend` in `meta-touch-display` (same pattern as the other layers):
  `dtparam=spi=on` and `dtoverlay=piscreen,drm,...` with portrait rotation (DRM driver's native mode is 320 × 480, so
  rotation 0 should be portrait; confirm on the screen). SPI speed: start at the overlay's default and raise only if it
  is stable.
- Deploy the overlay: `RPI_KERNEL_DEVICETREE_OVERLAYS:append = " overlays/piscreen.dtbo"` (meta-raspberrypi only copies
  overlays it lists; `meta-buzzer` does the same for `pwm-2chan`).
- GNOME (mutter) has to draw on the Pi 5 GPU (`v3d`) and show it on the SPI panel, which has no GPU. Mesa's `kmsro`
  driver supports `ili9486` panels and pairs them with the `v3d` renderer; make sure mesa is built with what this needs
  (check meta-raspberrypi's mesa settings). If mutter still picks the wrong device, a udev rule can mark the SPI panel's
  DRM device as mutter's preferred primary (`mutter-device-preferred-primary` tag).
- Touch: the `ads7846` touch must line up with the picture in portrait. Fix the axes with the overlay's
  `swapxy`/`invx`/`invy` parameters and/or a udev `LIBINPUT_CALIBRATION_MATRIX`, determined on the real screen. Touch
  must map to the 3.5" output.
- Anything GNOME needs to look sane at this size (e.g. text scaling) is up to the builder; it doesn't need to be pretty,
  it needs to be usable with the pen.

### Automatic login

GDM automatic login, Wayland session. Use a normal user, e.g. `pi` created with `extrausers` (GDM/GNOME and root don't
mix well). The account has no password, matching the development posture of the image (root already has an empty
password). The detector keeps running as a root system service; the app only needs `localhost:8080`.

### Camera app

- Name in GNOME: **Camera** (or "Detection Camera"), with its own icon, listed in the app grid **and pinned in the
  dash/favourites** (`org.gnome.shell favorite-apps` set through a gschema override in the recipe) so it's one tap away.
- What it does: opens a window that connects to `http://127.0.0.1:8080/stream`, reads the MJPEG parts and shows each
  JPEG scaled to fit the window while keeping the aspect ratio (the frame is 640 × 480 landscape; on the portrait screen
  it shows letterboxed). If the stream isn't available (detector starting or restarting), it shows a short "Waiting for
  camera…" text and retries every couple of seconds. Closing the window closes the connection, so the detector stops
  drawing preview frames.
- Technology: Python 3 + GTK 4 through PyGObject (GTK 4 is already pulled in by GNOME 46); JPEG decoding with
  GdkPixbuf. No ROS dependency and no change to the detector.
- Source in this repository at `apps/detection_camera/` (it's not a ROS package, so not under `ros2_ws/src`): the app
  code, a `.desktop` file, an SVG icon, and pytest tests for the stream parsing (runnable on the PC without a display).
  A recipe in `meta-touch-display/recipes-apps/detection-camera/` installs it, fetching the source from the repository
  the same way the ROS recipes do (`YOCTO_ROS_REPOSITORY_ROOT`).

### Documentation

- README: the new layer, the image, the screen pins, and how to open the Camera app.
- A short guide in `docs/` like the existing parts.

## Risks

1. **GNOME on an SPI panel without its own GPU** is the biggest unknown; it hasn't been proven on this board. First
   milestone: the GNOME desktop is visible and touchable on the 3.5" screen. Only then the app.
2. **GNOME at 320 × 480**: the top bar, dialogs and the app grid are built for bigger screens. Acceptable if the Camera
   app can be opened and closed with the pen.
3. **2 GB RAM, no swap**: GNOME (~0.5 GB+) plus the detector (~0.45 GB). Watch for out-of-memory; a swap file or zram
   is an option if needed.
4. **Build time**: the first GNOME build takes hours (mozjs/gjs, rust, mutter, gtk4, webkit-free set hopefully).
5. **SPI panel frame rate** is low (~10–20 fps at full screen). The camera view runs at the detector's ~5 fps anyway.

## Getting the image onto the Pi (decided by the owner)

The new image can't be installed in place (the partition layout changes), so the **owner takes the SD card out and
flashes the image** (Raspberry Pi Imager or `bmaptool`). The owner also **looks at the screen and taps it with the pen
when asked**: which way up portrait is, tapping corners for touch calibration, confirming the picture, the power-cycle
test. Everything else is checked over SSH (`root@192.168.0.101`; the address may change after a reflash, so try
`raspberrypi5.local` as well). Wi-Fi and SSH must keep working in the new image, since that's the only remote access.

## Calls made by Claude (owner to check)

- **Rendering fallback:** use the Pi 5 GPU (`v3d` through Mesa `kmsro`; meta-raspberrypi's mesa already builds `kmsro`,
  `v3d` and `vc4`). If mutter can't use it for the SPI panel within a short time-box, fall back to software rendering
  (llvmpipe). At 320 × 480 that is cheap, and it is still GNOME. Don't switch to another desktop without asking.
- **Detector speed:** "keeps running" means the service stays active and keeps publishing `/object_distance`. A drop
  below today's ~5 frames/s while GNOME or the Camera app runs is acceptable; measure it on the board and report the
  numbers. Add a swap file or zram from the first build (2 GB RAM, no swap today) so memory spikes don't kill the
  detector.
- **Git:** nothing is committed or branched until the owner asks; the work-item id for a branch name comes from the
  owner at that point.

## Left to the builder

- Exact GNOME package list, mesa/kmsro settings, rotation/touch calibration values, SPI speed, root file system size,
  app icon design, and how the app's window fills the screen (maximized/fullscreen).
- Whether `meta-buzzer` stays in the build's `bblayers.conf` (its `pwm-2chan` line in `config.txt` is harmless; the new
  image does not include the buzzer node).

## Verification

- On the board: `config.txt` has the screen lines, `/dev/dri` has the SPI panel's card, GDM logs in automatically,
  GNOME is on the 3.5" screen, touch hits where the pen taps, the Camera icon is in the dash, tapping it shows the live
  frame with boxes, closing it returns to the desktop, `object-detector` is still active and `/object_distance` is still
  published, and it all survives a power cycle.
- On the PC: pytest for the app's stream parser.
