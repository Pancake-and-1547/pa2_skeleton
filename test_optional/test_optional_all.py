import re
import subprocess
import sys
from pathlib import Path


CASE_PATTERN = re.compile(r"Case (\d+): (.+)")
SUMMARY_PATTERNS = {
    "all_passed": re.compile(r"All (\d+) case\(s\) passed\."),
    "failed": re.compile(r"(\d+)/(\d+) case\(s\) failed\."),
    "timing_failed": re.compile(r"All (\d+) case\(s\) correct, but (\d+) case\(s\) failed timing check\."),
}


def discover_test_files(test_dir: Path) -> list[Path]:
    return sorted(
        path for path in test_dir.glob("test_*.py") if path.name != "test_optional_all.py"
    )


def parse_output(output: str) -> dict:
    cases = {"passed": [], "failed": [], "timing_failed": [], "crash": []}
    for line in output.splitlines():
        match = CASE_PATTERN.search(line)
        if not match:
            continue
        case_id = int(match.group(1))
        message = match.group(2)
        if message.startswith("ERROR"):
            cases["crash"].append(case_id)
        elif message.startswith("FAIL"):
            cases["failed"].append(case_id)
        elif "timing FAILED" in message:
            cases["timing_failed"].append(case_id)
        elif message.startswith("PASS"):
            cases["passed"].append(case_id)

    parsed_summary = {"total": 0}
    for kind, pattern in SUMMARY_PATTERNS.items():
        match = pattern.search(output)
        if not match:
            continue
        if kind == "all_passed":
            parsed_summary["total"] = int(match.group(1))
        elif kind == "failed":
            parsed_summary["total"] = int(match.group(2))
        elif kind == "timing_failed":
            parsed_summary["total"] = int(match.group(1))
        break

    return {"cases": cases, "summary": parsed_summary}


def classify_file(returncode: int, parsed: dict) -> str:
    cases = parsed["cases"]
    if returncode != 0 or not parsed["summary"]["total"]:
        return "crash"
    if cases["crash"]:
        return "crash"
    if cases["failed"]:
        return "failed"
    if cases["timing_failed"]:
        return "timing_failed"
    return "passed"


def run_test_file(path: Path) -> dict:
    completed = subprocess.run(
        [sys.executable, str(path)],
        input="0\n",
        text=True,
        capture_output=True,
        cwd=path.parent.parent,
    )
    output = completed.stdout
    if completed.stderr:
        output = f"{output}\n[stderr]\n{completed.stderr}".strip()
    parsed = parse_output(output)
    return {
        "name": path.name,
        "status": classify_file(completed.returncode, parsed),
        "output": output,
        "cases": parsed["cases"],
        "total": parsed["summary"]["total"],
    }


def format_case_list(case_ids: list[int]) -> str:
    return ", ".join(str(case_id) for case_id in case_ids) if case_ids else "-"


def main() -> None:
    test_dir = Path(__file__).resolve().parent
    test_files = discover_test_files(test_dir)
    results = []
    counts = {"crash": 0, "failed": 0, "timing_failed": 0, "passed": 0}

    print("=" * 72)
    print(f"Testing {len(test_files)} optional test file(s) in {test_dir.name}")
    print("=" * 72)

    for path in test_files:
        print(f"Testing {path.name}: ", end="", flush=True)
        result = run_test_file(path)
        results.append(result)
        counts[result["status"]] += 1
        print(
            f"{result['status'].upper()}\n"
            f"cases: "
            f"pass={len(result['cases']['passed'])} "
            f"fail={len(result['cases']['failed'])} "
            f"timing={len(result['cases']['timing_failed'])} "
            f"crash={len(result['cases']['crash'])} "
            f"total={result['total']}\n"
        )

    print("\n" + "=" * 72)
    print("SUMMARY")
    print(f"Files passed: {counts['passed']}")
    print(f"Files timing_failed: {counts['timing_failed']}")
    print(f"Files failed: {counts['failed']}")
    print(f"Files crashed: {counts['crash']}")
    print("=" * 72)

    problem_results = [result for result in results if result["status"] != "passed"]
    if problem_results:
        print("PROBLEMS")
        for result in problem_results:
            print(f"{result['name']} [{result['status'].upper()}]")
            if result["cases"]["crash"]:
                print(f"  crash cases: {format_case_list(result['cases']['crash'])}")
            if result["cases"]["failed"]:
                print(f"  failed cases: {format_case_list(result['cases']['failed'])}")
            if result["cases"]["timing_failed"]:
                print(f"  timing_failed cases: {format_case_list(result['cases']['timing_failed'])}")
        print("=" * 72)


if __name__ == "__main__":
    main()
