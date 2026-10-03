# Start from the base OS (meta-rpi-base) and add ROS 2 on top.
require recipes-core/images/rpi-base-image.bb

SUMMARY = "Raspberry Pi 5 base image plus ROS 2 core and the counter demo"
DESCRIPTION = "${SUMMARY}"

# Gives the image the ROS 2 settings and appends -${ROS_DISTRO} to the image name.
inherit ros_distro_${ROS_DISTRO}
inherit ${ROS_DISTRO_TYPE}_image

IMAGE_INSTALL:append = " \
    ros-core \
    demo-nodes-py \
    counter-demo \
    ros-setup-profile \
"
