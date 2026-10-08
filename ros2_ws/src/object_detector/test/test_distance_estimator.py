"""Unit tests for DistanceEstimator. Run with: colcon test --packages-select object_detector"""

import pytest

from object_detector.distance_estimator import DistanceEstimator


def test_reference_area_gives_reference_distance():
    estimator = DistanceEstimator(reference_distance_m=1.0, reference_area_fraction=0.05)

    assert estimator.estimate(0.05) == pytest.approx(1.0)


def test_quarter_of_the_area_is_twice_as_far():
    estimator = DistanceEstimator(reference_distance_m=1.0, reference_area_fraction=0.08)

    assert estimator.estimate(0.02) == pytest.approx(2.0)


def test_four_times_the_area_is_half_as_far():
    estimator = DistanceEstimator(reference_distance_m=1.5, reference_area_fraction=0.04)

    assert estimator.estimate(0.16) == pytest.approx(0.75)


@pytest.mark.parametrize('distance, area', [(0, 0.05), (1.0, 0), (1.0, 1.5)])
def test_rejects_invalid_reference(distance, area):
    with pytest.raises(ValueError):
        DistanceEstimator(distance, area)


def test_rejects_an_empty_box():
    with pytest.raises(ValueError):
        DistanceEstimator(1.0, 0.05).estimate(0)
