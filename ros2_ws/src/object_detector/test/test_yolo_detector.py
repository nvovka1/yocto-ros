"""Unit tests for the YOLO pre- and post-processing. Run with: colcon test --packages-select object_detector"""

import numpy as np
import pytest

from object_detector.yolo_detector import Letterbox, decode_output, letterbox


def model_output(*candidates, class_count=1):
    """Raw YOLO11 output (1, 4 + classes, candidates) from (cx, cy, w, h, score per class...) tuples."""
    return np.array(candidates, dtype=np.float32).T.reshape(1, 4 + class_count, len(candidates))


def test_letterbox_fits_a_wide_frame_into_a_padded_square():
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)

    image, placement = letterbox(frame, 640)

    assert image.shape == (640, 640, 3)
    assert placement == Letterbox(scale=0.5, pad_x=0, pad_y=140)
    assert tuple(image[0, 0]) == (114, 114, 114)
    assert tuple(image[320, 320]) == (0, 0, 0)


def test_letterbox_puts_the_odd_pixel_of_padding_at_the_bottom():
    frame = np.zeros((98, 200, 3), dtype=np.uint8)

    image, placement = letterbox(frame, 100)

    # 200x98 -> 100x49, leaving 51 rows of padding: 25 above, 26 below.
    assert image.shape == (100, 100, 3)
    assert placement.pad_y == 25
    assert tuple(image[25 + 49, 50]) == (114, 114, 114)
    assert tuple(image[25 + 48, 50]) == (0, 0, 0)


def test_decode_maps_a_box_back_to_frame_pixels():
    # 1280x720 frame -> scale 0.5, 140 px of padding at the top.
    placement = Letterbox(scale=0.5, pad_x=0, pad_y=140)
    output = model_output((320, 320, 100, 50, 0.9))

    detections = decode_output(output, placement, 1280, 720, ['bibi'], 0.5, 0.45)

    assert len(detections) == 1
    detection = detections[0]
    assert detection.class_name == 'bibi'
    assert detection.confidence == pytest.approx(0.9)
    assert (detection.x, detection.y, detection.width, detection.height) == pytest.approx((540, 310, 200, 100))
    assert detection.area == pytest.approx(20000)


def test_decode_drops_low_confidence_candidates():
    output = model_output((320, 320, 100, 50, 0.3))

    assert decode_output(output, Letterbox(1.0, 0, 0), 640, 640, ['bibi'], 0.5, 0.45) == []


def test_decode_merges_overlapping_boxes_into_the_most_confident():
    output = model_output((320, 320, 100, 100, 0.7), (322, 322, 100, 100, 0.95), (100, 100, 40, 40, 0.8))

    detections = decode_output(output, Letterbox(1.0, 0, 0), 640, 640, ['bibi'], 0.5, 0.45)

    assert [round(detection.confidence, 2) for detection in detections] == [0.95, 0.8]


def test_decode_picks_the_best_class_for_each_candidate():
    output = model_output((320, 320, 100, 100, 0.1, 0.8), class_count=2)

    detections = decode_output(output, Letterbox(1.0, 0, 0), 640, 640, ['cat', 'dog'], 0.5, 0.45)

    assert [(detection.class_id, detection.class_name) for detection in detections] == [(1, 'dog')]


def test_decode_clips_boxes_to_the_frame():
    output = model_output((10, 10, 100, 100, 0.9))

    detection = decode_output(output, Letterbox(1.0, 0, 0), 640, 640, ['bibi'], 0.5, 0.45)[0]

    assert (detection.x, detection.y, detection.width, detection.height) == pytest.approx((0, 0, 60, 60))
