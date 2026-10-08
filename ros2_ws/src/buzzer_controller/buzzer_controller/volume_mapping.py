"""Distance -> buzzer volume: loud when the object is close, quiet when it is far away."""

from dataclasses import dataclass


@dataclass(frozen=True)
class VolumeMapping:
    # Closer than this: full volume.
    near_distance_m: float = 0.3
    # Farther than this: min_volume. In between the volume falls in a straight line.
    far_distance_m: float = 2.0
    # Volume for far objects, 0..1. 0 makes far objects silent.
    min_volume: float = 0.05

    def __post_init__(self):
        if not 0 <= self.near_distance_m < self.far_distance_m:
            raise ValueError(
                f'Need 0 <= near_distance_m < far_distance_m, got {self.near_distance_m} and {self.far_distance_m}')
        if not 0 <= self.min_volume <= 1:
            raise ValueError(f'min_volume must be in [0, 1], got {self.min_volume}')

    def volume_for(self, distance_m):
        """Volume 0..1 for an object `distance_m` metres away."""
        if distance_m <= self.near_distance_m:
            return 1.0
        if distance_m >= self.far_distance_m:
            return self.min_volume
        progress = (distance_m - self.near_distance_m) / (self.far_distance_m - self.near_distance_m)
        return 1.0 - progress * (1.0 - self.min_volume)
