import math
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd


COEFF_DIR = Path(__file__).with_name("coefficients")
OUTCOMES = ("total_cvd", "ascvd", "hf", "chd", "stroke")
OUTCOME_COLUMNS = {
    "total_cvd": "cvd",
    "ascvd": "ascvd",
    "hf": "hf",
    "chd": "chd",
    "stroke": "str",
}
MODEL_NUMBERS = {
    "base": 1,
    "uacr": 2,
    "sdi": 3,
    "hba1c": 4,
    "full": 5,
}
MODEL_REQUIREMENTS = {
    "base": (),
    "uacr": ("uacr",),
    "sdi": ("sdi",),
    "hba1c": ("hba1c",),
    "full": ("uacr", "hba1c", "sdi"),
}
REQUIRED_INPUT_LABELS = {
    "age": "age",
    "sex": "sex",
    "tc": "total cholesterol",
    "hdl": "HDL-C",
    "sbp": "systolic BP",
    "bptreat": "BP treatment status",
    "statin": "statin/lipid-lowering therapy status",
    "dm": "diabetes status",
    "smoke": "smoking status",
    "bmi": "BMI",
    "egfr": "eGFR",
    "uacr": "UACR",
    "hba1c": "HbA1c",
    "sdi": "SDI decile",
}


def _nan_none(value):
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    return value


def _patient_get(patient, *names):
    for name in names:
        if isinstance(patient, dict) and name in patient:
            value = _nan_none(patient[name])
            if value is not None:
                return value
        if hasattr(patient, name):
            value = _nan_none(getattr(patient, name))
            if value is not None:
                return value
    return None


def _bool01(value):
    if value is None:
        return None
    return 1.0 if bool(value) else 0.0


def _sex01(value):
    if value is None:
        return None
    if isinstance(value, str):
        s = value.strip().lower()
        if s in {"female", "f", "1"}:
            return 1.0
        if s in {"male", "m", "0"}:
            return 0.0
    try:
        return 1.0 if int(float(value)) == 1 else 0.0
    except Exception:
        return None


def _float(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def _base_inputs(patient) -> dict[str, float | None]:
    smoking = _patient_get(patient, "smoke", "smoking", "smoker")
    return {
        "age": _float(_patient_get(patient, "age")),
        "sex": _sex01(_patient_get(patient, "sex")),
        "tc": _float(_patient_get(patient, "tc", "total_cholesterol", "total_cholesterol_mgdl")),
        "hdl": _float(_patient_get(patient, "hdl", "hdl_c")),
        "sbp": _float(_patient_get(patient, "sbp")),
        "bptreat": _bool01(_patient_get(patient, "bptreat", "bp_treated", "htnmed")),
        "statin": _bool01(_patient_get(patient, "statin", "lipid_lowering")),
        "dm": _bool01(_patient_get(patient, "dm", "diabetes")),
        "smoke": _bool01(smoking),
        "bmi": _float(_patient_get(patient, "bmi")),
        "egfr": _float(_patient_get(patient, "egfr")),
        "uacr": _float(_patient_get(patient, "uacr")),
        "hba1c": _float(_patient_get(patient, "hba1c", "a1c")),
        "sdi": _float(_patient_get(patient, "sdi", "sdi10", "sdi_decile")),
    }


def _missing(inputs: dict[str, Any], model: str) -> list[str]:
    req = [
        "age",
        "sex",
        "tc",
        "hdl",
        "sbp",
        "bptreat",
        "statin",
        "dm",
        "smoke",
        "bmi",
        "egfr",
        *MODEL_REQUIREMENTS[model],
    ]
    return [REQUIRED_INPUT_LABELS[k] for k in req if inputs.get(k) is None]


def _warnings(inputs: dict[str, Any], model: str) -> list[str]:
    warnings = []
    ranges = {
        "tc": (130, 320, "total cholesterol outside validated range (130-320 mg/dL)"),
        "hdl": (20, 100, "HDL-C outside validated range (20-100 mg/dL)"),
        "sbp": (90, 200, "systolic BP outside validated range (90-200 mmHg)"),
        "bmi": (18.5, 40, "BMI outside validated range (18.5-39.9 kg/m^2)"),
    }
    for key, (lo, hi, msg) in ranges.items():
        value = inputs.get(key)
        if value is not None and not (lo <= float(value) < hi if key == "bmi" else lo <= float(value) <= hi):
            warnings.append(msg)
    if inputs.get("egfr") is not None and inputs["egfr"] < 0:
        warnings.append("eGFR cannot be negative")
    if model in {"uacr", "full"} and inputs.get("uacr") is not None and inputs["uacr"] < 0:
        warnings.append("UACR cannot be negative")
    if model in {"hba1c", "full"} and inputs.get("hba1c") is not None and inputs["hba1c"] < 0:
        warnings.append("HbA1c cannot be negative")
    if model in {"sdi", "full"} and inputs.get("sdi") is not None and not (1 <= int(inputs["sdi"]) <= 10):
        warnings.append("SDI should be an integer between 1 and 10")
    return warnings


@lru_cache(maxsize=None)
def _coeff_df(year: int):
    path = COEFF_DIR / f"prevent_beta{year}_2024.dta"
    return pd.read_stata(path)


def _coefficients(*, year: int, model: str, sex: int, outcome: str) -> list[float]:
    df = _coeff_df(year)
    i = MODEL_NUMBERS[model]
    f = int(sex)
    o = OUTCOME_COLUMNS[outcome]
    column = f"beta{i}{f}_{o}1"
    if column not in df.columns:
        return []
    if year == 10 or year == 5:
        lc = 16 if outcome == "hf" else 19
    else:
        lc = 17 if outcome == "hf" else 20
    count = lc + i + (1 if i == 2 else 0) + (1 if i == 3 else 0) + (4 if i == 5 else 0)
    return [float(x) for x in df[column].iloc[:count].tolist()]


def _spline_low_high(value: float, knot: float) -> tuple[float, float]:
    return min(value, knot), max(value - knot, 0.0)


def _transforms(inputs: dict[str, float | None]) -> dict[str, float]:
    age = float(inputs["age"])
    tc = float(inputs["tc"])
    hdl = float(inputs["hdl"])
    sbp = float(inputs["sbp"])
    bmi = float(inputs["bmi"])
    egfr = float(inputs["egfr"])
    dm = float(inputs["dm"])
    smoke = float(inputs["smoke"])
    bptreat = float(inputs["bptreat"])
    statin = float(inputs["statin"])

    prevent_age = (age - 55.0) / 10.0
    prevent_sbp = (sbp - 110.0) / 20.0
    prevent_sbp_1, prevent_sbp_2 = _spline_low_high(prevent_sbp, 0.0)
    prevent_sbp_2 -= 1.0
    prevent_nhdl = tc * 0.02586 - hdl * 0.02586 - 3.5
    prevent_hdl = (hdl * 0.02586 - 1.3) / 0.3
    prevent_bmi = (bmi - 25.0) / 5.0
    prevent_bmi_1, prevent_bmi_2 = _spline_low_high(prevent_bmi, 1.0)
    egfr_1_raw, egfr_2_raw = _spline_low_high(egfr, 60.0)
    prevent_egfr_1 = -egfr_1_raw / 15.0 + 4.0
    prevent_egfr_2 = -egfr_2_raw / 15.0 + 2.0

    uacr = inputs.get("uacr")
    hba1c = inputs.get("hba1c")
    sdi = inputs.get("sdi")
    prevent_logacr = math.log(0.1 if uacr == 0 else float(uacr)) if uacr is not None else 0.0
    prevent_hba1c = float(hba1c) - 5.3 if hba1c is not None else 0.0
    prevent_hba1c_dm = prevent_hba1c if dm == 1 else 0.0
    prevent_hba1c_nondm = 0.0 if dm == 1 else prevent_hba1c
    sdi_value = int(sdi) if sdi is not None else None

    t = {
        "prevent_age": prevent_age,
        "prevent_age2": prevent_age**2 if age < 60 else 0.0,
        "prevent_sbp_1": prevent_sbp_1,
        "prevent_sbp_2": prevent_sbp_2,
        "dm": dm,
        "smoke": smoke,
        "prevent_bmi_1": prevent_bmi_1,
        "prevent_bmi_2": prevent_bmi_2,
        "prevent_egfr_1": prevent_egfr_1,
        "prevent_egfr_2": prevent_egfr_2,
        "bptreat": bptreat,
        "statin": statin,
        "prevent_bptreat": prevent_sbp_2 * bptreat,
        "prevent_nhdl": prevent_nhdl,
        "prevent_statin": prevent_nhdl * statin,
        "prevent_hdl": prevent_hdl,
        "prevent_logacr": prevent_logacr,
        "prevent_acr_missing": 1.0 if uacr is None else 0.0,
        "prevent_hba1c_dm": prevent_hba1c_dm,
        "prevent_hba1c_nondm": prevent_hba1c_nondm,
        "prevent_hba1c_missing": 1.0 if hba1c is None else 0.0,
        "prevent_sdicat1": 1.0 if sdi_value is not None and 4 < sdi_value <= 6 else 0.0,
        "prevent_sdicat2": 1.0 if sdi_value is not None and 7 < sdi_value <= 10 else 0.0,
        "prevent_sdi_missing": 1.0 if sdi is None else 0.0,
    }
    for key in ("prevent_nhdl", "prevent_hdl", "prevent_sbp_2", "dm", "smoke", "prevent_bmi_2", "prevent_egfr_1"):
        t[f"age_{key}"] = t[key] * prevent_age
    return t


def _vector(inputs: dict[str, float | None], *, year: int, model: str, outcome: str) -> list[float]:
    t = _transforms(inputs)
    av = ["prevent_age", "prevent_age2"] if year == 30 else ["prevent_age"]
    if outcome == "hf":
        cov = [
            "prevent_sbp_1",
            "prevent_sbp_2",
            "dm",
            "smoke",
            "prevent_bmi_1",
            "prevent_bmi_2",
            "prevent_egfr_1",
            "prevent_egfr_2",
            "bptreat",
            "prevent_bptreat",
            "age_prevent_sbp_2",
            "age_dm",
            "age_smoke",
            "age_prevent_bmi_2",
            "age_prevent_egfr_1",
        ]
    else:
        cov = [
            "prevent_nhdl",
            "prevent_hdl",
            "prevent_sbp_1",
            "prevent_sbp_2",
            "dm",
            "smoke",
            "prevent_egfr_1",
            "prevent_egfr_2",
            "bptreat",
            "statin",
            "prevent_bptreat",
            "prevent_statin",
            "age_prevent_nhdl",
            "age_prevent_hdl",
            "age_prevent_sbp_2",
            "age_dm",
            "age_smoke",
            "age_prevent_egfr_1",
        ]
    extra = {
        "base": [],
        "uacr": ["prevent_logacr", "prevent_acr_missing"],
        "sdi": ["prevent_sdicat1", "prevent_sdicat2", "prevent_sdi_missing"],
        "hba1c": ["prevent_hba1c_dm", "prevent_hba1c_nondm", "prevent_hba1c_missing"],
        "full": [
            "prevent_sdicat1",
            "prevent_sdicat2",
            "prevent_sdi_missing",
            "prevent_logacr",
            "prevent_acr_missing",
            "prevent_hba1c_dm",
            "prevent_hba1c_nondm",
            "prevent_hba1c_missing",
        ],
    }[model]
    return [t[name] for name in av + cov + extra] + [1.0]


def _pct_from_xb(xb: float) -> float:
    ex = math.exp(xb)
    return round((ex / (ex + 1.0)) * 100.0, 2)


def _model_from_best_available(inputs: dict[str, Any]) -> str:
    if inputs.get("uacr") is not None and inputs.get("hba1c") is not None and inputs.get("sdi") is not None:
        return "full"
    if inputs.get("uacr") is not None:
        return "uacr"
    if inputs.get("hba1c") is not None:
        return "hba1c"
    if inputs.get("sdi") is not None:
        return "sdi"
    return "base"


def calculate_prevent(patient, model="best_available") -> dict[str, Any]:
    """Calculate official PREVENT estimates using the requested or best-available model."""
    inputs = _base_inputs(patient)
    model_used = _model_from_best_available(inputs) if model == "best_available" else model
    if model_used not in MODEL_NUMBERS:
        raise ValueError(f"Unsupported PREVENT model: {model}")

    missing = _missing(inputs, model_used)
    warnings = _warnings(inputs, model_used)
    informational_warnings = []
    if inputs.get("uacr") is None and model_used not in {"uacr", "full"}:
        model_label = {
            "base": "base",
            "hba1c": "HbA1c",
            "sdi": "SDI",
        }.get(model_used, model_used)
        informational_warnings.append(
            f"UACR not available; {model_label} PREVENT model used."
        )
    age_value = inputs.get("age")
    if age_value is not None:
        try:
            age_num = float(age_value)
        except (TypeError, ValueError):
            age_num = None
        if age_num is not None and 60 <= age_num < 80:
            informational_warnings.append("30-year PREVENT is only available for ages 30-59.")
    base = {
        "available": False,
        "model_used": model_used,
        "prevent_10y_total_cvd": None,
        "prevent_10y_ascvd": None,
        "prevent_10y_hf": None,
        "prevent_10y_chd": None,
        "prevent_10y_stroke": None,
        "prevent_30y_total_cvd": None,
        "prevent_30y_ascvd": None,
        "prevent_30y_hf": None,
        "prevent_30y_chd": None,
        "prevent_30y_stroke": None,
        "prevent_5y_total_cvd": None,
        "prevent_5y_ascvd": None,
        "prevent_5y_hf": None,
        # The bundled official AHA PREVENT STATA/R package does not include
        # PREVENT-age or percentile equations/fixtures. Keep these explicit
        # rather than estimating them locally.
        "prevent_age": None,
        "prevent_percentile": None,
        "missing_inputs": missing,
        "unavailable_reason": None,
        "warnings": warnings + informational_warnings,
    }
    age = float(inputs["age"]) if inputs.get("age") is not None else None
    if age is not None and not (30 <= age < 80):
        base["missing_inputs"] = []
        base["warnings"] = informational_warnings
        if age < 30:
            base["unavailable_reason"] = (
                "PREVENT not validated for age <30; interpretation should rely on clinical risk factors and guideline-specific pathways."
            )
        else:
            base["unavailable_reason"] = (
                "PREVENT not validated for age >79; individualized clinical judgment required."
            )
        return base
    if missing:
        base["unavailable_reason"] = "PREVENT inputs not available."
        return base
    if warnings:
        base["unavailable_reason"] = "One or more PREVENT inputs are outside the validated range."
        return base

    age = float(inputs["age"])

    sex = int(inputs["sex"])
    any_available = False
    coefficient_errors = []
    for year in (5, 10, 30):
        if year == 5 and model_used != "base":
            continue
        if year == 30 and not (30 <= age < 60):
            continue
        for outcome in OUTCOMES:
            if year == 5 and outcome not in {"total_cvd", "ascvd", "hf"}:
                continue
            try:
                coeffs = _coefficients(year=year, model=model_used, sex=sex, outcome=outcome)
            except Exception as exc:
                coefficient_errors.append(f"{year}-year {outcome}: {exc}")
                continue
            if not coeffs:
                continue
            vec = _vector(inputs, year=year, model=model_used, outcome=outcome)
            if len(coeffs) != len(vec):
                raise RuntimeError(
                    f"PREVENT coefficient/vector length mismatch: {year} {model_used} {outcome} "
                    f"{len(coeffs)} != {len(vec)}"
                )
            xb = sum(c * v for c, v in zip(coeffs, vec))
            base[f"prevent_{year}y_{outcome}"] = _pct_from_xb(xb)
            any_available = True

    base["available"] = any_available
    if base["prevent_30y_ascvd"] is None and base["prevent_10y_ascvd"] is not None:
        if not (30 <= age < 60):
            base["unavailable_reason"] = "30-year PREVENT is only available for ages 30-59."
        elif coefficient_errors:
            base["unavailable_reason"] = (
                "30-year PREVENT coefficient load failure: "
                + "; ".join(coefficient_errors)
            )
        else:
            base["unavailable_reason"] = (
                "30-year PREVENT output unavailable for the selected official model."
            )
    return base
