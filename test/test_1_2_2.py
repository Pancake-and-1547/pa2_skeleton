import os.path
import sys

# to import from parent directory
_current_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(_current_dir))

import numpy as np
from core import FloorMap
from encrypted_solution.core import FloorMap as SampleFloorMap
from test_support import run_testcases


def test(map_text, is_student=True):
    FloorMapClass = FloorMap if is_student else SampleFloorMap
    floor_map = FloorMapClass(map_text, auto_assign_room_types=False)
    floor_map._assign_room_types()
    return floor_map.room_types

def check_correctness(result_student, result_sample):
    return np.array_equal(result_student, result_sample)


testcases = [
    {'map_text': "...\n" "#A#\n" "###\n"},
    {'map_text': "#####\n" "#A@.#\n" "#.@.#\n" "#.@B#\n" "#####\n"},
    {'map_text': "..#.A\n" "..@..\n" "..#.B\n"},
    {'map_text': "#####\n" "#A..#\n" "#####\n" "#..B#\n" "#####\n"},
    {'map_text': "A#..\n" ".#..\n" "..#B\n" "..#.\n"},
]

if __name__ == "__main__":
    run_testcases(test, check_correctness, testcases, task_name='Task 1.2.2: FloorMap._assign_room_types')
