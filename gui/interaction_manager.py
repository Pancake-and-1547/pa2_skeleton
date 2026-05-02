"""World selection and primary/secondary interaction handling."""

import pygame
from typing import Optional, Tuple, Protocol, runtime_checkable

from .sprites import SelectedIndicator, CandidateIndicator
from .coord import find_sprite_at_house_cell


@runtime_checkable
class UIActions(Protocol):
    """Thin UI facade implemented by Level.

    InteractionManager depends on these high-level UI actions (opening modals) without
    importing PanelManager or any panel modules.
    """
    def open_cell_temp(self, r: int, c: int, current: float) -> None: ...
    def open_room_weight(self, room_type: str, current: float) -> None: ...
    def open_ac_control(self, ac_sprite) -> None: ...


class InteractionManager:
    """Encapsulates world interaction (selection + primary/secondary actions)."""
    def __init__(self, state, ui: UIActions):
        """Create an InteractionManager.

        Args:
            state: Shared GameState.
            ui: UIActions implementation (owned by Level).
        """
        self.state = state
        self.ui = ui

        self.selection_sprite: Optional[SelectedIndicator] = None

        # Visual-only cache. Authoritative positions live in GameState.candidates.
        self.candidate_sprites: dict[tuple[int, int], CandidateIndicator] = {}

        self._last_mouse_pos_virtual: tuple[int, int] = (0, 0)

        # Initial sync from GameState
        self._sync_candidate_visuals_from_state()

    # -------------------- event entrypoint --------------------
    def handle_events(self, events, *, blocked: bool) -> None:
        """
        World interaction entrypoint.
        Level should call this only when UI did NOT consume the batch.

        Args:
            events: Event batch already mapped into virtual coordinates.
            blocked: If True, all interaction is ignored (modal open or transition).
        """
        if blocked:
            return

        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN:
                if e.button == 1:
                    self.do_primary_action(mouse_pos_virtual=e.pos)
                elif e.button == 3:
                    self.do_secondary_action(mouse_pos_virtual=e.pos)
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_f:
                    self.do_primary_action(mouse_pos_virtual=None)
                elif e.key == pygame.K_r:
                    self.do_secondary_action(mouse_pos_virtual=None)

    # -------------------- targeting helpers --------------------
    def get_select_world_pos(self, *, mouse_pos_virtual: Optional[tuple[int, int]]) -> tuple[float, float]:
        """Compute the current selection world position.

        - In free-select mode: use mouse position (virtual) projected into world.
          If mouse_pos_virtual is None (keyboard F/R), fall back to last known mouse.
        - Otherwise: use the player's tool target position.
        """
        s = self.state
        if s.free_select_mode:
            pos = mouse_pos_virtual if mouse_pos_virtual is not None else self._last_mouse_pos_virtual
            return s.sprite_groups["all"].screen_to_world(pos)
        return s.player.get_target_pos()

    def find_ac_at_house_cell(self, r: int, c: int):
        """Return the AC sprite at (r, c) if present, else None."""
        return find_sprite_at_house_cell(self.state.sprite_groups["ac"], self.state.coord, int(r), int(c))

    def find_door_at_house_cell(self, r: int, c: int):
        """Return the door sprite at (r, c) if present, else None."""
        return find_sprite_at_house_cell(self.state.sprite_groups["door"], self.state.coord, int(r), int(c))

    # -------------------- candidate visuals (derived from GameState) --------------------
    def _sync_candidate_visuals_from_state(self) -> None:
        """Make candidate markers match GameState.candidates (real-time derived UI)."""
        s = self.state
        desired = set(getattr(s, "candidates", set()))

        # Add missing markers
        for key in desired:
            if key not in self.candidate_sprites:
                r, c = key
                topleft = s.coord.house_cell_to_world_topleft(int(r), int(c))
                self.candidate_sprites[key] = CandidateIndicator(topleft, [s.sprite_groups["all"]])

        # Remove extra markers
        for key in list(self.candidate_sprites.keys()):
            if key not in desired:
                spr = self.candidate_sprites.pop(key, None)
                if spr:
                    spr.kill()

    def toggle_candidate(self, r: int, c: int) -> None:
        """Toggle candidate in GameState/Engine, then resync visuals."""
        self.state.toggle_candidate(int(r), int(c))
        self._sync_candidate_visuals_from_state()

    # -------------------- selection sprite --------------------
    def clear_selection_sprite(self) -> None:
        """Remove the selection indicator sprite (if any)."""
        if self.selection_sprite:
            self.selection_sprite.kill()
            self.selection_sprite = None

    def update(self, *, blocked: bool, mouse_pos_virtual: tuple[int, int]) -> None:
        """
        Per-frame interaction update.
        """
        # Cache last mouse pos for keyboard actions (F/R) while in free-select mode
        self._last_mouse_pos_virtual = (int(mouse_pos_virtual[0]), int(mouse_pos_virtual[1]))

        s = self.state
        s.player.input_enabled = not blocked

        if blocked:
            self.clear_selection_sprite()
            return

        self._sync_candidate_visuals_from_state()
        self.update_selection_sprite(mouse_pos_virtual=mouse_pos_virtual)

    def update_selection_sprite(self, *, mouse_pos_virtual: tuple[int, int]) -> None:
        """Update the selection indicator to match the currently targeted cell.

        Color meaning (high-level):
        - edit_mode: pink=editable floor/AC; purple=blocked/wall/door.
        - normal: green=interactable (AC/door); yellow=placeable cell;
            pink=candidate cell.
        """
        s = self.state
        world_pos = self.get_select_world_pos(mouse_pos_virtual=mouse_pos_virtual)
        cell = s.coord.world_to_house_cell(world_pos)
        if cell is None:
            self.clear_selection_sprite()
            return

        r, c = cell
        topleft = s.coord.house_cell_to_world_topleft(r, c)

        if s.edit_mode:
            ac = self.find_ac_at_house_cell(r, c)
            if s.floor_map.doors[r, c]:
                color = "purple"
                door = self.find_door_at_house_cell(r, c)
                if door:
                    topleft = door.rect.topleft
            elif s.floor_map.walls[r, c]:
                color = "purple"
            elif (ac is not None) or bool(s.floor_map.floors[r, c]):
                color = "pink"
                if ac is not None:
                    topleft = ac.rect.topleft
            else:
                self.clear_selection_sprite()
                return

            self._set_selection(topleft, color)
            return

        # Normal mode
        if s.floor_map.can_place_ac(r, c):
            ac = self.find_ac_at_house_cell(r, c)
            if ac is not None:
                self._set_selection(ac.rect.topleft, "green")
                return

            # Candidate markers are derived from GameState.candidates
            color = "pink" if s.is_candidate(r, c) else "yellow"
            self._set_selection(topleft, color)
            return

        # Door highlight
        if s.floor_map.doors[r, c]:
            door = self.find_door_at_house_cell(r, c)
            if door is not None:
                self._set_selection(door.rect.topleft, "green")
                return

        self.clear_selection_sprite()

    def _set_selection(self, topleft, color: str) -> None:
        """Create or update the selection sprite at a world topleft with a color."""
        if self.selection_sprite is None:
            self.selection_sprite = SelectedIndicator(topleft, color, [self.state.sprite_groups["all"]])
        else:
            self.selection_sprite.set_state(topleft, color)

    # -------------------- actions --------------------
    def do_primary_action(self, *, mouse_pos_virtual: Optional[tuple[int, int]]) -> None:
        """Execute the primary action for the currently selected cell.

        Behavior summary:
        - edit_mode: open cell temperature editor.
        - door: toggle door via GameState (sprite syncs from model state).
        - empty placeable cell: place an AC.
        - existing AC: open AC control modal.
        """
        s = self.state
        world_pos = self.get_select_world_pos(mouse_pos_virtual=mouse_pos_virtual)
        cell = s.coord.world_to_house_cell(world_pos)
        if cell is None:
            return

        r, c = cell

        if s.edit_mode:
            field = s.engine.get_temperature_field()
            current = float(field[int(r), int(c)])
            self.ui.open_cell_temp(int(r), int(c), current)
            return

        # Door toggle
        if s.floor_map.doors[r, c]:
            s.toggle_door(r, c)
            return

        # AC place or interact
        if not s.floor_map.can_place_ac(r, c):
            return

        ac = self.find_ac_at_house_cell(r, c)
        if ac is None:
            # GameState.place_ac() auto-clears candidate cache when needed
            s.place_ac(r, c, signed_power=0)
            return

        self.ui.open_ac_control(ac)

    def do_secondary_action(self, *, mouse_pos_virtual: Optional[tuple[int, int]]) -> None:
        """Execute the secondary action for the currently selected cell.

        Behavior summary:
        - edit_mode: open room-weight editor (when room type exists).
        - AC present: remove the AC.
        - otherwise (placeable cell): toggle candidate.
        """
        s = self.state
        world_pos = self.get_select_world_pos(mouse_pos_virtual=mouse_pos_virtual)
        cell = s.coord.world_to_house_cell(world_pos)
        if cell is None:
            return

        r, c = cell

        if s.edit_mode:
            ac = self.find_ac_at_house_cell(r, c)
            is_floor_like = (ac is not None) or bool(s.floor_map.floors[r, c])
            if not is_floor_like:
                return

            room_type = s.floor_map.room_types[r, c]
            if (room_type is None) or (room_type == "x"):
                return

            weights = s.engine.get_room_weights()
            current = float(weights.get(room_type, 1.0))
            self.ui.open_room_weight(str(room_type), current)
            return

        # Remove AC if present, otherwise toggle candidate
        ac = self.find_ac_at_house_cell(r, c)
        if ac is not None:
            s.remove_ac_by_name(getattr(ac, "engine_name", ""))
            return

        if s.floor_map.can_place_ac(r, c):
            self.toggle_candidate(r, c)
