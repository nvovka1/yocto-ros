"""Reads JPEG frames from an MJPEG stream (multipart/x-mixed-replace), the format of the detector's live view.

Each part looks like:
    --frame\r\n
    Content-Type: image/jpeg\r\n
    Content-Length: 12345\r\n
    \r\n
    <12345 bytes of JPEG>\r\n
"""

MJPEG_CONTENT_TYPE = 'multipart/x-mixed-replace'


def boundary_from_content_type(content_type):
    """The boundary of a `multipart/x-mixed-replace; boundary=...` content type."""
    media_type, _, parameters = content_type.partition(';')
    if media_type.strip().lower() != MJPEG_CONTENT_TYPE:
        raise ValueError(f'Not an MJPEG stream: {content_type!r}')
    for parameter in parameters.split(';'):
        name, _, value = parameter.strip().partition('=')
        if name.lower() == 'boundary' and value:
            return value.strip('"')
    raise ValueError(f'No boundary in {content_type!r}')


def iter_jpeg_frames(stream, boundary):
    """Yield the bytes of every JPEG in `stream` until it ends. A frame cut short by the end of the stream is dropped."""
    boundary_line = f'--{boundary}'.encode()
    while True:
        line = stream.readline()
        if not line:
            return
        line = line.strip()
        if not line:
            continue  # The \r\n after the previous frame.
        if line != boundary_line:
            raise ValueError(f'Expected the boundary {boundary_line!r}, got {line[:80]!r}')

        content_length = _read_content_length(stream)
        if content_length is None:
            return
        jpeg = stream.read(content_length)
        if len(jpeg) < content_length:
            return
        yield jpeg


def _read_content_length(stream):
    """Read a part's headers up to the empty line; its Content-Length, or None if the stream ended."""
    content_length = None
    while True:
        line = stream.readline()
        if not line:
            return None
        line = line.strip()
        if not line:
            break
        name, _, value = line.decode('latin-1').partition(':')
        if name.strip().lower() == 'content-length':
            content_length = int(value.strip())
    if content_length is None:
        raise ValueError('MJPEG part without Content-Length')
    return content_length
