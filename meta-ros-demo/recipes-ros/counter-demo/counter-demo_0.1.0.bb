SUMMARY = "Counter publisher and subscriber with a start/stop service (Python)"
DESCRIPTION = "Publishes 1, 2, 3, ... on /counter. The /counter/enable service \
(std_srvs/SetBool) starts or stops counting."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=714456307d8622c584e969bccb77dfdf"

# Source lives in this repository (ros2_ws/src/counter_demo), the same code you build with colcon on the host.
FILESEXTRAPATHS:prepend := "${YOCTO_ROS_REPOSITORY_ROOT}/ros2_ws/src:"
SRC_URI = "file://counter_demo"
S = "${WORKDIR}/counter_demo"

# Same dependency layout meta-ros generates from package.xml for upstream packages.
# Pure Python: nothing to compile against, everything is needed at run time on the target.
ROS_BUILD_DEPENDS = ""

ROS_BUILDTOOL_DEPENDS = ""

ROS_EXEC_DEPENDS = " \
    launch-ros \
    rclpy \
    std-msgs \
    std-srvs \
"

DEPENDS = "${ROS_BUILD_DEPENDS} ${ROS_BUILDTOOL_DEPENDS}"
RDEPENDS:${PN} += "${ROS_EXEC_DEPENDS}"

ROS_BUILD_TYPE = "ament_python"

inherit ros_distro_${ROS_DISTRO}
inherit ros_component
inherit ros_${ROS_BUILD_TYPE}
