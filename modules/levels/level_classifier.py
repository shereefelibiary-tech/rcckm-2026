from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class LevelClassification:
    """Structured RCCKM level output for report and audit renderers."""

    level: str
    label: str
    short_reason: str
    drivers: list[str] = field(default_factory=list)
    prevent_category: str | None = None
    plaque_status: str = "Plaque unmeasured"
    treatment_posture: str = "lifestyle"

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the level classification."""
        return asdict(self)


def _risk_value(value):
    return getattr(value, "value", value)


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _age_30_to_59(patient) -> bool:
    age = _num(getattr(patient, "age", None))
    return age is not None and 30 <= age <= 59


def _has_diabetes(patient) -> bool:
    a1c = _num(getattr(patient, "a1c", None))
    return bool(getattr(patient, "diabetes", False)) or (
        a1c is not None and a1c >= 6.5
    )


def _has_prediabetes(patient) -> bool:
    a1c = _num(getattr(patient, "a1c", None))
    return a1c is not None and 5.7 <= a1c < 6.5


def _has_premature_family_history(patient) -> bool:
    return bool(getattr(patient, "premature_fhx_ascvd", False)) or bool(
        getattr(patient, "family_history_premature_ascvd", False)
    )


def _reproductive_signal_count(patient) -> int:
    fields = (
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
    return sum(1 for field in fields if bool(getattr(patient, field, False)))


def _lpa_elevated(patient) -> bool:
    value = _num(getattr(patient, "lp_a_value", None))
    unit = getattr(patient, "lp_a_unit", None)
    return bool(
        value is not None
        and (
            (unit == "nmol/L" and value >= 125)
            or (unit == "mg/dL" and value >= 50)
        )
    )


def _atherogenic_signal(patient) -> bool:
    apob = _num(getattr(patient, "apob", None))
    ldl_c = _num(getattr(patient, "ldl_c", None))
    non_hdl = _num(getattr(patient, "non_hdl_c", None))
    tg = _num(getattr(patient, "triglycerides", None))
    return bool(
        (apob is not None and apob >= 80)
        or (ldl_c is not None and ldl_c >= 100)
        or (non_hdl is not None and non_hdl >= 130)
        or (tg is not None and tg >= 150)
    )


def _ldl_160_189(patient) -> bool:
    ldl_c = _num(getattr(patient, "ldl_c", None))
    return ldl_c is not None and 160 <= ldl_c < 190


def _severe_hyperchol(patient) -> bool:
    ldl_c = _num(getattr(patient, "ldl_c", None))
    apob = _num(getattr(patient, "apob", None))
    return bool(
        (ldl_c is not None and ldl_c >= 190)
        or (apob is not None and apob >= 140)
    )


def _kidney_signal(patient) -> bool:
    egfr = _num(getattr(patient, "egfr", None))
    uacr = _num(getattr(patient, "uacr", None))
    return bool(
        (egfr is not None and egfr < 60)
        or (uacr is not None and uacr >= 30)
    )


def _albuminuria(patient) -> bool:
    uacr = _num(getattr(patient, "uacr", None))
    return uacr is not None and uacr >= 30


def _bp_signal(patient) -> bool:
    sbp = _num(getattr(patient, "sbp", None))
    dbp = _num(getattr(patient, "dbp", None))
    return bool(
        bool(getattr(patient, "bp_treated", False))
        or bool(getattr(patient, "hypertension", False))
        or bool(getattr(patient, "elevated_bp", False))
        or (sbp is not None and sbp >= 130)
        or (dbp is not None and dbp >= 80)
    )


def _ckm_context_signal(patient) -> bool:
    bmi = _num(getattr(patient, "bmi", None))
    return bool(
        (bmi is not None and bmi >= 30)
        or bool(getattr(patient, "osa", False))
        or bool(getattr(patient, "masld", False))
    )


def _inflammatory_signal(patient) -> bool:
    return any(
        bool(getattr(patient, field, False))
        for field in (
            "inflammatory_disease",
            "rheumatoid_arthritis",
            "sle",
            "psoriasis",
            "inflammatory_arthritis",
            "ibd",
        )
    )


def _enhancer_burden_count(patient) -> int:
    return sum(
        1
        for present in (
            _lpa_elevated(patient),
            _has_premature_family_history(patient),
            _reproductive_signal_count(patient) > 0,
            _inflammatory_signal(patient),
            bool(getattr(patient, "hiv", False)),
            bool(getattr(patient, "south_asian_ancestry", False)),
            bool(getattr(patient, "filipino_ancestry", False)),
        )
        if present
    )


def _metabolic_burden_count(patient) -> int:
    tg = _num(getattr(patient, "triglycerides", None))
    apob = _num(getattr(patient, "apob", None))
    non_hdl = _num(getattr(patient, "non_hdl_c", None))
    ldl_c = _num(getattr(patient, "ldl_c", None))
    return sum(
        1
        for present in (
            _has_prediabetes(patient),
            _has_diabetes(patient),
            _bp_signal(patient),
            _ckm_context_signal(patient),
            tg is not None and tg >= 150,
            apob is not None and apob >= 100,
            non_hdl is not None and non_hdl >= 160,
            ldl_c is not None and ldl_c >= 130,
        )
        if present
    )


def _young_family_metabolic_trajectory(patient, result) -> bool:
    age = _num(getattr(patient, "age", None))
    prevent_category = _risk_value(getattr(result, "prevent_risk_category", None))
    return bool(
        age is not None
        and 30 <= age < 40
        and prevent_category == "LOW"
        and _has_premature_family_history(patient)
        and _metabolic_burden_count(patient) >= 2
    )


def _mild_signal_drivers(patient, result) -> list[str]:
    drivers = []
    if _has_prediabetes(patient):
        drivers.append("prediabetes-range A1c")
    tg = _num(getattr(patient, "triglycerides", None))
    if tg is not None and 150 <= tg < 500:
        drivers.append("triglycerides >=150")
    apob = _num(getattr(patient, "apob", None))
    if apob is not None and 80 <= apob < 120:
        drivers.append("ApoB/non-HDL burden")
    elif apob is None and _atherogenic_signal(patient):
        drivers.append("LDL/non-HDL burden")
    if _ckm_context_signal(patient):
        drivers.append("CKM context")
    if _lpa_elevated(patient):
        drivers.append("Lp(a)")
    if _has_premature_family_history(patient):
        drivers.append("premature family history")
    if _reproductive_signal_count(patient):
        drivers.append("reproductive risk marker")
    if _inflammatory_signal(patient):
        drivers.append("inflammatory/immune risk marker")
    if getattr(patient, "hiv", False):
        drivers.append("HIV")
    if getattr(patient, "south_asian_ancestry", False):
        drivers.append("South Asian ancestry")
    if getattr(patient, "filipino_ancestry", False):
        drivers.append("Filipino ancestry")
    hscrp = _num(getattr(patient, "hscrp", None))
    if hscrp is not None and hscrp >= 2:
        drivers.append("hsCRP >=2")
    prevent_category = _risk_value(getattr(result, "prevent_risk_category", None))
    if prevent_category in {"BORDERLINE", "INTERMEDIATE"}:
        drivers.append(f"PREVENT {str(prevent_category).lower()} 10-year risk")
    return drivers


def _actionable_burden_drivers(patient, result) -> list[str]:
    drivers = []
    if _albuminuria(patient):
        drivers.append("albuminuria")
    egfr = _num(getattr(patient, "egfr", None))
    if egfr is not None and egfr < 60:
        drivers.append("reduced kidney function")
    if _has_diabetes(patient):
        drivers.append("diabetes")
    if bool(getattr(patient, "smoker", False)) or bool(getattr(patient, "smoking", False)):
        drivers.append("current smoking")
    if _ldl_160_189(patient):
        drivers.append("LDL-C 160-189")
    if _severe_hyperchol(patient):
        drivers.append("severe hypercholesterolemia")
    if getattr(patient, "suspected_fh_hefh", False):
        drivers.append("suspected FH / HeFH")
    if _bp_signal(patient):
        drivers.append("BP-treated/elevated BP")
    apob = _num(getattr(patient, "apob", None))
    if apob is not None and apob >= 120:
        drivers.append("ApoB >=120")
    elif apob is not None and apob >= 100:
        drivers.append("ApoB/non-HDL burden")
    if _lpa_elevated(patient):
        drivers.append("Lp(a)")
    if _has_premature_family_history(patient):
        drivers.append("premature family history")
    if _reproductive_signal_count(patient):
        drivers.append("reproductive risk markers")
    if _has_prediabetes(patient):
        drivers.append("prediabetes")
    tg = _num(getattr(patient, "triglycerides", None))
    if tg is not None and tg >= 150:
        drivers.append("triglycerides >=150")
    if _ckm_context_signal(patient):
        drivers.append("CKM context")
    return drivers


def _plaque_status(patient) -> str:
    if bool(getattr(patient, "clinical_ascvd", False)):
        return "Clinical ASCVD"
    if bool(getattr(patient, "incidental_cac", False)) and getattr(patient, "cac", None) is None:
        severity = str(getattr(patient, "incidental_cac_severity", "") or "").strip()
        return f"Incidental CAC noted{f' ({severity})' if severity else ''}"
    cac = _num(getattr(patient, "cac", None))
    if cac is None:
        if bool(getattr(patient, "cac_not_done", False)):
            return "Plaque unmeasured / CAC not performed"
        return "Plaque unmeasured"
    if cac == 0:
        return "CAC 0 measured"
    return f"CAC {cac:g} measured"


def _classification(level, label, reason, drivers, result, patient, posture):
    deduped_drivers = []
    for driver in drivers:
        if driver and driver not in deduped_drivers:
            deduped_drivers.append(driver)
    return LevelClassification(
        level=level,
        label=label,
        short_reason=reason,
        drivers=deduped_drivers,
        prevent_category=_risk_value(getattr(result, "prevent_risk_category", None)),
        plaque_status=_plaque_status(patient),
        treatment_posture=posture,
    )


def classify_rcckm_level(patient, prevent_result=None, rss_result=None, diagnosis_context=None):
    """Classify a reviewed patient worksheet into the RCCKM level taxonomy.

    The function combines PREVENT outputs, plaque/ASCVD status, kidney signals,
    and cardiometabolic burden into a structured LevelClassification.
    """
    result = prevent_result
    cac = _num(getattr(patient, "cac", None))

    if bool(getattr(patient, "clinical_ascvd", False)):
        return _classification(
            "5",
            "Level 5 - clinical ASCVD / secondary prevention",
            "Clinical ASCVD overrides PREVENT and CAC de-risking.",
            ["clinical ASCVD"],
            result,
            patient,
            "secondary prevention",
        )

    if cac is not None and cac >= 300:
        return _classification(
            "5",
            "Level 5 - very high plaque burden",
            "CAC >=300 indicates very high-risk management intensity.",
            [f"CAC {cac:g}"],
            result,
            patient,
            "very-high plaque pathway",
        )

    if cac is not None and cac > 0:
        return _classification(
            "4",
            "Level 4 - subclinical atherosclerosis present",
            "Measured coronary calcium indicates plaque is present.",
            [f"CAC {cac:g}"],
            result,
            patient,
            "plaque-present pathway",
        )

    actionable = _actionable_burden_drivers(patient, result)
    mild = _mild_signal_drivers(patient, result)
    prevent_30y = _num(getattr(result, "prevent_30y_ascvd", None))
    elevated_30y = _age_30_to_59(patient) and prevent_30y is not None and prevent_30y >= 10
    prevent_category = _risk_value(getattr(result, "prevent_risk_category", None))

    if _severe_hyperchol(patient) or bool(getattr(patient, "suspected_fh_hefh", False)):
        return _classification(
            "3B",
            "Level 3B - actionable early CKM / atherogenic risk",
            "Severe hypercholesterolemia/FH pathway should not be de-risked by PREVENT or CAC 0.",
            ["severe hypercholesterolemia / suspected FH", *[d for d in actionable if d != "severe hypercholesterolemia"]],
            result,
            patient,
            "treatment-forward",
        )

    if _albuminuria(patient) and (len(actionable) >= 2 or mild):
        return _classification(
            "3B",
            "Level 3B - CKM stage 3 with albuminuria-mediated kidney and ASCVD risk",
            "Albuminuria plus cardiometabolic burden is actionable early kidney risk.",
            actionable or ["albuminuria"],
            result,
            patient,
            "domain action",
        )

    if elevated_30y:
        if actionable or len(mild) >= 2:
            return _classification(
                "3B",
                "Level 3B - actionable early CKM / atherogenic risk",
                "Elevated 30-year trajectory plus actionable biologic burden.",
                [f"30-year PREVENT ASCVD {prevent_30y:g}%", *actionable, *mild],
                result,
                patient,
                "treatment discussion",
            )
        return _classification(
            "3A",
            "Level 3A - elevated long-term risk trajectory",
            "30-year PREVENT ASCVD risk is treatment-relevant in adults age 30-59.",
            [f"30-year PREVENT ASCVD {prevent_30y:g}%"],
            result,
            patient,
            "prevention discussion",
        )

    if _ldl_160_189(patient):
        level = "3B" if len(actionable) >= 2 or len(mild) >= 2 else "3A"
        label = "Level 3A - elevated long-term risk trajectory"
        short_reason = "LDL-C 160-189 supports cumulative atherogenic exposure discussion."
        if level == "3B":
            if _young_family_metabolic_trajectory(patient, result):
                label = "Level 3B - elevated lifetime cardiometabolic risk despite low short-term event risk"
                short_reason = (
                    "Low short-term ASCVD risk with premature family history and metabolic signals creates a prevention opportunity."
                )
            else:
                label = "Level 3B - actionable early CKM / atherogenic risk"
        return _classification(
            level,
            label,
            short_reason,
            actionable or ["LDL-C 160-189"],
            result,
            patient,
            "treatment discussion",
        )

    enhancer_count = _enhancer_burden_count(patient)
    metabolic_count = _metabolic_burden_count(patient)
    if enhancer_count >= 2 and metabolic_count >= 1:
        return _classification(
            "3B",
            "Level 3B - actionable early CKM / atherogenic risk",
            "Multiple risk enhancers plus biologic burden make the trajectory no longer benign.",
            actionable or mild,
            result,
            patient,
            "prevention discussion",
        )

    if _lpa_elevated(patient) and metabolic_count >= 2:
        return _classification(
            "3B",
            "Level 3B - actionable early CKM / atherogenic risk",
            "Lp(a) plus family, reproductive, or metabolic burden supports early action discussion.",
            actionable or mild,
            result,
            patient,
            "prevention discussion",
        )

    apob = _num(getattr(patient, "apob", None))
    if apob is not None and apob >= 120:
        return _classification(
            "3A",
            "Level 3A - elevated long-term risk trajectory",
            "ApoB >=120 is a guideline risk-enhancing threshold.",
            actionable or ["ApoB >=120"],
            result,
            patient,
            "prevention discussion",
        )

    if "current smoking" in actionable:
        if _has_diabetes(patient) or len(actionable) >= 2:
            return _classification(
                "3B",
                "Level 3B - actionable early CKM / atherogenic risk",
                "Current smoking plus CKM/atherogenic burden is actionable.",
                actionable,
                result,
                patient,
                "risk-factor action",
            )
        return _classification(
            "3A",
            "Level 3A - elevated long-term risk trajectory",
            "Current smoking is a major modifiable ASCVD risk driver.",
            actionable,
            result,
            patient,
            "risk-factor action",
        )

    if (
        prevent_category in {"BORDERLINE", "INTERMEDIATE", "HIGH"}
        and (len(actionable) >= 2 or _albuminuria(patient) or len(mild) >= 3)
    ):
        return _classification(
            "3B",
            "Level 3B - actionable early CKM / atherogenic risk",
            "PREVENT category plus CKM/enhancer burden supports action discussion.",
            actionable or mild,
            result,
            patient,
            "treatment discussion",
        )

    if prevent_category == "HIGH" or _has_diabetes(patient) or _kidney_signal(patient):
        return _classification(
            "3B",
            "Level 3B - actionable early CKM / atherogenic risk",
            "Actionable clinical pathway is present without measured plaque.",
            actionable or mild,
            result,
            patient,
            "treatment-forward",
        )

    if len(mild) >= 2:
        return _classification(
            "2B",
            "Level 2B - converging early risk signals",
            "Multiple early signals are present without a treatment-forward pathway.",
            mild,
            result,
            patient,
            "lifestyle plus risk discussion",
        )

    if len(mild) == 1:
        return _classification(
            "2A",
            "Level 2A - early isolated risk signal",
            "One mild or early signal is present without convergence.",
            mild,
            result,
            patient,
            "lifestyle",
        )

    return _classification(
        "1",
        "Level 1 - minimal risk signal",
        "No meaningful early CKM, plaque, or ASCVD signal is present.",
        [],
        result,
        patient,
        "lifestyle",
    )
