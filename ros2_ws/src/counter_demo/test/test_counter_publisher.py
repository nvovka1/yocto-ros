"""Unit tests for CounterPublisher. Run with: colcon test --packages-select counter_demo"""

import rclpy
from std_srvs.srv import SetBool

from counter_demo.counter_publisher import CounterPublisher


def setup_module():
    rclpy.init()


def teardown_module():
    rclpy.shutdown()


def test_publishes_incrementing_values():
    node = CounterPublisher()
    try:
        node.publish_next_value()
        node.publish_next_value()
        assert node.counter == 2
    finally:
        node.destroy_node()


def test_stop_pauses_counting_and_start_resumes():
    node = CounterPublisher()
    try:
        node.publish_next_value()

        response = node.set_enabled(SetBool.Request(data=False), SetBool.Response())
        node.publish_next_value()
        assert response.success
        assert node.counter == 1

        node.set_enabled(SetBool.Request(data=True), SetBool.Response())
        node.publish_next_value()
        assert node.counter == 2
    finally:
        node.destroy_node()
