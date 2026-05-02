"""main_cli

Interactive command-line interface for PA2 thermal simulation.

Reads map.txt from the workspace root directory and provides a menu-driven
interface exposing all public operations from:
  - core.simulation   (Simulator.step)
  - core.scoring      (Scoring.compute_*)
  - core.optimization (Optimizer.optimize_*)
  - core.statistics   (Statistics.compute_* / Statistics.plot_*)
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt

from encrypted_solution.core import (
    ACUnit, FloorMap, State,
    Simulator, Scoring, Optimizer, Statistics,
)


# ─────────────────────────────────────────────────────────────────────────────
# Generic input helpers
# ─────────────────────────────────────────────────────────────────────────────

def _prompt(msg: str, default=None) -> str:
    """Show prompt with optional default and return stripped input."""
    suffix = f" [{default}]" if default is not None else ""
    raw = input(f"  {msg}{suffix}: ").strip()
    return raw if raw else (str(default) if default is not None else "")


def _prompt_float(msg: str, default: float) -> float:
    while True:
        raw = _prompt(msg, default)
        try:
            return float(raw)
        except ValueError:
            print(f"    Invalid number '{raw}'. Please try again.")


def _prompt_int(msg: str, default: int) -> int:
    while True:
        raw = _prompt(msg, default)
        try:
            return int(raw)
        except ValueError:
            print(f"    Invalid integer '{raw}'. Please try again.")


def _prompt_room_weights() -> dict[str, float]:
    """
    Collect room weights interactively.
    Accepts:  A:2.0, B:1.5, C:1.0
    Empty input → all rooms default to 1.0 (handled by State constructor).
    """
    while True:
        print('  Input format for room weights: "Room1:Weight1,Room2:Weight2" (no spaces, letters A-Z as keys).')
        raw = input(
            "  Room weights (e.g. A:2.0,B:1.5)  [leave blank → default 1.0 for all]: "
        ).strip()
        if not raw:
            return {}
        try:
            weights: dict[str, float] = {}
            for token in raw.split(","):
                k, v = token.strip().split(":")
                k = k.strip().upper()
                if len(k) != 1 or not k.isalpha():
                    raise ValueError(f"Invalid room key '{k}' (must be a single letter A–Z)")
                weights[k] = float(v.strip())
            return weights
        except Exception as exc:
            print(f"    Parse error: {exc}. Try again.")


def _hr():
    print("─" * 62)


# ─────────────────────────────────────────────────────────────────────────────
# AC management helpers
# ─────────────────────────────────────────────────────────────────────────────

_MODE_MAP   = {"1": ACUnit.MODE_COOL, "2": ACUnit.MODE_HEAT, "3": ACUnit.MODE_OFF}
_MODE_LABEL = {ACUnit.MODE_COOL: "1", ACUnit.MODE_HEAT: "2", ACUnit.MODE_OFF: "3"}


def _get_door_positions(floor_map) -> np.ndarray:
    """Return door coordinates from the authoritative door mask."""
    return np.argwhere(floor_map.doors)


def _is_door_open(floor_map, r: int, c: int) -> bool:
    """Return the current open state for a door cell."""
    return bool(floor_map.is_door_open(r, c))


def _list_acs(state: State) -> None:
    if not state.ac_units:
        print("    (no AC units)")
        return
    for i, ac in enumerate(state.ac_units):
        print(f"    [{i}] {ac}")


def _add_ac(state: State) -> None:
    placeable = state.floor_map.get_all_placeable_positions()
    if not placeable:
        print("    No placeable positions on this map.")
        return
    print(f"    Showing first 20 of {len(placeable)} placeable (row, col) positions:")
    for pos in placeable[:20]:
        print(f"      {tuple(pos)}")
    name  = _prompt("AC name", f"ac{len(state.ac_units)}")
    row   = _prompt_int("Row",        int(placeable[0][0]))
    col   = _prompt_int("Column",     int(placeable[0][1]))
    power = _prompt_int("Power level (0–5)", 3)
    print("    Mode → 1: Cool   2: Heat   3: Off")
    mode  = _MODE_MAP.get(_prompt("Mode", "1"), ACUnit.MODE_COOL)
    if not state.floor_map.can_place_ac(row, col):
        print(f"    ({row},{col}) is not a valid floor cell. AC was not added.")
        return
    ac = ACUnit(name, row, col, power, mode)
    state.ac_units.append(ac)
    print(f"    Added: {ac}")


def _remove_ac(state: State) -> None:
    _list_acs(state)
    if not state.ac_units:
        return
    idx = _prompt_int("Remove by index", 0)
    if 0 <= idx < len(state.ac_units):
        print(f"    Removed: {state.ac_units.pop(idx)}")
    else:
        print("    Index out of range.")


def _modify_ac(state: State) -> None:
    _list_acs(state)
    if not state.ac_units:
        return
    idx = _prompt_int("Modify by index", 0)
    if not (0 <= idx < len(state.ac_units)):
        print("    Index out of range.")
        return
    ac = state.ac_units[idx]
    print(f"    Current: {ac}")
    ac.power_level = _prompt_int("New power level (0–5)", ac.power_level)
    print("    Mode → 1: Cool   2: Heat   3: Off")
    ac.mode = _MODE_MAP.get(_prompt("New mode", _MODE_LABEL.get(ac.mode, "1")), ac.mode)
    print(f"    Updated: {ac}")


def _toggle_door(state: State) -> None:
    door_positions = _get_door_positions(state.floor_map)
    if len(door_positions) == 0:
        print("    No doors on this map.")
        return
    print("    Door positions (row, col)  →  current state:")
    for pos in door_positions:
        r, c   = int(pos[0]), int(pos[1])
        is_open = _is_door_open(state.floor_map, r, c)
        print(f"      ({r},{c}) {'open' if is_open else 'closed'}")
    row = _prompt_int("Door row",    int(door_positions[0][0]))
    col = _prompt_int("Door column", int(door_positions[0][1]))
    if not state.floor_map.toggle_door(row, col):
        print(f"    ({row},{col}) is not a door cell.")
    else:
        new_state = _is_door_open(state.floor_map, row, col)
        print(f"    Door ({row},{col}) is now {'open' if new_state else 'closed'}.")


# ─────────────────────────────────────────────────────────────────────────────
# Sub-menus
# ─────────────────────────────────────────────────────────────────────────────

def menu_ac(state: State) -> None:
    while True:
        _hr()
        print("  AC Management")
        print("    1  List AC units")
        print("    2  Add AC unit")
        print("    3  Remove AC unit")
        print("    4  Modify AC unit (mode / power)")
        print("    5  Toggle door open/closed")
        print("    0  Back")
        choice = _prompt("Choice", "0")
        if   choice == "1": _list_acs(state)
        elif choice == "2": _add_ac(state)
        elif choice == "3": _remove_ac(state)
        elif choice == "4": _modify_ac(state)
        elif choice == "5": _toggle_door(state)
        elif choice == "0": break


def menu_simulation(
    state: State,
    history: list[State],
    simulator: Simulator,
    scoring: Scoring,
) -> None:
    while True:
        _hr()
        print("  Simulation")
        print("    1  Step N minutes  (advances state, records history)")
        print("    2  Print temperature field")
        print("    3  Print full state summary")
        print("    0  Back")
        choice = _prompt("Choice", "0")

        if choice == "1":
            n = _prompt_int("Number of minutes", 1)
            for _ in range(n):
                simulator.step(state)
                scoring.compute_total_score(state)
                history.append(state.copy())
            print(f"    Advanced {n} minute(s). History now has {len(history)} snapshot(s).")
            print(
                f"    Score → total={state.score[0]:.4f}  comfort={state.score[1]:.4f}"
                f"  uniformity={state.score[2]:.4f}  energy={state.score[3]:.4f}"
            )

        elif choice == "2":
            print("    temperature_field (°C):")
            print(state.temperature_field)

        elif choice == "3":
            print(f"    outdoor_temp  = {state.outdoor_temp}")
            print(f"    setpoint_temp = {state.setpoint_temp}")
            print(f"    room_weights  = {state.room_weights}")
            print(f"    score         = {state.score}")
            print(f"    energy_dict   = {state.energy_dict}")
            print("    AC units:")
            _list_acs(state)

        elif choice == "0":
            break


def menu_scoring(state: State, scoring: Scoring) -> None:
    while True:
        _hr()
        print("  Scoring")
        print("    1  Compute comfort score")
        print("    2  Compute uniformity score")
        print("    3  Compute energy score")
        print("    4  Compute total score  (updates state.score)")
        print("    0  Back")
        choice = _prompt("Choice", "0")

        if choice == "1":
            s = scoring.compute_comfort_score(
                state.floor_map, state.room_weights,
                state.setpoint_temp, state.temperature_field,
            )
            print(f"    Comfort score:    {s:.4f}")

        elif choice == "2":
            s = scoring.compute_uniformity_score(
                state.floor_map, state.room_weights, state.temperature_field,
            )
            print(f"    Uniformity score: {s:.4f}")

        elif choice == "3":
            s = scoring.compute_energy_score(state.energy_dict)
            print(f"    Energy score:     {s:.4f}")

        elif choice == "4":
            scoring.compute_total_score(state)
            print(f"    Total score:      {state.score[0]:.4f}")
            print(f"    Comfort score:    {state.score[1]:.4f}")
            print(f"    Uniformity score: {state.score[2]:.4f}")
            print(f"    Energy score:     {state.score[3]:.4f}")

        elif choice == "0":
            break


def menu_optimization(
    state: State,
    history: list[State],
    optimizer: Optimizer,
    simulator: Simulator,
    scoring: Scoring,
) -> None:
    while True:
        _hr()
        print("  Optimization")
        print("    1  Greedy placement       (optimize_greedy)")
        print("    2  Greedy schedule tuning (optimize_schedule_greedy)")
        print("    3  Simulated annealing placement (optimize_simulated_annealing)")
        print("    0  Back")
        choice = _prompt("Choice", "0")

        if choice in ("1", "3"):
            placeable = state.floor_map.get_all_placeable_positions()
            print(f"    {len(placeable)} placeable positions available.")
            if not placeable:
                print("    Cannot optimize placement: no placeable positions.")
                continue
            ac_count       = _prompt_int("Number of new ACs to place", 3)
            max_candidates = len(placeable)
            candidate_count = _prompt_int(
                f"Candidate positions to sample (max {max_candidates})",
                min(15, max_candidates),
            )
            candidate_count = min(candidate_count, max_candidates)
            sim_steps = _prompt_int("Simulation steps per evaluation", 10)
            rng_seed  = _prompt_int("Random seed", 42)

            rng = np.random.default_rng(rng_seed)
            idxs       = rng.choice(len(placeable), size=candidate_count, replace=False)
            candidates = [placeable[i] for i in idxs]

            prefix = "ac_greedy" if choice == "1" else "ac_sa"
            new_acs = [
                ACUnit(f"{prefix}{i}", -1, -1, 3, ACUnit.MODE_COOL)
                for i in range(ac_count)
            ]

            if choice == "1":
                placed = optimizer.optimize_greedy(state, new_acs, candidates, sim_steps)
            else:
                placed = optimizer.optimize_simulated_annealing(
                    state, new_acs, candidates, sim_steps
                )

            state.ac_units = state.ac_units + placed
            label = "greedy" if choice == "1" else "simulated annealing"
            print(f"    Placed {len(placed)} AC(s) via {label}:")
            for ac in placed:
                print(f"      {ac}")

        elif choice == "2":
            if not state.ac_units:
                print("    No AC units to tune. Add ACs first.")
                continue
            sim_steps = _prompt_int("Simulation steps per evaluation", 10)
            updated = optimizer.optimize_schedule_greedy(state, sim_steps)
            state.ac_units = updated
            print(f"    Tuned {len(updated)} AC schedule(s):")
            for ac in updated:
                print(f"      {ac}")

        elif choice == "0":
            break


def menu_statistics(
    state: State,
    history: list[State],
    statistics: Statistics,
) -> None:
    while True:
        _hr()
        print(f"  Statistics  (history: {len(history)} snapshot(s))")
        print("    1  Room statistics — current state")
        print("    2  Time-series statistics — full history")
        print("    3  Plot temperature heatmap — current state")
        print("    4  Plot time-series dashboard — full history")
        print("    5  Plot room comparison — current state")
        print("    0  Back")
        choice = _prompt("Choice", "0")

        if choice == "1":
            stats = statistics.compute_room_statistics(state)
            if not stats:
                print("    No room data available.")
            for room, s in sorted(stats.items()):
                print(
                    f"    Room {room}:  mean={s['mean']:.2f}  std={s['std']:.2f}"
                    f"  min={s['min']:.2f}  max={s['max']:.2f}"
                    f"  median={s['median']:.2f}  range={s['range']:.2f}"
                    f"  count={s['count']}"
                )

        elif choice == "2":
            if not history:
                print("    No history yet — run some simulation steps first.")
                continue
            ts = statistics.compute_time_series_statistics(history)
            print("    ── Score statistics ──")
            for key in (
                "total_score_mean", "total_score_std",
                "comfort_score_mean", "comfort_score_std",
                "uniformity_score_mean", "uniformity_score_std",
                "energy_score_mean", "energy_score_std",
            ):
                val = ts.get(key)
                print(f"      {key}: {val:.4f}" if isinstance(val, float) else f"      {key}: N/A")
            print("    ── Mean temperature by room ──")
            for room, val in sorted(ts.get("mean_temp_mean", {}).items()):
                std = ts.get("mean_temp_std", {}).get(room, 0.0)
                print(f"      Room {room}: mean={val:.2f}  std={std:.2f}")
            print("    ── Energy by AC ──")
            for ac_name, total in sorted(ts.get("energy_total", {}).items()):
                mean = ts.get("energy_mean", {}).get(ac_name, 0.0)
                std  = ts.get("energy_std",  {}).get(ac_name, 0.0)
                print(f"      {ac_name}: total={total:.2f}  mean/step={mean:.2f}  std={std:.2f}")

        elif choice == "3":
            fig = statistics.plot_temperature_heatmap(state)
            if fig:
                plt.show()

        elif choice == "4":
            if not history:
                print("    No history yet — run some simulation steps first.")
                continue
            fig = statistics.plot_time_series(history)
            if fig:
                plt.show()

        elif choice == "5":
            fig = statistics.plot_room_comparison(state)
            if fig:
                plt.show()

        elif choice == "0":
            break


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def _load_floor_map(map_path: str) -> FloorMap:
    with open(map_path, encoding="utf-8") as f:
        map_text = f.read()
    return FloorMap(map_text)


def main() -> None:
    map_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "map.txt")

    if not os.path.exists(map_path):
        print(f"Error: map.txt not found at {map_path}")
        sys.exit(1)

    try:
        floor_map = _load_floor_map(map_path)
    except Exception as exc:
        print(f"Error parsing map.txt: {exc}")
        sys.exit(1)

    room_chars = sorted(set(floor_map.room_types.flatten()) - {"x"})

    print("=" * 62)
    print("  PA2 — Interactive CLI")
    print(f"  Map: {floor_map.height} rows × {floor_map.width} cols   "
          f"Room types: {room_chars}")
    print(f"  Value inside [] will be used if you just press Enter without typing anything.")
    print("=" * 62)

    # Initial environment setup
    print("\nEnvironment setup:")
    outdoor_temp  = _prompt_float("Outdoor temperature (°C)",  30.0)
    setpoint_temp = _prompt_float("Setpoint temperature (°C)", 26.0)
    room_weights  = _prompt_room_weights()

    state = State(
        floor_map=floor_map,
        outdoor_temp=outdoor_temp,
        setpoint_temp=setpoint_temp,
        room_weights=room_weights,
    )
    simulator  = Simulator()
    scoring    = Scoring()
    optimizer  = Optimizer(simulator, scoring)
    statistics = Statistics()
    history: list[State] = []

    # Main loop
    while True:
        _hr()
        print(
            f"  Main menu   AC(s): {len(state.ac_units)}"
            f"   History: {len(history)} snapshot(s)"
        )
        if history:
            print(
                f"  Last score → total={state.score[0]:.4f}"
                f"  comfort={state.score[1]:.4f}"
                f"  uniformity={state.score[2]:.4f}"
                f"  energy={state.score[3]:.4f}"
            )
        print()
        print("    1  AC Management")
        print("    2  Simulation")
        print("    3  Scoring")
        print("    4  Optimization")
        print("    5  Statistics")
        print("    6  Clear simulation history")
        print("    7  Reset state  (reload map.txt + re-enter parameters)")
        print("    0  Exit")
        choice = _prompt("Choice", "0")

        if   choice == "1": menu_ac(state)
        elif choice == "2": menu_simulation(state, history, simulator, scoring)
        elif choice == "3": menu_scoring(state, scoring)
        elif choice == "4": menu_optimization(state, history, optimizer, simulator, scoring)
        elif choice == "5": menu_statistics(state, history, statistics)

        elif choice == "6":
            history.clear()
            print("  History cleared.")

        elif choice == "7":
            try:
                floor_map = _load_floor_map(map_path)
                room_chars = sorted(set(floor_map.room_types.flatten()) - {"x"})
                print(f"\n  Map reloaded — room types: {room_chars}")
                print("  Re-enter environment parameters:")
                outdoor_temp  = _prompt_float("Outdoor temperature (°C)",  outdoor_temp)
                setpoint_temp = _prompt_float("Setpoint temperature (°C)", setpoint_temp)
                room_weights  = _prompt_room_weights()
                state = State(
                    floor_map=floor_map,
                    outdoor_temp=outdoor_temp,
                    setpoint_temp=setpoint_temp,
                    room_weights=room_weights,
                )
                history.clear()
                print("  State reset.")
            except Exception as exc:
                print(f"  Error: {exc}")

        elif choice == "0":
            print("  Goodbye.")
            break


if __name__ == "__main__":
    main()
