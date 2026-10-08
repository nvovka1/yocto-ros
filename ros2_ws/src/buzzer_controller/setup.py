from glob import glob

from setuptools import find_packages, setup

package_name = 'buzzer_controller'

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
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Volodymyr Blahodyr',
    maintainer_email='nvovka1@users.noreply.github.com',
    description='Sounds a PWM buzzer while an object is detected, louder the closer it is.',
    license='MIT',
    entry_points={
        'console_scripts': [
            'buzzer_controller = buzzer_controller.buzzer_controller_node:main',
        ],
    },
)
