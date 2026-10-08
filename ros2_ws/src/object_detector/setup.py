from glob import glob

from setuptools import find_packages, setup

package_name = 'object_detector'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        # Marks the package as installed so `ros2 run` / `ros2 pkg list` can find it.
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
        ('share/' + package_name + '/models', glob('models/*.onnx')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Volodymyr Blahodyr',
    maintainer_email='nvovka1@users.noreply.github.com',
    description='Detects a trained YOLO object in the camera image and publishes its estimated distance.',
    license='MIT',
    entry_points={
        'console_scripts': [
            'object_detector = object_detector.object_detector_node:main',
        ],
    },
)
