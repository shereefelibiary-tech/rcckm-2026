from modules.cac_recommendation.engine import build_cac_recommendation
from modules.clarification.engine import (
    should_recommend_apob,
    should_recommend_lpa,
)
from modules.prevent.lipid_bands import (
    PREVENT_ASCVD_EARLY_DISCUSSION_THRESHOLD,
    PREVENT_ASCVD_HIGH_THRESHOLD,
    PREVENT_ASCVD_INTERMEDIATE_THRESHOLD,
    PREVENT_ASCVD_STATIN_DISCUSSION_THRESHOLD,
    lipid_recommendation_from_prevent_band,
)
from modules.risk_enhancers.reproductive import has_reproductive_risk_markers
from modules.risk_enhancers.breast_arterial_calcification import (
    BAC_CAC_CLARIFICATION_TEXT,
    has_breast_arterial_calcification,
)
from modules.targets.engine import LDL_TARGET_VERY_HIGH_RISK_ASCVD


def _has_diabetes(patient):
    a1c = getattr(patient, "a1c", None)
    return bool(getattr(patient, "diabetes", False)) or (
        a1c is not None and a1c >= 6.5
    )


def _risk_value(risk_level):
    return getattr(risk_level, "value", risk_level)


def _is_smoking(patient):
    return bool(getattr(patient, "smoker", False)) or bool(
        getattr(patient, "smoking", False)
    )


def _has_ckd_or_albuminuria(patient, result):
    egfr_stage = getattr(result, "egfr_stage", None)
    albuminuria_stage = getattr(result, "albuminuria_stage", None)
    egfr = getattr(patient, "egfr", None)
    uacr = getattr(patient, "uacr", None)

    return (
        egfr_stage in {"G3a", "G3b", "G4", "G5"}
        or albuminuria_stage in {"A2", "A3"}
        or (egfr is not None and egfr < 60)
        or (uacr is not None and uacr >= 30)
    )


def _has_albuminuria(patient, result=None):
    albuminuria_stage = getattr(result, "albuminuria_stage", None) if result is not None else None
    uacr = getattr(patient, "uacr", None)
    return bool(albuminuria_stage in {"A2", "A3"} or (uacr is not None and uacr >= 30))


def _has_ckd_context(patient, result):
    egfr_stage = getattr(result, "egfr_stage", None)
    egfr = getattr(patient, "egfr", None)
    return (
        bool(getattr(patient, "ckd", False))
        or egfr_stage in {"G3a", "G3b", "G4", "G5"}
        or (egfr is not None and egfr < 60)
    )


def _has_obesity(patient):
    bmi = getattr(patient, "bmi", None)
    return bmi is not None and bmi >= 30


def _has_elevated_tg(patient):
    triglycerides = getattr(patient, "triglycerides", None)
    return triglycerides is not None and triglycerides >= 150


def _age_40_to_75(patient):
    try:
        age = float(getattr(patient, "age", None))
    except (TypeError, ValueError):
        return False
    return 40 <= age <= 75


def _has_hiv_pathway(patient):
    return (
        bool(getattr(patient, "hiv", False))
        and bool(getattr(patient, "stable_art", False))
        and _age_40_to_75(patient)
    )


def _tg_value(patient):
    try:
        value = getattr(patient, "triglycerides", None)
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _very_severe_tg(patient):
    triglycerides = _tg_value(patient)
    return triglycerides is not None and triglycerides >= 1000


def _severe_tg(patient):
    triglycerides = _tg_value(patient)
    return triglycerides is not None and triglycerides >= 500


def _atherogenic_metric_available(patient):
    return getattr(patient, "non_hdl_c", None) is not None or getattr(patient, "apob", None) is not None


def _cac_value(patient):
    try:
        value = getattr(patient, "cac", None)
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _first_target(result):
    targets = getattr(result, "targets", None) or []
    return targets[0] if targets else None


def _above_lipid_target(patient, result):
    target = _first_target(result)
    if not target:
        return False
    ldl_target = getattr(target, "ldl_c_target", None)
    non_hdl_target = getattr(target, "non_hdl_c_target", None)
    apob_target = getattr(target, "apob_target", None)
    return bool(
        (
            ldl_target is not None
            and getattr(patient, "ldl_c", None) is not None
            and patient.ldl_c >= ldl_target
        )
        or (
            non_hdl_target is not None
            and getattr(patient, "non_hdl_c", None) is not None
            and patient.non_hdl_c >= non_hdl_target
        )
        or (
            apob_target is not None
            and getattr(patient, "apob", None) is not None
            and patient.apob >= apob_target
        )
    )


def _has_statin_intolerance(patient):
    if bool(getattr(patient, "statin_intolerance", False)):
        return True
    medication_text = " ".join(
        str(value or "")
        for value in [
            getattr(patient, "medications_raw", None),
            getattr(patient, "clinical_ascvd_context", None),
        ]
    ).lower()
    return "statin intoler" in medication_text or "could not tolerate" in medication_text


def _has_metabolic_risk(patient):
    return (
        _has_diabetes(patient)
        or _has_obesity(patient)
        or _has_elevated_tg(patient)
        or bool(getattr(patient, "hypertension", False))
        or _bp_above_target(patient)
    )


def _has_premature_family_history(patient):
    return bool(getattr(patient, "premature_fhx_ascvd", False)) or bool(
        getattr(patient, "family_history_premature_ascvd", False)
    )


def _has_rheumatoid_arthritis(patient):
    return bool(getattr(patient, "rheumatoid_arthritis", False))


def _ra_low_short_term_context(patient, result):
    if not (_has_rheumatoid_arthritis(patient) and _has_premature_family_history(patient)):
        return False
    risk_10y = _prevent_10y_ascvd_value(result)
    prevent_30y = getattr(result, "prevent_30y_ascvd", None)
    try:
        prevent_30y = float(prevent_30y) if prevent_30y is not None else None
    except (TypeError, ValueError):
        prevent_30y = None
    ldl_c = getattr(patient, "ldl_c", None)
    apob = getattr(patient, "apob", None)
    return bool(
        risk_10y is not None
        and risk_10y < PREVENT_ASCVD_EARLY_DISCUSSION_THRESHOLD
        and (prevent_30y is None or prevent_30y < 15)
        and (ldl_c is None or ldl_c < 160)
        and (apob is None or apob < 120)
        and not _has_diabetes(patient)
        and not _has_ckd_or_albuminuria(patient, result)
        and _cac_value(patient) is None
    )


def _has_elevated_lpa(patient):
    value = getattr(patient, "lp_a_value", None)
    unit = getattr(patient, "lp_a_unit", None)
    return (
        unit == "nmol/L"
        and value is not None
        and value >= 125
    ) or (
        unit == "mg/dL"
        and value is not None
        and value >= 50
    )


def _low_with_lpa_reproductive_context(patient, result):
    return bool(
        result is not None
        and _prevent_low(result)
        and _has_elevated_lpa(patient)
        and has_reproductive_risk_markers(patient)
    )


def _has_actionable_biologic_risk(patient):
    ldl_c = getattr(patient, "ldl_c", None)
    apob = getattr(patient, "apob", None)
    hscrp = getattr(patient, "hscrp", None)
    return (
        (apob is not None and apob >= 100)
        or (apob is None and ldl_c is not None and ldl_c >= 130)
        or _has_elevated_lpa(patient)
        or _has_diabetes(patient)
        or _is_smoking(patient)
        or bool(getattr(patient, "inflammatory_disease", False))
        or (hscrp is not None and hscrp >= 2 and _has_metabolic_risk(patient))
    )


def _prevent_borderline_or_intermediate(result):
    return _risk_value(getattr(result, "prevent_risk_category", None)) in {
        "BORDERLINE",
        "INTERMEDIATE",
    }


def _prevent_borderline(result):
    return _risk_value(getattr(result, "prevent_risk_category", None)) == "BORDERLINE"


def _prevent_intermediate(result):
    return _risk_value(getattr(result, "prevent_risk_category", None)) == "INTERMEDIATE"


def _prevent_low(result):
    return _risk_value(getattr(result, "prevent_risk_category", None)) == "LOW"


def _prevent_elevated(result):
    risk_category = _risk_value(getattr(result, "prevent_risk_category", None))
    prevent_value = getattr(result, "prevent_10y_ascvd", None)
    return risk_category in {"BORDERLINE", "INTERMEDIATE", "HIGH"} or (
        prevent_value is not None and prevent_value >= 3
    )


def _prevent_high(result):
    return _risk_value(getattr(result, "prevent_risk_category", None)) == "HIGH" or (
        getattr(result, "prevent_10y_ascvd", None) is not None
        and result.prevent_10y_ascvd >= PREVENT_ASCVD_HIGH_THRESHOLD
    )


def _prevent_10y_ascvd_value(result):
    value = getattr(result, "prevent_10y_ascvd", None)
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _prevent_ascvd_5_to_7_5(result):
    risk = _prevent_10y_ascvd_value(result)
    return risk is not None and PREVENT_ASCVD_STATIN_DISCUSSION_THRESHOLD <= risk < PREVENT_ASCVD_INTERMEDIATE_THRESHOLD


def _prevent_ascvd_7_5_to_20(result):
    risk = _prevent_10y_ascvd_value(result)
    return risk is not None and PREVENT_ASCVD_INTERMEDIATE_THRESHOLD <= risk < PREVENT_ASCVD_HIGH_THRESHOLD


def _prevent_ascvd_20_or_higher(result):
    risk = _prevent_10y_ascvd_value(result)
    return risk is not None and risk >= PREVENT_ASCVD_HIGH_THRESHOLD


def _prevent_ascvd_3_to_5(result):
    risk = _prevent_10y_ascvd_value(result)
    return risk is not None and PREVENT_ASCVD_EARLY_DISCUSSION_THRESHOLD <= risk < PREVENT_ASCVD_STATIN_DISCUSSION_THRESHOLD


def _lipid_enhancer_context(patient, result=None):
    ldl_c = getattr(patient, "ldl_c", None)
    apob = getattr(patient, "apob", None)
    cac = _cac_value(patient)
    return {
        "ckd_albuminuria": _has_ckd_or_albuminuria(patient, result),
        "diabetes": _has_diabetes(patient),
        "metabolic": _has_metabolic_risk(patient),
        "premature_family_history": _has_premature_family_history(patient),
        "elevated_lpa": _has_elevated_lpa(patient),
        "hypertriglyceridemia": _has_elevated_tg(patient),
        "cac_plaque": cac is not None and cac > 0,
        "breast_arterial_calcification": has_breast_arterial_calcification(patient),
        "very_high_lipid_burden": (ldl_c is not None and ldl_c >= 160) or (apob is not None and apob >= 120),
        "ldl_apob_burden": (ldl_c is not None and ldl_c >= 130) or (apob is not None and apob >= 100),
        "inflammatory": bool(getattr(patient, "inflammatory_disease", False)),
    }


def _prevent_lipid_recommendation(patient, result):
    return lipid_recommendation_from_prevent_band(
        patient,
        _prevent_10y_ascvd_value(result),
        getattr(result, "prevent_30y_ascvd", None),
        _lipid_enhancer_context(patient, result),
    )


def _low_short_term_elevated_cumulative_lipid_path(patient, result):
    if bool(getattr(patient, "clinical_ascvd", False)):
        return False
    age = getattr(patient, "age", None)
    prevent_10y = getattr(result, "prevent_10y_ascvd", None)
    prevent_30y = getattr(result, "prevent_30y_ascvd", None)
    ldl_c = getattr(patient, "ldl_c", None)
    if age is None or prevent_10y is None:
        return False
    apob = getattr(patient, "apob", None)
    has_major_lipid_burden = bool(
        (ldl_c is not None and 160 <= ldl_c <= 189)
        or (apob is not None and apob >= 120)
    )
    return bool(30 <= age <= 59 and prevent_10y < 3 and has_major_lipid_burden)


def _near_level3_lipid_trajectory(patient, result):
    if result is None or bool(getattr(patient, "clinical_ascvd", False)):
        return False
    if getattr(patient, "cac", None) is not None:
        return False
    age = getattr(patient, "age", None)
    prevent_10y = getattr(result, "prevent_10y_ascvd", None)
    prevent_30y = getattr(result, "prevent_30y_ascvd", None)
    ldl_c = getattr(patient, "ldl_c", None)
    apob = getattr(patient, "apob", None)
    if age is None or prevent_10y is None or prevent_30y is None:
        return False
    return bool(
        30 <= age <= 59
        and prevent_10y < 3
        and 8 <= prevent_30y < 10
        and (ldl_c is None or ldl_c < 160)
        and (apob is None or apob < 120)
        and (
            (ldl_c is not None and 150 <= ldl_c < 160)
            or (apob is not None and 110 <= apob < 120)
        )
    )


def _borderline_albuminuria_or_trajectory_path(patient, result):
    if result is None or bool(getattr(patient, "clinical_ascvd", False)):
        return False
    prevent_30y = getattr(result, "prevent_30y_ascvd", None)
    return bool(
        _prevent_ascvd_3_to_5(result)
        and (
            _has_albuminuria(patient, result)
            or (
                prevent_30y is not None
                and prevent_30y >= 10
                and _has_major_lipid_risk_enhancer(patient, result)
            )
        )
    )


def _low_10yr_elevated_30yr_prevent_path(patient, result):
    if result is None or bool(getattr(patient, "clinical_ascvd", False)):
        return False
    age = getattr(patient, "age", None)
    prevent_10y = _prevent_10y_ascvd_value(result)
    prevent_30y = getattr(result, "prevent_30y_ascvd", None)
    try:
        prevent_30y = float(prevent_30y) if prevent_30y is not None else None
    except (TypeError, ValueError):
        prevent_30y = None
    return bool(
        age is not None
        and 30 <= age <= 59
        and prevent_10y is not None
        and prevent_10y < PREVENT_ASCVD_EARLY_DISCUSSION_THRESHOLD
        and prevent_30y is not None
        and prevent_30y >= 15
    )


def _albuminuria_lipid_prevention_path(patient, result):
    if result is None or bool(getattr(patient, "clinical_ascvd", False)):
        return False
    prevent_30y = getattr(result, "prevent_30y_ascvd", None)
    return bool(
        _has_albuminuria(patient, result)
        and (
            _prevent_ascvd_5_to_7_5(result)
            or _prevent_ascvd_7_5_to_20(result)
            or _prevent_borderline_or_intermediate(result)
            or (prevent_30y is not None and prevent_30y >= 10)
        )
    )


def _level_3b_intermediate_prevent_path(result):
    classification = getattr(result, "level_classification", None) or {}
    return bool(
        _prevent_intermediate(result)
        and str(classification.get("level") or "") == "3B"
    )


def _hidden_high_risk_enhancer_cluster_path(result):
    classification = getattr(result, "level_classification", None) or {}
    return str(classification.get("label") or "").lower() == (
        "level 3b - hidden atherogenic risk burden"
    )


def _bp_above_target(patient):
    sbp = getattr(patient, "sbp", None)
    dbp = getattr(patient, "dbp", None)

    return (
        (sbp is not None and sbp > 130)
        or (dbp is not None and dbp > 80)
        or bool(getattr(patient, "elevated_bp", False))
    )


def _bp_treated_or_hypertension(patient):
    return bool(getattr(patient, "bp_treated", False)) or bool(
        getattr(patient, "hypertension", False)
    )


def _level_3b_intermediate_uacr_missing_path(patient, result):
    return bool(
        _level_3b_intermediate_prevent_path(result)
        and getattr(patient, "uacr", None) is None
    )


def _on_statin_therapy(patient):
    if bool(getattr(patient, "lipid_lowering", False)) and str(
        getattr(patient, "statin_intensity", "") or ""
    ).strip():
        return True
    medication_text = str(getattr(patient, "medications_raw", "") or "").lower()
    statin_names = (
        "atorvastatin",
        "rosuvastatin",
        "pravastatin",
        "simvastatin",
        "lovastatin",
        "fluvastatin",
        "pitavastatin",
    )
    return any(name in medication_text for name in statin_names)


def _on_lipid_lowering_therapy(patient):
    if bool(getattr(patient, "lipid_lowering", False)):
        return True
    medication_text = str(getattr(patient, "medications_raw", "") or "").lower()
    lipid_med_names = (
        "atorvastatin",
        "rosuvastatin",
        "pravastatin",
        "simvastatin",
        "lovastatin",
        "fluvastatin",
        "pitavastatin",
        "ezetimibe",
        "evolocumab",
        "alirocumab",
        "bempedoic",
        "inclisiran",
    )
    return any(name in medication_text for name in lipid_med_names)


def _level3b_atherogenic_discussion_path(result):
    classification = getattr(result, "level_classification", None) or {}
    if str(classification.get("level") or "") != "3B":
        return False
    text = " ".join(
        str(classification.get(key) or "")
        for key in ("label", "short_reason", "treatment_posture")
    ).lower()
    return any(
        phrase in text
        for phrase in (
            "hidden",
            "occult",
            "clustered",
            "actionable early ckm / atherogenic risk",
            "atherogenic risk",
            "risk-enhancer",
            "risk enhancer",
            "biologic burden",
        )
    )


def _off_treatment_level3b_lipid_discussion(patient, result):
    if result is None or _on_lipid_lowering_therapy(patient):
        return False
    prevent_10y = _prevent_10y_ascvd_value(result)
    prevent_30y = getattr(result, "prevent_30y_ascvd", None)
    try:
        prevent_30y = float(prevent_30y) if prevent_30y is not None else None
    except (TypeError, ValueError):
        prevent_30y = None
    ldl_c = getattr(patient, "ldl_c", None)
    apob = getattr(patient, "apob", None)
    return bool(
        _level3b_atherogenic_discussion_path(result)
        and (
            _prevent_low(result)
            or (prevent_10y is not None and prevent_10y < PREVENT_ASCVD_EARLY_DISCUSSION_THRESHOLD)
        )
        and (prevent_30y is None or prevent_30y < 10)
        and (
            (ldl_c is not None and ldl_c >= 130)
            or (apob is not None and apob >= 100)
            or _has_elevated_lpa(patient)
        )
    )


def _has_heart_failure(patient):
    return bool(getattr(patient, "heart_failure", False)) or bool(
        getattr(patient, "hf", False)
    )


def _sglt2_action_text(patient, result=None):
    egfr = getattr(patient, "egfr", None)
    uacr = getattr(patient, "uacr", None)
    try:
        egfr_value = float(egfr) if egfr is not None else None
    except (TypeError, ValueError):
        egfr_value = None
    try:
        uacr_value = float(uacr) if uacr is not None else None
    except (TypeError, ValueError):
        uacr_value = None

    if egfr_value is None or uacr_value is None:
        return None
    if uacr_value < 30 and not _has_heart_failure(patient):
        return None
    if bool(getattr(patient, "sglt2", False)):
        return "Continue SGLT2 inhibitor therapy if tolerated and clinically appropriate."
    if egfr_value < 20:
        return "SGLT2 inhibitor initiation is not routinely recommended at this eGFR; individualize based on nephrology guidance and existing therapy."
    if _has_heart_failure(patient) or uacr_value >= 200:
        return "Add an SGLT2 inhibitor for kidney and cardiovascular protection if no contraindication, despite ACEi/ARB therapy."
    if _has_diabetes(patient) and uacr_value >= 30:
        return "Consider an SGLT2 inhibitor for kidney and cardiovascular protection given diabetes with albuminuric CKD."
    return None


def _has_major_lipid_risk_enhancer(patient, result=None):
    ldl_c = getattr(patient, "ldl_c", None)
    apob = getattr(patient, "apob", None)
    return bool(
        _has_ckd_or_albuminuria(patient, result)
        or _has_diabetes(patient)
        or _has_metabolic_risk(patient)
        or _has_premature_family_history(patient)
        or _has_elevated_lpa(patient)
        or _has_elevated_tg(patient)
        or (ldl_c is not None and ldl_c >= 130)
        or (apob is not None and apob >= 100)
        or bool(getattr(patient, "inflammatory_disease", False))
        or (_cac_value(patient) is not None and _cac_value(patient) > 0)
    )


def _needs_lipid_action(patient, result=None):
    cac = getattr(patient, "cac", None)
    apob = getattr(patient, "apob", None)
    ldl_c = getattr(patient, "ldl_c", None)
    return (
        bool(getattr(patient, "clinical_ascvd", False))
        or (cac is not None and cac > 0)
        or (apob is not None and apob >= 100)
        or (ldl_c is not None and ldl_c >= 190)
        or bool(getattr(patient, "suspected_fh_hefh", False))
        or (_severe_tg(patient) and _atherogenic_metric_available(patient))
        or _has_hiv_pathway(patient)
        or (result is not None and _low_short_term_elevated_cumulative_lipid_path(patient, result))
        or (result is not None and _hidden_high_risk_enhancer_cluster_path(result))
        or (result is not None and _low_10yr_elevated_30yr_prevent_path(patient, result))
        or (result is not None and _near_level3_lipid_trajectory(patient, result))
        or (result is not None and _low_with_lpa_reproductive_context(patient, result))
        or (result is not None and _albuminuria_lipid_prevention_path(patient, result))
        or (result is not None and _prevent_ascvd_7_5_to_20(result))
        or (result is not None and _prevent_ascvd_5_to_7_5(result))
        or (result is not None and _prevent_ascvd_3_to_5(result))
        or (
            result is not None
            and _prevent_ascvd_5_to_7_5(result)
            and _has_major_lipid_risk_enhancer(patient, result)
        )
        or (result is not None and _borderline_albuminuria_or_trajectory_path(patient, result))
        or (
            result is not None
            and _prevent_borderline(result)
            and has_reproductive_risk_markers(patient)
        )
        or (result is not None and _prevent_high(result))
    )


def _needs_indicated_lipid_action(patient, result=None):
    cac = getattr(patient, "cac", None)
    ldl_c = getattr(patient, "ldl_c", None)
    return bool(getattr(patient, "clinical_ascvd", False)) or (
        cac is not None and cac >= 300
    ) or (ldl_c is not None and ldl_c >= 190) or (
        result is not None and _prevent_ascvd_20_or_higher(result)
    )


def _treatment_should_not_wait(patient, result=None):
    return _needs_indicated_lipid_action(patient, result)


def _needs_clarification(result):
    clarification = getattr(result, "clarification", None)
    return bool(clarification and clarification.get("tier", 0) >= 2)


def _add_action(actions, domains, domain, recommendation):
    if recommendation in actions:
        return
    actions.append(recommendation)
    domains[domain] = recommendation


def _cac_testing_action_text(cac_recommendation, lipid_treatment_forward=False):
    if cac_recommendation == "CAC may clarify treatment.":
        return cac_recommendation
    if (
        cac_recommendation
        == "CAC may clarify plaque burden if the patient is hesitant or if treatment intensity remains uncertain."
    ):
        return cac_recommendation
    if lipid_treatment_forward:
        return "CAC may clarify plaque burden if treatment intensity remains uncertain."
    if cac_recommendation in {
        "CAC reasonable if treatment decision remains uncertain.",
        "CAC may clarify plaque burden if treatment intensity remains uncertain.",
        "CAC may clarify plaque burden if the patient is hesitant or if treatment intensity remains uncertain.",
    }:
        return cac_recommendation
    return "CAC reasonable for risk clarification if treatment decision remains uncertain."


def _lipid_line_is_treatment_forward(lipid_line):
    text = str(lipid_line or "").strip().lower()
    if (
        text.startswith("no medication")
        or text.startswith("no escalation")
        or text.startswith("clinician-patient risk discussion")
        or text.startswith("risk discussion")
    ):
        return False
    return bool(
        text.startswith("moderate-intensity")
        or text.startswith("intensify")
        or text.startswith("high-intensity")
        or text.startswith("secondary-prevention")
        or "lipid-lowering therapy recommended" in text
        or "lipid-lowering therapy is indicated" in text
        or "lipid-lowering therapy is favored" in text
        or "statin therapy is reasonable" in text
        or "statin therapy reasonable" in text
        or "statin therapy recommended" in text
    )


def _lipid_action_text(patient, result):
    if bool(getattr(patient, "clinical_ascvd", False)):
        target = (getattr(result, "targets", None) or [None])[0]
        ldl_target = getattr(target, "ldl_c_target", None) if target else None
        non_hdl_target = getattr(target, "non_hdl_c_target", None) if target else None
        apob_target = getattr(target, "apob_target", None) if target else None
        above_target = (
            (ldl_target is not None and getattr(patient, "ldl_c", None) is not None and patient.ldl_c >= ldl_target)
            or (non_hdl_target is not None and getattr(patient, "non_hdl_c", None) is not None and patient.non_hdl_c >= non_hdl_target)
            or (apob_target is not None and getattr(patient, "apob", None) is not None and patient.apob >= apob_target)
        )
        very_high_risk_target = ldl_target == LDL_TARGET_VERY_HIGH_RISK_ASCVD
        if above_target:
            if very_high_risk_target:
                return "Intensify secondary-prevention lipid-lowering therapy; treat toward very-high-risk ASCVD targets."
            return "Intensify secondary-prevention lipid-lowering therapy; treat toward ASCVD targets."
        if very_high_risk_target:
            return "Secondary-prevention lipid-lowering therapy indicated; treat toward very-high-risk ASCVD targets."
        return "Secondary-prevention lipid-lowering therapy indicated; treat toward ASCVD targets."
    ldl_c = getattr(patient, "ldl_c", None)
    if (ldl_c is not None and ldl_c >= 190) or bool(getattr(patient, "suspected_fh_hefh", False)):
        return "High-intensity or maximally tolerated statin therapy indicated."
    if _severe_tg(patient) and _atherogenic_metric_available(patient):
        return "Address ASCVD risk with lipid-lowering therapy guided by non-HDL-C/ApoB."
    cac = _cac_value(patient)
    if cac is not None and cac >= 300:
        return "Lipid-lowering therapy is indicated; treat toward high-risk targets."
    if cac is not None and 100 <= cac <= 299:
        if bool(getattr(patient, "lipid_lowering", False)) and _above_lipid_target(patient, result):
            return "Intensify lipid-lowering therapy; treat toward LDL-C <70 and non-HDL-C <100."
        return "Lipid-lowering therapy recommended; treat toward LDL-C <70 and non-HDL-C <100."
    if cac is not None and cac > 0:
        return "Lipid-lowering therapy is favored because coronary plaque is already present despite low short-term ASCVD risk."
    if _prevent_ascvd_20_or_higher(result):
        return _prevent_lipid_recommendation(patient, result).emr_summary
    if _needs_indicated_lipid_action(patient, result):
        return "Lipid-lowering therapy is indicated; treat toward high-risk targets."
    if _has_hiv_pathway(patient):
        return "Statin therapy recommended/reasonable in HIV; review ART-statin interactions."
    if _off_treatment_level3b_lipid_discussion(patient, result):
        return "Discuss lipid-lowering therapy."
    if _hidden_high_risk_enhancer_cluster_path(result):
        if _on_statin_therapy(patient):
            return "Review intensity; atherogenic burden remains elevated."
        return "Discuss moderate-intensity statin therapy for hidden atherogenic risk."
    if _low_with_lpa_reproductive_context(patient, result):
        return "Lipid lowering: no escalation today; document elevated Lp(a) and reproductive risk markers as risk enhancers."
    if _near_level3_lipid_trajectory(patient, result):
        return "Clinician-patient risk discussion reasonable given near-threshold LDL/ApoB burden and 30-year trajectory."
    if _albuminuria_lipid_prevention_path(patient, result):
        if _on_statin_therapy(patient):
            return "Continue statin therapy; consider intensification if LDL-C/ApoB remain above target."
        if _prevent_10y_ascvd_value(result) is not None and _prevent_10y_ascvd_value(result) < PREVENT_ASCVD_STATIN_DISCUSSION_THRESHOLD:
            return _prevent_lipid_recommendation(patient, result).emr_summary
        return "Moderate-intensity statin therapy is reasonable given borderline/intermediate ASCVD risk with albuminuria and metabolic risk-enhancing factors."
    if _prevent_ascvd_7_5_to_20(result):
        return _prevent_lipid_recommendation(patient, result).emr_summary
    if _prevent_ascvd_5_to_7_5(result) and _has_major_lipid_risk_enhancer(patient, result):
        return _prevent_lipid_recommendation(patient, result).emr_summary
    if _prevent_ascvd_5_to_7_5(result):
        return _prevent_lipid_recommendation(patient, result).emr_summary
    if _prevent_ascvd_3_to_5(result):
        if bool(getattr(patient, "south_asian_ancestry", False)):
            return (
                "Discuss moderate-intensity statin therapy given South Asian ancestry, elevated ApoB/triglyceride "
                "burden, and elevated 30-year ASCVD risk despite low 10-year ASCVD risk."
            )
        return _prevent_lipid_recommendation(patient, result).emr_summary
    if _low_10yr_elevated_30yr_prevent_path(patient, result):
        return _prevent_lipid_recommendation(patient, result).emr_summary
    if _level_3b_intermediate_prevent_path(result):
        return "Moderate-intensity lipid-lowering therapy is reasonable to reduce cumulative atherogenic exposure."
    return (
        "Lipid-lowering therapy is indicated; treat toward high-risk targets."
        if _needs_indicated_lipid_action(patient, result)
        else (
            "Moderate-intensity statin therapy is reasonable to reduce cumulative atherogenic exposure."
            if _low_short_term_elevated_cumulative_lipid_path(patient, result)
            else (
                "Moderate-intensity lipid-lowering therapy is reasonable to reduce cumulative atherogenic exposure."
                if _borderline_albuminuria_or_trajectory_path(patient, result)
                else (
                "Discuss moderate-intensity statin therapy given reproductive risk markers and borderline ASCVD risk."
                    if (_prevent_ascvd_3_to_5(result) or _prevent_borderline(result))
                    and has_reproductive_risk_markers(patient)
                    else "Discuss moderate-intensity statin therapy."
                )
            )
        )
    )


def _build_treatment_actions(patient, result):
    recommendations = []
    domains = {}
    triglycerides = _tg_value(patient)

    if triglycerides is not None and triglycerides >= 1000:
        _add_action(
            recommendations,
            domains,
            "triglycerides",
            "Very severe hypertriglyceridemia: lower TG to reduce pancreatitis risk.",
        )
        _add_action(
            recommendations,
            domains,
            "tg_diet",
            "Very-low-fat diet; eliminate alcohol and added sugars/refined carbohydrates.",
        )
        _add_action(
            recommendations,
            domains,
            "rdn_referral",
            "Refer to registered dietitian nutritionist.",
        )
        _add_action(
            recommendations,
            domains,
            "tg_pharmacotherapy",
            "Consider fibrate or prescription omega-3 therapy to lower TG.",
        )
        _add_action(
            recommendations,
            domains,
            "fasting_lipids",
            "Recheck fasting lipid profile after treatment changes.",
        )

    if _ra_low_short_term_context(patient, result):
        _add_action(
            recommendations,
            domains,
            "lipids",
            "Continue lifestyle-focused prevention; no lipid escalation today based on current LDL-C/ApoB and ASCVD risk profile.",
        )
        _add_action(
            recommendations,
            domains,
            "inflammation",
            "RA is a risk enhancer; ensure inflammation is clinically controlled and avoid undertreating traditional risk factors.",
        )

    if _needs_lipid_action(patient, result):
        lipid_recommendation = _lipid_action_text(patient, result)
        _add_action(
            recommendations,
            domains,
            "lipids",
            lipid_recommendation,
        )
        if _has_statin_intolerance(patient):
            _add_action(
                recommendations,
                domains,
                "statin_intolerance",
                "Given prior high-intensity statin intolerance, consider maximally tolerated statin strategy and nonstatin intensification.",
            )

    ldl_c = getattr(patient, "ldl_c", None)
    if (ldl_c is not None and ldl_c >= 190) or bool(getattr(patient, "suspected_fh_hefh", False)):
        _add_action(
            recommendations,
            domains,
            "secondary_causes",
            "Evaluate secondary causes and consider FH/cascade screening when appropriate.",
        )

    if _has_ckd_or_albuminuria(patient, result):
        egfr = getattr(patient, "egfr", None)
        kidney_recommendation = "Optimize kidney-protective therapy."
        if _has_albuminuria(patient, result):
            if bool(getattr(patient, "ace_arb", False)) and not _bp_above_target(patient):
                kidney_recommendation = "Continue kidney-protective therapy and monitor UACR/eGFR."
            else:
                kidney_recommendation = "Confirm persistent albuminuria with repeat UACR if not already confirmed; optimize kidney-protective therapy."
        elif not (_has_diabetes(patient) or (egfr is not None and egfr < 60)):
            kidney_recommendation = "Optimize kidney-protective therapy and confirm albuminuria persistence."
        _add_action(
            recommendations,
            domains,
            "kidney",
            kidney_recommendation,
        )

        if (
            _has_albuminuria(patient, result)
            and _bp_treated_or_hypertension(patient)
            and not (bool(getattr(patient, "ace_arb", False)) and not _bp_above_target(patient))
        ):
            _add_action(
                recommendations,
                domains,
                "ace_arb",
                "Continue or optimize ACEi/ARB therapy if hypertension and persistent albuminuria are present.",
            )

    a1c = getattr(patient, "a1c", None)
    if a1c is not None and a1c >= 7.0:
        _add_action(
            recommendations,
            domains,
            "glycemia",
            "Optimize diabetes care.",
        )

    if _treatment_should_not_wait(patient, result):
        _add_action(
            recommendations,
            domains,
            "treatment_timing",
            "Clarification testing should not delay treatment.",
        )

    if _bp_above_target(patient) or (
        bool(getattr(patient, "bp_treated", False))
        and _level_3b_intermediate_prevent_path(result)
    ):
        bp_recommendation = (
            "Treat BP toward goal <130/80."
            if _has_albuminuria(patient, result)
            else "Optimize BP to <130/80."
        )
        _add_action(
            recommendations,
            domains,
            "blood_pressure",
            bp_recommendation,
        )

    sglt2_recommendation = _sglt2_action_text(patient, result)
    if sglt2_recommendation:
        _add_action(
            recommendations,
            domains,
            "sglt2",
            sglt2_recommendation,
        )

    if _is_smoking(patient):
        _add_action(
            recommendations,
            domains,
            "smoking",
            "Address smoking cessation as a primary prevention priority.",
        )

    if triglycerides is not None and 500 <= triglycerides < 1000:
        recommendation = (
            "Severe hypertriglyceridemia: lower TG to reduce pancreatitis risk; evaluate secondary causes and consider fibrate or prescription omega-3 therapy."
        )
        _add_action(
            recommendations,
            domains,
            "triglycerides",
            recommendation,
        )
        _add_action(
            recommendations,
            domains,
            "fasting_lipids",
            "Repeat fasting lipid panel to confirm severe hypertriglyceridemia.",
        )

    return recommendations, domains


def _build_testing_actions(patient, result):
    recommendations = []
    domains = {}
    ldl_c = getattr(patient, "ldl_c", None)
    triglycerides = getattr(patient, "triglycerides", None)
    cac = getattr(patient, "cac", None)
    severe_ldl = ldl_c is not None and ldl_c >= 190

    if should_recommend_apob(patient, result):
        _add_action(
            recommendations,
            domains,
            "apob_testing",
            "Obtain ApoB to define atherogenic particle burden.",
        )

    prioritize_uacr = _level_3b_intermediate_uacr_missing_path(patient, result)

    if prioritize_uacr and (
        _has_diabetes(patient)
        or _has_ckd_context(patient, result)
        or bool(getattr(patient, "hypertension", False))
        or _has_metabolic_risk(patient)
        or (_has_obesity(patient) and _has_elevated_tg(patient))
        or _prevent_elevated(result)
    ):
        _add_action(
            recommendations,
            domains,
            "uacr_testing",
            "Obtain UACR to complete kidney-risk assessment.",
        )

    if should_recommend_lpa(patient, result):
        _add_action(
            recommendations,
            domains,
            "lpa_testing",
            "Check Lp(a) once.",
        )

    cac_recommendation = build_cac_recommendation(patient, result)
    if cac_recommendation:
        lipid_line = _lipid_action_text(patient, result)
        lipid_treatment_forward = _lipid_line_is_treatment_forward(lipid_line)
        cac_text = (
            BAC_CAC_CLARIFICATION_TEXT
            if has_breast_arterial_calcification(patient)
            and getattr(patient, "cac", None) is None
            else _cac_testing_action_text(cac_recommendation, lipid_treatment_forward)
        )
        _add_action(
            recommendations,
            domains,
            "cac_testing",
            cac_text,
        )

    if not prioritize_uacr and getattr(patient, "uacr", None) is None and (
        _has_diabetes(patient)
        or _has_ckd_context(patient, result)
        or bool(getattr(patient, "hypertension", False))
        or _has_metabolic_risk(patient)
        or (_has_obesity(patient) and _has_elevated_tg(patient))
        or _prevent_elevated(result)
    ):
        _add_action(
            recommendations,
            domains,
            "uacr_testing",
            "Obtain UACR to complete kidney-risk assessment.",
        )

    hscrp_relevant = any(
        bool(getattr(patient, field, False))
        for field in (
            "inflammatory_disease",
            "rheumatoid_arthritis",
            "sle",
            "psoriasis",
            "inflammatory_arthritis",
            "ibd",
        )
    )
    if getattr(patient, "hscrp", None) is None and hscrp_relevant:
        _add_action(
            recommendations,
            domains,
            "hscrp_testing",
            "Obtain hsCRP if inflammatory risk clarification would change management.",
        )

    if triglycerides is not None and 400 <= triglycerides < 500:
        _add_action(
            recommendations,
            domains,
            "fasting_lipids",
            "Repeat fasting lipid panel to confirm severe hypertriglyceridemia.",
        )

    if _needs_clarification(result):
        clarification = result.clarification
        if clarification.get("recommend_apob"):
            _add_action(
                recommendations,
                domains,
                "apob_testing",
                "Obtain ApoB to define atherogenic particle burden.",
            )
        if clarification.get("recommend_lpa"):
            _add_action(
                recommendations,
                domains,
                "lpa_testing",
                "Check Lp(a) once.",
            )
        cac_recommendation = build_cac_recommendation(patient, result)
        if clarification.get("recommend_cac") and cac_recommendation:
            lipid_line = _lipid_action_text(patient, result)
            lipid_treatment_forward = _lipid_line_is_treatment_forward(lipid_line)
            cac_text = (
                BAC_CAC_CLARIFICATION_TEXT
                if has_breast_arterial_calcification(patient)
                and getattr(patient, "cac", None) is None
                else _cac_testing_action_text(cac_recommendation, lipid_treatment_forward)
            )
            _add_action(
                recommendations,
                domains,
                "cac_testing",
                cac_text,
            )
        if clarification.get("recommend_uacr"):
            _add_action(
                recommendations,
                domains,
                "uacr_testing",
                "Obtain UACR to complete kidney-risk assessment.",
            )

    return recommendations, domains


def build_action_plan(patient, result):
    treatment_recommendations, treatment_domains = _build_treatment_actions(
        patient,
        result,
    )
    testing_recommendations, testing_domains = _build_testing_actions(patient, result)
    recommendations = treatment_recommendations + testing_recommendations
    domains = {**treatment_domains, **testing_domains}

    if not recommendations:
        _add_action(
            recommendations,
            domains,
            "none",
            "No active domain changes from current risk profile.",
        )

    if not _very_severe_tg(patient):
        limit = (
            8
            if (
                _level_3b_intermediate_uacr_missing_path(patient, result)
                or (
                    _has_albuminuria(patient, result)
                    and not _treatment_should_not_wait(patient, result)
                    and not _severe_tg(patient)
                )
            )
            else 4
        )
        recommendations = recommendations[:limit]
    active_domains = {
        domain: recommendation
        for domain, recommendation in domains.items()
        if recommendation in recommendations
    }

    return {
        "dominant_action": recommendations[0],
        "recommendations": recommendations,
        "domains": active_domains,
    }
