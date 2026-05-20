from core.patient import Patient
from modules.targets.engine import build_target_result


def test_build_target_result_returns_clinical_ascvd_targets():
    patient = Patient(age=65, sex="female", clinical_ascvd=True)

    result = build_target_result(patient)

    assert result.ldl_c_target == 55
    assert result.non_hdl_c_target == 85
    assert result.rationale == "Clinical ASCVD: intensive secondary prevention target pathway."


def test_build_target_result_returns_extensive_cac_targets():
    patient = Patient(age=65, sex="female", cac=350)

    result = build_target_result(patient)

    assert result.ldl_c_target == 70
    assert result.non_hdl_c_target == 100


def test_build_target_result_returns_elevated_cac_targets():
    patient = Patient(age=65, sex="female", cac=150)

    result = build_target_result(patient)

    assert result.ldl_c_target == 100
    assert result.non_hdl_c_target == 130


def test_build_target_result_returns_no_target_for_zero_cac():
    patient = Patient(age=65, sex="female", cac=0)

    result = build_target_result(patient)

    assert result.ldl_c_target is None
    assert result.non_hdl_c_target is None
