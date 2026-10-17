"""Keeps a connection to the detector's live view open in a background thread and hands out every frame.

When the detector isn't there (still starting, restarting) or its stream stops moving, it reports WAITING_TEXT and
tries again.
"""

import socket
import threading
from urllib.parse import urlsplit

from detection_camera.mjpeg_stream import boundary_from_content_type, iter_jpeg_frames

WAITING_TEXT = 'Waiting for camera…'
CONNECT_TIMEOUT_SECONDS = 5
# How often a blocked read wakes up to see whether stop() was called. Waking up a blocked recv() from another thread
# with shutdown() works on Linux but not on Windows, so the receiver polls instead.
POLL_SECONDS = 0.25
STOP_TIMEOUT_SECONDS = 2
MAX_LINE_BYTES = 65536


class StoppedError(Exception):
    """stop() was called while the receiver was waiting for data."""


class StalledError(OSError):
    """No data arrived for `stalled_after_seconds`."""


class SocketReader:
    """readline()/read(n) over a socket with a short timeout, giving up when `stopping` is set or the stream stalls."""

    def __init__(self, connection_socket, stopping, stalled_after_seconds):
        self._socket = connection_socket
        self._stopping = stopping
        self._stalled_after_polls = max(1, round(stalled_after_seconds / POLL_SECONDS))
        self._buffer = bytearray()

    def readline(self):
        while True:
            end = self._buffer.find(b'\n')
            if end >= 0:
                return self._take(end + 1)
            if len(self._buffer) > MAX_LINE_BYTES:
                raise ValueError('Line too long in the live view stream')
            if not self._receive():
                return self._take(len(self._buffer))

    def read(self, size):
        while len(self._buffer) < size:
            if not self._receive():
                break
        return self._take(min(size, len(self._buffer)))

    def _take(self, size):
        data = bytes(self._buffer[:size])
        del self._buffer[:size]
        return data

    def _receive(self):
        """Append the next chunk to the buffer; False at the end of the stream."""
        for _ in range(self._stalled_after_polls):
            if self._stopping.is_set():
                raise StoppedError()
            try:
                chunk = self._socket.recv(65536)
            except socket.timeout:
                continue
            self._buffer += chunk
            return bool(chunk)
        raise StalledError('The live view stream stalled')


class FrameReceiver:
    """Calls `on_frame(jpeg_bytes)` for every frame of the MJPEG stream at `url`, and `on_status(text)` when the
    connection is lost (WAITING_TEXT) or comes back (''). Both callbacks run on the receiver's own thread."""

    def __init__(self, url, on_frame, on_status, retry_seconds=2.0, stalled_after_seconds=10.0):
        parts = urlsplit(url)
        self._host = parts.hostname
        self._port = parts.port or 80
        self._path = (parts.path or '/') + (f'?{parts.query}' if parts.query else '')
        self._on_frame = on_frame
        self._on_status = on_status
        self._retry_seconds = retry_seconds
        self._stalled_after_seconds = stalled_after_seconds
        self._stopping = threading.Event()
        self._thread = None

    @property
    def is_running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        self._stopping.clear()
        self._thread = threading.Thread(target=self._run, name='frame-receiver', daemon=True)
        self._thread.start()

    def stop(self):
        self._stopping.set()
        if self._thread is not None:
            self._thread.join(STOP_TIMEOUT_SECONDS)

    def _run(self):
        while not self._stopping.is_set():
            try:
                self._receive_until_disconnected()
            except StoppedError:
                break
            except (OSError, ValueError):
                pass
            if self._stopping.is_set():
                break
            self._on_status(WAITING_TEXT)
            self._stopping.wait(self._retry_seconds)

    def _receive_until_disconnected(self):
        with socket.create_connection((self._host, self._port), timeout=CONNECT_TIMEOUT_SECONDS) as connection:
            connection.settimeout(POLL_SECONDS)
            request = f'GET {self._path} HTTP/1.0\r\nHost: {self._host}:{self._port}\r\n\r\n'
            connection.sendall(request.encode('ascii'))
            reader = SocketReader(connection, self._stopping, self._stalled_after_seconds)
            boundary = boundary_from_content_type(read_response_headers(reader).get('content-type', ''))

            is_first_frame = True
            for jpeg in iter_jpeg_frames(reader, boundary):
                if is_first_frame:
                    self._on_status('')
                    is_first_frame = False
                self._on_frame(jpeg)


def read_response_headers(reader):
    """Read an HTTP response's status line and headers; the headers by lower-case name. Raises ValueError unless 200."""
    status_line = reader.readline().decode('latin-1').strip()
    status_parts = status_line.split()
    if len(status_parts) < 2 or not status_parts[0].startswith('HTTP/') or status_parts[1] != '200':
        raise ValueError(f'Unexpected answer from the live view: {status_line!r}')
    headers = {}
    while True:
        line = reader.readline().decode('latin-1').strip()
        if not line:
            return headers
        name, _, value = line.partition(':')
        headers[name.strip().lower()] = value.strip()
