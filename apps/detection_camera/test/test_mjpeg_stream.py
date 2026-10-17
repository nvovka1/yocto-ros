"""Unit tests for the MJPEG stream parser. Run from apps/detection_camera with: python -m pytest test"""

import io

import pytest

from detection_camera.mjpeg_stream import boundary_from_content_type, iter_jpeg_frames


def part(jpeg, boundary='frame'):
    """One part exactly as the detector's preview server writes it."""
    header = f'--{boundary}\r\nContent-Type: image/jpeg\r\nContent-Length: {len(jpeg)}\r\n\r\n'
    return header.encode() + jpeg + b'\r\n'


class OneByteReader(io.RawIOBase):
    """A raw stream that hands out one byte per read, like a slow network connection."""

    def __init__(self, data):
        self._data = data
        self._position = 0

    def readable(self):
        return True

    def readinto(self, buffer):
        if self._position >= len(self._data) or len(buffer) == 0:
            return 0
        buffer[0] = self._data[self._position]
        self._position += 1
        return 1


def test_boundary_is_read_from_the_content_type():
    assert boundary_from_content_type('multipart/x-mixed-replace; boundary=frame') == 'frame'


@pytest.mark.parametrize('content_type', ['text/html', 'multipart/x-mixed-replace'])
def test_other_content_types_are_rejected(content_type):
    with pytest.raises(ValueError):
        boundary_from_content_type(content_type)


def test_yields_every_frame_in_order():
    stream = io.BytesIO(part(b'one') + part(b'two') + part(b'three'))

    assert list(iter_jpeg_frames(stream, 'frame')) == [b'one', b'two', b'three']


def test_reads_frames_delivered_one_byte_at_a_time():
    data = part(b'one') + part(b'two') + part(b'three')
    stream = io.BufferedReader(OneByteReader(data), buffer_size=1)

    assert list(iter_jpeg_frames(stream, 'frame')) == [b'one', b'two', b'three']


def test_frame_containing_the_boundary_text_is_not_split():
    jpeg = b'xx--frame\r\nyy'

    assert list(iter_jpeg_frames(io.BytesIO(part(jpeg)), 'frame')) == [jpeg]


def test_stops_cleanly_on_a_truncated_last_frame():
    truncated = part(b'0123456789')[:-8]
    stream = io.BytesIO(part(b'one') + part(b'two') + truncated)

    assert list(iter_jpeg_frames(stream, 'frame')) == [b'one', b'two']


def test_missing_content_length_is_an_error():
    stream = io.BytesIO(b'--frame\r\nContent-Type: image/jpeg\r\n\r\njpeg\r\n')

    with pytest.raises(ValueError):
        list(iter_jpeg_frames(stream, 'frame'))
