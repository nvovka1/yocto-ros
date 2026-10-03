# Load the ROS 2 environment (AMENT_PREFIX_PATH, ROS_DISTRO, ...) for login shells.
# meta-ros installs ROS into /usr; /opt/ros/<distro> is checked as a fallback.
for ros_setup_file in /usr/setup.sh /opt/ros/*/setup.sh; do
    if [ -f "$ros_setup_file" ]; then
        . "$ros_setup_file"
        break
    fi
done
unset ros_setup_file
