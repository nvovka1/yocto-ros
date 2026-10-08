# Start from the object detection image (meta-object-detection) and add the buzzer on top.
require recipes-core/images/ros-detection-image.bb

SUMMARY = "Raspberry Pi 5 ROS 2 image with camera object detection and a distance buzzer"
DESCRIPTION = "${SUMMARY}"

IMAGE_INSTALL:append = " \
    buzzer-controller \
    buzzer-controller-service \
"
