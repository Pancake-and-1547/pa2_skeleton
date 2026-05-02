import os.path
import sys

# to import from parent directory
_current_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(_current_dir))

import numpy as np
from core import ACUnit
from encrypted_solution.core import ACUnit as SampleACUnit
from test_support import run_testcases


def test(power_level, mode, is_student=True):
    ACUnitClass = ACUnit if is_student else SampleACUnit
    return ACUnitClass('ac', 0, 0, power_level, mode).get_energy_consumption()


def check_correctness(result_student, result_sample):
    return np.isclose(result_student, result_sample)


testcases = [
    {'power_level': 3, 'mode': ACUnit.MODE_COOL},
    {'power_level': 4, 'mode': ACUnit.MODE_HEAT},
    {'power_level': 2, 'mode': ACUnit.MODE_OFF},
    {'power_level': 0, 'mode': ACUnit.MODE_HEAT},
    {'power_level': 1, 'mode': ACUnit.MODE_COOL},
]

if __name__ == "__main__":
    run_testcases(test, check_correctness, testcases, task_name='Task 2.2: ACUnit.get_energy_consumption')
