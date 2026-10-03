SUMMARY = "Sources the ROS 2 environment for every login shell"
DESCRIPTION = "Installs /etc/profile.d/ros-setup.sh so ros2 commands work right after SSH login."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://ros-setup.sh"
S = "${WORKDIR}"

do_install() {
    install -d ${D}${sysconfdir}/profile.d
    install -m 0644 ${WORKDIR}/ros-setup.sh ${D}${sysconfdir}/profile.d/ros-setup.sh
}

FILES:${PN} = "${sysconfdir}/profile.d/ros-setup.sh"
RDEPENDS:${PN} = "ros-workspace"
