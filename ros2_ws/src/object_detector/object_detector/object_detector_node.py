"""Detect the trained object in the camera image and publish its estimated distance on /object_distance.

Only frames that contain the object produce a message; when it leaves the frame the messages stop, and
listeners (buzzer_controller) treat silence as "nothing detected".
"""

import os
import time

import rclpy
from ament_index_python.packages import get_package_share_directory
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import Float32

from object_detector.distance_estimator import DistanceEstimator
from object_detector.frame_source import DEFAULT_CAMERA_PIPELINE, open_source
from object_detector.preview_server import PreviewServer, draw_detections
from object_detector.yolo_detector import YoloDetector

STATISTICS_PERIOD_S = 10.0


def default_model_path():
    return os.path.join(get_package_share_directory('object_detector'), 'models', 'my_model.onnx')


def closest_target(detections, target_class):
    """The biggest box of `target_class` (any class when it is empty): the biggest box is the closest object."""
    targets = [detection for detection in detections if not target_class or detection.class_name == target_class]
    return max(targets, key=lambda detection: detection.area, default=None)


class ObjectDetectorNode(Node):

    def __init__(self):
        super().__init__('object_detector')

        # Defaults match config/object_detector.yaml, which the launch file loads.
        source = self.declare_parameter('source', 'camera').value
        camera_pipeline = self.declare_parameter('camera_pipeline', DEFAULT_CAMERA_PIPELINE).value
        self.frame_width = self.declare_parameter('frame_width', 640).value
        self.frame_height = self.declare_parameter('frame_height', 480).value
        model_path = self.declare_parameter('model_path', '').value or default_model_path()
        class_names = self.declare_parameter('class_names', ['bibi']).value
        self.target_class = self.declare_parameter('target_class', 'bibi').value
        input_size = self.declare_parameter('input_size', 640).value
        confidence_threshold = self.declare_parameter('confidence_threshold', 0.5).value
        nms_threshold = self.declare_parameter('nms_threshold', 0.45).value
        reference_distance_m = self.declare_parameter('reference_distance_m', 1.0).value
        reference_area_fraction = self.declare_parameter('reference_area_fraction', 0.05).value
        period_ms = self.declare_parameter('period_ms', 100).value
        preview_port = self.declare_parameter('preview_port', 8080).value

        self.detector = YoloDetector(model_path, class_names, input_size, confidence_threshold, nms_threshold)
        self.distance_estimator = DistanceEstimator(reference_distance_m, reference_area_fraction)
        self.source = open_source(source, self.frame_width, self.frame_height, camera_pipeline)

        self.publisher = self.create_publisher(Float32, 'object_distance', 10)
        # Inference takes longer than the period on a Pi, so in practice this runs as fast as the model allows.
        self.timer = self.create_timer(period_ms / 1000.0, self.process_next_frame)

        # Frame rate, logged every STATISTICS_PERIOD_S so the speed of the model on this board is visible.
        self.frames_since_statistics = 0
        self.statistics_started_at = time.monotonic()
        self.frames_per_second = 0.0

        # Live view in a browser (preview_server.py); 0 turns it off.
        self.preview = PreviewServer(preview_port) if preview_port else None
        if self.preview is not None:
            self.get_logger().info(f'Live view: http://<board address>:{self.preview.port}')

        self.get_logger().info(
            f'Detecting "{self.target_class or "any class"}" with {model_path} '
            f'({self.frame_width}x{self.frame_height} from {source})')

    def process_next_frame(self):
        frame = self.source.read()
        detections = self.detector.detect(frame)
        target = closest_target(detections, self.target_class)
        self.log_frame_rate()

        distance_m = None
        if target is not None:
            frame_height, frame_width = frame.shape[:2]
            area_fraction = target.area / (frame_width * frame_height)
            distance_m = self.distance_estimator.estimate(area_fraction)
            self.publisher.publish(Float32(data=distance_m))

            # The area is what you need for calibration (reference_area_fraction), so it is always logged.
            self.get_logger().info(
                f'{target.class_name} {target.confidence:.2f}: area {area_fraction:.4f} of the frame, '
                f'distance {distance_m:.2f} m',
                throttle_duration_sec=1.0)

        if self.preview is not None and self.preview.has_viewers:
            status = f'{self.frames_per_second:.1f} frames/s' if self.frames_per_second else ''
            self.preview.publish(draw_detections(frame, detections, target, distance_m, status))

    def log_frame_rate(self):
        self.frames_since_statistics += 1
        elapsed_s = time.monotonic() - self.statistics_started_at
        if elapsed_s >= STATISTICS_PERIOD_S:
            self.frames_per_second = self.frames_since_statistics / elapsed_s
            self.get_logger().info(f'{self.frames_per_second:.1f} frames/s')
            self.frames_since_statistics = 0
            self.statistics_started_at = time.monotonic()

    def destroy_node(self):
        if self.preview is not None:
            self.preview.close()
        self.source.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = ObjectDetectorNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
