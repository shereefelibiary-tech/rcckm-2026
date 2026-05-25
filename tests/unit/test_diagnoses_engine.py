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


def test_build_diagnosis_candidates_does_not_add_prediabetes_when_diabetes_true():
    patient = Patient(age=60, sex="male", a1c=5.9, diabetes=True)

    candidates = build_diagnosis_candidates(patient)

    assert not any(c.name == "Prediabetes" for c in candidates)


def test_build_diagnosis_candidates_adds_chronic_kidney_disease_candidate():
    patient = Patient(age=60, sex="male", egfr=55)

    candidates = build_diagnosis_candidates(patient)

    assert any(c.name == "Chronic kidney disease" for c in candidates)
    assert any(c.name == "Chronic kidney disease, stage 3a" for c in candidates)


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

    assert any(
        c.name == "Type 2 diabetes mellitus with diabetic chronic kidney disease"
        for c in candidates
    )


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


def test_build_diagnosis_candidates_adds_albuminuria_candidate():
    patient = Patient(age=60, sex="male", uacr=45)

    candidates = build_diagnosis_candidates(patient)

    assert any(c.name == "Albuminuria" for c in candidates)


def test_build_diagnosis_candidates_adds_severely_increased_albuminuria_candidate():
    patient = Patient(age=60, sex="male", uacr=300)

    candidates = build_diagnosis_candidates(patient)

    assert any(c.name == "Albuminuria" for c in candidates)
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

    assert any(c.name == "Elevated ApoB" for c in candidates)


def test_build_diagnosis_candidates_adds_hypertriglyceridemia():
    patient = Patient(age=60, sex="male", triglycerides=150)

    candidates = build_diagnosis_candidates(patient)

    assert any(c.name == "Hypertriglyceridemia" for c in candidates)


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
