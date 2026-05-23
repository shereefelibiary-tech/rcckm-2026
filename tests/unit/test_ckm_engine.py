from core.patient import Patient
from core.results import RCCKMResult
from modules.ckm.engine import classify_ckm_stage


def test_classify_ckm_stage_4_for_clinical_ascvd():
    patient = Patient(age=60, sex="male", clinical_ascvd=True)

    result = classify_ckm_stage(patient, RCCKMResult())

    assert result["stage"] == 4
    assert result["drivers"] == ["Clinical ASCVD"]


def test_classify_ckm_stage_3_for_cac():
    patient = Patient(age=60, sex="male", cac=350)

    result = classify_ckm_stage(patient, RCCKMResult())

    assert result["stage"] == 3
    assert result["drivers"] == ["CAC 350"]


def test_classify_ckm_stage_3_for_kdigo():
    patient = Patient(age=60, sex="male")
    rcckm_result = RCCKMResult(
        egfr_stage="G3a",
        albuminuria_stage="A2",
        kdigo_stage="G3aA2",
    )

    result = classify_ckm_stage(patient, rcckm_result)

    assert result["stage"] == 3
    assert result["drivers"] == ["CKD G3aA2"]


def test_classify_ckm_stage_0_for_normal_kdigo_stage():
    patient = Patient(age=60, sex="male")
    rcckm_result = RCCKMResult(
        egfr_stage="G1",
        albuminuria_stage="A1",
        kdigo_stage="G1A1",
    )

    result = classify_ckm_stage(patient, rcckm_result)

    assert result["stage"] == 0
    assert result["drivers"] == []


def test_classify_ckm_stage_2_for_metabolic_risk():
    patient = Patient(age=60, sex="male", a1c=7.1, triglycerides=180)

    result = classify_ckm_stage(patient, RCCKMResult())

    assert result["stage"] == 2
    assert result["drivers"] == ["A1c 7.1%", "TG 180"]


def test_classify_ckm_stage_2_for_low_hdl():
    patient = Patient(age=60, sex="male", hdl_c=35)

    result = classify_ckm_stage(patient, RCCKMResult())

    assert result["stage"] == 2
    assert result["drivers"] == ["Low HDL 35"]


def test_classify_ckm_stage_1_for_bmi_and_prediabetes():
    patient = Patient(age=60, sex="male", bmi=32.1, a1c=5.9)

    result = classify_ckm_stage(patient, RCCKMResult())

    assert result["stage"] == 1
    assert result["drivers"] == ["BMI 32.1", "A1c 5.9%"]


def test_classify_ckm_stage_0_when_no_signals():
    patient = Patient(age=60, sex="male")

    result = classify_ckm_stage(patient, RCCKMResult())

    assert result["stage"] == 0
    assert result["drivers"] == []
