import json
from pathlib import Path

import pytest

from core.engine import evaluate_patient
from core.patient import Patient
from modules.levels.definitions import classify_continuum_position
from modules.rss.engine import build_rss_contributions, calculate_rss_total
from renderers.emr_renderer import render_emr_note
from renderers.patient_roadmap import render_patient_roadmap_text
from renderers.rss_renderer import rss_interpretation
from tests.helpers import assert_absent, assert_present, render_all_outputs


GOLDEN_CASES_PATH = Path(__file__).with_name("golden_cases.json")


def _text(value):
    return str(getattr(value, "value", value) or "")


def _contains_any(haystack, needle):
    if needle is None:
        return True
    needle = str(needle).lower()
    return any(needle in str(item).lower() for item in haystack)


def _expected_values(value):
    if value is None:
        return None
    if isinstance(value, list):
        return set(value)
    return {value}


def _evaluate(patient_dict):
    patient = Patient(**patient_dict)
    result = evaluate_patient(patient)
    result._golden_position = classify_continuum_position(patient, result)
    rss_total = calculate_rss_total(build_rss_contributions(patient, result))
    result._golden_rss_total = rss_total
    result._golden_rss_category = rss_interpretation(rss_total)
    result._golden_emr = render_emr_note(patient, result)
    result._golden_roadmap_text = render_patient_roadmap_text(patient, result)
    return patient, result


def _diagnosis_names(result):
    return [
        candidate.name
        for candidate in getattr(result, "diagnosis_candidates", []) or []
    ]


def _actions(result):
    return [
        getattr(result, "dominant_action", None),
        *(getattr(result, "recommendations", []) or []),
    ]


def _clarifier_text(result):
    clarification = getattr(result, "clarification", None) or {}
    action_domains = getattr(result, "action_domains", None) or {}
    return [
        clarification.get("summary", ""),
        *(clarification.get("reasons", []) or []),
        *action_domains.keys(),
        *action_domains.values(),
    ]


def _discordance_text(result):
    discordance = getattr(result, "discordance_insight", None) or {}
    return list(discordance.values())


def _target(result):
    targets = getattr(result, "targets", []) or []
    return targets[0] if targets else None


def _combined_visible_text(result):
    return "\n".join(
        [
            result._golden_emr,
            result._golden_roadmap_text,
            "\n".join(_actions(result)),
            "\n".join(getattr(result, "top_drivers", []) or []),
            "\n".join(_diagnosis_names(result)),
        ]
    )


def _assert_section_phrases(outputs, case):
    section_map = {
        "emr": "emr",
        "roadmap": "roadmap",
        "action": "actions",
        "diagnosis": "diagnoses",
    }
    for prefix, output_key in section_map.items():
        assert_present(outputs[output_key], case.get(f"{prefix}_required_phrases", []))
        assert_absent(outputs[output_key], case.get(f"{prefix}_forbidden_phrases", []))


def _assert_in_expected(actual, expected):
    allowed = _expected_values(expected)
    if allowed is None:
        return
    assert actual in allowed


def _load_cases():
    return json.loads(GOLDEN_CASES_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", _load_cases(), ids=lambda case: case["name"])
def test_golden_clinical_cases(case):
    patient, result = _evaluate(case["patient"])
    expected = case.get("expected", {})
    outputs = render_all_outputs(patient, result)

    _assert_in_expected(
        result._golden_position.get("level"),
        expected.get("risk_continuum_level"),
    )
    _assert_in_expected(
        result._golden_position.get("sublevel"),
        expected.get("risk_continuum_sublevel"),
    )

    ckm_stage = getattr(result, "ckm_stage", None) or {}
    _assert_in_expected(ckm_stage.get("stage"), expected.get("ckm_stage"))
    _assert_in_expected(getattr(result, "kdigo_stage", None), expected.get("kdigo"))
    _assert_in_expected(result._golden_rss_category, expected.get("rss_category"))
    _assert_in_expected(
        _text(getattr(result, "prevent_risk_category", None)),
        expected.get("prevent_category"),
    )

    assert _contains_any(
        getattr(result, "top_drivers", []) or [],
        expected.get("required_driver"),
    )
    assert _contains_any(_diagnosis_names(result), expected.get("required_diagnosis"))
    assert _contains_any(_actions(result), expected.get("required_action"))
    assert _contains_any(_clarifier_text(result), expected.get("required_clarifier"))
    assert _contains_any(
        _discordance_text(result),
        expected.get("required_discordance"),
    )

    forbidden_diagnosis = expected.get("forbidden_diagnosis")
    if forbidden_diagnosis:
        assert not _contains_any(_diagnosis_names(result), forbidden_diagnosis)

    target = _target(result)
    if expected.get("target_ldl") is not None:
        assert target is not None
        assert target.ldl_c_target == expected["target_ldl"]
    if expected.get("target_non_hdl") is not None:
        assert target is not None
        assert target.non_hdl_c_target == expected["target_non_hdl"]

    visible = _combined_visible_text(result)
    for phrase in case.get("required_phrases", []):
        assert phrase.lower() in visible.lower()
    for phrase in case.get("forbidden_phrases", []):
        assert phrase.lower() not in visible.lower()
    _assert_section_phrases(outputs, case)
