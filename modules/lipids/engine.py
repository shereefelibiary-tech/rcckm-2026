from typing import List


def classify_atherogenic_burden(patient) -> List[str]:
    findings: List[str] = []

    apob = getattr(patient, "apob", None)
    if apob is None:
        findings.append("ApoB missing")
    else:
        if apob >= 130:
            findings.append("Severe ApoB elevation")
        elif apob >= 100:
            findings.append("Elevated ApoB")
        elif apob >= 80:
            findings.append("Borderline ApoB elevation")

    # LDL-C fallback only when ApoB is missing
    if apob is None:
        ldl = getattr(patient, "ldl_c", None)
        if ldl is not None:
            if ldl >= 190:
                findings.append("Severe LDL-C elevation")
            elif ldl >= 160:
                findings.append("Elevated LDL-C")
            elif ldl >= 130:
                findings.append("Borderline LDL-C elevation")

    non_hdl = getattr(patient, "non_hdl_c", None)
    if non_hdl is not None:
        if non_hdl >= 220:
            findings.append("Severe non-HDL-C elevation")
        elif non_hdl >= 190:
            findings.append("Elevated non-HDL-C")

    triglycerides = getattr(patient, "triglycerides", None)
    if triglycerides is not None:
        if triglycerides >= 500:
            findings.append("Severe hypertriglyceridemia")
        elif triglycerides >= 150:
            findings.append("Hypertriglyceridemia")

    return findings
