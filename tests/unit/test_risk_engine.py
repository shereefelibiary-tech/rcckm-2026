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


def test_assign_risk_level_returns_very_high_for_cac_1000_or_higher():
    patient = Patient(age=60, sex="male", cac=1000)

    result = assign_risk_level(patient)

    assert result == RiskLevel.VERY_HIGH


def test_assign_risk_level_returns_intermediate_for_elevated_cac():
    patient = Patient(age=60, sex="male", cac=150)

    result = assign_risk_level(patient)

    assert result == RiskLevel.INTERMEDIATE


def test_assign_risk_level_returns_borderline_for_mild_cac():
    patient = Patient(age=60, sex="male", cac=50)

    result = assign_risk_level(patient)

    assert result == RiskLevel.BORDERLINE


def test_assign_risk_level_returns_low_for_zero_cac():
    patient = Patient(age=60, sex="male", cac=0)

    result = assign_risk_level(patient)

    assert result == RiskLevel.LOW


def test_assign_risk_level_returns_borderline_when_cac_missing():
    patient = Patient(age=60, sex="male", cac=None)

    result = assign_risk_level(patient)

    assert result == RiskLevel.BORDERLINE


def test_assign_risk_level_uses_prevent_low_when_cac_missing():
    patient = Patient(age=60, sex="male", prevent_10y_ascvd=2.9)

    result = assign_risk_level(patient)

    assert result == RiskLevel.LOW


def test_assign_risk_level_uses_prevent_borderline_when_cac_missing():
    patient = Patient(age=60, sex="male", prevent_10y_ascvd=3.0)

    result = assign_risk_level(patient)

    assert result == RiskLevel.BORDERLINE


def test_assign_risk_level_uses_prevent_intermediate_when_cac_missing():
    patient = Patient(age=60, sex="male", prevent_10y_ascvd=5.0)

    result = assign_risk_level(patient)

    assert result == RiskLevel.INTERMEDIATE


def test_assign_risk_level_uses_prevent_high_when_cac_missing():
    patient = Patient(age=60, sex="male", prevent_10y_ascvd=10.0)

    result = assign_risk_level(patient)

    assert result == RiskLevel.HIGH


def test_assign_risk_level_cac_overrides_prevent_when_cac_present():
    patient = Patient(age=60, sex="male", cac=0, prevent_10y_ascvd=10.0)

    result = assign_risk_level(patient)

    assert result == RiskLevel.LOW
