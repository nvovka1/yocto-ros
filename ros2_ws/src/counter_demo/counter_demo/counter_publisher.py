"""Publish 1, 2, 3, ... on /counter and serve /counter/enable to start or stop counting."""

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import UInt32
from std_srvs.srv import SetBool


class CounterPublisher(Node):

    def __init__(self):
        super().__init__('counter_publisher')

        # Parameters can be overridden: ros2 run counter_demo counter_publisher --ros-args -p period_ms:=500
        period_ms = self.declare_parameter('period_ms', 1000).value
        self.is_enabled = self.declare_parameter('start_enabled', True).value
        self.counter = 0

        self.publisher = self.create_publisher(UInt32, 'counter', 10)
        self.timer = self.create_timer(period_ms / 1000.0, self.publish_next_value)
        self.enable_service = self.create_service(SetBool, 'counter/enable', self.set_enabled)

        state = 'started' if self.is_enabled else 'stopped'
        self.get_logger().info(f'Counter {state}, publishing every {period_ms} ms')

    def publish_next_value(self):
        if not self.is_enabled:
            return

        self.counter += 1
        message = UInt32()
        message.data = self.counter
        self.publisher.publish(message)
        self.get_logger().info(f'Published: {message.data}')

    def set_enabled(self, request, response):
        self.is_enabled = request.data
        response.success = True
        response.message = 'Counter started' if self.is_enabled else 'Counter stopped'
        self.get_logger().info(f'{response.message} at {self.counter}')
        return response


def main(args=None):
    rclpy.init(args=args)
    node = CounterPublisher()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
