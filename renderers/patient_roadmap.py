from html import escape
from textwrap import dedent

from modules.actions.scaffold import (
    build_action_recommendation_lines,
    build_compact_action_items,
)
from modules.lipids.non_hdl import format_non_hdl_display, should_show_non_hdl_default
from modules.lipids.statin_intensity import get_statin_intensity_definition
from modules.levels.definitions import classify_continuum_position, get_level_definition_payload
from modules.plaque.engine import format_cac_percentile_context
from modules.prevent.lipid_bands import LOW_10YR_HIGH_30YR_PATIENT_SUMMARY
from modules.risk_enhancers.breast_arterial_calcification import (
    BAC_PATIENT_CONTEXT_TEXT,
    has_breast_arterial_calcification,
)
from modules.risk_enhancers.masld import MASLD_CONTEXT_LABEL, MASLD_PATIENT_LABEL
from modules.risk_enhancers.reproductive import (
    reproductive_history_summary,
    reproductive_marker_items,
)
from ui.theme import component_theme_css


def _display_value(value):
    return getattr(value, "value", value)


def _fmt(value, suffix="", decimals=None):
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return f"{value}{suffix}"
    if decimals is not None:
        return f"{number:.{decimals}f}{suffix}"
    return f"{number:g}{suffix}"


def _risk_category(result):
    category = _display_value(getattr(result, "prevent_risk_category", None))
    if category:
        return str(category).replace("_", " ").lower()

    risk = getattr(result, "prevent_10y_ascvd", None)
    if risk is None:
        return "unavailable"
    try:
        value = float(risk)
    except (TypeError, ValueError):
        return "unavailable"
    if value < 3:
        return "low"
    if value < 5:
        return "borderline"
    if value < 10:
        return "intermediate"
    return "high"


def _has_early_metabolic_risk(patient, result):
    ckm_stage = getattr(result, "ckm_stage", None) or {}
    return bool(
        _risk_category(result) == "low"
        and ckm_stage.get("stage") in {1, 2}
        and (
            getattr(patient, "a1c", None) is not None
            or getattr(patient, "triglycerides", None) is not None
            or getattr(patient, "apob", None) is not None
            or reproductive_marker_items(patient)
        )
    )


def _has_elevated_lpa(patient):
    value = getattr(patient, "lp_a_value", None)
    unit = str(getattr(patient, "lp_a_unit", "") or "").strip()
    return bool(
        (unit == "nmol/L" and value is not None and value >= 125)
        or (unit == "mg/dL" and value is not None and value >= 50)
    )


def _has_premature_family_history(patient):
    return bool(
        getattr(patient, "premature_fhx_ascvd", False)
        or getattr(patient, "family_history_premature_ascvd", False)
    )


def _has_lpa_family_context(patient):
    return bool(_has_elevated_lpa(patient) and _has_premature_family_history(patient))


def _has_elevated_30y_trajectory(patient, result):
    age = getattr(patient, "age", None)
    prevent_30y = getattr(result, "prevent_30y_ascvd", None)
    return bool(age is not None and 30 <= age <= 59 and prevent_30y is not None and prevent_30y >= 10)


def _young_family_metabolic_trajectory(patient, result):
    if bool(getattr(patient, "clinical_ascvd", False)):
        return False
    age = getattr(patient, "age", None)
    if age is None or not (30 <= age < 40):
        return False
    if _risk_category(result) != "low":
        return False
    if not _has_premature_family_history(patient):
        return False
    try:
        position = classify_continuum_position(patient, result)
    except Exception:
        return False
    if position.get("level") != 3 or position.get("sublevel") != "3B":
        return False
    a1c = getattr(patient, "a1c", None)
    triglycerides = getattr(patient, "triglycerides", None)
    bmi = getattr(patient, "bmi", None)
    ldl_c = getattr(patient, "ldl_c", None)
    apob = getattr(patient, "apob", None)
    return bool(
        (a1c is not None and 5.7 <= a1c < 6.5)
        or (triglycerides is not None and triglycerides >= 150)
        or (bmi is not None and bmi >= 25)
        or (ldl_c is not None and 160 <= ldl_c < 190)
        or (apob is not None and apob >= 100)
    )


def _value_from_fields(result, field_names):
    for field_name in field_names:
        value = getattr(result, field_name, None)
        if value is not None:
            return value
    return None


def _total_cvd_value(result):
    return _value_from_fields(
        result,
        (
            "prevent_10y_total_cvd",
            "prevent_total_cvd_10y",
            "prevent_10y_total_cvd_pct",
            "total_cvd_10y_pct",
        ),
    )


def _ascvd_30y_value(result):
    return _value_from_fields(
        result,
        (
            "prevent_30y_ascvd",
            "prevent_30y_ascvd_pct",
            "ascvd_30y_pct",
        ),
    )


def _total_cvd_30y_value(result):
    return _value_from_fields(
        result,
        (
            "prevent_30y_total_cvd",
            "prevent_total_cvd_30y",
            "prevent_30y_total_cvd_pct",
            "total_cvd_30y_pct",
        ),
    )


def _prevent_age_value(result):
    return _value_from_fields(result, ("prevent_age", "prevent_cardiovascular_age"))


def _prevent_percentile_value(result):
    return _value_from_fields(result, ("prevent_percentile", "prevent_risk_percentile"))


def _prevent_explanation(risk):
    if risk is None:
        return "PREVENT estimate unavailable from the current data."
    try:
        people = max(0, int(float(risk) + 0.5))
    except (TypeError, ValueError):
        return "PREVENT estimate unavailable from the current data."
    return (
        f"About {people} out of 100 similar patients may have a "
        "heart attack, stroke, or related artery disease event over the next 10 years."
    )


def _prevent_30y_explanation(risk):
    if risk is None:
        return None
    try:
        people = max(0, int(float(risk) + 0.5))
    except (TypeError, ValueError):
        return None
    return (
        f"About {people} out of 100 similar patients may have a "
        "heart attack, stroke, or related artery disease event over the next 30 years."
    )


def _patient_risk_category_word(category):
    category_text = str(category or "").strip().lower()
    if category_text == "low":
        return "low"
    if category_text in {"borderline", "intermediate"}:
        return "moderate"
    if category_text == "high":
        return "high"
    return "not fully calculated"


def _primary_prevention_risk_summary_sentence(result, ascvd_30y):
    category_word = _patient_risk_category_word(_risk_category(result))
    if ascvd_30y is None:
        return f"Your 10-year ASCVD risk is {category_word}."
    try:
        elevated_30y = float(ascvd_30y) >= 10
    except (TypeError, ValueError):
        elevated_30y = False
    try:
        low_short_term = getattr(result, "prevent_10y_ascvd", None) is not None and float(
            getattr(result, "prevent_10y_ascvd", None)
        ) < 5
    except (TypeError, ValueError):
        low_short_term = category_word == "low"
    if low_short_term and elevated_30y:
        return LOW_10YR_HIGH_30YR_PATIENT_SUMMARY
    if elevated_30y:
        return (
            f"Your 10-year ASCVD risk is {category_word}, and your "
            "30-year risk is elevated enough to make prevention worth discussing."
        )
    return (
        f"Your 10-year ASCVD risk is {category_word}, and your "
        "30-year ASCVD risk helps guide prevention planning."
    )


def _has_clinical_ascvd(patient, result):
    return bool(
        getattr(patient, "clinical_ascvd", False)
        or getattr(result, "clinical_ascvd", False)
    )


def _has_severe_ldl_or_fh_pathway(patient, result):
    ldl_c = getattr(patient, "ldl_c", None)
    return bool(
        (ldl_c is not None and ldl_c >= 190)
        or getattr(patient, "suspected_fh_hefh", False)
        or getattr(result, "severe_hypercholesterolemia", False)
        or getattr(result, "possible_fh_pathway", False)
    )


def _has_measured_coronary_plaque(patient, result):
    cac = getattr(patient, "cac", None)
    if cac is not None:
        try:
            return float(cac) > 0
        except (TypeError, ValueError):
            return False
    plaque_category = _display_value(getattr(result, "plaque_category", None))
    return str(plaque_category or "").upper() not in {"", "NONE", "UNKNOWN"}


def build_patient_risk_summary_sentence(patient, result, ascvd_30y=None):
    """Build the patient-facing Where-you-stand summary from engine outputs."""
    if _has_clinical_ascvd(patient, result):
        return (
            "Known cardiovascular disease is present. The focus is secondary "
            "prevention: lowering the chance of future heart attack, stroke, "
            "or related artery disease events."
        )
    if _has_severe_ldl_or_fh_pathway(patient, result):
        return (
            "LDL-C is in a severe hypercholesterolemia range, so lipid-lowering "
            "decisions should not rely on risk estimates alone."
        )
    if _has_measured_coronary_plaque(patient, result):
        return (
            "Coronary plaque is present, so prevention decisions should account "
            "for measured plaque burden in addition to risk estimates."
        )

    risk_10y = getattr(result, "prevent_10y_ascvd", None)
    if risk_10y is None:
        return ""
    try:
        low_short_term = risk_10y is not None and float(risk_10y) < 5
    except (TypeError, ValueError):
        low_short_term = _patient_risk_category_word(_risk_category(result)) == "low"
    try:
        elevated_30y = ascvd_30y is not None and float(ascvd_30y) >= 10
    except (TypeError, ValueError):
        elevated_30y = False
    if low_short_term and elevated_30y:
        return LOW_10YR_HIGH_30YR_PATIENT_SUMMARY

    try:
        high_10y = risk_10y is not None and float(risk_10y) >= 7.5
    except (TypeError, ValueError):
        high_10y = False
    if high_10y or _patient_risk_category_word(_risk_category(result)) == "high":
        return (
            "Your 10-year ASCVD risk is elevated, so prevention and "
            "lipid-lowering therapy should be discussed with your clinician."
        )

    return _primary_prevention_risk_summary_sentence(result, ascvd_30y)


def _patient_safe_phrase(text):
    """Convert action-engine wording into calmer patient-facing language."""
    cleaned = str(text or "")
    for source, target in (
        ("Optimize", "Improve"),
        ("optimize", "improve"),
        ("Intensifying", "Changing"),
        ("intensifying", "changing"),
        ("Intensify", "Increase"),
        ("intensify", "increase"),
        ("Pharmacotherapy", "Medication"),
        ("pharmacotherapy", "medication"),
        ("Risk enhancer", "Risk factor"),
        ("risk enhancer", "risk factor"),
        ("Treatment posture", "Care plan"),
        ("treatment posture", "care plan"),
        ("Dominant action", "Main step"),
        ("dominant action", "main step"),
    ):
        cleaned = cleaned.replace(source, target)
    return cleaned


def _prevent_unavailable_reason_text(result):
    missing = list(getattr(result, "prevent_missing_inputs", None) or [])
    if missing:
        return "Missing inputs: " + ", ".join(str(item) for item in missing)
    unsupported = str(getattr(result, "prevent_unsupported_reason", "") or "").strip()
    if unsupported:
        return unsupported
    return "Complete the missing worksheet inputs to calculate estimated population risk."


def _naturalize_level_detail(text):
    return (
        str(text or "")
        .replace("Very high risk / ASCVD intensity", "Very high risk")
        .replace("Very high risk / high plaque burden", "Very high risk")
        .replace("ASCVD-intensity phenotype", "high plaque burden")
        .replace("ASCVD intensity", "high plaque burden")
    )


def _continuum_label(patient, result):
    try:
        position = classify_continuum_position(patient, result)
        level = position.get("level")
        sublevel = position.get("sublevel")
        if _young_family_metabolic_trajectory(patient, result):
            return (
                "Level 3B",
                "elevated lifetime cardiometabolic risk despite low short-term event risk",
            )
        payload = get_level_definition_payload(level, sublevel=sublevel)
        label = f"Level {level}"
        if sublevel:
            label = f"{label} ({sublevel})"
        level_label = _naturalize_level_detail(payload.get("sublevel_label") or payload.get("label"))
        return label, level_label or ""
    except Exception:
        risk_level = _display_value(getattr(result, "risk_level", None))
        return str(risk_level or "Not assigned"), ""


def _plaque_status(patient, result):
    cac = getattr(patient, "cac", None)
    if getattr(patient, "clinical_ascvd", False):
        return "Clinical ASCVD present"
    if cac is not None:
        try:
            value = float(cac)
        except (TypeError, ValueError):
            return f"CAC {cac}"
        if value >= 300:
            return f"CAC {value:g}"
        if value > 0:
            return f"CAC {value:g}; plaque present"
        return "CAC 0; no coronary calcium detected"

    plaque = _display_value(getattr(result, "plaque_category", None))
    if plaque:
        plaque_text = str(plaque).replace("_", " ").lower()
        if plaque_text == "unknown":
            return "Plaque status: unmeasured"
        return plaque_text
    return "Plaque status: unmeasured"


def _patient_plaque_status(patient, result):
    cac = getattr(patient, "cac", None)
    percentile_context = format_cac_percentile_context(
        cac, getattr(patient, "cac_percentile", None)
    )
    if getattr(patient, "clinical_ascvd", False):
        return "Known cardiovascular disease is present."
    if cac is not None:
        try:
            value = float(cac)
        except (TypeError, ValueError):
            return f"Coronary calcium score: {cac}."
        if value >= 300:
            return f"Coronary calcium score: {value:g}, showing a high amount of plaque."
        if value >= 100:
            text = f"Coronary calcium score: {value:g}, showing moderate calcified plaque burden."
            return f"{text} {percentile_context}" if percentile_context else text
        if value > 0:
            text = f"Coronary calcium score: {value:g}, showing mild calcified plaque detected."
            return f"{text} {percentile_context}" if percentile_context else text
        return "Coronary calcium score: 0, with no calcified plaque detected."
    return "Plaque status has not been measured."


def _bp_value(patient):
    sbp = getattr(patient, "sbp", None)
    dbp = getattr(patient, "dbp", None)
    if sbp is None and dbp is None:
        return None
    if sbp is not None and dbp is not None:
        text = f"{_fmt(sbp)}/{_fmt(dbp)} mmHg"
    elif sbp is not None:
        text = f"SBP {_fmt(sbp)} mmHg"
    else:
        text = f"DBP {_fmt(dbp)} mmHg"
    if getattr(patient, "bp_treated", False):
        text = f"{text}; treated"
    return text


def _inflammatory_context(patient):
    labels = []
    for field, label in (
        ("rheumatoid_arthritis", "RA"),
        ("sle", "SLE"),
        ("psoriasis", "psoriasis"),
        ("inflammatory_arthritis", "inflammatory arthritis"),
        ("ibd", "IBD"),
    ):
        if getattr(patient, field, False):
            labels.append(label)
    if getattr(patient, "inflammatory_disease", False) and not labels:
        labels.append("inflammatory/immune condition")
    return labels


def _contributor_groups(patient, result):
    groups = []

    cac = getattr(patient, "cac", None)
    if getattr(patient, "clinical_ascvd", False) or cac is not None:
        plaque_detail = _plaque_status(patient, result)
        if cac is not None:
            try:
                cac_value = float(cac)
                percentile_detail = format_cac_percentile_context(
                    cac_value,
                    getattr(patient, "cac_percentile", None),
                    include_clinician_detail=True,
                )
                if cac_value >= 300:
                    plaque_detail = f"CAC {cac_value:g}; high plaque burden"
                elif cac_value >= 100:
                    plaque_detail = f"CAC {cac_value:g}; moderate plaque burden"
                elif cac_value > 0:
                    plaque_detail = f"CAC {cac_value:g}; mild plaque present"
                if percentile_detail and 0 < cac_value < 300:
                    plaque_detail = f"{plaque_detail}; {percentile_detail}"
            except (TypeError, ValueError):
                pass
        groups.append(("Artery plaque", plaque_detail))

    apob = getattr(patient, "apob", None)
    ldl = getattr(patient, "ldl_c", None)
    lipids = []
    if apob is not None:
        lipids.append(f"ApoB {_fmt(apob)} mg/dL")
    if ldl is not None:
        lipids.append(f"LDL-C {_fmt(ldl)} mg/dL")
    non_hdl = format_non_hdl_display(patient, result) if should_show_non_hdl_default(patient, result) else None
    if non_hdl:
        lipids.append(f"non-HDL-C {_fmt(non_hdl['current_value'])} mg/dL calculated")
    if lipids:
        groups.append(("Cholesterol particles", "; ".join(lipids)))

    a1c = getattr(patient, "a1c", None)
    diabetes = bool(getattr(patient, "diabetes", False)) or (
        a1c is not None and a1c >= 6.5
    )
    egfr = getattr(patient, "egfr", None)
    uacr = getattr(patient, "uacr", None)
    kdigo = getattr(result, "kdigo_stage", None)
    kidney_bits = []
    if a1c is not None:
        kidney_bits.append(f"A1c {_fmt(a1c, '%', 1)}")
    elif diabetes:
        kidney_bits.append("diabetes")
    if egfr is not None:
        kidney_bits.append(f"eGFR {_fmt(egfr)}")
    if uacr is not None:
        kidney_bits.append(f"UACR {_fmt(uacr)} mg/g")
    if kdigo:
        kidney_bits.append(f"KDIGO {kdigo}")
    if diabetes and (egfr is not None or uacr is not None or kdigo):
        groups.append(("Diabetes / kidney involvement", "; ".join(kidney_bits)))
    elif diabetes or a1c is not None:
        groups.append(("Blood sugar / metabolic", "; ".join(kidney_bits)))
    elif egfr is not None or uacr is not None or kdigo:
        kidney_only = []
        if egfr is not None:
            kidney_only.append(f"eGFR {_fmt(egfr)}")
        if uacr is not None:
            kidney_only.append(f"UACR {_fmt(uacr)} mg/g")
        if kdigo:
            kidney_only.append(f"KDIGO {kdigo}")
        groups.append(("Kidney markers", "; ".join(kidney_only)))

    other_context = []

    lpa = getattr(patient, "lp_a_value", None)
    lpa_unit = getattr(patient, "lp_a_unit", None)
    if lpa is not None:
        other_context.append(f"Lp(a) {_fmt(lpa)} {lpa_unit or ''}".strip())

    bp = _bp_value(patient)
    if bp:
        other_context.append(f"BP {bp}")

    if getattr(patient, "smoker", False) or getattr(patient, "smoking", False):
        other_context.append("current smoking")

    family_summary = getattr(patient, "family_history_summary", None)
    if family_summary or getattr(patient, "premature_fhx_ascvd", False) or getattr(
        patient, "family_history_premature_ascvd", False
    ):
        other_context.append(family_summary or "premature family history")

    hscrp = getattr(patient, "hscrp", None)
    if hscrp is not None:
        other_context.append(f"hsCRP {_fmt(hscrp, ' mg/L', 1)}")

    inflammatory = _inflammatory_context(patient)
    if inflammatory:
        other_context.append("Inflammatory/immune: " + ", ".join(inflammatory))

    if getattr(patient, "osa", False):
        other_context.append("OSA")

    if getattr(patient, "masld", False):
        other_context.append(MASLD_CONTEXT_LABEL)

    if getattr(patient, "hiv", False):
        other_context.append("HIV on stable ART" if getattr(patient, "stable_art", False) else "HIV")
    if getattr(patient, "south_asian_ancestry", False):
        other_context.append("South Asian ancestry")
    if getattr(patient, "filipino_ancestry", False):
        other_context.append("Filipino ancestry")
    if getattr(patient, "active_cancer", False):
        other_context.append("active cancer context")
    elif getattr(patient, "cancer_survivor", False):
        other_context.append("cancer survivor context")
    if getattr(patient, "incidental_cac", False) and getattr(patient, "cac", None) is None:
        other_context.append("incidental CAC noted")
    if has_breast_arterial_calcification(patient):
        other_context.append("breast arterial calcification on mammogram")

    reproductive_summary = reproductive_history_summary(patient, patient_facing=True)
    if reproductive_summary:
        other_context.append(reproductive_summary)

    if other_context:
        groups.append(("Other context", "; ".join(other_context)))

    if not groups:
        for driver in getattr(result, "top_drivers", []) or []:
            groups.append(("Clinical signal", str(driver)))

    return groups


def _patient_contributor_groups(patient, result):
    groups = []

    cac = getattr(patient, "cac", None)
    if getattr(patient, "clinical_ascvd", False):
        groups.append(
            (
                "Artery plaque",
                "Known cardiovascular disease",
                "This means prevention decisions should be more treatment-focused.",
                "red",
            )
        )
    elif cac is not None:
        try:
            value = float(cac)
        except (TypeError, ValueError):
            value = None
        if value is not None and value >= 300:
            groups.append(
                (
                    "Artery plaque",
                    f"CAC {value:g}",
                    "The calcium score shows a high amount of coronary plaque.",
                    "red",
                )
            )
        elif value is not None and value > 0:
            groups.append(
                (
                    "Artery plaque",
                    f"CAC {value:g}",
                    "Calcium is present, which means plaque is present.",
                    "amber",
                )
            )
        elif value == 0:
            groups.append(
                (
                    "Artery plaque",
                    "CAC 0",
                    "No calcified coronary plaque was detected on this test.",
                    "green",
                )
            )

    if has_breast_arterial_calcification(patient):
        groups.append(
            (
                "Imaging context",
                "Breast arterial calcification",
                BAC_PATIENT_CONTEXT_TEXT,
                "blue",
            )
        )

    apob = getattr(patient, "apob", None)
    ldl = getattr(patient, "ldl_c", None)
    lipid_bits = []
    if apob is not None:
        lipid_bits.append(f"ApoB {_fmt(apob)}")
    if ldl is not None:
        lipid_bits.append(f"LDL-C {_fmt(ldl)}")
    non_hdl = format_non_hdl_display(patient, result) if should_show_non_hdl_default(patient, result) else None
    if non_hdl:
        lipid_bits.append(f"non-HDL-C {_fmt(non_hdl['current_value'])} (calculated)")
    if lipid_bits:
        groups.append(
            (
                "Cholesterol particles",
                "; ".join(lipid_bits),
                "These numbers help show plaque-driving cholesterol in the blood.",
                "amber",
            )
        )

    a1c = getattr(patient, "a1c", None)
    diabetes = bool(getattr(patient, "diabetes", False)) or (
        a1c is not None and a1c >= 6.5
    )
    if diabetes or a1c is not None:
        finding = f"A1c {_fmt(a1c, '%', 1)}" if a1c is not None else "Diabetes"
        groups.append(
            (
                "Blood sugar / diabetes",
                finding,
                "Improving blood sugar can lower long-term heart, kidney, and metabolic risk.",
                "orange" if diabetes else "amber",
            )
        )

    egfr = getattr(patient, "egfr", None)
    uacr = getattr(patient, "uacr", None)
    kidney_bits = []
    if egfr is not None:
        kidney_bits.append(f"eGFR {_fmt(egfr)}")
    if uacr is not None:
        kidney_bits.append(f"UACR {_fmt(uacr)}")
    if kidney_bits:
        groups.append(
            (
                "Kidney protection",
                "; ".join(kidney_bits),
                "Kidney markers also help estimate heart and metabolic risk.",
                "green" if not diabetes else "blue",
            )
        )

    bp = _bp_value(patient)
    if bp:
        groups.append(
            (
                "Blood pressure",
                bp,
                "Keeping blood pressure in a safer range protects the heart, brain, and kidneys.",
                "blue",
            )
        )

    other = []
    lpa = getattr(patient, "lp_a_value", None)
    if lpa is not None:
        other.append(f"Lp(a) {_fmt(lpa)} {getattr(patient, 'lp_a_unit', None) or ''}".strip())
    family_summary = getattr(patient, "family_history_summary", None)
    if family_summary or getattr(patient, "family_history_premature_ascvd", False):
        other.append(family_summary or "family history")
    hscrp = getattr(patient, "hscrp", None)
    if hscrp is not None:
        other.append(f"hsCRP {_fmt(hscrp, ' mg/L', 1)}")
    if getattr(patient, "smoker", False) or getattr(patient, "smoking", False):
        other.append("current smoking")
    if getattr(patient, "osa", False):
        other.append("OSA")
    if getattr(patient, "masld", False):
        other.append(MASLD_PATIENT_LABEL)
    inflammatory = _inflammatory_context(patient)
    if inflammatory:
        other.append(", ".join(inflammatory))
    reproductive_summary = reproductive_history_summary(patient, patient_facing=True)
    if reproductive_summary:
        other.append(reproductive_summary)
    if other:
        groups.append(
            (
                "Other factors",
                "; ".join(other),
                (
                    "Pregnancy or menopause history can affect long-term heart risk."
                    if reproductive_marker_items(patient)
                    else "These details can shape the prevention plan with your clinician."
                ),
                "gray",
            )
        )

    return groups


def _target_rows(patient, result):
    rows = []
    target = result.targets[0] if getattr(result, "targets", None) else None

    if getattr(patient, "ldl_c", None) is not None or (
        target and target.ldl_c_target is not None
    ):
        rows.append(
            (
                "LDL-C",
                _fmt(getattr(patient, "ldl_c", None), " mg/dL") or "-",
                f"<{_fmt(target.ldl_c_target)} mg/dL" if target and target.ldl_c_target is not None else "-",
            )
        )
    non_hdl = format_non_hdl_display(patient, result) if should_show_non_hdl_default(patient, result) else None
    if non_hdl:
        rows.append(
            (
                "non-HDL-C",
                (_fmt(non_hdl["current_value"], " mg/dL") or "-") + " calculated",
                f"<{_fmt(non_hdl['target_value'])} mg/dL",
            )
        )
    if getattr(patient, "apob", None) is not None or (
        target and target.apob_target is not None
    ):
        rows.append(
            (
                "ApoB",
                _fmt(getattr(patient, "apob", None), " mg/dL") or "-",
                f"<{_fmt(target.apob_target)} mg/dL" if target and target.apob_target is not None else "-",
            )
        )
    if getattr(patient, "a1c", None) is not None:
        rows.append(("A1c", _fmt(getattr(patient, "a1c", None), "%", 1), "individualized"))
    bp = _bp_value(patient)
    if bp:
        rows.append(("BP", bp, "<130/80 when appropriate"))
    if getattr(patient, "uacr", None) is not None or getattr(result, "kdigo_stage", None):
        rows.append(
            (
                "Kidney / albuminuria",
                "; ".join(
                    bit
                    for bit in (
                        _fmt(getattr(patient, "uacr", None), " mg/g"),
                        getattr(result, "kdigo_stage", None),
                    )
                    if bit
                ),
                "reduce albuminuria / preserve eGFR",
            )
        )
    if getattr(patient, "bmi", None) is not None:
        rows.append(("Weight", f"BMI {_fmt(getattr(patient, 'bmi', None), '', 1)}", "individualized"))

    return rows


def _recommendation_label(text):
    lowered = str(text or "").lower()
    if "lipid" in lowered or "statin" in lowered:
        return "Lipid therapy"
    if "kidney" in lowered or "uacr" in lowered or "albuminuria" in lowered:
        return "Kidney protection"
    if "glycemic" in lowered or "a1c" in lowered or "diabetes" in lowered:
        return "Glycemia"
    if "bp" in lowered or "blood pressure" in lowered:
        return "Blood pressure"
    if "coronary calcium" in lowered or "cac" in lowered:
        return "Coronary calcium"
    if "aspirin" in lowered or "antiplatelet" in lowered:
        return "Aspirin"
    if "clarification" in lowered or "check lp(a)" in lowered or "obtain apob" in lowered or "hscrp" in lowered:
        return "Clarification"
    if "smoking" in lowered:
        return "Smoking"
    return "Plan"


def _recommendation_items(patient, result):
    items = build_action_recommendation_lines(patient, result)
    if not items:
        items.append("Continue clinician-guided prevention review.")
    return items


def _recommendation_rows(patient, result):
    return [(_recommendation_label(item), item) for item in _recommendation_items(patient, result)]


def _patient_next_steps(patient, result):
    compact_items = build_compact_action_items(patient, result, max_items=5)
    compact_rows = []
    compact_seen = set()
    for item in compact_items:
        lowered = f"{item.title} {item.subtitle}".lower()
        if "lipid" in lowered or "statin" in lowered or "cholesterol" in lowered:
            label = "Lower plaque-driving cholesterol"
            if "high-intensity" in lowered or "high-risk targets" in lowered:
                detail = "Discuss stronger cholesterol-lowering therapy."
            elif "moderate-intensity" in lowered:
                detail = "Discuss cholesterol-lowering therapy."
            elif "very-high-risk ascvd targets" in lowered:
                detail = "Because heart artery disease is already established and additional high-risk features are present, the LDL cholesterol goal is lower than for routine prevention."
            else:
                detail = "Treat toward the cholesterol goals above."
        elif "protect kidneys" in lowered:
            label = "Protect the kidneys"
            detail = "Review kidney protection options with your clinician."
        elif "glycemia" in lowered:
            label = "Improve blood sugar trajectory"
            detail = "Keep diabetes care moving toward the safest individualized goal."
        elif "plaque" in lowered or "cac" in lowered or "calcium" in lowered:
            label = "Additional testing"
            detail = "A calcium scan may help if treatment choices are still uncertain."
        elif "aspirin" in lowered or "antiplatelet" in lowered:
            label = "Aspirin safety"
            detail = "Do not start aspirin unless your clinician recommends it."
        elif "lifestyle" in lowered:
            label = "Long-term prevention"
            detail = "Focus on weight, blood sugar, triglycerides, and long-term prevention."
        else:
            label = item.title
            detail = item.subtitle or "Continue prevention review with your clinician."
        key = (label, detail)
        if key not in compact_seen:
            compact_seen.add(key)
            compact_rows.append(key)
    if compact_rows:
        return compact_rows

    rows = []
    seen = set()
    for item in _recommendation_items(patient, result):
        lowered = str(item or "").lower()
        if "no repeat cac" in lowered:
            continue
        elif "obtain uacr" in lowered or "uacr" in lowered and "missing" in lowered:
            label = "Additional testing"
            detail = "Urine albumin test can help check early kidney stress."
        elif "cac reasonable" in lowered or "cac not routinely recommended" in lowered or "plaque burden unmeasured" in lowered:
            label = "Additional testing"
            detail = "A calcium scan may help if treatment choices are still uncertain."
        elif "hscrp" in lowered:
            label = "Additional testing"
            detail = "hsCRP can help clarify inflammatory risk context when clinically relevant."
        elif "very-high-risk ascvd targets" in lowered:
            label = "Lower plaque-driving cholesterol"
            detail = "Because heart artery disease is already established and additional high-risk features are present, the LDL cholesterol goal is lower than for routine prevention."
        elif "high-intensity statin" in lowered or "high-intensity lipid" in lowered:
            label = "Lower plaque-driving cholesterol"
            detail = "Discuss stronger cholesterol-lowering therapy."
        elif "moderate-intensity statin" in lowered or "moderate-intensity lipid" in lowered:
            label = "Lower plaque-driving cholesterol"
            detail = "Discuss cholesterol-lowering therapy."
        elif "lipid" in lowered or "statin" in lowered:
            label = "Lower plaque-driving cholesterol"
            detail = "Treat toward the cholesterol goals above."
        elif "kidney" in lowered or "uacr" in lowered or "albuminuria" in lowered:
            label = "Protect the kidneys"
            detail = "Review kidney protection options with your clinician."
        elif "glycemic" in lowered or "diabetes" in lowered or "a1c" in lowered:
            label = "Improve blood sugar trajectory"
            detail = "Keep diabetes care moving toward the safest individualized goal."
        elif "blood pressure" in lowered or "bp" in lowered:
            label = "Keep blood pressure in a safer range"
            detail = "Use lifestyle and medicines as appropriate."
        elif "aspirin" in lowered or "antiplatelet" in lowered:
            label = "Aspirin safety"
            detail = "Do not start aspirin unless your clinician recommends it."
        elif "no medication escalation" in lowered:
            label = "Medication plan"
            if "risk discussion" in lowered:
                detail = "No medication escalation required today; review Lp(a), family history, and long-term prevention options."
            else:
                detail = "No medication escalation today."
        elif "continue lifestyle" in lowered:
            label = "Long-term prevention"
            detail = "Focus on weight, blood sugar, triglycerides, and long-term prevention."
        elif "clarification testing should not delay treatment" in lowered:
            label = "Optional testing"
            detail = "Do not delay treatment while completing optional testing."
        elif "lp(a)" in lowered:
            label = "Additional testing"
            detail = "Lp(a) can be checked once to guide long-term prevention."
        else:
            label = "Next step"
            detail = _patient_safe_phrase(item)
        key = (label, detail)
        if key not in seen:
            seen.add(key)
            rows.append(key)
    has_statin_definition = any(
        label == "Lower plaque-driving cholesterol" and "usually lowers LDL cholesterol" in detail
        for label, detail in rows
    )
    if has_statin_definition:
        rows = [
            row
            for row in rows
            if row != ("Lower plaque-driving cholesterol", "Treat toward the cholesterol goals above.")
        ]
    order = {
        "Lower plaque-driving cholesterol": 0,
        "Protect the kidneys": 1,
        "Improve blood sugar trajectory": 2,
        "Keep blood pressure in a safer range": 3,
        "Medication plan": 4,
        "Long-term prevention": 5,
        "Aspirin safety": 6,
        "Additional testing": 7,
        "Optional testing": 8,
    }
    rows.sort(key=lambda row: order.get(row[0], 99))
    return rows or [("Next step", "Continue prevention review with your clinician.")]


def _risk_badge_text(category, patient):
    category_text = str(category or "").lower()
    cac = getattr(patient, "cac", None)
    try:
        cac_value = float(cac) if cac is not None else None
    except (TypeError, ValueError):
        cac_value = None
    if category_text in {"high", "intermediate"} or (
        cac_value is not None and cac_value >= 100
    ):
        return "Higher risk: action recommended"
    if category_text == "borderline":
        return "Risk discussion recommended"
    if category_text == "low":
        return "Lower estimated risk"
    return "Review with your clinician"


def _patient_risk_cards_html(risk, ascvd_30y):
    cards = []
    if risk is not None:
        cards.append(
            (
                "10-year ASCVD risk",
                "ASCVD risk: heart attack, stroke, or related artery disease event",
                _fmt(risk, "%"),
                _prevent_explanation(risk),
                "blue",
            )
        )
    else:
        cards.append(
            (
                "10-year ASCVD risk",
                "ASCVD risk: heart attack, stroke, or related artery disease event",
                "Unavailable",
                "More information is needed to calculate this estimate.",
                "gray",
            )
        )
    if ascvd_30y is not None:
        line = _prevent_30y_explanation(ascvd_30y) or "This longer-term estimate helps guide prevention planning."
        cards.append(
            (
                "30-year ASCVD risk",
                "ASCVD risk: heart attack, stroke, or related artery disease event",
                _fmt(ascvd_30y, "%"),
                line,
                "green",
            )
        )

    return "".join(
        f'<div class="roadmap-risk-card roadmap-tone-{tone}">'
        f'<div class="roadmap-risk-label">{escape(label)}</div>'
        f'<div class="roadmap-risk-subtitle">{escape(subtitle)}</div>'
        f'<div class="roadmap-risk-value">{escape(value or "--")}</div>'
        f'<div class="roadmap-risk-text">{escape(text)}</div>'
        "</div>"
        for label, subtitle, value, text, tone in cards
    )


def _patient_contributor_cards_html(groups):
    if not groups:
        return '<div class="roadmap-muted">No major measured factors were identified from the current worksheet.</div>'
    return "".join(
        f'<div class="roadmap-factor roadmap-tone-{tone}">'
        f'<div class="roadmap-factor-title">{escape(label)}</div>'
        f'<div class="roadmap-factor-finding">{escape(finding)}</div>'
        f'<div class="roadmap-factor-note">{escape(note)}</div>'
        "</div>"
        for label, finding, note, tone in groups
    )


def _patient_driver_sections(patient, result):
    priority = []
    context = []

    cac = getattr(patient, "cac", None)
    if getattr(patient, "clinical_ascvd", False):
        priority.append(
            (
                "Known cardiovascular disease",
                "Prevention decisions should be more treatment-focused.",
                "red",
            )
        )
    elif cac is not None:
        try:
            value = float(cac)
        except (TypeError, ValueError):
            value = None
        if value is not None and value >= 300:
            priority.append((f"Coronary calcium score {value:g} - high plaque burden", "Coronary calcium shows a high amount of plaque.", "red"))
        elif value is not None and value >= 100:
            percentile_context = format_cac_percentile_context(
                value, getattr(patient, "cac_percentile", None)
            )
            note = "Coronary calcium shows a moderate amount of plaque."
            if percentile_context:
                note = f"{note} {percentile_context}"
            priority.append((f"Coronary calcium score {value:g} - moderate plaque burden", note, "amber"))
        elif value is not None and value > 0:
            percentile_context = format_cac_percentile_context(
                value, getattr(patient, "cac_percentile", None)
            )
            note = "Coronary calcium shows mild calcified plaque."
            if percentile_context:
                note = f"{note} {percentile_context}"
            priority.append((f"Coronary calcium score {value:g} - mild plaque", note, "amber"))
        elif value == 0:
            context.append("CAC 0")

    if has_breast_arterial_calcification(patient):
        context.append(BAC_PATIENT_CONTEXT_TEXT)

    apob = getattr(patient, "apob", None)
    ldl = getattr(patient, "ldl_c", None)
    if apob is not None:
        lipid_bits = [f"ApoB {_fmt(apob)}"]
        if ldl is not None:
            lipid_bits.append(f"LDL-C {_fmt(ldl)}")
        non_hdl = format_non_hdl_display(patient, result) if should_show_non_hdl_default(patient, result) else None
        if non_hdl:
            lipid_bits.append(f"non-HDL-C {_fmt(non_hdl['current_value'])} calculated")
        priority.append(
            (
                f"ApoB {_fmt(apob)} - elevated particle burden",
                "ApoB reflects cholesterol-carrying particles that can contribute to plaque. "
                + "; ".join(lipid_bits)
                + ".",
                "amber",
            )
        )
    elif ldl is not None or should_show_non_hdl_default(patient, result):
        lipid_bits = []
        if ldl is not None:
            lipid_bits.append(f"LDL-C {_fmt(ldl)}")
        non_hdl = format_non_hdl_display(patient, result) if should_show_non_hdl_default(patient, result) else None
        if non_hdl:
            lipid_bits.append(f"non-HDL-C {_fmt(non_hdl['current_value'])} calculated")
        priority.append(("Cholesterol particles", "These numbers show plaque-driving cholesterol in the blood. Current values: " + "; ".join(lipid_bits) + ".", "amber"))

    a1c = getattr(patient, "a1c", None)
    diabetes = bool(getattr(patient, "diabetes", False)) or (
        a1c is not None and a1c >= 6.5
    )
    egfr = getattr(patient, "egfr", None)
    uacr = getattr(patient, "uacr", None)
    kdigo = getattr(result, "kdigo_stage", None)
    kidney_bits = []
    if a1c is not None:
        kidney_bits.append(f"A1c {_fmt(a1c, '%', 1)}")
    elif diabetes:
        kidney_bits.append("diabetes")
    if egfr is not None:
        kidney_bits.append(f"eGFR {_fmt(egfr)}")
    if uacr is not None:
        kidney_bits.append(f"UACR {_fmt(uacr)}")
    if kdigo:
        kidney_bits.append(f"KDIGO {kdigo}")
    if kidney_bits and (diabetes or egfr is not None or uacr is not None):
        if diabetes and (egfr is not None or uacr is not None or kdigo):
            label = "Diabetes / kidney involvement"
            detail = "Blood sugar and kidney markers add to long-term risk. "
        else:
            label = "Blood sugar / kidney"
            detail = "Blood sugar and kidney markers help guide prevention. "
        priority.append((label, detail + "; ".join(kidney_bits) + ".", "blue" if diabetes else "green"))

    lpa = getattr(patient, "lp_a_value", None)
    if lpa is not None:
        context.append(f"Lp(a) {_fmt(lpa)} {getattr(patient, 'lp_a_unit', None) or ''}".strip())
    bp = _bp_value(patient)
    if bp:
        context.append(f"BP {bp.replace(' mmHg', '')}")
    family_summary = getattr(patient, "family_history_summary", None)
    if family_summary or getattr(patient, "family_history_premature_ascvd", False):
        context.append(family_summary or "family history")
    hscrp = getattr(patient, "hscrp", None)
    if hscrp is not None:
        context.append(f"hsCRP {_fmt(hscrp, ' mg/L', 1)}")
    if getattr(patient, "smoker", False) or getattr(patient, "smoking", False):
        context.append("current smoking")
    if getattr(patient, "osa", False):
        context.append("OSA")
    if getattr(patient, "masld", False):
        context.append(MASLD_CONTEXT_LABEL)
    if getattr(patient, "hiv", False):
        context.append("HIV on stable ART" if getattr(patient, "stable_art", False) else "HIV")
    if getattr(patient, "south_asian_ancestry", False):
        context.append("South Asian ancestry")
    if getattr(patient, "filipino_ancestry", False):
        context.append("Filipino ancestry")
    if getattr(patient, "active_cancer", False):
        context.append("active cancer context")
    elif getattr(patient, "cancer_survivor", False):
        context.append("cancer survivor context")
    if getattr(patient, "incidental_cac", False) and getattr(patient, "cac", None) is None:
        context.append("incidental CAC noted")
    if has_breast_arterial_calcification(patient):
        context.append("breast arterial calcification on mammogram")
    inflammatory = _inflammatory_context(patient)
    if inflammatory:
        context.extend(inflammatory)

    return priority[:3], context


def _patient_priority_drivers_html(rows):
    if not rows:
        return '<div class="roadmap-muted">No major measured factors were identified from the current worksheet.</div>'
    return "".join(
        '<div class="roadmap-driver-row">'
        f'<span class="roadmap-driver-marker roadmap-marker-{escape(tone)}"></span>'
        '<div>'
        f'<div class="roadmap-driver-title">{escape(label)}</div>'
        f'<div class="roadmap-driver-detail">{escape(detail)}</div>'
        '</div>'
        '</div>'
        for label, detail, tone in rows
    )


def _patient_context_chips_html(items):
    if not items:
        return ""
    chips = "".join(f'<span class="roadmap-context-chip">{escape(item)}</span>' for item in items)
    return f'<div class="roadmap-context-line"><span class="roadmap-context-label">Other context</span>{chips}</div>'


def _patient_goals_strip_html(rows):
    parts = []
    for area, current, goal in rows:
        if not goal or goal == "-":
            continue
        current_display = str(current or "-")
        goal_display = str(goal)
        if area == "BP":
            current_display = (
                current_display.replace(" mmHg; treated", "")
                .replace(" mmHg", "")
                .replace("; treated", "")
            )
            goal_display = goal_display.replace("<130/80 when appropriate", "usually below 130/80")
        elif goal_display.startswith("<"):
            goal_display = "below " + goal_display[1:]
        parts.append(
            '<div class="roadmap-goal-item">'
            f'<div class="roadmap-goal-target"><span>{escape(str(area))}</span> {escape(goal_display)}</div>'
            f'<div class="roadmap-goal-current">Current {escape(current_display)}</div>'
            '</div>'
        )
    if not parts:
        return '<div class="roadmap-muted">No specific numeric goals are assigned yet.</div>'
    return "".join(parts)


def _patient_next_steps_html(rows):
    return "".join(
        f'<li><div><span>{escape(label)}:</span> {escape(detail)}</div></li>'
        for label, detail in rows
    )


def _text_lines(patient, result):
    risk = getattr(result, "prevent_10y_ascvd", None)
    ascvd_30y = _ascvd_30y_value(result)
    level, level_detail = _continuum_label(patient, result)

    lines = [
        "Your Prevention Roadmap",
        "Your results show where you stand today and the most important steps to lower future heart, kidney, and metabolic risk.",
        "",
        "STEP 1",
        "Where you stand:",
        f"- 10-year ASCVD risk: {_fmt(risk, '%') or 'unavailable'}",
    ]
    if ascvd_30y is not None:
        lines.append(f"- 30-year ASCVD risk: {_fmt(ascvd_30y, '%')}")
        prevent_30y_text = _prevent_30y_explanation(ascvd_30y)
        if prevent_30y_text:
            lines.append(f"- {prevent_30y_text}")
    summary_sentence = build_patient_risk_summary_sentence(patient, result, ascvd_30y)
    if summary_sentence:
        lines.append(f"- {summary_sentence}")
    lines.extend(
        [
            f"- {_prevent_explanation(risk)}",
            f"- {_patient_plaque_status(patient, result)}",
            f"- Care focus: {level}" + (f" - {level_detail}" if level_detail else ""),
            "",
            "STEP 2",
            "Why your risk is higher:",
        ]
    )
    if risk is None:
        lines.insert(4, f"- {_prevent_unavailable_reason_text(result)}")
    elif _risk_category(result) == "low":
        lines.insert(6, "- Near-term estimated risk is low.")

    if _has_early_metabolic_risk(patient, result):
        lines.append("- Early metabolic signals are present.")
    if _has_elevated_30y_trajectory(patient, result):
        if _risk_category(result) == "borderline":
            lines.append("- Near-term risk is borderline, but 30-year risk and multiple early risk markers support prevention discussion.")
        else:
            lines.append("- Near-term estimated risk may be low, but 30-year risk is elevated enough to justify prevention discussion.")
    if _has_lpa_family_context(patient):
        lines.append("- Lp(a) and family history increase long-term risk context.")

    for label, finding, note, _tone in _patient_contributor_groups(patient, result):
        lines.append(f"- {label}: {finding}. {note}")

    _priority, context_items = _patient_driver_sections(patient, result)
    if context_items:
        lines.append("- Other context: " + "; ".join(context_items[:8]) + ".")

    target_rows = _target_rows(patient, result)
    if target_rows:
        lines.extend(["", "STEP 3", "Your goals:"])
        for area, current, goal in target_rows:
            lines.append(f"- {area}: {current} to {goal}")

    lines.extend(["", "STEP 4", "Your next steps:"])
    for index, (label, detail) in enumerate(_patient_next_steps(patient, result)[:6], start=1):
        lines.append(f"{index}. {label}: {detail}")

    lines.extend(["", "This roadmap is for discussion with your clinician. Medication decisions should be individualized."])
    return lines


def render_patient_roadmap_text(patient, result):
    return "\n".join(_text_lines(patient, result))


def _editorial_rows_html(rows, *, empty_text="No major measured contributors identified.", class_name="roadmap-rows"):
    if not rows:
        return f'<div class="roadmap-muted">{escape(empty_text)}</div>'

    parts = []
    for label, detail in rows:
        detail_html = (
            f'<div class="roadmap-row-detail">{escape(str(detail))}</div>'
            if detail
            else ""
        )
        parts.append(
            '<div class="roadmap-row">'
            f'<div class="roadmap-row-label">{escape(str(label))}</div>'
            f"{detail_html}"
            "</div>"
        )
    return f'<div class="{escape(class_name)}">' + "".join(parts) + "</div>"


def _goals_strip_html(rows):
    parts = []
    for area, current, goal in rows:
        if not goal or goal == "-":
            continue
        detail = current if current and current != "-" else ""
        parts.append(
            '<div class="roadmap-goal">'
            f'<div class="roadmap-goal-label">{escape(str(area))}</div>'
            f'<div class="roadmap-goal-value">{escape(str(goal))}</div>'
            + (f'<div class="roadmap-goal-detail">Current {escape(str(detail))}</div>' if detail else "")
            + "</div>"
        )
    if not parts:
        return '<div class="roadmap-muted">No specific numeric goals assigned yet.</div>'
    return '<div class="roadmap-goal-strip">' + "".join(parts) + "</div>"


def _roadmap_section_html(eyebrow: str, title: str, description: str, body_html: str) -> str:
    """Render a patient roadmap section panel with a consistent header."""
    return (
        '<section class="roadmap-section-panel">'
        '<div class="roadmap-section-header">'
        f'<div class="roadmap-section-eyebrow">{escape(eyebrow)}</div>'
        f'<div class="roadmap-section-title">{escape(title)}</div>'
        f'<div class="roadmap-section-description">{escape(description)}</div>'
        "</div>"
        f'<div class="roadmap-section-body">{body_html}</div>'
        "</section>"
    )


def _render_patient_roadmap_legacy(patient, result):
    risk = getattr(result, "prevent_10y_ascvd", None)
    ascvd_30y = _ascvd_30y_value(result)
    category = _risk_category(result)
    level, level_detail = _continuum_label(patient, result)

    risk_value = _fmt(risk, "%") or "--"
    secondary_bits = []
    if ascvd_30y is not None:
        secondary_bits.append(f"30-year ASCVD risk {_fmt(ascvd_30y, '%')}")
    secondary_text = " • ".join(secondary_bits)
    stand_detail = (
        f"{escape(category.title())} estimated 10-year ASCVD risk"
        + (f" • {escape(secondary_text)}" if secondary_text else "")
    )
    continuum_detail = f"{level}" + (f" - {level_detail}" if level_detail else "")

    contributor_items = []
    for label, detail in _contributor_groups(patient, result):
        contributor_items.append(
            "<li>"
            f"<strong>{escape(label)}</strong>"
            f"<span>{escape(detail)}</span>"
            "</li>"
        )
    contributors_html = (
        f'<ul class="roadmap-list">{"".join(contributor_items)}</ul>'
        if contributor_items
        else '<div class="roadmap-muted">No major measured contributors identified.</div>'
    )

    goal_parts = []
    for area, _current, goal in _target_rows(patient, result):
        if goal and goal != "-" and area in {"LDL-C", "ApoB", "non-HDL-C", "BP", "A1c"}:
            goal_parts.append(f"{area} {goal}")
    goal_html = (
        " <span class='roadmap-sep'>•</span> ".join(escape(part) for part in goal_parts)
        if goal_parts
        else "No specific numeric goals assigned yet."
    )

    next_items = [
        f"<li>{escape(detail)}</li>"
        for _label, detail in _recommendation_rows(patient, result)[:7]
        if detail
    ]
    next_html = f'<ul class="roadmap-list roadmap-next">{"".join(next_items)}</ul>'

    return f"""\
<style>
{component_theme_css()}
.roadmap-card {{
    border: 1px solid var(--rc-line);
    border-radius: 14px;
    background: #fffdf8;
    box-shadow: none;
    color: var(--rc-black);
    font-family: var(--rc-font-body);
    margin: 8px 0 12px;
    padding: 13px 15px 12px;
}}
.roadmap-head {{
    display: flex;
    justify-content: space-between;
    gap: 12px;
    align-items: baseline;
    border-bottom: 1px solid rgba(11, 31, 58, 0.10);
    padding-bottom: 8px;
    margin-bottom: 9px;
}}
.roadmap-title {{
    color: var(--rc-black);
    font-family: var(--rc-font-title);
    font-size: 1.08rem;
    font-weight: 700;
    letter-spacing: -0.012em;
    line-height: 1.1;
}}
.roadmap-chip {{
    border: 1px solid rgba(115, 0, 10, 0.22);
    border-radius: 999px;
    background: var(--rc-garnet-tint);
    color: var(--rc-garnet);
    display: inline-flex;
    font-size: 0.68rem;
    font-weight: 850;
    line-height: 1;
    padding: 0.28rem 0.52rem;
    white-space: nowrap;
}}
.roadmap-section-title {{
    border-top: 1px solid rgba(7, 26, 47, 0.10);
    color: #071a2f;
    font-family: var(--rc-font-title);
    font-size: 1.02rem;
    font-weight: 800;
    letter-spacing: -0.01em;
    line-height: 1.2;
    margin: 18px 0 10px;
    padding-top: 12px;
}}
.roadmap-section-title:first-of-type {{
    border-top: 0;
    margin-top: 10px;
    padding-top: 0;
}}
.roadmap-stand {{
    padding-top: 0;
}}
.roadmap-risk-line {{
    color: var(--rc-black);
    font-size: 0.92rem;
    font-weight: 900;
    line-height: 1.22;
}}
.roadmap-detail {{
    color: rgba(7, 26, 47, 0.70);
    font-size: 0.80rem;
    font-weight: 650;
    line-height: 1.30;
    margin-top: 2px;
}}
.roadmap-list {{
    list-style: none;
    margin: 0;
    padding: 0;
}}
.roadmap-list li {{
    color: rgba(7, 26, 47, 0.75);
    font-size: 0.80rem;
    font-weight: 650;
    line-height: 1.26;
    margin: 2px 0;
}}
.roadmap-list li::before {{
    color: var(--rc-garnet);
    content: "\\2022";
    font-weight: 950;
    margin-right: 6px;
}}
.roadmap-list strong {{
    color: var(--rc-black);
    font-weight: 900;
}}
.roadmap-list span {{
    margin-left: 4px;
}}
.roadmap-goals-line {{
    color: var(--rc-black);
    font-size: 0.86rem;
    font-weight: 850;
    line-height: 1.30;
}}
.roadmap-sep {{
    color: rgba(47, 95, 143, 0.68);
    padding: 0 2px;
}}
.roadmap-muted {{
    color: rgba(7, 26, 47, 0.58);
    font-size: 0.80rem;
    font-weight: 650;
}}
.roadmap-footer {{
    border-top: 1px solid rgba(11, 31, 58, 0.10);
    color: rgba(7, 26, 47, 0.58);
    font-size: 0.70rem;
    font-weight: 700;
    margin-top: 9px;
    padding-top: 7px;
}}
@media print {{
    .roadmap-card {{
        box-shadow: none;
        break-inside: avoid;
    }}
}}
@media (max-width: 760px) {{
    .roadmap-head {{
        align-items: flex-start;
        flex-direction: column;
    }}
}}
</style>
<div class="roadmap-card rc-panel">
    <div class="roadmap-head">
        <div class="roadmap-title">Your Cardiometabolic Prevention Roadmap</div>
        <div class="roadmap-chip">{escape(category)}</div>
    </div>
    <div class="roadmap-section-title">Where you stand</div>
    <div class="roadmap-stand">
        <div class="roadmap-risk-line">10-year ASCVD risk {escape(risk_value)}</div>
        {f'<div class="roadmap-detail">30-year ASCVD risk: {escape(_fmt(ascvd_30y, "%"))}</div>' if ascvd_30y is not None else ''}
        <div class="roadmap-detail">{stand_detail}</div>
        <div class="roadmap-detail">{escape(_prevent_explanation(risk))}</div>
        <div class="roadmap-detail">{escape(continuum_detail)} &bull; {escape(_plaque_status(patient, result))}</div>
    </div>
    <div class="roadmap-section-title">Why your risk is higher</div>
    {contributors_html}
    <div class="roadmap-section-title">Your goals</div>
    <div class="roadmap-goals-line">{goal_html}</div>
    <div class="roadmap-section-title">Your next steps</div>
    {next_html}
    <div class="roadmap-footer">This roadmap supports clinician review and shared decision-making.</div>
</div>
""".strip()


def render_patient_roadmap(patient, result):
    """Return one complete HTML string for inline Streamlit rendering.

    Structural HTML is assembled as raw fragments with no leading Markdown-code
    indentation. Only values and free text are escaped.
    """
    risk = getattr(result, "prevent_10y_ascvd", None)
    ascvd_30y = _ascvd_30y_value(result)
    category = _risk_category(result)
    level, level_detail = _continuum_label(patient, result)

    stand_detail = ""
    stand_detail = build_patient_risk_summary_sentence(patient, result, ascvd_30y)
    if risk is None:
        unavailable = _prevent_unavailable_reason_text(result)
        stand_detail = f"{stand_detail} {unavailable}".strip() if stand_detail else unavailable
    else:
        if ascvd_30y is None:
            unsupported = str(getattr(result, "prevent_unsupported_reason", "") or "").strip()
            if unsupported:
                stand_detail = f"{stand_detail} {unsupported}"

    if risk is not None and ascvd_30y is None:
        unsupported = str(getattr(result, "prevent_unsupported_reason", "") or "").strip()
        if not stand_detail:
            stand_detail = unsupported or "30-year estimate unavailable for the current data or age range."

    risk_cards_html = _patient_risk_cards_html(risk, ascvd_30y)
    plaque_html = escape(_patient_plaque_status(patient, result))
    clinician_context = f"{level}" + (f" - {level_detail}" if level_detail else "")
    priority_drivers, context_items = _patient_driver_sections(patient, result)
    priority_html = _patient_priority_drivers_html(priority_drivers)
    context_html = _patient_context_chips_html(context_items)
    goal_html = _patient_goals_strip_html(
        [
            row
            for row in _target_rows(patient, result)
            if row[2] and row[2] != "-" and row[0] in {"LDL-C", "ApoB", "BP", "A1c"}
        ]
    )
    next_html = _patient_next_steps_html(_patient_next_steps(patient, result)[:6])
    badge = _risk_badge_text(category, patient)

    css = dedent(
        """
        <style>
        /*COMPONENT_THEME*/
        .roadmap-card {
            --patient-font-base: 16px;
            --patient-font-small: 14.5px;
            --patient-font-title: 19px;
            --patient-font-number: 28px;
            --patient-line-height: 1.45;
            border: 1px solid rgba(17, 17, 17, 0.10);
            border-radius: 20px;
            background:
                linear-gradient(180deg, rgba(255, 253, 248, 0.98), rgba(255, 250, 241, 0.98));
            box-shadow: 0 18px 42px rgba(17, 17, 17, 0.07);
            color: var(--rc-black);
            font-size: var(--patient-font-base);
            font-family: var(--rc-font-body);
            line-height: var(--patient-line-height);
            margin: 8px 0 12px;
            padding: 12px 14px 12px;
        }
        .roadmap-head {
            display: flex;
            justify-content: space-between;
            gap: 12px;
            align-items: flex-start;
            border-bottom: 1px solid rgba(17, 17, 17, 0.08);
            padding-bottom: 8px;
            margin-bottom: 8px;
        }
        .roadmap-title {
            color: var(--rc-black);
            font-family: var(--rc-font-title);
            font-size: clamp(1.18rem, 1.65vw, 1.38rem);
            font-weight: 720;
            letter-spacing: -0.015em;
            line-height: 1.15;
            margin: 0 0 3px;
        }
        .roadmap-subtitle {
            color: rgba(17, 17, 17, 0.66);
            font-size: 15px;
            font-weight: 560;
            line-height: 1.42;
            max-width: 760px;
        }
        .roadmap-chip {
            border: 1px solid rgba(217, 119, 6, 0.24);
            border-radius: 999px;
            background: rgba(217, 119, 6, 0.12);
            color: #7C3F00;
            display: inline-flex;
            font-size: 14px;
            font-weight: 820;
            line-height: 1;
            padding: 0.32rem 0.54rem;
            white-space: nowrap;
        }
        .roadmap-section-panel {
            background: rgba(255, 255, 255, 0.62);
            border: 1px solid rgba(17, 17, 17, 0.10);
            border-radius: 14px;
            margin: 11px 0 0;
            padding: 12px 14px 13px;
        }
        .roadmap-section-panel:first-of-type {
            margin-top: 10px;
        }
        .roadmap-section-header {
            margin-bottom: 8px;
        }
        .roadmap-section-eyebrow {
            color: rgba(115, 0, 10, 0.62);
            font-size: 13.5px;
            font-weight: 820;
            letter-spacing: 0.07em;
            line-height: 1.1;
            margin-bottom: 2px;
            text-transform: uppercase;
        }
        .roadmap-section-title {
            color: var(--rc-black);
            font-family: var(--rc-font-title);
            font-size: var(--patient-font-title);
            font-weight: 820;
            letter-spacing: -0.01em;
            line-height: 1.22;
            margin: 0;
        }
        .roadmap-section-description {
            color: rgba(17, 17, 17, 0.56);
            font-size: 15px;
            font-weight: 560;
            line-height: 1.38;
            margin-top: 2px;
            max-width: 720px;
        }
        .roadmap-section-body {
            min-width: 0;
        }
        .roadmap-risk-grid {
            display: grid;
            gap: 6px;
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
        .roadmap-risk-card {
            break-inside: avoid;
            border: 1px solid rgba(17, 17, 17, 0.09);
            border-radius: 12px;
            background: #FFFFFF;
            box-shadow: 0 8px 20px rgba(17, 17, 17, 0.045);
            padding: 7px 9px;
            position: relative;
            overflow: hidden;
        }
        .roadmap-risk-card::before {
            border-radius: 999px;
            content: "";
            height: 7px;
            left: 9px;
            position: absolute;
            top: 8px;
            width: 7px;
        }
        .roadmap-risk-label {
            color: rgba(17, 17, 17, 0.72);
            font-size: 15px;
            font-weight: 830;
            line-height: 1.22;
            padding-left: 13px;
        }
        .roadmap-risk-subtitle {
            color: rgba(17, 17, 17, 0.52);
            font-size: 14px;
            font-weight: 620;
            line-height: 1.32;
            margin-top: 2px;
            padding-left: 13px;
        }
        .roadmap-risk-value {
            color: var(--rc-black);
            font-size: var(--patient-font-number);
            font-weight: 900;
            letter-spacing: -0.035em;
            line-height: 1.05;
            margin-top: 4px;
        }
        .roadmap-risk-text,
        .roadmap-clinician-context {
            color: rgba(17, 17, 17, 0.62);
            font-size: var(--patient-font-small);
            font-weight: 540;
            line-height: 1.38;
            margin-top: 3px;
        }
        .roadmap-plaque-line {
            border: 1px solid rgba(47, 95, 143, 0.16);
            border-radius: 11px;
            background: rgba(47, 95, 143, 0.075);
            color: rgba(17, 17, 17, 0.76);
            font-size: 15px;
            font-weight: 680;
            line-height: 1.38;
            margin-top: 6px;
            padding: 5px 8px;
        }
        .roadmap-driver-list {
            border-top: 1px solid rgba(17, 17, 17, 0.08);
        }
        .roadmap-driver-row {
            align-items: flex-start;
            border-bottom: 1px solid rgba(17, 17, 17, 0.075);
            display: grid;
            gap: 7px;
            grid-template-columns: 10px 1fr;
            padding: 6px 0;
        }
        .roadmap-driver-row:last-child {
            border-bottom: 0;
        }
        .roadmap-driver-marker {
            border-radius: 999px;
            display: inline-block;
            height: 8px;
            margin-top: 4px;
            width: 8px;
        }
        .roadmap-marker-red { background: var(--rc-garnet); }
        .roadmap-marker-amber { background: #D97706; }
        .roadmap-marker-blue { background: #2F5F8F; }
        .roadmap-marker-green { background: #2E7D50; }
        .roadmap-marker-gray { background: #7A7A7A; }
        .roadmap-driver-title {
            color: var(--rc-black);
            font-size: 15.5px;
            font-weight: 850;
            line-height: 1.28;
        }
        .roadmap-driver-detail {
            color: rgba(17, 17, 17, 0.62);
            font-size: var(--patient-font-small);
            font-weight: 540;
            line-height: 1.36;
            margin-top: 1px;
        }
        .roadmap-context-line {
            align-items: center;
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
            margin-top: 4px;
        }
        .roadmap-context-label {
            color: rgba(17, 17, 17, 0.42);
            font-size: 14px;
            font-weight: 800;
        }
        .roadmap-context-chip {
            border: 1px solid rgba(17, 17, 17, 0.10);
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.72);
            color: rgba(17, 17, 17, 0.66);
            font-size: 14px;
            font-weight: 650;
            line-height: 1;
            padding: 0.22rem 0.38rem;
        }
        .roadmap-goal-strip {
            border: 1px solid rgba(17, 17, 17, 0.09);
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.68);
            display: flex;
            flex-wrap: wrap;
            gap: 0;
            overflow: hidden;
        }
        .roadmap-goal-item {
            border-right: 1px solid rgba(17, 17, 17, 0.075);
            flex: 1 1 126px;
            min-width: 118px;
            padding: 6px 8px;
        }
        .roadmap-goal-item:last-child {
            border-right: 0;
        }
        .roadmap-goal-target {
            color: var(--rc-black);
            font-size: 15px;
            font-weight: 850;
            line-height: 1.3;
        }
        .roadmap-goal-target span {
            color: #7C3F00;
            font-weight: 900;
        }
        .roadmap-goal-current {
            color: rgba(17, 17, 17, 0.56);
            font-size: 14px;
            font-weight: 600;
            line-height: 1.3;
            margin-top: 2px;
        }
        .roadmap-step-list {
            counter-reset: roadmap-step;
            list-style: none;
            margin: 0;
            padding: 0;
        }
        .roadmap-step-list li {
            align-items: flex-start;
            border-bottom: 1px solid rgba(17, 17, 17, 0.07);
            color: rgba(17, 17, 17, 0.68);
            counter-increment: roadmap-step;
            display: grid;
            font-size: 15px;
            font-weight: 540;
            gap: 7px;
            grid-template-columns: 19px 1fr;
            line-height: 1.38;
            padding: 4px 0;
        }
        .roadmap-step-list li::before {
            align-items: center;
            background: rgba(47, 95, 143, 0.11);
            border-radius: 999px;
            color: #2F5F8F;
            content: counter(roadmap-step);
            display: inline-flex;
            font-size: 13.5px;
            font-weight: 850;
            height: 17px;
            justify-content: center;
            width: 17px;
        }
        .roadmap-step-list li:last-child {
            border-bottom: 0;
        }
        .roadmap-step-list span {
            color: var(--rc-black);
            font-weight: 850;
        }
        .roadmap-tone-blue {
            background: linear-gradient(180deg, #F4F9FF, #FFFFFF);
            border-color: rgba(47, 95, 143, 0.16);
        }
        .roadmap-tone-blue::before { background: #2F5F8F; }
        .roadmap-tone-green {
            background: linear-gradient(180deg, #F3FBF6, #FFFFFF);
            border-color: rgba(22, 101, 52, 0.16);
        }
        .roadmap-tone-green::before { background: #2E7D50; }
        .roadmap-tone-amber {
            background: linear-gradient(180deg, #FFF8EA, #FFFFFF);
            border-color: rgba(217, 119, 6, 0.18);
        }
        .roadmap-tone-amber::before { background: #D97706; }
        .roadmap-tone-orange {
            background: linear-gradient(180deg, #FFF3E9, #FFFFFF);
            border-color: rgba(234, 88, 12, 0.18);
        }
        .roadmap-tone-orange::before { background: #EA580C; }
        .roadmap-tone-red {
            background: linear-gradient(180deg, #FFF4F4, #FFFFFF);
            border-color: rgba(115, 0, 10, 0.18);
        }
        .roadmap-tone-red::before { background: var(--rc-garnet); }
        .roadmap-tone-gray {
            background: linear-gradient(180deg, #F7F7F5, #FFFFFF);
            border-color: rgba(17, 17, 17, 0.10);
        }
        .roadmap-tone-gray::before { background: #7A7A7A; }
        .roadmap-muted {
            color: rgba(17, 17, 17, 0.58);
            font-size: var(--patient-font-small);
            font-weight: 520;
        }
        .roadmap-footer {
            border-top: 1px solid rgba(17, 17, 17, 0.10);
            color: rgba(17, 17, 17, 0.58);
            font-size: 14px;
            font-weight: 620;
            line-height: 1.38;
            margin-top: 13px;
            padding-top: 9px;
        }
        @media print {
            .roadmap-card {
                box-shadow: none;
                margin: 0;
                page-break-inside: avoid;
                padding: 16px 18px 14px;
            }
            .roadmap-section-panel {
                border-radius: 16px;
                margin-top: 16px;
                padding: 18px 20px 19px;
            }
            .roadmap-section-header {
                margin-bottom: 14px;
            }
            .roadmap-section-eyebrow {
                font-size: 0.68rem;
                margin-bottom: 4px;
            }
            .roadmap-section-title {
                font-size: 1.08rem;
            }
            .roadmap-section-description {
                font-size: 0.80rem;
            }
            .roadmap-risk-card,
            .roadmap-driver-row,
            .roadmap-goal-strip,
            .roadmap-step-list li {
                box-shadow: none;
                page-break-inside: avoid;
                break-inside: avoid;
            }
        }
        @media (max-width: 760px) {
            .roadmap-head {
                align-items: flex-start;
                flex-direction: column;
            }
            .roadmap-section-panel {
                padding: 11px 12px;
            }
            .roadmap-risk-grid,
            .roadmap-goal-strip {
                grid-template-columns: 1fr;
            }
            .roadmap-goal-strip {
                display: block;
            }
            .roadmap-goal-item {
                border-bottom: 1px solid rgba(17, 17, 17, 0.075);
                border-right: 0;
            }
            .roadmap-goal-item:last-child {
                border-bottom: 0;
            }
        }
        </style>
        """
    ).replace("/*COMPONENT_THEME*/", component_theme_css()).strip()

    where_body = "".join(
        part
        for part in (
            f'<div class="roadmap-risk-grid">{risk_cards_html}</div>',
            f'<div class="roadmap-detail">{escape(stand_detail)}</div>' if stand_detail else "",
            f'<div class="roadmap-plaque-line">{plaque_html}</div>',
            f'<div class="roadmap-clinician-context">Care focus: {escape(clinician_context)}</div>' if clinician_context else "",
        )
        if part
    )
    drivers_body = "".join(
        part
        for part in (
            f'<div class="roadmap-driver-list">{priority_html}</div>',
            context_html,
        )
        if part
    )
    goals_body = f'<div class="roadmap-goal-strip">{goal_html}</div>'
    next_body = f'<ol class="roadmap-step-list">{next_html}</ol>'

    body_parts = [
        '<div class="roadmap-card rc-panel">',
        '<div class="roadmap-head">',
        '<div><div class="roadmap-title rc-card-title">Your Prevention Roadmap</div>',
        '<div class="roadmap-subtitle">Your results show where you stand today and the most important steps to lower future heart, kidney, and metabolic risk.</div></div>',
        f'<div class="roadmap-chip">{escape(badge)}</div>',
        "</div>",
        _roadmap_section_html(
            "STEP 1",
            "Where you stand",
            "Your estimated artery disease risk and current care level.",
            where_body,
        ),
        _roadmap_section_html(
            "STEP 2",
            "Why your risk is higher",
            "The main reasons your risk is higher.",
            drivers_body,
        ),
        _roadmap_section_html(
            "STEP 3",
            "Your goals",
            "Targets to review with your clinician.",
            goals_body,
        ),
        _roadmap_section_html(
            "STEP 4",
            "Your next steps",
            "The most important steps to lower future risk.",
            next_body,
        ),
        '<div class="roadmap-footer">This roadmap is for discussion with your clinician. Medication decisions should be individualized.</div>',
        "</div>",
    ]

    return css + "\n" + "\n".join(part for part in body_parts if part)
