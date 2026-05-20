from typing import Optional


def identify_risk_enhancers(patient) -> list[str]:
    enhancers: list[str] = []

    lp_a_value = getattr(patient, "lp_a_value", None)
    lp_a_unit = getattr(patient, "lp_a_unit", None)
    if lp_a_value is not None:
        if lp_a_unit == "nmol/L" and lp_a_value >= 125:
            enhancers.append("Elevated Lp(a)")
        elif lp_a_unit == "mg/dL" and lp_a_value >= 50:
            enhancers.append("Elevated Lp(a)")

    hscrp = getattr(patient, "hscrp", None)
    if hscrp is not None and hscrp >= 2:
        enhancers.append("Elevated hsCRP")

    triglycerides = getattr(patient, "triglycerides", None)
    if triglycerides is not None and triglycerides >= 150:
        enhancers.append("Hypertriglyceridemia")

    if getattr(patient, "ckd", False):
        enhancers.append("CKD")

    if getattr(patient, "family_history_premature_ascvd", False):
        enhancers.append("Family history of premature ASCVD")

    return enhancers
