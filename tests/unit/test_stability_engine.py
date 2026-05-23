from core.patient import Patient
from core.enums import DecisionStability
from modules.stability.engine import assess_decision_stability


def test_assess_decision_stability_high_when_all_values_present():
    patient = Patient(
        age=60,
        sex="female",
        apob=90,
        lp_a_value=20,
        uacr=15,
        cac=100,
    )

    result = assess_decision_stability(patient)

    assert result == DecisionStability.HIGH


def test_assess_decision_stability_moderate_when_cac_missing_with_borderline_prevent():
    patient = Patient(
        age=60,
        sex="female",
        apob=90,
        lp_a_value=20,
        uacr=15,
        cac=None,
        prevent_10y_ascvd=3.0,
    )

    result = assess_decision_stability(patient)

    assert result == DecisionStability.MODERATE


def test_assess_decision_stability_low_when_apob_and_lpa_missing():
    patient = Patient(
        age=60,
        sex="female",
        apob=None,
        lp_a_value=None,
        uacr=15,
        cac=100,
    )

    result = assess_decision_stability(patient)

    assert result == DecisionStability.LOW


def test_assess_decision_stability_moderate_when_diabetes_has_missing_uacr():
    patient = Patient(
        age=60,
        sex="female",
        apob=90,
        lp_a_value=20,
        uacr=None,
        cac=100,
        diabetes=True,
    )

    result = assess_decision_stability(patient)

    assert result == DecisionStability.MODERATE
