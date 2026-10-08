"""A passive buzzer on a hardware PWM channel, driven through the Linux sysfs PWM interface.

The tone frequency stays fixed and the duty cycle sets the loudness. A buzzer is as loud as the
fundamental of the square wave driving it, whose strength is proportional to sin(pi * duty): 50 % duty is
the loudest, smaller duty cycles are quieter. duty = asin(volume) / pi makes the sound strength
proportional to `volume`.

Raspberry Pi 5: the PWM pins (GPIO 12, 13, 18, 19) belong to the RP1 chip's PWM0 controller, which appears
as one of /sys/class/pwm/pwmchip*. Its number changes between kernels, so the chip is found by device name.
The pin must first be routed to PWM in config.txt (meta-buzzer does this: dtoverlay=pwm-2chan,...).
"""

import math
import os
import time
from pathlib import Path

SYSFS_PWM_ROOT = Path('/sys/class/pwm')
# RP1 PWM0 on Raspberry Pi 5. Channel 0 = GPIO 12, 1 = GPIO 13, 2 = GPIO 18, 3 = GPIO 19.
RASPBERRY_PI_5_PWM_DEVICE = '1f00098000.pwm'
# After `export`, udev needs a moment to create the pwmN directory.
EXPORT_TIMEOUT_S = 1.0


class BuzzerError(RuntimeError):
    """The PWM channel is missing or could not be configured."""


def duty_cycle_for(volume):
    """Fraction of each period the pin is high (0..0.5) for a volume of 0..1."""
    volume = min(max(volume, 0.0), 1.0)
    return math.asin(volume) / math.pi


def find_pwm_chip(device_name=RASPBERRY_PI_5_PWM_DEVICE, sysfs_root=SYSFS_PWM_ROOT):
    chips = sorted(Path(sysfs_root).glob('pwmchip*'))
    for chip in chips:
        if device_name in os.path.realpath(chip / 'device'):
            return chip
    found = ', '.join(f'{chip.name} -> {os.path.realpath(chip / "device")}' for chip in chips) or 'none'
    raise BuzzerError(
        f'No PWM chip for {device_name} (found: {found}). Is the PWM overlay in /boot/config.txt? '
        'Otherwise set the pwm_chip parameter.')


class SysfsPwmBuzzer:

    def __init__(self, chip_path, channel, frequency_hz):
        self._chip_path = Path(chip_path)
        self._channel = channel
        self._channel_path = self._chip_path / f'pwm{channel}'
        self._export_channel()

        self._period_ns = round(1e9 / frequency_hz)
        # The duty cycle may never exceed the period, so start from 0 before changing the period.
        self._duty_cycle_ns = 0
        self._write('duty_cycle', 0)
        self._write('period', self._period_ns)
        self._write('enable', 1)

    def set_volume(self, volume):
        duty_cycle_ns = round(self._period_ns * duty_cycle_for(volume))
        if duty_cycle_ns != self._duty_cycle_ns:
            self._write('duty_cycle', duty_cycle_ns)
            self._duty_cycle_ns = duty_cycle_ns

    def close(self):
        self._write('duty_cycle', 0)
        self._write('enable', 0)
        (self._chip_path / 'unexport').write_text(str(self._channel))

    def _export_channel(self):
        if self._channel_path.exists():
            return
        try:
            (self._chip_path / 'export').write_text(str(self._channel))
        except OSError as error:
            raise BuzzerError(f'Could not export PWM channel {self._channel} of {self._chip_path}: {error}') from error

        deadline = time.monotonic() + EXPORT_TIMEOUT_S
        while not self._channel_path.exists():
            if time.monotonic() > deadline:
                raise BuzzerError(f'{self._channel_path} did not appear after export')
            time.sleep(0.01)

    def _write(self, attribute, value):
        (self._channel_path / attribute).write_text(str(value))


class LoggingBuzzer:
    """Used when `enabled` is false: no hardware, the volume is only remembered (and logged by the node)."""

    def __init__(self):
        self.volume = 0.0

    def set_volume(self, volume):
        self.volume = volume

    def close(self):
        pass
