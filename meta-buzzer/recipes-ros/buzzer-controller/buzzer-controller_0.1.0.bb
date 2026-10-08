SUMMARY = "Sounds a PWM buzzer while an object is detected, louder the closer it is (Python)"
DESCRIPTION = "Subscribes to /object_distance (std_msgs/Float32, metres) and drives a passive buzzer \
on GPIO 12 through the hardware PWM: close objects loud, far objects quiet, nothing detected silent."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=714456307d8622c584e969bccb77dfdf"

# Source lives in this repository (ros2_ws/src/buzzer_controller), the same code you build with colcon on the host.
FILESEXTRAPATHS:prepend := "${YOCTO_ROS_REPOSITORY_ROOT}/ros2_ws/src:"
SRC_URI = "file://buzzer_controller"
S = "${WORKDIR}/buzzer_controller"

# Same dependency layout meta-ros generates from package.xml for upstream packages.
# Pure Python: nothing to compile against, everything is needed at run time on the target.
ROS_BUILD_DEPENDS = ""

ROS_BUILDTOOL_DEPENDS = ""

ROS_EXEC_DEPENDS = " \
    ament-index-python \
    launch-ros \
    rclpy \
    std-msgs \
"

DEPENDS = "${ROS_BUILD_DEPENDS} ${ROS_BUILDTOOL_DEPENDS}"
RDEPENDS:${PN} += "${ROS_EXEC_DEPENDS}"

ROS_BUILD_TYPE = "ament_python"

inherit ros_distro_${ROS_DISTRO}
inherit ros_component
inherit ros_${ROS_BUILD_TYPE}
