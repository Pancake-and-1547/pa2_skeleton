"""Shared GUI-facing state and mutation facade."""

from typing import Callable, Optional, Iterable, Any


class GameState:
    """
    Lowest-level shared state.

    Rules:
    - Store shared data that multiple UI modules might need.
    - Do NOT store transient input data (mouse position, key states).
    - Do NOT store UI stack state (e.g., "panels open").
    - World updates MUST go through GameState APIs so UI can sync consistently.

    Collaboration map:
    - Level constructs GameState and wires hooks once UIMapManager/Transition exist.
    - InteractionManager calls GameState mutation APIs for doors/AC/candidates.
    - Panels call GameState mutation APIs for temperature/weights/AC power.
    """

    def __init__(
        self,
        *,
        player,
        engine,
        floor_map,
        sprite_groups,
        coord,
        on_sync_acs: Optional[Callable[[], None]] = None,
        on_sync_doors: Optional[Callable[[], None]] = None,
        on_refresh_grass: Optional[Callable[[], None]] = None,
        on_run_with_transition: Optional[Callable[[Callable[[], None], str], None]] = None,
    ) -> None:
        # Core references
        self.player = player
        self.engine = engine
        self.floor_map = floor_map
        self.sprite_groups = sprite_groups
        self.coord = coord

        # Hooks owned by upper layer (Level wires these).
        self._on_sync_acs = on_sync_acs
        self._on_sync_doors = on_sync_doors
        self._on_refresh_grass = on_refresh_grass

        # Optional UI hook: run a task with a transition animation.
        # This keeps panels UI-agnostic (no direct TransitionState dependency).
        self._on_run_with_transition = on_run_with_transition

        # Shared flags (NOT UI stack, NOT transient input)
        self.xray_mode: bool = False
        self.free_select_mode: bool = True
        self.edit_mode: bool = False
        self.run_mode: bool = False

        # Candidate positions (authoritative source = Engine, cached here for UI)
        self.candidates: set[tuple[int, int]] = set()
        self.sync_candidates_from_engine()

        # Heatmap cache (UI-only cache, safe in GameState)
        self.heatmap_dirty: bool = True
        self.heatmap_surface = None

        # Simulation step configuration (minutes)
        self._step_options_minutes: list[int] = [1, 5, 10, 30, 60]
        self._step_index: int = 2  # default = 10 minutes

    # ----------------------------
    # Hook wiring (late binding)
    # ----------------------------
    def set_hooks(
        self,
        *,
        on_sync_acs: Optional[Callable[[], None]] = None,
        on_sync_doors: Optional[Callable[[], None]] = None,
        on_refresh_grass: Optional[Callable[[], None]] = None,
        on_run_with_transition: Optional[Callable[[Callable[[], None], str], None]] = None,
    ) -> None:
        """Wire optional callbacks owned by the top-level orchestrator (Level).

        This late-binding pattern avoids import/initialization cycles:
        - GameState is constructed before UIMapManager/TransitionState exist.
        - Level calls set_hooks(...) afterwards with lambdas bound to those objects.
        """
        if on_sync_acs is not None:
            self._on_sync_acs = on_sync_acs
        if on_sync_doors is not None:
            self._on_sync_doors = on_sync_doors
        if on_refresh_grass is not None:
            self._on_refresh_grass = on_refresh_grass
        if on_run_with_transition is not None:
            self._on_run_with_transition = on_run_with_transition

    # ----------------------------
    # Shared mode flags
    # ----------------------------
    def set_xray_mode(self, enabled: bool) -> bool:
        """Set xray mode and invalidate the cached heatmap when it changes."""
        enabled = bool(enabled)
        if self.xray_mode != enabled:
            self.xray_mode = enabled
            self.mark_heatmap_dirty()
        return self.xray_mode

    def toggle_xray_mode(self) -> bool:
        """Toggle xray mode and return the new value."""
        return self.set_xray_mode(not self.xray_mode)

    def set_free_select_mode(self, enabled: bool) -> bool:
        """Set whether selection follows the mouse instead of the player."""
        self.free_select_mode = bool(enabled)
        return self.free_select_mode

    def toggle_free_select_mode(self) -> bool:
        """Toggle free-select mode and return the new value."""
        return self.set_free_select_mode(not self.free_select_mode)

    def set_edit_mode(self, enabled: bool) -> bool:
        """Set edit mode and return the new value."""
        self.edit_mode = bool(enabled)
        return self.edit_mode

    def toggle_edit_mode(self) -> bool:
        """Toggle edit mode and return the new value."""
        return self.set_edit_mode(not self.edit_mode)

    def set_run_mode(self, enabled: bool) -> bool:
        """Set run mode and return the new value."""
        self.run_mode = bool(enabled)
        return self.run_mode

    def toggle_run_mode(self) -> bool:
        """Toggle run mode and return the new value."""
        return self.set_run_mode(not self.run_mode)

    # ----------------------------
    # Transition helper (UI hook)
    # ----------------------------
    def run_with_transition(self, task: Callable[[], None], *, label: str = "Loading...") -> None:
        """
        Run a task using transition animation if the hook is wired,
        otherwise run the task immediately.

                Intended usage:
                - Panels and UI code can request a transition without depending on
                    gui.transition. The actual animation is provided by Level.
        """
        if callable(self._on_run_with_transition):
            self._on_run_with_transition(task, str(label))
            return
        task()

    # ----------------------------
    # Step / simulation control (used by StepControlPanel)
    # ----------------------------
    def step_minutes(self) -> int:
        """Return the currently selected simulation step size in minutes."""
        if not self._step_options_minutes:
            return 0
        self._step_index = max(0, min(self._step_index, len(self._step_options_minutes) - 1))
        return int(self._step_options_minutes[self._step_index])

    def cycle_step_minutes(self, delta: int) -> int:
        """Cycle the step size by `delta` positions and return the new value."""
        if not self._step_options_minutes:
            return 0
        n = len(self._step_options_minutes)
        self._step_index = (self._step_index + int(delta)) % n
        return self.step_minutes()

    def run_simulation_task(self) -> None:
        """
        Run one simulation step in Engine (blocking).
        Panels may wrap this using state.run_with_transition(...).

        Coupling note:
        - The Engine API surface may vary; we try several method names/signatures.
        - After a successful call we mark the heatmap dirty (xray overlay).
        """
        minutes = int(self.step_minutes())
        if minutes <= 0:
            return

        engine = self.engine
        called = False

        candidates = [
            ("simulate", ("minutes", "dt_minutes", "step_minutes")),
            ("run_simulation", ("minutes", "dt_minutes", "step_minutes")),
            ("step", ("minutes", "dt_minutes", "step_minutes")),
            ("advance", ("minutes", "dt_minutes", "step_minutes")),
            ("tick", ("minutes", "dt_minutes", "step_minutes")),
        ]

        for method_name, kw_names in candidates:
            fn = getattr(engine, method_name, None)
            if not callable(fn):
                continue

            try:
                fn(minutes)
                called = True
                break
            except TypeError:
                pass

            for kw in kw_names:
                try:
                    fn(**{kw: minutes})
                    called = True
                    break
                except TypeError:
                    continue

            if called:
                break

        if not called:
            sim = getattr(engine, "simulator", None)
            if sim is not None:
                fn = getattr(sim, "step", None)
                if callable(fn):
                    try:
                        fn(minutes)
                        called = True
                    except TypeError:
                        try:
                            fn()
                            called = True
                        except TypeError:
                            called = False

        if called:
            self._sync_after_engine_change(sync_acs=False, sync_doors=False, refresh_grass=False, mark_heatmap=True)

    # ----------------------------
    # Heatmap
    # ----------------------------
    def mark_heatmap_dirty(self) -> None:
        """Invalidate the cached heatmap surface so UIMapManager can rebuild it."""
        self.heatmap_dirty = True
        self.heatmap_surface = None

    # ----------------------------
    # Candidates (cached in GameState)
    # ----------------------------
    def sync_candidates_from_engine(self) -> None:
        """Refresh candidate set from Engine (used on init / bulk changes)."""
        self.candidates = {(int(r), int(c)) for (r, c) in self.engine.list_candidates()}

    def is_candidate(self, r: int, c: int) -> bool:
        """Return True if (r, c) is currently a candidate position."""
        return (int(r), int(c)) in self.candidates

    def toggle_candidate(self, r: int, c: int) -> bool:
        """Toggle candidate state in Engine and update the cached set.

        Returns:
            True if the cell becomes a candidate after toggling.
        """
        enabled = bool(self.engine.toggle_candidate(int(r), int(c)))
        key = (int(r), int(c))
        if enabled:
            self.candidates.add(key)
        else:
            self.candidates.discard(key)
        return enabled

    def clear_candidate(self, r: int, c: int) -> None:
        """Force-remove a candidate marker from Engine and from the local cache."""
        self.engine.clear_candidate(int(r), int(c))
        self.candidates.discard((int(r), int(c)))

    # ----------------------------
    # Internal sync helper
    # ----------------------------
    def _sync_after_engine_change(
        self,
        *,
        sync_acs: bool,
        sync_doors: bool,
        refresh_grass: bool,
        mark_heatmap: bool,
    ) -> None:
        """Run the minimal set of visual synchronization steps after a model change.

        Args:
            sync_acs: If True, rebuild/resync AC sprites from the Engine.
            sync_doors: If True, resync door sprites from the Engine/FloorMap state.
            refresh_grass: If True, re-render grass tiles (depends on outdoor temp).
            mark_heatmap: If True, invalidate heatmap cache.
        """
        if refresh_grass and callable(self._on_refresh_grass):
            self._on_refresh_grass()
        if sync_doors and callable(self._on_sync_doors):
            self._on_sync_doors()
        if sync_acs and callable(self._on_sync_acs):
            self._on_sync_acs()
        if mark_heatmap:
            self.mark_heatmap_dirty()

    # ----------------------------
    # World mutation API (authoritative = Engine)
    # ----------------------------
    def set_outdoor_temp(self, value: float) -> None:
        """Set outdoor temperature in the Engine and refresh dependent visuals."""
        self.engine.set_outdoor_temp(float(value))
        self._sync_after_engine_change(sync_acs=False, sync_doors=False, refresh_grass=True, mark_heatmap=True)

    def set_setpoint_temp(self, value: float) -> None:
        """Set target/setpoint temperature in the Engine."""
        self.engine.set_setpoint_temp(float(value))
        self._sync_after_engine_change(sync_acs=False, sync_doors=False, refresh_grass=False, mark_heatmap=True)

    def set_cell_temp(self, r: int, c: int, value: float) -> None:
        """Override a single cell temperature in the Engine."""
        self.engine.set_cell_temp(int(r), int(c), float(value))
        self._sync_after_engine_change(sync_acs=False, sync_doors=False, refresh_grass=False, mark_heatmap=True)

    def set_room_weight(self, room_type: str, weight: float) -> None:
        """Update a room-type comfort weight in the Engine."""
        self.engine.set_room_weight(str(room_type), float(weight))
        self._sync_after_engine_change(sync_acs=False, sync_doors=False, refresh_grass=False, mark_heatmap=True)

    def toggle_door(self, r: int, c: int) -> bool:
        """Toggle a door state in the Engine.

        Returns:
            True if the Engine accepted the toggle.
        """
        ok = bool(self.engine.toggle_door(int(r), int(c)))
        if ok:
            self._sync_after_engine_change(sync_acs=False, sync_doors=True, refresh_grass=False, mark_heatmap=True)
        return ok

    def place_ac(self, r: int, c: int, *, signed_power: int = 0) -> str:
        """Place an AC at (r, c) via the Engine and resync AC sprites.

        Notes:
        - Candidate state for the placed cell is cleared to keep UI markers correct.
        """
        rr, cc = int(r), int(c)
        name = self.engine.place_ac(rr, cc, signed_power=int(signed_power))

        # Keep GameState cache consistent (Engine.place_ac already discards its candidate set).
        self.candidates.discard((rr, cc))

        self._sync_after_engine_change(sync_acs=True, sync_doors=False, refresh_grass=False, mark_heatmap=True)
        return name

    def remove_ac_by_name(self, name: str) -> bool:
        """Remove an AC by its Engine name and resync sprites if successful."""
        ok = bool(self.engine.remove_ac(str(name)))
        if ok:
            self._sync_after_engine_change(sync_acs=True, sync_doors=False, refresh_grass=False, mark_heatmap=True)
        return ok

    def set_ac_power(self, name: str, signed_power: int, *, sync_acs: bool = True) -> bool:
        """Set an AC's signed power level.

        Args:
                name: Engine name/identifier for the AC.
                signed_power: Range -5..5; negative means heat, positive means cool.
                sync_acs: Whether to rebuild/resync AC sprites after the change.

        Important UI coupling:
        - Some panels (ACControlPanel) set `sync_acs=False` to avoid invalidating the
            currently selected sprite during live dragging.
        """
        ok = bool(self.engine.set_ac_power(str(name), int(signed_power)))
        if ok:
            self._sync_after_engine_change(
                sync_acs=bool(sync_acs),
                sync_doors=False,
                refresh_grass=False,
                mark_heatmap=True,
            )
        return ok

    @staticmethod
    def _extract_ac_row_col(ac: Any) -> Optional[tuple[int, int]]:
        """
        Extract (row, col) from either:
        - core ACUnit: ac.row / ac.col
        - dict-like: ac["row"] / ac["col"]
        """
        try:
            r = getattr(ac, "row")
            c = getattr(ac, "col")
            return (int(r), int(c))
        except Exception:
            pass

        try:
            r = ac["row"]
            c = ac["col"]
            return (int(r), int(c))
        except Exception:
            return None

    def apply_placement_result(self, placed_new_acs: Iterable[Any], *, name_prefix: str = "opt") -> None:
        """
        Apply optimizer placement results.

        IMPORTANT FIX:
        - Engine.apply_placement_result(...) may NOT automatically discard candidates
          for cells where new ACs are placed.
        - Candidate markers are derived from GameState.candidates, which is sourced
          from Engine.list_candidates().
        - Therefore we explicitly clear candidates for all placed AC coordinates.

                Collaboration notes:
                - Called by OptimizationPanel after user acceptance.
                - Performs a final resync of candidate caches to keep InteractionManager visuals
                    consistent.
        """
        placed_list = list(placed_new_acs)

        # Apply to engine first (authoritative).
        self.engine.apply_placement_result(placed_list, name_prefix=str(name_prefix))

        # Explicitly clear candidates for placed AC cells (engine + state cache).
        clear_fn = getattr(self.engine, "clear_candidate", None)
        for ac in placed_list:
            rc = self._extract_ac_row_col(ac)
            if rc is None:
                continue
            r, c = rc
            if callable(clear_fn):
                clear_fn(int(r), int(c))
            self.candidates.discard((int(r), int(c)))

        # Final resync to guarantee UI consistency.
        self.sync_candidates_from_engine()

        self._sync_after_engine_change(sync_acs=True, sync_doors=False, refresh_grass=False, mark_heatmap=True)

    def apply_schedule_result(self, tuned_acs: Iterable[Any]) -> None:
        """
        Apply optimizer schedule results.

        Note:
        - Schedule typically doesn't change candidates, but resync is cheap and keeps UI robust.
        """
        self.engine.apply_schedule_result(list(tuned_acs))
        self.sync_candidates_from_engine()
        self._sync_after_engine_change(sync_acs=True, sync_doors=False, refresh_grass=False, mark_heatmap=True)
