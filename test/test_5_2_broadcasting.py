import os.path
import sys

_current_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(_current_dir))

import numpy as np
from core import FloorMap, Scoring
from core.scoring import get_room_type_weight_mask as student_get_room_type_weight_mask
from encrypted_solution.core import FloorMap as SampleFloorMap, Scoring as SampleScoring
from test_support import run_testcases_broadcasting


def make_large_map(rows, cols, row_period, col_period):
    lines = []
    for r in range(rows):
        chars = []
        for c in range(cols):
            if r % row_period == row_period - 1 or c % col_period == col_period - 1:
                chars.append('#')
            else:
                block_id = (r // row_period) * 7 + (c // col_period)
                chars.append(chr(ord('A') + block_id % 26))
        lines.append("".join(chars))
    return "\n".join(lines) + "\n"


def make_room_weights(scale, offset=0.0):
    return {chr(ord('A') + i): offset + scale * (i + 1) for i in range(26)}


def test(map_text, room_weights, is_student=True):
    FloorMapClass = FloorMap if is_student else SampleFloorMap
    ScoringClass = Scoring if is_student else SampleScoring
    return ScoringClass().get_room_type_weight_mask(FloorMapClass(map_text), room_weights)


def check_correctness(result_student, result_sample):
    return np.isclose(result_student, result_sample).all()


testcases = [
    {
        'map_text': make_large_map(32, 32, 4, 5),
        'room_weights': make_room_weights(scale=0.5),
    },
    {
        'map_text': make_large_map(120, 160, 6, 7),
        'room_weights': make_room_weights(scale=1.0),
    },
    {
        'map_text': make_large_map(220, 180, 8, 9),
        'room_weights': make_room_weights(scale=1.5, offset=-2.0),
    }, 
    {
        'map_text': make_large_map(256, 225, 10, 11),
        'room_weights': make_room_weights(scale=0.75, offset=1.0),
    },
    {
        'map_text': make_large_map(150, 210, 7, 9),
        'room_weights': make_room_weights(scale=1.25, offset=-0.5),
    },
]


if __name__ == "__main__":
    run_testcases_broadcasting(
        test,
        check_correctness,
        testcases,
        func_to_check=student_get_room_type_weight_mask,
        module_to_check=Scoring,
    task_name='Task 5.2 - Broadcasting Test: Scoring.get_room_type_weight_mask',
    )
