from dataclasses import dataclass, field
from typing import Any

from modules.cac_recommendation.engine import build_cac_age_gate_note
from modules.risk_enhancers.reproductive import has_reproductive_risk_markers


@dataclass
class ActionSection:
    label: str
    line: str = ""
    items: list[str] = field(default_factory=list)


TESTING_LABELS = {
    "apob_testing": "ApoB - particle burden clarification",
    "lpa_testing": "Lp(a) - one-time risk assessment",
    "uacr_testing": "Obtain UACR to complete kidney-risk assessment.",
    "cac_testing": "CAC - risk clarification",
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
    if ldl is not None and ldl >= 190:
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
                line = "CAC not performed; below usual age threshold, use only if it would change management."
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

    if _clinical_ascvd(patient):
        return "Antiplatelet therapy indicated for secondary prevention if clinically appropriate."
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
        "blood_pressure": "Treat blood pressure toward individualized goal.",
        "smoking": "Prioritize smoking cessation support.",
        "triglycerides": _domain_line(result, "triglycerides"),
        "tg_diet": _domain_line(result, "tg_diet"),
        "rdn_referral": _domain_line(result, "rdn_referral"),
        "tg_pharmacotherapy": _domain_line(result, "tg_pharmacotherapy"),
        "supplements": _domain_line(result, "supplements"),
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
    sections.append(ActionSection("Lipid therapy", lipid_line))
    if lipid_line.startswith("No medication escalation"):
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
                "Evaluate secondary causes of severe hypercholesterolemia.",
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

    cac_line = _cac_line(patient, result)
    if cac_line:
        sections.append(ActionSection("Coronary calcium", cac_line))
    sections.append(ActionSection("Aspirin", _aspirin_line(patient, result)))

    supporting = [] if prioritize_uacr else _supporting_items(result)
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
