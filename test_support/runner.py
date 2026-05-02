import copy
import json
import os
from pathlib import Path
import sys
import time
from typing import Callable

from .compare import find_different_parameters
from .broadcast import ALLOWED_IMPORT, analyze_function, check_module_imports


def run_testcases(
    test_fn: Callable,
    check_fn: Callable,
    testcases: list[dict],
    task_name: str = "",
    interactive: bool = True,
    ignore_modified_args: list[str] | None = None,
) -> None:
    """Run test_fn / check_fn / testcases triples without unittest."""
    if task_name:
        print(f"=== {task_name} ===")

    score_info = _load_task_score_info(len(testcases))

    indices: range | list[int] = range(len(testcases))
    if interactive:
        idx = _choose_case_index(len(testcases))
        if idx != -1:
            indices = [idx]

    selected_case_count = len(testcases) if isinstance(indices, range) else len(indices)
    if score_info is not None:
        task_score, per_case_score = score_info
        selected_max_score = per_case_score * selected_case_count
        print(
            f"Task score available: {task_score:.2f} total, "
            f"{per_case_score:.2f} per testcase, "
            f"{selected_max_score:.2f} for this run."
        )

    passed = failed = 0

    for i in indices:
        case = testcases[i]
        try:
            student, student_case, _ = _run_case(test_fn, case, is_student=True)
            sample, sample_case, _ = _run_case(test_fn, case, is_student=False)

            changed_params = find_different_parameters(
                student_case,
                sample_case,
                ignored_params=ignore_modified_args,
            )
            if changed_params:
                print(
                    f"  Case {i + 1}: ERROR - parameter(s) changed unexpectedly: "
                    f"{', '.join(changed_params)}"
                )
                failed += 1
                continue

            ok = check_fn(student, sample)
        except Exception as exc:
            print(f"  Case {i + 1}: ERROR - {exc}")
            failed += 1
            continue

        if ok:
            print(f"  Case {i + 1}: PASS")
            passed += 1
        else:
            print(f"  Case {i + 1}: FAIL")
            print(f"    Input:   {case}")
            print(f"    Student: {student!r}")
            print(f"    Sample:  {sample!r}")
            failed += 1

    total = passed + failed
    if failed == 0:
        print(f"All {total} case(s) passed.")
    else:
        print(f"{failed}/{total} case(s) failed.")
    if score_info is not None:
        _, per_case_score = score_info
        earned_score = passed * per_case_score
        selected_max_score = per_case_score * total
        print(f"Score earned: {earned_score:.2f}/{selected_max_score:.2f}")


def run_testcases_broadcasting(
    test_fn: Callable,
    check_fn: Callable,
    testcases: list[dict],
    func_to_check,
    module_to_check,
    allowed_import=ALLOWED_IMPORT,
    task_name: str = "",
    interactive: bool = True,
    running_times: int = 5,
    allowed_time_multiplier: float = 6.0,
    ignore_modified_args: list[str] | None = None,
) -> None:
    if os.getenv("SKIP_BROADCASTING_CHECK") or os.getenv("SKIP_VECTORIZE_CHECK"):
        print("Skipping array-operation check.")
    else:
        broadcasting_violations = check_broadcasting(func_to_check, module_to_check, allowed_import)
        if broadcasting_violations:
            print("Array-operation check failed with the following issues:")
            for violation in broadcasting_violations:
                print(f"  - {violation}")
            return
    print("Array-operation check passed. Running test cases...")

    if task_name:
        print(f"=== {task_name} ===")

    print(f"Your running time will be averaged over {running_times} runs.")
    print(
        "The time will allow up to "
        f"{allowed_time_multiplier}x slowdown compared to the sample implementation."
    )

    score_info = _load_task_score_info(len(testcases))

    indices: range | list[int] = range(len(testcases))
    if interactive:
        idx = _choose_case_index(len(testcases))
        if idx != -1:
            indices = [idx]

    selected_case_count = len(testcases) if isinstance(indices, range) else len(indices)
    if score_info is not None:
        task_score, per_case_score = score_info
        selected_max_score = per_case_score * selected_case_count
        print(
            f"Task score available: {task_score:.2f} total, "
            f"{per_case_score:.2f} per testcase, "
            f"{selected_max_score:.2f} for this run."
        )

    passed = failed = timing_failed = 0

    for i in indices:
        case = testcases[i]
        try:
            student, student_case, _ = _run_case(test_fn, case, is_student=True)
            sample, sample_case, _ = _run_case(test_fn, case, is_student=False)

            changed_params = find_different_parameters(
                student_case,
                sample_case,
                ignored_params=ignore_modified_args,
            )
            if changed_params:
                print(
                    f"  Case {i + 1}: ERROR - parameter(s) changed unexpectedly: "
                    f"{', '.join(changed_params)}"
                )
                failed += 1
                continue

            ok = check_fn(student, sample)
        except Exception as exc:
            print(f"  Case {i + 1}: ERROR - {exc}")
            failed += 1
            continue

        if not ok:
            print(f"  Case {i + 1}: FAIL")
            print(f"    Input:   {case}")
            print(f"    Student: {student!r}")
            print(f"    Sample:  {sample!r}")
            failed += 1
            continue

        total_student = 0.0
        for _ in range(running_times):
            _, _, elapsed = _run_case(test_fn, case, is_student=True)
            total_student += elapsed
        avg_student = total_student / running_times

        total_sample = 0.0
        for _ in range(running_times):
            _, _, elapsed = _run_case(test_fn, case, is_student=False)
            total_sample += elapsed
        avg_sample = total_sample / running_times

        if avg_student > allowed_time_multiplier * avg_sample:
            timing = (
                f"student: {_format_duration(avg_student)}, "
                f"sample: {_format_duration(avg_sample)}"
            )
            print(f"  Case {i + 1}: PASS but timing FAILED ({timing}, limit: {allowed_time_multiplier}x)")
            timing_failed += 1
        else:
            print(f"  Case {i + 1}: PASS")
        passed += 1

    total = passed + failed
    if failed == 0 and timing_failed == 0:
        print(f"All {total} case(s) passed.")
    elif failed == 0:
        print(f"All {total} case(s) correct, but {timing_failed} case(s) failed timing check.")
    else:
        print(f"{failed}/{total} case(s) failed.")
    if score_info is not None:
        _, per_case_score = score_info
        earned_score = passed * per_case_score
        selected_max_score = per_case_score * total
        print(f"Score earned: {earned_score:.2f}/{selected_max_score:.2f}")


def _run_case(test_fn: Callable, case: dict, is_student: bool):
    case_copy = copy.deepcopy(case)
    t0 = time.perf_counter()
    result = test_fn(**case_copy, is_student=is_student)
    elapsed = time.perf_counter() - t0
    return result, case_copy, elapsed


def _choose_case_index(count: int) -> int:
    width = max(1, len(str(count)))
    lines = [f"{0:{width}}: All cases"]
    lines += [f"{i:{width}}: Case {i}" for i in range(1, count + 1)]
    lines.append("Enter a number: ")
    prompt = "\n".join(lines)
    while True:
        try:
            n = int(input(prompt)) - 1
            if -1 <= n < count:
                return n
        except ValueError:
            pass
        print("Invalid input.")


def _format_duration(seconds: float) -> str:
    if seconds < 1e-3:
        return f"{seconds * 1_000_000:.3f} us"
    if seconds < 1:
        return f"{seconds * 1000:.3f} ms"
    return f"{seconds:.3f} s"


def _load_task_score_info(total_cases: int) -> tuple[float, float] | None:
    if total_cases <= 0:
        return None
    main_module = sys.modules.get("__main__")
    main_file = getattr(main_module, "__file__", None)
    if not main_file:
        return None

    test_file = Path(main_file).resolve()
    score_filename = "hidden_test_scores.json" if test_file.name.startswith("hidden_test_") else "test_scores.json"
    score_file = test_file.parent / score_filename
    if not score_file.exists():
        return None

    with score_file.open("r", encoding="utf-8") as file:
        score_map = json.load(file)

    task_score = float(score_map.get(test_file.name, 0))
    return task_score, task_score / total_cases


def check_broadcasting(func, module, allowed_import=ALLOWED_IMPORT) -> list[str]:
    """Check whether a function uses broadcasting-style NumPy code and allowed imports only."""
    violations = analyze_function(func)
    violations.extend(check_module_imports(module, allowed_import))
    return violations
