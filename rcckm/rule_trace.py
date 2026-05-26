from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from modules.prevent.lipid_bands import (
    classify_prevent_ascvd_10yr_lipid_band,
    classify_prevent_ascvd_30yr_band,
    get_major_lipid_risk_enhancers,
    lipid_recommendation_from_prevent_band,
)
from rcckm.evidence_map import get_evidence_basis


@dataclass(frozen=True)
class RecommendationTrace:
    """Trace one recommendation from patient inputs to a governance rule."""

    recommendation_id: str
    recommendation_text: str
    domain: str
    triggering_inputs: dict[str, Any]
    rule_id: str
    evidence_basis: str
    strength_language: str
    uncertainty_flags: list[str]
    missing_data_that_could_change_decision: list[str]
    patient_facing_allowed: bool
    emr_allowed: bool

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable representation for tests and reports."""
        return asdict(self)


def _risk_category(result: Any) -> str | None:
    category = getattr(result, "prevent_risk_category", None)
    value = getattr(category, "value", category)
    return str(value) if value else None


def _input_snapshot(patient: Any, result: Any, keys: tuple[str, ...]) -> dict[str, Any]:
    snapshot: dict[str, Any] = {}
    for key in keys:
        if hasattr(patient, key):
            value = getattr(patient, key, None)
        else:
            value = getattr(result, key, None)
        if value is not None:
            snapshot[key] = value
    if "prevent_risk_category" in keys:
        category = _risk_category(result)
        if category:
            snapshot["prevent_risk_category"] = category
    return snapshot


def _missing_data(patient: Any, result: Any, domain: str, text: str) -> list[str]:
    missing: list[str] = []
    if domain in {"lipid", "diagnostics", "plaque"}:
        if getattr(patient, "apob", None) is None:
            missing.append("ApoB")
        if getattr(patient, "lp_a_value", None) is None:
            missing.append("Lp(a)")
        if getattr(patient, "cac", None) is None and bool(getattr(patient, "cac_not_done", False)):
            missing.append("CAC")
    if domain in {"kidney", "BP"} and getattr(patient, "uacr", None) is None:
        missing.append("UACR")
    if "hsCRP" in text and getattr(patient, "hscrp", None) is None:
        missing.append("hsCRP")
    if not getattr(result, "prevent_available", False):
        missing.extend(str(item) for item in (getattr(result, "prevent_missing_inputs", None) or []))
    return sorted(set(missing))


def _strength_from_text(text: str, fallback: str) -> str:
    lowered = str(text or "").lower()
    if "not indicated" in lowered or "not routinely recommended" in lowered or "defer" in lowered:
        return "defer"
    if "continue" in lowered:
        return "continue"
    if "consider" in lowered or "may clarify" in lowered or "if" in lowered:
        return "consider"
    if "reasonable" in lowered or "favored" in lowered:
        return "reasonable"
    if "recommended" in lowered or "indicated" in lowered or "recommend" in lowered:
        return "recommended"
    return fallback


def _lipid_rule_id(patient: Any, result: Any, text: str) -> str:
    lowered = str(text or "").lower()
    risk = getattr(result, "prevent_10y_ascvd", None)
    if bool(getattr(patient, "clinical_ascvd", False)) or "secondary-prevention" in lowered:
        return "lipid_clinical_ascvd_secondary_prevention"
    if (getattr(patient, "ldl_c", None) is not None and patient.ldl_c >= 190) or bool(getattr(patient, "suspected_fh_hefh", False)):
        return "prevent_lipid_ldl_190_override"
    age = getattr(patient, "age", None)
    if (
        bool(getattr(patient, "diabetes", False))
        and age is not None
        and 40 <= age <= 75
        and getattr(patient, "ldl_c", None) is not None
        and patient.ldl_c >= 70
    ):
        return "prevent_lipid_diabetes_override"
    if getattr(patient, "cac", None) is not None and patient.cac >= 100:
        return "cac_score_ge_100_plaque_burden"
    if getattr(patient, "cac", None) is not None and patient.cac > 0:
        return "prevent_lipid_plaque_override"
    recommendation = lipid_recommendation_from_prevent_band(
        patient,
        risk,
        getattr(result, "prevent_30y_ascvd", None),
    )
    if risk is not None and recommendation.trace_rule_id != "prevent_lipid_unknown":
        return recommendation.trace_rule_id
    if risk is not None and risk >= 20:
        return "lipid_prevent_ascvd_ge_20"
    if risk is not None and 7.5 <= risk < 20:
        return "lipid_prevent_ascvd_7_5_to_20"
    if risk is not None and 5 <= risk < 7.5:
        return (
            "lipid_prevent_ascvd_5_to_7_5_with_enhancers"
            if "reasonable" in lowered or "favored" in lowered
            else "lipid_prevent_ascvd_5_to_7_5_no_enhancers"
        )
    if risk is not None and 3 <= risk < 5:
        return (
            "lipid_prevent_ascvd_3_to_5_with_major_enhancers"
            if "worth discussing" in lowered or "consider" in lowered
            else "lipid_prevent_ascvd_3_to_5_no_enhancers"
        )
    if risk is not None and risk < 3 and "lifestyle-focused" in lowered:
        return "lipid_prevent_ascvd_lt_3"
    if "albuminuria" in lowered:
        return "lipid_borderline_with_albuminuria"
    if getattr(result, "prevent_30y_ascvd", None) is not None and result.prevent_30y_ascvd >= 10:
        return "lipid_lifetime_trajectory"
    return "lipid_lifetime_trajectory" if "cumulative" in lowered else "diagnostic_completion"


def _rule_id_for_domain(domain: str, patient: Any, result: Any, text: str) -> str:
    lowered = str(text or "").lower()
    if domain == "lipids":
        return _lipid_rule_id(patient, result, text)
    if domain == "cac_testing":
        age = getattr(patient, "age", None)
        sex = str(getattr(patient, "sex", "") or "").lower()
        young = bool((sex.startswith("f") and age is not None and age < 45) or (sex.startswith("m") and age is not None and age < 40))
        return "cac_young_age_defer" if young else "cac_plaque_clarification"
    if domain == "kidney":
        return "kidney_albuminuria_confirm_persistence" if "albuminuria" in lowered else "diagnostic_completion"
    if domain == "ace_arb":
        return "kidney_ace_arb_albuminuria_bp"
    if domain == "sglt2":
        if "add an sglt2" in lowered or getattr(patient, "uacr", None) is not None and patient.uacr >= 200:
            return "kidney_sglt2_uacr_ge_200_egfr_ge_20"
        return "kidney_sglt2_albuminuria_conditional"
    if domain == "blood_pressure":
        return "bp_albuminuria_goal_130_80"
    if domain == "glycemia":
        return "glycemia_a1c_ge_7"
    if domain in {"triglycerides", "tg_diet", "tg_pharmacotherapy", "rdn_referral"}:
        return "tg_ge_500_pancreatitis"
    if domain == "aspirin":
        return "aspirin_primary_prevention_not_indicated"
    return "diagnostic_completion"


def _domain_label(domain: str) -> str:
    return {
        "lipids": "lipid",
        "cac_testing": "diagnostics",
        "ace_arb": "kidney",
        "sglt2": "kidney",
        "blood_pressure": "BP",
        "uacr_testing": "diagnostics",
        "lpa_testing": "diagnostics",
        "apob_testing": "diagnostics",
        "hscrp_testing": "diagnostics",
    }.get(domain, domain)


def _triggering_inputs_for_domain(domain: str, patient: Any, result: Any) -> dict[str, Any]:
    if domain == "lipids":
        keys = ("age", "ldl_c", "non_hdl_c", "apob", "triglycerides", "cac", "prevent_10y_ascvd", "prevent_30y_ascvd", "prevent_risk_category", "clinical_ascvd")
    elif domain in {"kidney", "ace_arb", "sglt2"}:
        keys = ("egfr", "uacr", "albuminuria_stage", "egfr_stage", "diabetes", "heart_failure", "bp_treated", "sbp", "dbp", "ace_arb")
    elif domain in {"uacr_testing", "lpa_testing", "apob_testing", "hscrp_testing"}:
        keys = ("age", "sex", "egfr", "uacr", "a1c", "diabetes", "prevent_10y_ascvd", "prevent_30y_ascvd", "prevent_risk_category")
    elif domain == "blood_pressure":
        keys = ("sbp", "dbp", "bp_treated", "hypertension", "uacr")
    elif domain == "cac_testing":
        keys = ("age", "sex", "cac", "cac_not_done", "prevent_10y_ascvd", "prevent_30y_ascvd", "ldl_c", "apob")
    elif domain == "glycemia":
        keys = ("a1c", "diabetes")
    elif domain in {"triglycerides", "tg_diet", "tg_pharmacotherapy", "rdn_referral"}:
        keys = ("triglycerides", "non_hdl_c", "apob")
    else:
        keys = ("age", "sex", "prevent_10y_ascvd", "prevent_30y_ascvd")
    snapshot = _input_snapshot(patient, result, keys)
    if domain == "lipids":
        recommendation = lipid_recommendation_from_prevent_band(
            patient,
            getattr(result, "prevent_10y_ascvd", None),
            getattr(result, "prevent_30y_ascvd", None),
        )
        enhancer_groups = get_major_lipid_risk_enhancers(patient, result)
        snapshot.update(
            {
                "risk_10yr_ascvd": getattr(result, "prevent_10y_ascvd", None),
                "risk_30yr_ascvd": getattr(result, "prevent_30y_ascvd", None),
                "prevent_10yr_lipid_band": classify_prevent_ascvd_10yr_lipid_band(
                    getattr(result, "prevent_10y_ascvd", None)
                ),
                "prevent_30yr_band": classify_prevent_ascvd_30yr_band(
                    getattr(result, "prevent_30y_ascvd", None)
                ),
                "enhancers_present": recommendation.enhancers_present,
                "hard_indications": enhancer_groups["hard_indications"],
                "major_enhancers": enhancer_groups["major_enhancers"],
                "supporting_enhancers": enhancer_groups["supporting_enhancers"],
                "recommendation_strength": recommendation.recommendation_strength,
                "rule_id": recommendation.trace_rule_id,
            }
        )
    return snapshot


def build_rule_traces(patient: Any, result: Any) -> list[RecommendationTrace]:
    """Build structured trace metadata for active recommendation domains."""
    traces: list[RecommendationTrace] = []
    domains = getattr(result, "action_domains", None) or {}
    for domain, recommendation in domains.items():
        text = str(recommendation or "").strip()
        if not text:
            continue
        rule_id = _rule_id_for_domain(str(domain), patient, result, text)
        evidence = get_evidence_basis(rule_id)
        public_domain = _domain_label(str(domain))
        traces.append(
            RecommendationTrace(
                recommendation_id=f"{rule_id}:{domain}",
                recommendation_text=text,
                domain=public_domain,
                triggering_inputs=_triggering_inputs_for_domain(str(domain), patient, result),
                rule_id=rule_id,
                evidence_basis=evidence.evidence_basis,
                strength_language=_strength_from_text(text, evidence.default_strength_language),
                uncertainty_flags=[],
                missing_data_that_could_change_decision=_missing_data(patient, result, public_domain, text),
                patient_facing_allowed=evidence.patient_facing_allowed,
                emr_allowed=evidence.emr_allowed,
            )
        )
    return traces
