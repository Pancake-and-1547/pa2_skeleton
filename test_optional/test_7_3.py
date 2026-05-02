import os.path
import sys

# to import from parent directory
_current_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(_current_dir))

import numpy as np
from encrypted_solution.core import FloorMap, ACUnit, State, Simulator, Scoring
from core import Optimizer
from encrypted_solution.core import Optimizer as SampleOptimizer
from test_support import run_testcases, compare_ac


def test(base_state, n_steps, is_student=True):
    """Tests optimize_schedule_greedy when new_ac_specs is None, otherwise optimize_greedy."""
    OptimizationClass = Optimizer if is_student else SampleOptimizer
    
    result = OptimizationClass(Simulator(), Scoring()).optimize_schedule_greedy(
        base_state, n_steps
    )
    return result

def check_correctness(result_student, result_sample):
    return len(result_student) == len(result_sample) and all(
        compare_ac(ac_student, ac_sample) for ac_student, ac_sample in zip(result_student, result_sample)
    )


testcases = [
    {
        'base_state': State(
            floor_map=FloorMap("#####\n" "#A@.#\n" "#.@.#\n" "#.@B#\n" "#####\n"),
            room_weights={'A': 1.0, 'B': 2.0, 'C': 3.0},
            ac_units=[
                ACUnit(name='New ac1', row=2, col=1, power_level=2, mode=ACUnit.MODE_COOL),
                ACUnit(name='New ac2', row=2, col=3, power_level=5, mode=ACUnit.MODE_COOL)
            ],
        ),
        'n_steps': 5,
    },
    {
        'base_state': State(
            floor_map=FloorMap("C.#.A\n" "..@..\n" "..#.D\n"),
            room_weights={'A': 4.0, 'B': 3.0, 'C': 2.0, 'D': 1.0},
            temperature_field=np.array([[22.3, 22.7, 23.6, 24.0, 22.9],
                                        [22.0, 23.0, 24.0, 23.0, 22.0],
                                        [23.0, 24.0, 22.0, 24.0, 22.6]]),
            ac_units=[
                ACUnit(name='AC', row=0, col=1, power_level=2, mode=ACUnit.MODE_COOL),
                ACUnit(name='New ac1', row=1, col=3, power_level=2, mode=ACUnit.MODE_COOL),
                ACUnit(name='New ac2', row=2, col=3, power_level=5, mode=ACUnit.MODE_COOL)
            ],
        ),
        'n_steps': 10,
    },
    {
        'base_state': State(
            floor_map=FloorMap("A..B\n" "....\n" "C..D\n"),
            room_weights={'A': 1.0, 'B': 4.0, 'C': 2.0, 'D': 3.0},
            temperature_field=np.array([[19.0, 20.0, 21.0, 22.0],
                                        [20.0, 21.0, 22.0, 23.0],
                                        [21.0, 22.0, 23.0, 24.0]]),
            ac_units=[
                ACUnit(name='AC1', row=0, col=1, power_level=2, mode=ACUnit.MODE_COOL),
                ACUnit(name='AC2', row=2, col=2, power_level=3, mode=ACUnit.MODE_HEAT),
            ],
            setpoint_temp=22.0,
            outdoor_temp=18.0,
        ),
        'n_steps': 4,
    },
    {
        'base_state': State(
            floor_map=FloorMap("#####\n" "#A.B#\n" "#...#\n" "#C.D#\n" "#####\n"),
            room_weights={'A': 2.0, 'B': 1.0, 'C': 3.0, 'D': 4.0},
            temperature_field=np.linspace(18.0, 30.0, num=25).reshape((5, 5)),
            ac_units=[
                ACUnit(name='AC1', row=1, col=1, power_level=1, mode=ACUnit.MODE_HEAT),
                ACUnit(name='AC2', row=1, col=3, power_level=4, mode=ACUnit.MODE_OFF),
                ACUnit(name='AC3', row=3, col=2, power_level=5, mode=ACUnit.MODE_COOL),
            ],
            setpoint_temp=24.0,
            outdoor_temp=32.0,
        ),
        'n_steps': 6,
    },
    {
        'base_state': State(
            floor_map=FloorMap("A@#*#@B\n" "C#DEF#G\n" "H*IJK*L\n" "M#NOP#Q\n" "R@#*#@S\n"),
            room_weights={
                'A': 1.0, 'B': 2.0, 'C': 3.0, 'D': 4.0, 'E': 5.0, 'F': 6.0, 'G': 7.0,
                'H': 8.0, 'I': 9.0, 'J': 10.0, 'K': 11.0, 'L': 12.0, 'M': 13.0,
                'N': 14.0, 'O': 15.0, 'P': 16.0, 'Q': 17.0, 'R': 18.0, 'S': 19.0,
            },
            ac_units=[
                ACUnit('ac1', 2, 3, 2, ACUnit.MODE_COOL),
                ACUnit('ac2', 2, 4, 5, ACUnit.MODE_HEAT),
                ACUnit('ac3', 2, 6, 5, ACUnit.MODE_COOL),
            ],
        ),
        'n_steps': 5,
    },
    {
        'base_state': State(
            floor_map=FloorMap("C.#.A\n" "..@..\n" "..#.D\n"),
            room_weights={'A': 4.0, 'B': 3.0, 'C': 2.0, 'D': 1.0},
            temperature_field=np.array([[22.3, 22.7, 23.6, 24.0, 22.9],
                                        [22.0, 23.0, 24.0, 23.0, 22.0],
                                        [23.0, 24.0, 22.0, 24.0, 22.6]]),
            ac_units=[
                ACUnit('ac1', 1, 3, 2, ACUnit.MODE_HEAT),
                ACUnit('ac2', 0, 3, 4, ACUnit.MODE_OFF),
                ACUnit('ac3', 2, 0, 2, ACUnit.MODE_HEAT),
            ],
            setpoint_temp=25.0,
            outdoor_temp=24.0,
        ),
        'n_steps': 5,
    },
    {
        'base_state': State(
            floor_map=FloorMap("A...\n" "....\n" "...B\n"),
            room_weights={'A': 2.0},
            temperature_field=np.full((3, 4), 20.0),
            ac_units=[ACUnit('AC1', 0, 0, 3, ACUnit.MODE_OFF)],
        ),
        'n_steps': 0,
    },
]

if __name__ == "__main__":
    run_testcases(test, check_correctness, testcases, task_name='Optional Task 7.3: Optimizer.optimize_schedule_greedy')
