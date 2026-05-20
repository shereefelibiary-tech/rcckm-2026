from core.enums import RiskLevel


def assign_risk_level(patient):
    if patient.clinical_ascvd:
        return RiskLevel.VERY_HIGH

    if patient.cac is not None and patient.cac >= 300:
        return RiskLevel.HIGH

    if patient.cac is not None and patient.cac >= 100:
        return RiskLevel.INTERMEDIATE

    if patient.cac is not None and patient.cac == 0:
        return RiskLevel.LOW

    return RiskLevel.BORDERLINE
