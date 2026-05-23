import pandas as pd

from core.patient import Patient
from modules.prevent.official import COEFF_DIR, calculate_prevent


def _patient(**overrides):
    values = {
        "age": 45,
        "sex": "male",
        "tc": 200,
        "hdl_c": 50,
        "sbp": 130,
        "bp_treated": False,
        "lipid_lowering": False,
        "diabetes": False,
        "smoker": False,
        "bmi": 30,
        "egfr": 90,
    }
    values.update(overrides)
    return Patient(**values)


def test_official_prevent_age_45_has_10_30_and_5_year_outputs():
    result = calculate_prevent(_patient(age=45), model="base")

    assert result["available"] is True
    assert result["model_used"] == "base"
    assert result["prevent_10y_ascvd"] is not None
    assert result["prevent_10y_total_cvd"] is not None
    assert result["prevent_10y_hf"] is not None
    assert result["prevent_10y_chd"] is not None
    assert result["prevent_10y_stroke"] is not None
    assert result["prevent_30y_ascvd"] is not None
    assert result["prevent_30y_total_cvd"] is not None
    assert result["prevent_5y_ascvd"] is not None
    assert result["prevent_age"] is None
    assert result["prevent_percentile"] is None


def test_official_prevent_age_60_has_10_year_but_no_30_year():
    result = calculate_prevent(_patient(age=60), model="base")

    assert result["available"] is True
    assert result["prevent_10y_ascvd"] is not None
    assert result["prevent_30y_ascvd"] is None
    assert result["unavailable_reason"] == (
        "30-year PREVENT is only available for ages 30-59."
    )


def test_official_prevent_reports_missing_inputs():
    result = calculate_prevent(_patient(sbp=None, smoker=None, smoking=None), model="base")

    assert result["available"] is False
    assert "systolic BP" in result["missing_inputs"]
    assert "smoking status" in result["missing_inputs"]


def test_official_prevent_selects_full_when_all_enhancers_available():
    result = calculate_prevent(
        {
            "age": 45,
            "sex": "male",
            "tc": 200,
            "hdl": 50,
            "sbp": 130,
            "bptreat": False,
            "statin": False,
            "dm": False,
            "smoke": False,
            "bmi": 30,
            "egfr": 90,
            "uacr": 45,
            "hba1c": 7.1,
            "sdi": 5,
        },
        model="best_available",
    )

    assert result["available"] is True
    assert result["model_used"] == "full"
    assert result["prevent_10y_ascvd"] is not None


def test_official_prevent_known_base_example_outputs_from_aha_package():
    # Example inputs mirror the bundled AHAprevent R documentation example.
    # Expected values are fixed regression anchors from the official
    # coefficient tables shipped in the AHA PREVENT package.
    result = calculate_prevent(
        _patient(
            sex="female",
            age=45,
            tc=200,
            hdl_c=60,
            sbp=120,
            diabetes=True,
            smoker=False,
            bmi=25,
            egfr=95,
            bp_treated=False,
            lipid_lowering=False,
        ),
        model="base",
    )

    assert result["available"] is True
    assert result["prevent_10y_total_cvd"] == 3.38
    assert result["prevent_10y_ascvd"] == 2.1
    assert result["prevent_10y_hf"] == 1.7
    assert result["prevent_30y_total_cvd"] == 20.65
    assert result["prevent_30y_ascvd"] == 12.0
    assert result["prevent_30y_hf"] == 12.79


def test_official_prevent_known_full_model_outputs_from_coefficients():
    result = calculate_prevent(
        {
            "age": 45,
            "sex": "male",
            "tc": 200,
            "hdl": 50,
            "sbp": 130,
            "bptreat": False,
            "statin": False,
            "dm": False,
            "smoke": False,
            "bmi": 30,
            "egfr": 90,
            "uacr": 45,
            "hba1c": 7.1,
            "sdi": 5,
        },
        model="best_available",
    )

    assert result["available"] is True
    assert result["model_used"] == "full"
    assert result["prevent_10y_total_cvd"] == 3.13
    assert result["prevent_10y_ascvd"] == 2.13
    assert result["prevent_30y_total_cvd"] == 17.8
    assert result["prevent_30y_ascvd"] == 11.62


def test_prevent_age_and_percentile_are_not_in_bundled_official_source():
    result = calculate_prevent(_patient(age=45), model="base")

    assert result["prevent_age"] is None
    assert result["prevent_percentile"] is None


def test_prevent_test_fixture_has_no_expected_output_columns_but_runs_valid_rows():
    fixture = pd.read_stata(COEFF_DIR / "prevent_test.dta")
    expected_cols = [
        col
        for col in fixture.columns
        if col.startswith("aha_prevent_") or col.startswith("prevent5_")
    ]
    assert expected_cols == []

    valid = fixture.dropna(
        subset=["age", "sex", "tc", "hdl", "sbp", "bmi", "egfr", "dm", "smoke", "htnmed", "statin"]
    )
    result = None
    for _idx, row in valid.iterrows():
        candidate = calculate_prevent(
            {
                "age": row["age"],
                "sex": row["sex"],
                "tc": row["tc"],
                "hdl": row["hdl"],
                "sbp": row["sbp"],
                "bmi": row["bmi"],
                "egfr": row["egfr"],
                "dm": row["dm"],
                "smoke": row["smoke"],
                "bptreat": row["htnmed"],
                "statin": row["statin"],
                "uacr": row["uacr"],
                "hba1c": row["hba1c"],
                "sdi": row["sdi10"],
            },
            model="best_available",
        )
        if candidate["available"]:
            result = candidate
            break

    assert result is not None
    assert result["available"] is True
    assert result["prevent_10y_total_cvd"] is not None
