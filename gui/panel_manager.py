"""Panel routing and modal stack management."""

from typing import Optional

from .support import figure_to_surface
from .panels.toolbar_panel import ToolbarPanel
from .panels.step_control_panel import StepControlPanel
from .panels.info_panels import PlayerInfoPanel, EnvScorePanel
from .panels.help_panel import HelpPanel
from .panels.stats_panel import StatsPanel
from .panels.value_input_panels import (
    OutdoorTempPanel,
    TargetTempPanel,
    CellTempPanel,
    RoomWeightPanel,
    OptStepsPanel,
)
from .panels.ac_control_panel import ACControlPanel
from .panels.text_popup_panel import TextPopupPanel
from .panels.plot_popup_panel import PlotPopupPanel
from .panels.confirm_popup_panel import ConfirmPopupPanel
from .panels.optimization_panel import OptimizationPanel


class PanelManager:
    """UI routing manager."""

    def __init__(self, state) -> None:
        self.state = state

        self.toolbar = ToolbarPanel()
        self.step_control = StepControlPanel()
        self.player_info = PlayerInfoPanel()
        self.env_score = EnvScorePanel()

        self._global_panels = [
            self.step_control,
            self.toolbar,
            self.player_info,
            self.env_score,
        ]

        self.help_panel = HelpPanel()
        self.stats_panel = StatsPanel()

        self.outdoor_temp_panel = OutdoorTempPanel()
        self.target_temp_panel = TargetTempPanel()
        self.cell_temp_panel = CellTempPanel()
        self.room_weight_panel = RoomWeightPanel()
        self.opt_steps_panel = OptStepsPanel()

        self.ac_control_panel = ACControlPanel()

        self.text_popup = TextPopupPanel()
        self.plot_popup = PlotPopupPanel()
        self.confirm_popup = ConfirmPopupPanel()

        self.optimization_panel = OptimizationPanel()

        self._modal_stack: list[object] = []

    def top_modal(self) -> Optional[object]:
        return self._modal_stack[-1] if self._modal_stack else None

    def is_any_modal_open(self) -> bool:
        return len(self._modal_stack) > 0

    def open_modal(self, panel, *args, **kwargs) -> None:
        if panel in self._modal_stack:
            self._modal_stack.remove(panel)
        kwargs.setdefault("state", self.state)
        kwargs.setdefault("manager", self)
        panel.open(*args, **kwargs)
        self._modal_stack.append(panel)

    def close_modal(self, panel) -> None:
        if panel in self._modal_stack:
            self._modal_stack.remove(panel)
        panel.close()

    def close_top_modal(self) -> None:
        top = self.top_modal()
        if top is None:
            return
        self.close_modal(top)

    def close_all_modals(self) -> None:
        for panel in list(self._modal_stack):
            panel.close()
        self._modal_stack.clear()

    def show_text_popup(self, title: str, text: str, *, scroll_y: int = 0) -> None:
        self.text_popup.set_content(title=title, text=text, scroll_y=scroll_y)
        self.open_modal(self.text_popup)

    def show_plot_popup(self, title: str, fig) -> None:
        surf = figure_to_surface(fig, max_width=850, max_height=450)
        self.plot_popup.set_content(title=title, surface=surf)
        self.open_modal(self.plot_popup)

    def show_confirm_popup(self, title: str, text: str, on_accept) -> None:
        self.confirm_popup.set_content(title=title, text=text, on_accept=on_accept)
        self.open_modal(self.confirm_popup)

    def route_events(self, events) -> bool:
        state = self.state

        top = self.top_modal()
        if top is not None and bool(top.handle_events(state, self, events)):
            return True

        for panel in self._global_panels:
            if panel.handle_events(state, self, events):
                return True

        return False

    def draw(self, surface, mouse_pos, ui) -> None:
        state = self.state
        for panel in self._global_panels:
            panel.draw(state, self, surface, mouse_pos, ui)
        for panel in self._modal_stack:
            panel.draw(state, self, surface, mouse_pos, ui)
