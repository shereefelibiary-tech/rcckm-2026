from core.enums import RiskLevel
from modules.prevent.calculator import calculate_prevent_ascvd_10y
from modules.prevent.engine import classify_prevent_ascvd_risk


def assign_risk_level(patient):
    if patient.clinical_ascvd:
        return RiskLevel.VERY_HIGH

    if patient.cac is not None:
        if patient.cac >= 1000:
            return RiskLevel.VERY_HIGH

        if 300 <= patient.cac <= 999:
            return RiskLevel.HIGH

    ldl_c = getattr(patient, "ldl_c", None)
    apob = getattr(patient, "apob", None)
    if (ldl_c is not None and ldl_c >= 190) or (apob is not None and apob >= 140):
        return RiskLevel.HIGH

    if patient.cac is not None:
        if 100 <= patient.cac <= 299:
            return RiskLevel.INTERMEDIATE

        if 1 <= patient.cac <= 99:
            return RiskLevel.BORDERLINE

        if patient.cac == 0:
            return RiskLevel.LOW

    prevent_risk = classify_prevent_ascvd_risk(
        calculate_prevent_ascvd_10y(patient)
    )
    if prevent_risk is not None:
        return prevent_risk

    return RiskLevel.BORDERLINE
