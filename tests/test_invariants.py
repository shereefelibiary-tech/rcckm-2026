from tests.validation_helpers import (
    action_lines,
    assert_no_raw_html_visible,
    clinical_visible_text,
    diagnosis_names,
    evaluate_dict,
)
from modules.levels.definitions import classify_continuum_position
from renderers.emr_renderer import render_emr_note


def test_clinical_ascvd_overrides_prevent_and_cac():
    patient, result = evaluate_dict(
        {
            "age": 60,
            "sex": "male",
            "clinical_ascvd": True,
            "clinical_ascvd_context": "prior NSTEMI and PCI/stent",
            "cac": 0,
            "prevent_10y_ascvd": 2.5,
        }
    )

    names = diagnosis_names(result)
    text = clinical_visible_text(patient, result)

    assert result.clinical_ascvd is True
    assert any("Clinical ASCVD" in name for name in names)
    assert not any("Subclinical coronary atherosclerosis" in name for name in names)
    assert "PREVENT not used for treatment decisions in established ASCVD." in text
    assert "does not de-risk secondary prevention" in text
    assert any("Secondary-prevention lipid-lowering therapy" in action for action in action_lines(result))


def test_cac_missing_never_generates_plaque_diagnosis_or_cac_zero_language():
    patient, result = evaluate_dict(
        {"age": 62, "sex": "male", "prevent_10y_ascvd": 12.0, "cac": None, "cac_not_done": True}
    )
    text = clinical_visible_text(patient, result)
    emr = render_emr_note(patient, result)

    assert not any("Subclinical coronary atherosclerosis" in name for name in diagnosis_names(result))
    assert "plaque unmeasured" in text.lower() or "CAC not performed" in text
    assert "Plaque: CAC 0" not in emr


def test_cac_zero_is_measured_and_not_missing():
    patient, result = evaluate_dict({"age": 55, "sex": "male", "cac": 0})
    text = clinical_visible_text(patient, result)

    assert "CAC 0" in text
    assert "plaque unmeasured" not in text.lower()
    assert not any("Subclinical coronary atherosclerosis" in name for name in diagnosis_names(result))


def test_prevent_high_alone_does_not_imply_plaque_present():
    patient, result = evaluate_dict({"age": 60, "sex": "male", "prevent_10y_ascvd": 12.0})
    text = clinical_visible_text(patient, result).lower()

    assert not any("Subclinical coronary atherosclerosis" in name for name in diagnosis_names(result))
    assert "plaque unmeasured" in text


def test_prevent_category_does_not_overwrite_rcckm_level_when_albuminuria_is_actionable():
    patient, result = evaluate_dict(
        {
            "age": 55,
            "sex": "female",
            "prevent_10y_ascvd": 3.74,
            "prevent_30y_ascvd": 18.8,
            "uacr": 34,
            "egfr": 82,
            "a1c": 6.1,
            "triglycerides": 162,
            "apob": 92,
            "ldl_c": 126,
            "bp_treated": True,
            "cac": None,
            "cac_not_done": True,
        }
    )

    assert str(getattr(result.prevent_risk_category, "value", result.prevent_risk_category)) == "BORDERLINE"
    assert classify_continuum_position(patient, result) == {"level": 3, "sublevel": "3B"}
    assert "Level 3B - actionable early CKM / kidney risk." in render_emr_note(patient, result)


def test_elevated_30_year_prevent_trajectory_sets_at_least_level_3_without_plaque():
    patient, result = evaluate_dict(
        {
            "age": 45,
            "sex": "male",
            "prevent_10y_ascvd": 1.2,
            "prevent_30y_ascvd": 10.5,
            "cac": None,
            "cac_not_done": True,
        }
    )
    position = classify_continuum_position(patient, result)
    names = diagnosis_names(result)
    text = clinical_visible_text(patient, result)

    assert position["level"] >= 3
    assert position["level"] < 4
    assert not any("Subclinical coronary atherosclerosis" in name for name in names)
    assert "plaque unmeasured / CAC not performed" in render_emr_note(patient, result)
    assert "30-year risk 10.5%" in text


def test_missing_uacr_is_not_normal_albuminuria_but_zero_is_measured():
    missing_patient, missing_result = evaluate_dict({"age": 55, "sex": "female", "egfr": 84})
    zero_patient, zero_result = evaluate_dict({"age": 55, "sex": "female", "egfr": 84, "uacr": 0})

    assert getattr(missing_patient, "uacr") is None
    assert not any("Albuminuria" in name for name in diagnosis_names(missing_result))
    assert "UACR 0" not in clinical_visible_text(missing_patient, missing_result)

    assert zero_patient.uacr == 0
    assert not any("Albuminuria" in name for name in diagnosis_names(zero_result))
    assert "UACR 0" in clinical_visible_text(zero_patient, zero_result)


def test_lpa_80_and_single_hscrp_are_not_major_diagnoses():
    _patient, lpa_result = evaluate_dict({"age": 55, "sex": "female", "lp_a_value": 80, "lp_a_unit": "nmol/L"})
    patient, hscrp_result = evaluate_dict({"age": 55, "sex": "male", "hscrp": 2.5})

    assert not any("Elevated lipoprotein(a)" in name for name in diagnosis_names(lpa_result))
    assert "major driver" not in clinical_visible_text(patient, hscrp_result).lower()


def test_aspirin_not_routinely_recommended_and_cac_not_repeated_when_measured():
    patient, result = evaluate_dict({"age": 55, "sex": "male", "cac": 350})
    text = clinical_visible_text(patient, result)

    assert "Aspirin may be considered only if bleeding risk is low after shared decision-making." in text
    assert "CAC 350 already measured" in text
    assert "Coronary calcium reasonable for plaque clarification" not in "\n".join(action_lines(result))


def test_ldl_190_pathway_not_derisked_by_cac_zero():
    _patient, result = evaluate_dict({"age": 55, "sex": "male", "ldl_c": 190, "cac": 0})

    assert any("Severe hypercholesterolemia" in name for name in diagnosis_names(result))
    assert any("maximally tolerated statin therapy indicated" in action for action in action_lines(result))


def test_rendered_outputs_do_not_expose_raw_html_or_unwanted_language():
    patient, result = evaluate_dict(
        {
            "age": 55,
            "sex": "male",
            "cac": 350,
            "apob": 110,
            "lp_a_value": 80,
            "lp_a_unit": "nmol/L",
            "a1c": 7.1,
            "diabetes": True,
            "egfr": 55,
            "uacr": 45,
        }
    )
    text = clinical_visible_text(patient, result)

    assert_no_raw_html_visible(text)
    for phrase in ("phenotype", "inherited risk", "genetics", "Supporting actions:"):
        assert phrase.lower() not in text.lower()
