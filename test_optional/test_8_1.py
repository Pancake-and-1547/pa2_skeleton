import os.path
import sys

# to import from parent directory
_current_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(_current_dir))

from app import init_test_state
from encrypted_solution.app import init_test_state as SampleInitTestState
from test_support import run_testcases, compare_state


def test(map_text, outdoor_temp, setpoint_temp, room_weights, is_student=True):
    fn = init_test_state if is_student else SampleInitTestState
    return fn(map_text, outdoor_temp, setpoint_temp, room_weights)


def check_correctness(result_student, result_sample):
    return compare_state(result_student, result_sample)


testcases = [
    {
        'map_text': "A@#*#@B\n" "C#DEF#G\n" "H*IJK*L\n" "M#NOP#Q\n" "R@#*#@S\n",
        'outdoor_temp': 30.0,
        'setpoint_temp': 26.0,
        'room_weights': {
            'A': 1.0, 'B': 2.0, 'C': 3.0, 'D': 4.0, 'E': 5.0, 'F': 6.0, 'G': 7.0,
            'H': 8.0, 'I': 9.0, 'J': 10.0, 'K': 11.0, 'L': 12.0, 'M': 13.0,
            'N': 14.0, 'O': 15.0, 'P': 16.0, 'Q': 17.0, 'R': 18.0, 'S': 19.0,
        },
    },
    {
        'map_text': "A.#.B\n" "..@..\n" "C.#.D\n",
        'outdoor_temp': 25.0,
        'setpoint_temp': 26.0,
        'room_weights': {'A': 1.0, 'B': 2.0, 'C': 3.0, 'D': 4.0},
    },
    {
        'map_text': "A..B\n" "....\n" "C..D\n",
        'outdoor_temp': 18.0,
        'setpoint_temp': 24.0,
        'room_weights': {'A': 1.0, 'B': 4.0, 'C': 2.0, 'D': 3.0},
    },
    {
        'map_text': "#####\n" "#A.B#\n" "#...#\n" "#C.D#\n" "#####\n",
        'outdoor_temp': 33.0,
        'setpoint_temp': 26.0,
        'room_weights': {'A': 2.0, 'B': 1.0, 'C': 3.0, 'D': 4.0},
    },
    {
        'map_text': "A.#.@.B#\n" "C@.@@..@\n",
        'outdoor_temp': -5.0,
        'setpoint_temp': 18.0,
        'room_weights': {'A': 4.0, 'B': 3.0},
    },
    {
        'map_text': "A....\n" ".....\n" ".....\n" ".....\n" ".....\n",
        'outdoor_temp': 12.5,
        'setpoint_temp': 21.0,
        'room_weights': {'A': 1.0},
    },
    {
        'map_text': "#####\n" "#A.B#\n" "#...#\n" "#C.D#\n" "#####\n",
        'outdoor_temp': 33.0,
        'setpoint_temp': 26.0,
        'room_weights': {'A': 2.0, 'C': 3.0},
    },
    {
        'map_text': "A..#B\n" "..@..\n" "C..#D\n",
        'outdoor_temp': 18.0,
        'setpoint_temp': 24.0,
        'room_weights': {'A': 1.0, 'B': 4.0, 'C': 2.0, 'D': 3.0},
    },
]

if __name__ == "__main__":
    run_testcases(test, check_correctness, testcases, task_name='Optional Task 8.1: init_test_state')
