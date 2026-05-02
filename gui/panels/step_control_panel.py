"""gui.panels.step_control_panel

Always-visible simulation step control panel.

Primary responsibility:
- Trigger simulation execution and adjust the simulation step size.

Dependencies and collaboration:
- Depends on pygame for input events and drawing.
- Uses BasePanel for a consistent interface, but is not modal (always open).
- Collaborates with GameState (`state`) for:
    - `state.run_with_transition(state.run_simulation_task, ...)` to run simulation.
    - `state.cycle_step_minutes(delta)` to adjust step size.

Maintenance notes:
- Transition animation wiring lives in Level via GameState hooks.
"""

import pygame

from .base_panel import BasePanel


class StepControlPanel(BasePanel):
    """
    Global step/sim control panel (always visible).

    Design note:
    - This panel is UI-only.
    - It requests simulation via GameState API and lets Level decide whether to animate.
    """

    def __init__(self) -> None:
        super().__init__()
        self.is_open = True

        self.rect = pygame.Rect(16, 16, 240, 100)

        btn_h, sim_w, gap = 22, 200, 10
        row1_y = self.rect.top + 36
        row2_y = row1_y + btn_h + 6

        self.step_button_rect = pygame.Rect(int(self.rect.centerx - sim_w / 2), row1_y, sim_w, btn_h)
        small_w = (sim_w - gap) // 2
        self.step_minus_rect = pygame.Rect(self.step_button_rect.left, row2_y, small_w, btn_h)
        self.step_plus_rect = pygame.Rect(self.step_button_rect.right - small_w, row2_y, small_w, btn_h)

    @staticmethod
    def _try_run_simulation(state) -> None:
        """Run the simulation task under a transition animation."""
        state.run_with_transition(state.run_simulation_task, label="Simulating...")

    def handle_events(self, state, manager, events) -> bool:
        """Consume key/click events for simulation and step-size adjustment."""
        if not self.is_open:
            return False

        consumed = False
        for e in events:
            if e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE:
                self._try_run_simulation(state)
                consumed = True

            if e.type == pygame.KEYDOWN and e.key == pygame.K_i:
                if hasattr(state, "cycle_step_minutes"):
                    state.cycle_step_minutes(-1)
                consumed = True

            if e.type == pygame.KEYDOWN and e.key == pygame.K_o:
                if hasattr(state, "cycle_step_minutes"):
                    state.cycle_step_minutes(+1)
                consumed = True

            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if self.step_button_rect.collidepoint(e.pos):
                    self._try_run_simulation(state)
                    consumed = True
                elif self.step_minus_rect.collidepoint(e.pos):
                    if hasattr(state, "cycle_step_minutes"):
                        state.cycle_step_minutes(-1)
                    consumed = True
                elif self.step_plus_rect.collidepoint(e.pos):
                    if hasattr(state, "cycle_step_minutes"):
                        state.cycle_step_minutes(+1)
                    consumed = True

        return consumed

    def draw(self, state, manager, surface, mouse_pos, ui) -> None:
        """Render the panel and its three buttons."""
        if not self.is_open:
            return

        ui.draw_panel_bg(surface, self.rect, title=None)

        step_minutes = state.step_minutes() if hasattr(state, "step_minutes") else 0
        label = f"Step: {ui.format_step_label(int(step_minutes))}"
        ui.draw_text(surface, label, (self.rect.centerx, self.rect.top + 22), font=ui.font_step, anchor="center")

        ui.draw_button(surface, self.step_button_rect, "Simulate (Space)", mouse_pos=mouse_pos, variant="primary")
        ui.draw_button(surface, self.step_minus_rect, "- (I)", mouse_pos=mouse_pos)
        ui.draw_button(surface, self.step_plus_rect, "+ (O)", mouse_pos=mouse_pos)
