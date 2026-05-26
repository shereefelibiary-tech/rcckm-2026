from modules.cac_recommendation.engine import build_cac_recommendation
from modules.risk_enhancers.reproductive import has_reproductive_risk_markers


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
        and result.prevent_10y_ascvd >= 10
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
    return bool(
        30 <= age <= 59
        and prevent_10y < 3
        and (
            (ldl_c is not None and 160 <= ldl_c <= 189)
            or (prevent_30y is not None and prevent_30y >= 10)
        )
    )


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
        _prevent_borderline(result)
        and (
            _has_albuminuria(patient, result)
            or (prevent_30y is not None and prevent_30y >= 10)
        )
    )


def _level_3b_intermediate_prevent_path(result):
    classification = getattr(result, "level_classification", None) or {}
    return bool(
        _prevent_intermediate(result)
        and str(classification.get("level") or "") == "3B"
    )


def _bp_above_target(patient):
    sbp = getattr(patient, "sbp", None)
    dbp = getattr(patient, "dbp", None)

    return (
        (sbp is not None and sbp > 130)
        or (dbp is not None and dbp > 80)
        or bool(getattr(patient, "elevated_bp", False))
    )


def _level_3b_intermediate_uacr_missing_path(patient, result):
    return bool(
        _level_3b_intermediate_prevent_path(result)
        and getattr(patient, "uacr", None) is None
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
        or (result is not None and _near_level3_lipid_trajectory(patient, result))
        or (result is not None and _low_with_lpa_reproductive_context(patient, result))
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
        result is not None and _prevent_high(result)
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
    if lipid_treatment_forward:
        return "CAC may clarify plaque burden if treatment intensity remains uncertain."
    if cac_recommendation in {
        "CAC reasonable if treatment decision remains uncertain.",
        "CAC may clarify plaque burden if treatment intensity remains uncertain.",
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
        if above_target:
            return "Intensify secondary-prevention lipid-lowering therapy; treat toward ASCVD targets."
        return "Secondary-prevention lipid-lowering therapy indicated; treat toward ASCVD targets."
    ldl_c = getattr(patient, "ldl_c", None)
    if (ldl_c is not None and ldl_c >= 190) or bool(getattr(patient, "suspected_fh_hefh", False)):
        return "High-intensity or maximally tolerated statin therapy indicated."
    if _severe_tg(patient) and _atherogenic_metric_available(patient):
        return "Address ASCVD risk with lipid-lowering therapy guided by non-HDL-C/ApoB."
    cac = _cac_value(patient)
    if cac is not None and 100 <= cac <= 299:
        if bool(getattr(patient, "lipid_lowering", False)) and _above_lipid_target(patient, result):
            return "Intensify lipid-lowering therapy; treat toward LDL-C <70 and non-HDL-C <100."
        return "Lipid-lowering therapy recommended; treat toward LDL-C <70 and non-HDL-C <100."
    if _has_hiv_pathway(patient):
        return "Statin therapy recommended/reasonable in HIV; review ART-statin interactions."
    if _low_with_lpa_reproductive_context(patient, result):
        return "No medication escalation required today; clinician-patient risk discussion recommended given high Lp(a) and reproductive risk markers."
    if _near_level3_lipid_trajectory(patient, result):
        return "Clinician-patient risk discussion reasonable given near-threshold LDL/ApoB burden and 30-year trajectory."
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
                    "Risk discussion reasonable; consider lipid-lowering therapy."
                    if _prevent_borderline(result) and has_reproductive_risk_markers(patient)
                    else "Lipid-lowering therapy is reasonable."
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
        kidney_recommendation = (
            "Optimize kidney-protective therapy."
            if _has_diabetes(patient) or (egfr is not None and egfr < 60)
            else "Optimize kidney-protective therapy and confirm albuminuria persistence."
        )
        _add_action(
            recommendations,
            domains,
            "kidney",
            kidney_recommendation,
        )

    a1c = getattr(patient, "a1c", None)
    if a1c is not None and a1c >= 7.0:
        _add_action(
            recommendations,
            domains,
            "glycemia",
            "Optimize glycemic therapy.",
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
        _add_action(
            recommendations,
            domains,
            "blood_pressure",
            "Optimize BP to <130/80.",
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

    if ldl_c is not None and getattr(patient, "apob", None) is None:
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

    if getattr(patient, "lp_a_value", None) is None:
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
        _add_action(
            recommendations,
            domains,
            "cac_testing",
            _cac_testing_action_text(cac_recommendation, lipid_treatment_forward),
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

    hscrp_relevant = (
        bool(getattr(patient, "inflammatory_disease", False))
        or _has_premature_family_history(patient)
        or (
            getattr(patient, "apob", None) is not None
            and patient.apob >= 100
            and cac is None
        )
        or (_has_metabolic_risk(patient) and not _prevent_low(result))
    )
    if getattr(patient, "hscrp", None) is None and hscrp_relevant:
        _add_action(
            recommendations,
            domains,
            "hscrp_testing",
            "Consider hsCRP to clarify inflammatory biomarker context.",
        )

    if triglycerides is not None and 400 <= triglycerides < 500:
        _add_action(
            recommendations,
            domains,
            "fasting_lipids",
            "Repeat fasting lipid panel to confirm severe hypertriglyceridemia.",
        )

    if getattr(patient, "lipid_supplements", False):
        _add_action(
            recommendations,
            domains,
            "supplements",
            "Dietary supplements are not recommended as a substitute for evidence-based lipid-lowering therapy.",
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
            _add_action(
                recommendations,
                domains,
                "cac_testing",
                _cac_testing_action_text(cac_recommendation, lipid_treatment_forward),
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
            "No escalation indicated.",
        )

    if not _very_severe_tg(patient):
        limit = 6 if _level_3b_intermediate_uacr_missing_path(patient, result) else 4
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
