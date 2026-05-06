"""core.simulation

Time-step simulation for heat dynamics.

This module advances a `State` object forward in discrete, per-minute steps by
combining:
- AC injection (point-wise temperature change per AC)
- heat diffusion across the grid
"""

import numpy as np

from .state.ac import ACUnit
from .state.state import State


def _ac_injection(
    temperature_field: np.ndarray,
    ac_units: list[ACUnit],
) -> tuple[np.ndarray, dict[str, float]]:
    """
    Task 4.1.

    Apply each AC unit's temperature change to the grid and record energy usage.

    Conceptual algorithm: for every AC unit `ac` in `ac_units`
        temperature_field[ac.row, ac.col] += ac.get_temperature_change()
        energy_dict[ac.name] = ac.get_energy_consumption()

    No broadcasting trick is needed here: the number of AC units is small
    relative to the grid, and each AC only affects one point.

    Example:
        temperature_field = [[20.0, 20.0],
                             [20.0, 20.0]]
        ac_units = [
            ACUnit(name='AC1', row=0, col=0, mode=MODE_COOL, power_level=2),
            ACUnit(name='AC2', row=1, col=1, mode=MODE_HEAT, power_level=1),
        ]

        AC1 at (0,0): get_temperature_change() = -2.0
                      get_energy_consumption() = 2.0
        AC2 at (1,1): get_temperature_change() = +1.0
                      get_energy_consumption() = 1.0

        -> updated field = [[18.0, 20.0],
                            [20.0, 21.0]]
        -> energy_dict = {'AC1': 2.0, 'AC2': 1.0}

    Args:
        temperature_field: H x W array of current temperatures (degC).
            Not modified in-place.
        ac_units: List of ACUnit instances to apply.

    Returns:
        (updated_temperature_field, energy_dict), where energy_dict maps
        each AC's name to its energy consumed this minute.
    """
    updated_temperature_field = temperature_field.copy()
    energy_dict = {}
    for ac in ac_units:
        updated_temperature_field[ac.row, ac.col] += ac.get_temperature_change()
        energy_dict[ac.name] = ac.get_energy_consumption()
    return (updated_temperature_field, energy_dict)


class Simulator:
    """Simulate heat diffusion with outdoor exchange and AC injection."""

    def __init__(
        self,
        diffusion_rate: float = 0.3,
        diffusion_steps: int = 10,
    ) -> None:
        """
        Provided function.
        Initialize simulator.

        Args:
            diffusion_rate: Diffusion coefficient for heat transfer.
            diffusion_steps: Number of sub-steps for diffusion per minute.
        """
        self.diffusion_rate = diffusion_rate
        self.diffusion_steps = diffusion_steps

    def _ac_injection(
        self,
        temperature_field: np.ndarray,
        ac_units: list[ACUnit],
    ) -> tuple[np.ndarray, dict[str, float]]:
        """
        Wrapper for the module-level `_ac_injection(...)` task function.

        The actual student task lives at module level so the required inputs
        are explicit in the signature.
        """
        return _ac_injection(temperature_field, ac_units)

    def _diffusion_step(
        self,
        temperature_field: np.ndarray,
        outdoor_temp: float,
        conductivity_mask: np.ndarray,
    ) -> np.ndarray:
        """
        Provided function.
        Advance the temperature field by one diffusion sub-step.

        Conceptual algorithm: for every cell (r, c)

        Step 1 - collect the four neighbour temperatures.
            For each direction d in {up, down, left, right}:
                calculate neighbour_r, neighbour_c based on the direction
                If the neighbour is inside the grid:
                    neighbour_temp[d] = temperature_field[neighbor_r, neighbor_c]
                Else:
                    neighbour_temp[d] = outdoor_temp

        Step 2 - compute effective conductivity to each neighbour.
            Let c_self = conductivity_mask[r, c]
                c_neighbour = conductivity_mask[neighbor_r, neighbor_c]
                    (or 1.0 if neighbour is outside the grid)
            Effective conductivity:
                If c_self and c_neighbour not both zero:
                    eff_cond[d] = 2 * c_self * c_neighbour / (c_self + c_neighbour) 
                Else (both zero):
                    eff_cond[d] = 0

        Step 3 - accumulate net heat flux into cell (r, c).
            flux = sum over d of [eff_cond[d] * (neighbour_temp[d] - temp[r, c])] / 4.0

        Step 4 - update the temperature.
            new_temp[r, c] = temp[r, c] + diffusion_rate * flux

        Example (outdoor_temp=10.0, diffusion_rate=0.3):
            temperature_field = [[20.0, 30.0, 10.0],
                                 [10.0, 10.0, 0.0]]
            conductivity_mask = [[0.1, 0.1, 1.0],
                                 [0.0, 0.0, 0.1]]

            For cell (0,0):
                temp[r, c] = 20.0
                c_self = 0.1

                up: neighbour is outside
                    neighbour_temp[up] = outdoor_temp = 10.0
                    c_neighbour = 1.0 (outside of grid)
                    eff_cond = 2 * 0.1 * 1.0 / (0.1 + 1.0) = 0.1818
                down: neighbour is (1,0)
                    neighbour_temp[down] = temp[1, 0] = 10.0
                    c_neighbour = conductivity_mask[1, 0] = 1.0
                    eff_cond = 2 * 0.1 * 0.0 / (0.1 + 0.0) = 0.0
                left: neighbour is outside
                    neighbour_temp[left] = outdoor_temp = 10.0
                    c_neighbour = 1.0 (outside of grid)
                    eff_cond = 2 * 0.1 * 1.0 / (0.1 + 1.0) = 0.1818
                right: neighbour is (0,1)
                    neighbour_temp[right] = temp[0, 1] = 30.0
                    c_neighbour = conductivity_mask[0, 1] = 1.0
                    eff_cond = 2 * 0.1 * 0.1 / (0.1 + 0.1) = 0.1
                
                flux = (0.1818 * (10.0 - 20.0) + 0.0 * (10.0 - 20.0) 
                        + 0.1818 * (10.0 - 20.0) + 0.1 * (30.0 - 20.0)) / 4
                     = -0.659

                new_temp[0, 0] = 20.0 + 0.3 * (-0.659) = 19.802

            For cell(1, 1):
                temp[r, c] = 10.0
                c_self = 0.0

                neighbour_temp = [30.0, 10.0, 10.0, 0.0] (up, down, left, right)
                c_neighbour = [0.1, 1.0, 0.0, 0.1]
                eff_cond = [0.0, 0.0, 0.0, 0.0]
                    (for left cell, both c_self and c_neighbour are zero, so eff_cond is 0)

                flux = (0.0 * (30.0 - 10.0) + 0.0 * (10.0 - 10.0) 
                        + 0.0 * (10.0 - 10.0) + 0.0 * (0.0 - 10.0)) / 4 
                     = 0.0
                new_temp[1, 1] = 10.0 + 0.3 * 0.0 = 10.0


        Args:
            temperature_field: Current H x W temperature array (degC).
                Not modified in-place.
            outdoor_temp: Scalar ambient temperature outside the building.
            conductivity_mask: H x W conductivity array from FloorMap.

        Returns:
            New H x W temperature array after one diffusion sub-step.
        """
        temp_pad = np.pad(temperature_field, pad_width=1, mode='constant', constant_values=outdoor_temp)
        cond_pad = np.pad(conductivity_mask, pad_width=1, mode='constant', constant_values=1.0)

        # Collect neighbour temperatures and conductivities using slicing for the padded arrays.
        temp_up = temp_pad[:-2, 1:-1]
        temp_down = temp_pad[2:, 1:-1]
        temp_left = temp_pad[1:-1, :-2]
        temp_right = temp_pad[1:-1, 2:]
        temp = temp_pad[1:-1, 1:-1]

        cond_up = cond_pad[:-2, 1:-1]
        cond_down = cond_pad[2:, 1:-1]
        cond_left = cond_pad[1:-1, :-2]
        cond_right = cond_pad[1:-1, 2:]
        cond = cond_pad[1:-1, 1:-1]

        # Compute effective conductivity via harmonic mean. Guard against
        # division by zero when both sides are insulating.
        def harmonic_mean(c1, c2):
            denom = c1 + c2
            return np.divide(2 * c1 * c2, denom, out=np.zeros_like(denom), where=denom > 0)

        cond_eff_up = harmonic_mean(cond_up, cond)
        cond_eff_down = harmonic_mean(cond_down, cond)
        cond_eff_left = harmonic_mean(cond_left, cond)
        cond_eff_right = harmonic_mean(cond_right, cond)

        # Net heat flux into each cell: weighted sum of temperature differences
        # from all four neighbours, normalised by 4.
        flux = (
            cond_eff_up * (temp_up - temp)
            + cond_eff_down * (temp_down - temp)
            + cond_eff_left * (temp_left - temp)
            + cond_eff_right * (temp_right - temp)
        ) / 4.0

        return temp + self.diffusion_rate * flux

    def step(self, state: State) -> None:
        """
        Provided function.
        Simulate one minute of heat dynamics and update the state in-place.

        Conceptual algorithm:
            1. Apply AC injection once.
            2. Repeat _diffusion_step `diffusion_steps` times.
            3. Write results back to state.temperature_field and state.energy_dict.

        The conductivity mask is computed once outside the diffusion loop
        because it does not change within one minute.

        Args:
            state: State instance. `temperature_field` and `energy_dict` are
                overwritten; `floor_map`, `ac_units`, and `outdoor_temp` are read.
        """
        temp = state.temperature_field.copy()
        temp, energy_dict = self._ac_injection(temp, state.ac_units)

        conductivity_mask = state.floor_map.get_conductivity_mask()
        for _ in range(self.diffusion_steps):
            temp = self._diffusion_step(temp, state.outdoor_temp, conductivity_mask)

        state.temperature_field = temp
        state.energy_dict = energy_dict

    def __repr__(self) -> str:
        """
        Provided function.
        Short debug representation.

        Example:
            print(simulator)
        """
        return (
            f"Simulator(diffusion_rate={self.diffusion_rate}, "
            f"diffusion_steps={self.diffusion_steps})"
        )