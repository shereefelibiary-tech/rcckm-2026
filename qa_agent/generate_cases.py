from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from qa_agent.synthetic_patient_generator import PHENOTYPES, generate_patient, write_case


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = ROOT / "generated_cases"


def _case_id(index: int, phenotype: str) -> str:
    return f"synthetic_{index:03d}_{phenotype}"


def generate_cases(
    *,
    count: int,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    phenotype: str | None = None,
    seed: int = 20260601,
) -> list[dict]:
    cases = []
    for index in range(1, count + 1):
        selected = phenotype or PHENOTYPES[(index - 1) % len(PHENOTYPES)]
        case = generate_patient(
            case_id=_case_id(index, selected),
            phenotype=selected,
            seed=seed + index,
        )
        json_path, txt_path = write_case(case, output_dir)
        cases.append(
            {
                "case_id": case.case_id,
                "phenotype": case.phenotype,
                "patient_json": str(json_path),
                "smartphrase_text": str(txt_path),
            }
        )
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(cases, indent=2), encoding="utf-8")
    return cases


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate synthetic RCCKM QA patients.")
    parser.add_argument("--count", type=int, default=10, help="Number of cases to generate.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for generated JSON and SmartPhrase files.",
    )
    parser.add_argument(
        "--phenotype",
        choices=PHENOTYPES,
        default=None,
        help="Generate only one phenotype. Default cycles through all phenotypes.",
    )
    parser.add_argument("--seed", type=int, default=20260601)
    args = parser.parse_args(argv)

    if args.count < 1:
        parser.error("--count must be at least 1")

    cases = generate_cases(
        count=args.count,
        output_dir=args.output_dir,
        phenotype=args.phenotype,
        seed=args.seed,
    )
    counts = {name: 0 for name in PHENOTYPES}
    for case in cases:
        counts[case["phenotype"]] += 1

    print(f"generated: {len(cases)}")
    print(f"output_dir: {args.output_dir}")
    for name in PHENOTYPES:
        if counts[name]:
            print(f"{name}: {counts[name]}")
    print(f"manifest: {args.output_dir / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
