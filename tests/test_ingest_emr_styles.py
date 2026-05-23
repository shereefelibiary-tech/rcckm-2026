import json
from pathlib import Path

import pytest

from core.patient import Patient
from core.results import RCCKMResult
from modules.actions.engine import build_action_plan
from smartphrase_ingest.parser import detect_source_style, parse_smartphrase_report
from ui.ingest_panel import apply_parsed_to_session_state, parse_ingest_report


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "ingest"


def _fixture_stems():
    return sorted(path.stem for path in FIXTURE_DIR.glob("*.txt"))


def _assert_value(actual, expected):
    if isinstance(expected, float):
        assert actual is not None
        assert float(actual) == pytest.approx(expected, abs=0.01)
    elif isinstance(expected, str) and "father mi age" in expected.lower():
        assert str(actual).lower() == expected.lower()
    else:
        assert actual == expected


@pytest.mark.parametrize("stem", _fixture_stems())
def test_emr_style_fixture_parses_expected_fields(stem):
    text = (FIXTURE_DIR / f"{stem}.txt").read_text(encoding="utf-8")
    expected = json.loads((FIXTURE_DIR / f"{stem}.expected.json").read_text(encoding="utf-8-sig"))

    report = parse_smartphrase_report(text)

    assert report.source_style == expected["source_style"]
    assert detect_source_style(text) == expected["source_style"]
    assert isinstance(report.extracted, dict)
    assert isinstance(report.warnings, list)
    assert isinstance(report.conflicts, list)

    for field, expected_value in expected["extracted"].items():
        assert field in report.extracted, f"{stem}: missing {field}"
        _assert_value(report.extracted[field], expected_value)
        assert field in report.field_meta, f"{stem}: missing metadata for {field}"
        assert report.field_meta[field].get("confidence") in {
            "parsed",
            "inferred",
            "uncertain",
            "not found",
        }


def test_a1c_reference_range_does_not_falsely_trigger_diabetes():
    report = parse_smartphrase_report(
        "A1c reference range: diabetes >=6.5; prediabetes 5.7-6.4."
    )

    assert "a1c" not in report.extracted
    assert "diabetes" not in report.extracted


def test_lpa_units_mgdl_and_nmol_are_preserved():
    nmol = parse_smartphrase_report("Lp(a) 180 nmol/L")
    mgdl = parse_smartphrase_report("Lp(a): 65 mg/dL")

    assert nmol.extracted["lpa"] == 180
    assert nmol.extracted["lpa_unit"] == "nmol/L"
    assert mgdl.extracted["lpa"] == 65
    assert mgdl.extracted["lpa_unit"] == "mg/dL"


def test_uacr_and_egfr_unavailable_reasons_are_preserved():
    report = parse_smartphrase_report(
        "eGFR not available due to hemolyzed specimen. UACR unavailable because urine not collected."
    )

    assert "egfr" in report.field_meta
    assert "uacr" in report.field_meta
    assert report.field_meta["egfr"]["confidence"] == "not found"
    assert report.field_meta["uacr"]["confidence"] == "not found"
    assert any("eGFR unavailable" in warning for warning in report.warnings)
    assert any("UACR unavailable" in warning for warning in report.warnings)


def test_cac_not_done_does_not_become_zero():
    report = parse_smartphrase_report("CAC not done; coronary calcium deferred.")

    assert "cac" in report.extracted
    assert report.extracted["cac"] is None
    assert report.field_meta["cac"]["confidence"] == "not found"


def test_family_history_does_not_become_clinical_ascvd():
    report = parse_smartphrase_report("Family history: Father MI age 49. No clinical ASCVD.")

    assert report.extracted["fhx"] is True
    assert report.extracted.get("ascvd_clinical") is False


def test_clinical_ascvd_does_not_trigger_from_family_history_stroke_line():
    report = parse_smartphrase_report("Mother stroke age 61. Patient denies ASCVD.")

    assert report.extracted["fhx"] is True
    assert report.extracted.get("ascvd_clinical") is False


def test_nonfasting_tg_400_triggers_repeat_fasting_clarifier():
    report = parse_smartphrase_report("Nonfasting lipid panel: TG 420.")
    patient = Patient(age=55, sex="male", triglycerides=report.extracted["tg"])

    assert report.extracted["fasting_lipids"] is False
    plan = build_action_plan(patient, RCCKMResult())
    assert "fasting_lipids" in plan["domains"]


def test_no_diabetes_with_a1c_diabetes_range_creates_conflict():
    report = parse_smartphrase_report("No diabetes. A1c 7.1.")

    assert report.extracted["diabetes"] is False
    assert any("A1c is >=6.5" in conflict for conflict in report.conflicts)


def test_stopped_statin_does_not_count_as_active_lipid_lowering():
    report = parse_smartphrase_report("Stopped atorvastatin last year. No lipid lowering therapy.")

    assert report.extracted["lipidLowering"] is False
    assert "medications_raw" not in report.extracted


def test_parse_ingest_report_normalizes_fields_and_keeps_source_style():
    report = parse_ingest_report("Cerner PowerChart synthetic. 55M BP 132/82 LDL 132 Lp(a) 80 nmol/L.")

    assert report["source_style"] == "cerner"
    assert report["parsed"]["ldl_c"] == 132
    assert report["parsed"]["lp_a_value"] == 80
    assert report["parsed"]["lp_a_unit"] == "nmol/L"


def test_manual_override_wins_after_parser_populates_session_state():
    state = {"input_ldl_c": 140}
    apply_parsed_to_session_state(state, {"ldl_c": 132, "apob": 110})
    state["input_ldl_c"] = 145

    assert state["input_apob"] == 110
    assert state["input_ldl_c"] == 145
