from core.enums import DecisionStability


def assess_decision_stability(patient):
    if patient.apob is None or patient.lp_a_value is None or patient.uacr is None:
        if patient.cac is None:
            return DecisionStability.LOW
        return DecisionStability.MODERATE

    return DecisionStability.HIGH
