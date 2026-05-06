"""core.state.state

Container of all data for a full simulation and scoring.

`State` groups together:
- the FloorMap layout
- the current temperature field
- the list of AC units and their settings
- environment parameters (outdoor temp, setpoint temp)
- per-room weights for scoring
- per-minute energy accounting and composite score
"""

from .ac import ACUnit
from .floor_map import FloorMap
import numpy as np

class State:
    """Represent the current state of the simulation/scoring."""

    def __init__(
        self,
        floor_map: FloorMap,
        ac_units: list[ACUnit] | None = None,
        temperature_field: np.ndarray | None = None,
        outdoor_temp: float = 30.0,
        setpoint_temp: float = 26.0,
        room_weights: dict[str, float] | None = None,
        energy_dict: dict[str, float] | None = None,
        score: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0),
    ) -> None:
        """
        Provided function.
        Create a new State.

        Args:
            floor_map: Spatial layout for the simulation.

            ac_units: Optional list of AC units present in the building.
                Empty list by default (no AC units placed).

            temperature_field: Optional HxW numpy array of the temperature per cell.
                If omitted, initializes to `outdoor_temp` everywhere.

            outdoor_temp: Outdoor temperature boundary condition (°C).
                30.0 by default.

            setpoint_temp: Target temperature used for comfort scoring (°C).
                26.0 by default.
                
            room_weights: Optional mapping from room type letter to weight.
                Missing room types default to 1.0.
                type 'x' will not have a room weight.

            energy_dict: Optional mapping from AC name to per-minute energy.
                Empty dictionary by default.

            score: Optional tuple of (total, comfort, uniformity, energy).
                (0.0, 0.0, 0.0, 0.0) by default.
        """

        self.floor_map: FloorMap = floor_map
        self.outdoor_temp: float = float(outdoor_temp)
        self.setpoint_temp: float = float(setpoint_temp)

        if temperature_field is None:
            self.temperature_field: np.ndarray = np.full(
                (floor_map.height, floor_map.width), outdoor_temp, dtype=np.float32
            )
        else:
            self.temperature_field = temperature_field

        # Store a fresh list so later caller-side list mutations do not affect this state.
        self.ac_units: list[ACUnit] = list(ac_units) if ac_units is not None else []

        self.room_weights: dict[str, float] = dict(room_weights) if room_weights is not None else {}
        for rt in np.unique(floor_map.room_types):
            if rt != "x" and rt not in self.room_weights:
                self.room_weights[rt] = 1.0

        self.energy_dict: dict[str, float] = dict(energy_dict) if energy_dict is not None else {}
        self.score: tuple[float, float, float, float] = score  # (total, comfort, uniformity, energy)

    def copy(self) -> "State":
        """
        Provided function.
        Create a deep copy of the state.

        The floor_map reference is shared (assumed unique).
        Temperature field, AC list, and dictionaries are copied.
        """
        return State(
            floor_map=self.floor_map,
            ac_units=[ac.copy() for ac in self.ac_units],
            temperature_field=self.temperature_field.copy(),
            outdoor_temp=float(self.outdoor_temp),
            setpoint_temp=float(self.setpoint_temp),
            room_weights=dict(self.room_weights),
            energy_dict=dict(self.energy_dict),
            score=tuple(self.score),
        )

    def __repr__(self) -> str:
        """
        Provided function.
        Short debug representation.
        """
        return (
            f"State("
            f"floor_map={self.floor_map}, "
            f"ac_units={self.ac_units}, "
            f"temperature_field={self.temperature_field.tolist()!r}, "
            f"outdoor_temp={self.outdoor_temp}, "
            f"setpoint_temp={self.setpoint_temp}, "
            f"room_weights={self.room_weights}, "
            f"energy_dict={self.energy_dict}, "
            f"score={self.score})"
        )
