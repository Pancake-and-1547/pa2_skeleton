import os.path
import sys

# to import from parent directory
_current_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(_current_dir))

import numpy as np
from encrypted_solution.core import FloorMap, ACUnit, State, Simulator, Scoring
from core import Optimizer
from encrypted_solution.core import Optimizer as SampleOptimizer
from test_support import run_testcases


def test(base_state, new_ac_list, n_steps, temp_field=None, is_student=True):
    OptimizerClass = Optimizer if is_student else SampleOptimizer
    return OptimizerClass(Simulator(), Scoring())._evaluate(base_state, new_ac_list, n_steps)


def check_correctness(result_student, result_sample):
    return np.isclose(result_student, result_sample)


testcases = [
    {
        'base_state': State(
            floor_map=FloorMap("#####\n" "#A@.#\n" "#.@.#\n" "#.@B#\n" "#####\n"),
            room_weights={'A': 1.0, 'B': 2.0, 'C': 3.0},
            ac_units=[ACUnit(name='cool', row=1, col=1, power_level=3, mode=ACUnit.MODE_COOL),
                      ACUnit(name='heat', row=2, col=1, power_level=3, mode=ACUnit.MODE_HEAT)]
        ),
        'new_ac_list': [ACUnit(name='cool2', row=3, col=1, power_level=5, mode=ACUnit.MODE_COOL)],
        'n_steps': 10,
    },
    {
        'base_state': State(
            floor_map=FloorMap("C.#.A\n" "..@..\n" "..#.D\n"),
            room_weights={'A': 4.0, 'B': 3.0, 'C': 2.0, 'D': 1.0},
            ac_units=[],
            temperature_field=np.array([[22.3, 22.7, 23.6, 24.0, 22.9],
                                        [22.0, 23.0, 24.0, 23.0, 22.0],
                                        [23.0, 24.0, 22.0, 24.0, 22.6]]),
        ),
        'new_ac_list': [
            ACUnit(name='cool', row=1, col=1, power_level=4, mode=ACUnit.MODE_COOL),
            ACUnit(name='heat', row=1, col=4, power_level=5, mode=ACUnit.MODE_COOL),
        ],
        'n_steps': 20,
    },
    {
        'base_state': State(
            floor_map=FloorMap("A..B\n" "....\n" "C..D\n"),
            room_weights={'A': 1.0, 'B': 4.0, 'C': 2.0, 'D': 3.0},
            ac_units=[ACUnit(name='fixed', row=1, col=2, power_level=2, mode=ACUnit.MODE_COOL)],
            temperature_field=np.array([[19.0, 20.0, 21.0, 22.0],
                                        [20.0, 21.0, 22.0, 23.0],
                                        [21.0, 22.0, 23.0, 24.0]]),
            outdoor_temp=18.0,
            setpoint_temp=22.0,
        ),
        'new_ac_list': [
            ACUnit(name='cool2', row=0, col=1, power_level=3, mode=ACUnit.MODE_COOL),
            ACUnit(name='heat1', row=2, col=2, power_level=2, mode=ACUnit.MODE_HEAT),
        ],
        'n_steps': 6,
    },
    {
        'base_state': State(
            floor_map=FloorMap("#####\n" "#A.B#\n" "#...#\n" "#C.D#\n" "#####\n"),
            room_weights={'A': 2.0, 'B': 1.0, 'C': 3.0, 'D': 4.0},
            temperature_field=np.linspace(18.0, 30.0, num=25).reshape((5, 5)),
            outdoor_temp=32.0,
            setpoint_temp=24.0,
        ),
        'new_ac_list': [
            ACUnit(name='cool', row=1, col=2, power_level=5, mode=ACUnit.MODE_COOL),
            ACUnit(name='heat', row=3, col=2, power_level=1, mode=ACUnit.MODE_HEAT),
        ],
        'n_steps': 8,
    },
    {
        'base_state': State(
            floor_map=FloorMap("A@#*#@B\n" "C#DEF#G\n" "H*IJK*L\n" "M#NOP#Q\n" "R@#*#@S\n"),
            room_weights={
                'A': 1.0, 'B': 2.0, 'C': 3.0, 'D': 4.0, 'E': 5.0, 'F': 6.0, 'G': 7.0,
                'H': 8.0, 'I': 9.0, 'J': 10.0, 'K': 11.0, 'L': 12.0, 'M': 13.0,
                'N': 14.0, 'O': 15.0, 'P': 16.0, 'Q': 17.0, 'R': 18.0, 'S': 19.0,
            },
        ),
        'new_ac_list': [
            ACUnit('cool', 1, 2, 4, ACUnit.MODE_COOL),
            ACUnit('heat', 3, 4, 2, ACUnit.MODE_HEAT),
        ],
        'n_steps': 10,
    },
    {
        'base_state': State(
            floor_map=FloorMap("#####\n" "#A@D#\n" "#E@B#\n" "##@##\n" "#FCG#\n" "#####\n"),
            room_weights={'A': 4.0, 'B': 3.0, 'C': 2.0, 'D': 1.0, 'E': 0.5, 'F': 0.2, 'G': 0.1},
            temperature_field=np.array([[22.3, 22.7, 23.6, 24.0, 22.9],
                                        [22.0, 23.0, 24.0, 23.0, 22.0],
                                        [23.0, 24.0, 22.0, 24.0, 22.6],
                                        [24.5, 25.0, 24.8, 25.2, 24.9],
                                        [25.0, 24.7, 24.5, 24.6, 25.1],
                                        [24.8, 24.9, 25.0, 24.8, 24.7]]),
            setpoint_temp=24.0,
        ),
        'new_ac_list': [
            ACUnit('cool', 1, 1, 5, ACUnit.MODE_COOL),
            ACUnit('cool2', 2, 1, 4, ACUnit.MODE_COOL),
            ACUnit('heat', 4, 3, 3, ACUnit.MODE_HEAT),
        ],
        'n_steps': 10,
    },
    {
        'base_state': State(
            floor_map=FloorMap("A...\n" "....\n" "...B\n"),
            room_weights={'A': 2.0},
            temperature_field=np.full((3, 4), 20.0),
        ),
        'new_ac_list': [],
        'n_steps': 0,
    },
]

if __name__ == "__main__":
    run_testcases(test, check_correctness, testcases, task_name='Optional Task 7.1: Optimizer._evaluate')
