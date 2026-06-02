from core.enums import RiskLevel
from core.patient import Patient
from core.results import RCCKMResult
from modules.cac_recommendation.engine import build_cac_recommendation


def test_build_cac_recommendation_returns_none_when_cac_present():
    patient = Patient(age=60, sex="male", cac=0)
    result = RCCKMResult(prevent_risk_category=RiskLevel.INTERMEDIATE)

    assert build_cac_recommendation(patient, result) is None


def test_build_cac_recommendation_for_borderline_prevent_without_cac():
    patient = Patient(
        age=60,
        sex="male",
        cac=None,
        family_history_premature_ascvd=True,
    )
    result = RCCKMResult(prevent_risk_category=RiskLevel.BORDERLINE)

    assert (
        build_cac_recommendation(patient, result)
        == "CAC may clarify risk."
    )


def test_build_cac_recommendation_for_intermediate_prevent_without_cac():
    patient = Patient(age=60, sex="male", cac=None)
    result = RCCKMResult(prevent_risk_category=RiskLevel.INTERMEDIATE)

    assert (
        build_cac_recommendation(patient, result)
        == "CAC may clarify risk."
    )


def test_build_cac_recommendation_for_high_prevent_without_cac():
    patient = Patient(age=60, sex="male", cac=None)
    result = RCCKMResult(prevent_risk_category=RiskLevel.HIGH)

    assert (
        build_cac_recommendation(patient, result)
        == "CAC may clarify risk."
    )


def test_build_cac_recommendation_returns_none_for_low_prevent_without_cac():
    patient = Patient(age=60, sex="male", cac=None)
    result = RCCKMResult(prevent_risk_category=RiskLevel.LOW)

    assert build_cac_recommendation(patient, result) is None


def test_build_cac_recommendation_for_near_level_3_lipid_trajectory():
    patient = Patient(
        age=40,
        sex="male",
        cac=None,
        ldl_c=158,
        apob=116,
    )
    result = RCCKMResult(
        prevent_risk_category=RiskLevel.LOW,
        prevent_10y_ascvd=1.41,
        prevent_30y_ascvd=9.82,
    )

    assert (
        build_cac_recommendation(patient, result)
        == "CAC may clarify risk."
    )


def test_build_cac_recommendation_for_treatment_relevant_lipid_trajectory():
    patient = Patient(
        age=42,
        sex="male",
        cac=None,
        ldl_c=166,
        apob=121,
        non_hdl_c=202,
        triglycerides=182,
    )
    result = RCCKMResult(
        prevent_risk_category=RiskLevel.LOW,
        prevent_10y_ascvd=1.73,
        prevent_30y_ascvd=11.85,
    )

    assert (
        build_cac_recommendation(patient, result)
        == "CAC may clarify risk."
    )


def test_cac_age_gate_for_men():
    result = RCCKMResult(prevent_risk_category=RiskLevel.LOW)

    assert build_cac_recommendation(Patient(age=39, sex="male", cac=None), result) is None
    assert (
        build_cac_recommendation(Patient(age=40, sex="male", ldl_c=130, cac=None), result)
        == "CAC may clarify risk."
    )


def test_cac_age_gate_for_women():
    result = RCCKMResult(prevent_risk_category=RiskLevel.LOW)

    assert build_cac_recommendation(Patient(age=39, sex="female", cac=None), result) is None
    assert (
        build_cac_recommendation(Patient(age=40, sex="female", ldl_c=130, cac=None), result)
        == "CAC may clarify risk."
    )


def test_cac_not_recommended_for_clinical_ascvd_or_measured_cac():
    result = RCCKMResult(prevent_risk_category=RiskLevel.INTERMEDIATE)

    assert build_cac_recommendation(Patient(age=55, sex="male", clinical_ascvd=True, cac=None), result) is None
    assert build_cac_recommendation(Patient(age=55, sex="male", cac=0), result) is None
    assert build_cac_recommendation(Patient(age=55, sex="male", cac=120), result) is None
    assert build_cac_recommendation(Patient(age=55, sex="male", ldl_c=190, cac=None), result) == "CAC may clarify risk."


def test_cac_may_clarify_risk_with_diabetes_or_ckd_signals():
    result = RCCKMResult(prevent_risk_category=RiskLevel.INTERMEDIATE, egfr_stage="G3a")

    assert build_cac_recommendation(Patient(age=55, sex="male", diabetes=True, cac=None), result) == "CAC may clarify risk."
    assert build_cac_recommendation(Patient(age=55, sex="male", egfr=55, cac=None), result) == "CAC may clarify risk."
