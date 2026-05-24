from modules.levels.level_classifier import classify_rcckm_level


LEVEL_DEFS = {
    1: {
        "title": "Level 1",
        "label": "Minimal risk signal",
        "description": "No major plaque, CKM, or biologic risk signal identified.",
    },
    2: {
        "title": "Level 2",
        "label": "Emerging risk signals",
        "description": "Early or mild risk signals without measured plaque or major actionable biology.",
        "sublevels": {
            "2A": "Early isolated risk signal",
            "2B": "Converging early risk signals",
        },
    },
    3: {
        "title": "Level 3",
        "label": "Actionable biologic risk",
        "description": "Actionable biology or elevated estimated population risk without measured subclinical plaque.",
        "sublevels": {
            "3A": "Elevated long-term risk trajectory",
            "3B": "Actionable early CKM / atherogenic risk",
        },
    },
    4: {
        "title": "Level 4",
        "label": "Subclinical atherosclerosis present",
        "description": "Measured subclinical plaque is present below very high plaque burden.",
    },
    5: {
        "title": "Level 5",
        "label": "Very high risk / ASCVD intensity",
        "description": "Clinical ASCVD or CAC >=300 indicates very high-risk management intensity.",
    },
}

MILD_SIGNALS = [
    "ApoB 80-99 mg/dL",
    "LDL-C 100-129 mg/dL only if ApoB unavailable",
    "A1c 5.7-6.4%",
    "hsCRP >=2 mg/L without stronger inflammatory context",
    "premature family history as isolated enhancer",
]

MAJOR_ACTIONABLE_DRIVERS = [
    "ApoB >=100 mg/dL",
    "LDL-C >=130 mg/dL only if ApoB unavailable",
    "Lp(a) >=125 nmol/L or >=50 mg/dL",
    "diabetes-range A1c >=6.5% or diabetes true",
    "current smoking",
    "chronic inflammatory disease",
    "hsCRP >=2 with supportive inflammatory/metabolic context",
]


def get_level_definition_payload(level, sublevel=None):
    level_payload = dict(LEVEL_DEFS[level])
    if sublevel:
        sublevels = level_payload.get("sublevels", {})
        level_payload["sublevel"] = sublevel
        level_payload["sublevel_label"] = sublevels.get(sublevel)
    return level_payload


def levels_legend_compact():
    return [
        f"{payload['title']}: {payload['label']}"
        for _, payload in sorted(LEVEL_DEFS.items())
    ]


def _risk_value(risk_level):
    return getattr(risk_level, "value", risk_level)


def _has_diabetes(patient):
    a1c = getattr(patient, "a1c", None)
    return bool(getattr(patient, "diabetes", False)) or (
        a1c is not None and a1c >= 6.5
    )


def _has_supportive_inflammatory_context(patient):
    return any(
        bool(getattr(patient, field, False))
        for field in ("diabetes", "ckd", "hypertension", "inflammatory_disease")
    )


def _has_premature_family_history(patient):
    return bool(getattr(patient, "premature_fhx_ascvd", False)) or bool(
        getattr(patient, "family_history_premature_ascvd", False)
    )


def _has_albuminuria(patient):
    uacr = getattr(patient, "uacr", None)
    return uacr is not None and uacr >= 30


def _age_30_to_59(patient):
    age = getattr(patient, "age", None)
    return age is not None and 30 <= age <= 59


def _has_elevated_30y_trajectory(patient, result):
    prevent_30y = getattr(result, "prevent_30y_ascvd", None)
    return bool(_age_30_to_59(patient) and prevent_30y is not None and prevent_30y >= 10)


def _has_additional_ckm_signal(patient, result):
    a1c = getattr(patient, "a1c", None)
    apob = getattr(patient, "apob", None)
    ldl_c = getattr(patient, "ldl_c", None)
    triglycerides = getattr(patient, "triglycerides", None)
    prevent_category = _risk_value(getattr(result, "prevent_risk_category", None))
    return bool(
        (a1c is not None and a1c >= 5.7)
        or _has_diabetes(patient)
        or bool(getattr(patient, "bp_treated", False))
        or bool(getattr(patient, "elevated_bp", False))
        or bool(getattr(patient, "hypertension", False))
        or (apob is not None and apob >= 80)
        or (ldl_c is not None and ldl_c >= 100)
        or (triglycerides is not None and triglycerides >= 150)
        or bool(getattr(patient, "osa", False))
        or bool(getattr(patient, "masld", False))
        or (prevent_category in {"BORDERLINE", "INTERMEDIATE", "HIGH"})
    )


def _family_history_signal(patient):
    summary = getattr(patient, "family_history_summary", None)
    return summary if summary else "Premature family history"


def _mild_signals(patient, result):
    signals = []
    apob = getattr(patient, "apob", None)
    ldl_c = getattr(patient, "ldl_c", None)
    a1c = getattr(patient, "a1c", None)
    hscrp = getattr(patient, "hscrp", None)

    if apob is not None and 80 <= apob <= 99:
        signals.append("ApoB 80-99 mg/dL")
    elif apob is None and ldl_c is not None and 100 <= ldl_c <= 129:
        signals.append("LDL-C 100-129 mg/dL")

    if a1c is not None and 5.7 <= a1c <= 6.4:
        signals.append("A1c 5.7-6.4%")

    if (
        hscrp is not None
        and hscrp >= 2
        and not _has_supportive_inflammatory_context(patient)
    ):
        signals.append("hsCRP >=2 mg/L")

    if _has_premature_family_history(patient):
        signals.append(_family_history_signal(patient))

    prevent_category = _risk_value(getattr(result, "prevent_risk_category", None))
    if prevent_category in {"BORDERLINE", "INTERMEDIATE"}:
        signals.append(f"PREVENT {prevent_category.lower()} estimated population risk")

    return signals


def _major_actionable_drivers(patient, result):
    drivers = []
    apob = getattr(patient, "apob", None)
    ldl_c = getattr(patient, "ldl_c", None)
    lpa = getattr(patient, "lp_a_value", None)
    lpa_unit = getattr(patient, "lp_a_unit", None)
    hscrp = getattr(patient, "hscrp", None)

    if apob is not None and apob >= 100:
        drivers.append("ApoB >=100 mg/dL")
    elif apob is None and ldl_c is not None and ldl_c >= 130:
        drivers.append("LDL-C >=130 mg/dL")

    if (lpa_unit == "nmol/L" and lpa is not None and lpa >= 125) or (
        lpa_unit == "mg/dL" and lpa is not None and lpa >= 50
    ):
        drivers.append("Elevated Lp(a)")

    if _has_diabetes(patient):
        drivers.append("Diabetes-range glycemia")

    if bool(getattr(patient, "smoker", False)) or bool(getattr(patient, "smoking", False)):
        drivers.append("Current smoking")

    if getattr(patient, "inflammatory_disease", False):
        drivers.append("Chronic inflammatory disease")

    if (
        hscrp is not None
        and hscrp >= 2
        and _has_supportive_inflammatory_context(patient)
    ):
        drivers.append("hsCRP with inflammatory/metabolic context")

    if _risk_value(getattr(result, "prevent_risk_category", None)) == "HIGH":
        drivers.append("PREVENT high estimated population risk")

    if _has_albuminuria(patient) and _has_additional_ckm_signal(patient, result):
        drivers.append("Albuminuria with CKM risk")

    return drivers


def classify_continuum_position(patient, result):
    classification = classify_rcckm_level(patient, result)
    level = classification.level
    if level in {"2A", "2B"}:
        return {"level": 2, "sublevel": level}
    if level in {"3A", "3B"}:
        return {"level": 3, "sublevel": level}
    return {"level": int(level), "sublevel": None}
