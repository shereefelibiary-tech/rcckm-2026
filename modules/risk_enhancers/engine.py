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
    if getattr(patient, "inflammatory_arthritis", False):
        inflammatory_contexts.append("inflammatory arthritis")
    if getattr(patient, "ibd", False):
        inflammatory_contexts.append("IBD")
    if inflammatory_contexts:
        enhancers.append("Inflammatory/immune context: " + ", ".join(inflammatory_contexts))
    elif getattr(patient, "inflammatory_disease", False):
        enhancers.append("Inflammatory disease")
    if getattr(patient, "hiv", False):
        if getattr(patient, "stable_art", False):
            enhancers.append("HIV on stable ART")
        else:
            enhancers.append("HIV-related risk enhancer")

    if getattr(patient, "south_asian_ancestry", False):
        enhancers.append("Higher-risk ancestry/context: South Asian ancestry")
    if getattr(patient, "filipino_ancestry", False):
        enhancers.append("Higher-risk ancestry/context: Filipino ancestry")
    if getattr(patient, "higher_risk_ancestry_context", None):
        enhancers.append(f"Higher-risk ancestry/context: {patient.higher_risk_ancestry_context}")

    if getattr(patient, "suspected_fh_hefh", False):
        enhancers.append("Suspected FH / HeFH pathway")

    if getattr(patient, "incidental_cac", False):
        severity = str(getattr(patient, "incidental_cac_severity", "") or "").strip()
        suffix = f" ({severity})" if severity else ""
        enhancers.append(f"Incidental CAC on noncardiac CT{suffix}")

    if getattr(patient, "active_cancer", False):
        enhancers.append("Active cancer context")
    elif getattr(patient, "cancer_survivor", False):
        if getattr(patient, "cancer_life_expectancy_gt_2y", False):
            enhancers.append("Cancer survivor context; life expectancy >2 years")
        else:
            enhancers.append("Cancer survivor context")

    if getattr(patient, "osa", False):
        enhancers.append("Sleep/hypoxia context: OSA")

    if getattr(patient, "masld", False):
        enhancers.append("Liver/metabolic context: MASLD")

    triglycerides = getattr(patient, "triglycerides", None)
    if triglycerides is not None and triglycerides >= 150:
        enhancers.append("Hypertriglyceridemia")

    if getattr(patient, "diabetes", False):
        diabetes_specific = []
        duration = getattr(patient, "diabetes_duration_years", None)
        abi = getattr(patient, "abi", None)
        if duration is not None and duration >= 10:
            diabetes_specific.append("diabetes duration >=10 years")
        if getattr(patient, "uacr", None) is not None and patient.uacr >= 30:
            diabetes_specific.append("albuminuria >=30 mg/g")
        if getattr(patient, "egfr", None) is not None and patient.egfr < 60:
            diabetes_specific.append("eGFR <60")
        if getattr(patient, "diabetic_retinopathy", False):
            diabetes_specific.append("retinopathy")
        if getattr(patient, "diabetic_neuropathy", False):
            diabetes_specific.append("neuropathy")
        if getattr(patient, "abi_lt_0_9", False) or (abi is not None and abi < 0.9):
            diabetes_specific.append("ABI <0.9")
        if diabetes_specific:
            enhancers.append("Diabetes-specific enhancer: " + ", ".join(diabetes_specific))

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
