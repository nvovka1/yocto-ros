# The 3.5" panel's DRM driver (ili9486) reports a 0.0065 Hz refresh rate, and GNOME then draws a window only every
# 154 seconds: the Camera app showed one still picture. The patch reports about 30 Hz.
FILESEXTRAPATHS:prepend := "${THISDIR}/files:"
SRC_URI += "file://0001-drm-tiny-ili9486-give-the-mode-a-real-pixel-clock.patch"
