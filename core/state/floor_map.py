"""core.state.floor_map

Floor-map parsing and spatial metadata for the simulation.

`FloorMap` turns a text-based map description into numpy arrays that represent:
- blocked cells (walls / doors)
- walkable/occupiable floor cells
- room labels and computed room types
- door state (closed/open mask)
- thermal conductivity mask used by diffusion

Map encoding conventions:
- '#': wall
- '@': insulating wall (completely blocks heat)
    insulating wall counts as a type of wall in all contexts,
    except for conductivity
- '.': floor
- 'A'..'Z': labeled floor cells (also treated as floor)
- '*': door (state tracked separately)

The letters 'A' to 'Z' are room labels, not fixed semantic room meanings.
They simply mark floor cells that belong to a room type. During flood-fill,
every connected component inherits the alphabetically smallest label found
inside that component. For example, if a connected region contains both 'B'
and 'D', the entire region resolves to room type 'B'.
"""

import numpy as np


def check_doors(
    doors: np.ndarray,
    height: int,
    width: int,
    walls: np.ndarray,
) -> bool:
    """
    Validate that every door cell satisfies the placement rule: it must have
    walls or other doors on exactly two opposite sides (top+bottom or
    left+right).

    A door flanked on non-opposite sides (for example top+left) or with
    fewer/more than two blocked neighbours is considered invalid.

    Example:
        map = "# # #\\n"
              "# A *\\n"   <- door at (1,2)
              "# # #"

        door (1,2): up=(0,2)='#' blocked, down=(2,2)='#' blocked,
                    left=(1,1)='A' not blocked, right=out-of-bounds (skipped)
        OK because blocked sides are up+down (opposite)

        map = "# # #\\n"
              "# A #\\n"   <- no doors
              "# # #"
        (no doors -> trivially True)

    Args:
        doors: H x W boolean array where `doors[r, c]` is True exactly when
            `(r, c)` is a door cell. The function should iterate over the door
            cells represented by this mask.
        height: Map height.
        width: Map width.
        walls: H x W boolean array for all structural wall cells, including
            insulating walls. During validation, a neighbouring cell counts as
            blocked if it is a wall cell in `walls` or a door cell in `doors`.

    Returns:
        True if all doors are valid; False if any door violates the rule.
    """
    door_positions = np.argwhere(doors)  # 获取所有门的位置

    for x, y in door_positions:
        count = 0

        # 检查上下左右是否被墙或门包围
        if x > 0 and (walls[x - 1, y] or doors[x - 1, y]):
            count += 1
        if x < height - 1 and (walls[x + 1, y] or doors[x + 1, y]):
            count += 1
        if y > 0 and (walls[x, y - 1] or doors[x, y - 1]):
            count += 1
        if y < width - 1 and (walls[x, y + 1] or doors[x, y + 1]):
            count += 1

        # 检查两个包围物
        if count != 2:
            return False

        if not (
            (x > 0 and x < height - 1 and (walls[x - 1, y] or doors[x - 1, y]) and (walls[x + 1, y] or doors[x + 1, y]))
            or (y > 0 and y < width - 1 and (walls[x, y - 1] or doors[x, y - 1]) and (walls[x, y + 1] or doors[x, y + 1]))):
            return False

    return True

def _flood_fill(
    r: int,
    c: int,
    height: int,
    width: int,
    visited: np.ndarray,
    walls: np.ndarray,
    doors: np.ndarray,
    grid: np.ndarray,
    component_cells: list[tuple[int, int]],
    component_labels: list[str],
) -> None:
    """
    Task 1.2.1.

    Recursively explore all floor cells reachable from (r, c) and collect
    their coordinates and any 'A'-'Z' labels into the caller-provided lists.

    Conceptual algorithm:
        If (r, c) is out of bounds, already visited, or blocked: return.
        Mark (r, c) as visited; append to component_cells.
        If grid[r, c] is 'A'..'Z': append to component_labels.
        Recurse on the four orthogonal neighbours (up, down, left, right).

    Both open and closed doors count as blocked and are never added to a
    component.

    Example:
        grid:
            # # # # # #
            # A . # B #
            # # # # # #

        _flood_fill(1, 1, ...):
            (1,1): not visited, not blocked ->
              mark (1,1) as visited,
              append (1,1) to component_cells,
              grid='A', append 'A' to component_labels

              recurse up    (0,1): '#' blocked -> return
              recurse down  (2,1): '#' blocked -> return
              recurse left  (1,0): '#' blocked -> return
              recurse right (1,2): not visited, not blocked ->
                mark (1,2) as visited,
                append (1,2) to component_cells,
                grid='.', no label appended

        -> component_cells = [(1,1), (1,2)]
        -> component_labels = ['A']

    Args:
        r, c: Starting grid coordinates.
        height, width: Map dimensions.
        visited: H x W boolean array tracking explored cells.
        walls: H x W boolean array for structural wall cells.
        doors: H x W boolean array for door cells.
        grid: Raw character grid.
        component_cells: Accumulates (r, c) of every reachable cell.
        component_labels: Accumulates 'A'-'Z' labels found in the component.
    """
    coordinate = (r, c)
    # 检测是否超出地图范围
    if r < 0 or r >= height or c < 0 or c >= width:
        return None
    # 检测是否已经在 visited, walls, doors, if yes, return
    if visited[r, c] or walls[r, c] or doors[r, c]:
        return None
    visited[r, c] = True
    component_cells.append(coordinate)
    # 检测是不是字母标签
    if grid[r, c] >= 'A' and grid[r, c] <= 'Z':
        component_labels.append(grid[r, c])
    _flood_fill(r - 1, c, height, width, visited, walls, doors, grid, component_cells, component_labels)  # up
    _flood_fill(r + 1, c, height, width, visited, walls, doors, grid, component_cells, component_labels)  # down
    _flood_fill(r, c - 1, height, width, visited, walls, doors, grid, component_cells, component_labels)  # left
    _flood_fill(r, c + 1, height, width, visited, walls, doors, grid, component_cells, component_labels)  # right

def _assign_room_types(
    height: int,
    width: int,
    room_types: np.ndarray,
    visited: np.ndarray,
    walls: np.ndarray,
    doors: np.ndarray,
    grid: np.ndarray,
) -> None:
    """
    Task 1.2.2.

    Assign a room type label to every non-wall, non-door cell by flood-filling
    each connected floor component.

    Conceptual algorithm:
        For each unvisited, non-blocked cell (r, c):
            call _flood_fill to collect all cells and 'A'-'Z' labels in the component
            room_type = min(labels) if any labels were found, else 'x'
            assign room_type to every cell in the component

    Walls and doors are never entered and permanently keep room type 'x'.
    Unlabelled floor components also resolve to 'x'; the `visited` array is
    necessary to distinguish them from unprocessed cells, since both share
    the initial 'x' value in room_types.

    Example:
        grid:
            # # # # # #
            # A B # C #
            # # # # # #
            # . . . . #
            # # # # # #

        Component 1: flood-fill from (1,1) -> cells [(1,1),(1,2)], labels ['A', 'B']
                     room_type = min('A', 'B') = 'A'
                     assign 'A' to (1,1) and (1,2)

        Component 2: flood-fill from (1,4) -> cells [(1,4)], labels ['C']
                     room_type = 'C'
                     assign 'C' to (1,4)

        Component 3: flood-fill from (3,1) -> cells [(3,1),(3,2),(3,3),(3,4)], labels []
                     room_type = 'x'
                     assign 'x' to all component cells

    Args:
        height, width: Map dimensions.
        room_types: Output H x W array to fill.
        visited: H x W boolean helper array.
        walls: H x W boolean array for structural wall cells.
        doors: H x W boolean array for door cells.
        grid: Raw character grid.
    """
    for r in range(height):
        for c in range(width):
            if visited[r, c] or walls[r, c] or doors[r, c]:
                continue

            component_cells = []
            component_labels = []
            _flood_fill(r, c, height, width, visited, walls, doors, grid, component_cells, component_labels)

            room_type = min(component_labels) if component_labels else "x"
            for cell_r, cell_c in component_cells:
                room_types[cell_r, cell_c] = room_type

def get_conductivity_mask(
    height: int,
    width: int,
    walls: np.ndarray,
    insulating_walls: np.ndarray,
    closed_doors_mask: np.ndarray,
) -> np.ndarray:
    """
    Task 1.3. (Broadcasting Task)

    Broadcasting requirement: use broadcasting-style NumPy operations to receive full marks.

    Build the thermal conductivity array used by the diffusion step.

    Each cell is assigned a coefficient based on its type and, for doors,
    its current open/closed state:
        floor cell      -> 1.0  (fully conductive)
        wall cell       -> 0.1  (partially insulating)
        insulating wall -> 0.0  (fully insulating)
        door, closed    -> 0.1  (same as wall)
        door, open      -> 1.0  (same as floor)

    Example:
        grid:                door (1,2) closed:     door (1,2) open:
            # # #               0.1  0.1  0.1          0.1  0.1  0.1
            # A *               0.1  1.0  0.1          0.1  1.0  1.0
            # # #               0.1  0.1  0.1          0.1  0.1  0.1

    Args:
        height, width: Map dimensions.
        walls: Boolean mask of all wall cells.
        insulating_walls: Boolean mask of '@' cells only.
        closed_doors_mask: Boolean mask of currently closed door cells.

    Returns:
        H x W float array of conductivity coefficients.
    """
    conductivity_array = np.zeros((height, width))
    conductivity_array[walls] = 0.1
    conductivity_array[insulating_walls] = 0.0
    conductivity_array[closed_doors_mask] = 0.1
    conductivity_array[~walls & ~insulating_walls & ~closed_doors_mask] = 1.0
    return conductivity_array

class FloorMap:
    """Floor map with room typing, door masks, and thermal conductivity."""

    def __init__(self, map_text: str, auto_check_doors: bool = True, auto_assign_room_types: bool = True) -> None:
        """
        Provided function.
        Parse map from text and initialize basic floor map data.

        Args:
            map_text: Multi-line string with the map layout using the encoding
                described in this module docstring.
            auto_check_doors: Whether to automatically check door validity during initialization.
            auto_assign_room_types: Whether to automatically assign room types during initialization.
        """
        self.map_text: str = map_text.strip()
        lines = [line.strip() for line in map_text.strip().split("\n")]
        self.height: int = len(lines)
        self.width: int = max((len(line) for line in lines), default=0)

        # Validity check 1. All rows should have the same length.
        if not all(len(line) == self.width for line in lines):
            raise ValueError("All rows in the map must have the same length.")

        # Validity check 2. Only valid characters should be present.
        valid_chars = set("#@.*") | set(chr(i) for i in range(ord("A"), ord("Z") + 1))
        if not all(ch in valid_chars for line in lines for ch in line):
            raise ValueError("Map contains invalid characters. Allowed characters are: # @ . * A-Z")

        # Create character grid.
        self.grid: np.ndarray = np.array([list(line) for line in lines])

        # Create masks for different cell types.
        self.insulating_walls: np.ndarray = self.grid == "@"
        self.walls: np.ndarray = (self.grid == "#") | self.insulating_walls
        self.floors: np.ndarray = (self.grid == ".") | ((self.grid >= "A") & (self.grid <= "Z"))
        self.doors: np.ndarray = self.grid == "*"
        self.closed_doors_mask: np.ndarray = self.doors.copy()

        # Validity check 3. Map should contain at least one typed room.
        if not np.any((self.grid >= "A") & (self.grid <= "Z")):
            raise ValueError("Map must contain at least one labeled room (A-Z).")

        # Validity check 4. All doors must be connected with a wall/door on
        # exactly two opposite sides.
        if auto_check_doors and not self.check_doors():
            raise ValueError("Invalid map: All doors must be connected with a wall/door on exactly two opposite sides.")

        # Room type assignment (will be filled by flood fill).
        # Untyped / closed door / wall cells have room type 'x'.
        self.room_types: np.ndarray = np.full((self.height, self.width), "x", dtype=object)

        # Assistant array for flood fill, to track visited cells during room type assignment.
        self.visited: np.ndarray = np.zeros((self.height, self.width), dtype=bool)

        if auto_assign_room_types:
            self._assign_room_types()

    def is_blocked(self, r: int, c: int) -> bool:
        """
        Provided function.
        Check whether a cell at (r, c) is a structural blocker (wall/door).
        """
        return bool(self.walls[r, c] or self.doors[r, c])

    def check_doors(self) -> bool:
        """
        Wrapper for the module-level `check_doors(...)` task function.

        This method forwards the `FloorMap` instance data that the standalone
        task function needs.
        """
        return check_doors(self.doors, self.height, self.width, self.walls)

    def _assign_room_types(self) -> None:
        """
        Wrapper for the module-level `_assign_room_types(...)` task function.

        The actual required logic lives at module level so the task's data
        dependencies are explicit in the function signature.
        """
        _assign_room_types(
            self.height,
            self.width,
            self.room_types,
            self.visited,
            self.walls,
            self.doors,
            self.grid,
        )

    def _flood_fill(
        self,
        r: int,
        c: int,
        component_cells: list[tuple[int, int]],
        component_labels: list[str],
    ) -> None:
        """
        Wrapper for the module-level `_flood_fill(...)` task function.

        The standalone worker receives the wall/door masks and accumulator
        lists directly instead of reading hidden state.
        """
        _flood_fill(
            r,
            c,
            self.height,
            self.width,
            self.visited,
            self.walls,
            self.doors,
            self.grid,
            component_cells,
            component_labels,
        )

    def get_conductivity_mask(self) -> np.ndarray:
        """
        Wrapper for the module-level `get_conductivity_mask(...)` task function.

        Returns:
            H x W float array of conductivity coefficients.
        """
        return get_conductivity_mask(
            self.height,
            self.width,
            self.walls,
            self.insulating_walls,
            self.closed_doors_mask,
        )

    def can_place_ac(self, r: int, c: int) -> bool:
        """
        Provided function.
        Return True if an AC can be placed at grid cell (r, c).
        """
        if r < 0 or r >= self.height or c < 0 or c >= self.width:
            return False
        return bool(self.floors[r, c])

    def toggle_door(self, r: int, c: int) -> bool:
        """
        Provided function.
        Toggle door state at (r, c).
        Returns True if successful, False if not a door.
        """
        if r < 0 or r >= self.height or c < 0 or c >= self.width:
            return False
        if not self.doors[r, c]:
            return False
        self.closed_doors_mask[r, c] = not self.closed_doors_mask[r, c]
        return True

    def is_door_open(self, r: int, c: int) -> bool:
        """
        Provided function.
        Return True if (r, c) is a door cell and that door is currently open.
        """
        if r < 0 or r >= self.height or c < 0 or c >= self.width:
            return False
        return bool(self.doors[r, c] and not self.closed_doors_mask[r, c])

    def get_all_placeable_positions(self) -> list[tuple[int, int]]:
        """
        Provided function.
        Get list of all positions where AC can be placed.
        Returns list of (r, c) tuples.

        This can be used by optimizers to enumerate candidate placements.
        """
        positions: list[tuple[int, int]] = []
        for r in range(self.height):
            for c in range(self.width):
                if self.can_place_ac(r, c):
                    positions.append((r, c))
        return positions

    def __repr__(self) -> str:
        """
        Provided function.
        Short debug representation.
        """
        room_types_repr = f"np.array({self.room_types.tolist()!r}, dtype=object)"
        return (
            f"FloorMap(size={self.height}x{self.width}, "
            f"map_text={self.map_text!r}, "
            f"room_types={room_types_repr}, "
            f"closed_doors_mask=np.array({self.closed_doors_mask.tolist()!r}, dtype=bool))"
        )
