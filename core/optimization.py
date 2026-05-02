"""core.optimization

Placement and schedule optimizers for AC units.

This module explores candidate AC placements and mode/power schedules to
maximize the scoring function.
"""

import numpy as np

from .state.state import State
from .state.ac import ACUnit
from .simulation import Simulator
from .scoring import Scoring

class Optimizer:
    """
    Unified optimizer with a fixed Simulator and Scoring.

    Conventions:
      - base_state.ac_units: already-placed (fixed-position) AC units
      - new_ac_list: AC templates to be placed (their .row/.col will be ignored for placement)
      - candidate_position_list: iterable of (r, c) candidate cells
      - All optimize_* methods return ONLY the newly-added AC units (not including base_state.ac_units)
    """

    def __init__(
        self,
        simulator: Simulator,
        scoring: Scoring,
        random_seed: int = 42,
        initial_temperature: float = 1000.0,
        cooling_rate: float = 0.95,
        max_iterations: int = 500,
    ) -> None:
        """Create an optimizer.

        Args:
            Needed for your tasks:
                simulator: Object with `step(state)`.
                scoring: Object with `compute_total_score(state)`.

            Not needed for your tasks (provided for SA):
                random_seed: RNG seed for simulated annealing.
                initial_temperature: Starting temperature for annealing.
                cooling_rate: Cooling rate per iteration for annealing.
                max_iterations: Maximum annealing iterations.
        """
        self.simulator = simulator
        self.scoring = scoring

        # SA params
        self.random_seed = int(random_seed)
        self.initial_temperature = float(initial_temperature)
        self.cooling_rate = float(cooling_rate)
        self.max_iterations = int(max_iterations)

    def _evaluate(self, base_state: State, ac_units: list[ACUnit], simulation_steps: int) -> float:
        """
        Task 7.1 (Optional Task).

        Optional task: complete this optional practice helper if you want more optimization experience.

        Evaluate the total score obtained by running a simulation from a copy of base_state
        with `ac_units` appended to the existing fixed AC units.

        Conceptual algorithm:
            - Combine base_state.ac_units (fixed) with ac_units (new) as the full
              AC list for the state, then run simulator.step for simulation_steps minutes.
            - Call scoring.compute_total_score(state) to populate state.score,
              then return state.score[0] (the total score).

        Implementation Hints:
            - Do NOT modify base_state directly; work on a deep copy so subsequent
              calls are not affected. Both the state object and AC unit lists should
              be copied (e.g., state.copy() and ac.copy() for each ACUnit).

        Args:
            base_state: Baseline state containing already-placed fixed AC units.
            ac_units: Newly added AC units to evaluate (on top of base_state.ac_units).
            simulation_steps: Number of minutes to simulate.

        Returns:
            Total score (float) after the simulation.
        """
        pass

    def optimize_greedy(
        self,
        base_state: State,
        new_ac_list: list[ACUnit],
        candidate_position_list: list[tuple[int, int]],
        simulation_steps: int = 30,
    ) -> list[ACUnit]:
        """
        Task 7.2 (Optional Task).

        Optional task: complete this optional practice optimizer if you want more optimization experience.

        Greedily place each new AC unit one at a time, choosing the candidate
        position that maximises the score when evaluating the prefix of placed ACs so far.

        Conceptual algorithm:
            deep copy `ac_units` to a new list `new_ac_list` (to avoid mutating input ACUnit objects)
            For each AC i in new_ac_list (in order):
                1. Try every unoccupied candidate position for AC i.
                2. Evaluate using the prefix new_ac_list[0:i] + [AC_i at the candidate position] 
                   (also with base_state.ac_units)
                   (ACs after index i are not yet placed and should be excluded).
                3. Lock AC i at the best-scoring position; mark it as occupied.

        This is a locally greedy decision — it does not guarantee globally optimal placement.

        Assumption for the distributed optional tests:
            existing fixed-AC positions in `base_state.ac_units` will not appear
            inside `candidate_position_list`.

        Example:
            new_ac_list = [AC_a, AC_b]  (two ACs to place)
            candidate_position_list = [(0,0), (0,1), (1,0)]

            i=0: try place AC_a (0,0), (0,1), (1,0) with prefix [] -> best is (0,1), score=72
                 lock AC_a at (0,1)
            i=1: try place AC_b (0,0), (1,0) (skip occupied (0,1)) with prefix [AC_a@(0,1)] -> best is (1,0)
                 lock AC_b at (1,0)

            -> return [AC_a@(0,1), AC_b@(1,0)]

        Args:
            base_state: Baseline state with fixed ACs already in base_state.ac_units.
            new_ac_list: AC templates to place; their .row/.col are overwritten.
            candidate_position_list: Valid (r, c) cells where new ACs may be placed.
            simulation_steps: Minutes to simulate for each evaluation.

        Returns:
            List of newly placed ACUnit instances (same length as new_ac_list).
        """
        pass

    def optimize_schedule_greedy(
        self,
        base_state: State,
        simulation_steps: int = 30,
    ) -> list[ACUnit]:
        """
        Task 7.3 (Optional Task).

        Optional task: complete this optional practice optimizer if you want more optimization experience.

        Greedily tune the mode and power level of each AC unit already placed in
        base_state, one unit at a time, using the same prefix-evaluation strategy
        as optimize_greedy.

        Conceptual algorithm:
            Let tuned_acs = deep copy of base_state.ac_units
            For each AC i in tuned_acs (in order):
                1. Try every (mode, power_level) combination:
                       mode         ∈ {MODE_HEAT, MODE_COOL, MODE_OFF}
                       power_level  ∈ {1, 2, 3, 4, 5}  (power_level = 0 when MODE_OFF)
                2. Evaluate using only the prefix tuned_acs[0:i] + [AC_i with candidate (mode, power_level)] 
                   (also with base_state.ac_units)
                   (ACs after index i are not yet tuned and should be excluded).
                3. Lock AC i at the best-scoring (mode, power_level).

        This is a locally greedy decision — it does not guarantee globally optimal schedules.

        Implementation Hints:
            - Do NOT modify the AC units in base_state directly; work on copies so that
              the original state is not affected between evaluations.

        Example:
            base_state.ac_units = [AC1, AC2]  (positions already fixed)

            i=0: try AC1 with (MODE_HEAT,1), (MODE_HEAT,2), ..., (MODE_COOL,5), (MODE_OFF,0)
                      with prefix [] only
                 best is (MODE_HEAT, 3), score=65
                 lock AC1 at MODE_HEAT, power_level=3
            i=1: try all (mode, power_level) combinations for AC2
                      with prefix [AC1(HEAT,3)]
                 best is (MODE_COOL, 2), score=71
                 lock AC2 at MODE_COOL, power_level=2

            -> return [AC1(HEAT,3), AC2(COOL,2)]

        Args:
            base_state: State whose ac_units positions are fixed; modes/powers will be tuned.
            simulation_steps: Minutes to simulate for each evaluation.

        Returns:
            List of ACUnit instances with optimised mode and power_level.
        """
        pass

    def optimize_simulated_annealing(
        self,
        base_state: State,
        new_ac_list: list[ACUnit],
        candidate_position_list: list[tuple[int, int]],
        simulation_steps: int = 30,
    ) -> list[ACUnit]:
        """
        Provided function.

        Simulated annealing placement (positions only) for all new ACs at once.

        This samples neighbors by reassigning one AC to an unassigned available
        position and accepts moves according to an annealing schedule.

        Args:
            base_state: Baseline state with fixed ACs.
            new_ac_list: AC templates to place.
            candidate_position_list: Candidate placement cells.
            simulation_steps: Minutes to simulate for evaluation.

        Returns:
            placed_new_acs: List of newly placed ACUnit instances.
        """
        new_ac_list = list(new_ac_list)
        n = len(new_ac_list)
        if n == 0:
            return []

        rng = np.random.default_rng(self.random_seed)

        # Deduplicate candidates while preserving order
        seen = set()
        candidates = []
        for p in candidate_position_list:
            r, c = int(p[0]), int(p[1])
            if (r, c) not in seen:
                seen.add((r, c))
                candidates.append((r, c))

        fixed_occupied = {(int(ac.row), int(ac.col)) for ac in base_state.ac_units}
        available = [pos for pos in candidates if pos not in fixed_occupied]

        if len(available) < n:
            raise ValueError("Not enough candidate positions to place all new ACs.")

        avail = available.copy()
        rng.shuffle(avail)

        current_pos = avail[:n]
        best_pos = current_pos.copy()

        # Build current new ACs
        current_new = []
        for i, (r, c) in enumerate(current_pos):
            tpl = new_ac_list[i]
            current_new.append(
                ACUnit(
                    name=tpl.name,
                    row=r,
                    col=c,
                    power_level=int(tpl.power_level),
                    mode=tpl.mode,
                )
            )

        current_score = self._evaluate(base_state, current_new, simulation_steps)
        best_score = current_score

        temperature = float(self.initial_temperature)
        cooling_rate = float(self.cooling_rate)
        max_iter = int(self.max_iterations)

        available_set = set(avail)

        for _ in range(max_iter):
            # neighbor: replace one assigned position with one currently unassigned available position
            idx = int(rng.integers(0, n))
            assigned = set(current_pos)
            unassigned = list(available_set - assigned)
            if not unassigned:
                break

            new_pos = current_pos.copy()
            new_pos[idx] = unassigned[int(rng.integers(0, len(unassigned)))]

            # Build new ACs for evaluation (inline, no helper)
            new_new = []
            for i, (r, c) in enumerate(new_pos):
                tpl = new_ac_list[i]
                new_new.append(
                    ACUnit(
                        name=tpl.name,
                        row=r,
                        col=c,
                        power_level=int(tpl.power_level),
                        mode=tpl.mode,
                    )
                )

            new_score = self._evaluate(base_state, new_new, simulation_steps)
            delta = new_score - current_score

            accept = (delta > 0) or (rng.random() < np.exp(delta / max(temperature, 1e-12)))
            if accept:
                current_pos = new_pos
                current_score = new_score
                current_new = new_new
                if new_score > best_score:
                    best_score = new_score
                    best_pos = new_pos

            temperature *= cooling_rate
            if temperature <= 1e-12:
                temperature = 1e-12

        # Build best new ACs to return
        best_new = []
        for i, (r, c) in enumerate(best_pos):
            tpl = new_ac_list[i]
            best_new.append(
                ACUnit(
                    name=tpl.name,
                    row=r,
                    col=c,
                    power_level=int(tpl.power_level),
                    mode=tpl.mode,
                )
            )

        return best_new

    def __repr__(self) -> str:
        """
        Provided function.
        Short debug representation.

        e.g.: print(optimizer)
        """
        return (
            f"Optimizer(simulator={self.simulator!r}, "
            f"scoring={self.scoring!r}, "
            f"max_iterations={self.max_iterations})"
        )
