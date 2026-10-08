"""Sound the buzzer while an object is detected: louder the closer it is (/object_distance, metres).

object_detector only publishes while it sees the object, so no message for `silence_after_ms` means
nothing is detected and the buzzer goes quiet.
"""

import time
from pathlib import Path

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import Float32

from buzzer_controller.pwm_buzzer import SYSFS_PWM_ROOT, LoggingBuzzer, SysfsPwmBuzzer, find_pwm_chip
from buzzer_controller.volume_mapping import VolumeMapping


class BuzzerControllerNode(Node):

    def __init__(self, now=time.monotonic, **node_options):
        super().__init__('buzzer_controller', **node_options)

        # Defaults match config/buzzer_controller.yaml, which the launch file loads.
        is_enabled = self.declare_parameter('enabled', True).value
        pwm_chip = self.declare_parameter('pwm_chip', -1).value
        pwm_channel = self.declare_parameter('pwm_channel', 0).value
        frequency_hz = self.declare_parameter('frequency_hz', 2000.0).value
        self.volume_mapping = VolumeMapping(
            near_distance_m=self.declare_parameter('near_distance_m', 0.3).value,
            far_distance_m=self.declare_parameter('far_distance_m', 2.0).value,
            min_volume=self.declare_parameter('min_volume', 0.05).value,
        )
        self.silence_after_s = self.declare_parameter('silence_after_ms', 500).value / 1000.0

        if is_enabled:
            chip_path = find_pwm_chip() if pwm_chip < 0 else SYSFS_PWM_ROOT / f'pwmchip{pwm_chip}'
            self.buzzer = SysfsPwmBuzzer(chip_path, pwm_channel, frequency_hz)
            target = f'{Path(chip_path).name}/pwm{pwm_channel}'
        else:
            self.buzzer = LoggingBuzzer()
            target = 'no hardware (enabled: false)'

        self.now = now
        self.last_distance_at = None
        self.volume = 0.0

        self.subscription = self.create_subscription(Float32, 'object_distance', self.on_distance, 10)
        self.silence_timer = self.create_timer(0.1, self.silence_if_object_lost)

        self.get_logger().info(f'Buzzer on {target}, {frequency_hz:.0f} Hz')

    def on_distance(self, message):
        self.last_distance_at = self.now()
        self.set_volume(self.volume_mapping.volume_for(message.data))
        self.get_logger().info(f'Object at {message.data:.2f} m, volume {self.volume:.2f}', throttle_duration_sec=1.0)

    def silence_if_object_lost(self):
        if self.last_distance_at is not None and self.now() - self.last_distance_at > self.silence_after_s:
            self.last_distance_at = None
            self.set_volume(0.0)
            self.get_logger().info('Object lost, buzzer off')

    def set_volume(self, volume):
        self.volume = volume
        self.buzzer.set_volume(volume)

    def destroy_node(self):
        self.buzzer.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = BuzzerControllerNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
