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

VAGUE_RECOMMENDATION_FRAGMENTS = (
    "may be reasonable if",
    "risk-enhancing factors support treatment",
    "apob/ldl-c burden support treatment",
    "as clinically indicated",
    "optimize therapy",
    "risk-factor control",
    "management as appropriate",
    "treatment is reasonable",
    "consider treatment",
    "address risk factors",
    "follow clinically",
)

DIRECT_ACTION_VERBS = (
    "start",
    "discuss",
    "continue",
    "intensify",
    "add",
    "confirm",
    "obtain",
    "treat",
    "review",
    "avoid",
    "document",
    "reassess",
    "check",
    "repeat",
    "lower",
    "use",
)

DOMAIN_TERMS = (
    "lipid",
    "ldl",
    "apob",
    "statin",
    "cac",
    "plaque",
    "kidney",
    "uacr",
    "egfr",
    "bp",
    "blood pressure",
    "glyc",
    "a1c",
    "diabetes",
    "aspirin",
    "antiplatelet",
    "lp(a)",
    "hscrp",
    "triglyceride",
    "smoking",
    "ra",
    "inflammation",
)

NEUTRAL_STATUS_TERMS = (
    "not indicated",
    "not routine",
    "not routinely",
    "no escalation",
    "no medication changes",
    "key data available",
    "at goal",
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


def _is_allowed_appropriate_context(lowered: str) -> bool:
    return bool(
        "if clinically appropriate" in lowered
        and ("antiplatelet" in lowered or "aspirin" in lowered)
    )


def validate_recommendation_directness(text: str) -> list[GovernanceFinding]:
    """Flag vague recommendation language before it reaches output surfaces."""
    findings: list[GovernanceFinding] = []
    raw = str(text or "").strip()
    if not raw:
        return findings
    lowered = _lower(raw)

    if "no medication escalation today" in lowered:
        _add(
            findings,
            "directness",
            "Use domain-specific neutral wording instead of 'No medication escalation today'.",
        )

    for fragment in VAGUE_RECOMMENDATION_FRAGMENTS:
        if fragment in lowered:
            if fragment == "as clinically indicated" and _is_allowed_appropriate_context(lowered):
                continue
            _add(findings, "directness", f"Vague recommendation fragment present: {fragment}")

    return findings


def _contains_any(text: str, fragments: tuple[str, ...]) -> bool:
    lowered = _lower(text)
    return any(fragment in lowered for fragment in fragments)


def extract_domain_signals(text: str) -> dict[str, bool]:
    """Extract coarse clinical recommendation signals from rendered text."""
    lowered = _lower(text)
    cac_numeric = bool(re.search(r"\bcac\s*(?:score\s*)?(?:=|:)?\s*\d+", lowered))
    calcium_numeric = bool(re.search(r"\bcalcium score\s*(?:=|:)?\s*\d+", lowered))
    aspirin_consider = _contains_any(
        lowered,
        (
            "aspirin may be considered",
            "consider only if low bleeding risk",
            "consider aspirin",
            "aspirin: only if low bleeding risk",
        ),
    )
    antiplatelet_positive = _contains_any(
        lowered,
        (
            "antiplatelet therapy is indicated",
            "aspirin recommended",
            "start aspirin",
            "aspirin therapy indicated",
            "secondary-prevention antiplatelet",
            "antiplatelet therapy. use if no contraindication",
        ),
    )
    return {
        "lipid_intensify": _contains_any(
            lowered,
            (
                "intensify lipid",
                "intensify secondary-prevention lipid",
                "high-intensity therapy indicated",
                "high-intensity or maximally tolerated statin indicated",
                "high-intensity lipid-lowering",
                "secondary-prevention lipid therapy",
                "add-on lipid-lowering",
                "discuss lipid-lowering therapy",
                "lipid-lowering therapy recommended",
                "lipid-lowering therapy is reasonable",
                "lipid-lowering therapy is favored",
            ),
        ),
        "lipid_no_escalation": _contains_any(
            lowered,
            (
                "no lipid escalation",
                "lipid lowering: no escalation",
                "no escalation based on current ldl-c/apob",
            ),
        ),
        "statin_moderate": "moderate-intensity statin" in lowered,
        "statin_high": _contains_any(lowered, ("high-intensity statin", "high-intensity therapy indicated")),
        "cac_measured": cac_numeric or calcium_numeric or _contains_any(
            lowered,
            (
                "cac already measured",
                "cac 0",
                "calcified plaque detected",
                "plaque present",
                "high plaque burden",
                "elevated plaque burden",
            ),
        ),
        "cac_missing": _contains_any(
            lowered,
            (
                "cac not performed",
                "cac not done",
                "plaque burden unmeasured",
                "not measured",
            ),
        ),
        "cac_recommend_obtain": _contains_any(
            lowered,
            (
                "obtain cac",
                "cac may clarify",
                "cac reasonable",
                "calcium scan may help",
                "cac - risk clarification",
                "cac - plaque burden clarification",
                "consider cac",
            ),
        ),
        "kidney_albuminuria": bool(re.search(r"\buacr\s*(?:=|:)?\s*\d+", lowered))
        or _contains_any(lowered, ("albuminuria", "uacr a2", "uacr a3")),
        "sglt2_consider": _contains_any(
            lowered,
            (
                "consider sglt2",
                "add sglt2",
                "add an sglt2",
                "use sglt2",
                "sglt2 inhibitor",
            ),
        ),
        "bp_goal": _contains_any(lowered, ("<130/80", "130/80", "blood pressure goal", "bp goal")),
        "glycemia_action": _contains_any(
            lowered,
            (
                "optimize diabetes",
                "optimize glycemia",
                "prediabetes prevention",
                "a1c",
                "glycemia / metabolic",
            ),
        ),
        "aspirin_negative": _contains_any(
            lowered,
            (
                "aspirin not indicated",
                "not routine for primary prevention",
                "do not start routine aspirin",
                "aspirin is not routine",
            ),
        ),
        "aspirin_positive": antiplatelet_positive,
        "aspirin_conditional": aspirin_consider,
        "secondary_prevention": _contains_any(
            lowered,
            (
                "secondary prevention",
                "secondary-prevention",
                "clinical ascvd",
                "known cardiovascular disease is present",
            ),
        ),
        "primary_prevention": "primary prevention" in lowered or "primary-prevention" in lowered,
        "diagnoses_coding": _contains_any(lowered, ("assessment candidates", "icd", "hcc", "diagnosis")),
        "data_clarifiers": _contains_any(lowered, ("data to clarify", "clarifier", "obtain apob", "obtain uacr", "lp(a)")),
    }


def audit_cross_surface_alignment(
    action_card_text: str,
    emr_text: str,
    patient_text: str = "",
) -> list[GovernanceFinding]:
    """Flag semantic drift between Action, EMR, and patient recommendation surfaces."""
    findings: list[GovernanceFinding] = []
    action = _lower(action_card_text)
    emr = _lower(emr_text)
    patient = _lower(patient_text)
    combined = f"{emr}\n{patient}"
    action_signals = extract_domain_signals(action_card_text)
    emr_signals = extract_domain_signals(emr_text)
    combined_signals = extract_domain_signals(combined)

    if action_signals["lipid_intensify"] and not (
        combined_signals["lipid_intensify"]
        or _contains_any(
            combined,
            (
                "treat toward lipid",
                "lipid-lowering therapy is favored",
                "lipid-lowering therapy recommended",
                "lipid-lowering therapy indicated",
            ),
        )
    ):
        _add(
            findings,
            "cross_surface_alignment",
            "Drift detected: Action card says lipid intensification but EMR/patient text lacks lipid intensification.",
        )
    if action_signals["statin_high"] and "high-intensity" not in combined:
        _add(findings, "cross_surface_alignment", "Action card high-intensity lipid therapy is missing from EMR/patient text.")
    if action_signals["statin_moderate"] and "moderate-intensity statin" not in combined:
        _add(findings, "cross_surface_alignment", "Action card moderate-intensity statin language is missing from EMR/patient text.")
    if action_signals["lipid_no_escalation"] and (
        emr_signals["lipid_intensify"] or emr_signals["statin_moderate"] or emr_signals["statin_high"]
    ):
        _add(findings, "cross_surface_alignment", "Action card says no lipid escalation while EMR recommends lipid escalation.")
    if "statin therapy is reasonable" in emr and action_signals["lipid_no_escalation"]:
        _add(findings, "cross_surface_alignment", "EMR recommends statin therapy while Action card says no lipid escalation.")
    if emr_signals["aspirin_negative"] and action_signals["aspirin_positive"] and not action_signals["secondary_prevention"]:
        _add(findings, "cross_surface_alignment", "Aspirin recommendation differs between Action card and EMR.")
    if action_signals["aspirin_negative"] and emr_signals["aspirin_positive"] and not emr_signals["secondary_prevention"]:
        _add(findings, "cross_surface_alignment", "Aspirin recommendation differs between Action card and EMR.")
    if action_signals["cac_measured"] and emr_signals["cac_missing"]:
        _add(findings, "cross_surface_alignment", "CAC status differs between Action card and EMR.")
    if action_signals["cac_measured"] and combined_signals["cac_recommend_obtain"]:
        _add(findings, "cross_surface_alignment", "CAC already measured but another surface recommends obtaining CAC.")
    if action_signals["kidney_albuminuria"] and not emr_signals["kidney_albuminuria"]:
        _add(findings, "cross_surface_alignment", "Kidney action mentions albuminuria but EMR lacks UACR/albuminuria context.")
    if "no kidney-risk signal" in action and (emr_signals["sglt2_consider"] or "optimize kidney-protective" in emr):
        _add(findings, "cross_surface_alignment", "Kidney recommendation differs between Action card and EMR.")
    if combined_signals["secondary_prevention"] and _contains_any(
        combined,
        (
            "prevention worth discussing",
            "low prevent score lowers treatment",
        ),
    ):
        _add(findings, "cross_surface_alignment", "Secondary-prevention text appears to de-risk treatment using primary-prevention framing.")

    return findings


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

    findings.extend(validate_recommendation_directness(text))

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


def audit_result(
    patient: Any,
    result: Any,
    visible_text: str,
    *,
    action_card_text: str = "",
    emr_text: str = "",
    patient_text: str = "",
) -> GovernanceAudit:
    """Run governance traceability and safety checks for one evaluated patient."""
    raw_traces = list(getattr(result, "rule_traces", None) or build_rule_traces(patient, result))
    traces = [_coerce_trace(trace) for trace in raw_traces]
    findings = validate_output_safety(patient, result, visible_text)
    if action_card_text or emr_text or patient_text:
        findings.extend(audit_cross_surface_alignment(action_card_text, emr_text, patient_text))
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
