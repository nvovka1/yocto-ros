# GNOME on the 3.5" Touch Screen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A new image, `ros-touch-display-image`. It boots the Pi 5 straight into GNOME on the 3.5" SPI touch screen, and a Camera app in GNOME's dash shows the detector's live frame with the detection boxes.

**Architecture:** A new layer, `meta-touch-display`, sits on top of `meta-object-detection` and upstream `meta-gnome`. It has five parts:
- the screen (`piscreen` overlay in DRM mode);
- GDM with automatic login;
- swap;
- a bigger root file system;
- the Camera app.

The Camera app is plain Python + GTK 4 under `apps/detection_camera/`. It reads the detector's existing MJPEG stream (`http://127.0.0.1:8080/stream`), so the detector code doesn't change.

**Tech Stack:** Yocto scarthgap, meta-raspberrypi, meta-ros (jazzy), meta-openembedded (`meta-gnome`, `meta-networking`, `meta-multimedia`), GNOME 46, Mesa `kmsro`/`v3d`, Python 3, PyGObject, GTK 4.14, pytest.

**Spec:** `docs/superpowers/specs/2026-10-17-gnome-touch-display-design.md`

## Global Constraints

- Yocto **scarthgap**, `MACHINE = "raspberrypi5"`, ROS 2 **jazzy**, systemd. New layers set `LAYERSERIES_COMPAT_* = "scarthgap"`.
- **No git commits and no branches** until the owner asks. Where a step says "Checkpoint", stop and report; do not commit.
- No Firefox and no web browser. No buzzer in the new image. No changes to `ros2_ws/src/object_detector`.
- Stream URL: `http://127.0.0.1:8080/stream`. The format is `multipart/x-mixed-replace; boundary=frame`, and each part is `--frame\r\nContent-Type: image/jpeg\r\nContent-Length: N\r\n\r\n<N bytes>\r\n`.
- Screen pins: SPI0 (GPIO 7–11), touch IRQ GPIO 17, backlight GPIO 22, DC GPIO 24, reset GPIO 25. Orientation is portrait, 320 wide × 480 tall.
- Automatic login as user `pi`, Wayland session, no password prompt anywhere.
- Code is edited in `C:\MyProjects\yocto-ros`. Builds run in WSL in `/home/vblahodyr/yocto-ros` (build dir `build/`), which is updated by **copying** from Windows, not by git:
  - Run WSL work as script files from PowerShell: `wsl -d Ubuntu-24.04 --exec bash <wslpath-of-script>`.
  - Start every script with `set -euo pipefail` and guard every path variable.
  - Never `wsl -- bash -lc '...$VAR...'`. Never run `/mnt/...` paths through Git Bash.
- Board: `ssh root@192.168.0.101`, or `raspberrypi5.local` after a reflash. Copy single files to the board with `ssh ... "cat > file"`, or untar with `--no-same-owner --no-overwrite-dir` and without a `.` entry. The owner flashes SD cards and does anything that needs eyes or the pen on the screen.
- Naming follows the user rules: whole words, `snake_case` Python modules, kebab-case recipe names.

## Review Focus

1. **The detector is not running yet when the app opens**, or it restarts while the app is open. The app shows "Waiting for camera…", reconnects by itself and never freezes on an old frame. Tests: Task 2 `test_reports_waiting_when_nothing_listens`, `test_reconnects_after_the_server_drops_the_connection`.
2. **The stream arrives in odd-sized chunks** (TCP splits headers and JPEGs anywhere), so frames must still come out whole. Test: Task 1 `test_reads_frames_delivered_one_byte_at_a_time`.
3. **A broken or truncated JPEG part** gets skipped, with the next frame shown; the app does not crash. Tests: Task 1 `test_stops_cleanly_on_a_truncated_last_frame`, Task 3 manual check (texture decode errors are caught).
4. **Closing the window** really closes the HTTP connection, so the detector stops drawing preview frames and the CPU goes back to normal. Test: Task 2 `test_stop_returns_quickly_while_waiting_for_data`. Board check: Task 7 shows the detector's frame rate back to its idle value after closing.
5. **Memory on a 2 GB Pi** with GNOME, the detector and the app all running: no out-of-memory kill. Board check: Task 7 (`free -m`, `journalctl -k | grep -i oom` empty, swap active).

---

### Task 1: MJPEG stream parser

**Files:**
- Create: `apps/detection_camera/detection_camera/__init__.py` (empty)
- Create: `apps/detection_camera/detection_camera/mjpeg_stream.py`
- Create: `apps/detection_camera/test/test_mjpeg_stream.py`
- Create: `apps/detection_camera/LICENSE` (MIT, same text as `ros2_ws/src/object_detector/LICENSE`)

**Interfaces:**
- Produces:
  - `boundary_from_content_type(content_type: str) -> str`. It raises `ValueError` when the type isn't `multipart/x-mixed-replace` or has no `boundary=`.
  - `iter_jpeg_frames(stream: BinaryIO, boundary: str) -> Iterator[bytes]`. It yields each part's body. It uses `readline()` for headers and `read(n)` for bodies, and returns at EOF. It raises `ValueError` on a part without `Content-Length` or a line that isn't the expected `--<boundary>`.

- [ ] **Step 1: Write the failing tests.** Build the bytes with a helper `part(jpeg: bytes) -> bytes` in the exact format from Global Constraints.
  - `test_boundary_is_read_from_the_content_type`: `boundary_from_content_type('multipart/x-mixed-replace; boundary=frame') == 'frame'`
  - `test_other_content_types_are_rejected`: `pytest.raises(ValueError)` for `'text/html'` and for `'multipart/x-mixed-replace'`
  - `test_yields_every_frame_in_order`: three parts `b'one'`, `b'two'`, `b'three'` in `io.BytesIO` → `list(iter_jpeg_frames(stream, 'frame')) == [b'one', b'two', b'three']`
  - `test_reads_frames_delivered_one_byte_at_a_time`: wrap a raw reader whose `readinto` returns 1 byte per call in `io.BufferedReader(raw, buffer_size=1)`. Same three frames come out.
  - `test_frame_containing_the_boundary_text_is_not_split`: frame `b'xx--frame\r\nyy'` comes back unchanged (proves Content-Length is used, not a boundary search).
  - `test_stops_cleanly_on_a_truncated_last_frame`: two whole parts, then a part whose body is cut short. Yields the two whole frames and then stops; no exception, no partial frame.
  - `test_missing_content_length_is_an_error`: `pytest.raises(ValueError)`.
- [ ] **Step 2: Check the tests fail.** Run `cd apps/detection_camera && python -m pytest test -v`. Expected: ImportError / FAIL.
- [ ] **Step 3: Implement both functions in `mjpeg_stream.py`.** Skip blank lines before a boundary line. Read header lines until an empty line. A short `read(n)` (fewer than n bytes) means EOF: return.
- [ ] **Step 4: Check the tests pass.** Run the same command. Expected: 7 passed.
- [ ] **Checkpoint:** report the test output.

### Task 2: Frame receiver (background connection with reconnect)

**Files:**
- Create: `apps/detection_camera/detection_camera/frame_receiver.py`
- Create: `apps/detection_camera/test/test_frame_receiver.py`

**Interfaces:**
- Consumes: `boundary_from_content_type`, `iter_jpeg_frames` (Task 1).
- Produces:
  - `WAITING_TEXT = 'Waiting for camera…'`
  - `class FrameReceiver(url: str, on_frame: Callable[[bytes], None], on_status: Callable[[str], None], retry_seconds: float = 2.0)` with `start() -> None` and `stop() -> None`.
  - Callbacks run on the receiver's thread. The GTK side moves them to the main loop.
  - `on_status(WAITING_TEXT)` is called on every failed connect or dropped connection. `on_status('')` is called when the first frame of a connection arrives.

- [ ] **Step 1: Write the failing tests.** Use a fake MJPEG server fixture: a `ThreadingHTTPServer` on `127.0.0.1` port 0 whose `/stream` writes N parts and then closes. Collect callback calls in lists and use `threading.Event` with a 5 s timeout for waiting.
  - `test_delivers_frames_from_the_stream`: the server sends `b'a'`, `b'b'`, and the receiver gets `[b'a', b'b']` in that order.
  - `test_reports_waiting_when_nothing_listens`: a URL on a closed port (bind a socket, read its port, close it), so `on_status` gets `WAITING_TEXT` within 5 s.
  - `test_reconnects_after_the_server_drops_the_connection`: `retry_seconds=0.1`. The server sends one frame per connection and closes. Within 5 s at least 2 frames arrive and `WAITING_TEXT` was reported in between.
  - `test_stop_returns_quickly_while_waiting_for_data`: the server sends headers and then sleeps 30 s. `stop()` returns in under 1 s and the receiver thread is no longer alive.
- [ ] **Step 2: Check the tests fail.** Run `python -m pytest test/test_frame_receiver.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement `FrameReceiver`.**
  - A daemon thread runs a loop with `urllib.request.urlopen(url, timeout=5)`.
  - It checks the boundary, then calls `on_frame` for each frame.
  - On `OSError`/`ValueError`, it reports waiting and then waits `retry_seconds` on a `threading.Event`, so `stop()` interrupts the wait.
  - `stop()` sets the event, closes the current response from the calling thread so a blocked `read` returns, and joins with a 2 s timeout.
- [ ] **Step 4: Check the tests pass.** Run `python -m pytest test -v`. Expected: 11 passed (Tasks 1 and 2).
- [ ] **Checkpoint:** report the test output.

### Task 3: GTK window, launcher, desktop entry, icon

**Files:**
- Create: `apps/detection_camera/detection_camera/app.py`
- Create: `apps/detection_camera/detection-camera` (launcher script, `#!/usr/bin/env python3`)
- Create: `apps/detection_camera/data/io.github.nvovka1.DetectionCamera.desktop`
- Create: `apps/detection_camera/data/io.github.nvovka1.DetectionCamera.svg`
- Create: `apps/detection_camera/README.md` (what it is, how to run on the PC against a board: `DETECTION_CAMERA_URL=http://192.168.0.101:8080/stream python -m detection_camera.app`)

**Interfaces:**
- Consumes: `FrameReceiver`, `WAITING_TEXT` (Task 2).
- Produces:
  - `main(argv: list[str] | None = None) -> int` in `detection_camera.app`, run by the launcher. The app is also runnable as `python -m detection_camera.app`.
  - Application id `io.github.nvovka1.DetectionCamera`. The desktop file name, the icon name and the GNOME favourite entry all use this id.
  - Stream URL from the environment variable `DETECTION_CAMERA_URL`, defaulting to `http://127.0.0.1:8080/stream`.

- [ ] **Step 1: Implement `app.py`.**
  - `Gtk.Application` holds one `Gtk.ApplicationWindow` with title `Camera`, maximized.
  - The window contains a `Gtk.Overlay` with a `Gtk.Picture` (`content_fit = Gtk.ContentFit.CONTAIN`) and a centered `Gtk.Label` for status.
  - Frames go through `GLib.idle_add` to `Gdk.Texture.new_from_bytes(GLib.Bytes.new(jpeg))`. `GLib.Error` is caught and the frame skipped (Review Focus 3).
  - Status text is set on the label. An empty string hides it.
  - The receiver starts on `activate` and stops on the window's `close-request`.
- [ ] **Step 2: Write the desktop entry and icon.**
  - Desktop entry: `Name=Camera`, `Comment=Live camera view with object detection`, `Exec=detection-camera`, `Icon=io.github.nvovka1.DetectionCamera`, `Categories=Video;`, `StartupNotify=true`.
  - Icon: a simple camera glyph as a 128×128 viewBox SVG.
- [ ] **Step 3: Validate the desktop file.** If WSL has `desktop-file-validate` (skip this step if it doesn't), run it on `apps/detection_camera/data/io.github.nvovka1.DetectionCamera.desktop`. Expected: no output.
- [ ] **Step 4: Run all tests.** Run `python -m pytest apps/detection_camera/test -v`. Expected: 11 passed. The GTK window itself is checked on the board in Task 7.
- [ ] **Checkpoint:** report.

### Task 4: `meta-touch-display` layer: screen, GNOME, auto-login, swap, image

**Files:**
- Create: `meta-touch-display/conf/layer.conf`. Copy the shape of `meta-object-detection/conf/layer.conf`, with collection `touch-display-layer`, priority 20, and `LAYERDEPENDS` = `core openembedded-layer networking-layer multimedia-layer gnome-layer raspberrypi object-detection-layer`. It also sets `RPI_KERNEL_DEVICETREE_OVERLAYS:append = " overlays/piscreen.dtbo"`, with a comment like `meta-buzzer`'s.
- Create: `meta-touch-display/recipes-bsp/bootfiles/rpi-config_git.bbappend`. It appends `dtparam=spi=on` and `dtoverlay=piscreen,drm,rotate=0` via `RPI_EXTRA_CONFIG:append`, with a comment block naming the pins.
- Create: `meta-touch-display/recipes-gnome/gdm/gdm_%.bbappend` plus `files/custom.conf`. The `[daemon]` section has `AutomaticLoginEnable=True`, `AutomaticLogin=pi` and `WaylandEnable=true`. Install it over `${sysconfdir}/gdm/custom.conf` in `do_install:append`.
- Create: `meta-touch-display/recipes-core/images/ros-touch-display-image.bb`.
- Create: `meta-touch-display/README.md` (short: what the layer adds).
- Modify: `meta-rpi-base/conf/templates/default/bblayers.conf.sample`. Add `meta-openembedded/meta-networking`, `meta-multimedia`, `meta-gnome` and `meta-touch-display` (also `meta-object-detection` if missing), using the same relative style as the existing entries.
- Modify: `meta-rpi-base/conf/templates/default/local.conf.sample`. Add `DISTRO_FEATURES:append = " polkit pam"` with a comment saying GNOME needs it and it applies to every image in the build dir.
- Modify (WSL only, not in git): `/home/vblahodyr/yocto-ros/build/conf/bblayers.conf` (add the same layers with `bitbake-layers add-layer`) and `build/conf/local.conf` (same `DISTRO_FEATURES` line).
- Modify: `build_image.py`. Add `'ros-touch-display-image': 'ros-detection-image + GNOME on the 3.5" touch screen + Camera app (meta-touch-display)'` to `IMAGES`.

**Interfaces:**
- Produces: the image recipe name `ros-touch-display-image` and the user `pi` (home `/home/pi`). The recipe holds:
  - `require recipes-core/images/ros-detection-image.bb`.
  - `IMAGE_INSTALL:append`:
    - GNOME: `gdm gnome-session gnome-shell gnome-settings-daemon gnome-control-center adwaita-icon-theme adwaita-icon-theme-cursors gnome-backgrounds gsettings-desktop-schemas`. Add `gnome-console` if the recipe exists, otherwise `gnome-terminal`.
    - Fonts: `ttf-dejavu-sans` or another font packages recipe that exists.
    - Swap: `zram` if the kernel has `CONFIG_ZRAM`, otherwise a 1 GB swap file created by a small systemd unit in this layer.
  - `inherit extrausers` with `EXTRA_USERS_PARAMS = "useradd -m -s /bin/sh -G video,render,input pi; usermod -p '' pi;"`. The empty password means nothing ever asks for one; add a comment that this is a development image, like root.
  - `SYSTEMD_DEFAULT_TARGET = "graphical.target"`.
  - `IMAGE_ROOTFS_EXTRA_SPACE = "2097152"` (2 GiB free, in KiB).
  - `IMAGE_FEATURES += "x11-base"` only if needed for Xwayland. Leave it out unless the parse/build demands it.

- [ ] **Step 1: Copy the repo to WSL.** Write `scratchpad/sync_to_wsl.sh` (`set -euo pipefail`; `SOURCE=/mnt/c/MyProjects/yocto-ros`, `TARGET=/home/vblahodyr/yocto-ros`; `[ -d "$TARGET/.git" ] || exit 1`). It runs `rsync -a --exclude build --exclude layers --exclude .git --exclude downloads --exclude sstate-cache --exclude __pycache__ "$SOURCE/" "$TARGET/"`. Then it checks no `.bb`/`.conf`/`.sh` under `TARGET/meta-*` or `TARGET/apps` contains `\r` (`grep -rl $'\r'` must print nothing). Run it from PowerShell as in Global Constraints.
- [ ] **Step 2: Check that BitBake parses and resolves every dependency.** In WSL, run a script that sources `setup-environment.sh` and runs `bitbake -g ros-touch-display-image`. Expected: `task-depends.dot` is written and there are no `Nothing PROVIDES` / `No eligible RPROVIDERs` / missing-layer errors. If a provider is missing, add the meta-openembedded sublayer that has it (find it with `find layers/meta-openembedded -name '<recipe>_*.bb'`) to both bblayers files and `LAYERDEPENDS`, then repeat.
- [ ] **Step 3: Check the generated boot config and users.** Run `bitbake -e rpi-config | grep -E '^RPI_EXTRA_CONFIG='`. Expected: it contains `dtoverlay=piscreen,drm,rotate=0` and `dtparam=spi=on`. Run `bitbake -e ros-touch-display-image | grep -E '^(SYSTEMD_DEFAULT_TARGET|IMAGE_ROOTFS_EXTRA_SPACE|EXTRA_USERS_PARAMS)='`. Expected: the values above.
- [ ] **Checkpoint:** report the parse result and the list of layers added.

### Task 5: Camera app recipe, pinned in GNOME

**Files:**
- Create: `meta-touch-display/recipes-apps/detection-camera/detection-camera_0.1.0.bb`
- Create: `meta-touch-display/recipes-apps/detection-camera/files/90_detection-camera.gschema.override`
- Modify: `meta-touch-display/recipes-core/images/ros-touch-display-image.bb` (add `detection-camera` to `IMAGE_INSTALL`)
- Modify: `README.md`: new layer row in the layout, the image table, a short "Touch screen and Camera app" section (pins, `dtoverlay` line, how to open the app), and the bblayers note for existing build dirs.

**Interfaces:**
- Consumes: the files from Tasks 1–3 and the image from Task 4.
- Produces: package `detection-camera`, which installs:
  - `${PYTHON_SITEPACKAGES_DIR}/detection_camera/*.py`;
  - `${bindir}/detection-camera` (0755);
  - `${datadir}/applications/io.github.nvovka1.DetectionCamera.desktop`;
  - `${datadir}/icons/hicolor/scalable/apps/io.github.nvovka1.DetectionCamera.svg`;
  - `${datadir}/glib-2.0/schemas/90_detection-camera.gschema.override`. Its contents are `[org.gnome.shell]` with `favorite-apps=['io.github.nvovka1.DetectionCamera.desktop']`.

- [ ] **Step 1: Write the recipe.**
  - Source: `FILESEXTRAPATHS:prepend := "${YOCTO_ROS_REPOSITORY_ROOT}/apps:${THISDIR}/files:"`, `SRC_URI = "file://detection_camera file://90_detection-camera.gschema.override"`, `S = "${WORKDIR}/detection_camera"`.
  - License: `LICENSE = "MIT"` with `LIC_FILES_CHKSUM` on its own `LICENSE` file. Copy the md5 approach from `object-detector_0.1.0.bb` and compute the md5 in WSL.
  - `inherit python3native gsettings gtk-icon-cache allarch`. `gsettings` compiles the schemas and the override at install time.
  - `RDEPENDS:${PN} = "python3-core python3-pygobject gtk4 python3-netclient"`. Add any extra `python3-*` that a test import on the board shows is missing.
  - `do_install` copies the files listed above. Tests are not installed.
- [ ] **Step 2: Sync and build only the package.** Run the Task 4 sync, then `bitbake detection-camera`. Expected: success. Check the package contents with `ls build/tmp/work/*/detection-camera/*/packages-split/detection-camera/usr/share/applications`. Expected: the desktop file.
- [ ] **Checkpoint:** report.

### Task 6: Full image build

**Files:** none new.

- [ ] **Step 1: Start the full build in the background.** Run the sync, then `python3 build_image.py ros-touch-display-image --copy-to /mnt/c/Users/volodymyr_blahodyr/Downloads` from a WSL script started with `run_in_background`, logging to `/home/vblahodyr/yocto-ros/build/touch-display-build.log`. Expect many hours (mozjs/gjs, rust, gtk4, mutter).
- [ ] **Step 2: On failure,** use superpowers:systematic-debugging. Read the failing task's log (`build/tmp/work/.../temp/log.do_*`), fix in the layer (never in `layers/`), sync and resume. Typical failures:
  - a missing `DISTRO_FEATURES` entry;
  - a missing sublayer;
  - a GNOME recipe needing `gobject-introspection` / `qemu-usermode` (`MACHINE_FEATURES`).
- [ ] **Step 3: Check the result.** `build/tmp/deploy/images/raspberrypi5/ros-touch-display-image-jazzy-raspberrypi5.rootfs.wic.xz` exists and was copied to Downloads. Report its size.
- [ ] **Checkpoint:** tell the owner the image path and ask them to flash it (Raspberry Pi Imager → Use custom, or `bmaptool copy`) and boot with the screen attached.

### Task 7: On the board: screen, touch, app, detector

**Files:** possibly `meta-touch-display/recipes-bsp/bootfiles/rpi-config_git.bbappend` (rotation / touch parameters), a new `meta-touch-display/recipes-bsp/touch-calibration/` udev rule recipe (only if overlay parameters aren't enough), and `meta-touch-display/README.md` (record the final values).

- [ ] **Step 1: Over SSH, check the hardware.** Expected results:
  - `ls /dev/dri` shows a third card. `cat /sys/class/drm/card*-SPI-1/status` (or similar) shows `connected`.
  - `dmesg | grep -iE 'ili9486|ads7846|panel'` shows the drivers bound.
  - `systemctl is-active gdm object-detector` prints `active` twice.
  - `loginctl list-sessions` shows a session for `pi`.
- [ ] **Step 2: If GNOME isn't on the panel,** use superpowers:systematic-debugging.
  - Look at `journalctl -b -u gdm` and `journalctl -b _COMM=gnome-shell` for which GPU mutter picked.
  - If needed, add a udev rule tagging the SPI card `mutter-device-preferred-primary`.
  - Time-box GPU attempts. Then fall back to software rendering (llvmpipe) as the spec allows.
  - Hot-test config changes by editing `/boot/config.txt` or `/etc` over SSH, then bake the working values into the layer.
- [ ] **Step 3: Ask the owner which way up the picture is.** Change `rotate=` (0 or 180) if needed.
- [ ] **Step 4: Touch.** Run `libinput debug-events` over SSH (add `libinput-bin` to the image if it's missing) while the owner taps the four corners in order: top-left, top-right, bottom-right, bottom-left. Work out the axis swap and inversion, then apply `swapxy`/`invx`/`invy` on the `piscreen` overlay, or a `LIBINPUT_CALIBRATION_MATRIX` udev rule. Have the owner confirm taps land where the pen is.
- [ ] **Step 5: App.** The owner taps the Camera icon in the dash.
  - Expected: the live frame with boxes. Meanwhile `journalctl -u object-detector -f` keeps logging the frame rate; record it with the app open and closed.
  - The owner closes the app. Expected: back to the desktop, and the detector's frame rate returns to its earlier value.
- [ ] **Step 6: Memory.** With GNOME, the detector and the app open, check:
  - `free -m` and `swapon --show` (swap active);
  - `journalctl -k | grep -i 'out of memory'` (must be empty).
  - Record the numbers.
- [ ] **Step 7: Power cycle.** The owner unplugs and replugs the Pi. Steps 1 and 5 pass again. `find / -xdev -user 1000` stays empty if any files were copied to the board.
- [ ] **Step 8: Write the docs.** Put the final rotation and touch values and the measured frame rates and memory in `meta-touch-display/README.md`. If the layer changed, rebuild so the image matches what was tested on the board, and tell the owner.
- [ ] **Checkpoint:** report results to the owner and ask about committing (branch name needs a work-item id from the owner).
