import os.path
import sys

# to import from parent directory
_current_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(_current_dir))

import numpy as np
from core import FloorMap
from encrypted_solution.core import FloorMap as SampleFloorMap
from test_support import run_testcases


def test(map_text, toggle_doors=None, is_student=True):
    FloorMapClass = FloorMap if is_student else SampleFloorMap
    m = FloorMapClass(map_text)
    if toggle_doors:
        for row, col in toggle_doors:
            m.toggle_door(row, col)
    return m.get_conductivity_mask()


def check_correctness(result_student, result_sample):
    return np.isclose(result_student, result_sample).all()


testcases = [
    {'map_text': "##*##\n" "#...#\n" "#.A.#\n" "#...#\n" "@@@@@\n"},
    {'map_text': "##*##\n" "#...#\n" "#.A.#\n" "#..B#\n" "#@*@#\n", 'toggle_doors': [(0, 2), (4, 2)]},
    {'map_text': "A...\n" "....\n" "...B\n"},
    {'map_text': "##*##\n" "#A..#\n" "#...#\n" "#..B#\n" "#####\n", 'toggle_doors': [(0, 2)]},
    {'map_text': "@@@\n" "@A@\n" "@@@\n"},
]

if __name__ == "__main__":
    run_testcases(test, check_correctness, testcases, task_name='Task 1.3: FloorMap.get_conductivity_mask')
