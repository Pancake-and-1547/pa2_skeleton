import os.path
import sys
from unittest import result

# to import from parent directory
_current_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(_current_dir))

from app import optimize_given
from encrypted_solution.app import init_test_state
from encrypted_solution.core import Simulator, Scoring, State
from test_support import run_testcases, compare_state

res = None # to store the result of optimize_given for checks, avoid repeated calls in multiple testcases

def test(tail_start, tail_end, min_tail_score, is_student=True):
    if not is_student: return True

    global res
    if res is None: res = optimize_given() # call once and reuse for all testcases to save time

    # Validate that the returned list has exactly 120 State objects
    if len(res) != 120:
        return 'Expected 120 State objects, got {}'.format(len(res))
    
    # Validate that scores for the requested window exceed the required threshold
    if not all(s.score[0] > min_tail_score for s in res[tail_start:tail_end]):
        return (
            f'Scores for indices {tail_start}-{tail_end} do not exceed '
            f'the required threshold {min_tail_score}'
        )
    
    map_text = """
    ##################
    #.......#........#
    #...B...*.C.###*##
    #.......#...#..D.#
    ####*#############
    #....A...*.......#
    #........#....E..#
    @@@@@@@*@@@@@@@@@@
    """
    
    room_weights = {
        'A': 2.0, 
        'B': 1.5, 
        'C': 1.0, 
        'D': 1.0, 
        'E': 1.3  
    }
    
    # Initialize state with environment parameters
    init_state = init_test_state(
        map_text, 
        outdoor_temp=30.0, 
        setpoint_temp=26.0, 
        room_weights=room_weights
    )

    # Validate that the returned states are consistent with the simulation dynamics
    simulator = Simulator()
    scoring = Scoring()
    current_state = init_state.copy()

    for next_state in res:
        # copy the AC settings
        current_state.ac_units = next_state.ac_units

        # simulate one step
        simulator.step(current_state)
        # calculate the score
        scoring.compute_total_score(current_state)

        # Validate the score and temperature field match the next state
        if not compare_state(current_state, next_state):
            return 'Integrity check failed for state history at step {}'.format(res.index(next_state))
        
    return True

def check_correctness(result_student, result_sample):
    return result_student == result_sample

testcases = [
    {'tail_start': 115, 'tail_end': 120, 'min_tail_score': 80.0},
    {'tail_start': 110, 'tail_end': 120, 'min_tail_score': 85.0},
    {'tail_start': 100, 'tail_end': 120, 'min_tail_score': 90.0},
    {'tail_start': 80, 'tail_end': 120, 'min_tail_score': 95.0},
    {'tail_start': 60, 'tail_end': 120, 'min_tail_score': 97.0},
]

if __name__ == "__main__":
    run_testcases(test, check_correctness, testcases, task_name='Optional Task 8.3: optimize_given')
