from modules.risk_enhancers.breast_arterial_calcification import (
    has_breast_arterial_calcification,
)


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _prevent_10y(patient, result=None):
    if result is not None:
        value = _num(getattr(result, "prevent_10y_ascvd", None))
        if value is not None:
            return value
    return _num(getattr(patient, "prevent_10y_ascvd", None))


def _elevated_lpa(patient):
    value = _num(getattr(patient, "lp_a_value", None))
    unit = str(getattr(patient, "lp_a_unit", "") or "").strip().lower()
    return bool(
        value is not None
        and (
            (unit in {"nmol/l", "nmol"} and value >= 125)
            or (unit in {"mg/dl", "mg"} and value >= 50)
            or (not unit and value >= 125)
        )
    )


def _confirmed_premature_family_history(patient):
    return bool(getattr(patient, "premature_fhx_ascvd", False)) or bool(
        getattr(patient, "family_history_premature_ascvd", False)
    )


def _reproductive_marker(patient):
    return any(
        bool(getattr(patient, field, False))
        for field in (
            "early_menopause",
            "premature_menopause",
            "preeclampsia",
            "gestational_hypertension",
            "gestational_diabetes",
            "preterm_delivery",
            "small_for_gestational_age",
            "recurrent_pregnancy_loss",
            "pcos_or_irregular_menses",
            "early_menarche",
        )
    )


def _inflammatory_marker(patient):
    return any(
        bool(getattr(patient, field, False))
        for field in (
            "inflammatory_disease",
            "rheumatoid_arthritis",
            "sle",
            "psoriasis",
            "ibd",
        )
    )


def _major_enhancer_count(patient):
    return sum(
        1
        for present in (
            _elevated_lpa(patient),
            _confirmed_premature_family_history(patient),
            _inflammatory_marker(patient),
            bool(getattr(patient, "south_asian_ancestry", False)),
            bool(getattr(patient, "filipino_ancestry", False)),
            _reproductive_marker(patient),
            has_breast_arterial_calcification(patient),
        )
        if present
    )


def has_occult_lipid_discussion_path(patient, result=None):
    """Shared target/CAC predicate for low-PREVENT clustered atherogenic risk."""
    age = _num(getattr(patient, "age", None))
    cac = _num(getattr(patient, "cac", None))
    ldl_c = _num(getattr(patient, "ldl_c", None))
    apob = _num(getattr(patient, "apob", None))
    prevent_10y = _prevent_10y(patient, result)
    strong_lipid_burden = bool(
        (ldl_c is not None and ldl_c >= 150)
        or (apob is not None and apob >= 120)
    )
    moderate_lipid_burden = bool(
        (ldl_c is not None and ldl_c >= 130)
        or (apob is not None and apob >= 100)
    )
    occult_signature = bool(
        _elevated_lpa(patient)
        and (_confirmed_premature_family_history(patient) or _reproductive_marker(patient))
    )
    return bool(
        age is not None
        and 40 <= age <= 59
        and not bool(getattr(patient, "clinical_ascvd", False))
        and cac is None
        and prevent_10y is not None
        and prevent_10y < 3
        and (strong_lipid_burden or (moderate_lipid_burden and occult_signature))
        and _major_enhancer_count(patient) >= 2
    )
