# 3.5" SPI touch screen, 320x480 (ILI9486 panel + ADS7846/XPT2046 touch, sold as "3.5inch RPi LCD (A)").
# It sits on pins 1-26: SPI0 (GPIO 7-11), touch interrupt GPIO 17, backlight GPIO 22, DC GPIO 24, reset GPIO 25.
# The piscreen overlay has the same wiring; its "drm" parameter selects the DRM driver (ili9486.ko) instead of the
# old fbtft one, so GNOME sees the screen as a normal display. rotate=0 is the panel's native portrait 320x480.
# invx: with rotate=0 the touch's left/right is mirrored against the picture (measured on the board: a tap in the
# top-left corner landed bottom-right with invy, and correctly with invx). The edge-to-edge scaling is a libinput
# calibration matrix (touchscreen-calibration recipe).
ENABLE_SPI_BUS = "1"
RPI_EXTRA_CONFIG:append = "\n# 3.5 inch touch screen (DRM driver, portrait)\ndtoverlay=piscreen,drm,rotate=0,invx\n"
