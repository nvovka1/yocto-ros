"""Unit tests for the sysfs PWM buzzer, against a fake /sys/class/pwm in a temporary folder."""

import os

import pytest

from buzzer_controller.pwm_buzzer import BuzzerError, SysfsPwmBuzzer, duty_cycle_for, find_pwm_chip


def make_chip(sysfs_root, name, device_name):
    """A fake pwmchip whose `device` link points at `device_name`, like the kernel's."""
    device = sysfs_root / 'devices' / device_name
    device.mkdir(parents=True)
    chip = sysfs_root / name
    chip.mkdir()
    try:
        os.symlink(device, chip / 'device', target_is_directory=True)
    except OSError:
        pytest.skip('creating symlinks is not allowed here')
    return chip


def make_channel(chip, channel):
    """What the kernel creates after `echo <channel> > export`."""
    channel_path = chip / f'pwm{channel}'
    channel_path.mkdir()
    for attribute in ('period', 'duty_cycle', 'enable'):
        (channel_path / attribute).write_text('0')
    return channel_path


def test_volume_one_is_half_duty_and_zero_is_off():
    assert duty_cycle_for(1.0) == pytest.approx(0.5)
    assert duty_cycle_for(0.0) == 0.0


def test_duty_cycle_grows_with_volume_and_clamps():
    assert 0 < duty_cycle_for(0.1) < duty_cycle_for(0.5) < duty_cycle_for(0.9) < 0.5
    assert duty_cycle_for(2.0) == pytest.approx(0.5)
    assert duty_cycle_for(-1.0) == 0.0


def test_finds_the_chip_by_device_name(tmp_path):
    make_chip(tmp_path, 'pwmchip0', '107d517a80.pwm')
    expected = make_chip(tmp_path, 'pwmchip2', '1f00098000.pwm')

    assert find_pwm_chip('1f00098000.pwm', tmp_path) == expected


def test_missing_chip_names_what_was_found(tmp_path):
    make_chip(tmp_path, 'pwmchip0', '107d517a80.pwm')

    with pytest.raises(BuzzerError, match='pwmchip0'):
        find_pwm_chip('1f00098000.pwm', tmp_path)


def test_starts_silent_with_the_tone_period(tmp_path):
    channel_path = make_channel(tmp_path, 0)

    SysfsPwmBuzzer(tmp_path, 0, frequency_hz=2000)

    assert (channel_path / 'period').read_text() == '500000'
    assert (channel_path / 'duty_cycle').read_text() == '0'
    assert (channel_path / 'enable').read_text() == '1'


def test_full_volume_is_half_the_period(tmp_path):
    channel_path = make_channel(tmp_path, 0)
    buzzer = SysfsPwmBuzzer(tmp_path, 0, frequency_hz=2000)

    buzzer.set_volume(1.0)

    assert (channel_path / 'duty_cycle').read_text() == '250000'


def test_close_silences_disables_and_releases_the_channel(tmp_path):
    channel_path = make_channel(tmp_path, 1)
    buzzer = SysfsPwmBuzzer(tmp_path, 1, frequency_hz=2000)
    buzzer.set_volume(0.5)

    buzzer.close()

    assert (channel_path / 'duty_cycle').read_text() == '0'
    assert (channel_path / 'enable').read_text() == '0'
    assert (tmp_path / 'unexport').read_text() == '1'


def test_export_that_never_creates_the_channel_fails(tmp_path, monkeypatch):
    monkeypatch.setattr('buzzer_controller.pwm_buzzer.EXPORT_TIMEOUT_S', 0.05)

    with pytest.raises(BuzzerError, match='did not appear'):
        SysfsPwmBuzzer(tmp_path, 0, frequency_hz=2000)

    assert (tmp_path / 'export').read_text() == '0'
