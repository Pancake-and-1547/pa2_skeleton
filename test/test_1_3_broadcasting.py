import os.path
import sys

_current_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(_current_dir))

import numpy as np
from core import FloorMap
from core.state.floor_map import get_conductivity_mask as student_get_conductivity_mask
from encrypted_solution.core import FloorMap as SampleFloorMap
from test_support import run_testcases_broadcasting


def make_large_map(rows, cols, row_period, col_period):
    lines = []
    for r in range(rows):
        chars = []
        for c in range(cols):
            if r % row_period == 0:
                chars.append("@")
            elif c % col_period == 0:
                chars.append("#")
            elif r % row_period == row_period - 1 and c % col_period == col_period - 1:
                chars.append("*")
            else:
                chars.append(chr(ord("A") + ((r // row_period) + (c // col_period)) % 26))
        lines.append("".join(chars))
    return "\n".join(lines) + "\n"


def make_toggle_positions(map_text, stride):
    toggles = []
    for r, line in enumerate(map_text.strip().splitlines()):
        for c, ch in enumerate(line):
            if ch == "*" and (len(toggles) % stride == 0):
                toggles.append((r, c))
    return toggles


def test(map_text, toggle_doors=None, is_student=True):
    FloorMapClass = FloorMap if is_student else SampleFloorMap
    floor_map = FloorMapClass(map_text, auto_check_doors=False)
    if toggle_doors:
        for row, col in toggle_doors:
            floor_map.toggle_door(row, col)
    return floor_map.get_conductivity_mask()


def check_correctness(result_student, result_sample):
    return np.isclose(result_student, result_sample).all()


_MAP_1 = make_large_map(72, 96, 6, 8)
_MAP_2 = make_large_map(180, 220, 9, 11)
_MAP_3 = make_large_map(300, 300, 10, 10)
_MAP_4 = make_large_map(36, 40, 5, 6)
_MAP_5 = make_large_map(210, 180, 8, 9)

testcases = [
    {"map_text": _MAP_1, "toggle_doors": make_toggle_positions(_MAP_1, 2)},
    {"map_text": _MAP_2, "toggle_doors": make_toggle_positions(_MAP_2, 3)},
    {"map_text": _MAP_3, "toggle_doors": make_toggle_positions(_MAP_3, 4)},
    {"map_text": _MAP_4, "toggle_doors": make_toggle_positions(_MAP_4, 1)},
    {"map_text": _MAP_5, "toggle_doors": make_toggle_positions(_MAP_5, 5)},
]


if __name__ == "__main__":
    run_testcases_broadcasting(
        test,
        check_correctness,
        testcases,
        func_to_check=student_get_conductivity_mask,
        module_to_check=FloorMap,
        task_name="Task 1.3 - Broadcasting Test: FloorMap.get_conductivity_mask",
    )
