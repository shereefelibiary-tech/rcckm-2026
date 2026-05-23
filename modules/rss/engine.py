from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass
class SignalContribution:
    domain: str
    label: str
    actual_value: Any
    points: float
    severity: Optional[str]
    rationale: str


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
        if 125 <= lp_a_value <= 249:
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
                    severity=None,
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

    if getattr(patient, "diabetes", False):
        contributions.append(
            SignalContribution(
                domain="Metabolic",
                label="Diabetes",
                actual_value=getattr(patient, "a1c", None) or True,
                points=8,
                severity=None,
                rationale="Diabetes is a risk enhancer for ASCVD.",
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

    return contributions


def calculate_rss_total(contributions: List[SignalContribution]) -> float:
    total = sum(contribution.points for contribution in contributions)
    return round(total, 1)
