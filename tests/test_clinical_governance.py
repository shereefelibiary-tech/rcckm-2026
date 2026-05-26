from __future__ import annotations

from core.patient import Patient
from core.engine import evaluate_patient
from rcckm.governance import audit_result
from rcckm.rule_trace import build_rule_traces
from tests.helpers import render_all_outputs


def _audit(patient_dict):
    patient = Patient(**patient_dict)
    result = evaluate_patient(patient)
    outputs = render_all_outputs(patient, result)
    return patient, result, outputs, audit_result(patient, result, outputs["visible"])


def test_major_recommendations_have_structured_rule_traces():
    patient, result, _outputs, audit = _audit(
        {
            "age": 57,
            "sex": "male",
            "prevent_10y_ascvd": 6.65,
            "prevent_30y_ascvd": 26.07,
            "ldl_c": 126,
            "triglycerides": 150,
            "a1c": 6.0,
            "egfr": 76,
            "uacr": 62,
            "sbp": 142,
            "dbp": 86,
            "bp_treated": True,
        }
    )

    traces = build_rule_traces(patient, result)
    assert traces
    assert {trace.domain for trace in traces} >= {"lipid", "kidney", "BP", "diagnostics"}
    for trace in traces:
        assert trace.recommendation_id
        assert trace.recommendation_text
        assert trace.triggering_inputs
        assert trace.rule_id
        assert trace.evidence_basis
        assert trace.strength_language in {
            "recommended",
            "reasonable",
            "consider",
            "continue",
            "defer",
        }
        assert isinstance(trace.missing_data_that_could_change_decision, list)
        assert isinstance(trace.patient_facing_allowed, bool)
        assert isinstance(trace.emr_allowed, bool)
    assert audit.passed


def test_rule_trace_captures_lipid_and_kidney_specific_rules():
    patient, result, _outputs, audit = _audit(
        {
            "age": 55,
            "sex": "male",
            "egfr": 55,
            "uacr": 250,
            "diabetes": True,
            "a1c": 7.1,
        }
    )
    traces = build_rule_traces(patient, result)
    rule_ids = {trace.rule_id for trace in traces}

    assert "kidney_albuminuria_confirm_persistence" in rule_ids
    assert "kidney_sglt2_uacr_ge_200_egfr_ge_20" in rule_ids
    sglt2_trace = next(trace for trace in traces if trace.rule_id == "kidney_sglt2_uacr_ge_200_egfr_ge_20")
    assert sglt2_trace.triggering_inputs["uacr"] == 250
    assert "eGFR >=20" in sglt2_trace.evidence_basis


def test_rule_trace_captures_severe_ldl_pathway():
    patient, result, _outputs, audit = _audit(
        {"age": 55, "sex": "male", "ldl_c": 204, "cac": 0, "egfr": 80, "uacr": 8}
    )
    traces = build_rule_traces(patient, result)
    lipid_trace = next(trace for trace in traces if trace.rule_id == "prevent_lipid_ldl_190_override")
    assert lipid_trace.triggering_inputs["ldl_c"] == 204
    assert "PREVENT" in lipid_trace.evidence_basis
    assert audit.passed


def test_rule_trace_captures_low_10yr_high_30yr_lipid_context():
    patient, result, _outputs, audit = _audit(
        {
            "age": 38,
            "sex": "male",
            "tc": 220,
            "ldl_c": 154,
            "hdl_c": 46,
            "triglycerides": 165,
            "apob": 112,
            "family_history_premature_ascvd": True,
            "prevent_10y_ascvd": 3.8,
            "prevent_30y_ascvd": 24.0,
        }
    )
    traces = build_rule_traces(patient, result)
    lipid_trace = next(
        trace for trace in traces if trace.rule_id == "prevent_lipid_10yr_3to5_30yr_elevated_with_enhancer"
    )
    inputs = lipid_trace.triggering_inputs
    assert inputs["risk_10yr_ascvd"] == 3.8
    assert inputs["risk_30yr_ascvd"] == 24.0
    assert inputs["age"] == 38
    assert inputs["prevent_10yr_lipid_band"] == "early_discussion_3_to_lt_5"
    assert inputs["prevent_30yr_band"] == "elevated_15_to_lt_30"
    assert "premature_family_history" in inputs["enhancers_present"]
    assert inputs["recommendation_strength"] == "may_be_reasonable"
    assert audit.passed


def test_governance_flags_unsafe_or_overbroad_wording():
    patient = Patient(age=55, sex="male", prevent_10y_ascvd=6.0, ldl_c=160)
    result = evaluate_patient(patient)
    bad_text = (
        "10-year ASCVD risk 6%. Total cardiovascular risk is used for statin thresholds. "
        "No medication escalation today. Moderate-intensity statin therapy is reasonable. "
        "hsCRP - inflammatory residual risk."
    )

    findings = audit_result(patient, result, bad_text).findings
    messages = " ".join(finding.message for finding in findings)
    assert "total cardiovascular risk" in messages
    assert "No medication escalation" in messages
    assert "hsCRP - inflammatory residual risk" in messages


def test_current_representative_outputs_pass_governance_safety():
    for patient_dict in (
        {"age": 60, "sex": "male", "cac": 350, "ldl_c": 124},
        {"age": 65, "sex": "female", "clinical_ascvd": True, "cac": 0, "ldl_c": 120},
        {"age": 50, "sex": "male", "triglycerides": 1000, "tc": 286, "hdl_c": 32},
        {"age": 55, "sex": "female", "egfr": 76, "uacr": 45, "sbp": 138, "dbp": 84, "bp_treated": True},
    ):
        patient, result, _outputs, audit = _audit(patient_dict)
        assert audit.passed, [finding.message for finding in audit.errors]
