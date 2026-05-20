from core.patient import Patient
from core.enums import RiskLevel
from modules.risk.engine import assign_risk_level


def test_assign_risk_level_returns_very_high_for_clinical_ascvd():
    patient = Patient(age=60, sex="male", clinical_ascvd=True)

    result = assign_risk_level(patient)

    assert result == RiskLevel.VERY_HIGH


def test_assign_risk_level_returns_high_for_extensive_cac():
    patient = Patient(age=60, sex="male", cac=350)

    result = assign_risk_level(patient)

    assert result == RiskLevel.HIGH


def test_assign_risk_level_returns_intermediate_for_elevated_cac():
    patient = Patient(age=60, sex="male", cac=150)

    result = assign_risk_level(patient)

    assert result == RiskLevel.INTERMEDIATE


def test_assign_risk_level_returns_low_for_zero_cac():
    patient = Patient(age=60, sex="male", cac=0)

    result = assign_risk_level(patient)

    assert result == RiskLevel.LOW


def test_assign_risk_level_returns_borderline_when_cac_missing():
    patient = Patient(age=60, sex="male", cac=None)

    result = assign_risk_level(patient)

    assert result == RiskLevel.BORDERLINE
