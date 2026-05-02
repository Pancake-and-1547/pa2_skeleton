import os.path
import sys

# to import from parent directory
_current_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(_current_dir))

import numpy as np
from core import Scoring
from encrypted_solution.core import Scoring as SampleScoring
from test_support import run_testcases


def test(room_weights, is_student=True):
    ScoringClass = Scoring if is_student else SampleScoring
    return ScoringClass()._build_weight_lookup(room_weights)


def check_correctness(result_student, result_sample):
    return np.isclose(result_student, result_sample).all()


testcases = [
    {'room_weights': {'A': 1.0, 'B': 2.0, 'C': 3.0}},
    {'room_weights': {'X': 0.5, 'Y': 1.5}},
    {'room_weights': {'A': 0.0, 'M': 7.25, 'Z': 1.5}},
    {'room_weights': {'B': 2.5, 'H': 2.5, 'N': 9.0, 'Q': 3.14}},
    {'room_weights': {}},
]

if __name__ == "__main__":
    run_testcases(test, check_correctness, testcases, task_name='Task 5.1: Scoring._build_weight_lookup')
