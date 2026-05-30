from pathlib import Path

from smartphrase_ingest.pipeline import parse_to_draft
from smartphrase_ingest.resolver import to_patient


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "ingest"


def test_epic_placeholder_fixture_parses_through_staged_pipeline():
    draft = parse_to_draft(
        (FIXTURE_DIR / "epic_placeholder_garbage_smartphrase.txt").read_text(
            encoding="utf-8"
        )
    )

    resolved = draft.resolved
    assert draft.source_system == "epic"
    assert draft.raw_text_hash
    assert resolved["age"] == 73
    assert resolved["sex"] == "male"
    assert resolved["smoker"] is False
    assert resolved["former_smoker"] is True
    assert resolved["pack_years"] == 2.8
    assert resolved["sbp"] == 132
    assert resolved["dbp"] == 77
    assert resolved["bmi"] == 30.81
    assert resolved["tc"] == 198
    assert resolved["triglycerides"] == 323
    assert resolved["hdl_c"] == 44
    assert resolved["ldl_c"] == 90
    assert resolved["a1c"] == 5.8
    assert resolved["diabetes"] is False
    assert resolved["prediabetes_context"] is True
    assert resolved["egfr"] == 71
    assert "uacr" not in resolved
    assert "apob" not in resolved
    assert "lp_a_value" not in resolved
    assert "hscrp" not in resolved
    assert "cac" not in resolved
    assert "premature_fhx_ascvd" not in resolved
    assert resolved["bp_treated"] is True
    assert resolved["ace_arb"] is True

    assert "ApoB not available" in draft.review_flags
    assert "Lp(a) not available" in draft.review_flags
    assert "UACR not available" in draft.review_flags
    assert "CAC not measured" in draft.review_flags
    assert "Family history unknown" in draft.review_flags
    assert "BMI parsed from calculated text" in draft.review_flags
    assert "Multiple BP readings detected; most recent selected" in draft.review_flags
    assert "A1c reference table ignored" in draft.review_flags
    assert {"apob", "lp_a_value", "uacr", "cac", "premature_fhx_ascvd"}.issubset(
        set(draft.missing_fields)
    )


def test_pipeline_candidates_preserve_source_evidence_and_confidence():
    draft = parse_to_draft(
        (FIXTURE_DIR / "epic_placeholder_garbage_smartphrase.txt").read_text(
            encoding="utf-8"
        )
    )

    bmi_candidate = draft.candidates["bmi"][0]
    assert bmi_candidate.value == 30.81
    assert bmi_candidate.source_text == "Estimated body mass index is 30.81 kg/m2."
    assert bmi_candidate.confidence == 0.9
    assert bmi_candidate.reason == "calculated BMI prose"

    a1c_candidate = draft.candidates["a1c"][0]
    assert a1c_candidate.value == 5.8
    assert "04/24/2026 5.8" in a1c_candidate.source_text
    assert a1c_candidate.confidence == 0.95

    egfr_sources = {candidate.source_text for candidate in draft.candidates["egfr"]}
    assert "LABGLOM 71" in egfr_sources
    assert "eGFR Cre 71" in egfr_sources
    assert all("Creatinine clearance" not in text for text in egfr_sources)


def test_pipeline_to_patient_uses_resolved_high_confidence_values_only():
    draft = parse_to_draft(
        (FIXTURE_DIR / "epic_placeholder_garbage_smartphrase.txt").read_text(
            encoding="utf-8"
        )
    )

    patient = to_patient(draft)

    assert patient.age == 73
    assert patient.sex == "male"
    assert patient.smoker is False
    assert patient.sbp == 132
    assert patient.dbp == 77
    assert patient.bmi == 30.81
    assert patient.a1c == 5.8
    assert patient.diabetes is False
    assert patient.egfr == 71
    assert patient.uacr is None
    assert patient.apob is None
    assert patient.lp_a_value is None
    assert patient.cac is None
    assert patient.bp_treated is True
    assert patient.ace_arb is True
