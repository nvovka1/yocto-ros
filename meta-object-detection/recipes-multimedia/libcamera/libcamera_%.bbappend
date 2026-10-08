# Raspberry Pi 5 camera: build only the PiSP pipeline handler (and its IPA module), which needs libpisp.
# The default ("auto") also tries rpi/pisp, but would download libpisp at configure time and fail.
LIBCAMERA_PIPELINES:raspberrypi5 = "rpi/pisp"
DEPENDS:append:raspberrypi5 = " libpisp"

# libcamerasrc, the GStreamer element OpenCV reads the camera through (package libcamera-gst).
PACKAGECONFIG:append = " gst"
