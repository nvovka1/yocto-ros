#!/usr/bin/env python3
"""Convert the trained Ultralytics YOLO model (.pt) to the ONNX file the object_detector node runs.

PyTorch does not run on the Yocto image; OpenCV's DNN module runs the ONNX export instead. Run this on
the PC whenever the model is retrained, then rebuild the image.

    pip install ultralytics onnx onnxslim
    python tools/export_model.py C:/MyProjects/my_model/my_model.pt

It prints the model's class names: copy them into class_names in
ros2_ws/src/object_detector/config/object_detector.yaml if they changed.
"""

import argparse
import shutil
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = REPOSITORY_ROOT / 'ros2_ws' / 'src' / 'object_detector' / 'models' / 'my_model.onnx'


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('model', type=Path, help='trained model, e.g. my_model.pt')
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT, help=f'default: {DEFAULT_OUTPUT}')
    parser.add_argument('--image-size', type=int, default=640, help='imgsz the model was trained with (default 640)')
    return parser.parse_args()


def main():
    arguments = parse_arguments()
    from ultralytics import YOLO

    model = YOLO(str(arguments.model))
    # Opset 12, fixed input size and a simplified graph: the combination OpenCV 4.9's DNN module loads.
    exported = Path(model.export(format='onnx', imgsz=arguments.image_size, opset=12, simplify=True, dynamic=False))

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(exported, arguments.output)
    print(f'ONNX model: {arguments.output}')
    print(f'class_names: [{", ".join(model.names[class_id] for class_id in sorted(model.names))}]')


if __name__ == '__main__':
    main()
