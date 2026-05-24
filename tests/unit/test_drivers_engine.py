from core.patient import Patient
from core.results import RCCKMResult
from modules.drivers.engine import build_top_drivers


def test_build_top_drivers_uses_deterministic_clinical_priority():
    patient = Patient(
        age=60,
        sex="male",
        clinical_ascvd=True,
        cac=120,
        apob=118,
        a1c=7.1,
        lp_a_value=180,
        lp_a_unit="nmol/L",
    )

    drivers = build_top_drivers(patient, RCCKMResult())

    assert drivers == [
        "Clinical ASCVD",
        "CAC 120",
        "ApoB 118 mg/dL",
        "A1c 7.1%",
    ]


def test_build_top_drivers_puts_high_cac_first_without_clinical_ascvd():
    patient = Patient(
        age=60,
        sex="male",
        cac=350,
        apob=118,
        ldl_c=160,
        a1c=7.1,
    )

    drivers = build_top_drivers(patient, RCCKMResult())

    assert drivers == [
        "CAC 350",
        "ApoB 118 mg/dL",
        "A1c 7.1%",
    ]


def test_build_top_drivers_suppresses_ldl_when_apob_present_unless_ldl_190():
    patient = Patient(age=60, sex="male", apob=118, ldl_c=160)

    drivers = build_top_drivers(patient, RCCKMResult())

    assert drivers == ["ApoB 118 mg/dL"]

    patient.ldl_c = 190

    drivers = build_top_drivers(patient, RCCKMResult())

    assert drivers == [
        "Severe hypercholesterolemia / LDL-C 190 mg/dL (>=190)",
        "ApoB 118 mg/dL",
    ]


def test_build_top_drivers_compresses_diabetes_ckd_albuminuria():
    patient = Patient(age=60, sex="male", diabetes=True, egfr=55, uacr=45)
    result = RCCKMResult(
        egfr_stage="G3a",
        albuminuria_stage="A2",
        kdigo_stage="G3aA2",
    )

    drivers = build_top_drivers(patient, result)

    assert drivers == ["T2DM with CKD G3aA2"]


def test_build_top_drivers_returns_max_four_drivers():
    patient = Patient(
        age=60,
        sex="male",
        cac=350,
        apob=118,
        ldl_c=190,
        a1c=7.1,
        lp_a_value=180,
        lp_a_unit="nmol/L",
        smoker=True,
        triglycerides=220,
    )

    drivers = build_top_drivers(patient, RCCKMResult())

    assert drivers == [
        "CAC 350",
        "Severe hypercholesterolemia / LDL-C 190 mg/dL (>=190)",
        "ApoB 118 mg/dL",
        "A1c 7.1%",
    ]


def test_build_top_drivers_reserves_lpa_for_major_threshold():
    patient = Patient(age=60, sex="male", lp_a_value=80, lp_a_unit="nmol/L")

    assert build_top_drivers(patient, RCCKMResult()) == []

    patient.lp_a_value = 180

    assert build_top_drivers(patient, RCCKMResult()) == ["Lp(a) 180 nmol/L"]


def test_build_top_drivers_does_not_promote_hscrp_alone():
    patient = Patient(age=60, sex="male", hscrp=2.5)

    assert build_top_drivers(patient, RCCKMResult()) == []

    patient.psoriasis = True

    assert build_top_drivers(patient, RCCKMResult()) == ["hsCRP 2.5 mg/L"]


def test_build_top_drivers_reserves_triglycerides_for_severe_range():
    patient = Patient(age=60, sex="male", triglycerides=240)

    assert build_top_drivers(patient, RCCKMResult()) == []

    patient.triglycerides = 620

    assert build_top_drivers(patient, RCCKMResult()) == ["TG 620 mg/dL"]
