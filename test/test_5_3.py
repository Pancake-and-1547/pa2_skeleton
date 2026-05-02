import os.path
import sys

# to import from parent directory
_current_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(_current_dir))

import numpy as np
from core import Scoring
from encrypted_solution.core import FloorMap, Scoring as SampleScoring
from test_support import run_testcases


def test(map_text, room_weights, setpoint_temp, temperature_field, is_student=True):
    ScoringClass = Scoring if is_student else SampleScoring
    floor_map = FloorMap(map_text)
    return ScoringClass().compute_comfort_score(
        floor_map,
        room_weights,
        setpoint_temp,
        temperature_field,
    )


def check_correctness(result_student, result_sample):
    return np.isclose(result_student, result_sample)


testcases = [
    {
        "map_text": "AA#\n" "###\n" "BB#\n",
        "room_weights": {"A": 1.0, "B": 2.0, "C": 3.0},
        "setpoint_temp": 22.0,
        "temperature_field": np.array(
            [
                [20.0, 24.0, 30.0],
                [30.0, 30.0, 30.0],
                [21.0, 25.0, 30.0],
            ],
            dtype=float,
        ),
    },
    {
        "map_text": "..A..\n" ".###.\n" "..B..\n",
        "room_weights": {"A": 3.0, "B": 1.5},
        "setpoint_temp": 18.5,
        "temperature_field": np.array(
            [
                [19.0, 18.0, 17.0, 18.0, 19.0],
                [18.5, 22.0, 22.0, 22.0, 18.5],
                [20.0, 19.0, 16.0, 19.0, 20.0],
            ],
            dtype=float,
        ),
    },
    {
        "map_text": "A..B\n" ".@@.\n" "C..D\n",
        "room_weights": {"A": 4.0, "B": 2.0, "C": 1.0, "D": 3.0},
        "setpoint_temp": 24.0,
        "temperature_field": np.array(
            [
                [26.0, 25.0, 22.0, 23.0],
                [24.0, 30.0, 30.0, 24.0],
                [21.0, 20.0, 24.0, 27.0],
            ],
            dtype=float,
        ),
    },
    {
        "map_text": "A...\n" "....\n" "...B\n",
        "room_weights": {"A": 2.0},
        "setpoint_temp": 21.0,
        "temperature_field": np.array(
            [
                [20.0, 21.0, 22.0, 23.0],
                [21.0, 21.0, 21.0, 21.0],
                [24.0, 23.0, 22.0, 21.0],
            ],
            dtype=float,
        ),
    },
    {
        "map_text": "A#B\n" "###\n" "C#D\n",
        "room_weights": {"A": 1.0, "B": 1.5, "C": 2.0, "D": 2.5},
        "setpoint_temp": 22.0,
        "temperature_field": np.array(
            [
                [22.0, 30.0, 21.0],
                [30.0, 30.0, 30.0],
                [23.0, 30.0, 24.0],
            ],
            dtype=float,
        ),
    },
]


if __name__ == "__main__":
    run_testcases(test, check_correctness, testcases, task_name="Task 5.3: compute_comfort_score(...)")
