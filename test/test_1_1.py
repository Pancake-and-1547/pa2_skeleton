import os.path
import sys

# to import from parent directory
_current_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(_current_dir))

from core import FloorMap
from encrypted_solution.core import FloorMap as SampleFloorMap
from test_support import run_testcases


def test(map_text, is_student=True):
    FloorMapClass = FloorMap if is_student else SampleFloorMap
    return FloorMapClass(map_text, auto_check_doors=False).check_doors()


def check_correctness(result_student, result_sample):
    return result_student == result_sample


testcases = [
    {'map_text': "#A#\n" "#*#\n" "#.#\n"},
    {'map_text': "###\n" "A*#\n" "###\n"},
    {'map_text': "#####\n" "#...#\n" "#.*A#\n" "#...#\n" "#####\n"},
    {'map_text': "#*#*#\n" "#.*A#\n" "#.*.#\n" "#.*.#\n" "#*#*#\n"},
    {'map_text': "#*#*#\n" "#A*B#\n" "#C*D#\n" "#E*F#\n" "@G#H@\n"},
]

if __name__ == "__main__":
    run_testcases(test, check_correctness, testcases, task_name='Task 1.1: FloorMap.check_doors')