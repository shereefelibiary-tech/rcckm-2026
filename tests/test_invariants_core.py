from __future__ import annotations

import dataclasses
import json

from core.patient import Patient
from rcckm.governance import audit_result
from tests.helpers import assert_no_contradictions, render_all_outputs, render_case_output


def test_engine_output_is_deterministic_for_same_inputs():
    patient = Patient(
        age=57,
        sex="male",
        tc=202,
        ldl_c=126,
        hdl_c=46,
        triglycerides=150,
        egfr=64,
        uacr=48,
        prevent_10y_ascvd=6.65,
        prevent_30y_ascvd=26.07,
    )
    first = render_case_output(patient)
    second = render_case_output(patient)
    assert first["outputs"]["emr"] == second["outputs"]["emr"]
    assert first["outputs"]["roadmap"] == second["outputs"]["roadmap"]
    assert first["outputs"]["actions"] == second["outputs"]["actions"]
    assert getattr(first["result"], "risk_level", None) == getattr(second["result"], "risk_level", None)


def test_renderers_do_not_mutate_engine_action_domains():
    bundle = render_case_output(Patient(age=60, sex="female", diabetes=True, egfr=52, uacr=210, ldl_c=132))
    result = bundle["result"]
    before = dict(getattr(result, "action_domains", {}) or {})
    render_all_outputs(bundle["patient"], result)
    after = dict(getattr(result, "action_domains", {}) or {})
    assert before == after


def test_major_recommendations_have_rule_trace_metadata():
    bundle = render_case_output(Patient(age=60, sex="female", diabetes=True, egfr=52, uacr=210, ldl_c=132))
    audit = audit_result(bundle["patient"], bundle["result"], bundle["outputs"]["visible"])
    assert not audit.errors, [finding.message for finding in audit.errors]
    assert audit.traces
    for trace in audit.traces:
        assert trace.recommendation_id
        assert trace.rule_id
        assert trace.domain
        assert trace.evidence_basis
        assert trace.strength_language in {"recommended", "reasonable", "consider", "continue", "defer"}


def test_engine_result_is_serializable_enough_for_validation_artifacts():
    bundle = render_case_output(Patient(age=50, sex="male", ldl_c=204, tc=280, hdl_c=45, triglycerides=150))
    result = bundle["result"]
    payload = dataclasses.asdict(result) if dataclasses.is_dataclass(result) else dict(result.__dict__)
    json.dumps(payload, default=str)


def test_combined_output_has_no_core_contradictions_or_internal_variable_leaks():
    bundle = render_case_output(Patient(age=61, sex="female", cac=350, ldl_c=124, tc=218, hdl_c=56, triglycerides=190))
    text = bundle["outputs"]["visible"]
    assert_no_contradictions(text)
    for forbidden in ("dominant_action", "action_domains", "risk_continuum_sublevel", "None", "null", "NaN"):
        assert forbidden not in text
