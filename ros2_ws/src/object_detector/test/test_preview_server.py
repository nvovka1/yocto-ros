"""Unit tests for the live view. Run with: colcon test --packages-select object_detector"""

import http.client
import threading

import numpy as np
import pytest

from object_detector.preview_server import OTHER_COLOR, TARGET_COLOR, PreviewServer, draw_detections
from object_detector.yolo_detector import Detection


def black_frame():
    return np.zeros((480, 640, 3), dtype=np.uint8)


@pytest.fixture
def server():
    preview = PreviewServer(port=0, host='127.0.0.1')
    yield preview
    preview.close()


def test_draws_the_target_green_and_other_detections_gray():
    target = Detection(0, 'bibi', 0.9, 100, 100, 200, 150)
    other = Detection(0, 'bibi', 0.6, 400, 300, 100, 100)
    frame = black_frame()

    image = draw_detections(frame, [target, other], target, 0.8)

    assert tuple(image[200, 100]) == TARGET_COLOR
    assert tuple(image[350, 400]) == OTHER_COLOR
    assert not frame.any()  # the original frame is left alone


def test_label_of_a_box_at_the_top_edge_stays_inside_the_image():
    detection = Detection(0, 'bibi', 0.9, 50, 0, 100, 100)

    image = draw_detections(black_frame(), [detection], detection, 0.5)

    assert image[0:10, 50:100].any()


def test_page_shows_the_stream(server):
    connection = http.client.HTTPConnection('127.0.0.1', server.port, timeout=5)
    connection.request('GET', '/')
    response = connection.getresponse()

    assert response.status == 200
    assert b'src="/stream"' in response.read()


def test_unknown_path_is_not_found(server):
    connection = http.client.HTTPConnection('127.0.0.1', server.port, timeout=5)
    connection.request('GET', '/secret')

    assert connection.getresponse().status == 404


def test_stream_sends_published_frames_as_jpeg(server):
    assert not server.has_viewers
    stop = threading.Event()

    def publish_until_stopped():
        while not stop.is_set():
            if server.has_viewers:
                server.publish(black_frame())
            stop.wait(0.05)

    publisher = threading.Thread(target=publish_until_stopped)
    publisher.start()
    try:
        connection = http.client.HTTPConnection('127.0.0.1', server.port, timeout=5)
        connection.request('GET', '/stream')
        response = connection.getresponse()
        assert response.status == 200
        assert response.getheader('Content-Type') == 'multipart/x-mixed-replace; boundary=frame'

        first_part = response.read(200)
        assert first_part.startswith(b'--frame\r\nContent-Type: image/jpeg')
        assert b'\xff\xd8' in first_part  # JPEG start marker
        assert server.has_viewers
        connection.close()
    finally:
        stop.set()
        publisher.join()
