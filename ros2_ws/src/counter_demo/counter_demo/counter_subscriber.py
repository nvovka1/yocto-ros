"""Subscribe to /counter and log every value received."""

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import UInt32


class CounterSubscriber(Node):

    def __init__(self):
        super().__init__('counter_subscriber')
        self.subscription = self.create_subscription(UInt32, 'counter', self.on_counter, 10)

    def on_counter(self, message):
        self.get_logger().info(f'Received: {message.data}')


def main(args=None):
    rclpy.init(args=args)
    node = CounterSubscriber()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
