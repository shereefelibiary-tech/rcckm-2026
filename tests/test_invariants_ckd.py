from __future__ import annotations

from core.patient import Patient
from modules.kdigo.engine import classify_albuminuria_stage, classify_egfr_stage
from tests.helpers import assert_absent, assert_present, render_case_output


def test_kdigo_boundary_values_are_not_rounded_across_thresholds():
    assert classify_egfr_stage(90) == "G1"
    assert classify_egfr_stage(60) == "G2"
    assert classify_egfr_stage(59) == "G3a"
    assert classify_egfr_stage(45) == "G3a"
    assert classify_egfr_stage(44) == "G3b"
    assert classify_egfr_stage(30) == "G3b"
    assert classify_egfr_stage(29) == "G4"
    assert classify_egfr_stage(15) == "G4"
    assert classify_egfr_stage(14) == "G5"
    assert classify_albuminuria_stage(29) == "A1"
    assert classify_albuminuria_stage(30) == "A2"
    assert classify_albuminuria_stage(299) == "A2"
    assert classify_albuminuria_stage(300) == "A3"


def test_uacr_missing_is_not_rendered_as_zero_and_zero_is_not_missing():
    missing = render_case_output(Patient(age=55, sex="male", egfr=80, uacr=None))["outputs"]["visible"]
    zero = render_case_output(Patient(age=55, sex="male", egfr=80, uacr=0))["outputs"]["visible"]
    assert "UACR 0" not in missing
    assert "albuminuria not measured" in missing
    assert "UACR 0" in zero or "0 mg/g" in zero
    assert "albuminuria not measured" not in zero


def test_albuminuria_surfaces_kidney_risk_and_specific_actions():
    bundle = render_case_output(
        Patient(
            age=57,
            sex="male",
            tc=202,
            ldl_c=126,
            hdl_c=46,
            triglycerides=150,
            sbp=142,
            dbp=86,
            bp_treated=True,
            egfr=64,
            uacr=48,
            a1c=6.0,
            diabetes=False,
            prevent_10y_ascvd=6.65,
            prevent_30y_ascvd=26.07,
        )
    )
    text = bundle["outputs"]["visible"]
    assert_present(
        text,
        (
            "G2A2",
            "Confirm persistent albuminuria",
            "ACEi/ARB",
            "Treat BP toward goal <130/80",
        ),
    )
    assert_absent(text, ("normal kidney function", "No medication escalation today"))


def test_sglt2_strong_soft_and_low_egfr_paths_are_distinct():
    strong = render_case_output(Patient(age=64, sex="male", egfr=55, uacr=220, ace_arb=True))["outputs"]["actions"]
    soft = render_case_output(Patient(age=64, sex="male", egfr=55, uacr=80, diabetes=False, ace_arb=True))["outputs"]["actions"]
    low_egfr = render_case_output(Patient(age=64, sex="male", egfr=18, uacr=350, ace_arb=True))["outputs"]["actions"]
    assert "Add an SGLT2 inhibitor" in strong
    assert "Consider SGLT2 inhibitor" in soft
    assert "Add an SGLT2 inhibitor" not in low_egfr
    assert "not routinely recommended at this eGFR" in low_egfr


def test_prediabetes_albuminuria_does_not_become_diabetic_kidney_disease():
    bundle = render_case_output(Patient(age=56, sex="female", a1c=6.1, diabetes=False, egfr=62, uacr=55))
    assert "Prediabetes" in bundle["outputs"]["diagnoses"]
    assert "Type 2 diabetes mellitus with CKD" not in bundle["outputs"]["diagnoses"]


def test_diabetes_with_albuminuria_surfaces_linked_kidney_context():
    bundle = render_case_output(Patient(age=60, sex="female", diabetes=True, a1c=7.2, egfr=52, uacr=210))
    text = bundle["outputs"]["visible"]
    assert "Type 2 diabetes mellitus with CKD" in text
    assert "G3aA2" in text
