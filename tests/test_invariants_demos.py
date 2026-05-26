from __future__ import annotations

import pytest

from tests.helpers import (
    assert_absent,
    assert_demo_baseline_complete,
    assert_no_contradictions,
    assert_risk_labels_valid,
)
from tools.demo_audit import audit_demo_cases, validate_demo_case
from ui.demo_case_gallery import DEMO_CASES, DEMO_PATIENTS, demo_case_description


DEMO_FORBIDDEN_FRAGMENTS = (
    "total cardiovascular risk",
    "heart failure risk",
    "hsCRP - inflammatory residual risk",
    "hsCRP - inflammatory biomarker clarification",
    "dominant_action",
    "action_domains",
    "risk_continuum_sublevel",
)


@pytest.mark.parametrize("label,case_name", DEMO_CASES)
def test_every_demo_has_realistic_primary_care_baseline(label, case_name):
    assert_demo_baseline_complete(case_name)
    payload = DEMO_PATIENTS[case_name]
    assert payload.get("smoker") is not None, f"{label} should state smoking status"
    assert payload.get("diabetes") is not None or payload.get("a1c") is not None
    assert payload.get("medications_raw") not in (None, "")
    assert payload.get("egfr") is not None or payload.get("creatinine") is not None


@pytest.mark.parametrize("label,case_name", DEMO_CASES)
def test_demo_selector_copy_is_present_and_not_overstated(label, case_name):
    description = demo_case_description(case_name)
    assert description
    assert len(description) <= 180
    if "low risk" in label.lower():
        assert "very high" not in description.lower()


@pytest.mark.parametrize("label,case_name", DEMO_CASES)
def test_each_demo_passes_structured_coherence_audit(label, case_name):
    finding = validate_demo_case((label, case_name))
    assert not finding.errors, "\n".join(finding.errors)
    assert finding.completeness_score >= 90
    assert finding.coherence_score >= 90
    assert finding.patient_readability_score >= 90
    assert finding.showcase_value_score >= 75


def test_demo_audit_report_has_no_strict_failures():
    report = audit_demo_cases()
    assert not report.errors, report.format_summary()
    assert all(case.overall_score >= 85 for case in report.cases)


@pytest.mark.parametrize("label,case_name", DEMO_CASES)
def test_demo_outputs_are_complete_and_safe(label, case_name):
    from tools.demo_audit import render_demo_output_snapshot

    text = render_demo_output_snapshot(case_name)
    assert "EMR:" in text
    assert "PATIENT ROADMAP:" in text
    assert "ACTIONS:" in text
    assert "Assessment:" in text
    assert "Recommendations:" in text
    assert "Where you stand" in text
    assert "Next steps" in text
    assert_absent(text, DEMO_FORBIDDEN_FRAGMENTS)
    assert "{{" not in text and "}}" not in text
    assert " None " not in f" {text} "
    assert " null " not in f" {text.lower()} "
    assert " nan " not in f" {text.lower()} "
    assert_no_contradictions(text)
    assert_risk_labels_valid(text)


def test_younger_family_history_demo_uses_low_short_term_prevention_framing():
    from tools.demo_audit import render_demo_output_snapshot

    text = render_demo_output_snapshot("younger_strong_family_history")
    lowered = text.lower()
    assert "10-year ascvd risk" in lowered
    assert "30-year ascvd risk" in lowered
    assert "father mi age 49" in lowered
    assert "low short-term" in lowered or "prevention opportunity" in lowered
    assert "cac not routinely recommended at this age" in lowered
    assert "very high risk" not in lowered
    assert "total cardiovascular risk" not in lowered
