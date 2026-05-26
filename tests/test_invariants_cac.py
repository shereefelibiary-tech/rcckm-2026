from __future__ import annotations

from core.patient import Patient
from modules.plaque.engine import build_plaque_result, format_cac_percentile_context
from modules.levels.definitions import classify_continuum_position
from tests.helpers import assert_absent, assert_present, render_case_output


def test_cac_zero_missing_and_positive_plaque_states_do_not_cross():
    missing_outputs = render_case_output(Patient(age=55, sex="male", cac=None, cac_not_done=True))["outputs"]
    zero_outputs = render_case_output(Patient(age=55, sex="male", cac=0))["outputs"]
    positive_outputs = render_case_output(Patient(age=55, sex="male", cac=38))["outputs"]
    missing = "\n".join([missing_outputs["emr"], missing_outputs["roadmap"], missing_outputs["actions"]])
    zero = "\n".join([zero_outputs["emr"], zero_outputs["roadmap"], zero_outputs["actions"]])
    positive = "\n".join([positive_outputs["emr"], positive_outputs["roadmap"], positive_outputs["actions"]])
    assert "CAC 0" not in missing
    assert "plaque unmeasured" in missing.lower() or "CAC not performed" in missing
    assert "no calcified plaque detected" in zero.lower()
    assert "CAC not performed" not in zero
    assert "mild plaque" in positive.lower() or "plaque present" in positive.lower()
    assert "no calcified coronary plaque detected" not in positive.lower()


def test_cac_100_and_300_have_treatment_forward_plaque_language():
    cac100 = render_case_output(Patient(age=60, sex="male", cac=100, ldl_c=120, tc=200, hdl_c=45, triglycerides=150))
    cac300 = render_case_output(Patient(age=60, sex="male", cac=300, ldl_c=120, tc=200, hdl_c=45, triglycerides=150))
    assert "mild plaque" not in cac100["outputs"]["visible"].lower()
    assert "High-intensity lipid-lowering therapy indicated" in cac300["outputs"]["visible"]
    assert classify_continuum_position(cac300["patient"], cac300["result"])["level"] == 5


def test_clinical_ascvd_overrides_cac_zero():
    bundle = render_case_output(Patient(age=62, sex="male", clinical_ascvd=True, cac=0, ldl_c=100))
    text = bundle["outputs"]["visible"]
    assert classify_continuum_position(bundle["patient"], bundle["result"])["level"] == 5
    assert "Secondary-prevention lipid-lowering" in text or "secondary-prevention" in text.lower()
    assert "defer" not in text.lower()


def test_cac_percentile_context_never_overpowers_absolute_score():
    assert format_cac_percentile_context(0, 90) is None
    assert "Higher than expected" in format_cac_percentile_context(20, 80)
    assert "Within the expected" in format_cac_percentile_context(20, 50)
    assert format_cac_percentile_context(350, 10) is None
    assert format_cac_percentile_context(20, 101) is None
    assert format_cac_percentile_context(20, -1) is None


def test_young_cac_missing_recommendation_is_conditional():
    bundle = render_case_output(
        Patient(
            age=38,
            sex="male",
            ldl_c=164,
            tc=236,
            hdl_c=48,
            triglycerides=186,
            apob=118,
            a1c=5.9,
            family_history_premature_ascvd=True,
            cac_not_done=True,
            prevent_10y_ascvd=1.03,
            prevent_30y_ascvd=7.53,
        )
    )
    assert_present(bundle["outputs"]["visible"], ("CAC not routinely recommended at this age",))
    assert_absent(bundle["outputs"]["visible"], ("CAC reasonable for risk clarification",))


def test_cac_interpretation_helper_rejects_invalid_values():
    assert build_plaque_result(Patient(age=55, sex="male", cac=-1)).plaque_category.value == "UNKNOWN"
