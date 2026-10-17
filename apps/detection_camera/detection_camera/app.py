"""Camera: the detector's live view (camera frame with the detection boxes) in a GNOME window.

Run on the board with `detection-camera`, or on a PC against the board:
    DETECTION_CAMERA_URL=http://192.168.0.101:8080/stream python -m detection_camera.app
"""

import os
import sys
import threading

import gi

gi.require_version('Gdk', '4.0')
gi.require_version('Gtk', '4.0')
from gi.repository import Gdk, GLib, Gtk  # noqa: E402  (must come after require_version)

from detection_camera.frame_receiver import WAITING_TEXT, FrameReceiver  # noqa: E402

APPLICATION_ID = 'io.github.nvovka1.DetectionCamera'
DEFAULT_STREAM_URL = 'http://127.0.0.1:8080/stream'
STREAM_URL_VARIABLE = 'DETECTION_CAMERA_URL'


class CameraWindow(Gtk.ApplicationWindow):

    def __init__(self, application, stream_url):
        super().__init__(application=application, title='Camera', default_width=320, default_height=480)
        self._picture = Gtk.Picture(content_fit=Gtk.ContentFit.CONTAIN, can_shrink=True, hexpand=True, vexpand=True)
        self._status = Gtk.Label(label=WAITING_TEXT, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, wrap=True)
        self._status.add_css_class('title-2')
        overlay = Gtk.Overlay(child=self._picture)
        overlay.add_overlay(self._status)
        self.set_child(overlay)
        self.maximize()

        # Only the newest frame is kept: if drawing falls behind the stream, older frames are skipped, not queued.
        self._pending_lock = threading.Lock()
        self._pending_jpeg = None

        self._receiver = FrameReceiver(stream_url, self._on_frame, self._on_status)
        self.connect('close-request', self._on_close_request)
        self._receiver.start()

    # Called on the receiver's thread: hand over to the GTK main loop.
    def _on_frame(self, jpeg):
        with self._pending_lock:
            is_already_scheduled = self._pending_jpeg is not None
            self._pending_jpeg = jpeg
        if not is_already_scheduled:
            GLib.idle_add(self._show_pending_frame)

    def _on_status(self, text):
        GLib.idle_add(self._show_status, text)

    # On the GTK main loop.
    def _show_pending_frame(self):
        with self._pending_lock:
            jpeg, self._pending_jpeg = self._pending_jpeg, None
        try:
            texture = Gdk.Texture.new_from_bytes(GLib.Bytes.new(jpeg))
        except GLib.Error:
            return GLib.SOURCE_REMOVE  # A broken frame: keep showing the previous one.
        self._picture.set_paintable(texture)
        return GLib.SOURCE_REMOVE

    def _show_status(self, text):
        if text:
            self._picture.set_paintable(None)  # Don't leave an old frame on screen while the camera is gone.
        self._status.set_label(text)
        self._status.set_visible(bool(text))
        return GLib.SOURCE_REMOVE

    def _on_close_request(self, window):
        # Closing the connection makes the detector stop drawing preview frames.
        self._receiver.stop()
        return False


class CameraApplication(Gtk.Application):

    def __init__(self, stream_url):
        super().__init__(application_id=APPLICATION_ID)
        self._stream_url = stream_url

    def do_activate(self):
        window = self.get_active_window() or CameraWindow(self, self._stream_url)
        window.present()


def main(argv=None):
    stream_url = os.environ.get(STREAM_URL_VARIABLE, DEFAULT_STREAM_URL)
    return CameraApplication(stream_url).run(sys.argv if argv is None else argv)


if __name__ == '__main__':
    sys.exit(main())
