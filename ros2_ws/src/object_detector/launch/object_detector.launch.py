"""Start the object detector with the parameters from config/object_detector.yaml."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    parameters_file = os.path.join(get_package_share_directory('object_detector'), 'config', 'object_detector.yaml')
    return LaunchDescription([
        Node(
            package='object_detector',
            executable='object_detector',
            output='screen',
            parameters=[parameters_file],
        ),
    ])
