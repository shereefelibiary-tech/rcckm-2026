from dataclasses import dataclass, field
from typing import Any

from modules.cac_recommendation.engine import build_cac_age_gate_note
from modules.prevention_context.engine import (
    PREVENTION_CONTEXT_SECONDARY_ASCVD,
    classify_prevention_context,
)
from modules.risk_enhancers.reproductive import has_reproductive_risk_markers


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
        if not recommendation or recommendation == "Treatment is reasonable.":
            continue
        low = recommendation.lower()
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
) -> ActionDomainReadout:
    return ActionDomainReadout(
        domain_id=domain_id,
        label=label,
        status=_clean_readout_text(status) or "No active signal",
        detail=_clean_readout_text(detail),
        priority=priority,
        state=state,
        rule_id=rule_id,
        trace_inputs=trace_inputs or {},
        detail_lines=[_clean_readout_text(line) for line in (detail_lines or []) if _clean_readout_text(line)],
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
    return category == "HIGH" or (risk is not None and risk >= 10)


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
        "Treatment is reasonable",
    )
    if dominant and not dominant.startswith(non_lipid_starts):
        return dominant

    ldl = _num(getattr(patient, "ldl_c", None))
    if (ldl is not None and ldl >= 190) or bool(getattr(patient, "suspected_fh_hefh", False)):
        return "High-intensity or maximally tolerated statin therapy indicated."
    if _low_with_lpa_reproductive_context(patient, result):
        return "No medication escalation required today; clinician-patient risk discussion recommended given high Lp(a) and reproductive risk markers."
    if _low_with_lpa_family_context(patient, result):
        return "No medication escalation required today; clinician-patient risk discussion recommended given elevated Lp(a) and premature family history."
    if _prevent_high(result):
        return "Lipid-lowering therapy is indicated; treat toward high-risk targets."
    return "No medication escalation today."


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
    if age is not None and age >= 70:
        return "Aspirin not indicated for routine primary prevention."
    if cac is None:
        return "Aspirin not indicated for routine primary prevention."
    if age is not None and 40 <= age <= 69 and 100 <= cac <= 299:
        return "Aspirin not routine for primary prevention; consider only if bleeding risk is low and shared decision-making supports it."
    if age is not None and 40 <= age <= 69 and (cac >= 100 or _prevent_high(result)):
        return "Aspirin may be considered only if bleeding risk is low after shared decision-making."
    return "Aspirin not indicated for routine primary prevention."


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
        "glycemia": "Optimize glycemic therapy.",
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
        lipid_line.startswith("No medication escalation")
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
    if lipid_line.startswith("No medication escalation") and not actionable_non_lipid_without_lipid_escalation:
        sections.append(ActionSection("Lifestyle", "Continue lifestyle-based prevention."))
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
    if lowered.startswith("no medication escalation") or lowered.startswith("no escalation"):
        return CompactActionItem(
            "Continue lifestyle-focused prevention",
            "No medication escalation today.",
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
        return "Use shared decision-making."
    if "primary prevention" in lowered:
        return "Primary prevention risk discussion."
    return "Use shared decision-making and lipid targets."


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
        subtitle = "Add SGLT2 if no contraindication; optimize BP/ACEi-ARB."
    elif bool(getattr(patient, "ace_arb", False)):
        subtitle = "Confirm UACR; continue/optimize ACEi-ARB; consider SGLT2 if criteria met."
    else:
        subtitle = "Confirm UACR; optimize BP/ACEi-ARB; consider SGLT2 if criteria met."
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
        return CompactActionItem(
            "Aspirin: only if low bleeding risk",
            "Shared decision-making.",
            "",
            "aspirin",
        )
    return None


def _compact_detail_lines(sections: list[ActionSection]) -> list[str]:
    details: list[str] = []
    for section in sections:
        if section.label == "Monitoring":
            _append_detail(details, "Monitor lipids after therapy change.")
        elif section.label == "Coronary calcium":
            line = str(section.line or "").strip()
            if "already measured" in line.lower() or "no repeat cac" in line.lower():
                _append_detail(details, line)
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
    "aspirin_antiplatelet",
    "data_to_clarify",
]


def _line_to_lipid_readout(line: str) -> tuple[str, str, str, str]:
    lowered = str(line or "").lower()
    if "secondary-prevention" in lowered:
        return "Secondary-prevention lipid therapy", "Treat toward ASCVD targets.", "high", "action"
    if "add-on" in lowered or "nonstatin" in lowered:
        return "Add-on therapy consideration", "If LDL-C/ApoB remain above target.", "high", "action"
    if "high-intensity" in lowered or "maximally tolerated" in lowered:
        return "High-intensity therapy indicated", "Treat toward high-risk targets.", "high", "action"
    if "intensify" in lowered or "above target" in lowered:
        return "Intensify lipid-lowering", "Treat toward lipid targets.", "high", "action"
    if "moderate-intensity" in lowered:
        if "reasonable" in lowered or "may be reasonable" in lowered or "discuss" in lowered:
            return "Discuss moderate-intensity statin", "Use shared decision-making.", "moderate", "consider"
        return "Start moderate-intensity statin", "Primary-prevention lipid therapy.", "moderate", "action"
    if "low-intensity" in lowered:
        return "Low-intensity statin", "Use clinician-guided context.", "low", "consider"
    if "lifestyle" in lowered:
        return "Lifestyle-focused", "No routine medication escalation.", "low", "neutral"
    if "no medication escalation" in lowered or "no escalation" in lowered:
        return "No medication escalation", "Continue lifestyle-focused prevention.", "none", "neutral"
    if "lipid-lowering therapy" in lowered or "statin therapy" in lowered:
        return "Intensify lipid-lowering", "Treat toward lipid targets.", "moderate", "action"
    return "Review lipid plan", "Use risk context and targets.", "low", "consider"


def _plaque_readout(patient: Any, result: Any, section: ActionSection | None) -> ActionDomainReadout:
    line = _clean_readout_text(getattr(section, "line", "") if section else "")
    cac = _num(getattr(patient, "cac", None))
    incidental = bool(getattr(patient, "incidental_cac", False))
    severity = _clean_readout_text(getattr(patient, "incidental_cac_severity", ""))
    if _prevention_context(patient, result) == PREVENTION_CONTEXT_SECONDARY_ASCVD:
        if cac is not None:
            return _make_readout(
                "plaque_cac",
                "CAC / plaque",
                f"CAC {cac:g} is context only",
                "Clinical ASCVD drives management.",
                priority="low",
                state="complete",
                rule_id="action_panel_plaque_secondary_prevention",
            )
        return _make_readout(
            "plaque_cac",
            "CAC / plaque",
            "Clinical ASCVD present",
            "CAC is not needed for lipid decisions.",
            priority="low",
            state="complete",
            rule_id="action_panel_plaque_secondary_prevention",
        )
    if cac is not None:
        if cac == 0:
            return _make_readout("plaque_cac", "CAC / plaque", "CAC 0: no calcified plaque", "Use overall risk context.", state="complete")
        if 1 <= cac <= 99:
            return _make_readout("plaque_cac", "CAC / plaque", f"CAC {cac:g}: plaque present", "Plaque supports prevention review.", priority="moderate", state="consider")
        if cac >= 100:
            return _make_readout("plaque_cac", "CAC / plaque", f"CAC {cac:g} already measured", "No repeat CAC needed.", priority="high", state="complete")
    if incidental:
        label = "Incidental CAC on CT"
        detail = "Qualitative plaque evidence."
        if severity and severity not in {"unknown", "present"}:
            label = f"{severity.title()} incidental CAC"
        return _make_readout("plaque_cac", "CAC / plaque", label, detail, priority="moderate", state="consider")
    if line:
        lowered = line.lower()
        if "not routinely recommended at this age" in lowered:
            return _make_readout("plaque_cac", "CAC / plaque", "CAC not routinely recommended", "Consider only if results change management.", priority="low", state="neutral")
        if "cac reasonable" in lowered or "cac may clarify" in lowered:
            return _make_readout("plaque_cac", "CAC / plaque", "CAC may clarify risk", "If treatment intensity remains uncertain.", priority="low", state="consider")
    return _make_readout("plaque_cac", "CAC / plaque", "Not measured", "Plaque burden unmeasured.", state="neutral")


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
    if "add an sglt2" in lowered:
        return _make_readout("kidney_protection", "Kidney protection", "Add SGLT2 if eligible", "Optimize BP/ACEi-ARB.", priority="high", state="action")
    if "sglt2" in lowered:
        return _make_readout("kidney_protection", "Kidney protection", "Consider SGLT2 if criteria met", "Confirm albuminuria and optimize BP/ACEi-ARB.", priority="moderate", state="consider")
    if "albuminuria" in lowered or (uacr is not None and uacr >= 30):
        detail = "Continue/optimize ACEi-ARB and BP." if bool(getattr(patient, "ace_arb", False)) else "ACEi/ARB and BP per criteria."
        return _make_readout("kidney_protection", "Kidney protection", "Confirm albuminuria", detail, priority="moderate", state="action")
    if "uacr_testing" in domains:
        return _make_readout("kidney_protection", "Kidney protection", "UACR needed", "Complete kidney-risk assessment.", priority="low", state="consider")
    if egfr is not None or uacr is not None:
        return _make_readout("kidney_protection", "Kidney protection", "No kidney-risk signal", "Current kidney markers reviewed.", state="complete")
    return _make_readout("kidney_protection", "Kidney protection", "Kidney context not available", "UACR/eGFR can clarify risk.", priority="low", state="neutral")


def _blood_pressure_readout(patient: Any, result: Any) -> ActionDomainReadout:
    line = _domain_line(result, "blood_pressure")
    sbp = _num(getattr(patient, "sbp", None))
    dbp = _num(getattr(patient, "dbp", None))
    if line:
        lowered = line.lower()
        if "treat bp" in lowered or "optimize bp" in lowered:
            return _make_readout("blood_pressure", "Blood pressure", "Treat toward <130/80", "If tolerated.", priority="moderate", state="action")
    if sbp is None or dbp is None:
        return _make_readout("blood_pressure", "Blood pressure", "BP context not available", "Enter clinic or home BP.", state="neutral")
    if sbp >= 130 or dbp >= 80:
        return _make_readout("blood_pressure", "Blood pressure", "Review BP / confirm goal", f"Current {sbp:g}/{dbp:g}.", priority="low", state="consider")
    return _make_readout("blood_pressure", "Blood pressure", "At goal", f"Current {sbp:g}/{dbp:g}.", state="complete")


def _glycemia_readout(patient: Any, result: Any) -> ActionDomainReadout:
    line = _domain_line(result, "glycemia")
    a1c = _num(getattr(patient, "a1c", None))
    diabetes = bool(getattr(patient, "diabetes", False))
    bmi = _num(getattr(patient, "bmi", None))
    if line or diabetes:
        return _make_readout("glycemia_metabolic", "Glycemia / metabolic", "Optimize diabetes care", "Individualize A1c goal.", priority="moderate", state="action")
    if a1c is not None and 5.7 <= a1c < 6.5:
        return _make_readout("glycemia_metabolic", "Glycemia / metabolic", "Prediabetes prevention", "Weight and insulin-resistance focus.", priority="low", state="consider")
    if bmi is not None and bmi >= 30:
        return _make_readout("glycemia_metabolic", "Glycemia / metabolic", "Lifestyle / weight-focused prevention", "Address metabolic risk.", priority="low", state="consider")
    return _make_readout("glycemia_metabolic", "Glycemia / metabolic", "No immediate action", "No active glycemic signal.", state="neutral")


def _aspirin_readout(patient: Any, result: Any, section: ActionSection | None) -> ActionDomainReadout:
    line = _clean_readout_text(getattr(section, "line", "") if section else _aspirin_line(patient, result))
    lowered = line.lower()
    if "antiplatelet therapy is indicated" in lowered:
        return _make_readout("aspirin_antiplatelet", "Aspirin / antiplatelet", "Secondary-prevention antiplatelet", "If appropriate and no contraindication.", priority="high", state="action")
    if "bleeding risk" in lowered or "consider" in lowered:
        return _make_readout("aspirin_antiplatelet", "Aspirin / antiplatelet", "Consider only if low bleeding risk", "Shared decision-making.", priority="low", state="consider")
    return _make_readout("aspirin_antiplatelet", "Aspirin / antiplatelet", "Not routine for primary prevention", "Do not start routine aspirin.", state="neutral")


def _clarifier_readout(result: Any) -> ActionDomainReadout:
    clarifiers = _clarifier_items(result)
    if not clarifiers:
        return _make_readout("data_to_clarify", "Data to clarify", "Key data available", "No urgent clarifiers.", state="complete")
    labels = []
    for item in clarifiers:
        label = item.split(" - ", 1)[0].replace("Obtain ", "").replace(" to complete kidney-risk assessment.", "")
        if label.startswith("Consider hsCRP"):
            label = "hsCRP"
        labels.append(label)
    return _make_readout(
        "data_to_clarify",
        "Data to clarify",
        ", ".join(_unique(labels[:4])),
        "Clarification should not delay indicated therapy.",
        priority="low",
        state="consider",
        detail_lines=clarifiers,
    )


def build_action_instrument_panel(patient: Any, result: Any) -> list[ActionDomainReadout]:
    """Return fixed-domain action readouts for the default clinical instrument panel."""
    sections = build_action_scaffold(patient, result)
    by_label = {section.label: section for section in sections}
    lipid_line = _clean_readout_text(getattr(by_label.get("Lipid therapy"), "line", "") or _lipid_line(patient, result))
    lipid_status, lipid_detail, lipid_priority, lipid_state = _line_to_lipid_readout(lipid_line)
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
        _aspirin_readout(patient, result, by_label.get("Aspirin")),
        _clarifier_readout(result),
    ]
    order = {domain_id: index for index, domain_id in enumerate(ACTION_PANEL_DOMAIN_ORDER)}
    return sorted(panel, key=lambda item: order[item.domain_id])
