import json
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


def discover_test_files(test_dir: Path, score_map: dict[str, int]) -> list[Path]:
    return sorted(
        path
        for path in test_dir.glob("test_*.py")
        if path.name != "test_all.py" and score_map.get(path.name, 0) > 0
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
    status = classify_file(completed.returncode, parsed)
    return {
        "name": path.name,
        "status": status,
        "returncode": completed.returncode,
        "output": output,
        "cases": parsed["cases"],
        "total": parsed["summary"]["total"],
    }


def format_case_list(case_ids: list[int]) -> str:
    return ", ".join(str(case_id) for case_id in case_ids) if case_ids else "-"


def load_scores(test_dir: Path) -> dict[str, int]:
    with (test_dir / "test_scores.json").open("r", encoding="utf-8") as file:
        return json.load(file)


def compute_file_score(file_score: float, passed_cases: int, total_cases: int) -> tuple[float, float]:
    if total_cases <= 0:
        return 0.0, 0.0
    per_case_score = file_score / total_cases
    return passed_cases * per_case_score, per_case_score


def main() -> None:
    test_dir = Path(__file__).resolve().parent
    score_map = load_scores(test_dir)
    test_files = discover_test_files(test_dir, score_map)
    results = []

    counts = {"crash": 0, "failed": 0, "timing_failed": 0, "passed": 0}
    total_cases = {"passed": 0, "failed": 0, "timing_failed": 0, "crash": 0}
    total_score = 0.0
    total_max_score = 0.0

    print("=" * 72)
    print(f"Testing {len(test_files)} test file(s) in {test_dir.name}")
    print("=" * 72)

    for path in test_files:
        print(f"Testing {path.name}: ", end='', flush=True)
        result = run_test_file(path)
        file_score = score_map.get(path.name, 0)
        result["max_score"] = file_score
        result["score"], result["per_case_score"] = compute_file_score(
            file_score=file_score,
            passed_cases=len(result["cases"]["passed"]),
            total_cases=result["total"],
        )
        results.append(result)
        counts[result["status"]] += 1
        total_cases["passed"] += len(result["cases"]["passed"])
        total_cases["failed"] += len(result["cases"]["failed"])
        total_cases["timing_failed"] += len(result["cases"]["timing_failed"])
        total_cases["crash"] += len(result["cases"]["crash"])
        total_score += result["score"]
        total_max_score += result["max_score"]

        print(
            f"{result['status'].upper()}, "
            f"score={result['score']:.2f}/{result['max_score']:.2f}\n"
            f"cases: "
            f"pass={len(result['cases']['passed'])} "
            f"fail={len(result['cases']['failed'])} "
            f"timing={len(result['cases']['timing_failed'])} "
            f"crash={len(result['cases']['crash'])} "
            f"total={result['total']} "
            f"per_pass_case={result['per_case_score']:.2f}\n"
        )

    print("\n" + "=" * 72)
    print("SUMMARY")
    print(f"Files passed: {counts['passed']}")
    print(f"Files timing_failed: {counts['timing_failed']}")
    print(f"Files failed: {counts['failed']}")
    print(f"Files crashed: {counts['crash']}")
    print(f"Case passed: {total_cases['passed']}")
    print(f"Case timing_failed: {total_cases['timing_failed']}")
    print(f"Case failed: {total_cases['failed']}")
    print(f"Case crashed: {total_cases['crash']}")
    print(f"Score: {total_score:.2f}/{total_max_score:.2f}")
    print("=" * 72)

    problem_results = [r for r in results if r["status"] != "passed"]
    if problem_results:
        print("PROBLEMS")
        for result in problem_results:
            print(f"{result['name']} [{result['status'].upper()}]")
            if result["status"] == "crash" and not result["cases"]["crash"]:
                stderr_line = ""
                if "[stderr]" in result["output"]:
                    stderr_line = result["output"].split("[stderr]", 1)[1].strip().splitlines()[0]
                print(f"  crash: {stderr_line or 'subprocess failed before case summary'}")
            else:
                if result["cases"]["crash"]:
                    print(f"  crash cases: {format_case_list(result['cases']['crash'])}")
                if result["cases"]["failed"]:
                    print(f"  failed cases: {format_case_list(result['cases']['failed'])}")
                if result["cases"]["timing_failed"]:
                    print(f"  timing_failed cases: {format_case_list(result['cases']['timing_failed'])}")
        print("=" * 72)


if __name__ == "__main__":
    main()
