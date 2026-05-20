from typing import List


def classify_kidney_risk(patient) -> List[str]:
    findings: List[str] = []

    egfr = getattr(patient, "egfr", None)
    if egfr is not None and egfr < 60:
        findings.append("CKD by eGFR")

    uacr = getattr(patient, "uacr", None)
    if uacr is not None and uacr >= 30:
        findings.append("Albuminuria")
    if uacr is not None and uacr >= 300:
        findings.append("Severely increased albuminuria")

    if getattr(patient, "diabetes", False) and (
        (egfr is not None and egfr < 60) or (uacr is not None and uacr >= 30)
    ):
        findings.append("Diabetes with kidney involvement")

    return findings
