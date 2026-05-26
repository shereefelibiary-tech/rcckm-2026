from __future__ import annotations

from core.patient import Patient
from core.engine import evaluate_patient
from rcckm.governance import validate_output_safety
from tests.helpers import render_all_outputs


def _visible(patient_dict):
    patient = Patient(**patient_dict)
    result = evaluate_patient(patient)
    return patient, result, render_all_outputs(patient, result)["visible"]


def test_actionable_therapy_never_pairs_with_no_medication_escalation():
    patient, result, text = _visible(
        {
            "age": 57,
            "sex": "male",
            "prevent_10y_ascvd": 6.65,
            "prevent_30y_ascvd": 26.07,
            "egfr": 76,
            "uacr": 62,
            "sbp": 142,
            "dbp": 86,
            "bp_treated": True,
            "a1c": 6.0,
            "triglycerides": 150,
        }
    )
    assert "No medication escalation today" not in text
    assert not validate_output_safety(patient, result, text)


def test_prevent_terminology_does_not_mix_ascvd_total_cvd_or_hf():
    patient, result, text = _visible(
        {
            "age": 48,
            "sex": "male",
            "sbp": 136,
            "dbp": 86,
            "tc": 212,
            "hdl_c": 39,
            "ldl_c": 132,
            "triglycerides": 205,
            "diabetes": False,
            "smoker": False,
            "bp_treated": False,
        }
    )
    assert "10-year ASCVD risk" in text
    assert "total cardiovascular risk" not in text.lower()
    assert "heart failure" not in text.lower()
    assert not validate_output_safety(patient, result, text)


def test_plaque_kidney_diabetes_and_aspirin_never_cross_rules():
    patient, result, text = _visible({"age": 55, "sex": "male", "cac": 0, "a1c": 6.1, "uacr": 0})
    assert "Subclinical coronary atherosclerosis" not in text
    assert "CAC not performed" not in text
    assert "Type 2 diabetes mellitus" not in text
    assert not validate_output_safety(patient, result, text)

    patient, result, text = _visible({"age": 55, "sex": "male", "cac": 300, "cac_percentile": 35})
    assert "mild plaque" not in text.lower()
    assert "within the expected range for age and sex" not in text.lower()
    assert not validate_output_safety(patient, result, text)


def test_sglt2_strong_wording_requires_strong_criteria():
    patient, result, text = _visible({"age": 57, "sex": "male", "egfr": 76, "uacr": 62, "diabetes": False})
    assert "Add an SGLT2 inhibitor" not in text
    assert not validate_output_safety(patient, result, text)

    bad_findings = validate_output_safety(patient, result, text + "\nAdd an SGLT2 inhibitor now.")
    assert any("Strong SGLT2" in finding.message for finding in bad_findings)

