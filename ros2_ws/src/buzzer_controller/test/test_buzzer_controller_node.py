"""Unit tests for BuzzerControllerNode, without hardware. Run with: colcon test --packages-select buzzer_controller"""

import rclpy
from rclpy.parameter import Parameter
from std_msgs.msg import Float32

from buzzer_controller.buzzer_controller_node import BuzzerControllerNode


class FakeClock:

    def __init__(self):
        self.seconds = 0.0

    def __call__(self):
        return self.seconds


def setup_module():
    rclpy.init()


def teardown_module():
    rclpy.shutdown()


def create_node(clock):
    return BuzzerControllerNode(now=clock, parameter_overrides=[Parameter('enabled', value=False)])


def test_close_object_is_louder_than_far_object():
    node = create_node(FakeClock())
    try:
        node.on_distance(Float32(data=0.2))
        close_volume = node.buzzer.volume
        node.on_distance(Float32(data=1.5))
        assert close_volume == 1.0
        assert 0 < node.buzzer.volume < close_volume
    finally:
        node.destroy_node()


def test_goes_silent_when_distances_stop_arriving():
    clock = FakeClock()
    node = create_node(clock)
    try:
        node.on_distance(Float32(data=0.5))

        clock.seconds = 0.4
        node.silence_if_object_lost()
        assert node.buzzer.volume > 0

        clock.seconds = 0.6
        node.silence_if_object_lost()
        assert node.buzzer.volume == 0.0
    finally:
        node.destroy_node()
