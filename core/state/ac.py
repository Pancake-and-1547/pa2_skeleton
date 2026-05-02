"""core.state.ac

Data model for an air-conditioning (AC) unit used by the simulation.
"""

class ACUnit:
    """
    Air-conditioning unit with a fixed grid position and a controllable mode.

    Conventions:
    - power_level is an integer in [0, 5] (both boundaries inclusive).
    - mode is one of MODE_OFF / MODE_COOL / MODE_HEAT.

    If you need to modify the mode or power level of an AC unit, ensure that you keep the above conventions.
    """
    # Mode constants
    MODE_OFF: str = 'off'
    MODE_COOL: str = 'cool'
    MODE_HEAT: str = 'heat'

    # Power level limits
    MAX_POWER_LEVEL: int = 5
    
    # Temperature change per power level (degrees per minute)
    TEMP_CHANGE_PER_LEVEL: float = 1.0
    
    # Energy cost per power level (arbitrary units per minute)
    ENERGY_COST_PER_LEVEL: float = 10.0
    
    def __init__(
        self,
        name: str,
        row: int,
        col: int,
        power_level: int = 3,
        mode: str = MODE_COOL,
    ) -> None:
        """
        Provided function.
        Initialize AC unit.
        
        Args:
            name: Unique identifier used for energy accounting and GUI binding.
            row, col: Grid position on the FloorMap (integer indices).
            power_level: 0..5 inclusive, where 0 behaves like off.
            mode: ACUnit.MODE_OFF, ACUnit.MODE_COOL or ACUnit.MODE_HEAT
        """
        self.name: str = name
        self.row: int = int(row)
        self.col: int = int(col)
        self.power_level: int = int(power_level)
        self.mode: str = str(mode)
    
    def get_temperature_change(self) -> float:
        """
        Task 2.1.

        Calculate the temperature change applied at the AC's grid cell for one simulated minute.

        Conceptual algorithm:
            If mode is MODE_OFF or power_level == 0: return 0.0
            delta = power_level * TEMP_CHANGE_PER_LEVEL
            If mode is MODE_COOL: return -delta   (cooling lowers temperature)
            If mode is MODE_HEAT: return +delta   (heating raises temperature)

        Returns:
            Temperature change (float, °C) for one simulated minute.
            Negative for cooling, positive for heating, 0.0 when off.
        """
        pass

    def get_energy_consumption(self) -> float:
        """
        Task 2.2.

        Calculate the energy consumed by this AC unit for one simulated minute.

        Conceptual algorithm:
            If mode is MODE_OFF or power_level == 0: return 0.0
            return power_level * ENERGY_COST_PER_LEVEL

        Returns:
            Energy consumption (float, arbitrary units) per simulated minute.
            0.0 when off; proportional to power_level otherwise.
        """
        pass
    
    def copy(self) -> "ACUnit":
        """
        Provided function.
        Create a copy of this AC unit.
        
        Returns:
            New ACUnit instance with the same properties.

        This is used by State.copy() and optimizers to avoid mutating shared
        objects between evaluations.
        """
        return ACUnit(self.name, self.row, self.col, self.power_level, self.mode)

    def __repr__(self):
        """
        Provided function.
        Debug-friendly representation, returns the specific string when asked to be converted to string.
        Can be used to print the object for debugging purposes.

        e.g.: print(ACUnit('A1', 2, 3, 4, ACUnit.MODE_COOL))
        """
        return f"ACUnit(name={self.name}, pos=({self.row},{self.col}), power={self.power_level}, mode={self.mode})"
