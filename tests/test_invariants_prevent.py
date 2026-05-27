from __future__ import annotations

from core.patient import Patient
from modules.prevent.engine import classify_prevent_ascvd_risk
from modules.prevent.lipid_bands import LOW_10YR_HIGH_30YR_PATIENT_SUMMARY
from tests.helpers import (
    assert_absent,
    assert_present,
    assert_risk_labels_valid,
    render_case_output,
)


def test_prevent_ascvd_risk_band_boundaries_are_stable():
    assert classify_prevent_ascvd_risk(2.99).value == "LOW"
    assert classify_prevent_ascvd_risk(3.00).value == "BORDERLINE"
    assert classify_prevent_ascvd_risk(4.99).value == "BORDERLINE"
    assert classify_prevent_ascvd_risk(5.00).value == "INTERMEDIATE"
    assert classify_prevent_ascvd_risk(9.99).value == "INTERMEDIATE"
    assert classify_prevent_ascvd_risk(10.00).value == "HIGH"


def test_ascvd_outputs_are_labeled_by_type_and_time_horizon():
    bundle = render_case_output(
        Patient(
            age=56,
            sex="male",
            tc=205,
            ldl_c=130,
            hdl_c=45,
            triglycerides=160,
            sbp=128,
            dbp=76,
            diabetes=False,
            smoker=False,
            bp_treated=False,
            prevent_10y_ascvd=6.2,
            prevent_30y_ascvd=22.4,
        )
    )
    text = bundle["outputs"]["visible"]
    assert_present(text, ("10-year ASCVD risk", "30-year ASCVD risk"))
    assert_absent(text, ("total cardiovascular risk", "heart failure risk"))
    assert_risk_labels_valid(bundle)


def test_patient_roadmap_defines_ascvd_in_plain_language():
    bundle = render_case_output(
        Patient(
            age=61,
            sex="female",
            tc=218,
            ldl_c=124,
            hdl_c=56,
            triglycerides=190,
            sbp=138,
            dbp=84,
            diabetes=False,
            smoker=False,
            bp_treated=True,
            prevent_10y_ascvd=10.16,
            prevent_30y_ascvd=30.65,
            cac=350,
        )
    )
    roadmap = bundle["outputs"]["roadmap"]
    assert_present(
        roadmap,
        (
            "10-year ASCVD risk",
            "30-year ASCVD risk",
            "heart attack, stroke, or related artery disease event",
            "About 10 in 100",
            "About 31 in 100",
        ),
    )
    assert_absent(roadmap, ("total cardiovascular risk", "heart failure risk"))


def test_unavailable_prevent_does_not_fabricate_percentages():
    bundle = render_case_output(Patient(age=52, sex="female", ldl_c=132, triglycerides=150))
    text = bundle["outputs"]["visible"]
    assert "unavailable" in text.lower() or "missing" in text.lower()
    assert "10-year ASCVD risk: 0" not in text
    assert "30-year ASCVD risk: 0" not in text


def test_total_cvd_values_can_display_only_with_distinct_labeling():
    bundle = render_case_output(
        Patient(
            age=58,
            sex="male",
            tc=210,
            ldl_c=132,
            hdl_c=44,
            triglycerides=150,
            sbp=130,
            dbp=80,
            diabetes=False,
            smoker=False,
            bp_treated=False,
            prevent_10y_ascvd=4.5,
            prevent_30y_ascvd=18.0,
            prevent_10y_total_cvd=8.0,
            prevent_30y_total_cvd=30.0,
        )
    )
    prevent = bundle["outputs"]["prevent"]
    assert "Atherosclerotic event risk" in prevent
    assert "Cardiovascular event risk" in prevent
    assert "Heart failure risk" not in prevent


def test_low_10_year_high_30_year_patient_roadmap_uses_standard_summary():
    bundle = render_case_output(
        Patient(
            age=38,
            sex="male",
            tc=220,
            ldl_c=154,
            hdl_c=46,
            triglycerides=165,
            apob=112,
            family_history_premature_ascvd=True,
            prevent_10y_ascvd=3.8,
            prevent_30y_ascvd=24.0,
        )
    )
    roadmap = bundle["outputs"]["roadmap"]
    assert LOW_10YR_HIGH_30YR_PATIENT_SUMMARY in roadmap
    assert_absent(roadmap, ("high near-term risk", "event likely soon", "total cardiovascular risk", "heart failure risk"))
