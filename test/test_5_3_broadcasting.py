import os.path
import sys

_current_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(_current_dir))

import numpy as np
import core.scoring as student_scoring_module
from core import FloorMap, Scoring
from encrypted_solution.core import FloorMap as SampleFloorMap, Scoring as SampleScoring
from test_support import run_testcases_broadcasting


student_compute_comfort_score = student_scoring_module.compute_comfort_score


def make_large_map(rows, cols, row_period, col_period):
    lines = []
    for r in range(rows):
        chars = []
        for c in range(cols):
            if r % row_period == row_period - 1 or c % col_period == col_period - 1:
                chars.append("#")
            else:
                block_id = (r // row_period) * 9 + (c // col_period)
                chars.append(chr(ord("A") + block_id % 26))
        lines.append("".join(chars))
    return "\n".join(lines) + "\n"


def make_room_weights(scale, offset=0.0):
    return {chr(ord("A") + i): offset + scale * (i + 1) for i in range(26)}


def make_temperature_field(rows, cols, row_scale, col_scale, offset=0.0):
    return np.fromfunction(
        lambda r, c: offset + row_scale * r + col_scale * c,
        (rows, cols),
        dtype=float,
    )


def test(map_text, room_weights, setpoint_temp, temperature_field, is_student=True):
    FloorMapClass = FloorMap if is_student else SampleFloorMap
    ScoringClass = Scoring if is_student else SampleScoring
    floor_map = FloorMapClass(map_text)
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
        "map_text": make_large_map(40, 48, 5, 6),
        "room_weights": make_room_weights(scale=0.4),
        "setpoint_temp": 22.5,
        "temperature_field": make_temperature_field(40, 48, 0.05, 0.03, offset=18.0),
    },
    {
        "map_text": make_large_map(128, 160, 7, 8),
        "room_weights": make_room_weights(scale=0.8, offset=-1.0),
        "setpoint_temp": 24.0,
        "temperature_field": make_temperature_field(128, 160, 0.02, 0.015, offset=19.0),
    },
    {
        "map_text": make_large_map(240, 220, 9, 10),
        "room_weights": make_room_weights(scale=1.1, offset=0.5),
        "setpoint_temp": 26.0,
        "temperature_field": make_temperature_field(240, 220, 0.01, 0.02, offset=17.5),
    },
    {
        "map_text": make_large_map(72, 96, 6, 7),
        "room_weights": make_room_weights(scale=0.6, offset=1.0),
        "setpoint_temp": 23.0,
        "temperature_field": make_temperature_field(72, 96, 0.03, 0.02, offset=18.0),
    },
    {
        "map_text": make_large_map(192, 208, 8, 9),
        "room_weights": make_room_weights(scale=0.95, offset=0.25),
        "setpoint_temp": 25.5,
        "temperature_field": make_temperature_field(192, 208, 0.012, 0.016, offset=17.0),
    },
]


if __name__ == "__main__":
    run_testcases_broadcasting(
        test,
        check_correctness,
        testcases,
        func_to_check=student_compute_comfort_score,
        module_to_check=student_compute_comfort_score,
        task_name="Task 5.3 - Broadcasting Test: compute_comfort_score(...)",
    )
