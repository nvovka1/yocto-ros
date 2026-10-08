# Raspberry Pi 5 camera.
#
# Use Raspberry Pi's libcamera fork (as Raspberry Pi OS does) instead of upstream: the Raspberry Pi kernel
# (linux-raspberrypi 6.6) names its camera device nodes rp1-cfe-fe_config, rp1-cfe-fe_image0, ..., while
# upstream libcamera 0.5.2 looks for the mainline kernel names (rp1-cfe-fe-config, ...) and reports
# "Unable to acquire a CFE instance": no camera at all. Same 0.5.2 base, same licenses, same libpisp.
SRC_URI:raspberrypi5 = "git://github.com/raspberrypi/libcamera.git;protocol=https;nobranch=1"
# Tag v0.5.2+rpt20250903
SRCREV:raspberrypi5 = "bfd68f786964636b09f8122e6c09c230367390e7"
PV:raspberrypi5 = "0.5.2+rpt20250903"

# Build only the PiSP pipeline handler (and its IPA module), which needs libpisp.
# The default ("auto") also tries rpi/pisp, but would download libpisp at configure time and fail.
LIBCAMERA_PIPELINES:raspberrypi5 = "rpi/pisp"
DEPENDS:append:raspberrypi5 = " libpisp"

# libcamerasrc, the GStreamer element OpenCV reads the camera through (package libcamera-gst).
PACKAGECONFIG:append = " gst"
