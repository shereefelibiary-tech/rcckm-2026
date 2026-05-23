import json
from pathlib import Path

import pytest

from smartphrase_ingest.parser import detect_source_style, parse_smartphrase_report


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "ingest"


def _matches_expected(actual, expected) -> bool:
    if isinstance(expected, float):
        return float(actual) == pytest.approx(expected, abs=0.01)
    if isinstance(expected, str) and "father mi age" in expected.lower():
        return str(actual).lower() == expected.lower()
    return actual == expected


@pytest.mark.parametrize("text_path", sorted(FIXTURE_DIR.glob("*.txt")))
def test_emr_style_fixtures_parse_expected_normalized_fields(text_path):
    expected_path = text_path.with_name(text_path.stem + ".expected.json")
    expected = json.loads(expected_path.read_text(encoding="utf-8-sig"))
    report = parse_smartphrase_report(text_path.read_text(encoding="utf-8"))

    assert report.source_style == expected["source_style"]
    assert detect_source_style(text_path.read_text(encoding="utf-8")) == expected["source_style"]

    for field, value in expected["extracted"].items():
        assert field in report.extracted, f"{text_path.name}: missing {field}"
        assert _matches_expected(report.extracted[field], value), (
            f"{text_path.name}: {field} {report.extracted[field]!r} != {value!r}"
        )
