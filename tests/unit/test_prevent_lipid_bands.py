from __future__ import annotations

from core.patient import Patient
from modules.prevent.lipid_bands import (
    LOW_10YR_HIGH_30YR_APOB_PATIENT_SUMMARY,
    LOW_10YR_HIGH_30YR_CLINICIAN_SUMMARY,
    LOW_10YR_HIGH_30YR_PATIENT_SUMMARY,
    PREVENT_ASCVD_10YR_EARLY_DISCUSSION_THRESHOLD,
    PREVENT_ASCVD_10YR_HIGH_THRESHOLD,
    PREVENT_ASCVD_10YR_INTERMEDIATE_THRESHOLD,
    PREVENT_ASCVD_10YR_STATIN_DISCUSSION_THRESHOLD,
    PREVENT_ASCVD_30YR_ELEVATED_THRESHOLD,
    PREVENT_ASCVD_30YR_HIGH_THRESHOLD,
    PREVENT_ASCVD_30YR_LOW_THRESHOLD,
    PREVENT_ASCVD_30YR_VERY_HIGH_THRESHOLD,
    PREVENT_ASCVD_EARLY_DISCUSSION_THRESHOLD,
    PREVENT_ASCVD_HIGH_THRESHOLD,
    PREVENT_ASCVD_INTERMEDIATE_THRESHOLD,
    PREVENT_ASCVD_STATIN_DISCUSSION_THRESHOLD,
    classify_prevent_ascvd_10yr_lipid_band,
    classify_prevent_ascvd_30yr_band,
    classify_prevent_ascvd_lipid_band,
    get_major_lipid_risk_enhancers,
    lipid_recommendation_from_prevent_band,
)


def test_named_prevent_ascvd_lipid_threshold_constants():
    assert PREVENT_ASCVD_EARLY_DISCUSSION_THRESHOLD == 3.0
    assert PREVENT_ASCVD_STATIN_DISCUSSION_THRESHOLD == 5.0
    assert PREVENT_ASCVD_INTERMEDIATE_THRESHOLD == 7.5
    assert PREVENT_ASCVD_HIGH_THRESHOLD == 20.0
    assert PREVENT_ASCVD_10YR_EARLY_DISCUSSION_THRESHOLD == 3.0
    assert PREVENT_ASCVD_10YR_STATIN_DISCUSSION_THRESHOLD == 5.0
    assert PREVENT_ASCVD_10YR_INTERMEDIATE_THRESHOLD == 7.5
    assert PREVENT_ASCVD_10YR_HIGH_THRESHOLD == 20.0
    assert PREVENT_ASCVD_30YR_LOW_THRESHOLD == 10.0
    assert PREVENT_ASCVD_30YR_ELEVATED_THRESHOLD == 15.0
    assert PREVENT_ASCVD_30YR_HIGH_THRESHOLD == 30.0
    assert PREVENT_ASCVD_30YR_VERY_HIGH_THRESHOLD == 50.0


def test_prevent_ascvd_lipid_band_boundaries():
    assert classify_prevent_ascvd_lipid_band(None) == "unknown"
    assert classify_prevent_ascvd_lipid_band(2.99) == "very_low_lt_3"
    assert classify_prevent_ascvd_lipid_band(3.00) == "early_discussion_3_to_lt_5"
    assert classify_prevent_ascvd_lipid_band(4.99) == "early_discussion_3_to_lt_5"
    assert classify_prevent_ascvd_lipid_band(5.00) == "discussion_5_to_lt_7_5"
    assert classify_prevent_ascvd_lipid_band(7.49) == "discussion_5_to_lt_7_5"
    assert classify_prevent_ascvd_lipid_band(7.50) == "intermediate_7_5_to_lt_20"
    assert classify_prevent_ascvd_lipid_band(19.99) == "intermediate_7_5_to_lt_20"
    assert classify_prevent_ascvd_lipid_band(20.00) == "high_ge_20"
    assert classify_prevent_ascvd_10yr_lipid_band(3.00) == "early_discussion_3_to_lt_5"


def test_prevent_ascvd_30yr_band_boundaries():
    assert classify_prevent_ascvd_30yr_band(None) == "unknown"
    assert classify_prevent_ascvd_30yr_band("bad") == "unknown"
    assert classify_prevent_ascvd_30yr_band(9.99) == "low_lt_10"
    assert classify_prevent_ascvd_30yr_band(10.00) == "mildly_elevated_10_to_lt_15"
    assert classify_prevent_ascvd_30yr_band(14.99) == "mildly_elevated_10_to_lt_15"
    assert classify_prevent_ascvd_30yr_band(15.00) == "elevated_15_to_lt_30"
    assert classify_prevent_ascvd_30yr_band(29.99) == "elevated_15_to_lt_30"
    assert classify_prevent_ascvd_30yr_band(30.00) == "high_30_to_lt_50"
    assert classify_prevent_ascvd_30yr_band(49.99) == "high_30_to_lt_50"
    assert classify_prevent_ascvd_30yr_band(50.00) == "very_high_ge_50"


def test_prevent_band_recommendation_strengths():
    patient = Patient(age=50, sex="male")
    assert lipid_recommendation_from_prevent_band(patient, 2.99).recommendation_strength == "lifestyle"
    early = lipid_recommendation_from_prevent_band(patient, 3.0, 18.0, {"premature_family_history": True})
    assert early.recommendation_strength == "may_be_reasonable"
    assert "worth discussing" in early.emr_summary
    discussion = lipid_recommendation_from_prevent_band(patient, 5.0, 18.0, {"ldl_apob_burden": True})
    assert discussion.recommendation_strength == "reasonable"
    intermediate = lipid_recommendation_from_prevent_band(patient, 7.5)
    assert intermediate.recommendation_strength == "favored"
    high = lipid_recommendation_from_prevent_band(patient, 20.0)
    assert high.recommendation_strength == "recommended"


def test_low_10_year_high_30_year_summaries_are_standardized():
    patient = Patient(age=38, sex="male", family_history_premature_ascvd=True)
    recommendation = lipid_recommendation_from_prevent_band(
        patient,
        3.8,
        24.0,
        {"premature_family_history": True},
    )
    assert recommendation.patient_facing_summary == LOW_10YR_HIGH_30YR_PATIENT_SUMMARY
    assert recommendation.rationale == LOW_10YR_HIGH_30YR_CLINICIAN_SUMMARY
    assert "not automatic from 30-year risk alone" in recommendation.rationale


def test_low_10_year_elevated_30_year_apob_family_history_is_treatment_supported():
    patient = Patient(
        age=55,
        sex="male",
        apob=125,
        triglycerides=170,
        family_history_premature_ascvd=True,
    )

    recommendation = lipid_recommendation_from_prevent_band(patient, 2.8, 15.04)

    assert recommendation.recommendation_strength == "reasonable"
    assert recommendation.intensity == "moderate"
    assert recommendation.patient_facing_summary == LOW_10YR_HIGH_30YR_APOB_PATIENT_SUMMARY
    assert "elevated ApoB particle burden" in recommendation.emr_summary
    assert "premature family history" in recommendation.emr_summary
    assert "despite low 10-year ASCVD risk" in recommendation.emr_summary
    assert "if ApoB/LDL-C burden support treatment" not in recommendation.emr_summary
    assert recommendation.trace_rule_id == "prevent_lipid_10yr_lt3_30yr_elevated_apob_family_history"


def test_major_lipid_risk_enhancers_are_grouped_without_missing_as_positive():
    grouped = get_major_lipid_risk_enhancers(
        Patient(age=45, sex="male", ldl_c=164, apob=None, uacr=None, cac_not_done=True)
    )
    assert "ldl_c_ge_160" in grouped["major_enhancers"]
    assert "ApoB" in grouped["missing_data_that_could_change_decision"]
    assert "ApoB" not in grouped["major_enhancers"]
