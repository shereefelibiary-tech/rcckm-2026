from core.enums import RiskLevel
from modules.cac_recommendation.engine import build_cac_recommendation


def _num(value):
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _has_premature_family_history(patient):
    return bool(getattr(patient, "premature_fhx_ascvd", False)) or bool(
        getattr(patient, "family_history_premature_ascvd", False)
    )


def _has_elevated_lpa(patient):
    value = _num(getattr(patient, "lp_a_value", None))
    unit = str(getattr(patient, "lp_a_unit", "") or "").strip()
    return bool(
        (unit == "nmol/L" and value is not None and value >= 125)
        or (unit == "mg/dL" and value is not None and value >= 50)
    )


def _non_hdl_elevated(patient):
    non_hdl = _num(getattr(patient, "non_hdl_c", None))
    return non_hdl is not None and non_hdl >= 130


def _has_lipid_uncertainty_context(patient, result):
    risk_category = getattr(result, "prevent_risk_category", None)
    risk_value = getattr(risk_category, "value", risk_category)
    prevent = _num(getattr(result, "prevent_10y_ascvd", None))
    return bool(
        risk_value
        in {
            RiskLevel.BORDERLINE,
            RiskLevel.INTERMEDIATE,
            RiskLevel.HIGH,
            "BORDERLINE",
            "INTERMEDIATE",
            "HIGH",
        }
        or (prevent is not None and prevent >= 3)
    )


def should_recommend_apob(patient, result):
    """Return True when missing ApoB could change lipid intensity or risk interpretation."""
    if getattr(patient, "apob", None) is not None:
        return False

    ldl_c = _num(getattr(patient, "ldl_c", None))
    triglycerides = _num(getattr(patient, "triglycerides", None))
    cac = _num(getattr(patient, "cac", None))
    bmi = _num(getattr(patient, "bmi", None))

    if ldl_c is not None and ldl_c >= 100:
        return True
    if triglycerides is not None and triglycerides >= 150:
        return True
    if _non_hdl_elevated(patient):
        return True
    if _has_premature_family_history(patient) or _has_elevated_lpa(patient):
        return True
    if cac is not None and cac > 0 and (ldl_c is None or ldl_c >= 70):
        return True
    if _has_lipid_uncertainty_context(patient, result) and ldl_c is not None and ldl_c >= 70:
        return True
    if (
        bool(getattr(patient, "diabetes", False))
        or bool(getattr(patient, "masld", False))
        or (bmi is not None and bmi >= 30)
    ) and (
        ldl_c is None
        or ldl_c >= 70
        or (triglycerides is not None and triglycerides >= 150)
        or _non_hdl_elevated(patient)
    ):
        return True

    return False


def should_recommend_lpa(patient, result):
    """Return True when missing Lp(a) could change inherited-risk counseling or intensity."""
    if getattr(patient, "lp_a_value", None) is not None:
        return False

    ldl_c = _num(getattr(patient, "ldl_c", None))
    cac = _num(getattr(patient, "cac", None))
    age = _num(getattr(patient, "age", None))

    if _has_premature_family_history(patient):
        return True
    if bool(getattr(patient, "possible_fh_pathway", False)) or bool(
        getattr(result, "possible_fh_pathway", False)
    ) or (
        ldl_c is not None and ldl_c >= 190
    ):
        return True
    if ldl_c is not None and 130 <= ldl_c < 190:
        return True
    if cac is not None and (cac >= 100 or (cac > 0 and age is not None and age < 55)):
        return True
    if _has_lipid_uncertainty_context(patient, result) and (
        ldl_c is None or ldl_c >= 70 or cac is None
    ):
        return True

    return False


def _uacr_completion_relevant(patient, result):
    prevent_category = getattr(result, "prevent_risk_category", None)
    a1c = getattr(patient, "a1c", None)
    egfr = getattr(patient, "egfr", None)
    sbp = getattr(patient, "sbp", None)
    dbp = getattr(patient, "dbp", None)
    bmi = getattr(patient, "bmi", None)
    triglycerides = getattr(patient, "triglycerides", None)

    return bool(
        getattr(patient, "diabetes", False)
        or (a1c is not None and a1c >= 5.7)
        or getattr(patient, "ckd", False)
        or getattr(patient, "hypertension", False)
        or getattr(patient, "bp_treated", False)
        or (sbp is not None and sbp >= 130)
        or (dbp is not None and dbp >= 80)
        or (egfr is not None and egfr < 90)
        or (bmi is not None and bmi >= 30)
        or (triglycerides is not None and triglycerides >= 150)
        or getattr(patient, "masld", False)
        or getattr(patient, "osa", False)
        or prevent_category in {RiskLevel.BORDERLINE, RiskLevel.INTERMEDIATE, RiskLevel.HIGH}
    )


def _add_uacr_completion_if_needed(ladder, patient, result):
    if getattr(patient, "uacr", None) is None and _uacr_completion_relevant(patient, result):
        ladder["recommend_uacr"] = True
        ladder["tier"] = max(ladder["tier"], 2)
        reason = "UACR is missing; obtain to complete kidney-risk assessment."
        if reason not in ladder["reasons"]:
            ladder["reasons"].append(reason)


def build_clarification_ladder(patient, result):
    ladder = {
        "tier": 0,
        "recommend_apob": False,
        "recommend_lpa": False,
        "recommend_cac": False,
        "recommend_uacr": False,
        "summary": "No major clarification testing recommended from current signals.",
        "reasons": [],
    }

    if getattr(patient, "clinical_ascvd", False) or (
        getattr(patient, "cac", None) is not None and patient.cac >= 300
    ):
        ladder["tier"] = 3
        ladder["summary"] = (
            "Very high-risk patient; clarification testing should not delay management."
        )
        ladder["reasons"].append(
            "Clinical ASCVD or CAC >=300 supports very high-risk management."
        )
        _add_uacr_completion_if_needed(ladder, patient, result)
        return ladder

    ldl_c = getattr(patient, "ldl_c", None)
    severe_ldl = ldl_c is not None and ldl_c >= 190

    if build_cac_recommendation(patient, result):
        ladder["recommend_cac"] = True
        ladder["tier"] = max(ladder["tier"], 2)
        ladder["reasons"].append(
            "CAC is missing and PREVENT risk is borderline/intermediate/high."
        )

    if not ladder["recommend_cac"] and getattr(patient, "cac", None) is None and not severe_ldl and (
        getattr(patient, "premature_fhx_ascvd", False)
        or getattr(patient, "family_history_premature_ascvd", False)
    ) and build_cac_recommendation(patient, result):
        ladder["recommend_cac"] = True
        ladder["tier"] = max(ladder["tier"], 2)
        ladder["reasons"].append(
            "CAC is missing with premature first-degree ASCVD family history."
        )

    if should_recommend_apob(patient, result):
        ladder["recommend_apob"] = True
        ladder["tier"] = max(ladder["tier"], 2)
        ladder["reasons"].append("ApoB may change lipid intensity or particle-burden interpretation.")

    if should_recommend_lpa(patient, result):
        ladder["recommend_lpa"] = True
        ladder["tier"] = max(ladder["tier"], 1)
        ladder["reasons"].append("Lp(a) may change inherited-risk counseling or treatment intensity.")

    _add_uacr_completion_if_needed(ladder, patient, result)

    recommendations = []
    if ladder["recommend_cac"]:
        recommendations.append("CAC")
    if ladder["recommend_apob"]:
        recommendations.append("ApoB")
    if ladder["recommend_lpa"]:
        recommendations.append("Lp(a)")
    if ladder["recommend_uacr"]:
        recommendations.append("UACR")

    if recommendations:
        ladder["summary"] = "Next useful clarifier(s): " + ", ".join(recommendations) + "."

    return ladder
