"""Frame sources: the Raspberry Pi camera, or image files for testing without one.

Everything downstream sees a plain BGR NumPy array. On Raspberry Pi 5 the camera is driven by libcamera;
OpenCV reads it through libcamera's GStreamer element (libcamerasrc), so no Python camera library is needed.
"""

import glob
import os

import cv2

# {width} and {height} are filled in from the node parameters.
DEFAULT_CAMERA_PIPELINE = (
    'libcamerasrc ! video/x-raw,width={width},height={height} ! videoconvert ! video/x-raw,format=BGR ! '
    'appsink drop=true max-buffers=1 sync=false'
)


class CameraError(RuntimeError):
    """A frame source could not be opened, or stopped producing frames."""


class GStreamerCameraSource:

    def __init__(self, pipeline):
        self._capture = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        if not self._capture.isOpened():
            raise CameraError(
                f'Could not open the camera pipeline: {pipeline}\n'
                'Check the ribbon cable and that libcamera sees the camera: cam --list')

    def read(self):
        is_read, frame = self._capture.read()
        if not is_read:
            raise CameraError('The camera stopped producing frames')
        return frame

    def close(self):
        self._capture.release()


class FileSource:
    """Replays a still image, or every image in a directory, looping forever."""

    def __init__(self, path, width, height):
        if os.path.isdir(path):
            self._paths = sorted(
                candidate for candidate in glob.glob(os.path.join(path, '*'))
                if candidate.lower().endswith(('.jpg', '.jpeg', '.png')))
        else:
            self._paths = [path]
        if not self._paths:
            raise CameraError(f'No images found at {path}')
        self._size = (width, height)
        self._index = 0

    def read(self):
        path = self._paths[self._index % len(self._paths)]
        self._index += 1
        image = cv2.imread(path)
        if image is None:
            raise CameraError(f'Could not read image {path}')
        return cv2.resize(image, self._size)

    def close(self):
        pass


def open_source(source, width, height, camera_pipeline=DEFAULT_CAMERA_PIPELINE):
    """`source` is "camera", or "file:<path to an image or a directory of images>"."""
    if source == 'camera':
        return GStreamerCameraSource(camera_pipeline.format(width=width, height=height))
    if source.startswith('file:'):
        return FileSource(source[len('file:'):], width, height)
    raise CameraError(f'Unknown source "{source}". Use "camera" or "file:<path>".')
