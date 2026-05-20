from core.patient import Patient
from core.enums import DecisionStability
from modules.stability.engine import assess_decision_stability


def test_assess_decision_stability_high_when_all_values_present():
    patient = Patient(age=60, sex="female", apob=90, lp_a_value=20, uacr=15, cac=100)

    result = assess_decision_stability(patient)

    assert result == DecisionStability.HIGH


def test_assess_decision_stability_moderate_when_apob_missing_and_cac_present():
    patient = Patient(age=60, sex="female", apob=None, lp_a_value=20, uacr=15, cac=100)

    result = assess_decision_stability(patient)

    assert result == DecisionStability.MODERATE


def test_assess_decision_stability_low_when_apob_and_cac_missing():
    patient = Patient(age=60, sex="female", apob=None, lp_a_value=20, uacr=15, cac=None)

    result = assess_decision_stability(patient)

    assert result == DecisionStability.LOW
