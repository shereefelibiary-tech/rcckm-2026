from core.results import DiagnosisCandidate


def build_diagnosis_candidates(patient):
    candidates = []

    if patient.clinical_ascvd:
        candidates.append(
            DiagnosisCandidate(
                name="Clinical ASCVD",
                icd10_code=None,
                status="reported",
                source="clinical_ascvd flag",
                hcc_relevant=False,
            )
        )

    if patient.diabetes:
        candidates.append(
            DiagnosisCandidate(
                name="Diabetes mellitus",
                icd10_code=None,
                status="reported",
                source="diabetes flag",
                hcc_relevant=True,
            )
        )

    if patient.egfr is not None and patient.egfr < 60:
        candidates.append(
            DiagnosisCandidate(
                name="Chronic kidney disease",
                icd10_code=None,
                status="data-derived",
                source="eGFR <60",
                hcc_relevant=True,
            )
        )

    if patient.uacr is not None and patient.uacr >= 30:
        candidates.append(
            DiagnosisCandidate(
                name="Albuminuria",
                icd10_code=None,
                status="data-derived",
                source="UACR >=30 mg/g",
                hcc_relevant=False,
            )
        )

    return candidates
