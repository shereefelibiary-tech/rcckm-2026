from typing import Any

from modules.risk_enhancers.breast_arterial_calcification import (
    has_breast_arterial_calcification,
)
from modules.risk_enhancers.incidental_cac import incidental_cac_context


PREVENTION_CONTEXT_PRIMARY = "primary_prevention"
PREVENTION_CONTEXT_PRIMARY_SUBCLINICAL_PLAQUE = "primary_prevention_subclinical_plaque"
PREVENTION_CONTEXT_SECONDARY_ASCVD = "secondary_prevention_clinical_ascvd"

RULE_PRIMARY = "prevention_context_primary_no_clinical_ascvd"
RULE_PRIMARY_SUBCLINICAL_PLAQUE = "prevention_context_primary_subclinical_plaque"
RULE_SECONDARY_ASCVD = "prevention_context_secondary_clinical_ascvd"


def _num(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _context_value(engine_context: Any, key: str) -> Any:
    if engine_context is None:
        return None
    if isinstance(engine_context, dict):
        return engine_context.get(key)
    return getattr(engine_context, key, None)


def _add_unique(items: list[str], value: str | None) -> None:
    value = str(value or "").strip()
    if value and value not in items:
        items.append(value)


def _clinical_ascvd_reason(patient: Any) -> str:
    context = str(getattr(patient, "clinical_ascvd_context", "") or "").strip()
    if context:
        return f"Clinical ASCVD documented: {context}."
    return "Clinical ASCVD documented."


def _subclinical_plaque_findings(patient: Any, engine_context: Any) -> list[str]:
    findings: list[str] = []
    cac = _num(getattr(patient, "cac", None))
    if cac is not None and cac > 0:
        _add_unique(findings, f"CAC {cac:g}")

    incidental_context = incidental_cac_context(patient)
    if incidental_context:
        _add_unique(findings, "incidental coronary artery calcification on CT")

    if has_breast_arterial_calcification(patient):
        _add_unique(findings, "breast arterial calcification on mammogram")

    for attr, label in (
        ("coronary_plaque", "coronary plaque on imaging"),
        ("carotid_plaque", "carotid plaque"),
        ("aortic_calcification", "aortic calcification"),
        ("vascular_calcification", "non-coronary vascular calcification"),
    ):
        if bool(getattr(patient, attr, False)):
            _add_unique(findings, label)

    plaque_category = _context_value(engine_context, "plaque_category")
    plaque_value = str(getattr(plaque_category, "value", plaque_category) or "").upper()
    if plaque_value in {"MILD", "MODERATE", "SEVERE", "HIGH", "EXTENSIVE"}:
        _add_unique(findings, "coronary plaque on imaging")

    return findings


def classify_prevention_context(patient: Any, engine_context: Any = None) -> dict[str, Any]:
    """Classify prevention context before aspirin/antiplatelet rules run.

    Secondary prevention is reserved for documented clinical ASCVD. CAC and other
    subclinical imaging findings can intensify primary prevention but cannot create
    secondary-prevention status by themselves.
    """
    if bool(getattr(patient, "clinical_ascvd", False)):
        return {
            "prevention_context": PREVENTION_CONTEXT_SECONDARY_ASCVD,
            "primary_reason": _clinical_ascvd_reason(patient),
            "supporting_findings": ["clinical ASCVD"],
            "rule_id": RULE_SECONDARY_ASCVD,
        }

    subclinical_findings = _subclinical_plaque_findings(patient, engine_context)
    if subclinical_findings:
        primary = subclinical_findings[0]
        return {
            "prevention_context": PREVENTION_CONTEXT_PRIMARY_SUBCLINICAL_PLAQUE,
            "primary_reason": f"Primary prevention with subclinical plaque/imaging marker: {primary}.",
            "supporting_findings": subclinical_findings,
            "rule_id": RULE_PRIMARY_SUBCLINICAL_PLAQUE,
        }

    return {
        "prevention_context": PREVENTION_CONTEXT_PRIMARY,
        "primary_reason": "No documented clinical ASCVD.",
        "supporting_findings": [],
        "rule_id": RULE_PRIMARY,
    }
