from modules.prevent.full_equation import (
    adjust_uacr,
    mmol_conversion,
    prevent10_total_and_ascvd,
    sdi_to_decile,
    sdicat,
)


def test_prevent_helpers():
    assert round(mmol_conversion(200), 4) == 5.172
    assert adjust_uacr(-4) == 0.1
    assert sdicat(2) == 0
    assert sdicat(5) == 1
    assert sdicat(9) == 2
    assert sdi_to_decile(1) == 1
    assert sdi_to_decile(100) == 10
    assert sdi_to_decile("not-a-number") is None


def test_prevent_returns_missing_inputs_when_required_fields_absent():
    trace = []

    result = prevent10_total_and_ascvd({"age": 55, "sex": "female"}, trace)

    assert result["total_cvd_10y_pct"] is None
    assert result["ascvd_10y_pct"] is None
    assert result["total_cvd_30y_pct"] is None
    assert result["ascvd_30y_pct"] is None
    assert "tc" in result["missing"]
    assert trace[0]["event"] == "PREVENT_missing_inputs"


def test_prevent_returns_none_when_age_out_of_range():
    trace = []
    patient = {
        "age": 29,
        "sex": "female",
        "tc": 200,
        "hdl": 50,
        "sbp": 130,
        "bp_treated": False,
        "smoking": False,
        "diabetes": False,
        "bmi": 30,
        "egfr": 90,
        "lipid_lowering": False,
    }

    result = prevent10_total_and_ascvd(patient, trace)

    assert result["total_cvd_10y_pct"] is None
    assert result["ascvd_10y_pct"] is None
    assert result["total_cvd_30y_pct"] is None
    assert result["ascvd_30y_pct"] is None
    assert result["notes"] == "PREVENT validated for ages 30-79."
    assert trace[0]["event"] == "PREVENT_age_out_of_range"


def test_prevent_baseline_female_known_output():
    patient = {
        "age": 55,
        "sex": "female",
        "tc": 200,
        "hdl": 50,
        "sbp": 130,
        "bp_treated": False,
        "smoking": False,
        "diabetes": False,
        "bmi": 30,
        "egfr": 90,
        "lipid_lowering": False,
    }

    result = prevent10_total_and_ascvd(patient)

    assert result["total_cvd_10y_pct"] == 2.52
    assert result["ascvd_10y_pct"] == 1.62
    assert result["total_cvd_30y_pct"] is None
    assert result["ascvd_30y_pct"] is None
    assert result["missing"] == []
    assert result["notes"] == "PREVENT (population model)."


def test_prevent_male_with_optional_uacr_hba1c_sdi_known_output():
    trace = []
    patient = {
        "age": 60,
        "sex": "male",
        "tc": 210,
        "hdl": 45,
        "sbp": 140,
        "bp_treated": True,
        "smoking": True,
        "diabetes": True,
        "bmi": 32,
        "egfr": 55,
        "lipid_lowering": True,
        "uacr": 45,
        "a1c": 7.1,
        "sdi": 5,
        "_statin_source": "medication_list",
    }

    result = prevent10_total_and_ascvd(patient, trace)

    assert result["total_cvd_10y_pct"] == 33.16
    assert result["ascvd_10y_pct"] == 18.08
    assert result["statin_used"] is True
    assert result["statin_source"] == "medication_list"
    assert trace[-1]["event"] == "PREVENT_calculated"
    assert trace[-1]["value"]["uacr"] is True
    assert trace[-1]["value"]["hba1c"] is True
    assert trace[-1]["value"]["sdi"] is True


def test_prevent_ignores_invalid_optional_inputs():
    trace = []
    patient = {
        "age": 55,
        "sex": "female",
        "tc": 200,
        "hdl": 50,
        "sbp": 130,
        "bp_treated": False,
        "smoking": False,
        "diabetes": False,
        "bmi": 30,
        "egfr": 90,
        "lipid_lowering": False,
        "uacr": -5,
        "hba1c": -1,
        "sdi": 11,
    }

    result = prevent10_total_and_ascvd(patient, trace)

    assert result["total_cvd_10y_pct"] is not None
    assert [entry["event"] for entry in trace[:2]] == [
        "PREVENT_uacr_invalid",
        "PREVENT_hba1c_invalid",
    ]
