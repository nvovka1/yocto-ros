SUMMARY = "Detects a trained YOLO object in the camera image and publishes its distance (Python)"
DESCRIPTION = "Runs the YOLO11 model (models/my_model.onnx) on the Raspberry Pi camera with OpenCV DNN \
and publishes the estimated distance to the object on /object_distance (std_msgs/Float32, metres)."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=714456307d8622c584e969bccb77dfdf"

# Source lives in this repository (ros2_ws/src/object_detector), the same code you build with colcon on the host.
FILESEXTRAPATHS:prepend := "${YOCTO_ROS_REPOSITORY_ROOT}/ros2_ws/src:"
SRC_URI = "file://object_detector"
S = "${WORKDIR}/object_detector"

# Same dependency layout meta-ros generates from package.xml for upstream packages.
# Pure Python: nothing to compile against, everything is needed at run time on the target.
ROS_BUILD_DEPENDS = ""

ROS_BUILDTOOL_DEPENDS = ""

# python3-opencv comes with the DNN module: meta-ros-common's opencv bbappend enables it.
ROS_EXEC_DEPENDS = " \
    ament-index-python \
    launch-ros \
    python3-numpy \
    python3-opencv \
    rclpy \
    std-msgs \
"

# The camera: libcamera's GStreamer element plus the GStreamer plugins the capture pipeline uses
# (videoconvert lives in videoconvertscale since GStreamer 1.22, appsink in app).
CAMERA_EXEC_DEPENDS = " \
    libcamera \
    libcamera-gst \
    gstreamer1.0-plugins-base-app \
    gstreamer1.0-plugins-base-videoconvertscale \
"

DEPENDS = "${ROS_BUILD_DEPENDS} ${ROS_BUILDTOOL_DEPENDS}"
RDEPENDS:${PN} += "${ROS_EXEC_DEPENDS} ${CAMERA_EXEC_DEPENDS}"

ROS_BUILD_TYPE = "ament_python"

inherit ros_distro_${ROS_DISTRO}
inherit ros_component
inherit ros_${ROS_BUILD_TYPE}
