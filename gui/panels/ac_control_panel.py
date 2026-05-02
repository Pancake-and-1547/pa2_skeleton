"""gui.panels.ac_control_panel

AC control modal for adjusting the power of a single AC instance.

Primary responsibility:
- Provide a UI (slider, wheel, hotkeys) to change an AC's power in real time.

Dependencies and collaboration:
- Depends on pygame for event types and Rect geometry.
- Uses BasePanel as the common panel interface.
- Reads screen sizing constants from gui/settings.py.
- Collaborates with PanelManager (passed in as `manager`) for modal lifecycle.
- Collaborates with GameState (passed in as `state`) to apply changes via
    `state.set_ac_power(name, power, sync_acs=False)`.

Important coupling/side effects:
- This panel intentionally avoids triggering a full AC sprite rebuild while dragging.
    Rebuilding sprites can invalidate the currently selected sprite object.
- If sprites are rebuilt externally, the panel will re-bind the selected sprite using
    a stable identifier (`engine_name`) stored as `ac_name`.
"""

import pygame

from .base_panel import BasePanel
from .input_helpers import is_dec_key, is_inc_key, shift_pressed
from ..settings import SCREEN_WIDTH, SCREEN_HEIGHT


class ACControlPanel(BasePanel):
    """
    AC control modal with slider + drag.
    """

    def __init__(self) -> None:
        super().__init__()
        w, h = 760, 400
        self.rect = pygame.Rect((SCREEN_WIDTH - w) // 2, (SCREEN_HEIGHT - h) // 2, w, h)

        self.apply_rect = pygame.Rect(self.rect.centerx - 160, self.rect.bottom - 50, 150, 36)
        self.cancel_rect = pygame.Rect(self.rect.centerx + 10, self.rect.bottom - 50, 150, 36)

        self.slider_rect = pygame.Rect(self.rect.left + 90, self.rect.top + 190, self.rect.width - 180, 12)
        self.knob_rect = pygame.Rect(0, 0, 16, 26)

        self._dragging = False

        self.selected_ac = None
        self.ac_name = None
        self.power = 0
        self._initial_power = 0

    def open_for_ac(self, ac_sprite) -> None:
        """Open the modal for a specific AC sprite.

        Args:
            ac_sprite: A UI sprite representing an AC. Expected attributes:
                - engine_name: stable identifier mapping back to the Engine model.
                - power: current signed power (-5..5)
        """
        self.is_open = True
        self.selected_ac = ac_sprite
        self.ac_name = getattr(ac_sprite, "engine_name", None)
        self.power = int(getattr(ac_sprite, "power", 0))
        self._initial_power = self.power
        self._dragging = False

    def close(self) -> None:
        """Close the modal and clear selection/drag state."""
        super().close()
        self._dragging = False
        self.selected_ac = None
        self.ac_name = None
        self.power = 0
        self._initial_power = 0

    def _rebind_selected_ac(self, state) -> None:
        """
        Rebind selected_ac from current sprite_groups["ac"] by engine_name.
        This makes the panel robust even if sprites were rebuilt externally.
        """
        nm = self.ac_name
        if not nm:
            self.selected_ac = None
            return

        grp = state.sprite_groups.get("ac", None)
        if grp is None:
            self.selected_ac = None
            return

        for spr in grp:
            if getattr(spr, "engine_name", None) == nm:
                self.selected_ac = spr
                # Keep local power consistent with sprite
                try:
                    self.power = int(getattr(spr, "power", self.power))
                except Exception:
                    pass
                return

        self.selected_ac = None

    @staticmethod
    def _power_from_slider_x(rect: pygame.Rect, x: int) -> int:
        """Convert an x coordinate inside a slider rect into a signed power.

        The mapping is linear from [-5..5] across the width of the slider.
        """
        if rect.width <= 0:
            return 0
        t = (x - rect.left) / rect.width
        t = max(0.0, min(1.0, t))
        return int(round(-5 + 10 * t))

    def _apply_power(self, state, pwr: int) -> None:
        """
        Apply power change without rebuilding AC sprites.

        Collaboration rules:
        - UI feedback: update the currently bound sprite object (if still alive).
        - Model update: call the GameState API with `sync_acs=False` so the UI layer
            does not lose selection due to sprite regeneration.
        """
        self.power = max(-5, min(5, int(pwr)))

        # Update sprite immediately (user feedback)
        if self.selected_ac is not None and getattr(self.selected_ac, "alive", lambda: True)():
            if hasattr(self.selected_ac, "set_power"):
                self.selected_ac.set_power(self.power)
            else:
                self.selected_ac.power = int(self.power)

        # Update engine via GameState API; do NOT resync sprites here.
        nm = self.ac_name
        if nm is not None:
            state.set_ac_power(str(nm), int(self.power), sync_acs=False)

    def handle_events(self, state, manager, events) -> bool:
        """Handle modal input.

        Returns True if input was consumed (including closing the modal).
        """
        if not self.is_open:
            return False

        # If sprite was rebuilt, re-bind instead of closing immediately.
        if self.ac_name and (self.selected_ac is None or (hasattr(self.selected_ac, "alive") and not self.selected_ac.alive())):
            self._rebind_selected_ac(state)

        # If the AC no longer exists, close panel.
        if self.ac_name and self.selected_ac is None:
            manager.close_modal(self)
            return True

        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_f:
                    manager.close_modal(self)
                    return True

                if e.key == pygame.K_r:
                    # Restore initial power (no sprite rebuild)
                    self._apply_power(state, self._initial_power)
                    manager.close_modal(self)
                    return True

                if is_inc_key(e.key):
                    step = 2 if shift_pressed() else 1
                    self._apply_power(state, self.power + step)
                    return True

                if is_dec_key(e.key):
                    step = 2 if shift_pressed() else 1
                    self._apply_power(state, self.power - step)
                    return True

            if e.type == pygame.MOUSEWHEEL:
                step = 2 if shift_pressed() else 1
                self._apply_power(state, self.power + step * e.y)
                return True

            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if self.apply_rect.collidepoint(e.pos):
                    manager.close_modal(self)
                    return True

                if self.cancel_rect.collidepoint(e.pos):
                    self._apply_power(state, self._initial_power)
                    manager.close_modal(self)
                    return True

                if self.slider_rect.collidepoint(e.pos):
                    self._dragging = True
                    self._apply_power(state, self._power_from_slider_x(self.slider_rect, int(e.pos[0])))
                    return True

            if e.type == pygame.MOUSEMOTION and self._dragging:
                self._apply_power(state, self._power_from_slider_x(self.slider_rect, int(e.pos[0])))
                return True

            if e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                self._dragging = False

        return False

    def draw(self, state, manager, surface, mouse_pos, ui) -> None:
        """Render panel chrome + slider + hints."""
        if not self.is_open:
            return

        ui.draw_panel_bg(surface, self.rect, title="AC Control")

        name = self.ac_name or "---"
        ui.draw_text(
            surface,
            f"Name: {name}",
            (self.rect.centerx, self.rect.top + 84),
            font=ui.font_panel_value,
            anchor="midtop",
        )
        ui.draw_text(
            surface,
            ui.power_mode_text(self.power),
            (self.rect.centerx, self.rect.top + 84 + ui.font_panel_value.get_height() + 6),
            font=ui.font_panel_value,
            anchor="midtop",
        )

        # Slider
        pygame.draw.rect(surface, (255, 255, 255), self.slider_rect, 2)

        t = (max(-5, min(5, int(self.power))) + 5) / 10.0
        kx = int(self.slider_rect.left + t * self.slider_rect.width)
        self.knob_rect.center = (kx, self.slider_rect.centery)
        pygame.draw.rect(surface, (255, 255, 255), self.knob_rect, 2)

        # Hints
        hints = [
            "Increase +1: Arrow up/right / W / D / Wheel up",
            "Decrease -1: Arrow down/left / S / A / Wheel down",
            "Hold shift for +/-2",
        ]
        yy = self.rect.bottom - 140
        for tline in hints:
            ui.draw_text(surface, tline, (self.rect.centerx, yy), font=ui.font_panel_hint, anchor="midtop")
            yy += ui.font_panel_hint.get_height() + 6

        def draw_btn(rect: pygame.Rect, label: str):
            ui.draw_button(surface, rect, label, mouse_pos=mouse_pos)

        draw_btn(self.apply_rect, "Apply (F)")
        draw_btn(self.cancel_rect, "Cancel (R)")
