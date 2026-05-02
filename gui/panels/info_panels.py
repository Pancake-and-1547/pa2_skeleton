"""gui.panels.info_panels

Small always-visible informational panels.

Primary responsibility:
- Render read-only status information (player cell, temperatures, scores).

Dependencies and collaboration:
- Depends on pygame for Rect geometry.
- Uses BasePanel as the common interface, but these panels are not modal; they are
    always open (`is_open=True`) and do not consume input.
- Reads from the shared GameState (`state`) and, through it, the Engine model:
    - `state.engine.get_temperature_field()`
    - `state.engine.get_score_tuple()`
    - `state.engine.get_room_weights()`
    - `state.engine.get_outdoor_temp()`
    - `state.engine.get_setpoint_temp()`
- Uses coordinate conversion via `state.coord` to map player world position to house
    cell indices.

Maintenance notes:
- These panels should not mutate state; they are strictly informational.
"""

import pygame

from .base_panel import BasePanel
from ..settings import SCREEN_WIDTH


class _InfoPanelBase(BasePanel):
    """Base class for right-side info panels.

    This base provides a consistent background and a simple multi-line text renderer.
    """
    def __init__(self, rect: pygame.Rect) -> None:
        super().__init__()
        self.is_open = True
        self.rect = rect

    def _draw_lines(self, surface, ui, lines: list[str]) -> None:
        """Draw a list of lines centered vertically within this panel's rect."""
        ui.draw_panel_bg(surface, self.rect, title=None)
        font = ui.font_right
        lh, gap = font.get_height(), 6
        content_h = len(lines) * lh + (len(lines) - 1) * gap
        top_y = self.rect.centery - content_h // 2
        for i, t in enumerate(lines):
            color = ui.colors["muted"] if i == 0 else ui.colors["text"]
            ui.draw_text(surface, t, (self.rect.centerx, top_y + i * (lh + gap)), font=font, anchor="midtop", color=color)

    def handle_events(self, state, manager, events) -> bool:
        return False


class PlayerInfoPanel(_InfoPanelBase):
    """Panel showing information about the cell under the player."""
    def __init__(self) -> None:
        right_w, player_h, pad = 296, 182, 16
        px, py = SCREEN_WIDTH - right_w - pad, pad
        rect = pygame.Rect(px, py, right_w, player_h)
        super().__init__(rect)

    @staticmethod
    def _player_cell_info(state):
        """
        Compute player cell info without relying on GameState helper methods.

        Returns:
            title: str
            temp: float
            room_type: str
            rc: tuple[int, int]  (-1, -1) means outdoor/unknown
        """
        # World-space reference: player rect center (camera-independent)
        player = state.player
        world_pos = None

        if hasattr(player, "rect") and player.rect is not None:
            world_pos = (float(player.rect.centerx), float(player.rect.centery))
        elif hasattr(player, "pos"):
            try:
                world_pos = (float(player.pos.x), float(player.pos.y))
            except Exception:
                world_pos = (0.0, 0.0)
        else:
            world_pos = (0.0, 0.0)

        cell = state.coord.world_to_house_cell(world_pos)

        # Outdoor / invalid
        if cell is None:
            temp = float(state.engine.get_outdoor_temp())
            return ("Outdoor", temp, "x", (-1, -1))

        r, c = int(cell[0]), int(cell[1])

        # Temperature field is authoritative from engine
        field = state.engine.get_temperature_field()
        try:
            temp = float(field[r, c])
        except Exception:
            temp = float(state.engine.get_outdoor_temp())

        # Room type from floor map
        try:
            room_type = state.floor_map.room_types[r, c]
        except Exception:
            room_type = "x"

        return ("Player Cell", temp, str(room_type), (r, c))

    def draw(self, state, manager, surface, mouse_pos, ui) -> None:
        if not self.is_open:
            return

        title, temp, typ, rc = self._player_cell_info(state)
        r, c = rc

        weights = state.engine.get_room_weights()
        weight_text = f"{weights.get(typ, 1.0):.2f}" if (typ and typ != "x" and typ in weights) else "---"

        lines = [
            str(title),
            f"Temperature: {float(temp):.1f}°C{' (outdoor)' if r < 0 or c < 0 else ''}",
            f"Room Type: {typ if typ != 'x' else '---'}",
            f"Room Weight: {weight_text}",
            f"Cell: {f'({r}, {c})' if r >= 0 and c >= 0 else '---'}",
        ]
        self._draw_lines(surface, ui, lines)


class EnvScorePanel(_InfoPanelBase):
    """Panel showing outdoor/target temperatures and the current score breakdown."""
    def __init__(self) -> None:
        right_w, player_h, score_h, pad, gap = 296, 182, 182, 16, 10
        px, py = SCREEN_WIDTH - right_w - pad, pad
        player_rect = pygame.Rect(px, py, right_w, player_h)
        rect = pygame.Rect(px, player_rect.bottom + gap, right_w, score_h)
        super().__init__(rect)

    def draw(self, state, manager, surface, mouse_pos, ui) -> None:
        if not self.is_open:
            return

        total, comfort, uniformity, energy = state.engine.get_score_tuple()
        outdoor = state.engine.get_outdoor_temp()
        target = state.engine.get_setpoint_temp()

        lines = [
            f"Outdoor: {float(outdoor):.2f}°C",
            f"Target: {float(target):.2f}°C",
            f"Score: {float(total):.2f}",
            f"Comfort: {float(comfort):.2f}",
            f"Uniform: {float(uniformity):.2f}",
            f"Energy: {float(energy):.2f}",
        ]
        self._draw_lines(surface, ui, lines)
