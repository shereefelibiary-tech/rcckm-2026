from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from rcckm.rule_trace import RecommendationTrace, build_rule_traces


FORBIDDEN_FRAGMENTS = (
    "hsCRP - inflammatory residual risk",
    "hsCRP - inflammatory biomarker clarification",
    "dominant_action",
    "action_domains",
    "risk_continuum_sublevel",
    "Supporting actions:",
)

CONTRADICTION_PAIRS = (
    ("No medication escalation", "high-intensity"),
    ("No medication escalation", "lipid-lowering therapy indicated"),
    ("No medication escalation", "statin therapy"),
    ("Subclinical coronary atherosclerosis", "CAC not performed"),
    ("aspirin not indicated", "aspirin may be considered"),
)


@dataclass
class GovernanceFinding:
    """One clinical governance validation finding."""

    category: str
    message: str
    severity: str = "error"


@dataclass
class GovernanceAudit:
    """Aggregate governance findings and trace records for one output."""

    findings: list[GovernanceFinding] = field(default_factory=list)
    traces: list[RecommendationTrace] = field(default_factory=list)

    @property
    def errors(self) -> list[GovernanceFinding]:
        return [finding for finding in self.findings if finding.severity == "error"]

    @property
    def warnings(self) -> list[GovernanceFinding]:
        return [finding for finding in self.findings if finding.severity == "warning"]

    @property
    def passed(self) -> bool:
        return not self.errors


def _add(findings: list[GovernanceFinding], category: str, message: str, severity: str = "error") -> None:
    findings.append(GovernanceFinding(category=category, message=message, severity=severity))


def _lower(text: str) -> str:
    return str(text or "").lower()


def _has_actionable_therapy(patient: Any, result: Any) -> bool:
    domains = getattr(result, "action_domains", None) or {}
    actionable_domains = {
        "lipids",
        "kidney",
        "ace_arb",
        "sglt2",
        "blood_pressure",
        "glycemia",
        "triglycerides",
        "tg_pharmacotherapy",
    }
    for domain in actionable_domains:
        recommendation = str(domains.get(domain) or "").lower()
        if recommendation and not recommendation.startswith(("no medication", "no escalation")):
            return True
    cac = getattr(patient, "cac", None)
    ldl = getattr(patient, "ldl_c", None)
    return bool(
        getattr(patient, "clinical_ascvd", False)
        or (ldl is not None and ldl >= 190)
        or (cac is not None and cac >= 100)
        or (getattr(patient, "uacr", None) is not None and patient.uacr >= 30)
        or (getattr(patient, "egfr", None) is not None and patient.egfr < 60)
    )


def validate_output_safety(patient: Any, result: Any, visible_text: str) -> list[GovernanceFinding]:
    """Validate terminology, contradiction, and never-cross output safety rules."""
    findings: list[GovernanceFinding] = []
    text = str(visible_text or "")
    lowered = _lower(text)

    for fragment in FORBIDDEN_FRAGMENTS:
        if fragment.lower() in lowered:
            _add(findings, "terminology", f"Forbidden fragment present: {fragment}")

    if "total cardiovascular risk" in lowered and (
        "10-year ASCVD risk" in text or "30-year ASCVD risk" in text
    ):
        _add(findings, "prevent", "ASCVD-only values are being described as total cardiovascular risk.")
    total_cvd_present = bool(
        getattr(result, "prevent_10y_total_cvd", None) is not None
        or getattr(result, "prevent_30y_total_cvd", None) is not None
    )
    if (
        "heart failure" in lowered
        and "HF risk" not in text
        and "PREVENT-HF" not in text
        and not total_cvd_present
    ):
        _add(findings, "prevent", "Heart failure is mentioned without an explicit HF risk output.", "warning")
    if "cardiovascular event risk" in lowered and "ASCVD risk" in text and not total_cvd_present:
        _add(findings, "prevent", "ASCVD-only risk should not be described as broad cardiovascular event risk.")

    for left, right in CONTRADICTION_PAIRS:
        if left.lower() in lowered and right.lower() in lowered:
            _add(findings, "contradiction", f"Contradictory phrases present: {left!r} with {right!r}")
    cac_zero_measured = re.search(
        r"\b(cac 0 measured|plaque:\s*cac 0|coronary calcium score:\s*0)\b",
        lowered,
    )
    if "cac not performed" in lowered and cac_zero_measured:
        _add(findings, "contradiction", "CAC not performed appears with measured CAC 0 language.")

    if _has_actionable_therapy(patient, result) and "no medication escalation today" in lowered:
        _add(findings, "action", "No medication escalation appears despite actionable therapy logic.")

    cac = getattr(patient, "cac", None)
    if cac is None and "Subclinical coronary atherosclerosis" in text:
        _add(findings, "plaque", "Missing CAC generated subclinical plaque language.")
    if cac == 0 and "plaque present" in lowered:
        _add(findings, "plaque", "CAC 0 output describes plaque as present.")
    if cac is not None and cac >= 100 and "mild plaque" in lowered:
        _add(findings, "plaque", "CAC >=100 should not be described as mild plaque.")
    if cac is not None and cac >= 300 and "within the expected range for age and sex" in lowered:
        _add(findings, "plaque", "CAC percentile language is softening high absolute CAC.")

    age = getattr(patient, "age", None)
    sex = str(getattr(patient, "sex", "") or "").lower()
    young_for_cac = bool((sex.startswith("f") and age is not None and age < 45) or (sex.startswith("m") and age is not None and age < 40))
    if young_for_cac and cac is None and "CAC reasonable for risk clarification" in text:
        _add(findings, "plaque", "Young CAC-missing patient has non-age-aware CAC wording.")

    uacr = getattr(patient, "uacr", None)
    egfr = getattr(patient, "egfr", None)
    if uacr is not None and uacr >= 30 and "normal kidney function" in lowered:
        _add(findings, "kidney", "Albuminuria output describes kidney status as normal.")
    if egfr is not None and egfr < 60 and "normal kidney function" in lowered:
        _add(findings, "kidney", "eGFR <60 output describes kidney status as normal.")

    if getattr(patient, "diabetes", False) is False and getattr(patient, "a1c", None) is not None and patient.a1c < 6.5:
        if re.search(r"\bType 2 diabetes mellitus\b", text):
            _add(findings, "diagnosis", "Prediabetes-range A1c became Type 2 diabetes diagnosis.")

    ldl = getattr(patient, "ldl_c", None)
    if ldl is not None and ldl >= 190 and "lifestyle" in lowered and "statin" not in lowered:
        _add(findings, "lipid", "LDL-C >=190 appears lifestyle-only.")

    aspirin_positive = bool(
        "aspirin may be considered" in lowered
        or "aspirin indicated" in lowered
        or re.search(r"(?<!do not )(?<!not )\bstart aspirin\b", lowered)
    )
    if "aspirin not indicated" in lowered and aspirin_positive:
        _add(findings, "aspirin", "Aspirin-negative and aspirin-positive language coexist.")

    if "sglt2 inhibitor" in lowered and "add an sglt2" in lowered:
        egfr_ok = egfr is not None and egfr >= 20
        strong_criteria = bool(
            egfr_ok
            and (
                getattr(patient, "diabetes", False)
                or getattr(patient, "heart_failure", False)
                or (uacr is not None and uacr >= 200)
            )
        )
        if not strong_criteria:
            _add(findings, "kidney", "Strong SGLT2 wording appears without strong SGLT2 criteria.")

    return findings


def _coerce_trace(trace: Any) -> RecommendationTrace:
    if isinstance(trace, RecommendationTrace):
        return trace
    return RecommendationTrace(**dict(trace))


def audit_result(patient: Any, result: Any, visible_text: str) -> GovernanceAudit:
    """Run governance traceability and safety checks for one evaluated patient."""
    raw_traces = list(getattr(result, "rule_traces", None) or build_rule_traces(patient, result))
    traces = [_coerce_trace(trace) for trace in raw_traces]
    findings = validate_output_safety(patient, result, visible_text)
    major_recommendations = [
        text
        for text in (getattr(result, "recommendations", None) or [])
        if str(text or "").strip()
    ]
    traced_text = {trace.recommendation_text for trace in traces}
    for recommendation in major_recommendations:
        if recommendation not in traced_text:
            _add(findings, "traceability", f"Recommendation lacks rule trace: {recommendation}")
    for trace in traces:
        if not trace.triggering_inputs:
            _add(findings, "traceability", f"Trace lacks triggering inputs: {trace.recommendation_id}")
        if not trace.evidence_basis:
            _add(findings, "traceability", f"Trace lacks evidence basis: {trace.recommendation_id}")
    return GovernanceAudit(findings=findings, traces=traces)
