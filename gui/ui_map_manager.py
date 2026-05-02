"""Map asset loading, world rendering, and sprite sync."""

import random
import pygame

from .settings import TILE_SIZE
from .sprites import Grass, Floor, Wall, Door, AC
from .support import import_folder, build_heatmap_surface
from .coord import HouseGridCoord
from .paths import asset_path


class UIMapManager:
    """
    UI map renderer / resources / sprite sync.

    Design constraints:
    - Must not depend on ui_runtime or interaction_manager.
    - Depends on GameState (read-only), and reads map via:
        state.engine.get_state().floor_map
    - Coordinate conversions live in coord.py (HouseGridCoord).
    """

    def __init__(self, state, coord: HouseGridCoord):
        """Create a map manager bound to a specific GameState and coord system.

        Args:
            state: GameState-like object providing access to Engine and sprite_groups.
            coord: HouseGridCoord for mapping between house grid cells and world pixels.
        """
        self.state = state
        self.coord = coord

        fm = self._floor_map()
        self.map_height = int(fm.height)
        self.map_width = int(fm.width)

        # Random seeds for grass tiles (bigger than house area)
        big_height = self.map_height + 40
        big_width = self.map_width + 40
        self.grass_seeds = [
            [random.randint(0, 1000) for _ in range(big_width)] for _ in range(big_height)
        ]

        self._load_resources()

    def _floor_map(self):
        """Always read the authoritative floor_map from Engine->State."""
        return self.state.engine.get_state().floor_map

    def _door_is_open(self, floor_map, r: int, c: int) -> bool:
        """Read door state from the authoritative FloorMap."""
        return bool(floor_map.is_door_open(r, c))

    # ----------------------------
    # Resources
    # ----------------------------
    def _load_resources(self):
        """Load image assets used by the world renderer."""
        self.grass_images = {}
        for grass_type in ["universe", "winter", "fall", "spring", "summer", "heaven"]:
            self.grass_images[grass_type] = import_folder(
                asset_path("image", "environment", "grass", grass_type)
            )

        self.floor_images = {
            **{
                c: pygame.image.load(str(asset_path("image", "environment", "floor", f"{c}.bmp"))).convert_alpha()
                for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            },
            "x": pygame.image.load(str(asset_path("image", "environment", "floor", "untype.bmp"))).convert_alpha(),
        }

        wall_types = [
            "x", "l", "r", "u", "b", "lr", "lu", "lb", "ru", "rb", "ub",
            "lru", "lrb", "lub", "rub", "lrub",
        ]
        self.wall_images = {
            wt: pygame.image.load(str(asset_path("image", "environment", "wall", f"{wt}.bmp"))).convert_alpha()
            for wt in wall_types
        }
        self.wall2_images = {
            wt: pygame.image.load(str(asset_path("image", "environment", "wall2", f"{wt}.bmp"))).convert_alpha()
            for wt in wall_types
        }

        self.door_h_closed = pygame.image.load(
            str(asset_path("image", "environment", "door", "horizontal_close.bmp"))
        ).convert_alpha()
        self.door_h_open = pygame.image.load(
            str(asset_path("image", "environment", "door", "horizontal_open.bmp"))
        ).convert_alpha()
        self.door_v_closed = pygame.image.load(
            str(asset_path("image", "environment", "door", "vertical_close.bmp"))
        ).convert_alpha()
        self.door_v_open = pygame.image.load(
            str(asset_path("image", "environment", "door", "vertical_open.bmp"))
        ).convert_alpha()

    # ----------------------------
    # World build (static tiles)
    # ----------------------------
    def render_world(self, sprite_groups, outdoor_temp: float):
        """Render the full world into sprite groups (clear -> grass -> house).

        This rebuilds the world/grass/collision/door groups. Dynamic groups such
        as ACs are handled separately via `sync_ac_sprites`.
        """
        self._clear_sprites(sprite_groups)
        self._render_grass(sprite_groups, float(outdoor_temp))
        self._render_house(sprite_groups)

    def render_grass_only(self, sprite_groups, outdoor_temp: float):
        """Refresh only the grass sprites (used when outdoor temperature changes)."""
        for s in sprite_groups["grass"].sprites():
            s.kill()
        sprite_groups["grass"].empty()
        self._render_grass(sprite_groups, float(outdoor_temp))

    def _clear_sprites(self, sprite_groups):
        """Clear sprite groups that belong to the static world layers."""
        for key in ["world", "grass", "collision", "door"]:
            for s in sprite_groups[key].sprites():
                s.kill()
            sprite_groups[key].empty()

    def _render_grass(self, sprite_groups, outdoor_temp: float):
        """Render a grass background based on the outdoor temperature range."""
        from .settings import TEMPERATURE_RANGES  # local import to avoid cycles

        def get_grass_type(temp: float) -> str:
            for k, (lo, hi) in TEMPERATURE_RANGES.items():
                if lo <= temp < hi:
                    return k
            return "summer"

        grass_type = get_grass_type(outdoor_temp)
        grass_imgs = self.grass_images[grass_type]

        for r in range(len(self.grass_seeds)):
            for c in range(len(self.grass_seeds[0])):
                seed = self.grass_seeds[r][c]
                img = grass_imgs[seed % len(grass_imgs)]
                pos = (c * TILE_SIZE, r * TILE_SIZE)
                Grass(pos, img, [sprite_groups["all"], sprite_groups["world"], sprite_groups["grass"]])

    def _render_house(self, sprite_groups):
        """Render house layers (floors then walls/doors) into sprite groups."""
        self._render_floors(sprite_groups)
        self._render_walls_and_doors(sprite_groups)

    def _render_floors(self, sprite_groups):
        """Render floor tiles based on the floor_map and house offset."""
        fm = self._floor_map()
        offset_r, offset_c = self.coord.house_offset_r, self.coord.house_offset_c
        half_w = TILE_SIZE // 2

        for r in range(self.map_height):
            for c in range(self.map_width):
                if not fm.floors[r, c]:
                    continue

                room_type = fm.room_types[r, c]
                if room_type not in self.floor_images:
                    room_type = "x"
                floor_surf = self.floor_images[room_type]

                pos = ((offset_c + c) * TILE_SIZE, (offset_r + r) * TILE_SIZE)
                Floor(pos, floor_surf, [sprite_groups["all"], sprite_groups["world"]])

                # Fill half-tiles adjacent to walls/doors
                if c > 0 and (fm.walls[r, c - 1] or fm.doors[r, c - 1]):
                    right_half = floor_surf.subsurface((half_w, 0, half_w, TILE_SIZE))
                    Floor(
                        ((offset_c + c - 1) * TILE_SIZE + half_w, (offset_r + r) * TILE_SIZE),
                        right_half,
                        [sprite_groups["all"], sprite_groups["world"]],
                    )

                if c < self.map_width - 1 and (fm.walls[r, c + 1] or fm.doors[r, c + 1]):
                    left_half = floor_surf.subsurface((0, 0, half_w, TILE_SIZE))
                    Floor(
                        ((offset_c + c + 1) * TILE_SIZE, (offset_r + r) * TILE_SIZE),
                        left_half,
                        [sprite_groups["all"], sprite_groups["world"]],
                    )

    def _render_walls_and_doors(self, sprite_groups):
        """Render wall and door tiles, including collision sprites."""
        fm = self._floor_map()
        offset_r, offset_c = self.coord.house_offset_r, self.coord.house_offset_c

        for r in range(self.map_height):
            for c in range(self.map_width):
                pos = ((offset_c + c) * TILE_SIZE, (offset_r + r) * TILE_SIZE)

                if fm.walls[r, c]:
                    connections = self._get_wall_connections(r, c)
                    is_insulated = fm.insulating_walls[r, c]
                    img = (self.wall2_images if is_insulated else self.wall_images)[connections]
                    Wall(pos, img, [sprite_groups["all"], sprite_groups["world"], sprite_groups["collision"]])

                elif fm.doors[r, c]:
                    is_horizontal = self._is_door_horizontal(r, c)

                    if is_horizontal:
                        Floor(pos, self.floor_images["x"], [sprite_groups["all"], sprite_groups["world"]])

                    closed = self.door_h_closed if is_horizontal else self.door_v_closed
                    open_img = self.door_h_open if is_horizontal else self.door_v_open
                    Door(
                        pos,
                        closed,
                        open_img,
                        [sprite_groups["all"], sprite_groups["world"], sprite_groups["door"]],
                        sprite_groups["collision"],
                        house_cell=(int(r), int(c)),
                        is_open=self._door_is_open(fm, int(r), int(c)),
                    )

    def _get_wall_connections(self, r, c):
        """Compute a connection key (e.g. 'lrub') for choosing a wall tile image."""
        fm = self._floor_map()
        connections = ""
        if c > 0 and (fm.walls[r, c - 1] or fm.doors[r, c - 1]):
            connections += "l"
        if c < self.map_width - 1 and (fm.walls[r, c + 1] or fm.doors[r, c + 1]):
            connections += "r"
        if r > 0 and (fm.walls[r - 1, c] or fm.doors[r - 1, c]):
            connections += "u"
        if r < self.map_height - 1 and (fm.walls[r + 1, c] or fm.doors[r + 1, c]):
            connections += "b"
        return connections if connections else "x"

    def _is_door_horizontal(self, r, c):
        """Heuristic for door orientation based on adjacent walls/doors."""
        fm = self._floor_map()
        has_left = c > 0 and (fm.walls[r, c - 1] or fm.doors[r, c - 1])
        has_right = c < self.map_width - 1 and (fm.walls[r, c + 1] or fm.doors[r, c + 1])
        return has_left or has_right

    # ----------------------------
    # Door sprite sync (authoritative = FloorMap / Engine)
    # ----------------------------
    def sync_door_sprites(self, sprite_groups) -> None:
        """Synchronize existing door sprites from the authoritative FloorMap door state."""
        fm = self._floor_map()
        for sprite in sprite_groups.get("door", []):
            house_cell = getattr(sprite, "house_cell", None)
            if house_cell is None:
                continue
            state = self._door_is_open(fm, int(house_cell[0]), int(house_cell[1]))
            if hasattr(sprite, "set_open"):
                sprite.set_open(state)

    # ----------------------------
    # AC sprite sync (authoritative = Engine)
    # ----------------------------
    def sync_ac_sprites(self, sprite_groups) -> None:
        """
        Synchronize AC sprites with Engine state by rebuilding the AC group.

        This is a full rebuild (kill+recreate) to keep UI consistent with Engine.
        Some UI flows may temporarily skip this rebuild to preserve selection; in
        that case the caller is responsible for re-syncing later.
        """
        if "ac" not in sprite_groups:
            return

        for s in list(sprite_groups["ac"].sprites()):
            s.kill()
        sprite_groups["ac"].empty()

        for info in self.state.engine.list_acs():
            r = int(info["row"])
            c = int(info["col"])
            name = str(info["name"])
            signed_power = int(info.get("signed_power", 0))

            topleft = self.coord.house_cell_to_world_topleft(r, c)
            spr = AC(topleft, [sprite_groups["all"], sprite_groups["ac"]])
            spr.engine_name = name

            if hasattr(spr, "set_power"):
                spr.set_power(signed_power)
            elif hasattr(spr, "power"):
                spr.power = signed_power

    # ----------------------------
    # World drawing (moved from Level)
    # ----------------------------
    def draw_world(self, *, target_surface: pygame.Surface, state, overlay, dt: float) -> None:
        """
        Draw world sprites and optional heatmap onto target_surface.

        This method intentionally takes (state, overlay) as parameters so it can:
        - access engine temperature field
        - reuse overlay heatmap font
        without depending on ui_runtime module.
        """
        s = state

        # Draw sprites via camera group
        s.sprite_groups["all"].custom_draw(s.player, target_surface)
        s.sprite_groups["all"].update(float(dt))

        # Heatmap (xray mode)
        if not s.xray_mode:
            return

        if s.heatmap_dirty or (s.heatmap_surface is None):
            s.heatmap_surface = build_heatmap_surface(
                pygame,
                s.engine.get_state().floor_map,  # read map through engine->state
                s.engine.get_temperature_field(),
                TILE_SIZE,
                alpha=234,
                font=overlay.font_heatmap,
            )
            s.heatmap_dirty = False

        ox, oy = self.coord.house_origin_world()
        sx, sy = s.sprite_groups["all"].world_to_screen((ox, oy))
        target_surface.blit(s.heatmap_surface, (int(sx), int(sy)))
