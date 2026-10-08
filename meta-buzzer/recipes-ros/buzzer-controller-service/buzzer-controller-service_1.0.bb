SUMMARY = "Starts the ROS 2 buzzer controller at boot"
DESCRIPTION = "systemd service that runs `ros2 launch buzzer_controller buzzer_controller.launch.py`. \
Logs: journalctl -u buzzer-controller. Stop: systemctl stop buzzer-controller."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://buzzer-controller.service"
S = "${WORKDIR}"

inherit allarch systemd

# The systemd class enables the service in the image, like `systemctl enable buzzer-controller`.
SYSTEMD_SERVICE:${PN} = "buzzer-controller.service"
SYSTEMD_AUTO_ENABLE = "enable"

do_install() {
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/buzzer-controller.service ${D}${systemd_system_unitdir}/buzzer-controller.service
}

FILES:${PN} = "${systemd_system_unitdir}/buzzer-controller.service"
RDEPENDS:${PN} = "buzzer-controller ros-setup-profile ros2launch"
