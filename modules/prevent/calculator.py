from modules.prevent.official import calculate_prevent


def _explicit_prevent_summary(patient) -> dict | None:
    values = {
        "prevent_10y_ascvd": getattr(patient, "prevent_10y_ascvd", None),
        "prevent_10y_total_cvd": getattr(patient, "prevent_10y_total_cvd", None),
        "prevent_30y_ascvd": getattr(patient, "prevent_30y_ascvd", None),
        "prevent_30y_total_cvd": getattr(patient, "prevent_30y_total_cvd", None),
    }
    if not any(value is not None for value in values.values()):
        return None
    return {
        "available": values["prevent_10y_ascvd"] is not None,
        "model_used": "provided",
        "missing_inputs": [],
        "unavailable_reason": None,
        "unsupported_reason": None,
        "warnings": [],
        "prevent_10y_hf": None,
        "prevent_10y_chd": None,
        "prevent_10y_stroke": None,
        "prevent_30y_hf": None,
        "prevent_30y_chd": None,
        "prevent_30y_stroke": None,
        "prevent_5y_total_cvd": None,
        "prevent_5y_ascvd": None,
        "prevent_5y_hf": None,
        "prevent_age": getattr(patient, "prevent_age", None),
        "prevent_percentile": getattr(patient, "prevent_percentile", None),
        **values,
    }


def _merge_official_missing_values(patient, explicit: dict) -> dict:
    needs_official = any(
        explicit.get(key) is None
        for key in (
            "prevent_10y_total_cvd",
            "prevent_30y_ascvd",
            "prevent_30y_total_cvd",
        )
    )
    if not needs_official:
        return explicit

    official = calculate_prevent(patient, model="best_available")
    merged = dict(explicit)
    for key in (
        "prevent_10y_total_cvd",
        "prevent_10y_hf",
        "prevent_10y_chd",
        "prevent_10y_stroke",
        "prevent_30y_ascvd",
        "prevent_30y_total_cvd",
        "prevent_30y_hf",
        "prevent_30y_chd",
        "prevent_30y_stroke",
        "prevent_5y_total_cvd",
        "prevent_5y_ascvd",
        "prevent_5y_hf",
        "prevent_age",
        "prevent_percentile",
    ):
        if merged.get(key) is None and official.get(key) is not None:
            merged[key] = official[key]

    merged["warnings"] = list(official.get("warnings") or [])
    merged["missing_inputs"] = list(official.get("missing_inputs") or [])
    if merged.get("prevent_30y_ascvd") is None:
        reason = official.get("unavailable_reason")
        if reason:
            merged["unavailable_reason"] = reason
            merged["unsupported_reason"] = reason
    if official.get("missing_inputs"):
        merged["warnings"].append(
            "Official PREVENT calculation incomplete for missing fields: "
            + ", ".join(official["missing_inputs"])
        )
    return merged


def calculate_prevent_summary(patient, trace=None) -> dict:
    explicit = _explicit_prevent_summary(patient)
    if explicit is not None:
        explicit = _merge_official_missing_values(patient, explicit)
        if explicit["prevent_10y_ascvd"] is not None and explicit["prevent_30y_ascvd"] is None:
            age = getattr(patient, "age", None)
            try:
                age_num = float(age)
            except (TypeError, ValueError):
                age_num = None
            if age_num is not None and age_num >= 60:
                reason = "30-year PREVENT is only available for ages 30-59."
            else:
                reason = explicit.get("unavailable_reason") or (
                    "30-year PREVENT estimate unavailable for the current data/age range."
                )
            explicit["unavailable_reason"] = (
                reason
            )
            explicit["unsupported_reason"] = explicit["unavailable_reason"]
        return explicit

    result = calculate_prevent(patient, model="best_available")
    result["unsupported_reason"] = result.get("unavailable_reason")
    if trace is not None:
        trace.append(
            {
                "event": "PREVENT_official_calculated" if result["available"] else "PREVENT_official_unavailable",
                "value": {
                    "model_used": result["model_used"],
                    "missing_inputs": result["missing_inputs"],
                    "unavailable_reason": result["unavailable_reason"],
                },
                "note": "Official AHA PREVENT STATA coefficients",
            }
        )
    return result


def calculate_prevent_ascvd_10y(patient):
    return calculate_prevent_summary(patient)["prevent_10y_ascvd"]


def calculate_prevent_total_cvd_10y(patient):
    return calculate_prevent_summary(patient)["prevent_10y_total_cvd"]


def calculate_prevent_ascvd_30y(patient):
    return calculate_prevent_summary(patient)["prevent_30y_ascvd"]


def calculate_prevent_total_cvd_30y(patient):
    return calculate_prevent_summary(patient)["prevent_30y_total_cvd"]
