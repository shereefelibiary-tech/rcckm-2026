from core.patient import Patient
from modules.kidney.engine import classify_kidney_risk


def test_egfr_55_ckd_by_egfr():
    patient = Patient(age=60, sex="male", egfr=55)
    labels = classify_kidney_risk(patient)
    assert "CKD by eGFR" in labels


def test_uacr_45_albuminuria():
    patient = Patient(age=60, sex="male", uacr=45)
    labels = classify_kidney_risk(patient)
    assert "Albuminuria" in labels


def test_uacr_350_severe_albuminuria():
    patient = Patient(age=60, sex="male", uacr=350)
    labels = classify_kidney_risk(patient)
    assert "Severely increased albuminuria" in labels


def test_diabetes_with_egfr_returns_diabetes_with_kidney_involvement():
    patient = Patient(age=60, sex="male", diabetes=True, egfr=55)
    labels = classify_kidney_risk(patient)
    assert "Diabetes with kidney involvement" in labels


def test_diabetes_with_uacr_returns_diabetes_with_kidney_involvement():
    patient = Patient(age=60, sex="male", diabetes=True, uacr=45)
    labels = classify_kidney_risk(patient)
    assert "Diabetes with kidney involvement" in labels
