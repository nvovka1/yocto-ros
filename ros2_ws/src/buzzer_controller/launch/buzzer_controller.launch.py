"""Start the buzzer controller with the parameters from config/buzzer_controller.yaml."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    parameters_file = os.path.join(get_package_share_directory('buzzer_controller'), 'config', 'buzzer_controller.yaml')
    return LaunchDescription([
        Node(
            package='buzzer_controller',
            executable='buzzer_controller',
            output='screen',
            parameters=[parameters_file],
        ),
    ])
