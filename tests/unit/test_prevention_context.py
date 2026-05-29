from core.engine import evaluate_patient
from core.patient import Patient
from modules.actions.scaffold import build_action_scaffold
from modules.prevention_context.engine import (
    PREVENTION_CONTEXT_PRIMARY,
    PREVENTION_CONTEXT_PRIMARY_SUBCLINICAL_PLAQUE,
    PREVENTION_CONTEXT_SECONDARY_ASCVD,
    classify_prevention_context,
)
from renderers.emr_renderer import render_emr_note


def _aspirin_line(patient, result):
    return next(section.line for section in build_action_scaffold(patient, result) if section.label == "Aspirin")


def test_documented_ascvd_events_are_secondary_prevention():
    contexts = [
        "prior MI",
        "prior PCI",
        "prior CABG",
        "ischemic stroke",
        "TIA of atherosclerotic origin",
        "peripheral artery disease",
        "symptomatic carotid artery disease",
    ]

    for context in contexts:
        patient = Patient(age=62, sex="male", clinical_ascvd=True, clinical_ascvd_context=context)
        result = evaluate_patient(patient)

        assert result.prevention_context == PREVENTION_CONTEXT_SECONDARY_ASCVD
        assert result.prevention_context_rule_id == "prevention_context_secondary_clinical_ascvd"
        assert classify_prevention_context(patient)["prevention_context"] == PREVENTION_CONTEXT_SECONDARY_ASCVD


def test_cac_alone_is_subclinical_plaque_primary_prevention_not_secondary():
    for cac in (350, 5000):
        patient = Patient(age=62, sex="male", clinical_ascvd=False, cac=cac)
        result = evaluate_patient(patient)

        assert result.prevention_context == PREVENTION_CONTEXT_PRIMARY_SUBCLINICAL_PLAQUE
        assert result.prevention_context != PREVENTION_CONTEXT_SECONDARY_ASCVD
        assert f"CAC {cac:g}" in result.prevention_context_supporting_findings


def test_incidental_cac_is_subclinical_plaque_primary_prevention():
    patient = Patient(age=60, sex="female", incidental_cac=True, incidental_cac_severity="moderate")
    result = evaluate_patient(patient)

    assert result.prevention_context == PREVENTION_CONTEXT_PRIMARY_SUBCLINICAL_PLAQUE
    assert "incidental coronary artery calcification on CT" in result.prevention_context_supporting_findings


def test_breast_arterial_calcification_is_not_secondary_prevention():
    patient = Patient(age=58, sex="female", breast_arterial_calcification="severe")
    result = evaluate_patient(patient)

    assert result.prevention_context == PREVENTION_CONTEXT_PRIMARY_SUBCLINICAL_PLAQUE
    assert result.prevention_context != PREVENTION_CONTEXT_SECONDARY_ASCVD
    assert "breast arterial calcification on mammogram" in result.prevention_context_supporting_findings


def test_ldl_190_without_clinical_ascvd_remains_primary_prevention():
    patient = Patient(age=55, sex="male", clinical_ascvd=False, ldl_c=212)
    result = evaluate_patient(patient)

    assert result.prevention_context == PREVENTION_CONTEXT_PRIMARY
    assert result.severe_hypercholesterolemia is True


def test_diabetes_ckd_without_clinical_ascvd_remains_primary_prevention():
    patient = Patient(age=57, sex="female", clinical_ascvd=False, diabetes=True, egfr=52, uacr=80)
    result = evaluate_patient(patient)

    assert result.prevention_context == PREVENTION_CONTEXT_PRIMARY
    assert result.ckm_stage["stage"] >= 3


def test_subclinical_plaque_uses_primary_prevention_aspirin_logic():
    patient = Patient(age=62, sex="male", clinical_ascvd=False, cac=350)
    result = evaluate_patient(patient)
    aspirin = _aspirin_line(patient, result)

    assert "secondary prevention" not in aspirin.lower()
    assert "antiplatelet therapy is indicated" not in aspirin.lower()
    assert "bleeding risk" in aspirin.lower() or "not routine for primary prevention" in aspirin.lower()


def test_secondary_prevention_uses_antiplatelet_language_not_primary_aspirin():
    patient = Patient(age=62, sex="male", clinical_ascvd=True, clinical_ascvd_context="prior MI", cac=0)
    result = evaluate_patient(patient)
    aspirin = _aspirin_line(patient, result)

    assert aspirin == (
        "Antiplatelet therapy is indicated for secondary prevention if clinically appropriate and no contraindication is present."
    )
    assert "routine primary prevention" not in aspirin.lower()


def test_cac_alone_does_not_create_clinical_ascvd_diagnosis():
    patient = Patient(age=62, sex="male", clinical_ascvd=False, cac=5000)
    result = evaluate_patient(patient)
    diagnoses = " ".join(candidate.name for candidate in result.diagnosis_candidates)

    assert "Clinical ASCVD" not in diagnoses
    assert "coronary artery disease with prior" not in diagnoses
    assert "Severe subclinical coronary atherosclerosis" in diagnoses


def test_secondary_prevention_emr_wording_uses_goals_not_risk_derisking():
    patient = Patient(age=62, sex="male", clinical_ascvd=True, clinical_ascvd_context="prior PCI")
    result = evaluate_patient(patient)
    note = render_emr_note(patient, result)

    assert "Level: 5 - clinical ASCVD / secondary prevention" in note
    assert "Secondary-prevention antiplatelet therapy" in note
