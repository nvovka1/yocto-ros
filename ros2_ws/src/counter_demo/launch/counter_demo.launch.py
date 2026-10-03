"""Start the counter publisher and subscriber together."""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='counter_demo',
            executable='counter_publisher',
            output='screen',
            parameters=[{'period_ms': 1000, 'start_enabled': True}],
        ),
        Node(
            package='counter_demo',
            executable='counter_subscriber',
            output='screen',
        ),
    ])
