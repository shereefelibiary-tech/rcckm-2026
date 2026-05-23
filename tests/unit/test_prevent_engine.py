from modules.prevent.engine import classify_prevent_ascvd_risk
from modules.prevent.calculator import (
    calculate_prevent_ascvd_10y,
    calculate_prevent_summary,
)
from core.enums import RiskLevel
from core.patient import Patient


def test_calculate_prevent_ascvd_10y_returns_none_when_missing():
    patient = Patient(age=60, sex="male")

    assert calculate_prevent_ascvd_10y(patient) is None


def test_calculate_prevent_ascvd_10y_returns_placeholder_value():
    patient = Patient(age=60, sex="male", prevent_10y_ascvd=5.0)

    assert calculate_prevent_ascvd_10y(patient) == 5.0


def _valid_prevent_patient(**overrides):
    values = {
        "age": 55,
        "sex": "female",
        "tc": 200,
        "hdl_c": 50,
        "sbp": 130,
        "bp_treated": False,
        "smoker": False,
        "diabetes": False,
        "bmi": 30,
        "egfr": 90,
        "lipid_lowering": False,
    }
    values.update(overrides)
    return Patient(**values)


def test_prevent_summary_reports_missing_sbp():
    patient = _valid_prevent_patient(sbp=None)

    summary = calculate_prevent_summary(patient)

    assert summary["available"] is False
    assert "systolic BP" in summary["missing_inputs"]
    assert summary["prevent_10y_ascvd"] is None


def test_prevent_summary_reports_missing_smoking_status():
    patient = _valid_prevent_patient(smoker=None, smoking=None)

    summary = calculate_prevent_summary(patient)

    assert summary["available"] is False
    assert "smoking status" in summary["missing_inputs"]


def test_prevent_summary_reports_unsupported_age():
    patient = _valid_prevent_patient(age=82)

    summary = calculate_prevent_summary(patient)

    assert summary["available"] is False
    assert summary["missing_inputs"] == []
    assert summary["unsupported_reason"] == "PREVENT is validated for ages 30-79."


def test_prevent_summary_calculates_valid_10_year_and_explains_missing_30_year():
    patient = _valid_prevent_patient(age=60)

    summary = calculate_prevent_summary(patient)

    assert summary["available"] is True
    assert summary["prevent_10y_ascvd"] is not None
    assert summary["prevent_10y_total_cvd"] is not None
    assert summary["prevent_30y_ascvd"] is None
    assert summary["unsupported_reason"] == (
        "30-year PREVENT is only available for ages 30-59."
    )
    assert "30-year PREVENT is only available for ages 30-59." in summary["warnings"]


def test_prevent_summary_calculates_valid_30_year_for_age_45_complete_inputs():
    patient = _valid_prevent_patient(age=45)

    summary = calculate_prevent_summary(patient)

    assert summary["available"] is True
    assert summary["prevent_10y_ascvd"] is not None
    assert summary["prevent_10y_total_cvd"] is not None
    assert summary["prevent_30y_ascvd"] is not None
    assert summary["prevent_30y_total_cvd"] is not None
    assert summary["unsupported_reason"] is None


def test_prevent_summary_fills_30_year_when_explicit_10_year_and_inputs_complete():
    patient = _valid_prevent_patient(age=45, prevent_10y_ascvd=8.2)

    summary = calculate_prevent_summary(patient)

    assert summary["available"] is True
    assert summary["prevent_10y_ascvd"] == 8.2
    assert summary["prevent_30y_ascvd"] is not None
    assert summary["prevent_30y_total_cvd"] is not None


def test_prevent_summary_debug_payload_exposes_official_missing_inputs_for_partial_override():
    patient = _valid_prevent_patient(
        age=60,
        prevent_10y_ascvd=8.2,
        tc=None,
        hdl_c=None,
        sbp=None,
        bmi=None,
    )

    summary = calculate_prevent_summary(patient)

    assert summary["prevent_10y_ascvd"] == 8.2
    assert summary["prevent_30y_ascvd"] is None
    assert "total cholesterol" in summary["missing_inputs"]
    assert "HDL-C" in summary["missing_inputs"]
    assert summary["unsupported_reason"] == "30-year PREVENT is only available for ages 30-59."


def test_prevent_summary_preserves_explicit_10_and_30_year_values():
    patient = _valid_prevent_patient(
        prevent_10y_ascvd=8.2,
        prevent_10y_total_cvd=12.4,
        prevent_30y_ascvd=24.5,
        prevent_30y_total_cvd=31.2,
    )

    summary = calculate_prevent_summary(patient)

    assert summary["available"] is True
    assert summary["prevent_10y_ascvd"] == 8.2
    assert summary["prevent_10y_total_cvd"] == 12.4
    assert summary["prevent_30y_ascvd"] == 24.5
    assert summary["prevent_30y_total_cvd"] == 31.2


def test_classify_prevent_ascvd_risk_none_and_boundaries():
    assert classify_prevent_ascvd_risk(None) is None

    assert classify_prevent_ascvd_risk(2.99) == RiskLevel.LOW
    assert classify_prevent_ascvd_risk(3.0) == RiskLevel.BORDERLINE
    assert classify_prevent_ascvd_risk(4.99) == RiskLevel.BORDERLINE
    assert classify_prevent_ascvd_risk(5.0) == RiskLevel.INTERMEDIATE
    assert classify_prevent_ascvd_risk(9.99) == RiskLevel.INTERMEDIATE
    assert classify_prevent_ascvd_risk(10.0) == RiskLevel.HIGH
