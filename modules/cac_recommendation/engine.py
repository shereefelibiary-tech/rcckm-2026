from core.enums import RiskLevel
from modules.levels.level_classifier import _hidden_risk_cluster
from modules.occult_risk import has_occult_lipid_discussion_path


def _risk_value(risk_category):
    return getattr(risk_category, "value", risk_category)


def _sex_key(patient):
    sex = str(getattr(patient, "sex", "") or "").strip().lower()
    if sex.startswith("f"):
        return "female"
    if sex.startswith("m"):
        return "male"
    return ""


def meets_cac_age_gate(patient):
    age = getattr(patient, "age", None)
    if age is None:
        return False
    return age >= 40


def _below_cac_age_gate(patient):
    age = getattr(patient, "age", None)
    if age is None:
        return False
    return age < 40


def _has_diabetes(patient):
    a1c = getattr(patient, "a1c", None)
    return bool(getattr(patient, "diabetes", False)) or (
        a1c is not None and a1c >= 6.5
    )


def _has_ckd_stage_3_or_higher(patient, result):
    egfr_stage = getattr(result, "egfr_stage", None)
    egfr = getattr(patient, "egfr", None)
    return bool(getattr(patient, "ckd", False)) or egfr_stage in {
        "G3a",
        "G3b",
        "G4",
        "G5",
    } or (egfr is not None and egfr < 60)


def _has_elevated_lpa(patient):
    value = getattr(patient, "lp_a_value", None)
    unit = str(getattr(patient, "lp_a_unit", "") or "").strip()
    return (
        unit == "nmol/L"
        and value is not None
        and value >= 125
    ) or (
        unit == "mg/dL"
        and value is not None
        and value >= 50
    )


def _has_strong_enhancer(patient):
    ldl_c = getattr(patient, "ldl_c", None)
    apob = getattr(patient, "apob", None)
    return bool(
        getattr(patient, "premature_fhx_ascvd", False)
        or getattr(patient, "family_history_premature_ascvd", False)
        or getattr(patient, "smoker", False)
        or getattr(patient, "smoking", False)
        or _has_elevated_lpa(patient)
        or (apob is not None and apob >= 100)
        or (ldl_c is not None and 160 <= ldl_c <= 189)
        or _has_diabetes(patient)
        or bool(getattr(patient, "inflammatory_disease", False))
    )


def _has_lpa_plus_family_history(patient):
    return bool(
        _has_elevated_lpa(patient)
        and (
            getattr(patient, "premature_fhx_ascvd", False)
            or getattr(patient, "family_history_premature_ascvd", False)
        )
    )


def _has_reproductive_marker(patient):
    return any(
        bool(getattr(patient, field, False))
        for field in (
            "early_menopause",
            "premature_menopause",
            "preeclampsia",
            "gestational_hypertension",
            "gestational_diabetes",
            "preterm_delivery",
            "small_for_gestational_age",
            "recurrent_pregnancy_loss",
            "pcos_or_irregular_menses",
            "early_menarche",
        )
    )


def _has_lpa_plus_reproductive_marker(patient):
    return bool(_has_elevated_lpa(patient) and _has_reproductive_marker(patient))


def _has_albuminuria(patient):
    uacr = getattr(patient, "uacr", None)
    return uacr is not None and uacr >= 30


def has_meaningful_cac_risk_signal(patient, result):
    apob = getattr(patient, "apob", None)
    ldl_c = getattr(patient, "ldl_c", None)
    triglycerides = getattr(patient, "triglycerides", None)
    non_hdl_c = getattr(patient, "non_hdl_c", None)
    hscrp = getattr(patient, "hscrp", None)
    a1c = getattr(patient, "a1c", None)
    bmi = getattr(patient, "bmi", None)
    ckm_stage = getattr(result, "ckm_stage", None)
    if isinstance(ckm_stage, dict):
        ckm_value = ckm_stage.get("stage")
    else:
        ckm_value = ckm_stage
    risk_category = _risk_value(getattr(result, "prevent_risk_category", None))
    return bool(
        (apob is not None and apob >= 100)
        or (ldl_c is not None and ldl_c >= 130)
        or (triglycerides is not None and triglycerides >= 175)
        or (non_hdl_c is not None and non_hdl_c >= 130)
        or getattr(patient, "premature_fhx_ascvd", False)
        or getattr(patient, "family_history_premature_ascvd", False)
        or (hscrp is not None and hscrp >= 2)
        or bool(getattr(patient, "prediabetes_context", False))
        or (a1c is not None and 5.7 <= a1c < 6.5)
        or (bmi is not None and bmi >= 30)
        or bool(getattr(patient, "osa", False))
        or bool(getattr(patient, "masld", False))
        or bool(getattr(patient, "smoker", False))
        or bool(getattr(patient, "smoking", False))
        or _has_diabetes(patient)
        or _has_ckd_stage_3_or_higher(patient, result)
        or _has_albuminuria(patient)
        or (ckm_value is not None and ckm_value >= 1)
        or bool(getattr(patient, "inflammatory_disease", False))
        or bool(getattr(patient, "rheumatoid_arthritis", False))
        or bool(getattr(patient, "sle", False))
        or bool(getattr(patient, "psoriasis", False))
        or bool(getattr(patient, "ibd", False))
        or risk_category in {
            RiskLevel.BORDERLINE.value,
            RiskLevel.INTERMEDIATE.value,
            RiskLevel.HIGH.value,
        }
    )


def _has_elevated_30y_trajectory(patient, result):
    age = getattr(patient, "age", None)
    prevent_30y = getattr(result, "prevent_30y_ascvd", None)
    return bool(age is not None and 30 <= age <= 59 and prevent_30y is not None and prevent_30y >= 10)


def _has_near_level3_lipid_trajectory(patient, result):
    age = getattr(patient, "age", None)
    prevent_10y = getattr(result, "prevent_10y_ascvd", None)
    prevent_30y = getattr(result, "prevent_30y_ascvd", None)
    ldl_c = getattr(patient, "ldl_c", None)
    apob = getattr(patient, "apob", None)
    return bool(
        age is not None
        and 30 <= age <= 59
        and prevent_10y is not None
        and prevent_10y < 3
        and prevent_30y is not None
        and 8 <= prevent_30y < 10
        and (ldl_c is None or ldl_c < 160)
        and (apob is None or apob < 120)
        and (
            (ldl_c is not None and 150 <= ldl_c < 160)
            or (apob is not None and 110 <= apob < 120)
        )
    )


def _has_treatment_relevant_lipid_trajectory(patient, result):
    age = getattr(patient, "age", None)
    prevent_30y = getattr(result, "prevent_30y_ascvd", None)
    ldl_c = getattr(patient, "ldl_c", None)
    apob = getattr(patient, "apob", None)
    return bool(
        age is not None
        and 30 <= age <= 59
        and (
            (prevent_30y is not None and prevent_30y >= 10)
            or (ldl_c is not None and 160 <= ldl_c < 190)
            or (apob is not None and apob >= 120)
        )
    )


def _cac_available_for_decision(patient, result):
    if getattr(patient, "cac", None) is not None:
        return False
    if getattr(patient, "clinical_ascvd", False):
        return False
    return True


def build_cac_age_gate_note(patient, result):
    if not _cac_available_for_decision(patient, result):
        return None
    if _below_cac_age_gate(patient) and _has_strong_enhancer(patient):
        return "CAC may clarify risk."
    return None


def build_cac_recommendation(patient, result):
    if not _cac_available_for_decision(patient, result):
        return None
    if _hidden_risk_cluster(patient, result) or has_occult_lipid_discussion_path(patient, result):
        return "CAC may clarify risk."
    if not meets_cac_age_gate(patient):
        return "CAC may clarify risk." if has_meaningful_cac_risk_signal(patient, result) else None

    if has_meaningful_cac_risk_signal(patient, result):
        return "CAC may clarify risk."

    risk_category = _risk_value(getattr(result, "prevent_risk_category", None))
    if risk_category == RiskLevel.INTERMEDIATE.value:
        return "CAC may clarify risk."

    if risk_category == RiskLevel.BORDERLINE.value and (
        _has_strong_enhancer(patient) or _has_albuminuria(patient)
    ):
        return "CAC may clarify risk."

    if risk_category == RiskLevel.LOW.value and (
        _has_lpa_plus_family_history(patient) or _has_lpa_plus_reproductive_marker(patient)
    ):
        return "CAC may clarify risk."

    if risk_category == RiskLevel.LOW.value and _has_treatment_relevant_lipid_trajectory(patient, result):
        apob = getattr(patient, "apob", None)
        if (
            apob is not None
            and apob >= 120
            and (
                bool(getattr(patient, "family_history_premature_ascvd", False))
                or bool(getattr(patient, "premature_fhx_ascvd", False))
            )
        ):
            return "CAC may clarify risk."
        return "CAC may clarify risk."

    if risk_category == RiskLevel.LOW.value and _has_elevated_30y_trajectory(patient, result):
        return "CAC may clarify risk."

    if risk_category == RiskLevel.LOW.value and _has_near_level3_lipid_trajectory(patient, result):
        return "CAC may clarify risk."

    if risk_category == RiskLevel.HIGH.value:
        return "CAC may clarify risk."

    return None
