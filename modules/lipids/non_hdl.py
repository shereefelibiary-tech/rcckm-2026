from typing import Any


NON_HDL_TOOLTIP = (
    "non-HDL-C is total cholesterol minus HDL-C. It helps estimate cholesterol "
    "carried by plaque-forming particles, especially when triglycerides are high."
)


def _num(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def calculate_non_hdl(total_cholesterol: Any, hdl_c: Any) -> float | None:
    """Return total cholesterol minus HDL-C when both values are valid."""
    total = _num(total_cholesterol)
    hdl = _num(hdl_c)
    if total is None or hdl is None:
        return None
    value = total - hdl
    if value < 0:
        return None
    return value


def _current_non_hdl(patient: Any) -> float | None:
    # Visible non-HDL-C is presented as a calculated value, so require the
    # source lipid-panel values rather than asking clinicians to infer them.
    return calculate_non_hdl(
        getattr(patient, "tc", None),
        getattr(patient, "hdl_c", None),
    )


def _ui_detail_enabled(ui_context: Any) -> bool:
    if isinstance(ui_context, dict):
        return bool(
            ui_context.get("clinician_detail_mode")
            or ui_context.get("show_non_hdl")
            or ui_context.get("detail_mode")
        )
    return str(ui_context or "").strip().lower() in {
        "detail",
        "clinician_detail",
        "clinician_detail_mode",
    }


def _has_metabolic_context(patient: Any) -> bool:
    a1c = _num(getattr(patient, "a1c", None))
    bmi = _num(getattr(patient, "bmi", None))
    return bool(
        getattr(patient, "diabetes", False)
        or (a1c is not None and a1c >= 5.7)
        or (bmi is not None and bmi >= 30)
        or getattr(patient, "metabolic_syndrome", False)
        or getattr(patient, "masld", False)
    )


def should_show_non_hdl_default(patient: Any, result: Any = None, ui_context: Any = None) -> bool:
    """Return whether non-HDL-C should appear in the default visible target hierarchy."""
    current = _current_non_hdl(patient)
    if current is None:
        return False
    target = (getattr(result, "targets", None) or [None])[0]
    target_value = _num(getattr(target, "non_hdl_c_target", None)) if target else None
    if target_value is None:
        return False
    if _ui_detail_enabled(ui_context):
        return True
    if bool(getattr(result, "non_hdl_decision_relevant", False)):
        return True
    triglycerides = _num(getattr(patient, "triglycerides", None))
    if triglycerides is not None and triglycerides >= 150:
        return True
    if getattr(patient, "apob", None) is None:
        return True
    if _has_metabolic_context(patient):
        return True
    return False


def format_non_hdl_display(patient: Any, result: Any = None) -> dict[str, Any] | None:
    """Build a display payload for secondary non-HDL-C target rendering."""
    current = _current_non_hdl(patient)
    target = (getattr(result, "targets", None) or [None])[0] if result is not None else None
    target_value = _num(getattr(target, "non_hdl_c_target", None)) if target else None
    if current is None or target_value is None:
        return None
    return {
        "label": "non-HDL-C",
        "current_value": current,
        "target_value": target_value,
        "tooltip": NON_HDL_TOOLTIP,
        "display_priority": "secondary",
        "subtitle": "Calculated from total cholesterol minus HDL-C.",
    }
