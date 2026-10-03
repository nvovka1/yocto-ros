"""Call /counter/enable once to start or stop the counter, then exit.

Usage: ros2 run counter_demo counter_controller start|stop
"""

import sys

import rclpy
from rclpy.utilities import remove_ros_args
from std_srvs.srv import SetBool


def main(args=None):
    rclpy.init(args=args)
    # Drop the --ros-args part so only our own arguments remain.
    arguments = remove_ros_args(args=sys.argv)[1:]

    if arguments not in (['start'], ['stop']):
        print('Usage: counter_controller start|stop', file=sys.stderr)
        rclpy.try_shutdown()
        return 1

    node = rclpy.create_node('counter_controller')
    client = node.create_client(SetBool, 'counter/enable')
    exit_code = 1
    try:
        if not client.wait_for_service(timeout_sec=5.0):
            node.get_logger().error('Service /counter/enable is not available')
            return exit_code

        request = SetBool.Request()
        request.data = arguments[0] == 'start'
        future = client.call_async(request)
        rclpy.spin_until_future_complete(node, future)

        response = future.result()
        if response is None:
            node.get_logger().error('Call to /counter/enable failed')
            return exit_code

        node.get_logger().info(response.message)
        exit_code = 0
        return exit_code
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    sys.exit(main())
