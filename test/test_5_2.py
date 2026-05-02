import os.path
import sys

# to import from parent directory
_current_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(_current_dir))

import numpy as np
from core import Scoring
from encrypted_solution.core import FloorMap, Scoring as SampleScoring
from test_support import run_testcases


def test(map_text, room_weights, is_student=True):
    ScoringClass = Scoring if is_student else SampleScoring
    return ScoringClass().get_room_type_weight_mask(FloorMap(map_text), room_weights)


def check_correctness(result_student, result_sample):
    return np.isclose(result_student, result_sample).all()


testcases = [
    {
        'map_text': "#####\n" "#A@.#\n" "#.@.#\n" "#.@B#\n" "#####\n",
        'room_weights': {'A': 1.0, 'B': 2.0, 'C': 3.0},
    },
    {
        'map_text': "..#.A\n" "..@..\n" "..#.D\n",
        'room_weights': {'A': 4.0, 'B': 3.0, 'C': 2.0, 'D': 1.0},
    },
    {
        'map_text': "A..#B\n" "..@..\n" "C..#D\n",
        'room_weights': {'A': 1.0, 'B': 4.0, 'C': 2.0, 'D': 3.0},
    },
    {
        'map_text': "#####\n" "#A..#\n" "#.#B#\n" "#..C#\n" "#####\n",
        'room_weights': {'A': 2.5, 'B': 1.5, 'C': 0.5, 'D': 9.0},
    },
    {
        'map_text': "A...\n" "....\n" "...B\n",
        'room_weights': {'A': 2.0},
    },
]

if __name__ == "__main__":
    run_testcases(test, check_correctness, testcases, task_name='Task 5.2: Scoring.get_room_type_weight_mask')
