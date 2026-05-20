from core.patient import Patient
from modules.diagnoses.engine import build_diagnosis_candidates


def test_build_diagnosis_candidates_adds_clinical_ascvd_candidate():
    patient = Patient(age=60, sex="male", clinical_ascvd=True)

    candidates = build_diagnosis_candidates(patient)

    assert any(c.name == "Clinical ASCVD" for c in candidates)


def test_build_diagnosis_candidates_adds_diabetes_candidate_with_hcc_relevant_true():
    patient = Patient(age=60, sex="male", diabetes=True)

    candidates = build_diagnosis_candidates(patient)

    assert any(c.name == "Diabetes mellitus" and c.hcc_relevant is True for c in candidates)


def test_build_diagnosis_candidates_adds_chronic_kidney_disease_candidate():
    patient = Patient(age=60, sex="male", egfr=55)

    candidates = build_diagnosis_candidates(patient)

    assert any(c.name == "Chronic kidney disease" for c in candidates)


def test_build_diagnosis_candidates_adds_albuminuria_candidate():
    patient = Patient(age=60, sex="male", uacr=45)

    candidates = build_diagnosis_candidates(patient)

    assert any(c.name == "Albuminuria" for c in candidates)


def test_build_diagnosis_candidates_returns_empty_list_when_no_features():
    patient = Patient(age=60, sex="male")

    candidates = build_diagnosis_candidates(patient)

    assert candidates == []
