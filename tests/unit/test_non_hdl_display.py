from core.patient import Patient
from core.results import RCCKMResult, TargetResult
from modules.lipids.non_hdl import (
    calculate_non_hdl,
    format_non_hdl_display,
    should_show_non_hdl_default,
)
from renderers.patient_roadmap import render_patient_roadmap_text
from ui.report_layout import _build_targets_html


def _result(non_hdl_target=130):
    return RCCKMResult(
        targets=[
            TargetResult(
                ldl_c_target=100,
                non_hdl_c_target=non_hdl_target,
                apob_target=90,
            )
        ]
    )


def test_calculate_non_hdl_uses_total_cholesterol_minus_hdl():
    assert calculate_non_hdl(205, 48) == 157
    assert calculate_non_hdl("205", "48") == 157
    assert calculate_non_hdl(None, 48) is None
    assert calculate_non_hdl(205, None) is None
    assert calculate_non_hdl(40, 48) is None
    assert calculate_non_hdl("bad", 48) is None


def test_non_hdl_hidden_by_default_in_routine_case_with_apob_and_normal_tg():
    patient = Patient(
        age=52,
        sex="female",
        tc=180,
        hdl_c=55,
        ldl_c=105,
        triglycerides=95,
        apob=78,
    )
    result = _result()

    assert should_show_non_hdl_default(patient, result) is False
    assert "non-HDL-C" not in _build_targets_html(result, patient)
    assert "non-HDL-C" not in render_patient_roadmap_text(patient, result)


def test_non_hdl_available_but_not_default_when_tg_mildly_elevated_and_apob_present():
    patient = Patient(
        age=52,
        sex="female",
        tc=205,
        hdl_c=48,
        ldl_c=125,
        triglycerides=180,
        apob=90,
    )
    result = _result()

    payload = format_non_hdl_display(patient, result)
    assert should_show_non_hdl_default(patient, result) is True
    assert payload["current_value"] == 157
    assert payload["target_value"] == 130
    html = _build_targets_html(result, patient)
    assert "LDL-C" in html
    assert "ApoB" in html
    assert "non-HDL-C" not in html
    assert "Current 157" not in html
    assert "Calculated from total cholesterol minus HDL-C." not in html


def test_non_hdl_shown_when_apob_missing_and_calculable():
    patient = Patient(
        age=52,
        sex="female",
        tc=205,
        hdl_c=48,
        ldl_c=125,
        triglycerides=110,
        apob=None,
    )

    assert should_show_non_hdl_default(patient, _result()) is True
    assert "non-HDL-C" in _build_targets_html(_result(), patient)
    assert "target-secondary" in _build_targets_html(_result(), patient)


def test_non_hdl_not_shown_without_source_lipid_values_or_target():
    missing_tc = Patient(age=52, sex="female", hdl_c=48, triglycerides=180, apob=None)
    missing_hdl = Patient(age=52, sex="female", tc=205, triglycerides=180, apob=None)
    no_target = _result(non_hdl_target=None)
    patient = Patient(age=52, sex="female", tc=205, hdl_c=48, triglycerides=180, apob=None)

    assert should_show_non_hdl_default(missing_tc, _result()) is False
    assert should_show_non_hdl_default(missing_hdl, _result()) is False
    assert should_show_non_hdl_default(patient, no_target) is False
    assert "non-HDL-C" not in _build_targets_html(no_target, patient)


def test_clinician_detail_mode_can_show_non_hdl_when_otherwise_hidden():
    patient = Patient(
        age=52,
        sex="female",
        tc=180,
        hdl_c=55,
        ldl_c=105,
        triglycerides=95,
        apob=78,
    )
    result = _result()

    assert should_show_non_hdl_default(patient, result) is False
    assert should_show_non_hdl_default(patient, result, {"clinician_detail_mode": True}) is True
    html = _build_targets_html(result, patient, clinician_detail_mode=True)
    assert "LDL-C" in html
    assert "ApoB" in html
    assert "non-HDL-C" in html
    assert "target-secondary" in html
