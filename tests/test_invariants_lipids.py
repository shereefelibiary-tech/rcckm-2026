from __future__ import annotations

from core.patient import Patient
from modules.lipids.statin_intensity import get_statin_intensity_definition
from tests.helpers import assert_absent, assert_contains_any, render_case_output


def _actions(patient: Patient) -> str:
    return render_case_output(patient)["outputs"]["actions"]


def test_ldl_190_boundary_controls_severe_hypercholesterolemia_pathway():
    below = _actions(Patient(age=45, sex="male", ldl_c=189, tc=260, hdl_c=45, triglycerides=150))
    at = _actions(Patient(age=45, sex="male", ldl_c=190, tc=262, hdl_c=45, triglycerides=150))
    assert "High-intensity or maximally tolerated statin therapy indicated" not in below
    assert "High-intensity or maximally tolerated statin therapy indicated" in at


def test_ldl_190_with_cac_zero_is_not_de_risked_to_lifestyle_only():
    bundle = render_case_output(
        Patient(age=52, sex="male", ldl_c=204, tc=282, hdl_c=46, triglycerides=150, cac=0)
    )
    text = bundle["outputs"]["visible"]
    assert "High-intensity or maximally tolerated statin therapy indicated" in text
    assert "No medication escalation today" not in text


def test_prevent_ascvd_risk_bands_drive_statin_strength_semantically():
    moderate = _actions(
        Patient(
            age=60,
            sex="female",
            tc=210,
            ldl_c=128,
            hdl_c=48,
            triglycerides=150,
            prevent_10y_ascvd=8.0,
        )
    )
    high = _actions(
        Patient(
            age=66,
            sex="male",
            tc=240,
            ldl_c=150,
            hdl_c=40,
            triglycerides=180,
            prevent_10y_ascvd=20.0,
        )
    )
    assert "Moderate-intensity statin therapy is generally favored for primary prevention" in moderate
    assert "High-intensity statin therapy is generally recommended for primary prevention given high ASCVD risk" in high


def test_prevent_3_to_5_without_enhancers_remains_lifestyle_focused():
    actions = _actions(
        Patient(
            age=52,
            sex="female",
            tc=180,
            ldl_c=96,
            hdl_c=62,
            triglycerides=90,
            diabetes=False,
            smoker=False,
            prevent_10y_ascvd=3.4,
            prevent_30y_ascvd=8.0,
        )
    )
    assert "Continue lifestyle-focused prevention; reassess risk as clinical data evolve." in actions
    assert "statin therapy is reasonable" not in actions
    assert "recommended" not in actions.lower()


def test_prevent_3_to_5_with_lifetime_context_is_discussion_not_recommendation():
    actions = _actions(
        Patient(
            age=45,
            sex="male",
            tc=226,
            ldl_c=156,
            hdl_c=44,
            triglycerides=170,
            family_history_premature_ascvd=True,
            prevent_10y_ascvd=3.8,
            prevent_30y_ascvd=18.0,
        )
    )
    assert "Short-term ASCVD risk is low" in actions
    assert "may be reasonable after shared decision-making" in actions
    assert "generally recommended" not in actions


def test_low_10yr_high_30yr_without_enhancers_does_not_auto_recommend_statin():
    actions = _actions(
        Patient(
            age=38,
            sex="male",
            tc=178,
            ldl_c=96,
            hdl_c=56,
            triglycerides=95,
            prevent_10y_ascvd=2.4,
            prevent_30y_ascvd=18.0,
            diabetes=False,
            smoker=False,
        )
    )
    assert "short-term ascvd risk is low" in actions.lower()
    assert "not routinely indicated" in actions
    assert "High-intensity" not in actions


def test_low_10yr_high_30yr_with_major_enhancer_is_not_high_intensity():
    actions = _actions(
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
    assert "Moderate-intensity statin therapy may be reasonable after shared decision-making" in actions
    assert "High-intensity" not in actions
    assert "high near-term risk" not in actions.lower()


def test_low_10yr_high_30yr_with_albuminuria_reasonable_not_automatic_high_intensity():
    actions = _actions(
        Patient(
            age=46,
            sex="female",
            tc=210,
            ldl_c=126,
            hdl_c=48,
            triglycerides=170,
            egfr=72,
            uacr=48,
            prevent_10y_ascvd=4.2,
            prevent_30y_ascvd=34.0,
        )
    )
    assert "Low short-term ASCVD risk" in actions
    assert "moderate-intensity statin therapy" in actions.lower()
    assert "reasonable" in actions.lower()
    assert "High-intensity" not in actions


def test_plaque_present_favors_lipid_lowering_despite_low_short_term_risk():
    actions = _actions(
        Patient(
            age=44,
            sex="male",
            tc=196,
            ldl_c=126,
            hdl_c=52,
            triglycerides=118,
            cac=38,
            prevent_10y_ascvd=2.8,
            prevent_30y_ascvd=32.0,
        )
    )
    assert "Lipid-lowering therapy is favored because coronary plaque is already present" in actions
    assert "Continue lifestyle-focused prevention" not in actions
    assert "High-intensity" not in actions


def test_low_ascvd_without_major_enhancers_does_not_auto_recommend_statin():
    actions = _actions(
        Patient(
            age=40,
            sex="female",
            tc=170,
            ldl_c=92,
            hdl_c=60,
            triglycerides=90,
            diabetes=False,
            smoker=False,
            prevent_10y_ascvd=1.2,
            prevent_30y_ascvd=4.0,
        )
    )
    assert "Lipid lowering: no escalation based on current LDL-C/ApoB and ASCVD risk profile" in actions
    assert "statin therapy is generally recommended" not in actions


def test_borderline_ckd_albuminuria_strengthens_lipid_prevention():
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
    assert "Moderate-intensity statin therapy is reasonable given borderline/intermediate ASCVD risk with albuminuria" in text
    assert "No medication escalation today" not in text


def test_apob_value_not_reported_as_missing_and_lpa_not_called_inherited_risk():
    bundle = render_case_output(
        Patient(
            age=50,
            sex="female",
            tc=208,
            ldl_c=126,
            hdl_c=55,
            triglycerides=130,
            apob=112,
            lp_a_value=180,
            lp_a_unit="nmol/L",
            prevent_10y_ascvd=3.5,
        )
    )
    text = bundle["outputs"]["visible"]
    assert "ApoB" in text
    assert "ApoB missing" not in text
    assert_absent(text, ("inherited risk", "genetics"))


def test_statin_intensity_single_source_definitions():
    moderate = get_statin_intensity_definition("moderate")
    high = get_statin_intensity_definition("high")
    assert moderate.expected_ldl_reduction == "30% to 49%"
    assert high.expected_ldl_reduction == ">=50%"
    assert_contains_any("\n".join(moderate.examples), ("Atorvastatin 10-20 mg daily",))
    assert_contains_any("\n".join(high.examples), ("Rosuvastatin 20-40 mg daily",))
