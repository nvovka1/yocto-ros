SUMMARY = "Touch calibration for the 3.5 inch ADS7846 touch screen"
DESCRIPTION = "udev rule that gives libinput a calibration matrix, so the pen reaches the whole screen."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://99-touchscreen-calibration.rules"
S = "${WORKDIR}"

inherit allarch

do_install() {
    install -d ${D}${sysconfdir}/udev/rules.d
    install -m 0644 ${WORKDIR}/99-touchscreen-calibration.rules ${D}${sysconfdir}/udev/rules.d/
}

FILES:${PN} = "${sysconfdir}/udev/rules.d/99-touchscreen-calibration.rules"
