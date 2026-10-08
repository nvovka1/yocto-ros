"""YOLO11 object detection with OpenCV DNN.

The network is the Ultralytics YOLO11 model exported to ONNX (tools/export_model.py). PyTorch is not
on the image, so OpenCV's DNN module runs the network and this file does the pre- and post-processing
Ultralytics would otherwise do: letterbox the frame, then turn the raw output into boxes in frame pixels.
"""

from dataclasses import dataclass

import cv2
import numpy as np

# Ultralytics pads letterboxed images with this gray; the model was trained on it.
LETTERBOX_PAD_COLOR = (114, 114, 114)


@dataclass(frozen=True)
class Detection:
    class_id: int
    class_name: str
    confidence: float
    # Top-left corner and size, in pixels of the original frame.
    x: float
    y: float
    width: float
    height: float

    @property
    def area(self):
        return self.width * self.height


@dataclass(frozen=True)
class Letterbox:
    """How a frame was placed inside the square model input: scaled by `scale`, then shifted by the padding."""
    scale: float
    pad_x: int
    pad_y: int


def letterbox(frame, size):
    """Resize `frame` to fit a size x size square without distorting it, padding the rest with gray."""
    height, width = frame.shape[:2]
    scale = min(size / width, size / height)
    resized_width, resized_height = round(width * scale), round(height * scale)
    resized = cv2.resize(frame, (resized_width, resized_height), interpolation=cv2.INTER_LINEAR)

    # An odd amount of padding puts the extra pixel on the right / bottom, as Ultralytics does.
    pad_x, pad_y = (size - resized_width) / 2, (size - resized_height) / 2
    top, bottom = round(pad_y - 0.1), round(pad_y + 0.1)
    left, right = round(pad_x - 0.1), round(pad_x + 0.1)
    padded = cv2.copyMakeBorder(resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=LETTERBOX_PAD_COLOR)
    return padded, Letterbox(scale, left, top)


def decode_output(output, placement, frame_width, frame_height, class_names, confidence_threshold, nms_threshold):
    """Turn the raw YOLO11 output into detections in frame pixels.

    `output` has shape (1, 4 + classes, candidates). For every candidate the first four rows are the box
    centre and size (cx, cy, w, h) in model-input pixels, the rest are one score per class.
    """
    candidates = np.squeeze(output, axis=0).T
    class_scores = candidates[:, 4:]
    class_ids = np.argmax(class_scores, axis=1)
    confidences = class_scores[np.arange(len(class_scores)), class_ids]

    is_confident = confidences >= confidence_threshold
    candidates, class_ids, confidences = candidates[is_confident], class_ids[is_confident], confidences[is_confident]
    if len(candidates) == 0:
        return []

    # Centre/size in model-input pixels -> top-left/size in frame pixels, clipped to the frame.
    center_x, center_y, box_width, box_height = candidates[:, 0], candidates[:, 1], candidates[:, 2], candidates[:, 3]
    left = np.clip((center_x - box_width / 2 - placement.pad_x) / placement.scale, 0, frame_width)
    top = np.clip((center_y - box_height / 2 - placement.pad_y) / placement.scale, 0, frame_height)
    right = np.clip((center_x + box_width / 2 - placement.pad_x) / placement.scale, 0, frame_width)
    bottom = np.clip((center_y + box_height / 2 - placement.pad_y) / placement.scale, 0, frame_height)
    boxes = np.stack([left, top, right - left, bottom - top], axis=1)

    # Overlapping boxes of the same class are one object: keep the most confident.
    kept = cv2.dnn.NMSBoxesBatched(
        boxes.tolist(), confidences.tolist(), class_ids.tolist(), confidence_threshold, nms_threshold)

    detections = []
    for index in np.array(kept).flatten():
        class_id = int(class_ids[index])
        name = class_names[class_id] if class_id < len(class_names) else str(class_id)
        x, y, width, height = (float(value) for value in boxes[index])
        detections.append(Detection(class_id, name, float(confidences[index]), x, y, width, height))
    return sorted(detections, key=lambda detection: detection.confidence, reverse=True)


class YoloDetector:

    def __init__(self, model_path, class_names, input_size=640, confidence_threshold=0.5, nms_threshold=0.45):
        self._network = cv2.dnn.readNetFromONNX(model_path)
        self._class_names = list(class_names)
        self._input_size = input_size
        self._confidence_threshold = confidence_threshold
        self._nms_threshold = nms_threshold

    def detect(self, frame):
        """Detections in a BGR frame, most confident first."""
        image, placement = letterbox(frame, self._input_size)
        # The model expects RGB scaled to 0..1; camera frames are BGR 0..255.
        blob = cv2.dnn.blobFromImage(image, scalefactor=1 / 255.0, swapRB=True)
        self._network.setInput(blob)
        output = self._network.forward()

        frame_height, frame_width = frame.shape[:2]
        return decode_output(output, placement, frame_width, frame_height, self._class_names,
                             self._confidence_threshold, self._nms_threshold)
