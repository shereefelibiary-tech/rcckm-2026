from core.patient import Patient
from modules.targets.engine import build_target_result


def test_build_target_result_returns_clinical_ascvd_targets():
    patient = Patient(age=65, sex="female", clinical_ascvd=True)

    result = build_target_result(patient)

    assert result.ldl_c_target == 55
    assert result.non_hdl_c_target == 85
    assert result.apob_target == 60


def test_build_target_result_returns_extensive_cac_targets():
    patient = Patient(age=65, sex="female", cac=350)

    result = build_target_result(patient)

    assert result.ldl_c_target == 70
    assert result.non_hdl_c_target == 100
    assert result.apob_target == 80
    assert "CAC 300-999" in result.rationale
    assert "very-high-risk targets may be reasonable" in result.rationale


def test_build_target_result_returns_elevated_cac_targets():
    patient = Patient(age=65, sex="female", cac=150)

    result = build_target_result(patient)

    assert result.ldl_c_target == 70
    assert result.non_hdl_c_target == 100
    assert result.apob_target == 80


def test_build_target_result_returns_no_target_for_zero_cac():
    patient = Patient(age=65, sex="female", cac=0)

    result = build_target_result(patient)

    assert result.ldl_c_target is None
    assert result.non_hdl_c_target is None
    assert result.apob_target is None


def test_build_target_result_returns_very_high_targets_for_cac_1000():
    patient = Patient(age=65, sex="female", cac=1000)

    result = build_target_result(patient)

    assert result.ldl_c_target == 55
    assert result.non_hdl_c_target == 85
    assert result.apob_target == 60


def test_build_target_result_returns_mild_cac_targets_for_cac_50():
    patient = Patient(age=65, sex="female", cac=50)

    result = build_target_result(patient)

    assert result.ldl_c_target == 100
    assert result.non_hdl_c_target == 130
    assert result.apob_target == 90


def test_build_target_result_returns_high_prevent_targets_without_cac():
    patient = Patient(age=65, sex="female", prevent_10y_ascvd=10.0)

    result = build_target_result(patient)

    assert result.ldl_c_target == 70
    assert result.non_hdl_c_target == 100
    assert result.apob_target == 80


def test_build_target_result_returns_intermediate_prevent_targets_without_cac():
    patient = Patient(age=65, sex="female", prevent_10y_ascvd=8.2)

    result = build_target_result(patient)

    assert result.ldl_c_target == 100
    assert result.non_hdl_c_target == 130
    assert result.apob_target == 90


def test_build_target_result_returns_borderline_prevent_targets_without_cac():
    patient = Patient(age=65, sex="female", prevent_10y_ascvd=3.5)

    result = build_target_result(patient)

    assert result.ldl_c_target == 100
    assert result.non_hdl_c_target == 130
    assert result.apob_target == 90


def test_build_target_result_returns_no_target_for_low_prevent_without_cac():
    patient = Patient(age=65, sex="female", prevent_10y_ascvd=2.0)

    result = build_target_result(patient)

    assert result.ldl_c_target is None
    assert result.non_hdl_c_target is None
    assert result.apob_target is None


def test_build_target_result_low_prevent_with_ldl_160_uses_moderate_target():
    patient = Patient(age=55, sex="female", ldl_c=165, prevent_10y_ascvd=2.0)

    result = build_target_result(patient)

    assert result.ldl_c_target == 100
    assert result.non_hdl_c_target == 130
    assert result.apob_target == 90


def test_build_target_result_low_prevent_with_30_year_risk_uses_moderate_target():
    patient = Patient(
        age=45,
        sex="female",
        prevent_10y_ascvd=2.0,
        prevent_30y_ascvd=12.0,
    )

    result = build_target_result(patient)

    assert result.ldl_c_target == 100
    assert result.non_hdl_c_target == 130
    assert result.apob_target == 90


def test_build_target_result_diabetes_age_40_to_75_uses_diabetes_target():
    patient = Patient(age=55, sex="male", diabetes=True)

    result = build_target_result(patient)

    assert result.ldl_c_target == 100
    assert result.non_hdl_c_target == 130
    assert result.apob_target == 90
    assert "Diabetes age 40-75" in result.rationale


def test_build_target_result_diabetes_with_albuminuria_uses_high_risk_target():
    patient = Patient(age=55, sex="male", diabetes=True, uacr=45)

    result = build_target_result(patient)

    assert result.ldl_c_target == 70
    assert result.non_hdl_c_target == 100
    assert result.apob_target == 80
    assert "additional risk factors" in result.rationale


def test_build_target_result_ckd_stage_3_age_40_to_75_uses_moderate_target():
    patient = Patient(age=55, sex="male", egfr=55)

    result = build_target_result(patient)

    assert result.ldl_c_target == 100
    assert result.non_hdl_c_target == 130
    assert result.apob_target == 90
    assert "CKD stage 3 or higher" in result.rationale


def test_build_target_result_cac_zero_does_not_derisk_diabetes_age_over_40():
    patient = Patient(age=55, sex="male", cac=0, diabetes=True)

    result = build_target_result(patient)

    assert result.ldl_c_target == 100
    assert result.non_hdl_c_target == 130
    assert result.apob_target == 90
