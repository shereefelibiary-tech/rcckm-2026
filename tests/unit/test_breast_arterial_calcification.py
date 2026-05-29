from core.engine import evaluate_patient
from core.patient import Patient
from modules.actions.engine import build_action_plan
from modules.diagnoses.engine import build_diagnosis_candidates
from modules.risk_enhancers.breast_arterial_calcification import (
    BAC_CAC_CLARIFICATION_TEXT,
    BAC_PATIENT_CONTEXT_TEXT,
    has_breast_arterial_calcification,
    normalize_breast_arterial_calcification,
)
from modules.risk_enhancers.engine import identify_risk_enhancers
from renderers.emr_renderer import render_emr_note
from renderers.patient_roadmap import render_patient_roadmap_text
from renderers.where_patient_falls import build_where_patient_falls_html
from ui.input_worksheet import build_patient_from_inputs, normalize_input_aliases
from smartphrase_ingest.parser import parse_smartphrase_report


def _diagnosis_names(patient):
    return {candidate.name for candidate in build_diagnosis_candidates(patient)}


def test_bac_normalizes_boolean_and_allowed_values():
    assert normalize_breast_arterial_calcification(True) == "present"
    assert normalize_breast_arterial_calcification(False) == "absent"
    assert normalize_breast_arterial_calcification("moderate") == "moderate"
    assert normalize_breast_arterial_calcification("unknown") == "unknown"
    assert normalize_breast_arterial_calcification("not a value") == "unknown"


def test_bac_present_appears_as_context_not_coronary_diagnosis_or_cac_score():
    patient = Patient(age=57, sex="female", breast_arterial_calcification="moderate")
    result = evaluate_patient(patient)
    emr = render_emr_note(patient, result)
    roadmap = render_patient_roadmap_text(patient, result)
    falls = build_where_patient_falls_html(patient, result)
    enhancer_text = " ".join(identify_risk_enhancers(patient))
    diagnoses = _diagnosis_names(patient)

    assert has_breast_arterial_calcification(patient)
    assert "Breast arterial calcification on mammogram" in enhancer_text
    assert "Context: BAC." in emr
    assert "Breast arterial calcification" in falls
    assert BAC_PATIENT_CONTEXT_TEXT in roadmap
    assert "Subclinical coronary atherosclerosis" not in diagnoses
    assert "Clinical ASCVD" not in diagnoses
    assert "coronary artery disease" not in " ".join(diagnoses).lower()
    assert patient.cac is None
    assert result.plaque_category.value == "UNKNOWN"


def test_bac_absent_does_not_appear_as_risk_context():
    patient = Patient(age=57, sex="female", breast_arterial_calcification="absent")
    result = evaluate_patient(patient)
    text = (
        render_emr_note(patient, result)
        + "\n"
        + render_patient_roadmap_text(patient, result)
        + "\n"
        + " ".join(identify_risk_enhancers(patient))
    )

    assert not has_breast_arterial_calcification(patient)
    assert "Breast arterial calcification" not in text


def test_bac_alone_does_not_assign_level_5_or_trigger_aspirin():
    patient = Patient(age=58, sex="female", breast_arterial_calcification="severe")
    result = evaluate_patient(patient)
    plan = build_action_plan(patient, result)
    all_actions = " ".join(plan["recommendations"]).lower()

    assert result.level_classification["level"] != "5"
    assert "aspirin may be considered" not in all_actions


def test_bac_with_missing_cac_can_use_existing_cac_clarification_pathway():
    patient = Patient(
        age=58,
        sex="female",
        sbp=132,
        dbp=78,
        bp_treated=True,
        tc=220,
        hdl_c=48,
        ldl_c=142,
        triglycerides=178,
        breast_arterial_calcification="present",
        prevent_10y_ascvd=6.0,
        prevent_30y_ascvd=24.0,
    )
    result = evaluate_patient(patient)

    assert result.action_domains.get("cac_testing") == BAC_CAC_CLARIFICATION_TEXT


def test_cac_dominates_plaque_interpretation_when_bac_and_cac_present():
    patient = Patient(age=62, sex="female", cac=0, breast_arterial_calcification="present")
    result = evaluate_patient(patient)
    roadmap = render_patient_roadmap_text(patient, result)
    diagnoses = _diagnosis_names(patient)

    assert result.plaque_category.value == "NONE"
    assert "CAC 0: no calcified plaque detected." in roadmap
    assert BAC_PATIENT_CONTEXT_TEXT in roadmap
    assert "Subclinical coronary atherosclerosis" not in diagnoses


def test_bac_parser_and_worksheet_aliases_preserve_canonical_value():
    report = parse_smartphrase_report("Mammary artery calcification: moderate on mammogram.")
    patient = build_patient_from_inputs(report.extracted)
    alias_values = normalize_input_aliases({"breast_artery_calcification": True})

    assert report.extracted["breast_arterial_calcification"] == "moderate"
    assert patient.breast_arterial_calcification == "moderate"
    assert alias_values["breast_arterial_calcification"] is True
