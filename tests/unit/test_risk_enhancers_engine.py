from core.patient import Patient
from modules.risk_enhancers.engine import identify_risk_enhancers


def test_identify_risk_enhancers_elevated_lpa_nmol():
    patient = Patient(age=50, sex="male", lp_a_value=130, lp_a_unit="nmol/L")
    enhancers = identify_risk_enhancers(patient)
    assert "Elevated Lp(a)" in enhancers


def test_identify_risk_enhancers_elevated_lpa_mgdl():
    patient = Patient(age=50, sex="female", lp_a_value=55, lp_a_unit="mg/dL")
    enhancers = identify_risk_enhancers(patient)
    assert "Elevated Lp(a)" in enhancers


def test_identify_risk_enhancers_hscrp():
    patient = Patient(age=50, sex="male", hscrp=2.5)
    enhancers = identify_risk_enhancers(patient)
    assert "hsCRP >=2 mg/L (confirm persistence)" in enhancers
    assert "Elevated hsCRP" not in enhancers


def test_identify_risk_enhancers_triglycerides():
    patient = Patient(age=50, sex="male", triglycerides=160)
    enhancers = identify_risk_enhancers(patient)
    assert "Hypertriglyceridemia" in enhancers


def test_identify_risk_enhancers_ckd():
    patient = Patient(age=50, sex="male", ckd=True)
    enhancers = identify_risk_enhancers(patient)
    assert "CKD" in enhancers


def test_identify_risk_enhancers_family_history():
    patient = Patient(age=50, sex="male", family_history_premature_ascvd=True)
    enhancers = identify_risk_enhancers(patient)
    assert "Family history of premature ASCVD" in enhancers


def test_identify_risk_enhancers_separates_contexts():
    patient = Patient(
        age=50,
        sex="male",
        rheumatoid_arthritis=True,
        osa=True,
        masld=True,
    )

    enhancers = identify_risk_enhancers(patient)

    assert "Inflammatory/immune context: rheumatoid arthritis" in enhancers
    assert "Sleep/hypoxia context: OSA" in enhancers
    assert (
        "Liver/metabolic context: MASLD (metabolic dysfunction-associated steatotic liver disease)"
        in enhancers
    )


def test_identify_risk_enhancers_lpa_80_nmol_is_not_guideline_enhancer():
    patient = Patient(age=50, sex="male", lp_a_value=80, lp_a_unit="nmol/L")

    enhancers = identify_risk_enhancers(patient)

    assert "Elevated Lp(a)" not in enhancers


def test_identify_risk_enhancers_lpa_180_nmol_is_guideline_enhancer():
    patient = Patient(age=50, sex="male", lp_a_value=180, lp_a_unit="nmol/L")

    enhancers = identify_risk_enhancers(patient)

    assert "Elevated Lp(a)" in enhancers


def test_identify_risk_enhancers_apob_119_is_not_guideline_enhancer():
    patient = Patient(age=50, sex="male", apob=119)

    enhancers = identify_risk_enhancers(patient)

    assert "ApoB >=120 mg/dL" not in enhancers


def test_identify_risk_enhancers_apob_120_is_guideline_enhancer():
    patient = Patient(age=50, sex="male", apob=120)

    enhancers = identify_risk_enhancers(patient)

    assert "ApoB >=120 mg/dL" in enhancers
