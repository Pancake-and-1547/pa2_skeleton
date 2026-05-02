import os.path
import sys

# to import from parent directory
_current_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(_current_dir))

import numpy as np
from core import Simulator
from encrypted_solution.core import ACUnit, Simulator as SampleSimulator
from test_support import run_testcases

def test(temp_field, ac_units, is_student=True):
    SimulatorClass = Simulator if is_student else SampleSimulator
    simulator = SimulatorClass()
    return simulator._ac_injection(temp_field, ac_units)


def check_correctness(result_student, result_sample):
    new_temp_s, energy_s = result_student
    new_temp_r, energy_r = result_sample
    return (
        np.isclose(new_temp_s, new_temp_r).all()
        and energy_s.keys() == energy_r.keys()
        and all(np.isclose(energy_s[k], energy_r[k]) for k in energy_s)
    )


testcases = [
    {
        'temp_field': np.full((10, 10), 25.0),
        'ac_units': [
            ACUnit('AC1', 5, 5, 3, ACUnit.MODE_COOL),
            ACUnit('AC2', 2, 7, 2, ACUnit.MODE_HEAT),
        ],
    },
    {
        'temp_field': np.linspace(15.0, 39.0, num=25).reshape((5, 5)),
        'ac_units': [
            ACUnit('AC1', 3, 4, 4, ACUnit.MODE_OFF),
            ACUnit('AC2', 1, 3, 5, ACUnit.MODE_HEAT),
        ],
    },
    {
        'temp_field': np.array([[22.0]]),
        'ac_units': [ACUnit('Solo', 0, 0, 2, ACUnit.MODE_COOL)],
    },
    {
        'temp_field': np.arange(12.0, 27.0).reshape((3, 5)),
        'ac_units': [],
    },
    {
        'temp_field': np.full((4, 4), 20.0),
        'ac_units': [
            ACUnit('AC1', 1, 1, 1, ACUnit.MODE_HEAT),
            ACUnit('AC2', 1, 1, 2, ACUnit.MODE_COOL),
        ],
    },
]

if __name__ == "__main__":
    run_testcases(test, check_correctness, testcases, task_name='Task 4.1: Simulator._ac_injection')
