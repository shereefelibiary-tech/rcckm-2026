from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _run(label: str, args: list[str]) -> int:
    print(f"\n== {label} ==")
    completed = subprocess.run(args, cwd=ROOT)
    if completed.returncode:
        print(f"{label} failed with exit code {completed.returncode}")
    return completed.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run RCCKM layered validation.")
    parser.add_argument("--fuzz-n", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args(argv)

    python = sys.executable
    steps = [
        (
            "parser fixtures",
            [python, "-m", "tools.parser_regression"],
        ),
        (
            "golden cases",
            [python, "-m", "pytest", "tests/golden_cases/test_golden_cases.py"],
        ),
        (
            "boundary tests",
            [python, "-m", "pytest", "tests/test_boundaries.py"],
        ),
        (
            "invariants",
            [python, "-m", "pytest", "tests/test_invariants.py", "tests/invariants"],
        ),
        (
            "snapshot contracts",
            [python, "-m", "pytest", "tests/snapshots"],
        ),
        (
            "parser safety",
            [
                python,
                "-m",
                "pytest",
                "tests/test_parser_safety.py",
                "tests/test_parser_medications.py",
                "tests/test_parser_emr_styles.py",
                "tests/test_missing_vs_zero.py",
                "tests/test_parser_apply_to_worksheet.py",
            ],
        ),
        (
            "fuzz sample",
            [
                python,
                "-m",
                "tools.fuzz_rcckm",
                "--n",
                str(args.fuzz_n),
                "--seed",
                str(args.seed),
            ],
        ),
    ]

    failures = 0
    for label, command in steps:
        failures += int(_run(label, command) != 0)

    if failures:
        print(f"\nValidation complete: {failures} layer(s) failed.")
        return 1

    print("\nValidation complete: all layers passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
