from __future__ import annotations

from core.patient import Patient
from tests.helpers import assert_absent, assert_no_contradictions, assert_present, render_case_output


ROADMAP_FORBIDDEN = (
    "<div",
    "</div>",
    "<span",
    "</span>",
    "ICD:",
    "HCC",
    "RAF",
    "phenotype",
    "inherited risk",
    "genetics",
    "dominant_action",
    "action_domains",
    "risk_continuum_sublevel",
    "treatment posture",
    "risk enhancer",
    "pharmacotherapy",
    "None",
    "null",
    "NaN",
    "interpreted with the overall risk picture",
    "reviewed as part of the prevention plan",
    "does not show an immediate action signal",
    "No immediate blood sugar action is shown",
    "Targets to review with your clinician",
    "management as appropriate",
    "incomplete",
    "deficiency",
    "deficient",
    "failed",
    "overdue",
    "should have",
    "missing ApoB",
    "missing CAC",
    "missing UACR",
)


def test_patient_roadmap_has_required_sections_and_no_clinician_only_artifacts():
    roadmap = render_case_output(
        Patient(
            age=61,
            sex="female",
            tc=218,
            ldl_c=124,
            hdl_c=56,
            triglycerides=190,
            cac=350,
            prevent_10y_ascvd=10.16,
            prevent_30y_ascvd=30.65,
        )
    )["outputs"]["roadmap"]
    assert_present(
        roadmap,
        (
            "STEP 1",
            "Where you stand",
            "STEP 2",
            "Why your risk is higher",
            "STEP 3",
            "Your goals",
            "STEP 4",
            "Your next steps",
        ),
    )
    assert_absent(roadmap, ROADMAP_FORBIDDEN)
    assert_no_contradictions(roadmap)


def test_patient_roadmap_defines_artery_disease_risk_plainly():
    roadmap = render_case_output(
        Patient(age=55, sex="male", prevent_10y_ascvd=8.4, prevent_30y_ascvd=24.0, ldl_c=132)
    )["outputs"]["roadmap"]
    assert "ASCVD risk" in roadmap
    assert "heart attack, stroke, or related artery disease event" in roadmap
    assert "total cardiovascular risk" not in roadmap
    assert "heart failure risk" not in roadmap


def test_patient_roadmap_plaque_and_kidney_status_do_not_cross():
    plaque = render_case_output(Patient(age=60, sex="male", cac=38))["outputs"]["roadmap"]
    kidney = render_case_output(Patient(age=57, sex="male", egfr=64, uacr=48))["outputs"]["roadmap"]
    assert "plaque unmeasured" not in plaque.lower()
    assert "no calcified coronary plaque detected" not in plaque.lower()
    assert "Kidney" in kidney or "kidney" in kidney
    assert "normal kidney" not in kidney.lower()


def test_patient_roadmap_prioritizes_concise_next_steps():
    roadmap = render_case_output(Patient(age=60, sex="female", diabetes=True, egfr=52, uacr=210, ldl_c=132))["outputs"]["roadmap"]
    next_step_lines = [
        line
        for line in roadmap.splitlines()
        if line.strip().startswith(("1.", "2.", "3.", "4.", "5."))
    ]
    assert 1 <= len(next_step_lines) <= 5
    assert all(len(line) < 220 for line in next_step_lines)


def test_patient_roadmap_low_risk_old_egfr_missing_uacr_is_specific():
    roadmap = render_case_output(
        Patient(
            age=52,
            sex="female",
            ldl_c=97,
            hdl_c=62,
            triglycerides=80,
            a1c=5.4,
            egfr=55,
            uacr=None,
            sbp=105,
            dbp=71,
            prevent_10y_ascvd=2.1,
        )
    )["outputs"]["roadmap"]

    assert "A1c: 5.4% to normal range" in roadmap
    assert "BP: 105/71 mmHg to <130/80" in roadmap
    assert "Kidney: eGFR 55; UACR not available to repeat eGFR/UACR if due" in roadmap
    assert "Blood pressure: At goal." in roadmap
    assert "Blood sugar: Normal range." in roadmap
    assert "Protect the kidneys: Repeat kidney blood/urine testing; eGFR 55 and UACR not available." in roadmap
    assert "Artery plaque: Calcium scan only if it would change the treatment decision." in roadmap
    assert "ApoB:" not in roadmap
    assert "hsCRP" not in roadmap


def test_patient_roadmap_html_uses_distinct_compact_section_panels():
    bundle = render_case_output(Patient(age=60, sex="female", diabetes=True, egfr=52, uacr=210, ldl_c=132))
    html_visible = bundle["outputs"]["roadmap_html_visible"]
    assert_present(html_visible, ("STEP 1", "STEP 2", "STEP 3", "STEP 4"))
