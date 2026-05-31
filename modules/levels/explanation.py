from __future__ import annotations

from typing import Any

from modules.levels.level_classifier import classify_rcckm_level


def _num(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _append_unique(lines: list[str], line: str | None) -> None:
    clean = str(line or "").strip()
    if clean and clean not in lines:
        lines.append(clean)


def _lpa_line(patient: Any) -> str:
    value = _num(getattr(patient, "lp_a_value", None))
    if value is None:
        return "Lp(a)"
    unit = getattr(patient, "lp_a_unit", None) or ""
    return f"Lp(a) {value:g}{(' ' + unit) if unit else ''}"


def _family_history_line(patient: Any) -> str:
    relationship = str(
        getattr(patient, "family_history_relationship", None) or ""
    ).strip()
    event = str(getattr(patient, "family_history_event_type", None) or "").strip()
    age = _num(getattr(patient, "family_history_age_at_event", None))
    if relationship and event and age is not None:
        return f"{relationship.title()} {event.upper()} age {age:g}"
    if relationship and age is not None:
        return f"{relationship.title()} premature ASCVD age {age:g}"
    if age is not None:
        return f"Premature family history age {age:g}"
    return "Premature family history"


def _inflammatory_line(patient: Any) -> str:
    if bool(getattr(patient, "rheumatoid_arthritis", False)):
        return "RA"
    if bool(getattr(patient, "psoriasis", False)):
        return "Psoriasis"
    if bool(getattr(patient, "sle", False)):
        return "SLE"
    if bool(getattr(patient, "ibd", False)):
        return "IBD"
    return "Inflammatory disease"


def _bp_line(patient: Any) -> str:
    sbp = _num(getattr(patient, "sbp", None))
    dbp = _num(getattr(patient, "dbp", None))
    if sbp is not None and dbp is not None:
        return f"BP {sbp:g}/{dbp:g}"
    if bool(getattr(patient, "bp_treated", False)):
        return "Treated hypertension"
    return "Elevated BP"


def _glycemia_line(patient: Any, diabetes: bool = False) -> str:
    a1c = _num(getattr(patient, "a1c", None))
    label = "Diabetes" if diabetes else "Prediabetes"
    if a1c is not None:
        return f"{label} (A1c {a1c:g}%)"
    return label


def _driver_line(driver: str, patient: Any, result: Any) -> str:
    text = str(driver or "").strip()
    lower = text.lower()
    apob = _num(getattr(patient, "apob", None))
    ldl = _num(getattr(patient, "ldl_c", None))
    tg = _num(getattr(patient, "triglycerides", None))
    uacr = _num(getattr(patient, "uacr", None))
    egfr = _num(getattr(patient, "egfr", None))

    if lower.startswith("cac "):
        return text
    if lower == "clinical ascvd":
        return "Clinical ASCVD"
    if "apob" in lower:
        return f"ApoB {apob:g} mg/dL" if apob is not None else text
    if "ldl" in lower:
        return f"LDL-C {ldl:g} mg/dL" if ldl is not None else text
    if "lp(a)" in lower:
        return _lpa_line(patient)
    if "family history" in lower:
        return _family_history_line(patient)
    if "inflammatory" in lower or "rheumatoid arthritis" in lower:
        return _inflammatory_line(patient)
    if "south asian" in lower:
        return "South Asian ancestry"
    if "filipino" in lower:
        return "Filipino ancestry"
    if "gestational diabetes" in lower:
        return "Gestational diabetes"
    if "reproductive" in lower:
        if bool(getattr(patient, "gestational_hypertension", False)):
            return "Gestational hypertension"
        if bool(getattr(patient, "preeclampsia", False)):
            return "Preeclampsia"
        if bool(getattr(patient, "early_menopause", False)) or bool(
            getattr(patient, "premature_menopause", False)
        ):
            return "Premature menopause"
        return "Reproductive risk marker"
    if "breast arterial" in lower:
        return "BAC"
    if "albuminuria" in lower:
        return f"UACR {uacr:g} mg/g" if uacr is not None else "Albuminuria"
    if "reduced kidney" in lower:
        return f"eGFR {egfr:g}" if egfr is not None else "Reduced kidney function"
    if lower == "diabetes":
        return _glycemia_line(patient, diabetes=True)
    if "prediabetes" in lower or "a1c" in lower:
        return _glycemia_line(patient)
    if "triglycerides" in lower:
        return f"TG {tg:g} mg/dL" if tg is not None else text
    if "bp" in lower or "hypertension" in lower:
        return _bp_line(patient)
    if "current smoking" in lower:
        return "Current smoking"
    if "30-year prevent" in lower or "prevent" in lower:
        prevent_30 = _num(getattr(result, "prevent_30y_ascvd", None))
        prevent_10 = _num(getattr(result, "prevent_10y_ascvd", None))
        if prevent_30 is not None:
            return f"30y PREVENT {prevent_30:g}%"
        if prevent_10 is not None:
            return f"10y PREVENT {prevent_10:g}%"
    if "ckm context" in lower:
        if bool(getattr(patient, "osa", False)):
            return "OSA"
        if bool(getattr(patient, "masld", False)):
            return "MASLD"
        bmi = _num(getattr(patient, "bmi", None))
        return f"BMI {bmi:g}" if bmi is not None else "CKM context"
    return text[:1].upper() + text[1:]


def _fallback_driver_lines(patient: Any, result: Any) -> list[str]:
    lines: list[str] = []
    cac = _num(getattr(patient, "cac", None))
    if bool(getattr(patient, "clinical_ascvd", False)):
        _append_unique(lines, "Clinical ASCVD")
    if cac is not None:
        _append_unique(lines, f"CAC {cac:g}")
    egfr = _num(getattr(patient, "egfr", None))
    uacr = _num(getattr(patient, "uacr", None))
    if egfr is not None and egfr < 60:
        _append_unique(lines, f"eGFR {egfr:g}")
    if uacr is not None and uacr >= 30:
        _append_unique(lines, f"UACR {uacr:g} mg/g")
    apob = _num(getattr(patient, "apob", None))
    if apob is not None and apob >= 100:
        _append_unique(lines, f"ApoB {apob:g} mg/dL")
    if bool(getattr(patient, "diabetes", False)):
        _append_unique(lines, _glycemia_line(patient, diabetes=True))
    return lines


def build_level_explanation(patient: Any, result: Any) -> str:
    """Return compact level-driving findings for the active continuum tooltip."""
    classification = classify_rcckm_level(patient, result)
    drivers = list(getattr(classification, "drivers", None) or [])
    cac = _num(getattr(patient, "cac", None))
    lines: list[str] = []

    if cac is not None:
        _append_unique(lines, f"CAC {cac:g}")
        percentile = _num(getattr(patient, "cac_percentile", None))
        if percentile is not None:
            _append_unique(lines, f"{percentile:g}th percentile")
        if cac >= 300:
            _append_unique(lines, "Very high plaque burden")

    for driver in drivers:
        _append_unique(lines, _driver_line(driver, patient, result))

    label = str(getattr(classification, "label", "") or "").lower()
    reason = str(getattr(classification, "short_reason", "") or "").lower()
    if "hidden" in label or "occult" in label or "clustered" in reason:
        _append_unique(lines, "CAC unmeasured" if cac is None else None)

    if not lines:
        for line in _fallback_driver_lines(patient, result):
            _append_unique(lines, line)

    if not lines:
        return "Drivers not available."
    return "\n".join(lines[:5])
