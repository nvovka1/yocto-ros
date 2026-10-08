"""Unit tests for VolumeMapping. Run with: colcon test --packages-select buzzer_controller"""

import pytest

from buzzer_controller.volume_mapping import VolumeMapping


def test_close_objects_are_full_volume():
    mapping = VolumeMapping(near_distance_m=0.3, far_distance_m=2.0, min_volume=0.05)

    assert mapping.volume_for(0.1) == 1.0
    assert mapping.volume_for(0.3) == 1.0


def test_far_objects_are_min_volume():
    mapping = VolumeMapping(near_distance_m=0.3, far_distance_m=2.0, min_volume=0.05)

    assert mapping.volume_for(2.0) == pytest.approx(0.05)
    assert mapping.volume_for(10.0) == pytest.approx(0.05)


def test_volume_falls_in_a_straight_line_between_near_and_far():
    mapping = VolumeMapping(near_distance_m=1.0, far_distance_m=3.0, min_volume=0.0)

    assert mapping.volume_for(2.0) == pytest.approx(0.5)
    assert mapping.volume_for(1.5) == pytest.approx(0.75)


def test_closer_is_never_quieter():
    mapping = VolumeMapping()
    distances = [step / 10 for step in range(40)]

    volumes = [mapping.volume_for(distance) for distance in distances]

    assert volumes == sorted(volumes, reverse=True)


@pytest.mark.parametrize('near, far, min_volume', [(2.0, 1.0, 0.1), (1.0, 1.0, 0.1), (-1.0, 1.0, 0.1), (0.3, 2.0, 1.5)])
def test_rejects_invalid_settings(near, far, min_volume):
    with pytest.raises(ValueError):
        VolumeMapping(near, far, min_volume)
