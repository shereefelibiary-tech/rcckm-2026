from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from typing import Any

from modules.actions.scaffold import build_action_recommendation_lines
from renderers.clarifier_renderer import build_clarifier_card_html
from renderers.emr_renderer import render_emr_note
from renderers.patient_roadmap import render_patient_roadmap_text
from ui.demo_case_gallery import (
    DEMO_CASES,
    DEMO_PATIENTS,
    build_demo_patient,
    demo_case_description,
    demo_case_metadata,
)
from ui.report_layout import run_patient


STRICT_MODE = True

MANDATORY_BASELINE_FIELDS = (
    "age",
    "sex",
    "height_in",
    "weight_lb",
    "bmi",
    "sbp",
    "dbp",
    "tc",
    "ldl_c",
    "hdl_c",
    "triglycerides",
)

PREFERRED_BASELINE_FIELDS = (
    "smoker",
    "egfr",
    "creatinine",
    "medications_raw",
)

ADVANCED_PREVENTION_FIELDS = (
    "apob",
    "lp_a_value",
    "uacr",
    "hscrp",
)

FORBIDDEN_OUTPUT_FRAGMENTS = (
    "total cardiovascular risk",
    "cardiovascular event",
    "heart failure",
    "hsCRP - inflammatory residual risk",
    "inflammatory residual risk",
    "PREVENT 10-year risk",
)

CONTRADICTIONS = (
    ("No medication escalation", "High-intensity"),
    ("No medication escalation", "lipid-lowering therapy indicated"),
    ("CAC not performed", "CAC 0"),
    ("aspirin not indicated", "aspirin may be considered"),
)

AGE_AWARE_CAC_LINE = (
    "CAC not routinely recommended at this age; consider only if results would change management."
)

EXPECTED_SHOWCASE = {
    "healthy_low_risk_prevention": ("low-risk complete data", "lifestyle prevention"),
    "obesity_metabolic_syndrome": ("metabolic risk", "missing-data clarification"),
    "prediabetes_insulin_resistance": ("prediabetes", "reproductive history"),
    "high_apob_discordance": ("ApoB discordance", "particle burden"),
    "elevated_lpa": ("Lp(a)", "risk-enhancer context"),
    "cac_zero_ambiguity_resolution": ("CAC 0", "plaque clarification"),
    "cac_1_99_plaque_present": ("CAC 1-99", "plaque-present pathway"),
    "cac_100_high_plaque_burden": ("CAC high burden", "treatment escalation"),
    "ckd_albuminuria": ("albuminuria", "kidney involvement"),
    "diabetes_ckm_stage": ("diabetes", "CKM staging"),
    "on_treatment_above_target_lipids": ("on-treatment residual risk", "statin intolerance"),
    "sparse_realistic_pcp_intake": ("missing-data clarification", "PCP intake"),
    "younger_strong_family_history": ("premature family history", "prevention opportunity"),
    "older_multiple_treated_risk_factors": ("treated risk factors", "multi-domain prevention"),
}

SHOWCASE_TERMS = {
    "borderline ASCVD risk": ("borderline", "ascvd risk", "moderate-intensity"),
    "low 10-year high 30-year": ("low short-term", "longer-term", "30-year ascvd"),
    "LDL-C": ("ldl-c",),
    "LDL-C >=190": ("ldl-c >=190", "severe hypercholesterolemia"),
    "FH pathway": ("fh", "family history", "ldl-c >=190"),
    "hypertriglyceridemia": ("hypertriglyceridemia", "triglycerides"),
    "CAC >=100": ("cac 145", "coronary calcium", "plaque"),
    "incidental CAC": ("incidental coronary", "incidental cac"),
    "breast arterial calcification": ("breast arterial calcification",),
    "CKD G3aA2": ("g3a", "a2", "kidney"),
    "SGLT2": ("sglt2",),
    "add-on therapy": ("add-on", "intensification", "above target"),
    "BP treated above goal": ("bp", "blood pressure", "goal"),
    "ACEi/ARB": ("acei/arb", "ace inhibitor", "arb"),
    "rheumatoid arthritis": ("rheumatoid arthritis",),
    "South Asian ancestry": ("south asian ancestry",),
    "active smoking": ("smoking", "current smoking"),
    "cancer survivor": ("cancer survivor", "cancer survivorship"),
    "multiple enhancers": ("risk context", "preeclampsia", "family history", "osa", "masld"),
    "low-risk complete data": ("low", "no medication escalation", "complete"),
    "lifestyle prevention": ("lifestyle", "continue lifestyle"),
    "metabolic risk": ("metabolic", "triglycerides", "bmi", "osa", "masld"),
    "missing-data clarification": ("clarification", "obtain", "check lp(a)", "apob", "uacr"),
    "prediabetes": ("prediabetes", "a1c"),
    "reproductive history": ("reproductive", "gestational", "preeclampsia"),
    "ApoB discordance": ("apob", "particle"),
    "particle burden": ("apob", "particle"),
    "Lp(a)": ("lp(a)",),
    "risk-enhancer context": ("lp(a)", "reproductive", "preeclampsia"),
    "CAC 0": ("cac 0", "coronary calcium score: 0", "no calcified plaque"),
    "plaque clarification": ("plaque", "coronary calcium", "cac"),
    "CAC 1-99": ("cac 38", "coronary calcium score: 38", "mild plaque"),
    "plaque-present pathway": ("plaque present", "mild calcified plaque", "cac 38"),
    "CAC high burden": ("cac 350", "high plaque", "high amount of plaque"),
    "treatment escalation": ("high-intensity", "treat toward", "intensify"),
    "albuminuria": ("albuminuria", "uacr"),
    "kidney involvement": ("kidney", "albuminuria", "uacr"),
    "diabetes": ("diabetes", "a1c"),
    "CKM staging": ("ckm stage", "kidney"),
    "on-treatment residual risk": ("statin intolerance", "above target", "intensify"),
    "statin intolerance": ("statin intolerance", "myalgias", "maximally tolerated"),
    "PCP intake": ("primary-care", "pcp", "advanced prevention clarifiers", "standard"),
    "premature family history": ("premature family", "father mi age 49"),
    "prevention opportunity": ("prevention opportunity", "early risk reduction", "low short-term"),
    "treated risk factors": ("treated", "atorvastatin", "losartan", "bp"),
    "multi-domain prevention": ("diabetes", "blood pressure", "lipid", "kidney"),
}


@dataclass
class DemoCaseAudit:
    """Structured clinical and UX coherence findings for one demo case."""

    case_name: str
    label: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    coherence_score: int = 100
    completeness_score: int = 100
    patient_readability_score: int = 100
    showcase_value_score: int = 100
    showcase_concepts: tuple[str, ...] = ()

    @property
    def overall_score(self) -> int:
        return round(
            (
                self.coherence_score
                + self.completeness_score
                + self.patient_readability_score
                + self.showcase_value_score
            )
            / 4
        )


@dataclass
class DemoAuditReport:
    """Aggregate demo-case audit output for CLI, snapshots, and tests."""

    cases: list[DemoCaseAudit]

    @property
    def errors(self) -> list[str]:
        return [
            f"{case.label}: {message}"
            for case in self.cases
            for message in case.errors
        ]

    @property
    def warnings(self) -> list[str]:
        return [
            f"{case.label}: {message}"
            for case in self.cases
            for message in case.warnings
        ]

    @property
    def suggestions(self) -> list[str]:
        return [
            f"{case.label}: {message}"
            for case in self.cases
            for message in case.suggestions
        ]

    def ranked(self) -> list[DemoCaseAudit]:
        return sorted(self.cases, key=lambda case: case.overall_score, reverse=True)

    def format_summary(self) -> str:
        """Return a readable score table plus grouped findings."""
        lines = [
            "RCCKM Demo Case Audit",
            f"Cases checked: {len(self.cases)}",
            f"Errors: {len(self.errors)}",
            f"Warnings: {len(self.warnings)}",
            f"Suggestions: {len(self.suggestions)}",
            "",
            "Summary table:",
            "Score  Complete  Coherent  Readable  Showcase  Demo",
        ]
        for case in self.ranked():
            lines.append(
                f"{case.overall_score:>5}  "
                f"{case.completeness_score:>8}  "
                f"{case.coherence_score:>8}  "
                f"{case.patient_readability_score:>8}  "
                f"{case.showcase_value_score:>8}  "
                f"{case.label}"
            )
        lines.extend(
            [
                "",
                "Strongest demos: " + ", ".join(case.label for case in self.ranked()[:3]),
                "Weakest demos: " + ", ".join(case.label for case in self.ranked()[-3:]),
                "Sparse demos: "
                + (
                    ", ".join(
                        case.label
                        for case in self.cases
                        if any("sparse" in warning.lower() for warning in case.warnings)
                    )
                    or "none"
                ),
                "Contradictory demos: "
                + (
                    ", ".join(
                        case.label
                        for case in self.cases
                        if any("contradict" in error.lower() for error in case.errors)
                    )
                    or "none"
                ),
                "Demos needing rewrite: "
                + (", ".join(case.label for case in self.cases if case.errors) or "none"),
            ]
        )
        for heading, items in (
            ("Errors", self.errors),
            ("Warnings", self.warnings),
            ("Suggestions", self.suggestions),
        ):
            if not items:
                continue
            lines.extend(["", f"{heading}:"])
            lines.extend(f"- {item}" for item in items)
        return "\n".join(lines)


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", str(text or ""))


def _visible_demo_output(patient: Any, result: Any) -> str:
    action_text = "\n".join(build_action_recommendation_lines(patient, result))
    clarifier_text = _strip_html(build_clarifier_card_html(result))
    return "\n".join(
        [
            render_emr_note(patient, result),
            render_patient_roadmap_text(patient, result),
            action_text,
            clarifier_text,
        ]
    )


def render_demo_output_snapshot(case_name: str) -> str:
    """Render stable demo output text for snapshot-based drift checks."""
    label = next((label for label, name in DEMO_CASES if name == case_name), case_name)
    patient = build_demo_patient(case_name)
    result, rss_total, rss_contributions = run_patient(patient)
    return "\n".join(
        [
            f"DEMO: {label}",
            f"CASE: {case_name}",
            "",
            "EMR:",
            render_emr_note(patient, result),
            "",
            "PATIENT ROADMAP:",
            render_patient_roadmap_text(patient, result),
            "",
            "ACTIONS:",
            "\n".join(f"- {line}" for line in build_action_recommendation_lines(patient, result)),
            "",
            f"RSS: {rss_total:g}",
            "RSS CONTRIBUTORS:",
            "\n".join(
                f"- {item.label}: {item.actual_value} (+{item.points:g})"
                for item in rss_contributions
            )
            or "- none",
        ]
    )


def _is_below_usual_cac_age(patient: Any) -> bool:
    age = getattr(patient, "age", None)
    sex = str(getattr(patient, "sex", "") or "").strip().lower()
    if age is None:
        return False
    if sex.startswith("f"):
        return age < 45
    if sex.startswith("m"):
        return age < 40
    return False


def _missing(payload: dict[str, Any], fields: tuple[str, ...]) -> list[str]:
    return [field for field in fields if payload.get(field) in (None, "")]


def _score_floor(finding: DemoCaseAudit) -> None:
    finding.coherence_score = max(0, min(100, finding.coherence_score))
    finding.completeness_score = max(0, min(100, finding.completeness_score))
    finding.patient_readability_score = max(0, min(100, finding.patient_readability_score))
    finding.showcase_value_score = max(0, min(100, finding.showcase_value_score))


def audit_demo_case(label: str, case_name: str) -> DemoCaseAudit:
    """Evaluate one demo case for data, clinical, output, and UX coherence."""
    finding = DemoCaseAudit(case_name=case_name, label=label)
    payload = DEMO_PATIENTS.get(case_name, {})
    metadata = demo_case_metadata(case_name)
    finding.showcase_concepts = tuple(
        metadata.get("expected_showcase_points")
        or EXPECTED_SHOWCASE.get(case_name, ())
    )
    for field in (
        "category",
        "expected_showcase_points",
        "expected_primary_action",
        "expected_level_or_level_range",
        "expected_risk_framing",
    ):
        if not metadata.get(field):
            finding.errors.append(f"missing demo metadata `{field}`")

    missing_mandatory = _missing(payload, MANDATORY_BASELINE_FIELDS)
    for field in missing_mandatory:
        finding.errors.append(f"missing mandatory baseline field `{field}`")
    missing_preferred = _missing(payload, PREFERRED_BASELINE_FIELDS)
    for field in missing_preferred:
        finding.warnings.append(f"missing preferred clinic field `{field}`")
    if payload.get("diabetes") is None and payload.get("a1c") is None:
        finding.errors.append("missing both diabetes status and A1c")
    if not demo_case_description(case_name):
        finding.suggestions.append("add a short demo selector description")

    advanced_missing = _missing(payload, ADVANCED_PREVENTION_FIELDS)
    cac_known = payload.get("cac") is not None or bool(payload.get("cac_not_done"))
    if not cac_known:
        advanced_missing.append("cac_status")
    if len(advanced_missing) >= 4:
        finding.warnings.append(
            "sparse advanced prevention data: " + ", ".join(advanced_missing)
        )
        finding.completeness_score -= 8

    finding.completeness_score -= 20 * len(missing_mandatory)
    finding.completeness_score -= 4 * len(missing_preferred)
    if not finding.showcase_concepts:
        finding.suggestions.append("define the demo capability this case showcases")
        finding.showcase_value_score -= 25

    if finding.errors:
        _score_floor(finding)
        return finding

    patient = build_demo_patient(case_name)
    result, rss_total, rss_contributions = run_patient(patient)
    visible = _visible_demo_output(patient, result)
    visible_lower = visible.lower()

    for phrase in FORBIDDEN_OUTPUT_FRAGMENTS:
        if phrase.lower() in visible_lower:
            finding.errors.append(f"forbidden output wording `{phrase}`")
            finding.patient_readability_score -= 12

    if "10-year ASCVD risk" not in visible:
        finding.errors.append("missing 10-year ASCVD risk label")
        finding.coherence_score -= 20
    prevent_30y = getattr(result, "prevent_30y_ascvd", None)
    if prevent_30y is not None and "30-year ASCVD risk" not in visible:
        finding.errors.append("missing 30-year ASCVD risk label")
        finding.coherence_score -= 20

    for first, second in CONTRADICTIONS:
        if first.lower() in visible_lower and second.lower() in visible_lower:
            finding.errors.append(f"contradictory output `{first}` with `{second}`")
            finding.coherence_score -= 30

    cac_missing = getattr(patient, "cac", None) is None and bool(
        getattr(patient, "cac_not_done", False)
    )
    if _is_below_usual_cac_age(patient) and cac_missing and "CAC" in visible:
        if AGE_AWARE_CAC_LINE not in visible and "CAC reasonable" in visible:
            finding.errors.append("CAC recommendation is not age-aware")
            finding.coherence_score -= 20

    prevent_10y = getattr(result, "prevent_10y_ascvd", None)
    cac = getattr(patient, "cac", None)
    ldl = getattr(patient, "ldl_c", None)
    low_short_term_no_major_path = (
        prevent_10y is not None
        and prevent_10y < 3
        and cac is None
        and (ldl is None or ldl < 190)
        and not bool(getattr(patient, "clinical_ascvd", False))
    )
    if low_short_term_no_major_path and any(
        phrase in visible_lower
        for phrase in ("very high risk", "secondary-prevention", "high-intensity")
    ):
        finding.errors.append("low short-term ASCVD case uses alarming treatment language")
        finding.coherence_score -= 25

    if "statin" in visible_lower or "lipid-lowering therapy" in visible_lower:
        rationale_present = any(
            condition
            for condition in (
                cac is not None and cac > 0,
                ldl is not None and ldl >= 160,
                getattr(patient, "apob", None) is not None and patient.apob >= 100,
                prevent_10y is not None and prevent_10y >= 3,
                prevent_30y is not None and prevent_30y >= 10,
                bool(getattr(patient, "diabetes", False)),
                bool(getattr(patient, "clinical_ascvd", False)),
                bool(getattr(patient, "family_history_premature_ascvd", False)),
            )
        )
        if not rationale_present:
            finding.warnings.append("lipid/statin recommendation lacks an obvious demo rationale")
            finding.coherence_score -= 10
        if (
            prevent_10y is not None
            and 3 <= prevent_10y < 5
            and not any(
                condition
                for condition in (
                    getattr(patient, "cac", None) is not None and patient.cac > 0,
                    getattr(patient, "uacr", None) is not None and patient.uacr >= 30,
                    getattr(patient, "egfr", None) is not None and patient.egfr < 60,
                    getattr(patient, "ldl_c", None) is not None and patient.ldl_c >= 160,
                    getattr(patient, "apob", None) is not None and patient.apob >= 120,
                    bool(getattr(patient, "diabetes", False)),
                    bool(getattr(patient, "family_history_premature_ascvd", False)),
                )
            )
            and any(phrase in visible_lower for phrase in ("statin therapy is reasonable", "statin therapy is generally favored", "recommended"))
        ):
            finding.errors.append("3% to <5% ASCVD demo recommends statin too aggressively without major enhancers")
            finding.coherence_score -= 25
    if (
        prevent_10y is not None
        and prevent_10y >= 5
        and any(
            condition
            for condition in (
                getattr(patient, "uacr", None) is not None and patient.uacr >= 30,
                getattr(patient, "egfr", None) is not None and patient.egfr < 60,
                getattr(patient, "ldl_c", None) is not None and patient.ldl_c >= 130,
                getattr(patient, "apob", None) is not None and patient.apob >= 100,
                bool(getattr(patient, "diabetes", False)),
                bool(getattr(patient, "family_history_premature_ascvd", False)),
            )
        )
        and "statin" not in visible_lower
        and "lipid-lowering" not in visible_lower
    ):
        finding.errors.append("ASCVD >=5% with risk enhancers lacks lipid-prevention discussion")
        finding.coherence_score -= 25

    if any(fragment in visible_lower for fragment in ("dominant_action", "action_domains")):
        finding.errors.append("internal engine field leaked into visible output")
        finding.patient_readability_score -= 30

    if len(rss_contributions) == 0 and case_name not in {"healthy_low_risk_prevention"}:
        finding.warnings.append("demo has no RSS point contributors")
        finding.showcase_value_score -= 12
    if rss_total == 0 and case_name not in {"healthy_low_risk_prevention"}:
        finding.warnings.append("demo may feel visually underwhelming: RSS is 0")
        finding.showcase_value_score -= 12

    for concept in finding.showcase_concepts:
        concept_terms = SHOWCASE_TERMS.get(concept, (concept.lower(),))
        if not any(term in visible_lower for term in concept_terms):
            finding.suggestions.append(f"showcase concept may be too subtle: {concept}")
            finding.showcase_value_score -= 6

    if case_name == "younger_strong_family_history":
        if getattr(result, "prevent_10y_ascvd", None) is not None and result.prevent_10y_ascvd >= 3:
            finding.errors.append("younger family-history demo is not low short-term ASCVD risk")
            finding.coherence_score -= 25
        required = (
            "Level 3B - elevated lifetime cardiometabolic risk despite low short-term event risk",
            "Risk context: premature family history of ASCVD (Father MI age 49).",
            AGE_AWARE_CAC_LINE,
        )
        for phrase in required:
            if phrase not in visible:
                finding.errors.append(f"younger family-history output missing `{phrase}`")
                finding.coherence_score -= 15
        if not any(phrase in visible_lower for phrase in ("low short-term", "longer-term", "lifetime", "prevention opportunity")):
            finding.errors.append("younger family-history output does not explain low 10-year/high lifetime framing")
            finding.coherence_score -= 15

    _score_floor(finding)
    return finding


def validate_demo_case(case) -> DemoCaseAudit:
    """Validate a demo tuple, case name, or mapping and return structured findings."""
    if isinstance(case, tuple) and len(case) == 2:
        return audit_demo_case(str(case[0]), str(case[1]))
    if isinstance(case, str):
        label = next((label for label, name in DEMO_CASES if name == case), case)
        return audit_demo_case(label, case)
    if isinstance(case, dict):
        case_name = str(case.get("case_name") or case.get("name") or "")
        label = str(case.get("label") or case_name)
        return audit_demo_case(label, case_name)
    raise TypeError(f"Unsupported demo case reference: {case!r}")


def audit_demo_cases() -> DemoAuditReport:
    """Run the demo coherence audit across all configured in-app cases."""
    return DemoAuditReport(
        cases=[audit_demo_case(label, case_name) for label, case_name in DEMO_CASES]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit RCCKM demo case quality.")
    parser.add_argument(
        "--strict-warnings",
        action="store_true",
        help="Return a nonzero exit code when warnings are present.",
    )
    parser.add_argument(
        "--no-strict",
        action="store_true",
        help="Disable STRICT_MODE error exit while drafting demo cases.",
    )
    args = parser.parse_args(argv)

    report = audit_demo_cases()
    print(report.format_summary())
    strict = STRICT_MODE and not args.no_strict
    if (strict and report.errors) or (args.strict_warnings and report.warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
