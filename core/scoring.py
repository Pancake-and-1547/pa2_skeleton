"""core.scoring

Score computation for simulation states.

This module computes three components and aggregates them:
- comfort: deviation from setpoint (weighted by room types)
- uniformity: temperature variance within room types
- energy: penalty based on per-minute energy usage
"""

import numpy as np

from .state.floor_map import FloorMap
from .state.state import State


def _room_types_to_ascii(room_types: np.ndarray) -> np.ndarray:
    """
    Convert room types array to ASCII integer representation.

    Example:
        arr = np.array([['A', 'B'], ['C', 'A']])
        _room_types_to_ascii(arr)
        # returns array([[65, 66], [67, 65]], dtype=uint8)

    Args:
        room_types: NumPy array of room type characters ('A'..'Z' or 'x').

    Returns:
        NumPy array of corresponding uint8 ASCII codes.
    """
    return room_types.astype("S1").view(np.uint8)


def _build_weight_lookup(room_weights: dict[str, float]) -> np.ndarray:
    """
    Task 5.1. (Broadcasting Task)

    Broadcasting requirement: use broadcasting-style NumPy operations to receive full marks.

    Build a 256-element lookup array mapping ASCII code -> room weight.

    The lookup array is indexed by the ASCII integer value of a room type
    character, so any room type character can be converted to its weight
    with a single array index operation.

    Room type 'x' (walls, doors, unlabeled cells) is never present in
    `room_weights` and therefore defaults to 0.0.

    Example:
        room_weights = {'A': 2.0, 'B': 1.5}
        lookup = _build_weight_lookup(room_weights)
        lookup[65]   # -> 2.0, because ord('A') == 65
        lookup[66]   # -> 1.5, because ord('B') == 66
        lookup[120]  # -> 0.0, because ord('x') == 120

    Args:
        room_weights: Dict mapping room type letter ('A'..'Z') to float.

    Returns:
        Lookup array of size 256, dtype float.
    """
    pass


def get_room_type_weight_mask(
    floor_map: FloorMap,
    room_weights: dict[str, float],
) -> np.ndarray:
    """
    Task 5.2. (Broadcasting Task)

    Broadcasting requirement: use broadcasting-style NumPy operations to receive full marks.

    Produce an H x W weight array where every cell holds the scoring weight
    of the room type it belongs to.

    Conceptual algorithm: for every cell (r, c)
        room_char = floor_map.room_types[r, c]
        weight_mask[r, c] = room_weights.get(room_char, 0.0)

    The actual implementation avoids the Python-level loop by converting
    room type characters to their ASCII codes and using the lookup array
    from `_build_weight_lookup` as a direct index into the result.

    Example:
        floor_map.room_types:
            [['x', 'x', 'x'],
             ['x', 'A', 'x'],
             ['x', 'B', 'x']]
        room_weights = {'A': 2.0, 'B': 1.0, 'C': 0.5}

        -> weight_mask:
            [[0.0, 0.0, 0.0],
             [0.0, 2.0, 0.0],
             [0.0, 1.0, 0.0]]

    Args:
        floor_map: FloorMap-like object with a room_types array.
        room_weights: Dict mapping room type letter to float.

    Returns:
        NumPy array of weights with shape H x W.
        Cells with room type 'x' get a weight of 0.0.
    """
    pass


def compute_comfort_score(
    floor_map: FloorMap,
    room_weights: dict[str, float],
    setpoint_temp: float,
    temperature_field: np.ndarray,
) -> float:
    """
    Task 5.3. (Broadcasting Task)

    Broadcasting requirement: use broadcasting-style NumPy operations to receive full marks.

    Compute a weighted comfort score measuring how close every room cell is
    to the target setpoint temperature.

    Conceptual algorithm:
        weight[r, c] = room_weights.get(floor_map.room_types[r, c], 0.0)
        weighted_sq_error =
            sum over all cells of [weight[r,c] * (T[r,c] - setpoint)^2]
        total_weight =
            sum over all cells of [weight[r,c]]
        mean_sq_error = weighted_sq_error / total_weight
        comfort_score = 100.0 - 10.0 * mean_sq_error

    Cells whose room type is 'x' (walls, doors) have weight 0, so they
    contribute nothing to either sum.

    Example:
        room_types = [['A', 'A', 'x'],
                      ['x', 'x', 'x'],
                      ['B', 'B', 'x']]
        room_weights = {'A': 1.0, 'B': 2.0, 'C': 3.0}
        setpoint = 22.0
        temperature_field = [[20.0, 24.0, 30.0],
                             [30.0, 30.0, 30.0],
                             [21.0, 25.0, 30.0]]

        weight_mask = [[1.0, 1.0, 0.0],
                       [0.0, 0.0, 0.0],
                       [2.0, 2.0, 0.0]]

        weighted_sq_error = (1.0*(20-22)^2 + 1.0*(24-22)^2 + 2.0*(21-22)^2 + 2.0*(25-22)^2) = 28.0
        total_weight = 1.0 + 1.0 + 2.0 + 2.0 = 6.0
        mean_sq_error = 28.0 / 6.0 = 4.666
        comfort_score = 100.0 - 10.0 * 4.666 = 53.333

    Returns:
        Weighted comfort score (float). Can be negative if deviations are large.
    """
    pass


class Scoring:
    """Calculate comfort, uniformity, and energy scores."""

    def __init__(
        self,
        comfort_weight: float = 0.75,
        uniformity_weight: float = 0.19,
        energy_weight: float = 0.06,
    ) -> None:
        """
        Provided function.
        Initialize scoring parameters.

        Args:
            comfort_weight: Weight for comfort score.
            uniformity_weight: Weight for uniformity score.
            energy_weight: Weight for energy penalty.

        Notes:
            The weights should sum to 1.0.
        """
        self.comfort_weight = comfort_weight
        self.uniformity_weight = uniformity_weight
        self.energy_weight = energy_weight

        assert abs(comfort_weight + uniformity_weight + energy_weight - 1.0) < 1e-6, "Weights must sum to 1.0"

    def _room_types_to_ascii(self, room_types: np.ndarray) -> np.ndarray:
        """
        Provided function.
        Convert room types array to ASCII integer representation.
        """
        return _room_types_to_ascii(room_types)

    def _build_weight_lookup(self, room_weights: dict[str, float]) -> np.ndarray:
        """
        Wrapper for the module-level `_build_weight_lookup(...)` task function.
        """
        return _build_weight_lookup(room_weights)

    def get_room_type_weight_mask(
        self,
        floor_map: FloorMap,
        room_weights: dict[str, float],
    ) -> np.ndarray:
        """
        Wrapper for the module-level `get_room_type_weight_mask(...)` task function.
        """
        return get_room_type_weight_mask(floor_map, room_weights)

    def compute_comfort_score(
        self,
        floor_map: FloorMap,
        room_weights: dict[str, float],
        setpoint_temp: float,
        temperature_field: np.ndarray,
    ) -> float:
        """
        Wrapper for the module-level `compute_comfort_score(...)` task function.
        """
        return compute_comfort_score(
            floor_map,
            room_weights,
            setpoint_temp,
            temperature_field,
        )

    def compute_uniformity_score(
        self,
        floor_map: FloorMap,
        room_weights: dict[str, float],
        temperature_field: np.ndarray,
    ) -> float:
        """
        Provided function.
        Compute a weighted uniformity score measuring how evenly temperature is
        distributed within each room type.

        Conceptual algorithm:
            For each room type R with weight w_R:
                cells_R = all cells where room_types == R
                mean_R = average temperature across cells_R
                var_R = average of (T - mean_R)^2 across cells_R

            weighted_var = sum over R of [w_R * var_R]
            total_weight = sum over non-empty R of [w_R]
            uniformity_score = 100 - 12 * (weighted_var / total_weight)

        Example:
            room_types = [['A', 'A', 'A'],
                          ['x', 'x', 'x'],
                          ['B', 'B', 'B']]
            room_weights = {'A': 1.0, 'B': 2.0, 'C': 3.0}
            temperature_field = [[20.0, 24.0, 22.0],
                                 [30.0, 30.0, 30.0],
                                 [21.0, 25.0, 30.0]]

            weight_mask = [[1.0, 1.0, 1.0],
                           [0.0, 0.0, 0.0],
                           [2.0, 2.0, 2.0]]

            For room type A:
                cells_A = [(0,0), (0,1), (0,2)]
                mean_A = (20 + 24 + 22) / 3 = 22
                var_A = ((20-22)^2 + (24-22)^2 + (22-22)^2) / 3 = 2.667

            For room type B:
                cells_B = [(2,0), (2,1), (2,2)]
                mean_B = (21 + 25 + 30) / 3 = 25.333
                var_B = ((21-25.333)^2 + (25-25.333)^2 + (30-25.333)^2) / 3 = 13.556

            weighted_var = 1.0*2.667 + 2.0*13.556 + 3.0*0.0 = 29.778
            total_weight = 1.0 + 2.0 = 3.0
            uniformity_score = 100 - 12 * (29.778 / 3.0) = -19.111

        Returns:
            Weighted uniformity score (float). Can be negative for very non-uniform fields.
        """
        # Flatten to 1-D so np.bincount can treat each cell independently.
        temps = temperature_field.flatten()
        room_type_codes = self._room_types_to_ascii(floor_map.room_types.flatten())

        # Count cells per room type, and accumulate per-room temperature stats.
        cell_count = np.bincount(room_type_codes)
        sum_temps = np.bincount(room_type_codes, weights=temps)
        sum_temps_sq = np.bincount(room_type_codes, weights=temps ** 2)

        # Only compute statistics for bins that actually contain cells.
        nonempty_mask = cell_count > 0
        room_mean_temps = np.zeros_like(sum_temps)
        room_variance = np.zeros_like(sum_temps)
        room_mean_temps[nonempty_mask] = sum_temps[nonempty_mask] / cell_count[nonempty_mask]
        room_variance[nonempty_mask] = (
            sum_temps_sq[nonempty_mask] / cell_count[nonempty_mask]
        ) - (room_mean_temps[nonempty_mask] ** 2)

        # Retrieve room weights indexed by ASCII code.
        lookup = self._build_weight_lookup(room_weights)
        room_type_weights = lookup[np.arange(len(room_variance))]
        weighted_variances = room_variance * room_type_weights
        total_weight = np.sum(room_type_weights * nonempty_mask)
        mean_weighted_variance = np.sum(weighted_variances) / total_weight
        return 100 - 12 * mean_weighted_variance

    def compute_energy_score(self, energy_dict: dict[str, float]) -> float:
        """
        Provided function.
        Compute an energy score that penalizes high per-minute energy usage.

        Conceptual algorithm:
            If no AC units are running:
                energy_score = 100.0
            Else:
                mean_energy = average of energy_dict.values()
                energy_score = 100 - 2 * mean_energy

        Example:
            energy_dict = {'AC1': 50.0, 'AC2': 30.0}
            mean_energy = 40.0
            energy_score = 20.0
        """
        return 100 - 2 * np.mean(list(energy_dict.values())) if len(energy_dict) > 0 else 100.0

    def compute_total_score(self, state: State) -> None:
        """
        Provided function.
        Compute the composite score and write it back into `state.score`.

        The final stored tuple is:
            (total, comfort, uniformity, energy)

        This is useful because later code can inspect both the final combined
        score and the three component scores without recomputing them.
        """
        comfort = self.compute_comfort_score(
            state.floor_map,
            state.room_weights,
            state.setpoint_temp,
            state.temperature_field,
        )
        uniformity = self.compute_uniformity_score(
            state.floor_map,
            state.room_weights,
            state.temperature_field,
        )
        energy = self.compute_energy_score(state.energy_dict)

        total = (
            self.comfort_weight * comfort
            + self.uniformity_weight * uniformity
            + self.energy_weight * energy
        )
        state.score = (total, comfort, uniformity, energy)

    def __repr__(self) -> str:
        """
        Provided function.
        Short debug representation.
        """
        return (
            f"Scoring(comfort_weight={self.comfort_weight}, "
            f"uniformity_weight={self.uniformity_weight}, "
            f"energy_weight={self.energy_weight})"
        )
