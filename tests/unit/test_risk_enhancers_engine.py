from core.patient import Patient
from modules.risk_enhancers.engine import identify_risk_enhancers


def test_identify_risk_enhancers_elevated_lpa_nmol():
    patient = Patient(age=50, sex="male", lp_a_value=130, lp_a_unit="nmol/L")
    enhancers = identify_risk_enhancers(patient)
    assert "Elevated Lp(a)" in enhancers


def test_identify_risk_enhancers_elevated_lpa_mgdl():
    patient = Patient(age=50, sex="female", lp_a_value=55, lp_a_unit="mg/dL")
    enhancers = identify_risk_enhancers(patient)
    assert "Elevated Lp(a)" in enhancers


def test_identify_risk_enhancers_hscrp():
    patient = Patient(age=50, sex="male", hscrp=2.5)
    enhancers = identify_risk_enhancers(patient)
    assert "Elevated hsCRP" in enhancers


def test_identify_risk_enhancers_triglycerides():
    patient = Patient(age=50, sex="male", triglycerides=160)
    enhancers = identify_risk_enhancers(patient)
    assert "Hypertriglyceridemia" in enhancers


def test_identify_risk_enhancers_ckd():
    patient = Patient(age=50, sex="male", ckd=True)
    enhancers = identify_risk_enhancers(patient)
    assert "CKD" in enhancers


def test_identify_risk_enhancers_family_history():
    patient = Patient(age=50, sex="male", family_history_premature_ascvd=True)
    enhancers = identify_risk_enhancers(patient)
    assert "Family history of premature ASCVD" in enhancers
