# Start from the ROS 2 image (meta-ros-demo) and add the camera and the object detector on top.
require recipes-core/images/ros-counter-image.bb

SUMMARY = "Raspberry Pi 5 ROS 2 image plus camera object detection"
DESCRIPTION = "${SUMMARY}"

IMAGE_INSTALL:append = " \
    object-detector \
    object-detector-service \
"
