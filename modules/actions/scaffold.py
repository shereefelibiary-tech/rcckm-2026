from dataclasses import dataclass, field
import re
from typing import Any

from modules.cac_recommendation.engine import build_cac_age_gate_note
from modules.prevention_context.engine import (
    PREVENTION_CONTEXT_SECONDARY_ASCVD,
    classify_prevention_context,
)
from modules.risk_enhancers.reproductive import has_reproductive_risk_markers
from renderers.render_modes import RenderMode


@dataclass
class ActionSection:
    label: str
    line: str = ""
    items: list[str] = field(default_factory=list)


@dataclass
class CompactActionItem:
    title: str
    subtitle: str = ""
    detail: str = ""
    source: str = ""


@dataclass
class ActionDomainReadout:
    domain_id: str
    label: str
    status: str
    detail: str = ""
    priority: str = "none"
    state: str = "neutral"
    rule_id: str = ""
    trace_inputs: dict[str, Any] = field(default_factory=dict)
    detail_lines: list[str] = field(default_factory=list)
    hover_detail: str = ""
    expanded_detail_lines: list[str] = field(default_factory=list)
    recommendation_strength: str = ""
    emr_line: str = ""
    emr_lines: list[str] = field(default_factory=list)
    patient_line: str = ""
    action_card_line: str = ""
    display_priority: int = 0


ActionDomain = ActionDomainReadout


TESTING_LABELS = {
    "apob_testing": "ApoB - particle burden clarification",
    "lpa_testing": "Lp(a) - one-time risk assessment",
    "uacr_testing": "Obtain UACR to complete kidney-risk assessment.",
    "cac_testing": "CAC - risk clarification",
    "hscrp_testing": "Consider hsCRP only if inflammatory risk clarification would change management.",
    "fasting_lipids": "Repeat fasting lipids - confirm triglyceride burden",
}


def _num(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _has_domain(result: Any, domain: str) -> bool:
    domains = _domains(result)
    return domain in domains


def _domain_line(result: Any, domain: str) -> str:
    domains = _domains(result)
    value = domains.get(domain)
    return str(value or "").strip()


def _domains(result: Any) -> dict[str, str]:
    domains = dict(getattr(result, "action_domains", None) or {})
    recommendations = [str(x or "").strip() for x in getattr(result, "recommendations", []) or []]
    for recommendation in recommendations:
        if not recommendation:
            continue
        low = recommendation.lower()
        if "reasonable" in low and low.startswith(("treatment", "lipid-lowering therapy")):
            continue
        if low.startswith("no medication changes"):
            continue
        if ("lipid-lowering" in low or "statin therapy" in low) and "lipids" not in domains:
            domains["lipids"] = recommendation
        elif low.startswith("optimize kidney") and "kidney" not in domains:
            domains["kidney"] = recommendation
        elif low.startswith("confirm persistent albuminuria") and "kidney" not in domains:
            domains["kidney"] = recommendation
        elif low.startswith("continue kidney-protective") and "kidney" not in domains:
            domains["kidney"] = recommendation
        elif low.startswith("optimize glycemic") and "glycemia" not in domains:
            domains["glycemia"] = recommendation
        elif low.startswith("optimize bp") and "blood_pressure" not in domains:
            domains["blood_pressure"] = recommendation
        elif low.startswith("treat bp") and "blood_pressure" not in domains:
            domains["blood_pressure"] = recommendation
        elif ("acei/arb" in low or "ace inhibitor" in low) and "ace_arb" not in domains:
            domains["ace_arb"] = recommendation
        elif "sglt2 inhibitor" in low and "sglt2" not in domains:
            domains["sglt2"] = recommendation
        elif low.startswith("coronary calcium") and "cac_testing" not in domains:
            domains["cac_testing"] = recommendation
        elif low.startswith("obtain uacr") and "uacr_testing" not in domains:
            domains["uacr_testing"] = recommendation
        elif low.startswith("obtain apob") and "apob_testing" not in domains:
            domains["apob_testing"] = recommendation
        elif low.startswith("check lp(a)") and "lpa_testing" not in domains:
            domains["lpa_testing"] = recommendation
        elif low.startswith("consider hscrp") and "hscrp_testing" not in domains:
            domains["hscrp_testing"] = recommendation
        elif low.startswith("repeat fasting") and "fasting_lipids" not in domains:
            domains["fasting_lipids"] = recommendation
        elif "clarification testing should not delay treatment" in low and "treatment_timing" not in domains:
            domains["treatment_timing"] = recommendation
    return domains


def _unique(items: list[str]) -> list[str]:
    out: list[str] = []
    for item in items:
        item = str(item or "").strip()
        if item and item not in out:
            out.append(item)
    return out


def _clean_readout_text(text: Any) -> str:
    text = str(text or "").strip()
    if text.lower() in {"none", "null", "nan"}:
        return ""
    return " ".join(text.split())


def _make_readout(
    domain_id: str,
    label: str,
    status: str,
    detail: str = "",
    *,
    priority: str = "none",
    state: str = "neutral",
    rule_id: str = "",
    trace_inputs: dict[str, Any] | None = None,
    detail_lines: list[str] | None = None,
    hover_detail: str = "",
    expanded_detail_lines: list[str] | None = None,
    recommendation_strength: str = "",
    emr_line: str = "",
    emr_lines: list[str] | None = None,
    patient_line: str = "",
    action_card_line: str = "",
    display_priority: int = 0,
) -> ActionDomainReadout:
    clean_status = _clean_readout_text(status) or "No active signal"
    clean_detail = _clean_readout_text(detail)
    default_card = f"{clean_status}. {clean_detail}".strip()
    return ActionDomainReadout(
        domain_id=domain_id,
        label=label,
        status=clean_status,
        detail=clean_detail,
        priority=priority,
        state=state,
        rule_id=rule_id,
        trace_inputs=trace_inputs or {},
        detail_lines=[_clean_readout_text(line) for line in (detail_lines or []) if _clean_readout_text(line)],
        hover_detail=_clean_readout_text(hover_detail),
        expanded_detail_lines=[
            _clean_readout_text(line) for line in (expanded_detail_lines or []) if _clean_readout_text(line)
        ],
        recommendation_strength=_clean_readout_text(recommendation_strength),
        emr_line=_clean_readout_text(emr_line),
        emr_lines=[_clean_readout_text(line) for line in (emr_lines or []) if _clean_readout_text(line)],
        patient_line=_clean_readout_text(patient_line),
        action_card_line=_clean_readout_text(action_card_line) or default_card.rstrip(".") + ".",
        display_priority=display_priority,
    )


def _append_compact(
    items: list[CompactActionItem],
    title: str,
    subtitle: str = "",
    detail: str = "",
    source: str = "",
) -> None:
    title = str(title or "").strip()
    subtitle = str(subtitle or "").strip()
    detail = str(detail or "").strip()
    if not title:
        return
    key = (title.lower(), subtitle.lower())
    if any((item.title.lower(), item.subtitle.lower()) == key for item in items):
        return
    items.append(CompactActionItem(title, subtitle, detail, source))


def _has_compact_source(items: list[CompactActionItem], source: str) -> bool:
    return any(item.source == source for item in items)


def _prevent_high(result: Any) -> bool:
    category = getattr(getattr(result, "prevent_risk_category", None), "value", None)
    category = category or getattr(result, "prevent_risk_category", None)
    risk = _num(getattr(result, "prevent_10y_ascvd", None))
    return category == "HIGH" or (risk is not None and risk >= 20)


def _prevent_low(result: Any) -> bool:
    category = getattr(getattr(result, "prevent_risk_category", None), "value", None)
    category = category or getattr(result, "prevent_risk_category", None)
    risk = _num(getattr(result, "prevent_10y_ascvd", None))
    return category == "LOW" or (risk is not None and risk < 3)


def _prevent_intermediate(result: Any) -> bool:
    category = getattr(getattr(result, "prevent_risk_category", None), "value", None)
    category = category or getattr(result, "prevent_risk_category", None)
    return category == "INTERMEDIATE"


def _level_3b_intermediate_prevent_path(result: Any) -> bool:
    classification = getattr(result, "level_classification", None) or {}
    return bool(
        _prevent_intermediate(result)
        and str(classification.get("level") or "") == "3B"
    )


def _has_elevated_lpa(patient: Any) -> bool:
    value = _num(getattr(patient, "lp_a_value", None))
    unit = str(getattr(patient, "lp_a_unit", "") or "").strip()
    return bool(
        (unit == "nmol/L" and value is not None and value >= 125)
        or (unit == "mg/dL" and value is not None and value >= 50)
    )


def _has_premature_family_history(patient: Any) -> bool:
    return bool(
        getattr(patient, "premature_fhx_ascvd", False)
        or getattr(patient, "family_history_premature_ascvd", False)
    )


def _low_with_lpa_family_context(patient: Any, result: Any) -> bool:
    return bool(_prevent_low(result) and _has_elevated_lpa(patient) and _has_premature_family_history(patient))


def _has_rheumatoid_arthritis(patient: Any) -> bool:
    return bool(getattr(patient, "rheumatoid_arthritis", False))


def _ra_low_short_term_context(patient: Any, result: Any) -> bool:
    if not (_has_rheumatoid_arthritis(patient) and _has_premature_family_history(patient)):
        return False
    risk_10y = _num(getattr(result, "prevent_10y_ascvd", None))
    prevent_30y = _num(getattr(result, "prevent_30y_ascvd", None))
    ldl_c = _num(getattr(patient, "ldl_c", None))
    apob = _num(getattr(patient, "apob", None))
    return bool(
        risk_10y is not None
        and risk_10y < 3
        and (prevent_30y is None or prevent_30y < 15)
        and (ldl_c is None or ldl_c < 160)
        and (apob is None or apob < 120)
        and _num(getattr(patient, "cac", None)) is None
    )


def _low_with_lpa_reproductive_context(patient: Any, result: Any) -> bool:
    return bool(_prevent_low(result) and _has_elevated_lpa(patient) and has_reproductive_risk_markers(patient))


def _clinical_ascvd(patient: Any) -> bool:
    return bool(getattr(patient, "clinical_ascvd", False))


def _prevention_context(patient: Any, result: Any) -> str:
    context = str(getattr(result, "prevention_context", "") or "").strip()
    if context:
        return context
    return classify_prevention_context(patient, result)["prevention_context"]


def _triglycerides(patient: Any) -> float | None:
    return _num(getattr(patient, "triglycerides", None))


def _lipid_line(patient: Any, result: Any) -> str:
    if _clinical_ascvd(patient):
        line = _domain_line(result, "lipids")
        if line:
            return line
        return "Secondary-prevention lipid-lowering therapy indicated; treat toward ASCVD targets."

    line = _domain_line(result, "lipids")
    cac = _num(getattr(patient, "cac", None))
    if cac is not None and cac >= 300:
        return "High-intensity lipid-lowering therapy indicated; treat toward high-risk targets."
    if line:
        return line

    dominant = str(getattr(result, "dominant_action", None) or "").strip()
    dominant_low = dominant.lower()
    if ("reasonable" in dominant_low and dominant_low.startswith(("treatment", "lipid-lowering therapy"))) or dominant_low.startswith("no medication changes"):
        dominant = ""
        dominant_low = ""
    non_lipid_starts = (
        "Optimize kidney",
        "Confirm persistent albuminuria",
        "Continue kidney-protective",
        "Consider ACE inhibitor",
        "Continue or optimize ACEi/ARB",
        "Consider SGLT2",
        "Add an SGLT2",
        "SGLT2 inhibitor",
        "Optimize glycemic",
        "Optimize BP",
        "Address smoking",
        "Obtain ",
        "Check ",
        "Coronary calcium",
        "CAC ",
        "Consider hsCRP",
        "Repeat fasting",
        "No escalation",
        "No medication changes",
        "No active domain changes",
    )
    if dominant and not dominant.startswith(non_lipid_starts):
        return dominant

    ldl = _num(getattr(patient, "ldl_c", None))
    if (ldl is not None and ldl >= 190) or bool(getattr(patient, "suspected_fh_hefh", False)):
        return "High-intensity or maximally tolerated statin therapy indicated."
    if _low_with_lpa_reproductive_context(patient, result):
        return "Lipid lowering: no escalation today; document elevated Lp(a) and reproductive risk markers as risk enhancers."
    if _low_with_lpa_family_context(patient, result):
        return "Lipid lowering: no escalation today; document elevated Lp(a) and premature family history as risk enhancers."
    if _prevent_high(result):
        return "Lipid-lowering therapy is indicated; treat toward high-risk targets."
    return "Lipid lowering: no escalation based on current LDL-C/ApoB and ASCVD risk profile."


def _lipid_monitoring_item(patient: Any, result: Any) -> str | None:
    line = _lipid_line(patient, result).lower()
    if (
        "lipid-lowering therapy indicated" in line
        or "intensify lipid-lowering therapy" in line
        or "lipid-lowering therapy is reasonable" in line
        or "statin therapy" in line
        or "consider lipid-lowering therapy" in line
    ):
        return "Recheck lipid profile 4-12 weeks after starting or intensifying therapy, then every 6-12 months."
    return None


def _cac_line(patient: Any, result: Any) -> str | None:
    cac = _num(getattr(patient, "cac", None))
    cac_testing = _has_domain(result, "cac_testing")

    if _clinical_ascvd(patient):
        if cac is not None and cac == 0:
            return "CAC 0 is discordant/historical and should not be used to de-risk established ASCVD."
        if cac is not None:
            return f"CAC {cac:g} may be documented as plaque context; secondary-prevention management is driven by clinical ASCVD."
        return "Plaque is established clinically; CAC is not needed for current decision-making."

    if cac is not None:
        cac_s = f"{cac:g}"
        if cac == 0:
            ldl = _num(getattr(patient, "ldl_c", None))
            if ldl is not None and ldl >= 190:
                return "CAC 0 measured; do not use CAC 0 to defer lipid-lowering therapy in LDL-C >=190 / possible FH pathway."
            return f"CAC {cac_s} measured; no calcified plaque detected."
        if 1 <= cac <= 99:
            return f"CAC {cac_s} measured; plaque present."
        if 100 <= cac <= 299:
            return f"CAC {cac_s} already measured; no repeat CAC needed for current decision-making."
        if 300 <= cac <= 999:
            return f"CAC {cac_s} already measured; no repeat CAC needed for current decision-making."
        return f"CAC {cac_s} already measured; no repeat CAC needed for current decision-making."

    if getattr(patient, "cac_not_done", False):
        line = "CAC not performed; plaque burden unmeasured."
    else:
        line = "Plaque burden unmeasured."

    if _ra_low_short_term_context(patient, result):
        return "CAC is not routinely needed at this risk level; use only if results would change lipid-treatment decisions."

    if cac_testing and not _clinical_ascvd(patient):
        return _domain_line(result, "cac_testing") or "CAC reasonable for risk clarification if treatment decision remains uncertain."
    elif not cac_testing:
        age_gate_note = build_cac_age_gate_note(patient, result)
        if age_gate_note:
            if getattr(patient, "cac_not_done", False):
                line = "CAC not routinely recommended at this age; consider only if results would change management."
            else:
                line += f" {age_gate_note}"
        elif _prevent_low(result) and _num(getattr(patient, "age", None)) is not None:
            sex = str(getattr(patient, "sex", "") or "").strip().lower()
            age = _num(getattr(patient, "age", None))
            below_usual_age = (
                (sex.startswith("f") and age < 45)
                or (sex.startswith("m") and age < 40)
            )
            if below_usual_age:
                return None
    return line


def _aspirin_line(patient: Any, result: Any) -> str:
    age = _num(getattr(patient, "age", None))
    cac = _num(getattr(patient, "cac", None))

    if _prevention_context(patient, result) == PREVENTION_CONTEXT_SECONDARY_ASCVD:
        return "Antiplatelet therapy is indicated for secondary prevention if clinically appropriate and no contraindication is present."
    if _aspirin_active(patient):
        return "Aspirin active; confirm indication."
    if _aspirin_bleeding_risk_high(patient):
        return "Avoid routine primary-prevention aspirin."
    if age is not None and age >= 70:
        return "Aspirin not routine for primary prevention."
    if cac is None:
        return "Aspirin not routine for primary prevention."
    if cac < 100:
        return "Aspirin not routine for primary prevention."
    if age is not None and 40 <= age <= 69 and cac >= 300:
        return "Aspirin may be considered if bleeding risk is low; plaque burden is high."
    if age is not None and 40 <= age <= 69 and cac >= 100:
        return "Aspirin may be considered only if bleeding risk is low."
    return "Aspirin not routine for primary prevention."


def _aspirin_bleeding_risk_high(patient: Any) -> bool:
    if bool(getattr(patient, "aspirin_bleeding_risk_high", False)):
        return True
    if bool(getattr(patient, "bleeding_risk_high", False)) or bool(getattr(patient, "high_bleeding_risk", False)):
        return True
    bleeding_risk = str(getattr(patient, "bleeding_risk", "") or "").strip().lower()
    return bleeding_risk in {"high", "elevated"}


def _aspirin_active(patient: Any) -> bool:
    if bool(getattr(patient, "aspirin", False)) or bool(getattr(patient, "aspirin_active", False)):
        return True
    medication_text = str(getattr(patient, "medications_raw", "") or "").lower()
    return bool(re.search(r"\b(?:aspirin|asa)\b", medication_text))


def _clarifier_items(result: Any) -> list[str]:
    domains = _domains(result)
    items = []
    for key in TESTING_LABELS:
        if key not in domains:
            continue
        if key == "cac_testing":
            continue
        if key == "fasting_lipids" and _domain_line(result, key):
            items.append(_domain_line(result, key))
        else:
            items.append(TESTING_LABELS[key])
    if "treatment_timing" in domains and items:
        items.append("Clarification testing should not delay treatment.")
    return _unique(items)


def _clarifier_items_without(result: Any, excluded: set[str]) -> list[str]:
    domains = _domains(result)
    items = []
    for key in TESTING_LABELS:
        if key in excluded or key not in domains:
            continue
        if key == "cac_testing":
            continue
        if key == "fasting_lipids" and _domain_line(result, key):
            items.append(_domain_line(result, key))
        else:
            items.append(TESTING_LABELS[key])
    if "treatment_timing" in domains and items:
        items.append("Clarification testing should not delay treatment.")
    return _unique(items)


def _supporting_items(result: Any) -> list[str]:
    mapping = {
        "kidney": _domain_line(result, "kidney") or "Optimize kidney-protective therapy.",
        "glycemia": _domain_line(result, "glycemia") or "Optimize diabetes care.",
        "ace_arb": _domain_line(result, "ace_arb"),
        "blood_pressure": _domain_line(result, "blood_pressure") or "Treat BP toward goal <130/80.",
        "sglt2": _domain_line(result, "sglt2"),
        "smoking": "Prioritize smoking cessation support.",
        "triglycerides": _domain_line(result, "triglycerides"),
        "tg_diet": _domain_line(result, "tg_diet"),
        "rdn_referral": _domain_line(result, "rdn_referral"),
        "tg_pharmacotherapy": _domain_line(result, "tg_pharmacotherapy"),
    }
    domains = _domains(result)
    items = [mapping[key] for key in mapping if key in domains]
    return _unique(items)


def build_action_scaffold(patient: Any, result: Any) -> list[ActionSection]:
    sections: list[ActionSection] = []
    domains = _domains(result)
    triglycerides = _triglycerides(patient)
    prioritize_uacr = bool(
        "uacr_testing" in domains and _level_3b_intermediate_prevent_path(result)
    )

    if triglycerides is not None and triglycerides >= 1000:
        sections.append(
            ActionSection(
                "Triglycerides",
                _domain_line(result, "triglycerides")
                or "Very severe hypertriglyceridemia: lower TG to reduce pancreatitis risk.",
                items=[
                    item
                    for item in [
                        _domain_line(result, "tg_diet"),
                        _domain_line(result, "rdn_referral"),
                        _domain_line(result, "tg_pharmacotherapy"),
                    ]
                    if item
                ],
            )
        )

    lipid_line = _lipid_line(patient, result)
    actionable_non_lipid_without_lipid_escalation = bool(
        "no escalation" in lipid_line.lower()
        and any(
            domain in domains
            for domain in {
                "kidney",
                "ace_arb",
                "sglt2",
                "blood_pressure",
                "glycemia",
                "triglycerides",
                "tg_pharmacotherapy",
            }
        )
    )
    if not actionable_non_lipid_without_lipid_escalation:
        sections.append(ActionSection("Lipid therapy", lipid_line))
    if "no escalation" in lipid_line.lower() and not actionable_non_lipid_without_lipid_escalation:
        sections.append(ActionSection("Lifestyle", "Continue lifestyle-based prevention."))
    if "inflammation" in domains:
        sections.append(ActionSection("Inflammation", _domain_line(result, "inflammation")))
    if "statin_intolerance" in domains:
        sections.append(
            ActionSection(
                "Statin intolerance",
                "Given prior high-intensity statin intolerance, consider maximally tolerated statin strategy and nonstatin intensification.",
            )
        )

    if "secondary_causes" in domains:
        sections.append(
            ActionSection(
                "Secondary causes",
                domains.get("secondary_causes")
                or "Evaluate secondary causes and consider FH/cascade screening when appropriate.",
            )
        )
    if "fh_evaluation" in domains:
        sections.append(
            ActionSection(
                "FH evaluation",
                "Consider FH evaluation/cascade screening when clinical suspicion is present.",
            )
        )

    monitoring = _lipid_monitoring_item(patient, result)
    if monitoring:
        sections.append(ActionSection("Monitoring", monitoring))

    if prioritize_uacr:
        sections.append(
            ActionSection(
                "Clarifiers",
                items=["Obtain UACR to complete kidney-risk assessment."],
            )
        )

    if prioritize_uacr:
        supporting = _supporting_items(result)
        if supporting:
            sections.append(ActionSection("Supporting actions", items=supporting))

    supporting = _supporting_items(result)
    kidney_supporting_before_cac = bool(
        ("kidney" in domains or actionable_non_lipid_without_lipid_escalation)
        and supporting
    )
    if kidney_supporting_before_cac:
        sections.append(ActionSection("Kidney / BP", items=supporting))
        supporting = []

    cac_line = _cac_line(patient, result)
    if cac_line:
        sections.append(ActionSection("Coronary calcium", cac_line))
    sections.append(ActionSection("Aspirin", _aspirin_line(patient, result)))

    supporting = [] if prioritize_uacr else supporting
    if triglycerides is not None and triglycerides >= 1000:
        supporting = [
            item
            for item in supporting
            if item
            not in {
                _domain_line(result, "triglycerides"),
                _domain_line(result, "tg_diet"),
                _domain_line(result, "rdn_referral"),
                _domain_line(result, "tg_pharmacotherapy"),
            }
        ]
    if supporting:
        sections.append(ActionSection("Supporting actions", items=supporting))

    clarifiers = (
        _clarifier_items_without(result, {"uacr_testing"})
        if prioritize_uacr
        else _clarifier_items(result)
    )
    if clarifiers:
        sections.append(ActionSection("Clarifiers", items=clarifiers))

    return sections


def build_action_recommendation_lines(patient: Any, result: Any) -> list[str]:
    """Flatten the ordered scaffold into natural visible recommendation lines."""
    lines: list[str] = []
    for section in build_action_scaffold(patient, result):
        if section.line:
            lines.append(section.line)
        lines.extend(section.items)
    return _unique(lines)


def _compact_lipid_item(line: str, monitoring: str | None = None) -> CompactActionItem | None:
    lowered = str(line or "").lower()
    if not lowered:
        return None
    detail = "Monitor lipids after therapy change." if monitoring else ""
    if "secondary-prevention" in lowered:
        subtitle = (
            "Treat toward very-high-risk ASCVD targets."
            if "very-high-risk ascvd targets" in lowered
            else "Treat toward ASCVD targets."
        )
        return CompactActionItem(
            "Intensify secondary-prevention lipid therapy",
            subtitle,
            detail,
            "lipids",
        )
    if "high-intensity" in lowered or "maximally tolerated statin" in lowered:
        subtitle = (
            "Use high-intensity or maximally tolerated statin."
            if "maximally tolerated statin" in lowered
            else "Treat toward high-risk targets."
        )
        return CompactActionItem("Intensify lipid-lowering", subtitle, detail, "lipids")
    if "moderate-intensity statin" in lowered:
        return CompactActionItem(
            "Start or discuss moderate-intensity statin",
            _compact_lipid_rationale(line),
            detail,
            "lipids",
        )
    if "moderate-intensity lipid" in lowered:
        return CompactActionItem(
            "Start or discuss moderate-intensity lipid therapy",
            _compact_lipid_rationale(line),
            detail,
            "lipids",
        )
    if "lipid-lowering therapy" in lowered or "statin therapy" in lowered:
        subtitle = "Treat toward high-risk targets." if "high-risk targets" in lowered else "Treat toward lipid targets."
        return CompactActionItem("Intensify lipid-lowering", subtitle, detail, "lipids")
    if "no escalation" in lowered:
        return CompactActionItem(
            "Continue lifestyle-focused prevention",
            "No lipid escalation based on current LDL-C/ApoB and ASCVD risk profile.",
            "",
            "lifestyle",
        )
    if lowered.startswith("continue lifestyle"):
        return CompactActionItem("Continue lifestyle-focused prevention", "", "", "lifestyle")
    return None


def _compact_lipid_rationale(line: str) -> str:
    text = str(line or "").strip().rstrip(".")
    lowered = text.lower()
    if "given " in lowered:
        rationale = text[lowered.index("given ") :]
        return rationale[:1].upper() + rationale[1:] + "."
    if "after shared decision-making" in lowered:
        return "Review start/intensity."
    if "primary prevention" in lowered:
        return "Primary prevention risk discussion."
    return "Review lipid targets."


def _compact_kidney_item(sections: list[ActionSection], patient: Any) -> CompactActionItem | None:
    kidney_text = " ".join(
        part
        for section in sections
        if section.label in {"Kidney / BP", "Supporting actions"}
        for part in ([section.line] if section.line else []) + list(section.items or [])
    )
    lowered = kidney_text.lower()
    if not lowered or not any(
        token in lowered
        for token in ("kidney", "uacr", "albuminuria", "acei", "ace inhibitor", "arb", "sglt2", "bp", "blood pressure")
    ):
        return None
    if "add an sglt2" in lowered:
        subtitle = "Add SGLT2 if no contraindication; optimize ACEi-ARB."
    elif bool(getattr(patient, "ace_arb", False)):
        subtitle = "Monitor UACR; continue/optimize ACEi-ARB."
    else:
        subtitle = "Monitor UACR; optimize ACEi-ARB."
    return CompactActionItem("Protect kidneys", subtitle, "", "kidney")


def _compact_glycemia_item(sections: list[ActionSection]) -> CompactActionItem | None:
    text = " ".join(
        part
        for section in sections
        if section.label in {"Kidney / BP", "Supporting actions"}
        for part in ([section.line] if section.line else []) + list(section.items or [])
    ).lower()
    if "glycemic" not in text and "a1c" not in text and "diabetes" not in text:
        return None
    return CompactActionItem("Optimize glycemia", "Individualize A1c goal.", "", "glycemia")


def _compact_cac_item(section: ActionSection | None) -> CompactActionItem | None:
    line = str(getattr(section, "line", "") or "").strip()
    lowered = line.lower()
    if not line:
        return None
    if "already measured" in lowered or "no repeat cac" in lowered or "cac 0 measured" in lowered:
        return None
    if "cac 0 is discordant" in lowered:
        return CompactActionItem("Do not de-risk from CAC 0", "Clinical ASCVD drives treatment decisions.", line, "cac")
    if "cac reasonable" in lowered or "cac may clarify" in lowered or "plaque burden unmeasured" in lowered:
        return CompactActionItem("Clarify plaque if needed", "CAC may help if treatment intensity remains uncertain.", "", "cac")
    if "plaque present" in lowered:
        return CompactActionItem("Account for measured plaque", line, "", "cac")
    return None


def _compact_aspirin_item(section: ActionSection | None) -> CompactActionItem | None:
    line = str(getattr(section, "line", "") or "").strip()
    lowered = line.lower()
    if not line or "not indicated for routine primary prevention" in lowered:
        return None
    if "antiplatelet therapy is indicated" in lowered:
        return CompactActionItem(
            "Antiplatelet therapy",
            "Use if clinically appropriate and no contraindication.",
            "",
            "aspirin",
        )
    if "bleeding risk" in lowered:
        return None
    return None


def _compact_detail_lines(sections: list[ActionSection]) -> list[str]:
    details: list[str] = []
    for section in sections:
        if section.label == "Monitoring":
            _append_detail(details, "Monitor lipids after therapy change.")
        elif section.label == "Clarifiers":
            for item in section.items:
                _append_detail(details, item)
    return details


def _append_detail(details: list[str], text: str) -> None:
    text = str(text or "").strip()
    if text and text not in details:
        details.append(text)


def build_compact_action_items(
    patient: Any,
    result: Any,
    *,
    max_items: int = 5,
) -> list[CompactActionItem]:
    """Build the default high-yield Action card stack without changing detailed recommendations."""
    sections = build_action_scaffold(patient, result)
    by_label = {section.label: section for section in sections}
    items: list[CompactActionItem] = []

    monitoring = str(getattr(by_label.get("Monitoring"), "line", "") or "").strip() or None
    lipid_section = by_label.get("Lipid therapy")
    lipid_item = _compact_lipid_item(str(getattr(lipid_section, "line", "") or ""), monitoring)
    if lipid_item:
        _append_compact(items, lipid_item.title, lipid_item.subtitle, lipid_item.detail, lipid_item.source)

    kidney_item = _compact_kidney_item(sections, patient)
    if kidney_item:
        _append_compact(items, kidney_item.title, kidney_item.subtitle, kidney_item.detail, kidney_item.source)

    glycemia_item = _compact_glycemia_item(sections)
    if glycemia_item:
        _append_compact(items, glycemia_item.title, glycemia_item.subtitle, glycemia_item.detail, glycemia_item.source)

    cac_item = _compact_cac_item(by_label.get("Coronary calcium"))
    if cac_item:
        _append_compact(items, cac_item.title, cac_item.subtitle, cac_item.detail, cac_item.source)

    aspirin_item = _compact_aspirin_item(by_label.get("Aspirin"))
    if aspirin_item:
        _append_compact(items, aspirin_item.title, aspirin_item.subtitle, aspirin_item.detail, aspirin_item.source)

    if not items:
        for section in sections:
            for text in ([section.line] if section.line else []) + list(section.items or []):
                fallback = _compact_lipid_item(text)
                if fallback:
                    _append_compact(items, fallback.title, fallback.subtitle, fallback.detail, fallback.source)
                    break
            if items:
                break

    return items[:max_items] or [
        CompactActionItem(
            "Continue clinician-guided prevention review",
            "",
            "",
            "fallback",
        )
    ]


def build_compact_action_detail_lines(patient: Any, result: Any) -> list[str]:
    """Return secondary details for an optional expanded UI area."""
    return _compact_detail_lines(build_action_scaffold(patient, result))


ACTION_PANEL_DOMAIN_ORDER = [
    "lipid_lowering",
    "plaque_cac",
    "kidney_protection",
    "blood_pressure",
    "glycemia_metabolic",
    "inflammation_context",
    "aspirin_antiplatelet",
    "data_to_clarify",
]


def _line_to_lipid_readout(line: str, patient: Any | None = None) -> tuple[str, str, str, str]:
    lowered = str(line or "").lower()
    if "secondary-prevention" in lowered:
        return "Secondary-prevention lipid therapy", "Treat toward ASCVD targets.", "high", "action"
    if "add-on" in lowered or "nonstatin" in lowered:
        return "Add-on therapy consideration", "If LDL-C/ApoB remain above target.", "high", "action"
    if "high-intensity" in lowered or "maximally tolerated" in lowered:
        return "High-intensity therapy indicated", "Treat toward high-risk targets.", "high", "action"
    if "review intensity" in lowered and "atherogenic burden remains elevated" in lowered:
        return "Review intensity; atherogenic burden remains elevated", "", "moderate", "consider"
    if "intensify" in lowered or "above target" in lowered:
        return "Intensify lipid-lowering", "Treat toward lipid targets.", "high", "action"
    if lowered.strip() == "discuss lipid-lowering therapy.":
        return "Discuss lipid-lowering therapy", "", "moderate", "consider"
    if "moderate-intensity" in lowered:
        if "reasonable" in lowered or "may be reasonable" in lowered or "discuss" in lowered:
            return "Discuss moderate-intensity statin", "Review start/intensity.", "moderate", "consider"
        return "Start moderate-intensity statin", "Primary-prevention lipid therapy.", "moderate", "action"
    if "low-intensity" in lowered:
        return "Low-intensity statin", "Use clinician-guided context.", "low", "consider"
    if "lifestyle" in lowered:
        return "Lifestyle-focused", "No routine lipid escalation.", "low", "neutral"
    if "no escalation" in lowered:
        if patient is not None:
            if _is_on_lipid_lowering(patient):
                return "Continue current lipid treatment", "", "none", "neutral"
            return "No lipid-lowering medication indicated", "", "none", "neutral"
        return "No lipid escalation", "Current LDL-C/ApoB and risk profile do not support medication change.", "none", "neutral"
    if "lipid-lowering therapy" in lowered or "statin therapy" in lowered:
        return "Intensify lipid-lowering", "Treat toward lipid targets.", "moderate", "action"
    return "Review lipid plan", "Use risk context and targets.", "low", "consider"


def _join_target_parts(parts: list[str]) -> str:
    if len(parts) <= 1:
        return "".join(parts)
    if len(parts) == 2:
        return " and ".join(parts)
    return ", ".join(parts[:-1]) + f", and {parts[-1]}"


def _lipid_emr_line(line: str, patient: Any | None = None, result: Any | None = None) -> str:
    text = _clean_readout_text(line)
    replacements = {
        "Intensify secondary-prevention lipid-lowering therapy; treat toward very-high-risk ASCVD targets.": (
            "Intensify secondary-prevention lipid-lowering therapy; treat toward very-high-risk ASCVD targets: "
            "LDL-C <55 mg/dL, non-HDL-C <85 mg/dL, and ApoB <65 mg/dL if available. LDL-C <70 mg/dL "
            "remains the minimum secondary-prevention threshold."
        ),
        "Secondary-prevention lipid-lowering therapy indicated; treat toward very-high-risk ASCVD targets.": (
            "Treat toward very-high-risk ASCVD targets: LDL-C <55 mg/dL, non-HDL-C <85 mg/dL, and ApoB <65 mg/dL "
            "if available. LDL-C <70 mg/dL remains the minimum secondary-prevention threshold."
        ),
    }
    if text in replacements:
        return replacements[text]
    if patient is not None and result is not None and any(
        phrase in text.lower()
        for phrase in (
            "lipid-lowering therapy recommended",
            "intensify lipid-lowering",
            "high-intensity lipid-lowering",
            "lipid-lowering therapy indicated",
        )
    ):
        target = _first_target(result)
        ldl_target = _num(getattr(target, "ldl_c_target", None)) if target else None
        apob_target = _num(getattr(target, "apob_target", None)) if target else None
        non_hdl_target = _num(getattr(target, "non_hdl_c_target", None)) if target else None
        has_apob = _num(getattr(patient, "apob", None)) is not None
        target_parts: list[str] = []
        if ldl_target is not None:
            target_parts.append(f"LDL-C <{ldl_target:g}")
        if has_apob and apob_target is not None:
            target_parts.append(f"ApoB <{apob_target:g}")
        if non_hdl_target is not None:
            target_parts.append(f"non-HDL-C <{non_hdl_target:g}")
        if target_parts:
            verb = (
                "High-intensity lipid-lowering therapy indicated"
                if "high-intensity" in text.lower()
                else "Intensify lipid-lowering therapy"
            )
            return f"{verb}; treat toward {_join_target_parts(target_parts)}."
    return text


def _is_on_lipid_lowering(patient: Any) -> bool:
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


def _lipid_patient_line(patient: Any, status: str, detail: str, source_line: str) -> str:
    lowered = f"{status} {detail} {source_line}".lower()
    on_lipid_lowering = _is_on_lipid_lowering(patient)
    if "secondary-prevention" in lowered or "very-high-risk ascvd" in lowered:
        if on_lipid_lowering:
            return "Discuss stronger cholesterol-lowering therapy toward secondary-prevention goals."
        return "Discuss starting cholesterol-lowering therapy toward secondary-prevention goals."
    if "high-intensity" in lowered or "intensify" in lowered:
        if on_lipid_lowering:
            return "Discuss stronger cholesterol-lowering therapy."
        return "Discuss starting high-intensity cholesterol-lowering therapy."
    if "discuss lipid-lowering therapy" in lowered:
        if on_lipid_lowering:
            return "Discuss stronger cholesterol-lowering therapy."
        return "Discuss starting cholesterol-lowering therapy."
    if "moderate-intensity" in lowered:
        if on_lipid_lowering:
            return "Discuss stronger cholesterol-lowering therapy."
        return "Discuss starting cholesterol-lowering therapy."
    if "no lipid escalation" in lowered or "no escalation" in lowered or "no lipid-lowering medication indicated" in lowered:
        if on_lipid_lowering:
            return "Continue current lipid treatment."
        return "No medication indicated."
    if "continue current lipid treatment" in lowered:
        return "Continue current lipid treatment."
    if "lifestyle" in lowered:
        return "Continue lifestyle-focused prevention."
    return "Review the cholesterol plan with your clinician."


def _patient_lipid_line(patient: Any, item: ActionDomainReadout, source_line: str) -> str:
    ldl = _num(getattr(patient, "ldl_c", None))
    # Kept intentionally simple for patient wording; action/EMR carry the exact target semantics.
    lowered = f"{item.status} {item.detail} {source_line}".lower()
    if "no lipid escalation" in lowered or "lifestyle-focused" in lowered or "lifestyle" in lowered:
        if _is_on_lipid_lowering(patient):
            return "Continue current lipid treatment."
        if "lifestyle" in lowered:
            return "Continue lifestyle-focused prevention."
        return "No medication indicated."
    if "no lipid-lowering medication indicated" in lowered:
        return "No medication indicated."
    if "continue current lipid treatment" in lowered:
        return "Continue current lipid treatment."
    return _lipid_patient_line(patient, item.status, item.detail, source_line)


def _patient_plaque_line(patient: Any, item: ActionDomainReadout) -> str:
    status = item.status.lower()
    if _clinical_ascvd(patient):
        return "Known cardiovascular disease is present."
    if "may clarify" in status:
        return "Calcium scan may clarify treatment."
    if "not routine" in status or "not needed" in status:
        return "Calcium scan not needed right now."
    cac = _num(getattr(patient, "cac", None))
    if cac is not None:
        if cac >= 300:
            return f"Very high burden (CAC {cac:g})."
        if cac >= 100:
            return f"High burden (CAC {cac:g})."
        if cac > 0:
            return f"Present (CAC {cac:g})."
        return "Not detected (CAC 0)."
    if "not measured" in status:
        return "Not measured."
    return "Not measured."


def _patient_kidney_state_line(egfr: float | None, uacr: float | None) -> str:
    if egfr is not None and egfr < 30:
        return "Advanced kidney disease."
    if egfr is not None and egfr < 60 and uacr is not None and uacr >= 30:
        return f"Chronic kidney disease is present (UACR {uacr:g})."
    if uacr is not None and uacr >= 300:
        return f"Significant albuminuria is present (UACR {uacr:g})."
    if uacr is not None and uacr >= 30:
        return f"Albuminuria present (UACR {uacr:g})."
    if egfr is not None and 45 <= egfr < 60:
        return "Mild reduction in kidney function."
    if egfr is not None or uacr is not None:
        return "Stable."
    return "UACR not available."


def _patient_kidney_line(patient: Any, item: ActionDomainReadout) -> str:
    egfr = _num(getattr(patient, "egfr", None))
    uacr = _num(getattr(patient, "uacr", None))
    status_detail = f"{item.status} {item.detail}".lower()
    if "uacr missing" in status_detail or "uacr not available" in status_detail or "obtain uacr" in status_detail or (egfr is not None and egfr < 60 and uacr is None):
        if egfr is not None:
            return f"Repeat kidney blood/urine testing; eGFR {egfr:g} and UACR not available."
        return "Repeat kidney urine testing; UACR not available."
    if item.state in {"action", "consider"}:
        return _patient_kidney_state_line(egfr, uacr)
    if "no kidney-risk signal" in status_detail or "no kidney action" in status_detail:
        return _patient_kidney_state_line(egfr, uacr)
    if "kidney context not available" in status_detail:
        return "UACR not available."
    return _patient_kidney_state_line(egfr, uacr)


def _patient_bp_line(patient: Any, item: ActionDomainReadout) -> str:
    if item.status.lower() == "at goal":
        return "At goal."
    if "bp needed" in item.status.lower():
        return "Reading needed."
    if "treat toward" in item.status.lower():
        return "Treat toward <130/80."
    return item.status.rstrip(".") + "."


def _patient_glycemia_line(patient: Any, item: ActionDomainReadout) -> str:
    a1c = _num(getattr(patient, "a1c", None))
    status = item.status.lower()
    if "no glycemic action" in status and a1c is not None and a1c < 5.7:
        return "Normal range."
    if "a1c needed" in status:
        return "A1c needed."
    if "prediabetes" in status:
        return "Prediabetes range; focus on weight/activity."
    if "optimize diabetes" in status:
        return "Work toward A1c <7.0."
    if "lifestyle" in status:
        return "Focus on weight/activity."
    return item.status.rstrip(".") + "."


def _patient_aspirin_line(item: ActionDomainReadout) -> str:
    status = item.status.lower()
    if "active" in status:
        return "Aspirin is active; confirm the reason."
    if "antiplatelet" in status:
        return "Review antiplatelet therapy."
    if "avoid" in status:
        return "Avoid routine aspirin."
    if "plaque burden is high" in status or "high plaque burden" in item.detail.lower():
        return "May be considered if bleeding risk is low."
    if "consider" in status:
        return "Discuss only if bleeding risk is low."
    return "Not indicated."


def _line_or_none(text: str) -> str:
    text = _clean_readout_text(text)
    return text if text else ""


def action_domain_clinician_text(item: ActionDomainReadout) -> str:
    """Return compact clinician text for a structured action domain."""
    return _readout_sentence(item)


def action_domain_patient_text(item: ActionDomainReadout) -> str:
    """Return patient-facing text for a structured action domain."""
    return _clean_readout_text(getattr(item, "patient_line", "") or _readout_sentence(item))


def render_action_domain_text(item: ActionDomainReadout, mode: RenderMode = RenderMode.CLINICIAN) -> str:
    """Render one action domain using the requested audience mode."""
    if mode == RenderMode.PATIENT:
        return action_domain_patient_text(item)
    return action_domain_clinician_text(item)


def _first_target(result: Any) -> Any:
    targets = getattr(result, "targets", None) or []
    return targets[0] if targets else None


def _fmt_mg(value: float | int | None) -> str:
    if value is None:
        return ""
    return f"{float(value):g}"


def _bp_detail(patient: Any) -> str:
    sbp = _num(getattr(patient, "sbp", None))
    dbp = _num(getattr(patient, "dbp", None))
    if sbp is None or dbp is None:
        return ""
    return f"Current {sbp:g}/{dbp:g}."


def _has_diabetes_context(patient: Any) -> bool:
    return bool(getattr(patient, "diabetes", False))


def _has_heart_failure_context(patient: Any) -> bool:
    return bool(getattr(patient, "heart_failure", False)) or bool(getattr(patient, "hf", False))


def _has_bp_above_goal(patient: Any) -> bool:
    sbp = _num(getattr(patient, "sbp", None))
    dbp = _num(getattr(patient, "dbp", None))
    return bool((sbp is not None and sbp >= 130) or (dbp is not None and dbp >= 80))


def _kidney_value(value: float | None) -> str:
    return f"{value:g}" if value is not None else "not available"


def _kidney_bp_phrase(patient: Any) -> str:
    return ""


def _sglt2_hover_detail(patient: Any) -> str:
    if _has_diabetes_context(patient):
        return (
            "SGLT2 benefit is strongest with diabetes plus CKD, heart failure, or UACR >=200 when eGFR >=20. "
            "Confirm contraindications and formulary coverage."
        )
    return (
        "SGLT2 criteria: stronger if UACR >=200, diabetes with CKD, or heart failure and eGFR >=20. "
        "For UACR 30-199 without diabetes/HF, confirm persistence and optimize BP/ACEi-ARB first."
    )


def _lipid_target_detail(patient: Any, result: Any, fallback: str) -> str:
    target = _first_target(result)
    ldl = _num(getattr(patient, "ldl_c", None))
    apob = _num(getattr(patient, "apob", None))
    triglycerides = _num(getattr(patient, "triglycerides", None))
    non_hdl = _num(getattr(patient, "non_hdl_c", None))
    ldl_target = _num(getattr(target, "ldl_c_target", None)) if target else None
    apob_target = _num(getattr(target, "apob_target", None)) if target else None
    non_hdl_target = _num(getattr(target, "non_hdl_c_target", None)) if target else None
    parts: list[str] = []
    if ldl is not None and ldl_target is not None:
        parts.append(f"LDL-C {ldl:g}; target <{ldl_target:g}.")
    elif ldl is not None:
        parts.append(f"LDL-C {ldl:g}.")
    elif triglycerides is not None and 400 <= triglycerides < 500:
        parts.append(f"LDL-C unavailable due to TG {triglycerides:g}.")
    if apob is not None and apob_target is not None:
        parts.append(f"ApoB {apob:g}; target <{apob_target:g}.")
    elif apob is not None:
        parts.append(f"ApoB {apob:g}.")
    if ldl is None and triglycerides is not None and triglycerides >= 400 and non_hdl is not None and non_hdl_target is not None:
        parts.append(f"non-HDL-C {non_hdl:g}; target <{non_hdl_target:g}.")
    elif any("ApoB" in item for item in _clarifier_items(result)):
        if ldl is not None:
            parts.append(f"Obtain ApoB for particle burden.")
        else:
            parts.append("Obtain ApoB for particle burden.")
    return " ".join(parts) or fallback


def _plaque_readout(patient: Any, result: Any, section: ActionSection | None) -> ActionDomainReadout:
    line = _clean_readout_text(getattr(section, "line", "") if section else "")
    cac = _num(getattr(patient, "cac", None))
    incidental = bool(getattr(patient, "incidental_cac", False))
    severity = _clean_readout_text(getattr(patient, "incidental_cac_severity", ""))
    if _prevention_context(patient, result) == PREVENTION_CONTEXT_SECONDARY_ASCVD:
        if cac is not None:
            return _make_readout(
                "plaque_cac",
                "Plaque",
                f"CAC {cac:g}",
                priority="low",
                state="complete",
                rule_id="action_panel_plaque_secondary_prevention",
                hover_detail="Clinical ASCVD drives management; CAC is plaque context only.",
            )
        return _make_readout(
            "plaque_cac",
            "Plaque",
            "Clinical ASCVD present",
            "CAC is not needed for lipid decisions.",
            priority="low",
            state="complete",
            rule_id="action_panel_plaque_secondary_prevention",
        )
    if cac is not None:
        if cac == 0:
            return _make_readout(
                "plaque_cac",
                "Plaque",
                "CAC 0",
                state="complete",
                hover_detail="No calcified plaque detected.",
            )
        if 1 <= cac <= 99:
            return _make_readout(
                "plaque_cac",
                "Plaque",
                f"Present (CAC {cac:g})",
                priority="moderate",
                state="consider",
                hover_detail="Plaque present; no repeat CAC needed.",
            )
        if cac >= 100:
            status = "Very high burden" if cac >= 300 else "High burden"
            burden = "High plaque burden" if cac >= 300 else "Moderate plaque burden"
            return _make_readout(
                "plaque_cac",
                "Plaque",
                f"{status} (CAC {cac:g})",
                priority="high",
                state="complete",
                hover_detail=f"{burden}; no repeat CAC needed.",
            )
    if incidental:
        label = "Incidental CAC on CT"
        detail = "Qualitative plaque evidence."
        if severity and severity not in {"unknown", "present"}:
            label = f"{severity.title()} incidental CAC"
        return _make_readout("plaque_cac", "Plaque", label, detail, priority="moderate", state="consider")
    if line:
        lowered = line.lower()
        if "not routinely recommended at this age" in lowered:
            return _make_readout("plaque_cac", "Plaque", "CAC not needed", priority="low", state="neutral", hover_detail="Consider only if results change management.")
        if "cac may clarify treatment" in lowered:
            return _make_readout(
                "plaque_cac",
                "Plaque",
                "CAC may clarify treatment",
                priority="low",
                state="consider",
                hover_detail="Use only if it would change lipid-treatment intensity.",
                expanded_detail_lines=["Use only if it would change lipid-treatment intensity."],
            )
        if "cac reasonable" in lowered or "cac may clarify" in lowered:
            return _make_readout(
                "plaque_cac",
                "Plaque",
                "CAC may clarify risk",
                priority="low",
                state="consider",
                hover_detail="Use only if it would change lipid-treatment intensity.",
                expanded_detail_lines=["Use only if it would change lipid-treatment intensity."],
            )
    return _make_readout("plaque_cac", "Plaque", "Not measured", state="neutral")


def _kidney_readout(sections: list[ActionSection], patient: Any, result: Any) -> ActionDomainReadout:
    domains = _domains(result)
    text = " ".join(
        part
        for section in sections
        if section.label in {"Kidney / BP", "Supporting actions", "Clarifiers"}
        for part in ([section.line] if section.line else []) + list(section.items or [])
    )
    lowered = text.lower()
    egfr = _num(getattr(patient, "egfr", None))
    uacr = _num(getattr(patient, "uacr", None))
    diabetes = _has_diabetes_context(patient)
    heart_failure = _has_heart_failure_context(patient)
    ace_arb = bool(getattr(patient, "ace_arb", False))
    sglt2_active = bool(getattr(patient, "sglt2", False))
    if ("uacr_testing" in domains and uacr is None) or ("obtain uacr" in lowered and uacr is None):
        return _make_readout(
            "kidney_protection",
            "Kidney protection",
            "Obtain UACR",
            "UACR not available.",
            priority="low",
            state="consider",
        )
    if sglt2_active and (egfr is not None or (uacr is not None and uacr >= 30)):
        active_phrase = "ACEi/ARB + SGLT2 active" if ace_arb else "SGLT2 active"
        if egfr is not None and egfr < 30:
            kidney_detail = f"eGFR {_kidney_value(egfr)}; UACR {_kidney_value(uacr)}; {active_phrase}."
        else:
            kidney_detail = f"UACR {_kidney_value(uacr)}; {active_phrase}."
        return _make_readout(
            "kidney_protection",
            "Kidney protection",
            "Continue kidney-protective therapy",
            kidney_detail,
            priority="high" if uacr is not None and uacr >= 300 else "moderate",
            state="action",
            hover_detail=(
                "Further SGLT2 decisions should be individualized with nephrology."
                if egfr is not None and egfr < 20
                else _sglt2_hover_detail(patient)
            ),
        )
    if egfr is not None and egfr < 20 and (uacr is not None and uacr >= 30):
        return _make_readout(
            "kidney_protection",
            "Kidney protection",
            "Do not newly start SGLT2 routinely",
            "Individualize with nephrology guidance.",
            priority="moderate",
            state="consider",
            hover_detail="eGFR <20 is below routine new-start thresholds; individualize kidney-protective therapy with nephrology guidance.",
        )
    if heart_failure and (egfr is None or egfr >= 20):
        return _make_readout(
            "kidney_protection",
            "Kidney protection",
            "Use SGLT2 if no contraindication",
            f"Heart failure benefit; eGFR {_kidney_value(egfr)}.",
            priority="high",
            state="action",
            hover_detail="SGLT2 inhibitors have heart-failure benefit when eGFR is adequate; confirm contraindications and current therapy.",
        )
    if uacr is not None and uacr >= 200 and (egfr is None or egfr >= 20):
        return _make_readout(
            "kidney_protection",
            "Kidney protection",
            "Add SGLT2 if no contraindication",
            f"UACR {uacr:g}; eGFR {_kidney_value(egfr)}.",
            priority="high",
            state="action",
            hover_detail="Meets strong kidney-protection criteria: UACR >=200 mg/g and eGFR >=20.",
        )
    if uacr is not None and 30 <= uacr < 200 and diabetes:
        ace_phrase = "ACEi/ARB active" if ace_arb else "optimize ACEi-ARB"
        detail = f"UACR {uacr:g}; {ace_phrase}. Consider SGLT2 for diabetic CKD."
        detail += _kidney_bp_phrase(patient)
        return _make_readout(
            "kidney_protection",
            "Kidney protection",
            "Optimize kidney protection",
            detail,
            priority="moderate",
            state="consider",
            hover_detail=_sglt2_hover_detail(patient),
        )
    if "sglt2" in lowered and egfr is not None and egfr >= 20 and (heart_failure or diabetes or (uacr is not None and uacr >= 200)):
        detail = f"UACR {_kidney_value(uacr)}; eGFR {egfr:g}."
        return _make_readout(
            "kidney_protection",
            "Kidney protection",
            "Review SGLT2 kidney indication",
            detail,
            priority="moderate",
            state="consider",
            hover_detail=_sglt2_hover_detail(patient),
        )
    if "albuminuria" in lowered or (uacr is not None and uacr >= 30):
        detail = f"UACR {_kidney_value(uacr)}; "
        detail += "ACEi/ARB active." if ace_arb else "optimize ACEi-ARB."
        detail += _kidney_bp_phrase(patient)
        status = "Monitor albuminuria" if ace_arb else "Repeat UACR to confirm persistence"
        return _make_readout("kidney_protection", "Kidney protection", status, detail, priority="moderate", state="action")
    if egfr is not None and egfr < 60 and uacr is None:
        return _make_readout(
            "kidney_protection",
            "Kidney protection",
            "Complete kidney testing",
            f"eGFR {egfr:g}; UACR not available.",
            priority="low",
            state="consider",
        )
    if egfr is not None or uacr is not None:
        return _make_readout("kidney_protection", "Kidney protection", "No kidney action", state="complete")
    return _make_readout("kidney_protection", "Kidney protection", "Kidney context not available", priority="low", state="neutral")


def _blood_pressure_readout(patient: Any, result: Any) -> ActionDomainReadout:
    line = _domain_line(result, "blood_pressure")
    sbp = _num(getattr(patient, "sbp", None))
    dbp = _num(getattr(patient, "dbp", None))
    hover = "BP goals should be individualized based on frailty, orthostasis, kidney function, and treatment burden."
    if line:
        lowered = line.lower()
        if "treat bp" in lowered or "optimize bp" in lowered:
            return _make_readout("blood_pressure", "Blood pressure", "Treat toward <130/80", _bp_detail(patient), priority="moderate", state="action", hover_detail=hover)
    if sbp is None or dbp is None:
        return _make_readout("blood_pressure", "Blood pressure", "BP needed", "No current BP available.", state="neutral")
    if sbp >= 130 or dbp >= 80:
        return _make_readout("blood_pressure", "Blood pressure", "Treat toward <130/80", f"Current {sbp:g}/{dbp:g}.", priority="low", state="consider", hover_detail=hover)
    return _make_readout("blood_pressure", "Blood pressure", "At goal", f"Current {sbp:g}/{dbp:g}; goal <130/80.", state="complete", hover_detail=hover)


def _glycemia_readout(patient: Any, result: Any) -> ActionDomainReadout:
    line = _domain_line(result, "glycemia")
    a1c = _num(getattr(patient, "a1c", None))
    diabetes = bool(getattr(patient, "diabetes", False))
    bmi = _num(getattr(patient, "bmi", None))
    if line or diabetes:
        detail = f"A1c {a1c:g}%; goal <7.0." if a1c is not None else "Individualized A1c goal."
        return _make_readout("glycemia_metabolic", "Glycemia / metabolic", "Optimize diabetes care", detail, priority="moderate", state="action")
    if a1c is not None and 5.7 <= a1c < 6.5:
        return _make_readout("glycemia_metabolic", "Glycemia / metabolic", "Prediabetes prevention", f"A1c {a1c:g}%; weight/activity focus.", priority="low", state="consider")
    if bmi is not None and bmi >= 30:
        return _make_readout("glycemia_metabolic", "Glycemia / metabolic", "Lifestyle / weight-focused prevention", "Address metabolic risk.", priority="low", state="consider")
    if a1c is not None:
        return _make_readout("glycemia_metabolic", "Glycemia / metabolic", "No glycemic action", f"A1c {a1c:g}.", state="neutral")
    return _make_readout("glycemia_metabolic", "Glycemia / metabolic", "A1c needed", "No current A1c available.", state="neutral")


def _aspirin_readout(patient: Any, result: Any, section: ActionSection | None) -> ActionDomainReadout:
    line = _clean_readout_text(getattr(section, "line", "") if section else _aspirin_line(patient, result))
    lowered = line.lower()
    aspirin_active = _aspirin_active(patient)
    if "antiplatelet therapy is indicated" in lowered:
        return _make_readout("aspirin_antiplatelet", "Aspirin / antiplatelet", "Antiplatelet therapy", "Use if no contraindication.", priority="high", state="action")
    if aspirin_active and _prevention_context(patient, result) != PREVENTION_CONTEXT_SECONDARY_ASCVD:
        return _make_readout(
            "aspirin_antiplatelet",
            "Aspirin / antiplatelet",
            "Aspirin active; confirm indication",
            "Primary-prevention benefit uncertain.",
            priority="low",
            state="consider",
            hover_detail="Consider only if bleeding risk is low and prevention context supports it.",
        )
    cac = _num(getattr(patient, "cac", None))
    if "avoid routine" in lowered:
        return _make_readout("aspirin_antiplatelet", "Aspirin / antiplatelet", "Avoid routine primary-prevention aspirin", "", priority="low", state="neutral")
    if "plaque burden is high" in lowered:
        return _make_readout(
            "aspirin_antiplatelet",
            "Aspirin / antiplatelet",
            "Consider if bleeding risk is low",
            "High plaque burden.",
            priority="low",
            state="consider",
            hover_detail="Primary-prevention aspirin is selective. Consider only if bleeding risk is low.",
        )
    if "bleeding risk" in lowered or "consider" in lowered:
        detail = f"CAC {cac:g}." if cac is not None else "Review bleeding risk."
        return _make_readout(
            "aspirin_antiplatelet",
            "Aspirin / antiplatelet",
            "Consider only if bleeding risk is low",
            detail,
            priority="low",
            state="consider",
            hover_detail="Primary-prevention aspirin is selective. Consider only if bleeding risk is low.",
        )
    if line == "Aspirin not routine for primary prevention.":
        return _make_readout(
            "aspirin_antiplatelet",
            "Aspirin / antiplatelet",
            "Not indicated",
            state="neutral",
        )
    return _make_readout("aspirin_antiplatelet", "Aspirin / antiplatelet", "Not indicated", state="neutral")


def _clarifier_readout(result: Any, patient: Any | None = None) -> ActionDomainReadout | None:
    clarifiers = _clarifier_items(result)
    if patient is not None:
        available_fragments = []
        if _num(getattr(patient, "apob", None)) is not None:
            available_fragments.append("ApoB")
        if _num(getattr(patient, "lp_a_value", None)) is not None:
            available_fragments.append("Lp(a)")
        if _num(getattr(patient, "uacr", None)) is not None:
            available_fragments.append("UACR")
        if _num(getattr(patient, "hscrp", None)) is not None:
            available_fragments.append("hsCRP")
        if _num(getattr(patient, "cac", None)) is not None:
            available_fragments.append("CAC")
        if available_fragments:
            clarifiers = [
                item
                for item in clarifiers
                if not any(fragment.lower() in item.lower() for fragment in available_fragments)
            ]
    if not clarifiers:
        return None
    labels = []
    for item in clarifiers:
        label = item.split(" - ", 1)[0].replace("Obtain ", "").replace(" to complete kidney-risk assessment.", "")
        if label.startswith("Consider hsCRP"):
            label = "hsCRP"
        if label.startswith("Obtain hsCRP"):
            label = "hsCRP"
        labels.append(label)
    return _make_readout(
        "data_to_clarify",
        "Additional information",
        "Additional information",
        ", ".join(_unique(labels[:4])) + ".",
        priority="low",
        state="consider",
        detail_lines=clarifiers,
    )


def _readout_sentence(item: ActionDomainReadout) -> str:
    status = _clean_readout_text(item.status)
    detail = _clean_readout_text(item.detail)
    if detail:
        return f"{item.label}: {status}. {detail}"
    return f"{item.label}: {status}."


def _attach_surface_lines(
    patient: Any,
    result: Any,
    panel: list[ActionDomainReadout],
    sections: list[ActionSection],
    lipid_line: str,
) -> list[ActionDomainReadout]:
    by_label = {section.label: section for section in sections}
    section_text = {
        section.label: _unique(([section.line] if section.line else []) + list(section.items or []))
        for section in sections
    }
    order = {domain_id: index for index, domain_id in enumerate(ACTION_PANEL_DOMAIN_ORDER)}

    for item in panel:
        item.display_priority = order.get(item.domain_id, 99)
        item.recommendation_strength = item.priority
        item.action_card_line = _readout_sentence(item)

        if item.domain_id == "lipid_lowering":
            lipid_parts = []
            lipid_parts.extend(section_text.get("Triglycerides") or [])
            lipid_parts.append(_lipid_emr_line(lipid_line, patient, result))
            lipid_parts.extend(section_text.get("Lifestyle") or [])
            lipid_parts.extend(section_text.get("Statin intolerance") or [])
            lipid_parts.extend(section_text.get("Secondary causes") or [])
            lipid_parts.extend(section_text.get("FH evaluation") or [])
            lipid_parts = _unique(lipid_parts)
            item.emr_line = "; ".join(lipid_parts)
            item.emr_lines = lipid_parts
            item.patient_line = _patient_lipid_line(patient, item, lipid_line)
        elif item.domain_id == "plaque_cac":
            line = _line_or_none(getattr(by_label.get("Coronary calcium"), "line", ""))
            cac = _num(getattr(patient, "cac", None))
            if cac is not None and not _clinical_ascvd(patient):
                item.emr_line = f"CAC {cac:g}."
            else:
                if line and "already measured" in line.lower():
                    line = line.replace(" already measured", "")
                item.emr_line = line or _readout_sentence(item)
            item.patient_line = _patient_plaque_line(patient, item)
        elif item.domain_id == "kidney_protection":
            source = section_text.get("Kidney / BP") or section_text.get("Supporting actions") or section_text.get("Clarifiers")
            item.emr_line = "; ".join(source) if source else _readout_sentence(item)
            item.emr_lines = source if source else [item.emr_line]
            item.patient_line = _patient_kidney_line(patient, item)
        elif item.domain_id == "blood_pressure":
            item.emr_line = _domain_line(result, "blood_pressure") or _readout_sentence(item)
            item.patient_line = _patient_bp_line(patient, item)
        elif item.domain_id == "glycemia_metabolic":
            item.emr_line = _domain_line(result, "glycemia") or _readout_sentence(item)
            item.patient_line = _patient_glycemia_line(patient, item)
        elif item.domain_id == "inflammation_context":
            item.emr_line = _domain_line(result, "inflammation") or _readout_sentence(item)
            item.patient_line = "Chronic inflammation can shape the prevention plan with your clinician."
        elif item.domain_id == "aspirin_antiplatelet":
            item.emr_line = _aspirin_line(patient, result)
            if item.state == "consider" and item.emr_line == "Aspirin not routine for primary prevention.":
                item.hover_detail = "Consider only if bleeding risk is low and prevention context supports it."
            item.patient_line = _patient_aspirin_line(item)
        elif item.domain_id == "data_to_clarify":
            if item.detail_lines:
                item.emr_line = "; ".join(item.detail_lines)
                item.emr_lines = list(item.detail_lines)
                item.patient_line = "Additional information: " + item.detail.replace(".", "") + "."
            else:
                item.emr_line = ""
                item.emr_lines = []
                item.patient_line = ""

    return panel


def _inflammation_readout(result: Any) -> ActionDomainReadout | None:
    line = _domain_line(result, "inflammation")
    if not line:
        return None
    return _make_readout(
        "inflammation_context",
        "Inflammation",
        "Inflammatory risk enhancer",
        line,
        priority="low",
        state="consider",
        rule_id="action_panel_inflammation_context",
        emr_line=line,
        patient_line="Chronic inflammation can shape the prevention plan with your clinician.",
    )


def build_action_instrument_panel(patient: Any, result: Any) -> list[ActionDomainReadout]:
    """Return fixed-domain action readouts for the default clinical instrument panel."""
    sections = build_action_scaffold(patient, result)
    by_label = {section.label: section for section in sections}
    triglycerides = _triglycerides(patient)
    lipid_line = _clean_readout_text(getattr(by_label.get("Lipid therapy"), "line", "") or _lipid_line(patient, result))
    lipid_status, lipid_detail, lipid_priority, lipid_state = _line_to_lipid_readout(lipid_line, patient)
    if "moderate-intensity" in lipid_line.lower():
        lipid_detail = _compact_lipid_rationale(lipid_line)
    if triglycerides is not None and triglycerides >= 1000:
        lipid_status, lipid_detail, lipid_priority, lipid_state = (
            "Lower triglycerides urgently",
            "Reduce pancreatitis risk.",
            "high",
            "action",
        )
    lipid_detail = _lipid_target_detail(patient, result, lipid_detail)
    monitoring = _clean_readout_text(getattr(by_label.get("Monitoring"), "line", ""))
    lipid = _make_readout(
        "lipid_lowering",
        "Lipid lowering",
        lipid_status,
        lipid_detail,
        priority=lipid_priority,
        state=lipid_state,
        rule_id="action_panel_lipid_lowering",
        detail_lines=[monitoring] if monitoring else [],
    )
    panel = [
        lipid,
        _plaque_readout(patient, result, by_label.get("Coronary calcium")),
        _kidney_readout(sections, patient, result),
        _blood_pressure_readout(patient, result),
        _glycemia_readout(patient, result),
    ]
    inflammation = _inflammation_readout(result)
    if inflammation:
        panel.append(inflammation)
    panel.append(_aspirin_readout(patient, result, by_label.get("Aspirin")))
    clarifier = _clarifier_readout(result, patient)
    if clarifier:
        panel.append(clarifier)
    order = {domain_id: index for index, domain_id in enumerate(ACTION_PANEL_DOMAIN_ORDER)}
    panel = _attach_surface_lines(patient, result, panel, sections, lipid_line)
    return sorted(panel, key=lambda item: order[item.domain_id])


def build_domain_actions(patient: Any, result: Any) -> list[ActionDomain]:
    """Return engine-owned structured action domains shared by all output surfaces."""
    return build_action_instrument_panel(patient, result)


def render_domain_actions_for_surface(
    domain_actions: list[ActionDomain],
    surface: str = "emr",
) -> list[str]:
    """Format shared domain actions for one surface without changing clinical meaning."""
    surface = str(surface or "emr").strip().lower()
    attr = {
        "action_card": "action_card_line",
        "patient": "patient_line",
        "emr": "emr_line",
    }.get(surface, "emr_line")

    lines: list[str] = []
    for item in domain_actions:
        if surface == "emr" and getattr(item, "emr_lines", None):
            lines.extend(_clean_readout_text(line) for line in getattr(item, "emr_lines", []) if _clean_readout_text(line))
        else:
            line = _clean_readout_text(getattr(item, attr, ""))
            if line:
                lines.append(line)
    return _unique(lines)


def get_domain_recommendation_lines(patient: Any, result: Any, surface: str = "emr") -> list[str]:
    """Return surface-specific recommendation lines from the shared action domains."""
    return render_domain_actions_for_surface(build_domain_actions(patient, result), surface=surface)
