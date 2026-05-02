"""gui.panels.value_input_panels

Numeric value input modals.

Primary responsibility:
- Provide reusable modal UIs for editing numeric values via keyboard and mouse wheel.

Dependencies and collaboration:
- Depends on pygame for events and layout.
- Uses BasePanel for modal lifecycle.
- Reads screen sizing constants from gui/settings.py.
- Collaborates with GameState (`state`) in subclasses to apply changes via GameState
    APIs rather than calling Engine directly. This keeps sprite/model synchronization
    centralized (e.g., updating outdoor temp triggers grass refresh).

Panels included:
- OutdoorTempPanel: modifies outdoor temperature (runs under transition).
- TargetTempPanel: modifies setpoint temperature.
- CellTempPanel: modifies a specific cell temperature.
- RoomWeightPanel: modifies a room type weight.
- OptStepsPanel: integer-only input for OptimizationPanel.
"""

from dataclasses import dataclass
from typing import Optional

import pygame

from .base_panel import BasePanel
from .input_helpers import (
    is_dec_key,
    is_dot_key,
    is_inc_key,
    is_minus_key,
    key_to_digit,
    shift_pressed,
)
from ..settings import SCREEN_WIDTH, SCREEN_HEIGHT


def _safe_float(text: str, default: float = 0.0) -> float:
    """Best-effort float parser used for transient UI input."""
    try:
        return float(text)
    except Exception:
        return default


def _safe_int(text: str, default: int = 1) -> int:
    """Best-effort int parser used for transient UI input."""
    try:
        return int(float(text))
    except Exception:
        return default


@dataclass
class _ValueModalConfig:
    """Static configuration for a numeric input modal."""
    title: str
    fmt: str
    wheel_step: float
    wheel_step_shift: float

    inc_label: str
    dec_label: str
    shift_inc_label: str
    shift_dec_label: str
    allow_decimal: bool = True
    allow_negative: bool = True


class _ValueInputModal(BasePanel):
    """
    Generic numeric input modal.

    Refactor rule:
    - Subclasses must apply changes via GameState APIs (not Engine directly),
      so UI can sync consistently.
    """

    INPUT_LINES = (
        'You can press 0~9 and "." and backspace to edit the value above,',
        "mouse value picking is not supported.",
    )

    def __init__(self, cfg: _ValueModalConfig) -> None:
        super().__init__()
        self.cfg = cfg

        w, h = 760, 340
        self.rect = pygame.Rect((SCREEN_WIDTH - w) // 2, (SCREEN_HEIGHT - h) // 2, w, h)

        self.apply_rect = pygame.Rect(self.rect.centerx - 160, self.rect.bottom - 50, 150, 36)
        self.cancel_rect = pygame.Rect(self.rect.centerx + 10, self.rect.bottom - 50, 150, 36)

        self.text: str = ""

    def open_with_value(self, v: float) -> None:
        """Open the modal and populate the text field using the configured format."""
        self.is_open = True
        self.text = self.cfg.fmt.format(float(v))

    def nudge(self, delta: float) -> None:
        """Adjust current numeric text by delta, preserving formatting."""
        v = _safe_float(self.text, 0.0)
        self.text = self.cfg.fmt.format(v + float(delta))

    def apply_value(self, state) -> None:
        """Apply the current value to state.

        Subclasses must override and should call GameState APIs (not Engine directly).
        """
        # Override in subclasses.
        return

    def handle_events(self, state, manager, events) -> bool:
        """Handle editing keys, wheel nudges, and apply/cancel actions."""
        if not self.is_open:
            return False

        consumed = False
        for e in events:
            if e.type == pygame.KEYDOWN and e.key == pygame.K_f:
                self.apply_value(state)
                manager.close_modal(self)
                return True

            if e.type == pygame.KEYDOWN and e.key == pygame.K_r:
                manager.close_modal(self)
                return True

            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if self.apply_rect.collidepoint(e.pos):
                    self.apply_value(state)
                    manager.close_modal(self)
                    return True
                if self.cancel_rect.collidepoint(e.pos):
                    manager.close_modal(self)
                    return True

            if e.type == pygame.MOUSEWHEEL:
                step = self.cfg.wheel_step_shift if shift_pressed() else self.cfg.wheel_step
                self.nudge(step * e.y)
                consumed = True
                continue

            if e.type != pygame.KEYDOWN:
                continue

            if e.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
                consumed = True
                continue

            if is_inc_key(e.key):
                step = self.cfg.wheel_step_shift if shift_pressed() else self.cfg.wheel_step
                self.nudge(step)
                consumed = True
                continue

            if is_dec_key(e.key):
                step = self.cfg.wheel_step_shift if shift_pressed() else self.cfg.wheel_step
                self.nudge(-step)
                consumed = True
                continue

            d = key_to_digit(e.key)
            if d is not None:
                self.text += d
                consumed = True
                continue

            if is_dot_key(e.key):
                if self.cfg.allow_decimal and "." not in self.text:
                    if self.text in ("", "-"):
                        self.text += "0"
                    self.text += "."
                consumed = True
                continue

            if is_minus_key(e.key):
                if self.cfg.allow_negative:
                    if self.text.startswith("-"):
                        self.text = self.text[1:]
                    else:
                        self.text = "-" + self.text
                consumed = True
                continue

        return consumed

    def draw(self, state, manager, surface, mouse_pos, ui) -> None:
        """Draw the modal value and a small help section describing controls."""
        if not self.is_open:
            return

        ui.draw_panel_bg(surface, self.rect, title=self.cfg.title)

        ui.draw_text(
            surface,
            self.text,
            (self.rect.centerx, self.rect.top + 86),
            font=ui.font_panel_value,
            anchor="midtop",
        )

        hints = [
            *self.INPUT_LINES,
            f"Increase {self.cfg.inc_label}: Arrow up / Arrow right / W / D / Wheel up",
            f"Decrease {self.cfg.dec_label}: Arrow down / Arrow left / S / A / Wheel down",
            f"Hold shift: {self.cfg.shift_inc_label}/{self.cfg.shift_dec_label}",
        ]
        yy = self.rect.top + 140
        for t in hints:
            ui.draw_text(surface, t, (self.rect.centerx, yy), font=ui.font_panel_hint, anchor="midtop")
            yy += ui.font_panel_hint.get_height() + 6

        def draw_btn(rect: pygame.Rect, label: str):
            ui.draw_button(surface, rect, label, mouse_pos=mouse_pos)

        draw_btn(self.apply_rect, "Apply (F)")
        draw_btn(self.cancel_rect, "Cancel (R)")


class OutdoorTempPanel(_ValueInputModal):
    """Modal for updating the outdoor temperature via GameState."""
    def __init__(self) -> None:
        super().__init__(
            _ValueModalConfig(
                title="Set Outdoor Temperature",
                fmt="{:.2f}",
                wheel_step=1.0,
                wheel_step_shift=5.0,
                inc_label="+1°C",
                dec_label="-1°C",
                shift_inc_label="+5°C",
                shift_dec_label="-5°C",
            )
        )

    def open(self, *args, **kwargs) -> None:
        state = kwargs.get("state", None)
        v = float(state.engine.get_outdoor_temp()) if state is not None else 0.0
        self.open_with_value(v)

    def apply_value(self, state) -> None:
        """Apply outdoor temperature update under a transition (may be expensive)."""
        new_v = float(_safe_float(self.text, 0.0))

        def task():
            state.set_outdoor_temp(new_v)

        state.run_with_transition(task, label="Updating outdoor temperature...")


class TargetTempPanel(_ValueInputModal):
    """Modal for updating the target/setpoint temperature."""
    def __init__(self) -> None:
        super().__init__(
            _ValueModalConfig(
                title="Set Target Temperature",
                fmt="{:.2f}",
                wheel_step=1.0,
                wheel_step_shift=5.0,
                inc_label="+1°C",
                dec_label="-1°C",
                shift_inc_label="+5°C",
                shift_dec_label="-5°C",
            )
        )

    def open(self, *args, **kwargs) -> None:
        state = kwargs.get("state", None)
        v = float(state.engine.get_setpoint_temp()) if state is not None else 0.0
        self.open_with_value(v)

    def apply_value(self, state) -> None:
        state.set_setpoint_temp(float(_safe_float(self.text, 0.0)))


class CellTempPanel(_ValueInputModal):
    """Modal for setting the temperature of a specific cell (r, c)."""
    def __init__(self) -> None:
        super().__init__(
            _ValueModalConfig(
                title="Set Cell Temperature",
                fmt="{:.2f}",
                wheel_step=0.1,
                wheel_step_shift=1.0,
                inc_label="+0.1°C",
                dec_label="-0.1°C",
                shift_inc_label="+1°C",
                shift_dec_label="-1°C",
            )
        )
        self.cell: Optional[tuple[int, int]] = None

    def open_cell(self, r: int, c: int, current: float) -> None:
        """Open the modal for a given cell coordinate and prefill current value."""
        self.cell = (int(r), int(c))
        self.open_with_value(float(current))

    def close(self) -> None:
        super().close()
        self.cell = None

    def apply_value(self, state) -> None:
        if self.cell is None:
            return
        r, c = self.cell
        state.set_cell_temp(r, c, float(_safe_float(self.text, 0.0)))


class RoomWeightPanel(_ValueInputModal):
    """Modal for updating the weight associated with a room type."""
    def __init__(self) -> None:
        super().__init__(
            _ValueModalConfig(
                title="Set Room Weight",
                fmt="{:.3f}",
                wheel_step=0.1,
                wheel_step_shift=1.0,
                inc_label="+0.1",
                dec_label="-0.1",
                shift_inc_label="+1",
                shift_dec_label="-1",
            )
        )
        self.room_type: Optional[str] = None

    def open_room(self, room_type: str, current: float) -> None:
        self.room_type = str(room_type)
        self.open_with_value(float(current))

    def close(self) -> None:
        super().close()
        self.room_type = None

    def draw(self, state, manager, surface, mouse_pos, ui) -> None:
        if not self.is_open:
            return
        title = f"Set Room Weight (Type {self.room_type or '---'})"
        ui.draw_panel_bg(surface, self.rect, title=title)
        super().draw(state, manager, surface, mouse_pos, ui)

    def apply_value(self, state) -> None:
        if not self.room_type:
            return
        state.set_room_weight(self.room_type, float(_safe_float(self.text, 1.0)))


class OptStepsPanel(BasePanel):
    """
    Integer-only steps modal used by OptimizationPanel.
    """

    def __init__(self) -> None:
        self._cfg = _ValueModalConfig(
            title="Set Simulation Steps",
            fmt="{:.0f}",
            wheel_step=1.0,
            wheel_step_shift=10.0,
            inc_label="+1 step",
            dec_label="-1 step",
            shift_inc_label="+10 steps",
            shift_dec_label="-10 steps",
            allow_decimal=False,
            allow_negative=False,
        )
        super().__init__()
        w, h = 760, 340
        self.rect = pygame.Rect((SCREEN_WIDTH - w) // 2, (SCREEN_HEIGHT - h) // 2, w, h)
        self.apply_rect = pygame.Rect(self.rect.centerx - 160, self.rect.bottom - 50, 150, 36)
        self.cancel_rect = pygame.Rect(self.rect.centerx + 10, self.rect.bottom - 50, 150, 36)
        self.text = "30"
        self.min_value = 1
        self.max_value = 10000
        self.on_apply_int = None  # Callable[[int], None]

    INPUT_LINES = (
        "You can press 0~9 and backspace to edit the value above,",
        "mouse value picking is not supported.",
    )

    def open_with_value(self, v: int, *, on_apply_int) -> None:
        """Open with a starting integer value and a callback to receive the result."""
        self.is_open = True
        self.text = str(int(v))
        self.on_apply_int = on_apply_int

    def close(self) -> None:
        super().close()
        self.on_apply_int = None

    def value(self) -> int:
        """Return the current value clamped into [min_value, max_value]."""
        v = _safe_int(self.text, self.min_value)
        v = max(self.min_value, min(self.max_value, int(v)))
        return v

    def nudge(self, delta: float) -> None:
        """Adjust the integer step count and keep it in the allowed range."""
        self.text = str(int(max(self.min_value, min(self.max_value, self.value() + int(delta)))))

    def apply_value(self, state) -> None:
        """Send the selected integer value back to OptimizationPanel."""
        cb = self.on_apply_int
        if callable(cb):
            cb(self.value())

    def handle_events(self, state, manager, events) -> bool:
        """Handle integer editing, wheel nudges, and apply/cancel actions."""
        if not self.is_open:
            return False

        consumed = False
        for e in events:
            if e.type == pygame.KEYDOWN and e.key == pygame.K_f:
                self.apply_value(state)
                manager.close_modal(self)
                return True

            if e.type == pygame.KEYDOWN and e.key == pygame.K_r:
                manager.close_modal(self)
                return True

            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if self.apply_rect.collidepoint(e.pos):
                    self.apply_value(state)
                    manager.close_modal(self)
                    return True
                if self.cancel_rect.collidepoint(e.pos):
                    manager.close_modal(self)
                    return True

            if e.type == pygame.MOUSEWHEEL:
                step = self._cfg.wheel_step_shift if shift_pressed() else self._cfg.wheel_step
                self.nudge(step * e.y)
                consumed = True
                continue

            if e.type != pygame.KEYDOWN:
                continue

            if e.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
                consumed = True
                continue

            if is_inc_key(e.key):
                step = self._cfg.wheel_step_shift if shift_pressed() else self._cfg.wheel_step
                self.nudge(step)
                consumed = True
                continue

            if is_dec_key(e.key):
                step = self._cfg.wheel_step_shift if shift_pressed() else self._cfg.wheel_step
                self.nudge(-step)
                consumed = True
                continue

            d = key_to_digit(e.key)
            if d is not None:
                self.text += d
                consumed = True
                continue

        return consumed

    def draw(self, state, manager, surface, mouse_pos, ui) -> None:
        if not self.is_open:
            return

        ui.draw_panel_bg(surface, self.rect, title=self._cfg.title)
        ui.draw_text(surface, self.text, (self.rect.centerx, self.rect.top + 86), font=ui.font_panel_value, anchor="midtop")

        hints = [
            *self.INPUT_LINES,
            f"Increase {self._cfg.inc_label}: Arrow up / Arrow right / W / D / Wheel up",
            f"Decrease {self._cfg.dec_label}: Arrow down / Arrow left / S / A / Wheel down",
            f"Hold shift: {self._cfg.shift_inc_label}/{self._cfg.shift_dec_label}",
        ]
        yy = self.rect.top + 140
        for text in hints:
            ui.draw_text(surface, text, (self.rect.centerx, yy), font=ui.font_panel_hint, anchor="midtop")
            yy += ui.font_panel_hint.get_height() + 6

        def draw_btn(rect: pygame.Rect, label: str):
            ui.draw_button(surface, rect, label, mouse_pos=mouse_pos)

        draw_btn(self.apply_rect, "Apply (F)")
        draw_btn(self.cancel_rect, "Cancel (R)")
