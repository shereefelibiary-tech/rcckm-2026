from dataclasses import dataclass, field
from typing import Any

from modules.cac_recommendation.engine import build_cac_age_gate_note


@dataclass
class ActionSection:
    label: str
    line: str = ""
    items: list[str] = field(default_factory=list)


TESTING_LABELS = {
    "apob_testing": "ApoB - particle burden clarification",
    "lpa_testing": "Lp(a) - one-time risk assessment",
    "uacr_testing": "UACR - kidney risk clarification",
    "cac_testing": "CAC - plaque burden clarification",
    "hscrp_testing": "hsCRP - inflammatory residual risk",
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
        if "lipid-lowering" in low and "lipids" not in domains:
            domains["lipids"] = recommendation
        elif low.startswith("optimize kidney") and "kidney" not in domains:
            domains["kidney"] = recommendation
        elif low.startswith("optimize glycemic") and "glycemia" not in domains:
            domains["glycemia"] = recommendation
        elif low.startswith("optimize bp") and "blood_pressure" not in domains:
            domains["blood_pressure"] = recommendation
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


def _prevent_high(result: Any) -> bool:
    category = getattr(getattr(result, "prevent_risk_category", None), "value", None)
    category = category or getattr(result, "prevent_risk_category", None)
    risk = _num(getattr(result, "prevent_10y_ascvd", None))
    return category == "HIGH" or (risk is not None and risk >= 10)


def _clinical_ascvd(patient: Any) -> bool:
    return bool(getattr(patient, "clinical_ascvd", False))


def _lipid_line(patient: Any, result: Any) -> str:
    if _clinical_ascvd(patient):
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
        "Optimize glycemic",
        "Optimize BP",
        "Address smoking",
        "Obtain ",
        "Check ",
        "Coronary calcium",
        "Consider hsCRP",
        "Repeat fasting",
        "No escalation",
        "Treatment is reasonable",
    )
    if dominant and not dominant.startswith(non_lipid_starts):
        return dominant

    ldl = _num(getattr(patient, "ldl_c", None))
    if ldl is not None and ldl >= 190:
        return "Lipid-lowering therapy is indicated; treat toward severe hypercholesterolemia pathway."
    if _prevent_high(result):
        return "Lipid-lowering therapy is indicated; treat toward high-risk targets."
    return "No medication escalation today."


def _cac_line(patient: Any, result: Any) -> str:
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
        line += " CAC reasonable if treatment decision or intensity remains uncertain."
    elif not cac_testing:
        age_gate_note = build_cac_age_gate_note(patient, result)
        if age_gate_note:
            line += f" {age_gate_note}"
    return line


def _aspirin_line(patient: Any, result: Any) -> str:
    age = _num(getattr(patient, "age", None))
    cac = _num(getattr(patient, "cac", None))

    if _clinical_ascvd(patient):
        return "Antiplatelet therapy indicated for secondary prevention if clinically appropriate."
    if age is not None and age >= 70:
        return "Aspirin not indicated for routine primary prevention."
    if cac is None:
        return "Aspirin not indicated for routine primary prevention."
    if age is not None and 40 <= age <= 69 and (cac >= 100 or _prevent_high(result)):
        return "Aspirin may be considered if bleeding risk is low after shared decision-making."
    return "Aspirin not indicated for routine primary prevention."


def _clarifier_items(result: Any) -> list[str]:
    domains = _domains(result)
    items = [TESTING_LABELS[key] for key in TESTING_LABELS if key in domains]
    if "treatment_timing" in domains and items:
        items.append("Clarification testing should not delay treatment.")
    return _unique(items)


def _supporting_items(result: Any) -> list[str]:
    mapping = {
        "kidney": "Optimize kidney-protective therapy.",
        "glycemia": "Optimize glycemic therapy.",
        "blood_pressure": "Treat blood pressure toward individualized goal.",
        "smoking": "Prioritize smoking cessation support.",
        "triglycerides": _domain_line(result, "triglycerides"),
    }
    domains = _domains(result)
    items = [mapping[key] for key in mapping if key in domains]
    return _unique(items)


def build_action_scaffold(patient: Any, result: Any) -> list[ActionSection]:
    sections = [
        ActionSection("Lipid therapy", _lipid_line(patient, result)),
        ActionSection("Coronary calcium", _cac_line(patient, result)),
        ActionSection("Aspirin", _aspirin_line(patient, result)),
    ]

    supporting = _supporting_items(result)
    if supporting:
        sections.append(ActionSection("Supporting actions", items=supporting))

    clarifiers = _clarifier_items(result)
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
