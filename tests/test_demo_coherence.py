from __future__ import annotations

from rcckm.governance import audit_result
from tests.helpers import render_all_outputs
from tools.demo_audit import audit_demo_cases, validate_demo_case
from ui.demo_case_gallery import DEMO_CASES, DEMO_PATIENTS, build_demo_patient
from ui.report_layout import run_patient


MANDATORY_BASELINE = {
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
}


def test_every_demo_has_primary_care_baseline_data():
    for _label, case_name in DEMO_CASES:
        payload = DEMO_PATIENTS[case_name]
        missing = sorted(field for field in MANDATORY_BASELINE if payload.get(field) in (None, ""))
        assert not missing, f"{case_name} missing {missing}"


def test_demo_audit_strict_mode_passes_all_current_demos():
    report = audit_demo_cases()
    assert not report.errors, report.format_summary()
    for case in report.cases:
        assert case.completeness_score >= 80
        assert case.coherence_score >= 80
        assert case.patient_readability_score >= 80
        assert case.showcase_value_score >= 70


def test_validate_demo_case_returns_structured_scores_and_findings():
    finding = validate_demo_case("younger_strong_family_history")
    assert finding.case_name == "younger_strong_family_history"
    assert finding.completeness_score >= 80
    assert finding.coherence_score >= 80
    assert "premature family history" in finding.showcase_concepts


def test_demo_outputs_pass_governance_safety_and_traceability():
    for _label, case_name in DEMO_CASES:
        patient = build_demo_patient(case_name)
        result, _rss_total, _rss_contributions = run_patient(patient)
        outputs = render_all_outputs(patient, result)
        audit = audit_result(patient, result, outputs["visible"])
        assert audit.passed, f"{case_name}: {[finding.message for finding in audit.errors]}"
        assert audit.traces

