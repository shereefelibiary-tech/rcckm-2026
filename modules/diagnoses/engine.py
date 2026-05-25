from core.results import DiagnosisCandidate


def data_derived_candidate(name, source, icd10_code=None):
    return DiagnosisCandidate(
        name=name,
        icd10_code=icd10_code,
        status="data-derived",
        source=source,
        hcc_relevant=False,
    )


def build_diagnosis_candidates(patient):
    candidates = []
    candidate_names = set()

    def add_candidate(name, source, icd10_code=None):
        if name in candidate_names:
            return

        candidates.append(
            data_derived_candidate(
                name=name,
                source=source,
                icd10_code=icd10_code,
            )
        )
        candidate_names.add(name)

    if patient.clinical_ascvd:
        context = str(getattr(patient, "clinical_ascvd_context", "") or "").strip()
        name = "Clinical ASCVD"
        if context:
            name = f"Clinical ASCVD / coronary artery disease with {context}"
        candidates.append(
            DiagnosisCandidate(
                name=name,
                icd10_code="I25.10" if context else None,
                status="reported",
                source=context or "clinical_ascvd flag",
                hcc_relevant=False,
            )
        )
        candidate_names.add(name)

    a1c = getattr(patient, "a1c", None)
    if patient.diabetes or (a1c is not None and a1c >= 6.5):
        add_candidate(
            name="Type 2 diabetes mellitus",
            source="diabetes flag" if patient.diabetes else "A1c >=6.5%",
            icd10_code="E11.9",
        )

    if a1c is not None and 5.7 <= a1c <= 6.4 and patient.diabetes is not True:
        add_candidate(
            name="Prediabetes",
            source="A1c 5.7-6.4%",
            icd10_code="R73.03",
        )

    if a1c is not None and a1c >= 5.7 and patient.diabetes is not True:
        add_candidate(
            name="Hyperglycemia",
            source="A1c >=5.7%",
            icd10_code="R73.9",
        )

    has_reduced_egfr = patient.egfr is not None and patient.egfr < 60
    has_albuminuria = patient.uacr is not None and patient.uacr >= 30
    if patient.diabetes and has_reduced_egfr:
        add_candidate(
            name="Type 2 diabetes mellitus with diabetic chronic kidney disease",
            source="diabetes flag with eGFR <60",
            icd10_code="E11.22",
        )

    if patient.diabetes and has_albuminuria and not has_reduced_egfr:
        add_candidate(
            name="Type 2 diabetes mellitus with albuminuria / kidney involvement",
            source="diabetes flag with UACR >=30 mg/g",
            icd10_code="E11.29",
        )

    if has_reduced_egfr:
        add_candidate(
            name="Chronic kidney disease",
            source="eGFR <60",
            icd10_code="N18.9",
        )

    if patient.egfr is not None and 45 <= patient.egfr <= 59:
        add_candidate(
            name="Chronic kidney disease, stage 3a",
            source="eGFR 45-59",
            icd10_code="N18.31",
        )

    if patient.egfr is not None and 30 <= patient.egfr <= 44:
        add_candidate(
            name="Chronic kidney disease, stage 3b",
            source="eGFR 30-44",
            icd10_code="N18.32",
        )

    if patient.egfr is not None and 15 <= patient.egfr <= 29:
        add_candidate(
            name="Chronic kidney disease, stage 4",
            source="eGFR 15-29",
            icd10_code="N18.4",
        )

    if patient.egfr is not None and patient.egfr < 15:
        add_candidate(
            name="Chronic kidney disease, stage 5",
            source="eGFR <15",
            icd10_code="N18.5",
        )

    if patient.uacr is not None and patient.uacr >= 30:
        add_candidate(
            name="Albuminuria",
            source="UACR >=30 mg/g",
            icd10_code="R80.9",
        )

    if patient.uacr is not None and patient.uacr >= 300:
        add_candidate(
            name="Severely increased albuminuria",
            source="UACR >=300 mg/g",
            icd10_code="R80.9",
        )

    if not patient.clinical_ascvd and patient.cac is not None and patient.cac > 0:
        add_candidate(
            name="Subclinical coronary atherosclerosis",
            source="CAC >0",
            icd10_code="I25.10",
        )

    if not patient.clinical_ascvd and patient.cac is not None and patient.cac >= 300:
        add_candidate(
            name="Severe subclinical coronary atherosclerosis",
            source="CAC >=300",
            icd10_code="I25.10",
        )

    if patient.lp_a_value is not None:
        if patient.lp_a_unit == "nmol/L" and patient.lp_a_value >= 125:
            add_candidate(
                name="Elevated lipoprotein(a)",
                source="Lp(a) >=125 nmol/L",
                icd10_code="E78.41",
            )
        elif patient.lp_a_unit == "mg/dL" and patient.lp_a_value >= 50:
            add_candidate(
                name="Elevated lipoprotein(a)",
                source="Lp(a) >=50 mg/dL",
                icd10_code="E78.41",
            )

    if patient.apob is not None and patient.apob >= 120:
        add_candidate(
            name="Elevated ApoB",
            source="ApoB >=120 mg/dL",
            icd10_code="E78.89",
        )

    if patient.ldl_c is not None and patient.ldl_c >= 190:
        add_candidate(
            name="Severe hypercholesterolemia",
            source="LDL-C >=190 mg/dL",
            icd10_code="E78.00",
        )

    if patient.triglycerides is not None and patient.triglycerides >= 150:
        add_candidate(
            name="Hypertriglyceridemia",
            source="triglycerides >=150 mg/dL",
            icd10_code="E78.1",
        )

    if patient.triglycerides is not None and patient.triglycerides >= 500:
        add_candidate(
            name="Severe hypertriglyceridemia",
            source="triglycerides >=500 mg/dL",
            icd10_code="E78.1",
        )

    return candidates
