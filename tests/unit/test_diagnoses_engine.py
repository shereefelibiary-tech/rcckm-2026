from core.patient import Patient
from modules.diagnoses.engine import build_diagnosis_candidates


def test_build_diagnosis_candidates_adds_clinical_ascvd_candidate():
    patient = Patient(age=60, sex="male", clinical_ascvd=True)

    candidates = build_diagnosis_candidates(patient)

    assert any(c.name == "Clinical ASCVD" for c in candidates)


def test_build_diagnosis_candidates_uses_clinical_ascvd_context_and_suppresses_subclinical_cac():
    patient = Patient(
        age=60,
        sex="male",
        clinical_ascvd=True,
        clinical_ascvd_context="prior NSTEMI and PCI/stent",
        cac=350,
    )

    names = [candidate.name for candidate in build_diagnosis_candidates(patient)]

    assert "Clinical ASCVD / coronary artery disease with prior NSTEMI and PCI/stent" in names
    assert "Subclinical coronary atherosclerosis" not in names
    assert "Severe subclinical coronary atherosclerosis" not in names


def test_build_diagnosis_candidates_adds_hypertension_from_problem_list():
    patient = Patient(age=60, sex="male")
    patient.problem_list_text = "Essential hypertension"

    candidates = build_diagnosis_candidates(patient)

    candidate = next(c for c in candidates if c.name == "Essential hypertension")
    assert candidate.icd10_code == "I10"
    assert candidate.source == "problem list"


def test_build_diagnosis_candidates_adds_hypertension_from_antihypertensive_medication():
    patient = Patient(age=60, sex="male", medications_raw="losartan 50 mg daily")

    candidates = build_diagnosis_candidates(patient)

    candidate = next(c for c in candidates if c.name == "Essential hypertension")
    assert candidate.icd10_code == "I10"
    assert candidate.source == "antihypertensive therapy active"


def test_build_diagnosis_candidates_adds_hypertension_from_repeated_elevated_bp_readings():
    patient = Patient(age=60, sex="male")
    patient.bp_readings = [(142, 86), (136, 84), (128, 78)]

    candidates = build_diagnosis_candidates(patient)

    candidate = next(c for c in candidates if c.name == "Essential hypertension")
    assert candidate.icd10_code == "I10"
    assert candidate.source == "repeated elevated BP readings"


def test_build_diagnosis_candidates_adds_review_only_for_single_elevated_bp():
    patient = Patient(age=60, sex="male", sbp=166, dbp=100)

    candidates = build_diagnosis_candidates(patient)

    names = [candidate.name for candidate in candidates]
    candidate = next(c for c in candidates if c.name == "Elevated blood pressure reading")
    assert "Essential hypertension" not in names
    assert candidate.icd10_code == "R03.0"
    assert candidate.status == "review_suggested"
    assert candidate.source == "single elevated office BP"


def test_build_diagnosis_candidates_does_not_confirm_white_coat_hypertension_alone():
    patient = Patient(age=60, sex="male")
    patient.problem_list_text = "White coat hypertension"

    names = [candidate.name for candidate in build_diagnosis_candidates(patient)]

    assert "Essential hypertension" not in names


def test_build_diagnosis_candidates_adds_review_only_for_single_severe_bp():
    patient = Patient(age=60, sex="male", sbp=188, dbp=122)

    candidates = build_diagnosis_candidates(patient)

    names = [candidate.name for candidate in candidates]
    candidate = next(c for c in candidates if c.name == "Elevated blood pressure reading")
    assert "Essential hypertension" not in names
    assert not any("urgency" in name.lower() for name in names)
    assert candidate.status == "review_suggested"


def test_build_diagnosis_candidates_adds_diabetes_candidate_from_diabetes_flag():
    patient = Patient(age=60, sex="male", diabetes=True)

    candidates = build_diagnosis_candidates(patient)

    assert any(
        c.name == "Type 2 diabetes mellitus" and c.status == "data-derived"
        for c in candidates
    )


def test_build_diagnosis_candidates_adds_diabetes_candidate_from_a1c():
    patient = Patient(age=60, sex="male", a1c=6.5)

    candidates = build_diagnosis_candidates(patient)

    assert any(c.name == "Type 2 diabetes mellitus" for c in candidates)


def test_build_diagnosis_candidates_adds_prediabetes_candidate_from_a1c():
    patient = Patient(age=60, sex="male", a1c=5.9)

    candidates = build_diagnosis_candidates(patient)

    assert any(c.name == "Prediabetes" for c in candidates)
    assert any(c.name == "Hyperglycemia" for c in candidates)


def test_build_diagnosis_candidates_does_not_add_prediabetes_for_diabetes_range_a1c():
    patient = Patient(age=60, sex="male", a1c=7.0)

    candidates = build_diagnosis_candidates(patient)
    names = [candidate.name for candidate in candidates]

    assert "Type 2 diabetes mellitus" in names
    assert "Prediabetes" not in names


def test_build_diagnosis_candidates_does_not_add_prediabetes_when_diabetes_true():
    patient = Patient(age=60, sex="male", a1c=5.9, diabetes=True)

    candidates = build_diagnosis_candidates(patient)

    assert not any(c.name == "Prediabetes" for c in candidates)


def test_build_diagnosis_candidates_adds_chronic_kidney_disease_candidate():
    patient = Patient(age=60, sex="male", egfr=55)

    candidates = build_diagnosis_candidates(patient)

    assert any(c.name == "Chronic kidney disease" for c in candidates)
    stage = next(c for c in candidates if c.name == "Chronic kidney disease, stage 3a")
    assert stage.hcc_supported is True
    assert stage.hcc_label == "HCC-supported"


def test_build_diagnosis_candidates_adds_ckd_stage_3b_candidate():
    patient = Patient(age=60, sex="male", egfr=30)

    candidates = build_diagnosis_candidates(patient)

    assert any(c.name == "Chronic kidney disease, stage 3b" for c in candidates)


def test_build_diagnosis_candidates_adds_ckd_stage_4_candidate():
    patient = Patient(age=60, sex="male", egfr=15)

    candidates = build_diagnosis_candidates(patient)

    assert any(c.name == "Chronic kidney disease, stage 4" for c in candidates)


def test_build_diagnosis_candidates_adds_ckd_stage_5_candidate():
    patient = Patient(age=60, sex="male", egfr=14)

    candidates = build_diagnosis_candidates(patient)

    assert any(c.name == "Chronic kidney disease, stage 5" for c in candidates)


def test_build_diagnosis_candidates_adds_diabetes_with_ckd_candidate():
    patient = Patient(age=60, sex="male", diabetes=True, egfr=55)

    candidates = build_diagnosis_candidates(patient)

    candidate = next(
        c for c in candidates if c.name == "Type 2 diabetes mellitus with diabetic chronic kidney disease"
    )
    assert candidate.icd10_code == "E11.22"
    assert candidate.hcc_supported is True
    assert candidate.hcc_label == "HCC-supported"


def test_build_diagnosis_candidates_adds_diabetes_with_albuminuria_candidate():
    patient = Patient(age=60, sex="male", diabetes=True, uacr=45)

    candidates = build_diagnosis_candidates(patient)

    assert any(
        c.name == "Type 2 diabetes mellitus with albuminuria / kidney involvement"
        for c in candidates
    )


def test_build_diagnosis_candidates_does_not_add_generic_ckd_from_albuminuria_alone():
    patient = Patient(age=60, sex="male", uacr=45)

    candidates = build_diagnosis_candidates(patient)

    assert not any(c.name == "Chronic kidney disease" for c in candidates)


def test_build_diagnosis_candidates_uses_diabetes_kidney_involvement_for_g2a2():
    patient = Patient(age=60, sex="male", diabetes=True, egfr=64, uacr=38)

    names = [candidate.name for candidate in build_diagnosis_candidates(patient)]

    assert "Type 2 diabetes mellitus with albuminuria / kidney involvement" in names
    assert "Chronic kidney disease" not in names


def test_build_diagnosis_candidates_adds_moderately_increased_albuminuria_candidate():
    patient = Patient(age=60, sex="male", uacr=45)

    candidates = build_diagnosis_candidates(patient)

    candidate = next(c for c in candidates if c.name == "Moderately increased albuminuria")
    assert candidate.icd10_code == "R80.9"
    assert candidate.source == "UACR 30-299 mg/g"


def test_build_diagnosis_candidates_adds_severely_increased_albuminuria_candidate():
    patient = Patient(age=60, sex="male", uacr=300)

    candidates = build_diagnosis_candidates(patient)

    assert not any(c.name == "Moderately increased albuminuria" for c in candidates)
    assert any(c.name == "Severely increased albuminuria" for c in candidates)


def test_build_diagnosis_candidates_adds_subclinical_coronary_atherosclerosis():
    patient = Patient(age=60, sex="male", cac=10)

    candidates = build_diagnosis_candidates(patient)

    assert any(c.name == "Subclinical coronary atherosclerosis" for c in candidates)


def test_build_diagnosis_candidates_adds_severe_subclinical_coronary_atherosclerosis():
    patient = Patient(age=60, sex="male", cac=300)

    candidates = build_diagnosis_candidates(patient)

    assert any(c.name == "Subclinical coronary atherosclerosis" for c in candidates)
    assert any(
        c.name == "Severe subclinical coronary atherosclerosis"
        for c in candidates
    )


def test_build_diagnosis_candidates_does_not_mark_cac_as_clinical_ascvd():
    patient = Patient(age=60, sex="male", cac=38, clinical_ascvd=False)

    candidates = build_diagnosis_candidates(patient)
    names = [candidate.name for candidate in candidates]

    assert "Subclinical coronary atherosclerosis" in names
    assert "Clinical ASCVD" not in names


def test_build_diagnosis_candidates_adds_masld_from_confirmed_problem_list_signal():
    patient = Patient(age=60, sex="male", bmi=24, masld=True)

    candidates = build_diagnosis_candidates(patient)

    candidate = next(
        c for c in candidates
        if c.name == "Metabolic dysfunction-associated steatotic liver disease"
    )
    assert candidate.icd10_code == "K76.0"
    assert candidate.source == "Problem list / documented fatty liver"


def test_build_diagnosis_candidates_does_not_infer_masld_from_bmi_alone():
    patient = Patient(age=60, sex="male", bmi=45)

    names = [candidate.name for candidate in build_diagnosis_candidates(patient)]

    assert "Metabolic dysfunction-associated steatotic liver disease" not in names


def test_build_diagnosis_candidates_does_not_add_osa_from_suspected_sleep_apnea():
    patient = Patient(age=60, sex="male", osa=False)
    patient.sleep_apnea_review = True

    names = [candidate.name for candidate in build_diagnosis_candidates(patient)]

    assert "Obstructive sleep apnea" not in names


def test_build_diagnosis_candidates_adds_osa_from_confirmed_problem_list_signal():
    patient = Patient(age=60, sex="male", osa=True)

    candidates = build_diagnosis_candidates(patient)

    candidate = next(c for c in candidates if c.name == "Obstructive sleep apnea")
    assert candidate.icd10_code == "G47.33"
    assert candidate.source == "Problem list"


def test_build_diagnosis_candidates_adds_elevated_lpa_from_nmol():
    patient = Patient(age=60, sex="male", lp_a_value=125, lp_a_unit="nmol/L")

    candidates = build_diagnosis_candidates(patient)

    assert any(c.name == "Elevated lipoprotein(a)" for c in candidates)


def test_build_diagnosis_candidates_adds_elevated_lpa_from_mg_dl():
    patient = Patient(age=60, sex="male", lp_a_value=50, lp_a_unit="mg/dL")

    candidates = build_diagnosis_candidates(patient)

    assert any(c.name == "Elevated lipoprotein(a)" for c in candidates)


def test_build_diagnosis_candidates_does_not_add_elevated_apob_for_100_to_119():
    patient = Patient(age=60, sex="male", apob=119)

    candidates = build_diagnosis_candidates(patient)

    assert not any(c.name == "Elevated ApoB" for c in candidates)


def test_build_diagnosis_candidates_adds_elevated_apob_at_guideline_threshold():
    patient = Patient(age=60, sex="male", apob=120)

    candidates = build_diagnosis_candidates(patient)

    candidate = next(c for c in candidates if c.name == "Elevated ApoB")
    assert candidate.hcc_supported is False


def test_build_diagnosis_candidates_adds_possible_fh_review_candidate_for_ldl_190():
    patient = Patient(age=60, sex="male", ldl_c=192)

    candidates = build_diagnosis_candidates(patient)

    candidate = next(c for c in candidates if c.name == "Possible familial hypercholesterolemia")
    assert candidate.status == "review_suggested"
    assert candidate.review_status == "review_suggested"
    assert candidate.icd10_code is None


def test_build_diagnosis_candidates_adds_possible_fh_review_candidate_for_ldl_family_pattern():
    patient = Patient(
        age=60,
        sex="male",
        ldl_c=170,
        family_history_relationship="father",
        family_history_event_type="MI",
        family_history_age_at_event=49,
        family_history_premature_ascvd=True,
    )

    candidates = build_diagnosis_candidates(patient)

    candidate = next(c for c in candidates if c.name == "Possible familial hypercholesterolemia")
    assert candidate.status == "review_suggested"
    assert candidate.source == "LDL-C / family history pattern"


def test_build_diagnosis_candidates_adds_hypertriglyceridemia():
    patient = Patient(age=60, sex="male", triglycerides=150)

    candidates = build_diagnosis_candidates(patient)

    candidate = next(c for c in candidates if c.name == "Hypertriglyceridemia")
    assert candidate.hcc_supported is False


def test_build_diagnosis_candidates_does_not_add_obesity_for_bmi_below_30():
    patient = Patient(age=60, sex="male", bmi=29.9)

    candidates = build_diagnosis_candidates(patient)
    names = [candidate.name for candidate in candidates]

    assert "Obesity" not in names
    assert "Morbid obesity" not in names
    assert not any(name.startswith("Adult BMI") for name in names)


def test_build_diagnosis_candidates_adds_obesity_at_bmi_30():
    patient = Patient(age=60, sex="male", bmi=30.0)

    candidates = build_diagnosis_candidates(patient)

    obesity = next(candidate for candidate in candidates if candidate.name == "Obesity")
    bmi_code = next(candidate for candidate in candidates if candidate.name == "Adult BMI 30.0-30.9")
    assert obesity.icd10_code == "E66.9"
    assert obesity.source == "BMI >=30 kg/m²"
    assert bmi_code.icd10_code == "Z68.30"


def test_build_diagnosis_candidates_adds_obesity_and_adult_bmi_z_code():
    patient = Patient(age=60, sex="male", bmi=35.4)

    candidates = build_diagnosis_candidates(patient)

    assert any(candidate.name == "Obesity" and candidate.icd10_code == "E66.9" for candidate in candidates)
    bmi_code = next(candidate for candidate in candidates if candidate.name == "Adult BMI 35.0-35.9")
    assert bmi_code.icd10_code == "Z68.35"
    assert bmi_code.source == "BMI 35.0-35.9 kg/m²"


def test_build_diagnosis_candidates_adds_morbid_obesity_at_bmi_40():
    patient = Patient(age=60, sex="male", bmi=40.0)

    candidates = build_diagnosis_candidates(patient)
    names = [candidate.name for candidate in candidates]

    morbid_obesity = next(candidate for candidate in candidates if candidate.name == "Morbid obesity")
    bmi_code = next(candidate for candidate in candidates if candidate.name == "Adult BMI 40.0-44.9")
    assert "Obesity" not in names
    assert morbid_obesity.icd10_code == "E66.01"
    assert morbid_obesity.source == "BMI >=40 kg/m²"
    assert bmi_code.icd10_code == "Z68.41"


def test_build_diagnosis_candidates_adds_morbid_obesity_and_bmi_50_z_code():
    patient = Patient(age=60, sex="male", bmi=57.5)

    candidates = build_diagnosis_candidates(patient)

    assert any(
        candidate.name == "Morbid obesity" and candidate.icd10_code == "E66.01"
        for candidate in candidates
    )
    bmi_code = next(candidate for candidate in candidates if candidate.name == "Adult BMI 50.0-59.9")
    assert bmi_code.icd10_code == "Z68.43"


def test_build_diagnosis_candidates_adds_severe_hypertriglyceridemia():
    patient = Patient(age=60, sex="male", triglycerides=500)

    candidates = build_diagnosis_candidates(patient)

    assert any(c.name == "Hypertriglyceridemia" for c in candidates)
    assert any(c.name == "Severe hypertriglyceridemia" for c in candidates)


def test_build_diagnosis_candidates_avoids_duplicate_names():
    patient = Patient(age=60, sex="male", diabetes=True, a1c=7.1)

    candidates = build_diagnosis_candidates(patient)
    names = [candidate.name for candidate in candidates]

    assert names.count("Type 2 diabetes mellitus") == 1


def test_build_diagnosis_candidates_returns_empty_list_when_no_features():
    patient = Patient(age=60, sex="male")

    candidates = build_diagnosis_candidates(patient)

    assert candidates == []
