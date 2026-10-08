SUMMARY = "Raspberry Pi 5 ISP (PiSP) helper library"
DESCRIPTION = "Configures the Raspberry Pi 5 image signal processor. libcamera's rpi/pisp \
pipeline handler (the Raspberry Pi 5 camera support) cannot be built without it."
HOMEPAGE = "https://github.com/raspberrypi/libpisp"
LICENSE = "BSD-2-Clause"
LIC_FILES_CHKSUM = "file://LICENSE;md5=3417a46e992fdf62e5759fba9baef7a7"

# Tag v1.2.1: the version libcamera 0.5.2 pins in subprojects/libpisp.wrap.
SRC_URI = "git://github.com/raspberrypi/libpisp.git;protocol=https;branch=main"
SRCREV = "981977ff21f32c8a97d2a0ecbdff3e39d42ccce3"

S = "${WORKDIR}/git"

DEPENDS = "nlohmann-json"

inherit meson pkgconfig

# Logging would pull in Boost.Log; libcamera does its own logging.
EXTRA_OEMESON = "-Dlogging=disabled -Dexamples=false"
