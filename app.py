"""app

Application-level integration and testing functions.

This module provides high-level functions that integrate all core components
(FloorMap, State, Simulator, Scoring, Optimizer, Statistics) to:
- initialize test states from map specifications
- run optimization workflows
- demonstrate end-to-end system usage
"""

from core import *
import matplotlib.pyplot as plt
import numpy as np
import time


def init_test_state(
    map_text: str,
    outdoor_temp: float,
    setpoint_temp: float,
    room_weights: dict[str, float],
) -> State:
    """
    Task 8.1 (Optional Task)

    Optional task: complete this optional practice task if you want more end-to-end experience.

    Initialize a simulation State from raw map text and environment parameters.

    Wraps FloorMap construction and State initialization into a single call
    for use in tests and top-level workflows.

    The returned State has:
    - temperature_field initialized uniformly to outdoor_temp (boundary condition).
    - ac_units empty — no ACs placed yet.
    - energy_dict and score left at their defaults.

    Args:
        map_text: Multi-line string encoding the floor layout (see FloorMap).
        outdoor_temp: Outdoor boundary temperature (°C); also the initial
            temperature of every cell in the field.
        setpoint_temp: Target comfort temperature (°C) used by Scoring.
        room_weights: Mapping from room-type letter ('A'..'Z') to scoring weight.

    Returns:
        Fully constructed State ready for simulation or optimization.
    """
    pass


def optimization_test(
    base_state: State,
    simulation_steps: int,
    test_steps: int,
    candidate_count: int,
    ac_count: int,
    random_seed: int = 42,
):
    """
    Task 8.2 (Optional Task)

    Optional task: complete this optional practice workflow if you want more end-to-end experience.

    Run a complete two-phase optimization workflow and return the simulation history.

    Phase 1 — Placement:
        - Randomly sample `candidate_count` positions from all placeable floor cells
          (which has been done for you), then use `Optimizer.optimize_greedy` to assign
          the `ac_count` new AC units to the best subset of those candidate positions.
        - The AC units should be set with the cooling mode and power level 3.
        - For the distributed optional tests, any existing fixed-AC positions are
          guaranteed not to appear in the sampled candidate positions.

    Phase 2 — Repeated schedule tuning (runs `test_steps` times):
        a. Call `Optimizer.optimize_schedule_greedy` to tune AC mode/power for the
           current state.
        b. Simulate forward for `simulation_steps` minutes with `Simulator.step`.
        c. After each minute, call `Scoring.compute_total_score` and append a
           deep copy of the state to the history.

    State history contract:
        - Each element is a *deep copy* of the state at the end of that simulation
          minute (after `simulator.step` and `scoring.compute_total_score`).
        - Elements are chronologically ordered: index 0 -> state at end of minute 1,
          index k -> state at end of minute k+1.
        - `len(state_history) == test_steps * simulation_steps`.

    Args:
        base_state: Starting state; not modified (a copy is used internally).
        simulation_steps: Minutes simulated per optimization-simulation cycle.
        test_steps: Number of optimize-then-simulate cycles to run.
        candidate_count: Number of candidate AC positions sampled at random.
        ac_count: Number of new AC units to place during Phase 1.
            No more than 20 new AC units should be used.
        random_seed: NumPy RNG seed for reproducible candidate sampling (default 42).

    Returns:
        List of State deep-copies representing the full simulation history.
        Length equals `test_steps * simulation_steps`.
    """
    ac_count = max(0, min(int(ac_count), 20))

    np.random.seed(random_seed)
    placeable_positions = base_state.floor_map.get_all_placeable_positions()
    candidate_indexes = np.random.choice(
        np.arange(len(placeable_positions)),
        size=candidate_count,
        replace=False,
    )
    candidate_positions = [placeable_positions[i] for i in candidate_indexes]

    simulator = Simulator()
    scoring = Scoring()
    optimizer = Optimizer(simulator, scoring)

    state = base_state.copy()
    state_history = []

    # Important: Do not regenerate the candidate positions again.

    ####### Please modify in the area below #######
    pass
    ####### Please modify in the area above #######

    return state_history


def optimize_given():
    """
    Task 8.3 (Optional Task)

    Optional task: complete this optional practice workflow if you want more end-to-end experience.

    End-to-end optimization on a fixed building map and environment.

    Fixed parameters (do not modify):
        map_text — 5-room building layout (A–E)
        outdoor_temp = 30.0
        setpoint_temp = 26.0
        room_weights = {'A': 2.0, 'B': 1.5, 'C': 1.0, 'D': 1.0, 'E': 1.3}

    Goal:
        Return a 120-element State history that performs well across multiple
        scoring windows near the end of the simulation.

        There are totally 5 testcases:
            1. achieve >80.0 total score in minutes 115-120
            2. achieve >85.0 total score in minutes 110-120
            3. achieve >90.0 total score in minutes 100-120
            4. achieve >95.0 total score in minutes 80-120
            5. achieve >97.0 total score in minutes 60-120
        
        Passing each testcase would grant you 1/5 of the total score for this task.

    What you may tune:
        - AC count, positions, and parameters in every minute
        - At most 20 AC units may be present in any returned state

    What you must NOT change:
        - map_text, outdoor_temp, setpoint_temp, room_weights
        - the init_test_state call and its arguments

    You may reuse the `optimization_test` function or implement your own workflow.

    State history integrity contract:
        - Each element must be a deep copy of the simulation state at the end of
          that minute, produced by calling `simulator.step` then
          `scoring.compute_total_score` in order.
        - Elements must be chronologically ordered: index 0 = end of minute 1,
          index k = end of minute k+1.
        - `len(state_history)` must equal exactly 120.

    The grader replays your returned history using only its AC settings, so
    fabricated temperature/energy/score values will fail integrity checks.

    Returns:
        List of 120 State deep-copies representing the full simulation history.
    """
    map_text = """
    ##################
    #.......#........#
    #...B...*.C.###*##
    #.......#...#..D.#
    ####*#############
    #....A...*.......#
    #........#....E..#
    @@@@@@@*@@@@@@@@@@
    """

    room_weights = {
        "A": 2.0,
        "B": 1.5,
        "C": 1.0,
        "D": 1.0,
        "E": 1.3,
    }

    init_state = init_test_state(
        map_text,
        outdoor_temp=30.0,
        setpoint_temp=26.0,
        room_weights=room_weights,
    )

    state_history = []

    # TODO: Implement your optimization strategy below.
    # Aim to keep the later part of the 120-minute history consistently strong
    # across multiple checkpoint windows, while never using more than 20 ACs.

    ####### Please modify in the area below #######
    pass
    ####### Please modify in the area above #######

    if len(state_history) != 120:
        raise ValueError(f"Expected exactly 120 minutes of simulation history, got {len(state_history)}")
    if any(not isinstance(state, State) for state in state_history):
        raise TypeError("optimize_given() must return a list of State objects.")
    if any(len(state.ac_units) > 20 for state in state_history):
        raise ValueError("Each returned State must contain at most 20 AC units.")

    return state_history


if __name__ == "__main__":
    print("Running Task 8.3 optimization...")

    start_time = time.time()
    state_history = optimize_given()
    end_time = time.time()

    print(f"Completed in {end_time - start_time:.2f} seconds.")

    statistics = Statistics()
    statistics.plot_time_series(state_history)
    plt.show()
