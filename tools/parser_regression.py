from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from smartphrase_ingest.parser import parse_smartphrase_report  # noqa: E402


FIXTURE_DIR = ROOT / "tests" / "fixtures" / "ingest"


def _same(actual: Any, expected: Any) -> bool:
    if isinstance(expected, float):
        try:
            return abs(float(actual) - expected) <= 0.01
        except (TypeError, ValueError):
            return False
    if isinstance(expected, str) and "father mi age" in expected.lower():
        return str(actual).lower() == expected.lower()
    return actual == expected


def _run_fixture(text_path: Path) -> tuple[bool, list[str], dict[str, Any]]:
    expected_path = text_path.with_name(text_path.stem + ".expected.json")
    expected = json.loads(expected_path.read_text(encoding="utf-8-sig"))
    report = parse_smartphrase_report(text_path.read_text(encoding="utf-8"))
    errors: list[str] = []

    if report.source_style != expected["source_style"]:
        errors.append(f"source_style {report.source_style!r} != {expected['source_style']!r}")

    for field, expected_value in expected["extracted"].items():
        if field not in report.extracted:
            errors.append(f"missing {field}")
            continue
        if not _same(report.extracted[field], expected_value):
            errors.append(f"{field}: {report.extracted[field]!r} != {expected_value!r}")

    summary = {
        "source_style": report.source_style,
        "fields_parsed": sorted(report.extracted.keys()),
        "warnings": list(report.warnings),
        "conflicts": list(report.conflicts),
    }
    return not errors, errors, summary


def main() -> int:
    if not FIXTURE_DIR.exists():
        print(f"Missing fixture directory: {FIXTURE_DIR}")
        return 2

    passed = 0
    failed = 0
    all_fields: set[str] = set()

    for text_path in sorted(FIXTURE_DIR.glob("*.txt")):
        ok, errors, summary = _run_fixture(text_path)
        all_fields.update(summary["fields_parsed"])
        status = "PASS" if ok else "FAIL"
        print(f"{status} {text_path.name} [{summary['source_style']}]")
        print(f"  fields parsed ({len(summary['fields_parsed'])}): {', '.join(summary['fields_parsed'])}")
        if summary["warnings"]:
            print(f"  warnings: {' | '.join(summary['warnings'])}")
        if summary["conflicts"]:
            print(f"  conflicts: {' | '.join(summary['conflicts'])}")
        for error in errors:
            print(f"  ERROR: {error}")
        if ok:
            passed += 1
        else:
            failed += 1

    print("")
    print(f"Parser fixture summary: {passed} passed, {failed} failed")
    print(f"Coverage fields ({len(all_fields)}): {', '.join(sorted(all_fields))}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
