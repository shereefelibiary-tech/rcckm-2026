from dataclasses import dataclass
from typing import Any, List, Optional

from modules.risk_enhancers.reproductive import reproductive_marker_items


@dataclass
class SignalContribution:
    domain: str
    label: str
    actual_value: Any
    points: float
    severity: Optional[str]
    rationale: str
    id: Optional[str] = None
    color_key: Optional[str] = None
    display: bool = True
    stack_in_tower: bool = True


@dataclass
class RssContextItem:
    label: str
    detail: str
    note: str = "Shown as context; not included in RSS points."


def build_rss_contributions(patient, result) -> List[SignalContribution]:
    contributions: List[SignalContribution] = []

    cac = getattr(patient, "cac", None)
    if cac is not None:
        if 1 <= cac <= 99:
            contributions.append(
                SignalContribution(
                    domain="CAC",
                    label="CAC plaque burden",
                    actual_value=cac,
                    points=10,
                    severity="mild",
                    rationale="CAC 1-99 indicates mild plaque burden.",
                )
            )
        elif 100 <= cac <= 299:
            contributions.append(
                SignalContribution(
                    domain="CAC",
                    label="CAC plaque burden",
                    actual_value=cac,
                    points=20,
                    severity="moderate",
                    rationale="CAC 100-299 indicates moderate plaque burden.",
                )
            )
        elif 300 <= cac <= 999:
            contributions.append(
                SignalContribution(
                    domain="CAC",
                    label="CAC plaque burden",
                    actual_value=cac,
                    points=30,
                    severity="severe",
                    rationale="CAC 300-999 indicates severe plaque burden.",
                )
            )
        elif cac >= 1000:
            contributions.append(
                SignalContribution(
                    domain="CAC",
                    label="CAC plaque burden",
                    actual_value=cac,
                    points=40,
                    severity="extreme",
                    rationale="CAC >=1000 indicates extreme plaque burden.",
                )
            )

    apob = getattr(patient, "apob", None)
    if apob is not None:
        if 80 <= apob <= 99:
            contributions.append(
                SignalContribution(
                    domain="ApoB",
                    label="ApoB elevation",
                    actual_value=apob,
                    points=4,
                    severity=None,
                    rationale="ApoB 80-99 represents borderline elevation.",
                )
            )
        elif 100 <= apob <= 129:
            contributions.append(
                SignalContribution(
                    domain="ApoB",
                    label="ApoB elevation",
                    actual_value=apob,
                    points=8,
                    severity=None,
                    rationale="ApoB 100-129 represents elevated ApoB.",
                )
            )
        elif apob >= 130:
            contributions.append(
                SignalContribution(
                    domain="ApoB",
                    label="ApoB elevation",
                    actual_value=apob,
                    points=12,
                    severity=None,
                    rationale="ApoB >=130 represents severe elevation.",
                )
            )

    lp_a_value = getattr(patient, "lp_a_value", None)
    lp_a_unit = getattr(patient, "lp_a_unit", None)
    if lp_a_value is not None and lp_a_unit == "nmol/L":
        if 75 <= lp_a_value <= 124:
            points = 2
            rationale = "Lp(a) 75-124 nmol/L is a borderline risk enhancer."
        elif 125 <= lp_a_value <= 249:
            points = 8
            rationale = "Lp(a) 125-249 nmol/L indicates elevated Lp(a)."
        elif 250 <= lp_a_value <= 429:
            points = 12
            rationale = "Lp(a) 250-429 nmol/L indicates higher elevated Lp(a)."
        elif lp_a_value >= 430:
            points = 15
            rationale = "Lp(a) >=430 nmol/L indicates very high Lp(a) elevation."
        else:
            points = 0
            rationale = ""
        if points > 0:
            contributions.append(
                SignalContribution(
                    domain="Lp(a)",
                    label="Elevated Lp(a)",
                    actual_value=f"{lp_a_value} {lp_a_unit}",
                    points=points,
                    severity="tiny" if points <= 2 else None,
                    rationale=rationale,
                )
            )
    elif lp_a_value is not None and lp_a_unit == "mg/dL":
        if 30 <= lp_a_value <= 49:
            points = 2
            rationale = "Lp(a) 30-49 mg/dL is a borderline risk enhancer."
        elif 50 <= lp_a_value <= 99:
            points = 8
            rationale = "Lp(a) 50-99 mg/dL indicates elevated Lp(a)."
        elif 100 <= lp_a_value <= 179:
            points = 12
            rationale = "Lp(a) 100-179 mg/dL indicates higher elevated Lp(a)."
        elif lp_a_value >= 180:
            points = 15
            rationale = "Lp(a) >=180 mg/dL indicates very high Lp(a) elevation."
        else:
            points = 0
            rationale = ""
        if points > 0:
            contributions.append(
                SignalContribution(
                    domain="Lp(a)",
                    label="Elevated Lp(a)",
                    actual_value=f"{lp_a_value} {lp_a_unit}",
                    points=points,
                    severity="tiny" if points <= 2 else None,
                    rationale=rationale,
                )
            )

    hscrp = getattr(patient, "hscrp", None)
    if hscrp is not None:
        if 2 <= hscrp <= 4.9:
            contributions.append(
                SignalContribution(
                    domain="hsCRP",
                    label="Inflammatory risk",
                    actual_value=hscrp,
                    points=4,
                    severity=None,
                    rationale="hsCRP 2-4.9 mg/L indicates elevated inflammatory risk.",
                )
            )
        elif hscrp >= 5:
            contributions.append(
                SignalContribution(
                    domain="hsCRP",
                    label="Inflammatory risk",
                    actual_value=hscrp,
                    points=7,
                    severity=None,
                    rationale="hsCRP >=5 mg/L indicates high inflammatory risk.",
                )
            )

    egfr = getattr(patient, "egfr", None)
    if egfr is not None:
        if 45 <= egfr <= 59:
            contributions.append(
                SignalContribution(
                    domain="Kidney",
                    label="Reduced eGFR",
                    actual_value=egfr,
                    points=5,
                    severity=None,
                    rationale="eGFR 45-59 indicates mild kidney function reduction.",
                )
            )
        elif 30 <= egfr <= 44:
            contributions.append(
                SignalContribution(
                    domain="Kidney",
                    label="Reduced eGFR",
                    actual_value=egfr,
                    points=8,
                    severity=None,
                    rationale="eGFR 30-44 indicates moderate kidney function reduction.",
                )
            )
        elif 15 <= egfr <= 29:
            contributions.append(
                SignalContribution(
                    domain="Kidney",
                    label="Reduced eGFR",
                    actual_value=egfr,
                    points=12,
                    severity=None,
                    rationale="eGFR 15-29 indicates severe kidney function reduction.",
                )
            )
        elif egfr < 15:
            contributions.append(
                SignalContribution(
                    domain="Kidney",
                    label="Reduced eGFR",
                    actual_value=egfr,
                    points=15,
                    severity=None,
                    rationale="eGFR <15 indicates kidney failure risk.",
                )
            )

    uacr = getattr(patient, "uacr", None)
    if uacr is not None:
        if 30 <= uacr <= 299:
            contributions.append(
                SignalContribution(
                    domain="Kidney",
                    label="Albuminuria",
                    actual_value=uacr,
                    points=6,
                    severity=None,
                    rationale="UACR 30-299 indicates moderately increased albuminuria.",
                )
            )
        elif uacr >= 300:
            contributions.append(
                SignalContribution(
                    domain="Kidney",
                    label="Albuminuria",
                    actual_value=uacr,
                    points=10,
                    severity=None,
                    rationale="UACR >=300 indicates severely increased albuminuria.",
                )
            )

    triglycerides = getattr(patient, "triglycerides", None)
    if triglycerides is not None:
        if 150 <= triglycerides <= 499:
            contributions.append(
                SignalContribution(
                    domain="Lipids",
                    label="Hypertriglyceridemia",
                    actual_value=triglycerides,
                    points=4,
                    severity=None,
                    rationale="Triglycerides 150-499 indicates hypertriglyceridemia.",
                )
            )
        elif triglycerides >= 500:
            contributions.append(
                SignalContribution(
                    domain="Lipids",
                    label="Hypertriglyceridemia",
                    actual_value=triglycerides,
                    points=8,
                    severity=None,
                    rationale="Triglycerides >=500 indicates severe hypertriglyceridemia.",
                )
            )

    a1c = getattr(patient, "a1c", None)
    if getattr(patient, "diabetes", False):
        contributions.append(
            SignalContribution(
                domain="Metabolic",
                label="Diabetes",
                actual_value=a1c if a1c is not None else True,
                points=8,
                severity=None,
                rationale="Diabetes is a risk enhancer for ASCVD.",
            )
        )
    elif a1c is not None:
        if 5.7 <= a1c <= 6.4:
            contributions.append(
                SignalContribution(
                    domain="Metabolic",
                    label="A1c elevation",
                    actual_value=a1c,
                    points=2,
                    severity="tiny",
                    rationale="A1c 5.7-6.4% indicates prediabetes-range dysglycemia.",
                )
            )
        elif a1c >= 6.5:
            contributions.append(
                SignalContribution(
                    domain="Metabolic",
                    label="A1c elevation",
                    actual_value=a1c,
                    points=8,
                    severity=None,
                    rationale="A1c >=6.5% indicates diabetes-range glycemia.",
                )
            )

    if getattr(patient, "smoker", False):
        contributions.append(
            SignalContribution(
                domain="Behavioral",
                label="Smoking",
                actual_value=True,
                points=8,
                severity=None,
                rationale="Current smoking is a modifiable risk factor.",
            )
        )

    premature_family_history = bool(getattr(patient, "premature_fhx_ascvd", False)) or bool(
        getattr(patient, "family_history_premature_ascvd", False)
    )
    if premature_family_history:
        contributions.append(
            SignalContribution(
                domain="Family History",
                label="Premature family history",
                actual_value=getattr(patient, "family_history_summary", None) or True,
                points=3,
                severity="tiny",
                rationale="Premature first-degree family history is a risk enhancer.",
            )
        )

    inflammatory_items = [
        ("rheumatoid_arthritis", "RA"),
        ("sle", "SLE"),
        ("psoriasis", "Psoriasis"),
        ("inflammatory_arthritis", "Inflammatory arthritis"),
        ("ibd", "IBD"),
    ]
    added_inflammatory_specific = False
    for attr, label in inflammatory_items:
        if getattr(patient, attr, False):
            added_inflammatory_specific = True
            contributions.append(
                SignalContribution(
                    domain="Inflammatory Disease",
                    label=label,
                    actual_value=True,
                    points=2,
                    severity="tiny",
                    rationale=f"{label} is a chronic inflammatory risk enhancer.",
                )
            )
    if getattr(patient, "hiv", False):
        contributions.append(
            SignalContribution(
                domain="HIV",
                label="HIV",
                actual_value="stable ART" if getattr(patient, "stable_art", False) else True,
                points=2,
                severity="tiny",
                rationale="HIV is shown as its own guideline risk-enhancing pathway.",
            )
        )
    if getattr(patient, "inflammatory_disease", False) and not added_inflammatory_specific:
        contributions.append(
            SignalContribution(
                domain="Inflammatory Disease",
                label="Inflammatory disease",
                actual_value=True,
                points=2,
                severity="tiny",
                rationale="Chronic inflammatory disease is a risk enhancer.",
            )
        )

    ancestry_items = [
        ("south_asian_ancestry", "South Asian ancestry"),
        ("filipino_ancestry", "Filipino ancestry"),
    ]
    for attr, label in ancestry_items:
        if getattr(patient, attr, False):
            contributions.append(
                SignalContribution(
                    domain="Ancestry / SDOH",
                    label=label,
                    actual_value=True,
                    points=2,
                    severity="tiny",
                    rationale=f"{label} is a guideline risk-enhancing context.",
                )
            )

    if getattr(patient, "suspected_fh_hefh", False):
        contributions.append(
            SignalContribution(
                domain="Atherogenic Burden",
                label="Suspected FH / HeFH",
                actual_value=True,
                points=8,
                severity="moderate",
                rationale="Suspected FH/HeFH is a treatment-forward severe lipid pathway context.",
            )
        )

    if getattr(patient, "incidental_cac", False) and getattr(patient, "cac", None) is None:
        severe = str(getattr(patient, "incidental_cac_severity", "") or "").lower() == "severe"
        contributions.append(
            SignalContribution(
                domain="Plaque",
                label="Incidental CAC",
                actual_value="severe on noncardiac CT" if severe else "noted on noncardiac CT",
                points=20 if severe else 10,
                severity="major" if severe else "moderate",
                rationale="Incidental coronary calcium is qualitative plaque evidence.",
            )
        )

    if getattr(patient, "osa", False):
        contributions.append(
            SignalContribution(
                domain="Sleep / Hypoxia",
                label="OSA",
                actual_value=True,
                points=2,
                severity="tiny",
                rationale="OSA can contribute to cardiometabolic risk.",
            )
        )

    if getattr(patient, "masld", False):
        contributions.append(
            SignalContribution(
                domain="Liver / MASLD",
                label="MASLD",
                actual_value=True,
                points=2,
                severity="tiny",
                rationale="MASLD can track metabolic and cardiometabolic risk.",
            )
        )

    for item in reproductive_marker_items(patient):
        contributions.append(
            SignalContribution(
                domain="Reproductive History",
                label=item["label"],
                actual_value=item["detail"],
                points=2,
                severity="tiny",
                rationale=f"{item['label']} is a reproductive risk marker.",
            )
        )

    return contributions


def calculate_rss_total(contributions: List[SignalContribution]) -> float:
    total = sum(contribution.points for contribution in contributions)
    return round(total, 1)


def _fmt(value: Any) -> str:
    try:
        return f"{float(value):g}"
    except (TypeError, ValueError):
        return str(value)


def _has_contribution(contributions: list[SignalContribution], label: str) -> bool:
    return any(contribution.label == label and contribution.points > 0 for contribution in contributions)


def _lpa_context_label(value: float, unit: str | None) -> str | None:
    if unit == "nmol/L":
        if value >= 430:
            return "Very high Lp(a)"
        if value >= 250:
            return "High Lp(a)"
        if value >= 125:
            return "Elevated Lp(a)"
        if value >= 75:
            return "Borderline Lp(a)"
    if unit == "mg/dL":
        if value >= 180:
            return "Very high Lp(a)"
        if value >= 100:
            return "High Lp(a)"
        if value >= 50:
            return "Elevated Lp(a)"
        if value >= 30:
            return "Borderline Lp(a)"
    return None


def build_rss_transparency(patient, result, rss_contributions):
    contributors = [
        contribution
        for contribution in (rss_contributions or [])
        if getattr(contribution, "points", 0) > 0
    ]
    context: list[RssContextItem] = []

    a1c = getattr(patient, "a1c", None)
    diabetes = bool(getattr(patient, "diabetes", False)) or (
        a1c is not None and a1c >= 6.5
    )
    if a1c is not None and 5.7 <= a1c <= 6.4 and not _has_contribution(contributors, "A1c elevation"):
        context.append(
            RssContextItem(
                "Prediabetes-range A1c",
                f"A1c {_fmt(a1c)}%",
            )
        )
    elif diabetes and not _has_contribution(contributors, "Diabetes"):
        detail = f"A1c {_fmt(a1c)}%" if a1c is not None else "Diabetes"
        context.append(RssContextItem("Diabetes", detail))

    lpa = getattr(patient, "lp_a_value", None)
    lpa_unit = getattr(patient, "lp_a_unit", None)
    if lpa is not None:
        lpa_label = _lpa_context_label(float(lpa), lpa_unit)
        if lpa_label and not _has_contribution(contributors, "Elevated Lp(a)"):
            context.append(
                RssContextItem(
                    lpa_label,
                    f"Lp(a) {_fmt(lpa)} {lpa_unit or ''}".strip(),
                )
            )

    family_summary = getattr(patient, "family_history_summary", None)
    has_structured_family = bool(family_summary)
    premature = bool(getattr(patient, "premature_fhx_ascvd", False)) or bool(
        getattr(patient, "family_history_premature_ascvd", False)
    )
    if premature and not _has_contribution(contributors, "Premature family history"):
        context.append(
            RssContextItem(
                "Premature family history",
                family_summary or "First-degree relative with premature ASCVD",
            )
        )
    elif has_structured_family and not premature:
        context.append(RssContextItem("Family history", family_summary))

    missing: list[RssContextItem] = []
    clarification = getattr(result, "clarification", None) or {}
    missing_map = [
        ("recommend_lpa", "Lp(a)", "One-time risk assessment"),
        ("recommend_uacr", "UACR", "Kidney risk completion"),
        ("recommend_cac", "CAC", "Plaque burden clarification"),
        ("recommend_apob", "ApoB", "Particle burden clarification"),
    ]
    for flag, label, detail in missing_map:
        if clarification.get(flag):
            missing.append(RssContextItem(label, detail, "Missing clarifier."))

    result.rss_contributors = contributors
    result.risk_enhancers_context = context
    result.missing_clarifiers = missing
    return {
        "contributors": contributors,
        "context": context,
        "missing": missing,
    }


def get_rss_contributors(result):
    return list(getattr(result, "rss_contributors", None) or [])


def get_rss_contributions(result):
    """Return canonical RSS contribution dictionaries for scored display paths."""
    items = []
    for contribution in get_rss_contributors(result):
        points = float(getattr(contribution, "points", 0) or 0)
        if points <= 0:
            continue
        items.append(
            {
                "id": getattr(contribution, "id", None)
                or str(getattr(contribution, "label", "") or "").lower().replace(" ", "_"),
                "domain": getattr(contribution, "domain", ""),
                "label": getattr(contribution, "label", ""),
                "value_label": _fmt(getattr(contribution, "actual_value", "")),
                "points": points,
                "severity": getattr(contribution, "severity", None) or _severity_for_points(points),
                "color_key": getattr(contribution, "color_key", None)
                or str(getattr(contribution, "domain", "") or "").lower().replace(" ", "_"),
                "display": bool(getattr(contribution, "display", True)),
                "stack_in_tower": bool(getattr(contribution, "stack_in_tower", True)),
            }
        )
    return items


def _severity_for_points(points: float) -> str:
    if points >= 30:
        return "very_high"
    if points >= 8:
        return "major"
    if points >= 5:
        return "moderate"
    if points >= 3:
        return "mild"
    return "tiny"


def get_risk_enhancers_context(result):
    return list(getattr(result, "risk_enhancers_context", None) or [])


def get_missing_clarifiers(result):
    return list(getattr(result, "missing_clarifiers", None) or [])
