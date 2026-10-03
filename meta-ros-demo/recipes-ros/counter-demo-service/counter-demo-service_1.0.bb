SUMMARY = "Starts the ROS 2 counter demo at boot"
DESCRIPTION = "systemd service that runs `ros2 launch counter_demo counter_demo.launch.py`. \
Logs: journalctl -u counter-demo. Stop: systemctl stop counter-demo."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://counter-demo.service"
S = "${WORKDIR}"

inherit allarch systemd

# The systemd class enables the service in the image, like `systemctl enable counter-demo`.
SYSTEMD_SERVICE:${PN} = "counter-demo.service"
SYSTEMD_AUTO_ENABLE = "enable"

do_install() {
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/counter-demo.service ${D}${systemd_system_unitdir}/counter-demo.service
}

FILES:${PN} = "${systemd_system_unitdir}/counter-demo.service"
RDEPENDS:${PN} = "counter-demo ros-setup-profile ros2launch"
