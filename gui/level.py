"""Top-level GUI composition and frame loop."""

import pygame

from .settings import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE
from .player import Player
from .camera import CameraGroup
from .ui_map_manager import UIMapManager
from .interaction_manager import InteractionManager
from .game_state import GameState

from .coord import VirtualViewport, HouseGridCoord, mouse_pos_from_events
from .overlay import Overlay
from .panel_manager import PanelManager
from .transition import TransitionState
from .paths import asset_path

from bridge.engine import Engine
from core.state.floor_map import FloorMap


class _LevelUIActions:
    """
    Concrete UIActions implementation.
    This is owned by Level (top layer) and may freely call PanelManager.

    This class is the bridge between UI-agnostic InteractionManager and concrete
    panel implementations.
    """
    def __init__(self, state: GameState, panels: PanelManager):
        """Bind actions to the shared GameState and the PanelManager."""
        self.state = state
        self.panels = panels

    def open_cell_temp(self, r: int, c: int, current: float) -> None:
        """Open the cell-temperature editor modal for the selected cell."""
        self.panels.cell_temp_panel.open_cell(int(r), int(c), float(current))
        self.panels.open_modal(self.panels.cell_temp_panel)

    def open_room_weight(self, room_type: str, current: float) -> None:
        """Open the room-weight editor modal for a given room type."""
        self.panels.room_weight_panel.open_room(str(room_type), float(current))
        self.panels.open_modal(self.panels.room_weight_panel)

    def open_ac_control(self, ac_sprite) -> None:
        """Open the AC control modal for a given AC sprite."""
        self.panels.ac_control_panel.open_for_ac(ac_sprite)
        self.panels.open_modal(self.panels.ac_control_panel)


class Level:
    """
    Top-level orchestrator.

    Dependency rules:
    - Level may depend on everything.
    - Second-layer modules (ui_runtime / ui_map_manager / interaction_manager) must not depend on each other.
    - GameState must not store transient input state or panel-stack state.
    """

    def __init__(self, map_layout: str):
        """Construct the full GUI scene for a given map layout."""
        self.display_surface = pygame.display.get_surface()

        # This project never needs text input (IME). Force-disable it.
        pygame.key.stop_text_input()

        # Fixed virtual render target
        self.virtual_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

        self.sprite_groups = {
            "all": CameraGroup(),
            "world": pygame.sprite.Group(),
            "grass": pygame.sprite.Group(),
            "collision": pygame.sprite.Group(),
            "door": pygame.sprite.Group(),
            "ac": pygame.sprite.Group(),
        }

        self.floor_map = FloorMap(map_layout)

        # House grid coord space (shared)
        house_offset_r, house_offset_c = 20, 20
        self.coord = HouseGridCoord(
            house_offset_r=house_offset_r,
            house_offset_c=house_offset_c,
            map_height=self.floor_map.height,
            map_width=self.floor_map.width,
            tile_size=TILE_SIZE,
        )

        # Player
        self.player = self._create_player()
        self.loading_font = pygame.font.Font(str(asset_path("font", "dogicabold.ttf")), 64)

        # Engine
        initial_outdoor = 30.0
        self.engine = Engine(
            floor_map=self.floor_map,
            outdoor_temp=initial_outdoor,
            setpoint_temp=26.0,
            initial_indoor_temp=initial_outdoor,
            history_length=1440,
        )

        # UI runtime
        self.transition = TransitionState()
        self.overlay = Overlay()
        self.viewport = VirtualViewport(SCREEN_WIDTH, SCREEN_HEIGHT)

        # State (lowest layer)
        self.state = GameState(
            player=self.player,
            engine=self.engine,
            floor_map=self.floor_map,  # kept for convenience elsewhere
            sprite_groups=self.sprite_groups,
            coord=self.coord,
        )
        self.player.state = self.state

        # UI map manager depends on GameState
        self.ui_map = UIMapManager(self.state, self.coord)

        # Wire hooks after ui_map exists
        self.state.set_hooks(
            on_sync_acs=lambda: self.ui_map.sync_ac_sprites(self.sprite_groups),
            on_sync_doors=lambda: self.ui_map.sync_door_sprites(self.sprite_groups),
            on_refresh_grass=lambda: self.ui_map.render_grass_only(
                self.sprite_groups, outdoor_temp=float(self.engine.get_outdoor_temp())
            ),
            on_run_with_transition=lambda task, label: self.transition.start(task=task, label=str(label)),
        )

        # Build initial static world
        self.ui_map.render_world(self.sprite_groups, outdoor_temp=initial_outdoor)
        self.ui_map.sync_ac_sprites(self.sprite_groups)

        # Panels first, then UI actions, then interaction
        self.panels = PanelManager(self.state)
        self.ui_actions = _LevelUIActions(self.state, self.panels)
        self.interaction = InteractionManager(self.state, ui=self.ui_actions)

        self.dt = 0.0
        self._mouse_pos_virtual = (0, 0)

    def _create_player(self):
        """Create the player sprite and place it outside/near the house entrance."""
        spawn_x = (self.coord.house_offset_c + self.floor_map.width // 2) * TILE_SIZE
        spawn_y = (self.coord.house_offset_r + self.floor_map.height + 1) * TILE_SIZE
        return Player((spawn_x, spawn_y), self.sprite_groups["all"], self.sprite_groups["collision"])

    def _map_events_to_virtual(self, events, transform):
        """Map a window-space event batch into virtual-space coordinates."""
        mapped = self.viewport.map_events(events, transform=transform)
        self._mouse_pos_virtual = mouse_pos_from_events(mapped, fallback=self._mouse_pos_virtual)
        return mapped

    def _is_interaction_blocked(self) -> bool:
        """Centralized 'blocked' computation (NOT stored in GameState)."""
        return bool(self.transition.is_active or self.panels.is_any_modal_open())

    def run(self, dt, events):
        """One frame of the GUI loop.

        Args:
            dt: Delta time in seconds.
            events: Pygame events from the window (window coordinates).
        """
        # Ensure IME never activates (even if other code tries to start it).
        pygame.key.stop_text_input()

        self.dt = float(dt)
        self.virtual_surface.fill("black")

        # 1) Viewport transform
        window_w, window_h = self.display_surface.get_size()
        transform = self.viewport.compute(window_w, window_h)

        # 2) Map events into virtual space
        mapped_events = self._map_events_to_virtual(events, transform)

        # 3) UI first
        consumed_by_ui = bool(self.panels.route_events(mapped_events))

        # 4) Interaction (only if UI did not consume)
        blocked = self._is_interaction_blocked()
        if not consumed_by_ui:
            self.interaction.handle_events(mapped_events, blocked=blocked)

        # 5) Per-frame interaction update
        self.interaction.update(blocked=blocked, mouse_pos_virtual=self._mouse_pos_virtual)

        # 6) Transition tick
        self.transition.update(self.dt)

        # 7) Draw world + heatmap
        self.ui_map.draw_world(target_surface=self.virtual_surface, state=self.state, overlay=self.overlay, dt=self.dt)

        # 8) Draw UI
        self.overlay.draw(
            self.virtual_surface,
            panels=self.panels,
            mouse_pos=self._mouse_pos_virtual,
            state=self.state,
        )

        # 9) Transition overlay
        self.transition.draw(self.virtual_surface, self.loading_font)

        # 10) Present (letterboxed)
        self.display_surface.fill("black")
        dst_w, dst_h = transform.dst_size
        ox, oy = transform.offset

        if transform.scale != 1.0:
            scaled = pygame.transform.smoothscale(self.virtual_surface, (dst_w, dst_h))
            self.display_surface.blit(scaled, (int(ox), int(oy)))
        else:
            self.display_surface.blit(self.virtual_surface, (int(ox), int(oy)))
