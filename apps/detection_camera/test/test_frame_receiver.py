"""Unit tests for the background stream connection. Run from apps/detection_camera with: python -m pytest test"""

import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from detection_camera.frame_receiver import WAITING_TEXT, FrameReceiver

TIMEOUT_SECONDS = 5


def part(jpeg):
    return f'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: {len(jpeg)}\r\n\r\n'.encode() + jpeg + b'\r\n'


class FakeMjpegServer:
    """Serves /stream like the detector: sends `frames` and closes, or sends headers and stalls for `stall_seconds`."""

    def __init__(self, frames=(), stall_seconds=0):
        server = self

        class Handler(BaseHTTPRequestHandler):

            def do_GET(self):
                server.connection_count += 1
                self.send_response(200)
                self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
                self.end_headers()
                for jpeg in frames:
                    self.wfile.write(part(jpeg))
                self.wfile.flush()
                if stall_seconds:
                    server.stall_started.set()
                    server.stop_stalling.wait(stall_seconds)

            def log_message(self, format, *args):
                pass

        self.connection_count = 0
        self.stall_started = threading.Event()
        self.stop_stalling = threading.Event()
        self._http_server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self._http_server.daemon_threads = True
        threading.Thread(target=self._http_server.serve_forever, daemon=True).start()

    @property
    def url(self):
        return f'http://127.0.0.1:{self._http_server.server_address[1]}/stream'

    def close(self):
        self.stop_stalling.set()
        self._http_server.shutdown()
        self._http_server.server_close()


class Recorder:
    """Collects the receiver's callbacks and lets a test wait for a condition on them."""

    def __init__(self):
        self.frames = []
        self.statuses = []
        self._condition = threading.Condition()

    def on_frame(self, jpeg):
        with self._condition:
            self.frames.append(jpeg)
            self._condition.notify_all()

    def on_status(self, text):
        with self._condition:
            self.statuses.append(text)
            self._condition.notify_all()

    def wait_for(self, predicate):
        with self._condition:
            return self._condition.wait_for(predicate, TIMEOUT_SECONDS)


@pytest.fixture
def recorder():
    return Recorder()


def closed_port_url():
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    return f'http://127.0.0.1:{port}/stream'


def test_delivers_frames_from_the_stream(recorder):
    server = FakeMjpegServer(frames=[b'a', b'b'])
    receiver = FrameReceiver(server.url, recorder.on_frame, recorder.on_status, retry_seconds=60)
    receiver.start()
    try:
        assert recorder.wait_for(lambda: len(recorder.frames) >= 2)
        assert recorder.frames[:2] == [b'a', b'b']
    finally:
        receiver.stop()
        server.close()


def test_reports_waiting_when_nothing_listens(recorder):
    receiver = FrameReceiver(closed_port_url(), recorder.on_frame, recorder.on_status, retry_seconds=60)
    receiver.start()
    try:
        assert recorder.wait_for(lambda: WAITING_TEXT in recorder.statuses)
    finally:
        receiver.stop()


def test_reconnects_after_the_server_drops_the_connection(recorder):
    server = FakeMjpegServer(frames=[b'a'])
    receiver = FrameReceiver(server.url, recorder.on_frame, recorder.on_status, retry_seconds=0.1)
    receiver.start()
    try:
        assert recorder.wait_for(lambda: len(recorder.frames) >= 2)
        assert WAITING_TEXT in recorder.statuses
        assert server.connection_count >= 2
    finally:
        receiver.stop()
        server.close()


def test_reports_waiting_when_the_stream_stalls(recorder):
    server = FakeMjpegServer(frames=[b'a'], stall_seconds=30)
    receiver = FrameReceiver(server.url, recorder.on_frame, recorder.on_status, retry_seconds=60,
                             stalled_after_seconds=0.5)
    receiver.start()
    try:
        assert recorder.wait_for(lambda: recorder.frames)
        assert recorder.wait_for(lambda: WAITING_TEXT in recorder.statuses)
    finally:
        receiver.stop()
        server.close()


def test_status_is_cleared_when_a_frame_arrives(recorder):
    server = FakeMjpegServer(frames=[b'a'], stall_seconds=30)
    receiver = FrameReceiver(server.url, recorder.on_frame, recorder.on_status, retry_seconds=60)
    receiver.start()
    try:
        assert recorder.wait_for(lambda: recorder.frames)
        assert recorder.wait_for(lambda: '' in recorder.statuses)
    finally:
        receiver.stop()
        server.close()


def test_stop_returns_quickly_while_waiting_for_data(recorder):
    server = FakeMjpegServer(stall_seconds=30)
    receiver = FrameReceiver(server.url, recorder.on_frame, recorder.on_status, retry_seconds=60)
    receiver.start()
    try:
        assert server.stall_started.wait(TIMEOUT_SECONDS)
        started = time.monotonic()
        receiver.stop()
        assert time.monotonic() - started < 1
        assert not receiver.is_running
    finally:
        server.close()
