from typing import Optional


def identify_risk_enhancers(patient) -> list[str]:
    enhancers: list[str] = []

    apob = getattr(patient, "apob", None)
    if apob is not None and apob >= 120:
        enhancers.append("ApoB >=120 mg/dL")

    lp_a_value = getattr(patient, "lp_a_value", None)
    lp_a_unit = getattr(patient, "lp_a_unit", None)
    if lp_a_value is not None:
        if lp_a_unit == "nmol/L" and lp_a_value >= 125:
            enhancers.append("Elevated Lp(a)")
        elif lp_a_unit == "mg/dL" and lp_a_value >= 50:
            enhancers.append("Elevated Lp(a)")

    hscrp = getattr(patient, "hscrp", None)
    if hscrp is not None and hscrp >= 2:
        enhancers.append("hsCRP >=2 mg/L (confirm persistence)")

    inflammatory_contexts = []
    if getattr(patient, "rheumatoid_arthritis", False):
        inflammatory_contexts.append("rheumatoid arthritis")
    if getattr(patient, "sle", False):
        inflammatory_contexts.append("SLE")
    if getattr(patient, "psoriasis", False):
        inflammatory_contexts.append("psoriasis")
    if getattr(patient, "ibd", False):
        inflammatory_contexts.append("IBD")
    if getattr(patient, "hiv", False):
        inflammatory_contexts.append("HIV")
    if inflammatory_contexts:
        enhancers.append("Inflammatory/immune context: " + ", ".join(inflammatory_contexts))
    elif getattr(patient, "inflammatory_disease", False):
        enhancers.append("Inflammatory disease")

    if getattr(patient, "osa", False):
        enhancers.append("Sleep/hypoxia context: OSA")

    if getattr(patient, "masld", False):
        enhancers.append("Liver/metabolic context: MASLD")

    triglycerides = getattr(patient, "triglycerides", None)
    if triglycerides is not None and triglycerides >= 150:
        enhancers.append("Hypertriglyceridemia")

    if getattr(patient, "ckd", False):
        enhancers.append("CKD")

    if getattr(patient, "premature_fhx_ascvd", False) or getattr(
        patient, "family_history_premature_ascvd", False
    ):
        enhancers.append(
            getattr(patient, "family_history_summary", None)
            or "Family history of premature ASCVD"
        )

    return enhancers
