from glob import glob

from setuptools import find_packages, setup

package_name = 'counter_demo'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        # Marks the package as installed so `ros2 run` / `ros2 pkg list` can find it.
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Volodymyr Blahodyr',
    maintainer_email='nvovka1@users.noreply.github.com',
    description='Counter publisher and subscriber with a service to start and stop counting.',
    license='MIT',
    # Each entry becomes an executable in lib/counter_demo (see setup.cfg), runnable with `ros2 run`.
    entry_points={
        'console_scripts': [
            'counter_publisher = counter_demo.counter_publisher:main',
            'counter_subscriber = counter_demo.counter_subscriber:main',
            'counter_controller = counter_demo.counter_controller:main',
        ],
    },
)
