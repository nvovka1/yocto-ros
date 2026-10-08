SUMMARY = "Starts the ROS 2 object detector at boot"
DESCRIPTION = "systemd service that runs `ros2 launch object_detector object_detector.launch.py`. \
Logs: journalctl -u object-detector. Stop: systemctl stop object-detector."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://object-detector.service"
S = "${WORKDIR}"

inherit allarch systemd

# The systemd class enables the service in the image, like `systemctl enable object-detector`.
SYSTEMD_SERVICE:${PN} = "object-detector.service"
SYSTEMD_AUTO_ENABLE = "enable"

do_install() {
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/object-detector.service ${D}${systemd_system_unitdir}/object-detector.service
}

FILES:${PN} = "${systemd_system_unitdir}/object-detector.service"
RDEPENDS:${PN} = "object-detector ros-setup-profile ros2launch"
