from core.results import DiagnosisCandidate


HCC_SUPPORTED_BY_ICD = {
    "E11.22": "HCC-supported",
    "N18.31": "HCC-supported",
    "N18.32": "HCC-supported",
    "N18.4": "HCC-supported",
    "N18.5": "HCC-supported",
}


def _hcc_label_for_icd(icd10_code):
    if not icd10_code:
        return None
    return HCC_SUPPORTED_BY_ICD.get(str(icd10_code).strip().upper())


def data_derived_candidate(name, source, icd10_code=None):
    hcc_label = _hcc_label_for_icd(icd10_code)
    return DiagnosisCandidate(
        name=name,
        diagnosis=name,
        icd10_code=icd10_code,
        status="data-derived",
        source=source,
        hcc_relevant=bool(hcc_label),
        hcc_supported=bool(hcc_label),
        hcc_label=hcc_label,
        confidence="data-supported",
        review_status="review_suggested",
    )


def _num(value):
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _bmi_z_code(bmi):
    if bmi is None or bmi < 30:
        return None
    if bmi < 31:
        return ("Adult BMI 30.0-30.9", "Z68.30", "BMI 30.0-30.9 kg/m²")
    if bmi < 32:
        return ("Adult BMI 31.0-31.9", "Z68.31", "BMI 31.0-31.9 kg/m²")
    if bmi < 33:
        return ("Adult BMI 32.0-32.9", "Z68.32", "BMI 32.0-32.9 kg/m²")
    if bmi < 34:
        return ("Adult BMI 33.0-33.9", "Z68.33", "BMI 33.0-33.9 kg/m²")
    if bmi < 35:
        return ("Adult BMI 34.0-34.9", "Z68.34", "BMI 34.0-34.9 kg/m²")
    if bmi < 36:
        return ("Adult BMI 35.0-35.9", "Z68.35", "BMI 35.0-35.9 kg/m²")
    if bmi < 37:
        return ("Adult BMI 36.0-36.9", "Z68.36", "BMI 36.0-36.9 kg/m²")
    if bmi < 38:
        return ("Adult BMI 37.0-37.9", "Z68.37", "BMI 37.0-37.9 kg/m²")
    if bmi < 39:
        return ("Adult BMI 38.0-38.9", "Z68.38", "BMI 38.0-38.9 kg/m²")
    if bmi < 40:
        return ("Adult BMI 39.0-39.9", "Z68.39", "BMI 39.0-39.9 kg/m²")
    if bmi < 45:
        return ("Adult BMI 40.0-44.9", "Z68.41", "BMI 40.0-44.9 kg/m²")
    if bmi < 50:
        return ("Adult BMI 45.0-49.9", "Z68.42", "BMI 45.0-49.9 kg/m²")
    if bmi < 60:
        return ("Adult BMI 50.0-59.9", "Z68.43", "BMI 50.0-59.9 kg/m²")
    if bmi < 70:
        return ("Adult BMI 60.0-69.9", "Z68.44", "BMI 60.0-69.9 kg/m²")
    return ("Adult BMI 70 or greater", "Z68.45", "BMI >=70 kg/m²")


def _text_fields(patient, names):
    return "\n".join(
        str(getattr(patient, name, "") or "")
        for name in names
        if str(getattr(patient, name, "") or "").strip()
    )


def _problem_list_supports_hypertension(patient):
    if bool(getattr(patient, "hypertension", False)):
        return True

    text = _text_fields(
        patient,
        (
            "problem_list",
            "problem_list_text",
            "diagnoses_raw",
            "diagnosis_text",
            "clinical_diagnoses_raw",
            "conditions_raw",
        ),
    ).lower()
    if not text:
        return False
    text = text.replace("white coat hypertension", "")
    return any(term in text for term in ("essential hypertension", "hypertension", " htn", "\nhtn", "htn\n"))


def _medication_supports_hypertension(patient):
    if bool(getattr(patient, "bp_treated", False)) or bool(getattr(patient, "ace_arb", False)):
        return True

    meds = _text_fields(patient, ("medications_raw", "medication_list", "medications", "active_medications")).lower()
    if not meds:
        return False

    antihypertensive_patterns = (
        "lisinopril",
        "benazepril",
        "enalapril",
        "ramipril",
        "captopril",
        "losartan",
        "valsartan",
        "olmesartan",
        "irbesartan",
        "telmisartan",
        "candesartan",
        "amlodipine",
        "nifedipine",
        "diltiazem",
        "verapamil",
        "hydrochlorothiazide",
        "chlorthalidone",
        "indapamide",
        "metoprolol",
        "carvedilol",
        "atenolol",
        "bisoprolol",
        "propranolol",
        "spironolactone",
        "eplerenone",
    )
    if any(name in meds for name in antihypertensive_patterns):
        return True

    loop_diuretic = any(name in meds for name in ("furosemide", "torsemide", "bumetanide"))
    bp_or_hf_context = any(term in meds for term in ("hypertension", "htn", "heart failure", "hf", "blood pressure"))
    return loop_diuretic and bp_or_hf_context


def _bp_pairs(patient):
    pairs = []
    readings = getattr(patient, "bp_readings", None) or getattr(patient, "blood_pressure_readings", None)
    for reading in readings or []:
        sbp = dbp = None
        if isinstance(reading, dict):
            sbp = _num(reading.get("sbp"))
            dbp = _num(reading.get("dbp"))
        elif isinstance(reading, (tuple, list)) and len(reading) >= 2:
            sbp = _num(reading[0])
            dbp = _num(reading[1])
        if sbp is not None and dbp is not None:
            pairs.append((sbp, dbp))

    sbp = _num(getattr(patient, "sbp", None))
    dbp = _num(getattr(patient, "dbp", None))
    if sbp is not None and dbp is not None and (sbp, dbp) not in pairs:
        pairs.append((sbp, dbp))
    return pairs


def _elevated_bp_count(patient):
    return sum(1 for sbp, dbp in _bp_pairs(patient) if sbp >= 130 or dbp >= 80)


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

    def add_review_candidate(name, source, icd10_code=None):
        if name in candidate_names:
            return

        candidate = data_derived_candidate(
            name=name,
            source=source,
            icd10_code=icd10_code,
        )
        candidate.status = "review_suggested"
        candidate.confidence = "review-needed"
        candidate.review_status = "review_suggested"
        candidates.append(candidate)
        candidate_names.add(name)

    if patient.clinical_ascvd:
        context = str(getattr(patient, "clinical_ascvd_context", "") or "").strip()
        name = "Clinical ASCVD"
        if context:
            name = f"Clinical ASCVD / coronary artery disease with {context}"
        candidates.append(
            DiagnosisCandidate(
                name=name,
                diagnosis=name,
                icd10_code="I25.10" if context else None,
                status="reported",
                source=context or "clinical_ascvd flag",
                hcc_relevant=False,
                hcc_supported=False,
                hcc_label=None,
                confidence="reported",
                review_status="review_suggested",
            )
        )
        candidate_names.add(name)

    elevated_bp_count = _elevated_bp_count(patient)
    if _problem_list_supports_hypertension(patient):
        add_candidate(
            name="Essential hypertension",
            source="problem list",
            icd10_code="I10",
        )
    elif _medication_supports_hypertension(patient):
        add_candidate(
            name="Essential hypertension",
            source="antihypertensive therapy active",
            icd10_code="I10",
        )
    elif elevated_bp_count >= 2:
        add_candidate(
            name="Essential hypertension",
            source="repeated elevated BP readings",
            icd10_code="I10",
        )
    elif elevated_bp_count == 1:
        add_review_candidate(
            name="Elevated blood pressure reading",
            source="single elevated office BP",
            icd10_code="R03.0",
        )

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

    bmi = _num(getattr(patient, "bmi", None))
    if bmi is not None and bmi >= 40.0:
        add_candidate(
            name="Morbid obesity",
            source="BMI >=40 kg/m²",
            icd10_code="E66.01",
        )
    elif bmi is not None and bmi >= 30.0:
        add_candidate(
            name="Obesity",
            source="BMI >=30 kg/m²",
            icd10_code="E66.9",
        )
    z_code = _bmi_z_code(bmi)
    if z_code:
        z_name, z_icd, z_source = z_code
        add_candidate(
            name=z_name,
            source=z_source,
            icd10_code=z_icd,
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

    if patient.uacr is not None and 30 <= patient.uacr < 300:
        add_candidate(
            name="Moderately increased albuminuria",
            source="UACR 30-299 mg/g",
            icd10_code="R80.9",
        )

    if patient.uacr is not None and patient.uacr >= 300:
        add_candidate(
            name="Severely increased albuminuria",
            source="UACR >=300 mg/g",
            icd10_code="R80.9",
        )

    if bool(getattr(patient, "masld", False)):
        add_candidate(
            name="Metabolic dysfunction-associated steatotic liver disease",
            source="Problem list / documented fatty liver",
            icd10_code="K76.0",
        )

    if bool(getattr(patient, "osa", False)):
        add_candidate(
            name="Obstructive sleep apnea",
            source="Problem list",
            icd10_code="G47.33",
        )

    has_premature_family_history = bool(
        getattr(patient, "premature_fhx_ascvd", False)
        or getattr(patient, "family_history_premature_ascvd", False)
    )
    if patient.ldl_c is not None and (
        patient.ldl_c >= 190 or (patient.ldl_c >= 160 and has_premature_family_history)
    ):
        add_review_candidate(
            name="Possible familial hypercholesterolemia",
            source="LDL-C / family history pattern",
            icd10_code=None,
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
