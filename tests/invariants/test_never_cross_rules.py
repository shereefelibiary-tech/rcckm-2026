from __future__ import annotations

import re

from core.enums import RiskLevel
from modules.levels.definitions import classify_continuum_position
from tests.helpers import (
    action_text,
    assert_absent,
    assert_no_contradictions,
    diagnosis_text,
    evaluate_case,
    render_all_outputs,
    visible_text,
)


def _risk_category_value(result) -> str:
    return str(getattr(getattr(result, "prevent_risk_category", None), "value", getattr(result, "prevent_risk_category", "")))


def test_cac_missing_never_generates_plaque_diagnosis_or_zero_language():
    patient, result = evaluate_case({"age": 62, "sex": "male", "cac": None, "cac_not_done": True})
    outputs = render_all_outputs(patient, result)

    assert_absent(diagnosis_text(result), ["Subclinical coronary atherosclerosis"])
    assert "plaque" in outputs["visible"].lower()
    assert "unmeasured" in outputs["visible"].lower() or "CAC not performed" in outputs["visible"]
    assert_absent(outputs["emr"], ["CAC 0"])


def test_cac_zero_is_measured_no_plaque_and_not_missing():
    patient, result = evaluate_case({"age": 55, "sex": "male", "cac": 0})
    outputs = render_all_outputs(patient, result)

    assert "CAC 0" in outputs["visible"]
    assert_absent(diagnosis_text(result), ["Subclinical coronary atherosclerosis"])
    assert_absent(outputs["visible"], ["plaque unmeasured", "Plaque: unmeasured"])


def test_cac_positive_generates_plaque_context_and_cac_300_is_level_5():
    patient, result = evaluate_case({"age": 60, "sex": "male", "cac": 38})
    assert "Subclinical coronary atherosclerosis" in diagnosis_text(result)
    assert "CAC 38" in visible_text(patient, result)

    severe_patient, severe_result = evaluate_case({"age": 60, "sex": "male", "cac": 300})
    assert classify_continuum_position(severe_patient, severe_result)["level"] == 5
    assert "Severe subclinical coronary atherosclerosis" in diagnosis_text(severe_result)


def test_clinical_ascvd_overrides_cac_zero_and_prevent():
    patient, result = evaluate_case(
        {
            "age": 60,
            "sex": "male",
            "clinical_ascvd": True,
            "clinical_ascvd_context": "prior NSTEMI and PCI/stent",
            "cac": 0,
            "prevent_10y_ascvd": 1.2,
        }
    )
    outputs = render_all_outputs(patient, result)

    assert classify_continuum_position(patient, result)["level"] == 5
    assert "Clinical ASCVD" in diagnosis_text(result)
    assert_absent(diagnosis_text(result), ["Subclinical coronary atherosclerosis"])
    assert "PREVENT not used for treatment decisions in established ASCVD." in outputs["prevent"]
    assert "secondary-prevention lipid-lowering" in outputs["actions"].lower()


def test_cac_already_measured_does_not_recommend_repeat_for_current_decision():
    patient, result = evaluate_case({"age": 60, "sex": "male", "cac": 350})
    actions = action_text(result, patient)

    assert "CAC 350 already measured" in actions
    assert "no repeat CAC needed for current decision-making" in actions
    assert_absent(actions, ["CAC reasonable for risk clarification", "CAC may clarify plaque burden"])


def test_ldl_190_pathway_is_treatment_forward_and_not_derisked():
    patient, result = evaluate_case({"age": 55, "sex": "male", "ldl_c": 204, "cac": 0, "prevent_10y_ascvd": 1.0})
    outputs = render_all_outputs(patient, result)

    assert classify_continuum_position(patient, result)["level"] >= 3
    assert "High-intensity or maximally tolerated statin therapy indicated" in outputs["actions"]
    assert_absent(outputs["actions"], ["No escalation indicated"])
    assert "PREVENT should not be used to de-risk" in outputs["visible"]
    assert "CAC 0" in outputs["visible"]
    assert "defer lipid-lowering therapy" in outputs["visible"] or "not be used to de-risk" in outputs["visible"]


def test_clinical_ascvd_always_uses_secondary_prevention_lipid_language():
    patient, result = evaluate_case({"age": 65, "sex": "female", "clinical_ascvd": True, "ldl_c": 120})
    assert "secondary-prevention lipid-lowering" in action_text(result, patient).lower()


def test_cac_100_and_300_are_treatment_forward_not_no_escalation():
    patient_100, result_100 = evaluate_case({"age": 61, "sex": "female", "cac": 145, "ldl_c": 124, "non_hdl_c": 162})
    patient_300, result_300 = evaluate_case({"age": 61, "sex": "female", "cac": 350, "ldl_c": 124, "non_hdl_c": 162})

    assert_absent(action_text(result_100, patient_100), ["No escalation indicated"])
    assert "lipid-lowering therapy" in action_text(result_100, patient_100).lower()
    assert_absent(action_text(result_300, patient_300), ["No escalation indicated"])
    assert "High-intensity lipid-lowering therapy indicated" in action_text(result_300, patient_300)


def test_cac_clarification_is_not_dominant_when_lipids_are_indicated():
    _patient, result = evaluate_case({"age": 55, "sex": "male", "ldl_c": 204, "cac": None, "cac_not_done": True})
    assert not str(getattr(result, "dominant_action", "") or "").lower().startswith("cac")
    assert "maximally tolerated statin" in str(getattr(result, "dominant_action", "") or "").lower()


def test_severe_triglyceride_pathways_surface_pancreatitis_and_dominance():
    patient_500, result_500 = evaluate_case({"age": 50, "sex": "male", "triglycerides": 500, "tc": 286, "hdl_c": 32})
    patient_1000, result_1000 = evaluate_case({"age": 50, "sex": "male", "triglycerides": 1000, "tc": 286, "hdl_c": 32})

    assert "pancreatitis" in visible_text(patient_500, result_500).lower()
    assert "pancreatitis" in visible_text(patient_1000, result_1000).lower()
    assert "severe hypertriglyceridemia" in str(getattr(result_1000, "dominant_action", "") or "").lower()


def test_glycemic_and_kidney_actions_surface_when_criteria_are_present():
    patient, result = evaluate_case({"age": 55, "sex": "male", "diabetes": True, "a1c": 7.1, "egfr": 55, "uacr": 45})
    text = visible_text(patient, result)

    assert "Optimize glycemic therapy" in text
    assert "kidney-protective" in text
    assert "Albuminuria" in diagnosis_text(result)


def test_uacr_missing_zero_and_albuminuria_stages_never_cross():
    missing_patient, missing_result = evaluate_case({"age": 55, "sex": "female", "egfr": 76, "bp_treated": True})
    zero_patient, zero_result = evaluate_case({"age": 55, "sex": "female", "egfr": 76, "uacr": 0})
    a2_patient, a2_result = evaluate_case({"age": 55, "sex": "female", "egfr": 76, "uacr": 34})
    a3_patient, a3_result = evaluate_case({"age": 55, "sex": "female", "egfr": 76, "uacr": 300})

    assert "UACR 0" not in visible_text(missing_patient, missing_result)
    assert "UACR missing" in visible_text(missing_patient, missing_result)
    assert "UACR 0" in visible_text(zero_patient, zero_result)
    assert "UACR missing" not in visible_text(zero_patient, zero_result)
    assert getattr(a2_result, "albuminuria_stage", None) == "A2"
    assert getattr(a3_result, "albuminuria_stage", None) == "A3"


def test_egfr_stages_and_preserved_egfr_albuminuria_surface_kidney_risk():
    g3a_patient, g3a_result = evaluate_case({"age": 55, "sex": "male", "egfr": 59})
    g3b_patient, g3b_result = evaluate_case({"age": 55, "sex": "male", "egfr": 44})
    preserved_patient, preserved_result = evaluate_case({"age": 55, "sex": "male", "egfr": 90, "uacr": 45})

    assert getattr(g3a_result, "egfr_stage", None) == "G3a"
    assert getattr(g3b_result, "egfr_stage", None) == "G3b"
    assert "normal kidney function" not in visible_text(g3a_patient, g3a_result).lower()
    assert "Albuminuria" in diagnosis_text(preserved_result)
    assert "A2" in visible_text(preserved_patient, preserved_result)


def test_prevent_10_year_categories_are_locked():
    for risk, expected in (
        (2.99, RiskLevel.LOW),
        (3.00, RiskLevel.BORDERLINE),
        (4.99, RiskLevel.BORDERLINE),
        (5.00, RiskLevel.INTERMEDIATE),
        (9.99, RiskLevel.INTERMEDIATE),
        (10.00, RiskLevel.HIGH),
    ):
        _patient, result = evaluate_case({"age": 55, "sex": "male", "prevent_10y_ascvd": risk})
        assert result.prevent_risk_category == expected


def test_plaque_burden_dominates_over_prevent_only_framing():
    patient, result = evaluate_case({"age": 60, "sex": "male", "cac": 350, "prevent_10y_ascvd": 1.0})
    text = visible_text(patient, result)

    assert classify_continuum_position(patient, result)["level"] == 5
    assert "CAC 350" in text
    assert "High-intensity lipid-lowering therapy indicated" in text


def test_emr_and_roadmap_language_safety_and_no_raw_html():
    patient, result = evaluate_case({"age": 55, "sex": "male", "cac": 350, "diabetes": True, "a1c": 7.1, "egfr": 55, "uacr": 45})
    outputs = render_all_outputs(patient, result)

    for section in ("emr", "roadmap"):
        assert not re.search(r"</?[a-zA-Z][^>]*>", outputs[section])
        assert_absent(
            outputs[section],
            [
                "phenotype",
                "inherited risk",
                "genetics",
                "dominant_action",
                "action_domains",
                "risk_continuum_sublevel",
                "Supporting actions:",
            ],
        )
    assert_no_contradictions(outputs["visible"])


def test_contradictory_pairs_are_absent_in_representative_outputs():
    cases = [
        {"age": 55, "sex": "male", "cac": 0},
        {"age": 55, "sex": "male", "cac": 350},
        {"age": 55, "sex": "male", "ldl_c": 204, "cac": 0},
        {"age": 60, "sex": "male", "cac": None, "cac_not_done": True, "prevent_10y_ascvd": 8.0},
    ]
    for patient_dict in cases:
        patient, result = evaluate_case(patient_dict)
        assert_no_contradictions(visible_text(patient, result))


def test_prediabetes_does_not_become_diabetes_without_threshold_or_flag():
    _patient, result = evaluate_case({"age": 55, "sex": "female", "a1c": 6.4, "diabetes": False})
    diagnoses = diagnosis_text(result)

    assert "Prediabetes" in diagnoses
    assert "Type 2 diabetes mellitus" not in diagnoses


def test_diabetic_kidney_disease_requires_diabetes_and_kidney_criteria():
    no_diabetes_patient, no_diabetes_result = evaluate_case({"age": 55, "sex": "male", "egfr": 55, "uacr": 45})
    diabetes_patient, diabetes_result = evaluate_case({"age": 55, "sex": "male", "diabetes": True, "egfr": 55, "uacr": 45})

    assert "Type 2 diabetes mellitus with diabetic chronic kidney disease" not in diagnosis_text(no_diabetes_result)
    assert "Type 2 diabetes mellitus with diabetic chronic kidney disease" in diagnosis_text(diabetes_result)
    assert "CKD" in visible_text(diabetes_patient, diabetes_result)


def test_albuminuria_diagnosis_requires_uacr_30_or_higher():
    _missing_patient, missing_result = evaluate_case({"age": 55, "sex": "female", "egfr": 76})
    _a1_patient, a1_result = evaluate_case({"age": 55, "sex": "female", "egfr": 76, "uacr": 29})
    _a2_patient, a2_result = evaluate_case({"age": 55, "sex": "female", "egfr": 76, "uacr": 30})

    assert "Albuminuria" not in diagnosis_text(missing_result)
    assert "Albuminuria" not in diagnosis_text(a1_result)
    assert "Albuminuria" in diagnosis_text(a2_result)


def test_plaque_diagnoses_require_cac_thresholds_and_clinical_ascvd_does_not():
    _missing_patient, missing_result = evaluate_case({"age": 60, "sex": "male", "cac": None, "cac_not_done": True})
    _cac0_patient, cac0_result = evaluate_case({"age": 60, "sex": "male", "cac": 0})
    _cac1_patient, cac1_result = evaluate_case({"age": 60, "sex": "male", "cac": 1})
    _cac299_patient, cac299_result = evaluate_case({"age": 60, "sex": "male", "cac": 299})
    _cac300_patient, cac300_result = evaluate_case({"age": 60, "sex": "male", "cac": 300})
    _ascvd_patient, ascvd_result = evaluate_case({"age": 60, "sex": "male", "clinical_ascvd": True})

    assert "Subclinical coronary atherosclerosis" not in diagnosis_text(missing_result)
    assert "Subclinical coronary atherosclerosis" not in diagnosis_text(cac0_result)
    assert "Subclinical coronary atherosclerosis" in diagnosis_text(cac1_result)
    assert "Severe subclinical coronary atherosclerosis" not in diagnosis_text(cac299_result)
    assert "Severe subclinical coronary atherosclerosis" in diagnosis_text(cac300_result)
    assert "Clinical ASCVD" in diagnosis_text(ascvd_result)
