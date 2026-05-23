from core.enums import DecisionStability
from core.enums import RiskLevel
from modules.prevent.calculator import calculate_prevent_ascvd_10y
from modules.prevent.engine import classify_prevent_ascvd_risk


def assess_decision_stability(patient):
    missing_items = 0

    prevent_risk = classify_prevent_ascvd_risk(
        calculate_prevent_ascvd_10y(patient)
    )
    if patient.cac is None and prevent_risk in {
        RiskLevel.BORDERLINE,
        RiskLevel.INTERMEDIATE,
    }:
        missing_items += 1

    if patient.apob is None:
        missing_items += 1

    if patient.lp_a_value is None:
        missing_items += 1

    if patient.uacr is None and (patient.diabetes or patient.ckd):
        missing_items += 1

    if missing_items >= 2:
        return DecisionStability.LOW

    if missing_items == 1:
        return DecisionStability.MODERATE

    return DecisionStability.HIGH
