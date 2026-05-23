from core.enums import RiskLevel
from modules.cac_recommendation.engine import build_cac_recommendation


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

    if getattr(patient, "apob", None) is None and getattr(patient, "ldl_c", None) is not None:
        ladder["recommend_apob"] = True
        ladder["tier"] = max(ladder["tier"], 2)
        ladder["reasons"].append("ApoB is missing despite available LDL-C.")

    if getattr(patient, "lp_a_value", None) is None:
        ladder["recommend_lpa"] = True
        ladder["tier"] = max(ladder["tier"], 1)
        ladder["reasons"].append("Lp(a) is missing.")

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
