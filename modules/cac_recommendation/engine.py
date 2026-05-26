from core.enums import RiskLevel


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
    sex = _sex_key(patient)
    if sex == "male":
        return age >= 40
    if sex == "female":
        return age >= 45
    return False


def _below_cac_age_gate(patient):
    age = getattr(patient, "age", None)
    if age is None:
        return False
    sex = _sex_key(patient)
    if sex == "male":
        return age < 40
    if sex == "female":
        return age < 45
    return False


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
    ldl_c = getattr(patient, "ldl_c", None)
    if ldl_c is not None and ldl_c >= 190:
        return False
    age = getattr(patient, "age", None)
    if age is not None and age > 40 and _has_diabetes(patient):
        return False
    if _has_ckd_stage_3_or_higher(patient, result):
        return False
    return True


def build_cac_age_gate_note(patient, result):
    if not _cac_available_for_decision(patient, result):
        return None
    if _below_cac_age_gate(patient) and _has_strong_enhancer(patient):
        return "CAC not routinely recommended at this age; consider only if results would change management."
    return None


def build_cac_recommendation(patient, result):
    if not _cac_available_for_decision(patient, result):
        return None
    if not meets_cac_age_gate(patient):
        return None

    risk_category = _risk_value(getattr(result, "prevent_risk_category", None))
    if risk_category == RiskLevel.INTERMEDIATE.value:
        return "CAC scoring may help refine preventive risk classification."

    if risk_category == RiskLevel.BORDERLINE.value and (
        _has_strong_enhancer(patient) or _has_albuminuria(patient)
    ):
        return "CAC scoring may help refine preventive risk classification."

    if risk_category == RiskLevel.LOW.value and (
        _has_lpa_plus_family_history(patient) or _has_lpa_plus_reproductive_marker(patient)
    ):
        return "CAC reasonable for risk clarification if treatment decision remains uncertain."

    if risk_category == RiskLevel.LOW.value and _has_treatment_relevant_lipid_trajectory(patient, result):
        return "CAC may clarify plaque burden if treatment intensity remains uncertain."

    if risk_category == RiskLevel.LOW.value and _has_elevated_30y_trajectory(patient, result):
        return "CAC reasonable for risk clarification if treatment decision remains uncertain."

    if risk_category == RiskLevel.LOW.value and _has_near_level3_lipid_trajectory(patient, result):
        return "CAC reasonable if treatment decision remains uncertain."

    if risk_category == RiskLevel.HIGH.value:
        return (
            "CAC scoring may help clarify plaque burden but should not delay treatment of high estimated risk."
        )

    return None
