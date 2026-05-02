"""Shared Engine facade and internal services."""

from typing import Any, Iterable, Optional

import numpy as np


class SimulationSession:
    """Owns the live state, time, score refresh, and history snapshots."""

    def __init__(
        self,
        *,
        core,
        scoring,
        floor_map,
        outdoor_temp: float,
        setpoint_temp: float,
        initial_indoor_temp: float,
        history_length: int,
    ) -> None:
        self._core = core
        self._scoring = scoring
        self.state = core.State(
            floor_map=floor_map,
            ac_units=[],
            temperature_field=np.full(
                (floor_map.height, floor_map.width),
                float(initial_indoor_temp),
                dtype=np.float32,
            ),
            outdoor_temp=float(outdoor_temp),
            setpoint_temp=float(setpoint_temp),
            room_weights=None,
            energy_dict=None,
            score=(0.0, 0.0, 0.0, 0.0),
        )
        self.time = 0
        self.history_length = max(1, int(history_length))
        self.history: list[tuple[int, Any]] = []
        self.recompute_score()
        self.write_history_current()

    def recompute_score(self) -> None:
        if self.state.energy_dict is None:
            self.state.energy_dict = {}
        self._scoring.compute_total_score(self.state)

    def step(self, simulator, minutes: int) -> None:
        for _ in range(int(minutes)):
            simulator.step(self.state)
            self._scoring.compute_total_score(self.state)
            self.time += 1
            self.append_history_new_timestamp()

    def set_history_length(self, history_length: int) -> None:
        self.history_length = max(1, int(history_length))
        self.trim_history()

    def copy_state_snapshot(self, state) -> Any:
        return self._core.State(
            floor_map=state.floor_map,
            ac_units=[ac.copy() for ac in state.ac_units],
            temperature_field=state.temperature_field.copy(),
            outdoor_temp=float(state.outdoor_temp),
            setpoint_temp=float(state.setpoint_temp),
            room_weights=dict(state.room_weights) if state.room_weights is not None else {},
            energy_dict=dict(state.energy_dict) if state.energy_dict is not None else {},
            score=tuple(state.score),
        )

    def write_history_current(self) -> None:
        snap = self.copy_state_snapshot(self.state)
        if not self.history:
            self.history.append((int(self.time), snap))
            self.trim_history()
            return

        last_t, _ = self.history[-1]
        if int(last_t) == int(self.time):
            self.history[-1] = (int(self.time), snap)
        else:
            self.history.append((int(self.time), snap))
        self.trim_history()

    def append_history_new_timestamp(self) -> None:
        self.history.append((int(self.time), self.copy_state_snapshot(self.state)))
        self.trim_history()

    def trim_history(self) -> None:
        excess = len(self.history) - int(self.history_length)
        if excess > 0:
            del self.history[:excess]


class ACService:
    """Handles candidate markers and AC CRUD on the live state."""

    def __init__(self, *, core, session: SimulationSession) -> None:
        self._core = core
        self._session = session
        self._ac_candidates: set[tuple[int, int]] = set()
        self._ac_counter = 0
        self._opt_ac_counter = 0

    @property
    def state(self):
        return self._session.state

    def list_acs(self) -> list[dict[str, Any]]:
        items = []
        for ac in self.state.ac_units:
            items.append(
                {
                    "name": ac.name,
                    "row": int(ac.row),
                    "col": int(ac.col),
                    "signed_power": int(self.to_signed_power(ac)),
                    "mode": ac.mode,
                    "power_level": int(ac.power_level),
                }
            )
        return items

    def list_candidates(self) -> list[tuple[int, int]]:
        return sorted((int(r), int(c)) for (r, c) in self._ac_candidates)

    def toggle_candidate(self, r: int, c: int) -> bool:
        key = (int(r), int(c))
        if key in self._ac_candidates:
            self._ac_candidates.remove(key)
            return False
        self._ac_candidates.add(key)
        return True

    def clear_candidate(self, r: int, c: int) -> None:
        self._ac_candidates.discard((int(r), int(c)))

    def clear_all_candidates(self) -> None:
        self._ac_candidates.clear()

    def place_ac(self, r: int, c: int, *, name: Optional[str] = None, signed_power: int = 0) -> str:
        rr, cc = int(r), int(c)
        if not self.state.floor_map.can_place_ac(rr, cc):
            raise ValueError(f"Cannot place AC at ({rr}, {cc}).")
        if self.find_ac_index_at(rr, cc) is not None:
            raise ValueError(f"An AC already exists at ({rr}, {cc}).")

        final_name = self.new_unique_ac_name("ac") if name is None else str(name)
        if name is not None and self.find_ac_by_name(final_name) is not None:
            raise ValueError(f"AC name already exists: {final_name}")

        mode, level = self.from_signed_power(int(signed_power))
        self.state.ac_units.append(
            self._core.ACUnit(name=final_name, row=rr, col=cc, power_level=level, mode=mode)
        )
        self.clear_candidate(rr, cc)
        return final_name

    def remove_ac(self, name: str) -> bool:
        target = str(name)
        before = len(self.state.ac_units)
        self.state.ac_units = [ac for ac in self.state.ac_units if ac.name != target]
        return len(self.state.ac_units) != before

    def remove_ac_at(self, r: int, c: int) -> bool:
        idx = self.find_ac_index_at(int(r), int(c))
        if idx is None:
            return False
        self.state.ac_units.pop(idx)
        return True

    def set_ac_power(self, name: str, signed_power: int) -> bool:
        ac = self.find_ac_by_name(str(name))
        if ac is None:
            return False
        mode, level = self.from_signed_power(int(signed_power))
        ac.mode = mode
        ac.power_level = level
        return True

    def apply_schedule_result(self, tuned_acs: list[Any]) -> None:
        tuned_by_name = {ac.name: ac for ac in tuned_acs}
        for ac in self.state.ac_units:
            if ac.name in tuned_by_name:
                tuned = tuned_by_name[ac.name]
                ac.mode = tuned.mode
                ac.power_level = int(tuned.power_level)

    def apply_new_acs_to_state(self, state, new_acs: list[Any], *, name_prefix: str) -> None:
        existing_names = {ac.name for ac in state.ac_units}
        temp_counter = 0
        for ac in new_acs:
            applied = ac.copy()
            while applied.name in existing_names:
                temp_counter += 1
                applied.name = f"{name_prefix}_copy_{temp_counter}"
            existing_names.add(applied.name)
            state.ac_units.append(applied)

    def apply_new_acs(self, new_acs: list[Any], *, name_prefix: str = "opt") -> None:
        existing_names = {ac.name for ac in self.state.ac_units}
        for ac in new_acs:
            applied = ac.copy()
            if applied.name in existing_names:
                applied.name = self.new_unique_ac_name(name_prefix)
            existing_names.add(applied.name)
            self.state.ac_units.append(applied)

    def find_ac_by_name(self, name: str) -> Any | None:
        for ac in self.state.ac_units:
            if ac.name == name:
                return ac
        return None

    def find_ac_index_at(self, r: int, c: int) -> Optional[int]:
        for index, ac in enumerate(self.state.ac_units):
            if int(ac.row) == int(r) and int(ac.col) == int(c):
                return index
        return None

    def new_unique_ac_name(self, prefix: str) -> str:
        if prefix == "ac":
            while True:
                self._ac_counter += 1
                name = f"AC {self._ac_counter}"
                if self.find_ac_by_name(name) is None:
                    return name
        if prefix == "opt":
            while True:
                self._opt_ac_counter += 1
                name = f"Optimized AC {self._opt_ac_counter}"
                if self.find_ac_by_name(name) is None:
                    return name

        counter = 1
        while True:
            name = f"{prefix} {counter}"
            if self.find_ac_by_name(name) is None:
                return name
            counter += 1

    def from_signed_power(self, signed_power: int) -> tuple[str, int]:
        max_power = self._core.ACUnit.MAX_POWER_LEVEL
        pwr = max(-max_power, min(max_power, int(signed_power)))
        if pwr == 0:
            return (self._core.ACUnit.MODE_OFF, 0)
        if pwr < 0:
            return (self._core.ACUnit.MODE_HEAT, abs(pwr))
        return (self._core.ACUnit.MODE_COOL, pwr)

    def to_signed_power(self, ac) -> int:
        if ac.mode == self._core.ACUnit.MODE_HEAT:
            return -ac.power_level
        if ac.mode == self._core.ACUnit.MODE_COOL:
            return ac.power_level
        return 0


class StatsService:
    """Thin wrapper over the statistics component."""

    def __init__(self, *, statistics, session: SimulationSession) -> None:
        self._statistics = statistics
        self._session = session

    def compute_room_statistics(self) -> dict[str, dict[str, float]]:
        return self._statistics.compute_room_statistics(self._session.state)

    def compute_time_series_statistics(self) -> dict[str, Any]:
        states = [state for _, state in self._session.history]
        if not states:
            return {}
        return self._statistics.compute_time_series_statistics(states)

    def plot_temperature_heatmap(self):
        return self._statistics.plot_temperature_heatmap(self._session.state)

    def plot_room_comparison(self):
        return self._statistics.plot_room_comparison(self._session.state)

    def plot_time_series(self):
        states = [state for _, state in self._session.history]
        return self._statistics.plot_time_series(states)


class OptimizationService:
    """Runs optimizer workflows on copied state and applies accepted results."""

    def __init__(
        self,
        *,
        core,
        session: SimulationSession,
        optimizer,
        ac_service: ACService,
        simulator,
        scoring,
    ) -> None:
        self._core = core
        self._session = session
        self._optimizer = optimizer
        self._ac_service = ac_service
        self._simulator = simulator
        self._scoring = scoring

    def optimize_place_greedy(
        self,
        new_ac_specs: Iterable[Any],
        *,
        simulation_steps: int = 30,
        candidate_positions: Optional[Iterable[tuple[int, int]]] = None,
        apply: bool = False,
        name_prefix: str = "opt",
    ) -> tuple[list[Any], float]:
        templates = self.normalize_ac_templates(new_ac_specs)
        base_state = self._session.copy_state_snapshot(self._session.state)
        candidates = self.resolve_candidates(candidate_positions)
        placed_new = self._optimizer.optimize_greedy(
            base_state=base_state,
            new_ac_list=templates,
            candidate_position_list=candidates,
            simulation_steps=int(simulation_steps),
        )
        verify_state = self._session.copy_state_snapshot(self._session.state)
        self._ac_service.apply_new_acs_to_state(verify_state, placed_new, name_prefix=name_prefix)
        final_score = self.simulate_and_get_score(verify_state, simulation_steps)
        if apply:
            self._ac_service.apply_new_acs(placed_new, name_prefix=name_prefix)
        return placed_new, final_score

    def optimize_place_simulated_annealing(
        self,
        new_ac_specs: Iterable[Any],
        *,
        simulation_steps: int = 30,
        candidate_positions: Optional[Iterable[tuple[int, int]]] = None,
        apply: bool = False,
        name_prefix: str = "opt",
    ) -> tuple[list[Any], float]:
        templates = self.normalize_ac_templates(new_ac_specs)
        base_state = self._session.copy_state_snapshot(self._session.state)
        candidates = self.resolve_candidates(candidate_positions)
        placed_new = self._optimizer.optimize_simulated_annealing(
            base_state=base_state,
            new_ac_list=templates,
            candidate_position_list=candidates,
            simulation_steps=int(simulation_steps),
        )
        verify_state = self._session.copy_state_snapshot(self._session.state)
        self._ac_service.apply_new_acs_to_state(verify_state, placed_new, name_prefix=name_prefix)
        final_score = self.simulate_and_get_score(verify_state, simulation_steps)
        if apply:
            self._ac_service.apply_new_acs(placed_new, name_prefix=name_prefix)
        return placed_new, final_score

    def optimize_schedule_greedy_for_existing(
        self,
        *,
        simulation_steps: int = 30,
        apply: bool = False,
    ) -> tuple[list[Any], float]:
        base_state = self._session.copy_state_snapshot(self._session.state)
        tuned = self._optimizer.optimize_schedule_greedy(
            base_state=base_state,
            simulation_steps=int(simulation_steps),
        )
        verify_state = self._session.copy_state_snapshot(self._session.state)
        tuned_by_name = {ac.name: ac for ac in tuned}
        for ac in verify_state.ac_units:
            if ac.name in tuned_by_name:
                best = tuned_by_name[ac.name]
                ac.mode = best.mode
                ac.power_level = int(best.power_level)
        final_score = self.simulate_and_get_score(verify_state, simulation_steps)
        if apply:
            self._ac_service.apply_schedule_result(tuned)
        return tuned, final_score

    def apply_placement_result(self, new_acs: list[Any], *, name_prefix: str = "opt") -> None:
        self._ac_service.apply_new_acs(new_acs, name_prefix=name_prefix)

    def normalize_ac_templates(self, specs: Iterable[Any]) -> list[Any]:
        templates: list[Any] = []
        for index, item in enumerate(list(specs)):
            if isinstance(item, self._core.ACUnit):
                templates.append(item.copy())
                continue
            if isinstance(item, dict):
                templates.append(
                    self._core.ACUnit(
                        name=str(item.get("name", f"AC_new_{index}")),
                        row=0,
                        col=0,
                        power_level=int(item.get("power_level", 3)),
                        mode=str(item.get("mode", self._core.ACUnit.MODE_COOL)),
                    )
                )
                continue
            if isinstance(item, (tuple, list)) and item:
                if len(item) == 1:
                    mode, level = self._ac_service.from_signed_power(int(item[0]))
                else:
                    mode, level = str(item[0]), int(item[1])
                templates.append(
                    self._core.ACUnit(name=f"AC_new_{index}", row=0, col=0, power_level=level, mode=mode)
                )
                continue
            raise ValueError(f"Unsupported AC template spec at index {index}: {item!r}")
        return templates

    def resolve_candidates(
        self,
        candidate_positions: Optional[Iterable[tuple[int, int]]],
    ) -> list[tuple[int, int]]:
        if candidate_positions is not None:
            return [(int(r), int(c)) for (r, c) in candidate_positions]
        candidates = self._ac_service.list_candidates()
        if candidates:
            return candidates
        return [(int(r), int(c)) for (r, c) in self._session.state.floor_map.get_all_placeable_positions()]

    def simulate_and_get_score(self, state, steps: int) -> float:
        for _ in range(int(steps)):
            self._simulator.step(state)
        self._scoring.compute_total_score(state)
        return state.score[0]


class BaseEngine:
    """Facade presented to the GUI layer."""

    CORE = None

    def __init__(
        self,
        *,
        floor_map,
        outdoor_temp: float = 26.0,
        setpoint_temp: float = 26.0,
        initial_indoor_temp: float = 22.0,
        history_length: int = 1440,
        simulator=None,
        scoring=None,
        statistics=None,
        optimizer=None,
    ) -> None:
        core = self.CORE
        if core is None:
            raise RuntimeError("BaseEngine requires a concrete CORE module.")

        self._sim = simulator if simulator is not None else core.Simulator()
        self._scoring = scoring if scoring is not None else core.Scoring()
        self._stats = statistics if statistics is not None else core.Statistics()
        self._optimizer = optimizer if optimizer is not None else core.Optimizer(simulator=self._sim, scoring=self._scoring)

        self._session = SimulationSession(
            core=core,
            scoring=self._scoring,
            floor_map=floor_map,
            outdoor_temp=outdoor_temp,
            setpoint_temp=setpoint_temp,
            initial_indoor_temp=initial_indoor_temp,
            history_length=history_length,
        )
        self._ac_service = ACService(core=core, session=self._session)
        self._stats_service = StatsService(statistics=self._stats, session=self._session)
        self._optimization_service = OptimizationService(
            core=core,
            session=self._session,
            optimizer=self._optimizer,
            ac_service=self._ac_service,
            simulator=self._sim,
            scoring=self._scoring,
        )

    @property
    def _state(self):
        return self._session.state

    def get_time(self) -> int:
        return int(self._session.time)

    def get_state(self):
        return self._session.state

    def get_outdoor_temp(self) -> float:
        return float(self._session.state.outdoor_temp)

    def get_setpoint_temp(self) -> float:
        return float(self._session.state.setpoint_temp)

    def get_temperature_field(self) -> np.ndarray:
        return self._session.state.temperature_field

    def get_temperature_copy(self) -> np.ndarray:
        return self._session.state.temperature_field.copy()

    def get_energy_dict(self) -> dict[str, float]:
        return dict(self._session.state.energy_dict)

    def get_score_tuple(self) -> tuple[float, float, float, float]:
        return tuple(self._session.state.score)

    def get_room_weights(self) -> dict[str, float]:
        return dict(self._session.state.room_weights)

    def list_acs(self) -> list[dict[str, Any]]:
        return self._ac_service.list_acs()

    def list_candidates(self) -> list[tuple[int, int]]:
        return self._ac_service.list_candidates()

    def get_history(self) -> list[tuple[int, Any]]:
        return list(self._session.history)

    def get_history_states(self) -> list[Any]:
        return [state for _, state in self._session.history]

    def set_history_length(self, history_length: int) -> None:
        self._session.set_history_length(history_length)

    def step(self, minutes: int = 1) -> None:
        if int(minutes) <= 0:
            return
        self._session.step(self._sim, int(minutes))

    def recompute_score(self) -> None:
        self._session.recompute_score()
        self._session.write_history_current()

    def set_outdoor_temp(self, value: float) -> None:
        self._session.state.outdoor_temp = float(value)
        self.recompute_score()

    def set_setpoint_temp(self, value: float) -> None:
        self._session.state.setpoint_temp = float(value)
        self.recompute_score()

    def set_cell_temp(self, r: int, c: int, value: float) -> None:
        self._session.state.temperature_field[int(r), int(c)] = float(value)
        self.recompute_score()

    def set_room_weight(self, room_type: str, weight: float) -> None:
        self._session.state.room_weights[str(room_type)] = float(weight)
        self.recompute_score()

    def toggle_door(self, r: int, c: int) -> bool:
        ok = bool(self._session.state.floor_map.toggle_door(int(r), int(c)))
        if ok:
            self.recompute_score()
        return ok

    def toggle_candidate(self, r: int, c: int) -> bool:
        return self._ac_service.toggle_candidate(r, c)

    def clear_candidate(self, r: int, c: int) -> None:
        self._ac_service.clear_candidate(r, c)

    def clear_all_candidates(self) -> None:
        self._ac_service.clear_all_candidates()

    def place_ac(self, r: int, c: int, *, name: Optional[str] = None, signed_power: int = 0) -> str:
        result = self._ac_service.place_ac(r, c, name=name, signed_power=signed_power)
        self.recompute_score()
        return result

    def remove_ac(self, name: str) -> bool:
        removed = self._ac_service.remove_ac(name)
        if removed:
            self.recompute_score()
        return removed

    def remove_ac_at(self, r: int, c: int) -> bool:
        removed = self._ac_service.remove_ac_at(r, c)
        if removed:
            self.recompute_score()
        return removed

    def set_ac_power(self, name: str, signed_power: int) -> bool:
        updated = self._ac_service.set_ac_power(name, signed_power)
        if updated:
            self.recompute_score()
        return updated

    def compute_room_statistics(self) -> dict[str, dict[str, float]]:
        return self._stats_service.compute_room_statistics()

    def compute_time_series_statistics(self) -> dict[str, Any]:
        return self._stats_service.compute_time_series_statistics()

    def plot_temperature_heatmap(self):
        return self._stats_service.plot_temperature_heatmap()

    def plot_room_comparison(self):
        return self._stats_service.plot_room_comparison()

    def plot_time_series(self):
        return self._stats_service.plot_time_series()

    def optimize_place_greedy(
        self,
        new_ac_specs: Iterable[Any],
        *,
        simulation_steps: int = 30,
        candidate_positions: Optional[Iterable[tuple[int, int]]] = None,
        apply: bool = False,
        name_prefix: str = "opt",
    ) -> tuple[list[Any], float]:
        placed, final_score = self._optimization_service.optimize_place_greedy(
            new_ac_specs,
            simulation_steps=simulation_steps,
            candidate_positions=candidate_positions,
            apply=apply,
            name_prefix=name_prefix,
        )
        if apply:
            self.recompute_score()
        return placed, final_score

    def optimize_place_simulated_annealing(
        self,
        new_ac_specs: Iterable[Any],
        *,
        simulation_steps: int = 30,
        candidate_positions: Optional[Iterable[tuple[int, int]]] = None,
        apply: bool = False,
        name_prefix: str = "opt",
    ) -> tuple[list[Any], float]:
        placed, final_score = self._optimization_service.optimize_place_simulated_annealing(
            new_ac_specs,
            simulation_steps=simulation_steps,
            candidate_positions=candidate_positions,
            apply=apply,
            name_prefix=name_prefix,
        )
        if apply:
            self.recompute_score()
        return placed, final_score

    def optimize_schedule_greedy_for_existing(
        self,
        *,
        simulation_steps: int = 30,
        apply: bool = False,
    ) -> tuple[list[Any], float]:
        tuned, final_score = self._optimization_service.optimize_schedule_greedy_for_existing(
            simulation_steps=simulation_steps,
            apply=apply,
        )
        if apply:
            self.recompute_score()
        return tuned, final_score

    def apply_placement_result(self, new_acs: list[Any], name_prefix: str = "opt") -> None:
        self._optimization_service.apply_placement_result(new_acs, name_prefix=name_prefix)
        self.recompute_score()

    def apply_schedule_result(self, tuned_acs: list[Any]) -> None:
        self._ac_service.apply_schedule_result(tuned_acs)
        self.recompute_score()
