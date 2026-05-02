"""gui.panels.optimization_panel

Optimization UI panel.

Primary responsibility:
- Provide a UI for running two optimization workflows:
    1) AC placement optimization (for new ACs) based on candidate cells.
    2) Schedule optimization (for existing ACs).

Dependencies and collaboration:
- Depends on pygame for event handling and layout.
- Uses BasePanel for the modal panel contract.
- Reads screen sizing constants from gui/settings.py.
- Collaborates with GameState (`state`) for:
    - `state.run_with_transition(...)` to execute heavy tasks with a fade animation.
    - `state.apply_placement_result(...)` and `state.apply_schedule_result(...)` to apply
        results and centralize sprite/state synchronization.
- Collaborates with the Engine through `state.engine` for optimization computations:
    - `optimize_place_greedy`, `optimize_place_simulated_annealing`,
        `optimize_schedule_greedy_for_existing`, `list_candidates`, `list_acs`.
- Collaborates with PanelManager (`manager`) to open secondary modals and show results:
    - `manager.opt_steps_panel`, `manager.show_confirm_popup(...)`.

Design constraints:
- This panel must remain UI-only and must not reach into UIMapManager or other sibling
    modules; all world mutations happen through GameState APIs.
"""

from dataclasses import dataclass
from typing import Optional

import pygame

from .base_panel import BasePanel
from ..settings import SCREEN_WIDTH, SCREEN_HEIGHT


@dataclass
class PendingAC:
    """UI-only description of an AC to be optimized (not yet applied to the Engine)."""
    name: str
    signed_power: int = 0


class OptimizationPanel(BasePanel):
    """
    Optimization modal panel (menu + config in one panel).

    Refactor rules:
    - Panel stays in UI-only layer.
    - Do NOT access state.map_manager (UIMapManager is a sibling module).
    - Apply results via GameState APIs so sprite sync is centralized:
        state.apply_placement_result(...)
        state.apply_schedule_result(...)

    Transition rule:
    - The heavy optimization computation should run under a transition animation,
      but the panel must not depend on ui_runtime. We call state.run_with_transition(...)
      (wired by Level).
    """

    _global_counter = 0

    def __init__(self) -> None:
        super().__init__()
        w, h = 900, 680
        self.rect = pygame.Rect((SCREEN_WIDTH - w) // 2, (SCREEN_HEIGHT - h) // 2, w, h)

        self.view = "menu"  # "menu" | "placement" | "schedule"

        self.btn_choose_placement = pygame.Rect(self.rect.centerx - 210, self.rect.top + 80, 420, 50)
        self.btn_choose_schedule = pygame.Rect(self.rect.centerx - 210, self.rect.top + 140, 420, 50)

        self.btn_algo = pygame.Rect(0, 0, 0, 0)
        self.btn_steps = pygame.Rect(0, 0, 0, 0)
        self.btn_add = pygame.Rect(0, 0, 0, 0)

        self.btn_run = pygame.Rect(self.rect.centerx - 100, self.rect.bottom - 100, 200, 40)
        self.btn_close = pygame.Rect(self.rect.centerx - 100, self.rect.bottom - 50, 200, 36)

        # Placement config
        self.pending: list[PendingAC] = []
        self.placement_algo = "greedy"  # "greedy" | "sa"
        self.placement_steps = 30
        self.schedule_steps = 30

        self.scroll_y = 0
        self._slider_drag_index: Optional[int] = None
        self._row_slider_rects: list[pygame.Rect] = []
        self._row_remove_rects: list[pygame.Rect] = []

        # Cache the last list rect for consistent estimate placement
        self._last_list_rect = pygame.Rect(0, 0, 0, 0)

    def open(self, *args, **kwargs) -> None:
        """Open the modal; keeps the current view unless invalid."""
        self.is_open = True
        if self.view not in ("menu", "placement", "schedule"):
            self.view = "menu"

    def close(self) -> None:
        """Close the modal and reset transient drag/scroll state."""
        super().close()
        self.view = "menu"
        self.scroll_y = 0
        self._slider_drag_index = None

    # ---------- UI helpers ----------
    def _toggle_algo(self):
        """Toggle placement algorithm between greedy and simulated annealing."""
        self.placement_algo = "sa" if self.placement_algo == "greedy" else "greedy"

    def _add_ac(self):
        """Append a new pending AC entry to the placement configuration."""
        OptimizationPanel._global_counter += 1
        name = f"Optimized AC {OptimizationPanel._global_counter}"
        self.pending.append(PendingAC(name=name, signed_power=0))
        if len(self.pending) > 3:
            self.scroll_y = (len(self.pending) - 3) * 44 + 50

    def _remove_ac(self, idx: int):
        """Remove a pending AC entry by index (no-op if out of range)."""
        if 0 <= idx < len(self.pending):
            self.pending.pop(idx)

    @staticmethod
    def _power_from_slider_x(rect: pygame.Rect, x: int) -> int:
        """Map a slider x-coordinate to a signed power in [-5..5]."""
        if rect.width <= 0:
            return 0
        t = (x - rect.left) / rect.width
        t = max(0.0, min(1.0, t))
        return int(round(-5 + 10 * t))

    @staticmethod
    def _run_with_transition_if_available(state, task, *, label: str) -> None:
        """
        Panels are UI-only and must not depend on TransitionState.
        Level wires transition via GameState.run_with_transition(task, label=...).
        """
        state.run_with_transition(task, label=str(label))

    # ---------- complexity estimate ----------
    def _estimate_total_sim_minutes(self, state) -> int:
        """
        Returns estimated total simulated minutes for the currently selected optimization run.
        """
        if self.view == "placement":
            steps = int(self.placement_steps)
            cand = len(state.engine.list_candidates())
            k = len(self.pending)

            if self.placement_algo == "greedy":
                evals = k * max(0, cand)
            else:
                opt = getattr(state.engine, "_optimizer", None)
                iters = int(getattr(opt, "max_iterations", 500)) if opt is not None else 500
                evals = max(0, iters)

            return int(max(0, evals) * max(0, steps))

        if self.view == "schedule":
            steps = int(self.schedule_steps)
            n_acs = len(state.engine.list_acs())
            evals = max(0, n_acs) * 11
            return int(max(0, evals) * max(0, steps))

        return 0

    # ---------- optimization execution ----------
    def _run_placement(self, state, manager):
        """Run placement optimization and present a confirmation preview.

        This method does not apply results directly; it builds a preview and only applies
        when the user accepts in the confirmation popup.
        """
        if not self.pending:
            return

        candidates = state.engine.list_candidates()
        if not candidates:
            return
        if len(self.pending) > len(candidates):
            return

        specs = []
        for item in self.pending:
            sp = int(max(-5, min(5, item.signed_power)))
            if sp == 0:
                mode, level = ("off", 0)
            elif sp < 0:
                mode, level = ("heat", abs(sp))
            else:
                mode, level = ("cool", sp)
            specs.append({"name": item.name, "mode": mode, "power_level": level})

        steps = int(self.placement_steps)
        algo = self.placement_algo

        def task():
            if algo == "sa":
                placed, final_score = state.engine.optimize_place_simulated_annealing(
                    specs, simulation_steps=steps, apply=False, name_prefix="opt"
                )
                algo_name = "Simulated Annealing"
            else:
                placed, final_score = state.engine.optimize_place_greedy(
                    specs, simulation_steps=steps, apply=False, name_prefix="opt"
                )
                algo_name = "Greedy"

            lines = [f"{ac}" for ac in placed]
            preview = [
                f"Placement Result ({algo_name}, {steps} steps):",
                f"Estimated Score: {final_score:.2f}",
                "",
            ]
            preview += [f"  - {ln}" for ln in lines] if lines else ["  (no change)"]
            preview += ["", "Accept results to apply directly?"]

            def _apply():
                # Apply via GameState API (also responsible for resyncing candidates)
                state.apply_placement_result(placed, name_prefix="opt")

                # Clear panel-local UI state
                self.pending.clear()
                self.scroll_y = 0

            manager.show_confirm_popup("Optimization Result", "\n".join(preview), _apply)

        self._run_with_transition_if_available(
            state,
            task,
            label=f"Optimizing placement ({'SA' if algo == 'sa' else 'Greedy'})...",
        )

    def _run_schedule(self, state, manager):
        """Run schedule optimization for existing ACs and present a confirmation preview."""
        steps = int(self.schedule_steps)

        def task():
            tuned, final_score = state.engine.optimize_schedule_greedy_for_existing(simulation_steps=steps, apply=False)

            lines = [f"{ac}" for ac in tuned]
            preview = [f"Schedule Result (Greedy, {steps} steps):", f"Estimated Score: {final_score:.2f}", ""]
            preview += [f"  - {ln}" for ln in lines] if lines else ["  (no change)"]
            preview += ["", "Accept results to apply directly?"]

            def _apply():
                state.apply_schedule_result(tuned)

            manager.show_confirm_popup("Optimization Result", "\n".join(preview), _apply)

        self._run_with_transition_if_available(state, task, label="Optimizing schedule...")

    # ---------- events ----------
    def handle_events(self, state, manager, events) -> bool:
        """Handle modal input for menu/placement/schedule views."""
        if not self.is_open:
            return False

        consumed = False

        for e in events:
            # Global close keys
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_r, pygame.K_f):
                manager.close_modal(self)
                return True  # ok to early-return: no drag should continue after closing

            # Menu view
            if self.view == "menu":
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    if self.btn_choose_placement.collidepoint(e.pos):
                        self.view = "placement"
                        self.scroll_y = 0
                        consumed = True
                        continue
                    if self.btn_choose_schedule.collidepoint(e.pos):
                        self.view = "schedule"
                        consumed = True
                        continue
                    if self.btn_close.collidepoint(e.pos):
                        manager.close_modal(self)
                        return True
                continue

            # Common close button
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if self.btn_close.collidepoint(e.pos):
                    manager.close_modal(self)
                    return True

            # Steps editor (opens another modal)
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if self.btn_steps.width > 0 and self.btn_steps.collidepoint(e.pos):
                    current = self.placement_steps if self.view == "placement" else self.schedule_steps

                    def _apply_steps(v: int):
                        if self.view == "placement":
                            self.placement_steps = int(v)
                        else:
                            self.schedule_steps = int(v)

                    manager.opt_steps_panel.open_with_value(current, on_apply_int=_apply_steps)
                    manager.open_modal(manager.opt_steps_panel)
                    return True

            # --------------------
            # Placement view events
            # --------------------
            if self.view == "placement":
                if e.type == pygame.MOUSEWHEEL:
                    self.scroll_y -= int(e.y) * 30
                    self.scroll_y = max(0, self.scroll_y)
                    consumed = True
                    continue

                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    if self.btn_algo.width > 0 and self.btn_algo.collidepoint(e.pos):
                        self._toggle_algo()
                        consumed = True
                        continue
                    if self.btn_add.width > 0 and self.btn_add.collidepoint(e.pos):
                        self._add_ac()
                        consumed = True
                        continue

                    # Slider click detect (IMPORTANT: do NOT early-return)
                    for i, srect in enumerate(self._row_slider_rects):
                        if srect.width > 0 and srect.collidepoint(e.pos):
                            self._slider_drag_index = i
                            val = self._power_from_slider_x(srect, int(e.pos[0]))
                            if 0 <= i < len(self.pending):
                                self.pending[i].signed_power = max(-5, min(5, int(val)))
                            consumed = True
                            break  # keep scanning other events in this batch
                    else:
                        # Remove click detect (only if slider not hit)
                        for i, rrect in enumerate(self._row_remove_rects):
                            if rrect.width > 0 and rrect.collidepoint(e.pos):
                                self._remove_ac(i)
                                consumed = True
                                break

                    if self.btn_run.collidepoint(e.pos):
                        self._run_placement(state, manager)
                        return True

                if e.type == pygame.MOUSEMOTION:
                    # If left button is not held, do NOT keep dragging
                    buttons = getattr(e, "buttons", (0, 0, 0))
                    if self._slider_drag_index is not None and (not buttons or buttons[0] == 0):
                        self._slider_drag_index = None

                    if self._slider_drag_index is not None:
                        i = self._slider_drag_index
                        if 0 <= i < len(self._row_slider_rects):
                            srect = self._row_slider_rects[i]
                            if srect.width > 0:
                                val = self._power_from_slider_x(srect, int(e.pos[0]))
                                if 0 <= i < len(self.pending):
                                    self.pending[i].signed_power = max(-5, min(5, int(val)))
                                consumed = True
                                continue

                if e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                    # Always release drag state
                    if self._slider_drag_index is not None:
                        self._slider_drag_index = None
                        consumed = True
                    continue

                continue

            # --------------------
            # Schedule view events
            # --------------------
            if self.view == "schedule":
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    if self.btn_run.collidepoint(e.pos):
                        self._run_schedule(state, manager)
                        return True

        return consumed

    # ---------- drawing ----------
    def draw(self, state, manager, surface, mouse_pos, ui) -> None:
        """Draw menu/config UI, including dynamic slider rect caches."""
        if not self.is_open:
            return

        if self.view == "menu":
            ui.draw_panel_bg(surface, self.rect, title="OPTIMIZATION (K)")
            ui.draw_text(
                surface,
                "Choose optimization type",
                (self.rect.centerx, self.rect.top + 40),
                font=ui.font_panel_hint,
                anchor="midtop",
            )

            ui.draw_button(surface, self.btn_choose_placement, "Optimize AC Placement", mouse_pos=mouse_pos, variant="primary")
            ui.draw_button(surface, self.btn_choose_schedule, "Optimize AC Schedule", mouse_pos=mouse_pos)
            ui.draw_button(surface, self.btn_close, "Close (F/R)", mouse_pos=mouse_pos)
            return

        # Config views
        ui.draw_panel_bg(surface, self.rect, title="OPTIMIZATION (K)")

        # Steps row
        steps = self.placement_steps if self.view == "placement" else self.schedule_steps
        steps_text = f"Simulation Steps: {int(steps)} min"
        steps_text_w = ui.font_panel_hint.size(steps_text)[0]
        btn_w = 140
        total_w = steps_text_w + 10 + btn_w
        start_x = self.rect.centerx - total_w // 2
        steps_y = self.rect.top + 80

        ui.draw_text(surface, steps_text, (start_x, steps_y), font=ui.font_panel_hint, anchor="topleft")
        self.btn_steps = pygame.Rect(start_x + steps_text_w + 10, steps_y - 4, btn_w, 30)

        def draw_small_btn(rect, label):
            ui.draw_button(surface, rect, label, mouse_pos=mouse_pos)

        draw_small_btn(self.btn_steps, "Edit Steps")

        if self.view == "placement":
            algo_text = f'Algorithm: {"Simulated Annealing" if self.placement_algo == "sa" else "Greedy"}'
            algo_text_w = ui.font_panel_hint.size(algo_text)[0]
            btn_w2 = 200
            total_w2 = algo_text_w + 10 + btn_w2
            start_x2 = self.rect.centerx - total_w2 // 2
            algo_y = self.rect.top + 120

            ui.draw_text(surface, algo_text, (start_x2, algo_y), font=ui.font_panel_hint, anchor="topleft")
            self.btn_algo = pygame.Rect(start_x2 + algo_text_w + 10, algo_y - 4, btn_w2, 30)
            draw_small_btn(self.btn_algo, "Toggle Algorithm")

            add_y = self.rect.top + 160
            self.btn_add = pygame.Rect(self.rect.right - 100, add_y - 15, 40, 30)
            ui.draw_text(surface, "Add AC:", (self.btn_add.left - 80, add_y), font=ui.font_panel_hint, anchor="midleft")
            draw_small_btn(self.btn_add, "+")

            # List area (scroll box)
            self._row_slider_rects, self._row_remove_rects = [], []
            list_top = self.rect.top + 190
            list_bottom = self.btn_run.top - 110
            list_rect = pygame.Rect(self.rect.left + 20, list_top, self.rect.width - 40, list_bottom - list_top)
            self._last_list_rect = list_rect

            ui.draw_content_box(surface, list_rect)

            old_clip = surface.get_clip()
            surface.set_clip(list_rect)

            row_h = 44
            start_y = list_top + 10 - self.scroll_y

            name_x = self.rect.left + 60
            pad = 12

            for i, item in enumerate(self.pending):
                curr_y = start_y + i * row_h
                if curr_y + row_h < list_rect.top or curr_y > list_rect.bottom:
                    self._row_slider_rects.append(pygame.Rect(0, 0, 0, 0))
                    self._row_remove_rects.append(pygame.Rect(0, 0, 0, 0))
                    continue

                name_rect = ui.draw_text(surface, item.name, (name_x, curr_y + 6), font=ui.font_panel_hint, anchor="midleft")

                slider_x = name_rect.right + pad
                slider_w = self.rect.right - 350 - slider_x
                slider_w = max(100, slider_w)
                slider_rect = pygame.Rect(slider_x, curr_y, slider_w, 12)
                remove_rect = pygame.Rect(self.rect.right - 80, curr_y - 10, 40, 30)

                self._row_slider_rects.append(slider_rect)
                self._row_remove_rects.append(remove_rect)

                pygame.draw.rect(surface, ui.colors["panel_edge"], slider_rect, 2)

                pwr = int(max(-5, min(5, item.signed_power)))
                t = (pwr + 5) / 10.0
                kx = int(slider_rect.left + t * slider_rect.width)
                knob_rect = pygame.Rect(0, 0, 16, 26)
                knob_rect.center = (kx, slider_rect.centery)
                pygame.draw.rect(surface, ui.colors["panel_edge"], knob_rect, 2, border_radius=4)

                ui.draw_text(
                    surface,
                    ui.power_mode_text(pwr),
                    (slider_rect.right + 25, slider_rect.centery),
                    font=ui.font_panel_hint,
                    anchor="midleft",
                )
                draw_small_btn(remove_rect, "X")

            surface.set_clip(old_clip)

            # Estimate text moved under the scroll box
            total_minutes = self._estimate_total_sim_minutes(state)
            est_text = f"Total steps need to be simulated: {int(total_minutes)} min"
            ui.draw_text(
                surface,
                est_text,
                (list_rect.centerx, list_rect.bottom + 12),
                font=ui.font_panel_hint,
                anchor="midtop",
            )

            # Run button enablement
            candidate_count = len(state.engine.list_candidates())
            has_ac = len(self.pending) > 0
            has_cand = candidate_count > 0
            count_ok = len(self.pending) <= candidate_count
            can_run = has_ac and has_cand and count_ok

            if can_run:
                ui.draw_button(surface, self.btn_run, "Run Placement", mouse_pos=mouse_pos, variant="primary")
            else:
                if not has_cand:
                    msg = "No Candidates"
                elif not has_ac:
                    msg = "Add ACs"
                elif not count_ok:
                    msg = "Not Enough Candidates"
                else:
                    msg = "Disabled"
                ui.draw_button(surface, self.btn_run, msg, mouse_pos=mouse_pos, disabled=True)

        else:
            # Schedule view
            ac_count = len(state.engine.list_acs())
            ui.draw_text(
                surface,
                f"Optimizing schedule for {ac_count} existing ACs.",
                (self.rect.centerx, self.rect.top + 150),
                font=ui.font_panel_hint,
                anchor="midtop",
            )

            total_minutes = self._estimate_total_sim_minutes(state)
            est_text = f"Total steps need to be simulated: {int(total_minutes)} min"
            ui.draw_text(
                surface,
                est_text,
                (self.rect.centerx, self.rect.top + 180),
                font=ui.font_panel_hint,
                anchor="midtop",
            )

            ui.draw_button(surface, self.btn_run, "Run Schedule", mouse_pos=mouse_pos, variant="primary")

        # Close button
        ui.draw_button(surface, self.btn_close, "Close (F/R)", mouse_pos=mouse_pos)
