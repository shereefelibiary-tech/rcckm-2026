import math
from typing import Any, Dict, List, Optional


def mmol_conversion(x_mgdl: float) -> float:
    return float(x_mgdl) / 38.67


def _prevent_logistic_pct(logor: float) -> float:
    r = math.exp(logor) / (1.0 + math.exp(logor))
    return round(r * 100.0, 2)


def adjust_uacr(uacr: float) -> float:
    return max(float(uacr), 0.1)


def sdicat(sdi_decile: int) -> int:
    v = int(sdi_decile)
    if 1 <= v <= 3:
        return 0
    if 4 <= v <= 6:
        return 1
    if 7 <= v <= 10:
        return 2
    return 0


def sdi_to_decile(x) -> Optional[int]:
    try:
        v = int(float(x))
    except Exception:
        return None
    if 1 <= v <= 10:
        return v
    if 1 <= v <= 100:
        return int((v - 1) / 10) + 1
    return None


_PREVENT_FULL_LOGOR_10Y = {
    ("female", "total_cvd"):
        "-3.860385 + 0.7716794*((age - 55)/10) + 0.0062109*(mmol_conversion(tc - hdl) - 3.5) - "
        "0.1547756*(mmol_conversion(hdl) - 1.3)/0.3 - 0.1933123*(min(sbp, 110) - 110)/20 + "
        "0.3071217*(max(sbp, 110) - 130)/20 + 0.496753*(dm) + 0.466605*(smoking) + "
        "0.4780697*(min(egfr, 60) - 60)/(-15) + 0.0529077*(max(egfr, 60) - 90)/(-15) + "
        "0.3034892*(bptreat) - 0.1556524*(statin) - 0.0667026*(bptreat)*(max(sbp, 110) - 130)/20 + "
        "0.1197879*(statin)*(mmol_conversion(tc - hdl) - 3.5) - 0.070257*(age - 55)/10*(mmol_conversion(tc - hdl) - 3.5) + "
        "0.0310635*(age - 55)/10*(mmol_conversion(hdl) - 1.3)/0.3 - 0.0875231*(age - 55)/10*(max(sbp, 110) - 130)/20 - "
        "0.2267102*(age - 55)/10*(dm) - 0.0676125*(age - 55)/10*(smoking) - 0.1493231*(age - 55)/10*(min(egfr, 60) - 60)/(-15) + "
        "((0.1361989*(2-sdicat(sdi))*(sdicat(sdi)) + 0.2261596*(sdicat(sdi)-1)*(0.5*sdicat(sdi))) if sdi is not None else (0.1804508)) + "
        "((0.1645922*math.log(adjust_uacr(uacr))) if uacr is not None else (0.0198413)) + "
        "((0.1298513*(hba1c-5.3)*(dm) + 0.1412555*(hba1c-5.3)*(1 - dm)) if hba1c is not None else (-0.0031658))",

    ("female", "ascvd"):
        "-4.291503 + 0.7023067*((age - 55)/10) + 0.0898765*((mmol_conversion(tc) - mmol_conversion(hdl)) - 3.5) - "
        "0.1407316*(mmol_conversion(hdl) - 1.3)/0.3 - 0.0256648*(min(sbp, 110) - 110)/20 + "
        "0.314511*(max(sbp, 110) - 130)/20 + 0.4487393*(dm) + 0.425949*(smoking) + "
        "0.3631734*(min(egfr, 60) - 60)/(-15) + 0.0449096*(max(egfr, 60) - 90)/(-15) + "
        "0.2133861*(bptreat) - 0.0678552*(statin) - 0.036088*(bptreat)*(max(sbp, 110) - 130)/20 + "
        "0.0844423*(statin)*((mmol_conversion(tc) - mmol_conversion(hdl)) - 3.5) - 0.0504475*(age - 55)/10*((mmol_conversion(tc) - mmol_conversion(hdl)) - 3.5) + "
        "0.0325985*(age - 55)/10*(mmol_conversion(hdl) - 1.3)/0.3 - 0.0979228*(age - 55)/10*(max(sbp, 110) - 130)/20 - "
        "0.2251783*(age - 55)/10*(dm) - 0.1075591*(age - 55)/10*(smoking) - 0.163771*(age - 55)/10*(min(egfr, 60) - 60)/(-15) + "
        "((0.1067741*(2-sdicat(sdi))*(sdicat(sdi)) + 0.1735343*(sdicat(sdi)-1)*(0.5*sdicat(sdi))) if sdi is not None else (0.1567115)) + "
        "((0.1142251*math.log(adjust_uacr(uacr))) if uacr is not None else (-0.0055863)) + "
        "((0.0940543*(hba1c-5.3)*(dm) + 0.1116486*(hba1c-5.3)*(1 - dm)) if hba1c is not None else (-0.0024798))",

    ("male", "total_cvd"):
        "-3.631387 + 0.7847578*((age - 55)/10) + 0.0534485*(mmol_conversion(tc - hdl) - 3.5) - "
        "0.0946487*(mmol_conversion(hdl) - 1.3)/0.3 - 0.4921973*(min(sbp, 110) - 110)/20 + "
        "0.2825685*(max(sbp, 110) - 130)/20 + 0.4527054*(dm) + 0.3871999*(smoking) - "
        "0.0485841*(min(bmi, 30) - 25)/5 + 0.3726929*(max(bmi, 30) - 30)/5 + "
        "0.4140627*(min(egfr, 60) - 60)/(-15) + 0.0244018*(max(egfr, 60) - 90)/(-15) + "
        "0.2602434*(bptreat) - 0.1063606*(statin) - 0.0450131*(bptreat)*(max(sbp, 110) - 130)/20 + "
        "0.139964*(statin)*(mmol_conversion(tc - hdl) - 3.5) - 0.0465287*(age - 55)/10*(mmol_conversion(tc - hdl) - 3.5) + "
        "0.0179247*(age - 55)/10*(mmol_conversion(hdl) - 1.3)/0.3 - 0.0999406*(age - 55)/10*(max(sbp, 110) - 130)/20 - "
        "0.2031801*(age - 55)/10*(dm) - 0.1149175*(age - 55)/10*(smoking) + 0.0068126*(age - 55)/10*(max(bmi, 30) - 30)/5 - "
        "0.1357792*(age - 55)/10*(min(egfr, 60) - 60)/(-15) + "
        "((0.1213034*(2-sdicat(sdi))*(sdicat(sdi)) + 0.1865146*(sdicat(sdi)-1)*(0.5*sdicat(sdi))) if sdi is not None else (0.1819138)) + "
        "((0.1887974*math.log(adjust_uacr(uacr))) if uacr is not None else (0.0916979)) + "
        "((0.1856442*(hba1c-5.3)*(dm) + 0.1833083*(hba1c-5.3)*(1 - dm)) if hba1c is not None else (-0.0143112))",

    ("male", "ascvd"):
        "-3.969788 + 0.7128741*((age - 55)/10) + 0.1465201*((mmol_conversion(tc) - mmol_conversion(hdl)) - 3.5) - "
        "0.1125794*(mmol_conversion(hdl) - 1.3)/0.3 - 0.1830509*(min(sbp, 110) - 110)/20 + "
        "0.350999*(max(sbp, 110) - 130)/20 + 0.4089407*(dm) + 0.3786529*(smoking) - "
        "0.0833107*(min(bmi, 30) - 25)/5 + 0.26999*(max(bmi, 30) - 30)/5 + "
        "0.3237833*(min(egfr, 60) - 60)/(-15) + 0.0297847*(max(egfr, 60) - 90)/(-15) + "
        "0.1779797*(bptreat) - 0.0145553*(statin) - 0.022474*(bptreat)*(max(sbp, 110) - 130)/20 + "
        "0.1119581*(statin)*((mmol_conversion(tc) - mmol_conversion(hdl)) - 3.5) - 0.0407326*(age - 55)/10*((mmol_conversion(tc) - mmol_conversion(hdl)) - 3.5) + "
        "0.0189978*(age - 55)/10*(mmol_conversion(hdl) - 1.3)/0.3 - 0.1035993*(age - 55)/10*(max(sbp, 110) - 130)/20 - "
        "0.2264091*(age - 55)/10*(dm) - 0.1328636*(age - 55)/10*(smoking) + 0.0182831*(age - 55)/10*(max(bmi, 30) - 30)/5 - "
        "0.1275693*(age - 55)/10*(min(egfr, 60) - 60)/(-15) + "
        "((0.0847634*(2-sdicat(sdi))*(sdicat(sdi)) + 0.1444688*(sdicat(sdi)-1)*(0.5*sdicat(sdi))) if sdi is not None else (0.1485802)) + "
        "((0.1486028*math.log(adjust_uacr(uacr))) if uacr is not None else (0.011608)) + "
        "((0.0768169*(hba1c-5.3)*(dm) + 0.0777295*(hba1c-5.3)*(1 - dm)) if hba1c is not None else (0.0092204))",
}


def _prevent_eval_logor(
    expr: str,
    *,
    age,
    tc,
    hdl,
    sbp,
    dm,
    smoking,
    bmi,
    egfr,
    bptreat,
    statin,
    uacr,
    hba1c,
    sdi,
) -> float:
    scope = {
        "min": min,
        "max": max,
        "math": math,
        "mmol_conversion": mmol_conversion,
        "adjust_uacr": adjust_uacr,
        "sdicat": sdicat,
        "age": float(age),
        "tc": float(tc),
        "hdl": float(hdl),
        "sbp": float(sbp),
        "dm": 1.0 if bool(dm) else 0.0,
        "smoking": 1.0 if bool(smoking) else 0.0,
        "bmi": float(bmi),
        "egfr": float(egfr),
        "bptreat": 1.0 if bool(bptreat) else 0.0,
        "statin": 1.0 if bool(statin) else 0.0,
        "uacr": (float(uacr) if uacr is not None else None),
        "hba1c": (float(hba1c) if hba1c is not None else None),
        "sdi": (int(sdi) if sdi is not None else None),
    }
    return float(eval(expr, {"__builtins__": {}}, scope))


def _patient_has(patient, key: str) -> bool:
    aliases = {
        "tc": ("tc", "total_cholesterol", "total_cholesterol_mgdl"),
        "hdl": ("hdl", "hdl_c"),
        "smoking": ("smoking", "smoker"),
        "bp_treated": ("bp_treated", "bptreat", "hypertension_treated"),
        "lipid_lowering": ("lipid_lowering", "statin"),
        "hba1c": ("hba1c", "a1c"),
        "sdi": ("sdi", "sdi_decile"),
    }
    keys = aliases.get(key, (key,))
    for candidate in keys:
        if hasattr(patient, "has") and patient.has(candidate):
            return True
        if isinstance(patient, dict) and candidate in patient and patient[candidate] is not None:
            return True
        if hasattr(patient, candidate) and getattr(patient, candidate) is not None:
            return True
    return False


def _patient_get(patient, key: str, default=None):
    aliases = {
        "tc": ("tc", "total_cholesterol", "total_cholesterol_mgdl"),
        "hdl": ("hdl", "hdl_c"),
        "smoking": ("smoking", "smoker"),
        "bp_treated": ("bp_treated", "bptreat", "hypertension_treated"),
        "lipid_lowering": ("lipid_lowering", "statin"),
        "hba1c": ("hba1c", "a1c"),
        "sdi": ("sdi", "sdi_decile"),
    }
    keys = aliases.get(key, (key,))
    for candidate in keys:
        if hasattr(patient, "has") and patient.has(candidate):
            return patient.get(candidate, default)
        if isinstance(patient, dict) and candidate in patient and patient[candidate] is not None:
            return patient[candidate]
        if hasattr(patient, candidate) and getattr(patient, candidate) is not None:
            return getattr(patient, candidate)
    return default


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _add_trace(trace, event, value, note):
    if trace is not None:
        trace.append({"event": event, "value": value, "note": note})


def prevent10_total_and_ascvd(patient, trace: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    # TODO: Integrate this full equation behind calculate_prevent_ascvd_10y once
    # expected input mapping and known-output fixtures are validated end-to-end.
    req = [
        "age",
        "sex",
        "tc",
        "hdl",
        "sbp",
        "bp_treated",
        "smoking",
        "diabetes",
        "bmi",
        "egfr",
        "lipid_lowering",
    ]
    missing = [key for key in req if not _patient_has(patient, key)]
    if missing:
        _add_trace(trace, "PREVENT_missing_inputs", missing, "PREVENT not calculated")
        return {
            "total_cvd_10y_pct": None,
            "ascvd_10y_pct": None,
            "total_cvd_30y_pct": None,
            "ascvd_30y_pct": None,
            "missing": missing,
            "notes": "PREVENT not calculated (missing required inputs).",
            "statin_used": None,
            "statin_source": "none",
        }

    age = int(_patient_get(patient, "age"))
    if age < 30 or age > 79:
        _add_trace(trace, "PREVENT_age_out_of_range", age, "Validated for ages 30-79")
        return {
            "total_cvd_10y_pct": None,
            "ascvd_10y_pct": None,
            "total_cvd_30y_pct": None,
            "ascvd_30y_pct": None,
            "missing": [],
            "notes": "PREVENT validated for ages 30-79.",
            "statin_used": None,
            "statin_source": "none",
        }

    sex_raw = str(_patient_get(patient, "sex", "")).lower()
    sex_key = "female" if sex_raw in ("f", "female") else "male"

    tc = _safe_float(_patient_get(patient, "tc"))
    hdl = _safe_float(_patient_get(patient, "hdl"))
    sbp = _safe_float(_patient_get(patient, "sbp"))
    bmi = _safe_float(_patient_get(patient, "bmi"))
    egfr = _safe_float(_patient_get(patient, "egfr"))

    if (
        tc is None
        or hdl is None
        or sbp is None
        or bmi is None
        or egfr is None
        or tc <= 0
        or hdl <= 0
        or sbp <= 0
        or bmi <= 0
        or egfr <= 0
    ):
        _add_trace(
            trace,
            "PREVENT_invalid_inputs",
            {"tc": tc, "hdl": hdl, "sbp": sbp, "bmi": bmi, "egfr": egfr},
            "PREVENT not calculated",
        )
        return {
            "total_cvd_10y_pct": None,
            "ascvd_10y_pct": None,
            "total_cvd_30y_pct": None,
            "ascvd_30y_pct": None,
            "missing": [],
            "notes": "PREVENT not calculated (invalid inputs).",
            "statin_used": None,
            "statin_source": "none",
        }

    dm = bool(_patient_get(patient, "diabetes"))
    smoking = bool(_patient_get(patient, "smoking"))
    bptreat = bool(_patient_get(patient, "bp_treated"))
    statin = bool(_patient_get(patient, "lipid_lowering"))
    statin_source = str(_patient_get(patient, "_statin_source", "none") or "none")

    uacr = float(_patient_get(patient, "uacr")) if _patient_has(patient, "uacr") else None
    hba1c = None
    if _patient_has(patient, "hba1c"):
        hba1c = float(_patient_get(patient, "hba1c"))

    sdi = None
    if _patient_has(patient, "sdi"):
        sdi = sdi_to_decile(_patient_get(patient, "sdi"))
    elif _patient_has(patient, "sdi_decile"):
        sdi = sdi_to_decile(_patient_get(patient, "sdi_decile"))

    if uacr is not None and uacr < 0:
        _add_trace(trace, "PREVENT_uacr_invalid", uacr, "UACR < 0 (ignored)")
        uacr = None
    if hba1c is not None and hba1c <= 0:
        _add_trace(trace, "PREVENT_hba1c_invalid", hba1c, "HbA1c <= 0 (ignored)")
        hba1c = None
    if sdi is not None and not (1 <= int(sdi) <= 10):
        _add_trace(trace, "PREVENT_sdi_invalid", sdi, "SDI out of range (ignored)")
        sdi = None

    logor_total = _prevent_eval_logor(
        _PREVENT_FULL_LOGOR_10Y[(sex_key, "total_cvd")],
        age=age,
        tc=tc,
        hdl=hdl,
        sbp=sbp,
        dm=dm,
        smoking=smoking,
        bmi=bmi,
        egfr=egfr,
        bptreat=bptreat,
        statin=statin,
        uacr=uacr,
        hba1c=hba1c,
        sdi=sdi,
    )
    logor_ascvd = _prevent_eval_logor(
        _PREVENT_FULL_LOGOR_10Y[(sex_key, "ascvd")],
        age=age,
        tc=tc,
        hdl=hdl,
        sbp=sbp,
        dm=dm,
        smoking=smoking,
        bmi=bmi,
        egfr=egfr,
        bptreat=bptreat,
        statin=statin,
        uacr=uacr,
        hba1c=hba1c,
        sdi=sdi,
    )

    total_pct = _prevent_logistic_pct(logor_total)
    ascvd_pct = _prevent_logistic_pct(logor_ascvd)

    _add_trace(
        trace,
        "PREVENT_calculated",
        {
            "sex": sex_key,
            "total": total_pct,
            "ascvd": ascvd_pct,
            "uacr": (uacr is not None),
            "hba1c": (hba1c is not None),
            "sdi": (sdi is not None),
        },
        "PREVENT 10y calculated",
    )

    return {
        "total_cvd_10y_pct": total_pct,
        "ascvd_10y_pct": ascvd_pct,
        "total_cvd_30y_pct": None,
        "ascvd_30y_pct": None,
        "missing": [],
        "notes": "PREVENT (population model).",
        "statin_used": bool(statin),
        "statin_source": statin_source if statin else "none",
    }
