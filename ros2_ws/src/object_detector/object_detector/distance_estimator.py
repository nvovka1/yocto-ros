"""Distance to an object from how big its box looks.

Twice as far away, an object looks half as wide and half as tall, so its box area shrinks with the
square of the distance:

    distance = reference_distance * sqrt(reference_area / area)

The reference is one measurement you take yourself: put the object at `reference_distance_m` and read
the area the object_detector node logs. Areas are fractions of the frame (0..1), so the estimate does
not depend on the capture resolution.
"""

import math


class DistanceEstimator:

    def __init__(self, reference_distance_m, reference_area_fraction):
        if reference_distance_m <= 0:
            raise ValueError(f'reference_distance_m must be positive, got {reference_distance_m}')
        if not 0 < reference_area_fraction <= 1:
            raise ValueError(f'reference_area_fraction must be in (0, 1], got {reference_area_fraction}')
        self._reference_distance_m = reference_distance_m
        self._reference_area_fraction = reference_area_fraction

    def estimate(self, area_fraction):
        """Distance in metres for a box covering `area_fraction` of the frame."""
        if area_fraction <= 0:
            raise ValueError(f'area_fraction must be positive, got {area_fraction}')
        return self._reference_distance_m * math.sqrt(self._reference_area_fraction / area_fraction)
