import os.path
import sys

# to import from parent directory
_current_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(_current_dir))

import numpy as np
from core import FloorMap
from encrypted_solution.core import FloorMap as SampleFloorMap
from test_support import run_testcases


def test(map_text, start_row, start_col, is_student=True):
    FloorMapClass = FloorMap if is_student else SampleFloorMap
    m = FloorMapClass(map_text, auto_assign_room_types=False)

    m.room_types = np.full((m.height, m.width), "x", dtype=object)
    cells, labels = [], []
    m._flood_fill(start_row, start_col, cells, labels)
    
    return sorted(cells), sorted(labels)


def check_correctness(result_student, result_sample):
    return result_student == result_sample


testcases = [
    {'map_text': "#####\n" "#...#\n" "#.A.#\n" "#...#\n" "#####\n", 'start_row': 1, 'start_col': 1},
    {'map_text': "#@@@#\n" "#..C#\n" "#.A.#\n" "#.#B#\n" "#####\n", 'start_row': 1, 'start_col': 1},
    {'map_text': "A..\n" "...\n" "...\n", 'start_row': 0, 'start_col': 0},
    {'map_text': "A..#\n" ".#.#\n" "...B\n", 'start_row': 2, 'start_col': 0},
    {'map_text': "#####\n" "#A.B#\n" "#...#\n" "#####\n", 'start_row': 1, 'start_col': 3},
]


if __name__ == "__main__":
    run_testcases(test, check_correctness, testcases, task_name='Task 1.2.1: FloorMap._flood_fill')
