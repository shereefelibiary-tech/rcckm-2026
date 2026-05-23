from modules.cac_recommendation.engine import build_cac_recommendation


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


def _bp_above_target(patient):
    sbp = getattr(patient, "sbp", None)
    dbp = getattr(patient, "dbp", None)

    return (
        (sbp is not None and sbp >= 130)
        or (dbp is not None and dbp >= 80)
        or bool(getattr(patient, "elevated_bp", False))
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


def _build_treatment_actions(patient, result):
    recommendations = []
    domains = {}

    if _needs_lipid_action(patient, result):
        if bool(getattr(patient, "clinical_ascvd", False)):
            lipid_recommendation = (
                "Secondary-prevention lipid-lowering therapy indicated; treat toward ASCVD targets."
            )
        else:
            lipid_recommendation = (
                "Lipid-lowering therapy is indicated; treat toward high-risk targets."
                if _needs_indicated_lipid_action(patient, result)
                else "Lipid-lowering therapy is reasonable."
            )
        _add_action(
            recommendations,
            domains,
            "lipids",
            lipid_recommendation,
        )

    if _has_diabetes(patient) and _has_ckd_or_albuminuria(patient, result):
        _add_action(
            recommendations,
            domains,
            "kidney",
            "Optimize kidney-protective therapy.",
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

    if _bp_above_target(patient):
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

    triglycerides = getattr(patient, "triglycerides", None)
    if triglycerides is not None and triglycerides >= 1000:
        _add_action(
            recommendations,
            domains,
            "triglycerides",
            "Very severe hypertriglyceridemia; prioritize pancreatitis risk reduction and nutrition/lipid specialist pathway.",
        )
    elif triglycerides is not None and triglycerides >= 500:
        recommendation = (
            "Address pancreatitis-risk hypertriglyceridemia; repeat fasting lipids and evaluate secondary causes."
        )
        _add_action(
            recommendations,
            domains,
            "triglycerides",
            recommendation,
        )
        domains["fasting_lipids"] = recommendation

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

    if getattr(patient, "lp_a_value", None) is None:
        _add_action(
            recommendations,
            domains,
            "lpa_testing",
            "Check Lp(a) once.",
        )

    if build_cac_recommendation(patient, result):
        _add_action(
            recommendations,
            domains,
            "cac_testing",
            "Coronary calcium reasonable for plaque clarification.",
        )

    if getattr(patient, "uacr", None) is None and (
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
            "Obtain UACR to assess albuminuria/kidney risk.",
        )

    if getattr(patient, "hscrp", None) is None and (
        bool(getattr(patient, "inflammatory_disease", False))
        or _has_metabolic_risk(patient)
        or _has_premature_family_history(patient)
        or (
            getattr(patient, "apob", None) is not None
            and patient.apob >= 100
            and cac is None
        )
    ):
        _add_action(
            recommendations,
            domains,
            "hscrp_testing",
            "Consider hsCRP to clarify inflammatory residual risk.",
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
        if clarification.get("recommend_cac") and build_cac_recommendation(patient, result):
            _add_action(
                recommendations,
                domains,
                "cac_testing",
                "Coronary calcium reasonable for plaque clarification.",
            )
        if clarification.get("recommend_uacr"):
            _add_action(
                recommendations,
                domains,
                "uacr_testing",
                "Obtain UACR to assess albuminuria/kidney risk.",
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

    recommendations = recommendations[:4]
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
