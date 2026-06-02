from core.patient import Patient
from modules.targets.engine import (
    APOB_TARGET_HIGH_RISK_PRIMARY_PREVENTION,
    APOB_TARGET_PRIMARY_PREVENTION_DEFAULT,
    APOB_TARGET_SECONDARY_PREVENTION_MINIMUM,
    APOB_TARGET_VERY_HIGH_RISK_ASCVD,
    LDL_TARGET_HIGH_RISK_PRIMARY_PREVENTION,
    LDL_TARGET_PRIMARY_PREVENTION_DEFAULT,
    LDL_TARGET_SECONDARY_PREVENTION_MINIMUM,
    LDL_TARGET_VERY_HIGH_RISK_ASCVD,
    NON_HDL_TARGET_HIGH_RISK_PRIMARY_PREVENTION,
    NON_HDL_TARGET_PRIMARY_PREVENTION_DEFAULT,
    NON_HDL_TARGET_SECONDARY_PREVENTION_MINIMUM,
    NON_HDL_TARGET_VERY_HIGH_RISK_ASCVD,
    assign_lipid_targets,
    build_target_result,
    is_very_high_risk_ascvd,
)


def test_lipid_target_constants_are_centralized():
    assert LDL_TARGET_PRIMARY_PREVENTION_DEFAULT == 100
    assert LDL_TARGET_HIGH_RISK_PRIMARY_PREVENTION == 70
    assert LDL_TARGET_SECONDARY_PREVENTION_MINIMUM == 70
    assert LDL_TARGET_VERY_HIGH_RISK_ASCVD == 55
    assert NON_HDL_TARGET_PRIMARY_PREVENTION_DEFAULT == 130
    assert NON_HDL_TARGET_HIGH_RISK_PRIMARY_PREVENTION == 100
    assert NON_HDL_TARGET_SECONDARY_PREVENTION_MINIMUM == 100
    assert NON_HDL_TARGET_VERY_HIGH_RISK_ASCVD == 85
    assert APOB_TARGET_PRIMARY_PREVENTION_DEFAULT == 90
    assert APOB_TARGET_HIGH_RISK_PRIMARY_PREVENTION == 80
    assert APOB_TARGET_SECONDARY_PREVENTION_MINIMUM == 80
    assert APOB_TARGET_VERY_HIGH_RISK_ASCVD == 65


def test_build_target_result_returns_clinical_ascvd_targets():
    patient = Patient(age=60, sex="female", clinical_ascvd=True)

    result = build_target_result(patient)

    assert result.ldl_c_target == 70
    assert result.non_hdl_c_target == 100
    assert result.apob_target == 80
    assert "PREVENT should not be used to de-risk" in result.rationale


def test_build_target_result_returns_very_high_risk_ascvd_targets():
    patient = Patient(
        age=65,
        sex="female",
        clinical_ascvd=True,
        clinical_ascvd_context="prior MI and ischemic stroke",
        diabetes=True,
        ldl_c=110,
    )

    result = build_target_result(patient)

    assert result.ldl_c_target == 55
    assert result.non_hdl_c_target == 85
    assert result.apob_target == 65
    assert "LDL-C <70 mg/dL is the minimum secondary-prevention threshold" in result.rationale


def test_build_target_result_returns_extensive_cac_targets():
    patient = Patient(age=65, sex="female", cac=350)

    result = build_target_result(patient)

    assert result.ldl_c_target == 70
    assert result.non_hdl_c_target == 100
    assert result.apob_target == 80
    assert "CAC 300-999" in result.rationale
    assert "Consider very-high-risk targets only when overall context supports intensification" in result.rationale


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
    assert result.apob_target == 65


def test_very_high_risk_ascvd_helper_uses_clinical_ascvd_plus_features():
    assert not is_very_high_risk_ascvd(Patient(age=61, sex="male", clinical_ascvd=False, cac=500))
    assert not is_very_high_risk_ascvd(Patient(age=60, sex="male", clinical_ascvd=True))
    assert is_very_high_risk_ascvd(Patient(age=60, sex="male", clinical_ascvd=True, diabetes=True))
    assert is_very_high_risk_ascvd(Patient(age=60, sex="male", clinical_ascvd=True, uacr=45))
    assert is_very_high_risk_ascvd(Patient(age=60, sex="male", clinical_ascvd=True, ldl_c=190))
    assert is_very_high_risk_ascvd(Patient(age=60, sex="male", clinical_ascvd=True, apob=130))
    assert is_very_high_risk_ascvd(Patient(age=60, sex="male", clinical_ascvd=True, lp_a_value=150, lp_a_unit="nmol/L"))
    assert is_very_high_risk_ascvd(Patient(age=60, sex="male", clinical_ascvd=True, cac=300))


def test_assign_lipid_targets_is_public_target_helper():
    patient = Patient(age=67, sex="male", clinical_ascvd=True, diabetes=True)

    result = assign_lipid_targets(patient)

    assert result.ldl_c_target == 55
    assert result.non_hdl_c_target == 85
    assert result.apob_target == 65


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


def test_build_target_result_apob_discussion_path_uses_moderate_target():
    patient = Patient(age=55, sex="male", ldl_c=146, apob=122)

    result = build_target_result(patient)

    assert result.ldl_c_target == 100
    assert result.non_hdl_c_target == 130
    assert result.apob_target == 90
    assert "ApoB >=100" in result.rationale


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
