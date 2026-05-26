from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from modules.risk_enhancers.breast_arterial_calcification import (
    has_breast_arterial_calcification,
)


PREVENT_ASCVD_EARLY_DISCUSSION_THRESHOLD = 3.0
PREVENT_ASCVD_STATIN_DISCUSSION_THRESHOLD = 5.0
PREVENT_ASCVD_INTERMEDIATE_THRESHOLD = 7.5
PREVENT_ASCVD_HIGH_THRESHOLD = 20.0
PREVENT_ASCVD_10YR_EARLY_DISCUSSION_THRESHOLD = PREVENT_ASCVD_EARLY_DISCUSSION_THRESHOLD
PREVENT_ASCVD_10YR_STATIN_DISCUSSION_THRESHOLD = PREVENT_ASCVD_STATIN_DISCUSSION_THRESHOLD
PREVENT_ASCVD_10YR_INTERMEDIATE_THRESHOLD = PREVENT_ASCVD_INTERMEDIATE_THRESHOLD
PREVENT_ASCVD_10YR_HIGH_THRESHOLD = PREVENT_ASCVD_HIGH_THRESHOLD

# These 30-year PREVENT-ASCVD bands are RCCKM interpretation bands used to
# support prevention intensity and shared decision-making. They should remain
# centralized/configurable because formal guideline implementation thresholds
# may evolve. 30-year ASCVD risk should not be treated as high near-term risk
# and should not automatically trigger high-intensity statin therapy without
# hard indications or major risk enhancers.
PREVENT_ASCVD_30YR_LOW_THRESHOLD = 10.0
PREVENT_ASCVD_30YR_ELEVATED_THRESHOLD = 15.0
PREVENT_ASCVD_30YR_HIGH_THRESHOLD = 30.0
PREVENT_ASCVD_30YR_VERY_HIGH_THRESHOLD = 50.0

LOW_10YR_HIGH_30YR_PATIENT_SUMMARY = (
    "Your short-term risk is low, but your longer-term risk is higher than expected. "
    "This does not mean an event is likely soon. It means prevention now may lower your risk over time."
)

LOW_10YR_HIGH_30YR_CLINICIAN_SUMMARY = (
    "Low 10-year ASCVD risk with elevated 30-year ASCVD risk. Use longer-term risk to guide "
    "prevention intensity, risk-enhancer review, and shared decision-making. Statin therapy is "
    "not automatic from 30-year risk alone, but may be reasonable when ApoB/LDL-C burden, "
    "CKD/albuminuria, premature family history, Lp(a), diabetes, smoking, hypertension, or "
    "CAC/plaque supports treatment."
)


@dataclass(frozen=True)
class PreventLipidRecommendation:
    """Structured PREVENT-ASCVD lipid interpretation for action renderers."""

    recommendation_strength: str
    intensity: str
    rationale: str
    patient_facing_summary: str
    emr_summary: str
    trace_rule_id: str
    ten_year_band: str = "unknown"
    thirty_year_band: str = "unknown"
    enhancers_present: tuple[str, ...] = ()
    missing_data_that_could_change_decision: tuple[str, ...] = ()


def _risk_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def classify_prevent_ascvd_lipid_band(risk_10yr: Any) -> str:
    """Classify 10-year PREVENT-ASCVD risk into lipid-decision bands."""
    risk = _risk_float(risk_10yr)
    if risk is None:
        return "unknown"
    if risk < PREVENT_ASCVD_EARLY_DISCUSSION_THRESHOLD:
        return "very_low_lt_3"
    if risk < PREVENT_ASCVD_STATIN_DISCUSSION_THRESHOLD:
        return "early_discussion_3_to_lt_5"
    if risk < PREVENT_ASCVD_INTERMEDIATE_THRESHOLD:
        return "discussion_5_to_lt_7_5"
    if risk < PREVENT_ASCVD_HIGH_THRESHOLD:
        return "intermediate_7_5_to_lt_20"
    return "high_ge_20"


def classify_prevent_ascvd_10yr_lipid_band(risk_10yr: Any) -> str:
    """Classify 10-year PREVENT-ASCVD risk into lipid-decision bands."""
    return classify_prevent_ascvd_lipid_band(risk_10yr)


def classify_prevent_ascvd_30yr_band(risk_30yr: Any) -> str:
    """Classify 30-year PREVENT-ASCVD risk into RCCKM interpretation bands."""
    risk = _risk_float(risk_30yr)
    if risk is None:
        return "unknown"
    if risk < PREVENT_ASCVD_30YR_LOW_THRESHOLD:
        return "low_lt_10"
    if risk < PREVENT_ASCVD_30YR_ELEVATED_THRESHOLD:
        return "mildly_elevated_10_to_lt_15"
    if risk < PREVENT_ASCVD_30YR_HIGH_THRESHOLD:
        return "elevated_15_to_lt_30"
    if risk < PREVENT_ASCVD_30YR_VERY_HIGH_THRESHOLD:
        return "high_30_to_lt_50"
    return "very_high_ge_50"


def get_major_lipid_risk_enhancers(patient: Any, engine_context: Any = None) -> dict[str, tuple[str, ...]]:
    """Group lipid-decision enhancers without counting missing data as risk."""
    result = engine_context
    ldl_c = _risk_float(getattr(patient, "ldl_c", None))
    apob = _risk_float(getattr(patient, "apob", None))
    cac = _risk_float(getattr(patient, "cac", None))
    uacr = _risk_float(getattr(patient, "uacr", None))
    egfr = _risk_float(getattr(patient, "egfr", None))
    tg = _risk_float(getattr(patient, "triglycerides", None))
    a1c = _risk_float(getattr(patient, "a1c", None))
    lp_a = _risk_float(getattr(patient, "lp_a_value", None))
    age = _risk_float(getattr(patient, "age", None))

    hard: list[str] = []
    major: list[str] = []
    supporting: list[str] = []
    missing: list[str] = []

    if bool(getattr(patient, "clinical_ascvd", False)):
        hard.append("clinical_ascvd")
    if ldl_c is not None and ldl_c >= 190:
        hard.append("ldl_c_ge_190")
    if bool(getattr(patient, "diabetes", False)) and age is not None and 40 <= age <= 75 and ldl_c is not None and ldl_c >= 70:
        hard.append("diabetes_age_40_75_ldl_ge_70")
    if cac is not None and cac >= 100:
        hard.append("cac_ge_100")
    elif cac is not None and cac > 0:
        major.append("cac_plaque_present")

    albuminuria_stage = getattr(result, "albuminuria_stage", None) if result is not None else None
    egfr_stage = getattr(result, "egfr_stage", None) if result is not None else None
    if albuminuria_stage in {"A2", "A3"} or (uacr is not None and uacr >= 30):
        major.append("albuminuria")
    if egfr_stage in {"G3a", "G3b", "G4", "G5"} or (egfr is not None and egfr < 60):
        major.append("ckd")
    if bool(getattr(patient, "diabetes", False)):
        major.append("diabetes")
    if bool(getattr(patient, "family_history_premature_ascvd", False)):
        major.append("premature_family_history")
    if lp_a is not None and (
        (str(getattr(patient, "lp_a_unit", "") or "").lower() == "mg/dl" and lp_a >= 50)
        or (str(getattr(patient, "lp_a_unit", "") or "").lower() != "mg/dl" and lp_a >= 125)
    ):
        major.append("elevated_lpa")
    if apob is not None and apob >= 120:
        major.append("apob_ge_120")
    elif apob is not None and apob >= 100:
        supporting.append("apob_ge_100")
    if ldl_c is not None and ldl_c >= 160:
        major.append("ldl_c_ge_160")
    elif ldl_c is not None and ldl_c >= 130:
        supporting.append("ldl_c_ge_130")
    if tg is not None and tg >= 150:
        supporting.append("persistent_hypertriglyceridemia")
    if a1c is not None and 5.7 <= a1c < 6.5:
        supporting.append("prediabetes")
    if bool(getattr(patient, "smoker", False)) or bool(getattr(patient, "smoking", False)):
        major.append("smoking")
    if bool(getattr(patient, "bp_treated", False)) or bool(getattr(patient, "hypertension", False)):
        supporting.append("hypertension")
    if bool(getattr(patient, "inflammatory_disease", False)) or bool(getattr(patient, "rheumatoid_arthritis", False)) or bool(getattr(patient, "systemic_lupus", False)) or bool(getattr(patient, "psoriasis", False)) or bool(getattr(patient, "ibd", False)):
        supporting.append("inflammatory_condition")
    if has_breast_arterial_calcification(patient):
        supporting.append("breast_arterial_calcification")
    hscrp = _risk_float(getattr(patient, "hscrp", None))
    if hscrp is not None and hscrp >= 2:
        supporting.append("hscrp_ge_2")

    if apob is None:
        missing.append("ApoB")
    if lp_a is None:
        missing.append("Lp(a)")
    if uacr is None:
        missing.append("UACR")
    if cac is None and bool(getattr(patient, "cac_not_done", False)):
        missing.append("CAC")

    return {
        "hard_indications": tuple(dict.fromkeys(hard)),
        "major_enhancers": tuple(dict.fromkeys(major)),
        "supporting_enhancers": tuple(dict.fromkeys(supporting)),
        "missing_data_that_could_change_decision": tuple(dict.fromkeys(missing)),
    }


def _enhancer_names(grouped: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    names: list[str] = []
    for key in ("hard_indications", "major_enhancers", "supporting_enhancers"):
        names.extend(grouped.get(key, ()))
    return tuple(dict.fromkeys(names))


def lipid_recommendation_from_prevent_band(
    patient: Any,
    risk_10yr: Any,
    risk_30yr: Any = None,
    enhancers: dict[str, bool] | None = None,
) -> PreventLipidRecommendation:
    """Return conservative lipid wording based on PREVENT-ASCVD band and enhancers."""
    band = classify_prevent_ascvd_10yr_lipid_band(risk_10yr)
    thirty_band = classify_prevent_ascvd_30yr_band(risk_30yr)
    grouped = get_major_lipid_risk_enhancers(patient, None)
    if enhancers:
        major_names = list(grouped["major_enhancers"])
        supporting_names = list(grouped["supporting_enhancers"])
        hard_names = list(grouped["hard_indications"])
        for key, value in enhancers.items():
            if not value:
                continue
            if key in {"clinical_ascvd", "ldl_c_ge_190", "diabetes_age_40_75_ldl_ge_70", "cac_ge_100"}:
                hard_names.append(key)
            elif key in {"ckd_albuminuria", "diabetes", "cac_plaque", "very_high_lipid_burden", "premature_family_history", "metabolic"}:
                major_names.append(key)
            else:
                supporting_names.append(key)
        grouped = {
            **grouped,
            "hard_indications": tuple(dict.fromkeys(hard_names)),
            "major_enhancers": tuple(dict.fromkeys(major_names)),
            "supporting_enhancers": tuple(dict.fromkeys(supporting_names)),
        }
    has_major_enhancer = bool(grouped["hard_indications"] or grouped["major_enhancers"])
    has_enhancer = bool(
        grouped["hard_indications"]
        or grouped["major_enhancers"]
        or grouped["supporting_enhancers"]
    )
    has_albuminuria = "albuminuria" in grouped["major_enhancers"] or bool(enhancers and enhancers.get("ckd_albuminuria"))
    risk_30 = _risk_float(risk_30yr)
    age = _risk_float(getattr(patient, "age", None))
    in_lifetime_age = bool(age is not None and 30 <= age <= 59)
    younger_lifetime_context = bool(
        in_lifetime_age
        and risk_30 is not None
        and risk_30 >= PREVENT_ASCVD_30YR_ELEVATED_THRESHOLD
        and has_major_enhancer
    )
    enhancers_present = _enhancer_names(grouped)
    missing = grouped["missing_data_that_could_change_decision"]

    def _rec(strength, intensity, rationale, patient_summary, emr, rule_id):
        return PreventLipidRecommendation(
            strength,
            intensity,
            rationale,
            patient_summary,
            emr,
            rule_id,
            ten_year_band=band,
            thirty_year_band=thirty_band,
            enhancers_present=enhancers_present,
            missing_data_that_could_change_decision=missing,
        )

    if band == "high_ge_20":
        return _rec(
            "recommended",
            "high",
            "10-year PREVENT-ASCVD risk >=20%.",
            "High 10-year artery disease risk generally supports stronger cholesterol-lowering treatment.",
            "High-intensity statin therapy is generally recommended for primary prevention given high ASCVD risk.",
            "prevent_lipid_10yr_ge20",
        )
    if band == "intermediate_7_5_to_lt_20":
        return _rec(
            "favored",
            "moderate",
            "10-year PREVENT-ASCVD risk 7.5% to <20%.",
            "Moderate 10-year artery disease risk generally favors cholesterol-lowering discussion.",
            "Moderate-intensity statin therapy is generally favored for primary prevention.",
            "prevent_lipid_10yr_7_5to20",
        )
    if band == "discussion_5_to_lt_7_5":
        if has_enhancer:
            return _rec(
                "reasonable",
                "moderate",
                "10-year PREVENT-ASCVD risk 5% to <7.5% with risk-enhancing factors.",
                "Risk factors beyond the calculator make cholesterol-lowering worth discussing.",
                "Moderate-intensity statin therapy is reasonable given borderline ASCVD risk with risk-enhancing factors.",
                "prevent_lipid_10yr_5to7_5_with_enhancer",
            )
        return _rec(
            "consider",
            "none",
            "10-year PREVENT-ASCVD risk 5% to <7.5% without major risk enhancers.",
            "This is a preference-sensitive zone for cholesterol-lowering discussion.",
            "Discuss lipid-lowering therapy based on patient preference, LDL-C/ApoB burden, and overall prevention goals.",
            "prevent_lipid_10yr_5to7_5_no_enhancer",
        )
    if band == "early_discussion_3_to_lt_5":
        if in_lifetime_age and thirty_band in {"high_30_to_lt_50", "very_high_ge_50"} and has_major_enhancer:
            return _rec(
                "reasonable",
                "moderate",
                LOW_10YR_HIGH_30YR_CLINICIAN_SUMMARY,
                LOW_10YR_HIGH_30YR_PATIENT_SUMMARY,
                "Low short-term ASCVD risk, but high longer-term ASCVD risk and risk-enhancing factors support a shared decision about moderate-intensity statin therapy.",
                "prevent_lipid_10yr_3to5_30yr_high_with_enhancer",
            )
        if younger_lifetime_context:
            if has_albuminuria:
                emr = "Short-term ASCVD risk is low, but albuminuria and longer-term risk make lipid-lowering worth discussing."
            else:
                emr = "Short-term ASCVD risk is low, but longer-term risk and risk-enhancing factors may make lipid-lowering worth discussing. Moderate-intensity statin therapy may be reasonable after shared decision-making."
            return _rec(
                "may_be_reasonable",
                "moderate",
                LOW_10YR_HIGH_30YR_CLINICIAN_SUMMARY,
                LOW_10YR_HIGH_30YR_PATIENT_SUMMARY,
                emr,
                "prevent_lipid_10yr_3to5_30yr_elevated_with_enhancer",
            )
        if in_lifetime_age and thirty_band in {"high_30_to_lt_50", "very_high_ge_50"}:
            return _rec(
                "consider",
                "none",
                LOW_10YR_HIGH_30YR_CLINICIAN_SUMMARY,
                LOW_10YR_HIGH_30YR_PATIENT_SUMMARY,
                "Low short-term ASCVD risk with high longer-term ASCVD risk; strengthen lifestyle prevention and review risk enhancers before medication decisions.",
                "prevent_lipid_10yr_3to5_30yr_high_no_enhancer",
            )
        return _rec(
            "lifestyle",
            "none",
            "10-year PREVENT-ASCVD risk 3% to <5% without meaningful enhancers.",
            "Short-term risk is low; lifestyle-focused prevention remains the main step.",
            "Continue lifestyle-focused prevention; reassess risk as clinical data evolve.",
            "prevent_lipid_10yr_3to5_30yr_low_no_enhancer",
        )
    if band == "very_low_lt_3":
        if in_lifetime_age and thirty_band in {"high_30_to_lt_50", "very_high_ge_50"} and has_major_enhancer:
            return _rec(
                "may_be_reasonable",
                "moderate",
                LOW_10YR_HIGH_30YR_CLINICIAN_SUMMARY,
                LOW_10YR_HIGH_30YR_PATIENT_SUMMARY,
                "Moderate-intensity statin therapy may be reasonable after shared decision-making given low short-term but high longer-term ASCVD risk with risk-enhancing factors.",
                "prevent_lipid_10yr_lt3_30yr_high_with_enhancer",
            )
        if in_lifetime_age and thirty_band in {"elevated_15_to_lt_30"} and has_major_enhancer:
            return _rec(
                "consider",
                "none",
                LOW_10YR_HIGH_30YR_CLINICIAN_SUMMARY,
                LOW_10YR_HIGH_30YR_PATIENT_SUMMARY,
                "Short-term ASCVD risk is low, but longer-term risk is elevated. Earlier lipid-lowering may be reasonable if risk-enhancing factors or ApoB/LDL-C burden support treatment.",
                "prevent_lipid_10yr_lt3_30yr_elevated_with_enhancer",
            )
        if in_lifetime_age and thirty_band in {"elevated_15_to_lt_30", "high_30_to_lt_50", "very_high_ge_50"}:
            return _rec(
                "consider",
                "none",
                LOW_10YR_HIGH_30YR_CLINICIAN_SUMMARY,
                LOW_10YR_HIGH_30YR_PATIENT_SUMMARY,
                "Continue lifestyle-focused prevention; short-term ASCVD risk is low and lipid-lowering therapy is not routinely indicated. Reassess ASCVD risk over time and complete risk-enhancer testing if results would change management.",
                "prevent_lipid_10yr_lt3_30yr_elevated_no_enhancer",
            )
        return _rec(
            "lifestyle",
            "none",
            "10-year PREVENT-ASCVD risk <3%.",
            "Short-term artery disease risk is low; focus on healthy prevention habits unless a major risk signal is present.",
            "Lifestyle-focused prevention; lipid-lowering therapy is not routinely indicated unless major risk-enhancing features are present.",
            "prevent_lipid_10yr_lt3_30yr_low_lifestyle",
        )
    return _rec(
        "lifestyle",
        "none",
        "PREVENT-ASCVD risk unavailable.",
        "More information may be needed before medication decisions.",
        "Lipid-lowering decision should be individualized after completing risk data.",
        "prevent_lipid_unknown",
    )
