from core.patient import Patient
from modules.lipids.engine import classify_atherogenic_burden


def test_apob_missing():
    patient = Patient(age=50, sex="male")
    labels = classify_atherogenic_burden(patient)
    assert "ApoB not available" in labels


def test_apob_85_borderline():
    patient = Patient(age=50, sex="male", apob=85)
    labels = classify_atherogenic_burden(patient)
    assert "Borderline ApoB elevation" in labels


def test_apob_110_elevated():
    patient = Patient(age=50, sex="male", apob=110)
    labels = classify_atherogenic_burden(patient)
    assert "Elevated ApoB" in labels


def test_apob_140_severe():
    patient = Patient(age=50, sex="male", apob=140)
    labels = classify_atherogenic_burden(patient)
    assert "Severe ApoB elevation" in labels


def test_ldl_fallback_elevated():
    patient = Patient(age=50, sex="male", apob=None, ldl_c=170)
    labels = classify_atherogenic_burden(patient)
    assert "Elevated LDL-C" in labels


def test_ldl_severe_195():
    patient = Patient(age=50, sex="male", apob=None, ldl_c=195)
    labels = classify_atherogenic_burden(patient)
    assert "Severe LDL-C elevation" in labels


def test_non_hdl_200():
    patient = Patient(age=50, sex="male", non_hdl_c=200)
    labels = classify_atherogenic_burden(patient)
    assert "Elevated non-HDL-C" in labels


def test_triglycerides_550_severe():
    patient = Patient(age=50, sex="male", triglycerides=550)
    labels = classify_atherogenic_burden(patient)
    assert "Severe hypertriglyceridemia" in labels


def test_triglycerides_180():
    patient = Patient(age=50, sex="male", triglycerides=180)
    labels = classify_atherogenic_burden(patient)
    assert "Hypertriglyceridemia" in labels
