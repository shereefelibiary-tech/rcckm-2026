from core.engine import evaluate_patient
from core.patient import Patient
from modules.prevent.calculator import calculate_prevent_summary
from renderers.clarifier_renderer import build_clarifier_card_html
from renderers.emr_renderer import render_emr_note
from renderers.parse_coverage import render_parse_coverage
from renderers.prevent_card import render_prevent_card
from renderers.where_patient_falls import build_where_patient_falls_html
from ui.input_worksheet import build_patient_from_inputs
from ui.report_layout import _build_ckm_kdigo_summary_html


def test_missing_uacr_remains_none_and_zero_remains_measured_zero():
    missing = build_patient_from_inputs({"age": 55, "sex": "male", "egfr": 84, "uacr": ""})
    measured_zero = build_patient_from_inputs({"age": 55, "sex": "male", "egfr": 84, "uacr": "0"})

    assert missing.uacr is None
    assert measured_zero.uacr == 0


def test_missing_uacr_does_not_become_kdigo_a1():
    patient = Patient(age=55, sex="male", egfr=84, uacr=None)
    result = evaluate_patient(patient)
    html = _build_ckm_kdigo_summary_html(result, patient)

    assert result.albuminuria_stage is None
    assert result.kdigo_stage == "G2"
    assert "albuminuria not measured" in html
    assert "G2A1" not in html


def test_missing_uacr_triggers_clarifier_for_diabetes_and_bp_treated_contexts():
    diabetes_patient = Patient(age=55, sex="male", diabetes=True, egfr=84, uacr=None)
    bp_patient = Patient(age=55, sex="male", bp_treated=True, egfr=84, uacr=None)

    diabetes_result = evaluate_patient(diabetes_patient)
    bp_result = evaluate_patient(bp_patient)

    assert diabetes_result.clarification["recommend_uacr"] is True
    assert bp_result.clarification["recommend_uacr"] is True
    assert "UACR" in build_clarifier_card_html(diabetes_result)
    assert "kidney risk completion" in build_clarifier_card_html(diabetes_result)


def test_uacr_present_a2_does_not_trigger_missing_clarifier():
    patient = Patient(age=55, sex="male", diabetes=True, egfr=84, uacr=45)
    result = evaluate_patient(patient)

    assert result.albuminuria_stage == "A2"
    assert result.kdigo_stage == "G2A2"
    assert result.clarification["recommend_uacr"] is False


def test_where_patient_falls_shows_missing_uacr_as_needed_not_normal():
    patient = Patient(age=55, sex="male", egfr=84, uacr=None)
    result = evaluate_patient(patient)
    html = build_where_patient_falls_html(patient, result)

    assert "eGFR 84" in html
    assert "UACR missing" in html
    assert "needed" in html
    assert "UACR 0" not in html


def test_parse_coverage_shows_uacr_not_found_when_not_parsed():
    html = render_parse_coverage({"parsed": {"age": 55}, "meta": {}, "warnings": [], "conflicts": []})

    assert "UACR" in html
    assert "not found" in html


def test_prevent_uses_base_model_with_compact_uacr_missing_note():
    patient = Patient(
        age=55,
        sex="male",
        tc=205,
        hdl_c=48,
        sbp=132,
        bp_treated=True,
        lipid_lowering=False,
        diabetes=False,
        smoker=False,
        bmi=31,
        egfr=84,
        uacr=None,
    )
    prevent = calculate_prevent_summary(patient)
    result = evaluate_patient(patient)
    html = render_prevent_card(result)

    assert prevent["available"] is True
    assert prevent["model_used"] == "base"
    assert prevent["prevent_10y_ascvd"] is not None
    assert "UACR missing; base PREVENT model used." in prevent["warnings"]
    assert "Model used" in html
    assert "base" in html
    assert "UACR missing; base PREVENT model used." in html


def test_emr_note_includes_uacr_completion_only_when_relevant():
    relevant_patient = Patient(age=55, sex="male", diabetes=True, egfr=84, uacr=None)
    low_context_patient = Patient(age=35, sex="male", egfr=None, uacr=None)

    relevant_note = render_emr_note(relevant_patient, evaluate_patient(relevant_patient))
    low_context_note = render_emr_note(low_context_patient, evaluate_patient(low_context_patient))

    assert "UACR not available; obtain to complete kidney-risk assessment." in relevant_note
    assert "UACR not available" not in low_context_note
