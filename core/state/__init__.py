"""core.state

Contains the foundational state and domain models for the thermal simulation.
Includes the FloorMap physical layout logic, Air-Conditioning (AC) units models, 
and the overarching State container that ties simulations pieces together.
"""

from .ac import ACUnit
from .floor_map import FloorMap
from .state import State