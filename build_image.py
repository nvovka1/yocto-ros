#!/usr/bin/env python3
"""Build a Raspberry Pi image with BitBake and optionally copy it out for flashing.

Examples (run inside WSL / Linux, from anywhere):
    python3 build_image.py                       # list the images you can build
    python3 build_image.py ros-counter-image     # base OS + ROS 2 + counter demo
    python3 build_image.py rpi-base-image        # base OS only (the previous Raspberry Pi image)
    python3 build_image.py ros-counter-image --copy-to /mnt/c/Users/me/Downloads

The build directory is created on first use from meta-rpi-base/conf/templates/default,
exactly like `source ./setup-environment.sh`.
"""

import argparse
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent

# Image recipe -> what it contains. Add a line here when you add a new image recipe to a layer.
IMAGES = {
    'rpi-base-image': 'Base OS: SSH, Wi-Fi, Python, tools (meta-rpi-base)',
    'ros-counter-image': 'Base OS + ROS 2 Jazzy + counter demo (meta-ros-demo)',
}


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('image', nargs='?', choices=sorted(IMAGES), help='image recipe to build')
    parser.add_argument('--build-dir', default='build', help='build directory under the repository (default: build)')
    parser.add_argument('--copy-to', type=Path, help='copy the finished .wic.xz and .wic.bmap into this folder')
    return parser.parse_args()


def print_images():
    print('Images you can build:')
    for image, description in IMAGES.items():
        print(f'  {image:<20} {description}')
    print('\nUsage: python3 build_image.py <image> [--copy-to <folder>]')


def check_submodules():
    if not (REPOSITORY_ROOT / 'layers' / 'poky' / 'oe-init-build-env').is_file():
        sys.exit('layers/poky is missing. Run: git submodule update --init')


def run_bitbake(image, build_dir):
    # BitBake needs the environment from oe-init-build-env, which only exists inside a sourced bash shell.
    command = (
        f'source {shlex.quote(str(REPOSITORY_ROOT / "setup-environment.sh"))} {shlex.quote(build_dir)} > /dev/null'
        f' && bitbake {shlex.quote(image)}'
    )
    print(f'==> bitbake {image}  (build directory: {build_dir})', flush=True)
    return subprocess.run(['bash', '-c', command], cwd=REPOSITORY_ROOT).returncode


def find_image_files(image, build_dir):
    # BitBake keeps a stable symlink (<image>[-jazzy]-<machine>.rootfs.wic.xz) pointing at the newest build.
    deploy_root = REPOSITORY_ROOT / build_dir / 'tmp' / 'deploy' / 'images'
    image_files = []
    for extension in ('wic.xz', 'wic.bmap'):
        image_files += [path for path in deploy_root.glob(f'*/{image}*.rootfs.{extension}') if path.is_symlink()]
    return sorted(image_files)


def copy_image_files(image_files, destination):
    destination.mkdir(parents=True, exist_ok=True)
    for image_file in image_files:
        # copy2 follows the symlink, like `cp -L`, so the real image is copied.
        shutil.copy2(image_file, destination / image_file.name)
        print(f'    copied to {destination / image_file.name}')


def main():
    arguments = parse_arguments()
    if arguments.image is None:
        print_images()
        return 0

    check_submodules()
    exit_code = run_bitbake(arguments.image, arguments.build_dir)
    if exit_code != 0:
        print(f'bitbake failed with exit code {exit_code}', file=sys.stderr)
        return exit_code

    image_files = find_image_files(arguments.image, arguments.build_dir)
    if not image_files:
        print('Build finished, but no .wic.xz was found under tmp/deploy/images.', file=sys.stderr)
        return 1

    print('==> Image ready:')
    for image_file in image_files:
        print(f'    {image_file.relative_to(REPOSITORY_ROOT)}')

    if arguments.copy_to:
        copy_image_files(image_files, arguments.copy_to)

    print('Flash the .wic.xz with Raspberry Pi Imager (Use custom) or: bmaptool copy <image>.wic.xz /dev/sdX')
    return 0


if __name__ == '__main__':
    sys.exit(main())
