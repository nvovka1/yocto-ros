"""Live view of what the detector sees, as an MJPEG stream any browser can show.

http://raspberrypi5.local:8080 shows the camera image with a box around every detection: the object the
distance is measured to in green, other detections in gray. Frames are only drawn and JPEG-encoded while
somebody is watching, so the stream costs nothing otherwise.

There is no login: anybody on the network who opens the page sees the camera. Set preview_port to 0 to turn it off.
"""

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2

# Colors are BGR, like the frames.
TARGET_COLOR = (0, 190, 0)
OTHER_COLOR = (140, 140, 140)
TEXT_COLOR = (255, 255, 255)
FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE = 0.5
JPEG_QUALITY = 80
BOUNDARY = 'frame'
# A viewer waiting for the next frame checks this often whether the server is shutting down.
WAIT_TIMEOUT_S = 1.0

PAGE = b"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>object_detector</title>
<style>
  body { margin: 0; padding: 16px; background: #111; color: #ddd; font-family: sans-serif; text-align: center; }
  img { max-width: 100%; height: auto; }
</style>
</head>
<body>
<p>object_detector: live camera view</p>
<img src="/stream" alt="camera stream">
</body>
</html>
"""


def draw_label(image, text, left, bottom, color):
    """Text on a filled box whose bottom-left corner is (left, bottom), moved down if it would leave the image."""
    (text_width, text_height), baseline = cv2.getTextSize(text, FONT, FONT_SCALE, 1)
    box_height = text_height + baseline + 4
    bottom = max(bottom, box_height)
    cv2.rectangle(image, (left, bottom - box_height), (left + text_width + 4, bottom), color, cv2.FILLED)
    cv2.putText(image, text, (left + 2, bottom - baseline - 2), FONT, FONT_SCALE, TEXT_COLOR, 1, cv2.LINE_AA)


def draw_detections(frame, detections, target, distance_m, status_text=''):
    """A copy of `frame` with every detection boxed and labelled; `target` gets its distance in the label."""
    image = frame.copy()
    for detection in detections:
        is_target = detection is target
        color = TARGET_COLOR if is_target else OTHER_COLOR
        left, top = round(detection.x), round(detection.y)
        right, bottom = round(detection.x + detection.width), round(detection.y + detection.height)
        cv2.rectangle(image, (left, top), (right, bottom), color, 2)

        label = f'{detection.class_name} {detection.confidence:.2f}'
        if is_target and distance_m is not None:
            label += f'  {distance_m:.2f} m'
        draw_label(image, label, left, top, color)

    if status_text:
        draw_label(image, status_text, 0, image.shape[0], (0, 0, 0))
    return image


class PreviewServer:

    def __init__(self, port, host='0.0.0.0'):
        self._condition = threading.Condition()
        self._jpeg = None
        self._sequence = 0
        self._viewer_count = 0
        self._is_running = True

        preview = self

        class Handler(BaseHTTPRequestHandler):

            def do_GET(self):
                if self.path == '/':
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.send_header('Content-Length', str(len(PAGE)))
                    self.end_headers()
                    self.wfile.write(PAGE)
                elif self.path == '/stream':
                    preview._stream_to(self)
                else:
                    self.send_error(404)

            def log_message(self, format, *args):
                pass  # One line per request would flood the journal.

        self._http_server = ThreadingHTTPServer((host, port), Handler)
        self._http_server.daemon_threads = True
        self._thread = threading.Thread(target=self._http_server.serve_forever, daemon=True)
        self._thread.start()

    @property
    def port(self):
        return self._http_server.server_address[1]

    @property
    def has_viewers(self):
        with self._condition:
            return self._viewer_count > 0

    def publish(self, frame):
        """Send `frame` (BGR) to everybody watching."""
        is_encoded, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
        if not is_encoded:
            return
        with self._condition:
            self._jpeg = jpeg.tobytes()
            self._sequence += 1
            self._condition.notify_all()

    def close(self):
        with self._condition:
            self._is_running = False
            self._condition.notify_all()
        self._http_server.shutdown()
        self._http_server.server_close()

    def _stream_to(self, handler):
        handler.send_response(200)
        handler.send_header('Content-Type', f'multipart/x-mixed-replace; boundary={BOUNDARY}')
        handler.send_header('Cache-Control', 'no-cache')
        handler.end_headers()

        with self._condition:
            self._viewer_count += 1
            # Only frames published from now on: an old frame from an earlier viewer would be stale.
            sent_sequence = self._sequence
        try:
            while True:
                with self._condition:
                    self._condition.wait_for(
                        lambda: not self._is_running or self._sequence != sent_sequence, timeout=WAIT_TIMEOUT_S)
                    if not self._is_running:
                        return
                    if self._sequence == sent_sequence:
                        continue
                    jpeg, sent_sequence = self._jpeg, self._sequence
                header = f'--{BOUNDARY}\r\nContent-Type: image/jpeg\r\nContent-Length: {len(jpeg)}\r\n\r\n'
                handler.wfile.write(header.encode() + jpeg + b'\r\n')
                handler.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass  # The viewer closed the page.
        finally:
            with self._condition:
                self._viewer_count -= 1
