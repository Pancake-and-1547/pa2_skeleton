import os.path
import sys

_current_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(_current_dir))

import numpy as np
from core import Scoring
from core.scoring import _build_weight_lookup as student_build_weight_lookup
from encrypted_solution.core import Scoring as SampleScoring
from test_support import run_testcases_broadcasting


def make_room_weights(scale, offset=0.0, keep_mod=None):
    weights = {}
    for i, letter in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
        if keep_mod is not None and i % keep_mod == 0:
            continue
        weights[letter] = offset + scale * (i + 1)
    return weights


def test(room_weights, is_student=True):
    ScoringClass = Scoring if is_student else SampleScoring
    return ScoringClass()._build_weight_lookup(room_weights)


def check_correctness(result_student, result_sample):
    return np.isclose(result_student, result_sample).all()


testcases = [
    {'room_weights': {'A': 1.0, 'B': 2.0, 'C': 3.0}},
    {'room_weights': make_room_weights(scale=0.5)},
    {'room_weights': make_room_weights(scale=1.25, offset=-3.0)},
    {'room_weights': make_room_weights(scale=2.0, keep_mod=2)},
    {'room_weights': make_room_weights(scale=0.75, offset=2.5, keep_mod=5)},
]


if __name__ == "__main__":
    run_testcases_broadcasting(
        test,
        check_correctness,
        testcases,
        func_to_check=student_build_weight_lookup,
        module_to_check=Scoring,
    task_name='Task 5.1 - Broadcasting Test: Scoring._build_weight_lookup',
    )
