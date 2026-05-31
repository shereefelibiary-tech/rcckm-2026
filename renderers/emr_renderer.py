from core.diagnosis_workflow import (
    apply_diagnosis_review_overrides,
    prepare_diagnosis_display_entries,
    split_diagnoses,
)
from modules.actions.scaffold import build_domain_actions
from modules.levels.definitions import classify_continuum_position
from modules.risk_enhancers.breast_arterial_calcification import (
    breast_arterial_calcification_context,
)
from modules.risk_enhancers.incidental_cac import incidental_cac_context
from modules.risk_enhancers.reproductive import reproductive_history_summary
from renderers.emr_constants import (
    EMR_ASSESSMENT_TITLE,
    EMR_HEADER,
    EMR_RECOMMENDATION_DOMAIN_LABELS,
    EMR_RECOMMENDATION_DOMAIN_ORDER,
    EMR_RECOMMENDATIONS_TITLE,
    EMR_SUMMARY_LABELS,
)


def _display_value(value):
    if value is None:
        return None

    return getattr(value, "value", value)


def _ckm_summary(result):
    ckm_stage = getattr(result, "ckm_stage", None)
    if not ckm_stage:
        return None

    stage = ckm_stage.get("stage")
    headline = ckm_stage.get("headline")
    drivers = ckm_stage.get("drivers", [])

    if headline:
        return f"Stage {stage} - {headline}"
    if drivers:
        return f"Stage {stage} - {'; '.join(drivers)}"
    return f"Stage {stage}"


def _plaque_summary(patient, result):
    cac = getattr(patient, "cac", None)
    if getattr(patient, "clinical_ascvd", False):
        if cac is not None and cac == 0:
            return "established ASCVD; CAC 0 does not de-risk secondary prevention"
        if cac is not None:
            return f"established ASCVD; CAC {cac:g} is context only"
        return "established clinically"
    if bool(getattr(result, "severe_hypercholesterolemia", False)) and cac == 0:
        return "CAC 0 measured; do not use CAC 0 to defer lipid-lowering therapy in LDL-C >=190 / possible FH pathway"
    if cac is not None:
        return f"CAC {cac:g}"
    incidental_context = incidental_cac_context(patient)
    if incidental_context:
        return incidental_context
    if getattr(patient, "cac_not_done", False):
        return "unmeasured / CAC not performed"

    plaque_category = _display_value(getattr(result, "plaque_category", None))
    if plaque_category == "UNKNOWN":
        return "unmeasured"
    if plaque_category:
        return plaque_category

    return "unmeasured"


def _uacr_completion_relevant(patient, result):
    if getattr(patient, "uacr", None) is not None:
        return False
    prevent_value = getattr(result, "prevent_10y_ascvd", None)
    egfr = getattr(patient, "egfr", None)
    a1c = getattr(patient, "a1c", None)
    bmi = getattr(patient, "bmi", None)
    triglycerides = getattr(patient, "triglycerides", None)
    return bool(
        getattr(patient, "diabetes", False)
        or (a1c is not None and a1c >= 5.7)
        or getattr(patient, "bp_treated", False)
        or getattr(patient, "hypertension", False)
        or (egfr is not None and egfr < 90)
        or (bmi is not None and bmi >= 30)
        or (triglycerides is not None and triglycerides >= 150)
        or getattr(patient, "masld", False)
        or getattr(patient, "osa", False)
        or (prevent_value is not None and prevent_value >= 3)
    )


def _kidney_summary(patient, result):
    kdigo_stage = getattr(result, "kdigo_stage", None)
    if not kdigo_stage:
        return None
    if getattr(patient, "uacr", None) is None:
        return f"{kdigo_stage}; albuminuria not measured"
    return str(kdigo_stage)


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


def _has_elevated_30y_trajectory(patient, result):
    age = getattr(patient, "age", None)
    prevent_30y = getattr(result, "prevent_30y_ascvd", None)
    return bool(age is not None and 30 <= age <= 59 and prevent_30y is not None and prevent_30y >= 10)


def _low_with_significant_risk_enhancers(patient, result):
    if bool(getattr(patient, "clinical_ascvd", False)):
        return False
    if str(_display_value(getattr(result, "prevent_risk_category", None)) or "").upper() != "LOW":
        return False
    ldl_c = getattr(patient, "ldl_c", None)
    apob = getattr(patient, "apob", None)
    return bool(
        _has_elevated_lpa(patient)
        or _has_premature_family_history(patient)
        or (ldl_c is not None and 160 <= ldl_c <= 189)
        or (apob is not None and apob >= 120)
    )


def _albuminuria_actionable_ckm_path(patient, result):
    uacr = getattr(patient, "uacr", None)
    if uacr is None or uacr < 30:
        return False
    position = classify_continuum_position(patient, result)
    return position.get("level") == 3 and position.get("sublevel") == "3B"


def _early_lifetime_burden_path(patient, result):
    if bool(getattr(patient, "clinical_ascvd", False)):
        return False
    if str(_display_value(getattr(result, "prevent_risk_category", None)) or "").upper() != "LOW":
        return False

    age = getattr(patient, "age", None)
    ldl_c = getattr(patient, "ldl_c", None)
    prevent_30y = getattr(result, "prevent_30y_ascvd", None)
    return bool(
        age is not None
        and 30 <= age <= 59
        and (
            (ldl_c is not None and 160 <= ldl_c <= 189)
            or (prevent_30y is not None and prevent_30y >= 10)
        )
    )


def _young_family_metabolic_trajectory(patient, result):
    if bool(getattr(patient, "clinical_ascvd", False)):
        return False
    age = getattr(patient, "age", None)
    if age is None or not (30 <= age < 40):
        return False
    if str(_display_value(getattr(result, "prevent_risk_category", None)) or "").upper() != "LOW":
        return False
    if not _has_premature_family_history(patient):
        return False

    position = classify_continuum_position(patient, result)
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


def _near_level3_threshold_line(patient, result):
    if bool(getattr(patient, "clinical_ascvd", False)):
        return None
    age = getattr(patient, "age", None)
    prevent_10y = getattr(result, "prevent_10y_ascvd", None)
    prevent_30y = getattr(result, "prevent_30y_ascvd", None)
    ldl_c = getattr(patient, "ldl_c", None)
    apob = getattr(patient, "apob", None)
    if age is None or prevent_10y is None or prevent_30y is None:
        return None
    if not (30 <= age <= 59 and prevent_10y < 3 and 8 <= prevent_30y < 10):
        return None
    if (ldl_c is not None and ldl_c >= 160) or (apob is not None and apob >= 120):
        return None

    near_values = [f"30-year risk {prevent_30y:g}%"]
    if ldl_c is not None and 150 <= ldl_c < 160:
        near_values.append(f"LDL-C {ldl_c:g} mg/dL")
    if apob is not None and 110 <= apob < 120:
        near_values.append(f"ApoB {apob:g} mg/dL")
    if len(near_values) == 1:
        return None
    return f"Near Level 3 threshold: {', '.join(near_values)}."


def _risk_level_summary(patient, result):
    if _young_family_metabolic_trajectory(patient, result):
        return "Level 3B - elevated lifetime cardiometabolic risk despite low short-term event risk"

    classification = getattr(result, "level_classification", None) or {}
    classification_level = str(classification.get("level") or "")
    classification_label = str(classification.get("label") or "").strip()
    if classification_level in {"1", "2A", "2B", "3A", "3B", "4", "5"} and classification_label:
        return classification_label.replace("—", "-").replace("â€”", "-")

    if (
        classification_level == "2B"
        and classification_label
        and _has_elevated_lpa(patient)
        and reproductive_history_summary(patient)
    ):
        return classification_label.replace("—", "-").replace("â€”", "-")

    risk_level = _display_value(getattr(result, "risk_level", None))
    if not risk_level:
        return None
    position = classify_continuum_position(patient, result)
    if _albuminuria_actionable_ckm_path(patient, result):
        return "3B / actionable early CKM/kidney risk"
    if _has_elevated_30y_trajectory(patient, result) and position.get("level") == 3:
        if position.get("sublevel") == "3B":
            return "Level 3B - actionable early CKM / atherogenic risk"
        return "Level 3A - elevated long-term risk trajectory"
    if (
        str(risk_level).upper() == "LOW"
        and position.get("level") == 3
        and _early_lifetime_burden_path(patient, result)
    ):
        return "LOW near-term risk / elevated lifetime burden"
    if (
        str(risk_level).upper() == "LOW"
        and position.get("level") in {2, 3}
        and _low_with_significant_risk_enhancers(patient, result)
    ):
        return "LOW near-term risk / elevated lifetime-risk context"
    ckm_stage = getattr(result, "ckm_stage", None) or {}
    stage = ckm_stage.get("stage")
    if str(risk_level).upper() == "LOW" and stage is not None and stage >= 1:
        return "LOW with early metabolic risk signals"
    return str(risk_level)


def _codes_for(entry, confirmed):
    key = "icd10_confirmed" if confirmed else "icd10_suggested"
    codes = entry.get(key) or []
    return [str(code).strip() for code in codes if str(code).strip()]


def _hcc_note_for(entry, confirmed=True):
    """Keep HCC metadata out of the plain-text EMR note."""
    return None


def _candidate_line(entry, confirmed=True):
    label = str(entry.get("label_display") or entry.get("label") or "").strip()
    if not label:
        return ""

    codes = _codes_for(entry, confirmed=confirmed)
    line = f"- {label}"
    if codes:
        line += f" (ICD: {', '.join(codes)})"
    hcc_note = _hcc_note_for(entry, confirmed=confirmed)
    if hcc_note:
        line += f" [{hcc_note}]"
    return line


def _diagnosis_label(entry):
    return str(entry.get("label_display") or entry.get("label") or "").strip()


def _diagnosis_key(entry):
    return _diagnosis_label(entry).lower()


def _ckd_stage_phrase(label):
    lowered = str(label or "").strip().lower()
    marker = "chronic kidney disease, stage "
    if marker not in lowered:
        return ""
    return lowered.split(marker, 1)[1].strip()


def _emr_assessment_lines(entries):
    rows = [entry for entry in (entries or []) if isinstance(entry, dict)]
    diabetic_ckd = next(
        (
            entry
            for entry in rows
            if "type 2 diabetes mellitus with ckd" in _diagnosis_key(entry)
        ),
        None,
    )
    staged_ckd = next(
        (
            entry
            for entry in rows
            if _diagnosis_key(entry).startswith("chronic kidney disease, stage")
        ),
        None,
    )

    lines = []
    grouped_ids = {id(staged_ckd)} if staged_ckd else set()
    if diabetic_ckd:
        grouped_ids.add(id(diabetic_ckd))

    for entry in rows:
        if id(entry) in grouped_ids and entry is not diabetic_ckd:
            continue
        label_raw = _diagnosis_label(entry)
        if "family history" in label_raw.lower():
            continue

        if entry is not diabetic_ckd:
            _append_unique(lines, _candidate_line(entry, confirmed=True))
            continue

        label = _diagnosis_label(diabetic_ckd)
        parts = []
        codes = _codes_for(diabetic_ckd, confirmed=True)
        if codes:
            parts.append(f"ICD: {', '.join(codes)}")
        hcc_note = _hcc_note_for(diabetic_ckd, confirmed=True)
        if hcc_note:
            parts.append(hcc_note)
        if staged_ckd:
            stage = _ckd_stage_phrase(_diagnosis_label(staged_ckd))
            stage_codes = _codes_for(staged_ckd, confirmed=True)
            if stage and stage_codes:
                parts.append(f"CKD stage {stage} ICD: {', '.join(stage_codes)}")
            stage_hcc_note = _hcc_note_for(staged_ckd, confirmed=True)
            if stage_hcc_note and stage_hcc_note not in parts:
                parts.append(f"CKD stage {stage} {stage_hcc_note}")
        line = f"- {label}"
        if parts:
            line += f" ({'; '.join(parts)})"
        _append_unique(lines, line)
    return lines


def _append_unique(lines, line):
    if line and line not in lines:
        lines.append(line)


def _prevent_impression_sentence(patient, result):
    if getattr(patient, "clinical_ascvd", False):
        return "Known cardiovascular disease is present, so treatment decisions are based on secondary-prevention goals rather than risk estimates alone."

    fragments = []
    if getattr(result, "prevent_10y_ascvd", None) is not None:
        fragments.append(f"10-year ASCVD risk: {result.prevent_10y_ascvd:g}%")
    if getattr(result, "prevent_30y_ascvd", None) is not None:
        fragments.append(f"30-year ASCVD risk: {result.prevent_30y_ascvd:g}%")
    if not fragments:
        return "PREVENT unavailable; interpretation is based on worksheet data."
    return ".\n".join(fragments) + "."


def _disease_context_sentence(patient, result):
    ckm_part = None
    context_parts = []
    ckm_stage = getattr(result, "ckm_stage", None) or {}
    if ckm_stage.get("stage") is not None:
        ckm_part = f"CKM stage {ckm_stage.get('stage')}"

    kidney_summary = _kidney_summary(patient, result)
    if kidney_summary:
        if getattr(patient, "diabetes", False) and (
            "A2" in str(kidney_summary)
            or "A3" in str(kidney_summary)
        ):
            context_parts.append("diabetic kidney involvement")
        else:
            context_parts.append(f"kidney {kidney_summary}")

    plaque_summary = _plaque_summary(patient, result)
    if plaque_summary:
        plaque_category = str(_display_value(getattr(result, "plaque_category", None)) or "").upper()
        measured_plaque_category = bool(plaque_category and plaque_category != "UNKNOWN")
        important_plaque = (
            getattr(patient, "clinical_ascvd", False)
            or getattr(patient, "cac", None) is not None
            or incidental_cac_context(patient)
            or "LDL-C >=190" in plaque_summary
            or measured_plaque_category
        )
        cac_action = "cac_testing" in (getattr(result, "action_domains", None) or {})
        if important_plaque or cac_action:
            if plaque_summary.startswith("CAC ") or plaque_summary.startswith(("Mild incidental", "Moderate incidental", "Severe incidental", "Incidental coronary")):
                context_parts.append(plaque_summary)
            else:
                context_parts.append(f"plaque {plaque_summary}")

    if not ckm_part and not context_parts:
        return None
    if ckm_part and context_parts:
        if len(context_parts) == 1:
            return f"{ckm_part} with {context_parts[0]}."
        return f"{ckm_part} with {', '.join(context_parts[:-1])} and {context_parts[-1]}."
    return (ckm_part or "; ".join(context_parts)) + "."


def _history_context_sentence(patient):
    parts = []
    if getattr(patient, "rheumatoid_arthritis", False):
        parts.append("rheumatoid arthritis")
    reproductive_summary = reproductive_history_summary(patient)
    if reproductive_summary:
        parts.append(f"reproductive history: {reproductive_summary}")
    if getattr(patient, "hiv", False):
        parts.append("HIV on stable ART" if getattr(patient, "stable_art", False) else "HIV")
    ancestry = []
    if getattr(patient, "south_asian_ancestry", False):
        ancestry.append("South Asian ancestry")
    if getattr(patient, "filipino_ancestry", False):
        ancestry.append("Filipino ancestry")
    if getattr(patient, "higher_risk_ancestry_context", None):
        ancestry.append(str(patient.higher_risk_ancestry_context))
    if ancestry:
        parts.append("risk-enhancing ancestry/context: " + "; ".join(ancestry))
    if getattr(patient, "active_cancer", False):
        parts.append("active cancer context")
    elif getattr(patient, "cancer_survivor", False):
        suffix = " with life expectancy >2 years" if getattr(patient, "cancer_life_expectancy_gt_2y", False) else ""
        parts.append(f"cancer survivor context{suffix}")
    if getattr(patient, "suspected_fh_hefh", False):
        parts.append("suspected FH / HeFH pathway")
    bac_context = breast_arterial_calcification_context(patient)
    if bac_context:
        parts.append(bac_context)
    if bool(getattr(patient, "premature_fhx_ascvd", False)) or bool(
        getattr(patient, "family_history_premature_ascvd", False)
    ):
        family_summary = str(getattr(patient, "family_history_summary", "") or "").strip()
        if family_summary and family_summary.lower() != "premature family history of ascvd":
            if getattr(patient, "rheumatoid_arthritis", False):
                parts.append(f"premature family history of ASCVD ({family_summary})")
            else:
                parts.append(f"premature family history ({family_summary})")
        else:
            parts.append("premature family history of ASCVD")
    if not parts:
        return None
    return "Risk context: " + "; ".join(parts) + "."


def _young_family_history_context_sentence(patient):
    family_summary = str(getattr(patient, "family_history_summary", "") or "").strip()
    if not family_summary:
        relationship = str(getattr(patient, "family_history_relationship", "") or "").strip()
        event_type = str(getattr(patient, "family_history_event_type", "") or "").strip()
        event_age = getattr(patient, "family_history_age_at_event", None)
        bits = [bit for bit in (relationship, event_type) if bit]
        if event_age is not None:
            bits.append(f"age {event_age:g}")
        family_summary = " ".join(bits)
    if family_summary and family_summary.lower() != "premature family history of ascvd":
        return f"Risk context: premature family history of ASCVD ({family_summary})."
    return "Risk context: premature family history of ASCVD."


def _impression_paragraphs(patient, result):
    risk_level = _risk_level_summary(patient, result)
    first = f"{risk_level}." if risk_level else None
    prevent = _prevent_impression_sentence(patient, result)

    second_parts = [_disease_context_sentence(patient, result)]
    second = " ".join(part for part in second_parts if part)

    third_parts = []
    if _uacr_completion_relevant(patient, result):
        third_parts.append("UACR not available; obtain UACR.")
    history = (
        _young_family_history_context_sentence(patient)
        if _young_family_metabolic_trajectory(patient, result)
        else _history_context_sentence(patient)
    )
    if history:
        third_parts.append(history)
    if bool(getattr(result, "severe_hypercholesterolemia", False)):
        third_parts.append("LDL-C >=190 / possible FH pathway: PREVENT should not be used to de-risk treatment.")
    elif bool(getattr(result, "possible_fh_pathway", False)):
        third_parts.append("LDL-C >=190 / possible FH pathway: PREVENT should not be used to de-risk treatment.")
    near_level3_line = _near_level3_threshold_line(patient, result)
    if near_level3_line:
        third_parts.append(near_level3_line)
    third = " ".join(third_parts)

    return [paragraph for paragraph in [first, prevent, second, third] if paragraph]


def _skip_emr_recommendation(recommendation):
    lowered = str(recommendation or "").strip().lower()
    if not lowered:
        return True
    if "recheck lipid profile" in lowered or "recheck fasting lipid profile" in lowered or "recheck lipids" in lowered:
        return True
    if "cac" in lowered and ("already measured" in lowered or "no repeat" in lowered):
        return True
    if lowered == "plaque burden unmeasured.":
        return True
    return False


def _short_recommendation_line(recommendation):
    replacements = {
        "Moderate-intensity lipid-lowering therapy is reasonable to reduce cumulative atherogenic exposure.": "Discuss moderate-intensity lipid-lowering.",
        "Moderate-intensity statin therapy is reasonable to reduce cumulative atherogenic exposure.": "Discuss moderate-intensity statin.",
        "Lipid-lowering therapy is indicated; treat toward high-risk targets.": "Lipid-lowering therapy indicated; treat toward high-risk targets.",
        "Intensify secondary-prevention lipid-lowering therapy; treat toward very-high-risk ASCVD targets.": "Intensify secondary-prevention lipid-lowering therapy; treat toward very-high-risk ASCVD targets: LDL-C <55 mg/dL, non-HDL-C <85 mg/dL, and ApoB <65 mg/dL if available. LDL-C <70 mg/dL remains the minimum secondary-prevention threshold.",
        "Secondary-prevention lipid-lowering therapy indicated; treat toward very-high-risk ASCVD targets.": "Treat toward very-high-risk ASCVD targets: LDL-C <55 mg/dL, non-HDL-C <85 mg/dL, and ApoB <65 mg/dL if available. LDL-C <70 mg/dL remains the minimum secondary-prevention threshold.",
        "High-intensity lipid-lowering therapy indicated; treat toward high-risk targets.": "High-intensity lipid-lowering therapy indicated.",
        "High-intensity or maximally tolerated statin therapy indicated.": "High-intensity or maximally tolerated statin indicated.",
        "Optimize kidney-protective therapy and confirm albuminuria persistence.": "Confirm albuminuria persistence and optimize kidney-protective therapy.",
        "Treat blood pressure toward individualized goal.": "Treat BP toward goal <130/80.",
        "Optimize BP to <130/80.": "Treat BP toward goal <130/80.",
        "CAC reasonable for risk clarification if treatment decision remains uncertain.": "CAC may clarify risk if treatment decision remains uncertain.",
        "Aspirin may be considered only if bleeding risk is low after shared decision-making.": "Aspirin only if bleeding risk is low.",
        "Obtain hsCRP if inflammatory risk clarification would change management.": "Obtain hsCRP only if inflammatory risk clarification would change management.",
    }
    return replacements.get(recommendation, recommendation)


def _young_family_metabolic_recommendations(patient, result):
    if not _young_family_metabolic_trajectory(patient, result):
        return None
    return [
        "Focus on early risk reduction given metabolic risk signals and strong family history.",
        "Discuss moderate-intensity statin if ApoB/LDL-C burden, family history, or clinician judgment supports treatment.",
        "CAC not routinely recommended at this age; consider only if results would change management.",
        "Aspirin not indicated for routine primary prevention.",
        "Additional information: ApoB, Lp(a), and hsCRP if results would change management.",
    ]


def _albuminuria_assessment_display(line, patient, result):
    if "- Albuminuria" not in str(line or ""):
        return line
    kdigo_stage = getattr(result, "kdigo_stage", None)
    if not kdigo_stage or "A2" not in str(kdigo_stage) and "A3" not in str(kdigo_stage):
        return line
    suffix = ""
    if "(ICD:" in line:
        suffix = " " + line.split(" ", 2)[-1] if line.startswith("- Albuminuria ") else ""
    return f"- CKD stage {kdigo_stage} / albuminuria{suffix}"


def _emr_float(value):
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _emr_fmt(value):
    num = _emr_float(value)
    if num is None:
        return None
    return f"{num:g}"


def _emr_level_line(patient, result):
    level = _risk_level_summary(patient, result)
    if not level:
        return None
    level = str(level).strip()
    if level.lower().startswith("level "):
        level = level[6:].strip()
    if " / " in level and " - " not in level:
        first, rest = level.split(" / ", 1)
        if first in {"1", "2A", "2B", "3A", "3B", "4", "5"}:
            level = f"{first} - {rest}"
    level = level.replace("subclinical atherosclerosis present", "subclinical atherosclerosis")
    return f"{EMR_SUMMARY_LABELS['level']}: {level}."


def _emr_risk_line(result):
    ten = _emr_fmt(getattr(result, "prevent_10y_ascvd", None))
    thirty = _emr_fmt(getattr(result, "prevent_30y_ascvd", None))
    category = _display_value(getattr(result, "prevent_risk_category", None))
    category_text = str(category).replace("_", " ").title() if category else None
    if category_text is None and ten is not None:
        ten_value = _emr_float(ten)
        if ten_value is not None:
            if ten_value >= 20:
                category_text = "High"
            elif ten_value >= 7.5:
                category_text = "Intermediate"
            elif ten_value >= 5:
                category_text = "Borderline"
            else:
                category_text = "Low"
    category_text = category_text or "Unavailable"
    if ten and thirty:
        return f"{EMR_SUMMARY_LABELS['prevent']}: ASCVD 10y {ten}% ({category_text}); 30y {thirty}%."
    if ten:
        return f"{EMR_SUMMARY_LABELS['prevent']}: ASCVD 10y {ten}% ({category_text})."
    return f"{EMR_SUMMARY_LABELS['prevent']}: unavailable."


def _emr_ckm_line(patient, result):
    parts = []
    ckm_stage = getattr(result, "ckm_stage", None) or {}
    stage = ckm_stage.get("stage")
    kdigo = getattr(result, "kdigo_stage", None)
    kdigo_text = str(kdigo or "")
    kdigo_ckd_signal = bool(
        kdigo_text.startswith(("G3a", "G3b", "G4", "G5"))
        or "A2" in kdigo_text
        or "A3" in kdigo_text
    )
    if stage is not None:
        drivers = [str(driver).lower() for driver in ckm_stage.get("drivers", []) or []]
        cac_driven = any(driver.startswith("cac ") for driver in drivers)
        ckd_driven = any(driver.startswith("ckd ") for driver in drivers)
        if stage == 3 and cac_driven and not ckd_driven and not kdigo_ckd_signal:
            parts.append("CKM 3 by subclinical atherosclerosis")
        else:
            parts.append(f"CKM {stage}")
    if kdigo:
        parts.append(f"kidney {kdigo}")
        if getattr(patient, "uacr", None) is None and _uacr_completion_relevant(patient, result):
            parts.append("UACR not available")
    elif _uacr_completion_relevant(patient, result):
        parts.append("UACR not available")
    cac = _emr_fmt(getattr(patient, "cac", None))
    if cac is not None:
        parts.append(f"CAC {cac}")
    elif getattr(patient, "cac_not_done", False):
        parts.append("CAC not measured")
    else:
        incidental = incidental_cac_context(patient)
        if incidental:
            parts.append(incidental)
        else:
            plaque_category = _display_value(getattr(result, "plaque_category", None))
            if plaque_category and str(plaque_category).upper() != "UNKNOWN":
                parts.append(f"plaque {plaque_category}")
            else:
                parts.append("CAC not measured")
    if not parts:
        return None
    return f"{EMR_SUMMARY_LABELS['ckm']}: {'; '.join(parts)}."


def _compact_family_history_context(patient):
    if not _has_premature_family_history(patient):
        return None
    summary = str(getattr(patient, "family_history_summary", "") or "").strip()
    if summary and summary.lower() != "premature family history of ascvd":
        return summary[:1].lower() + summary[1:]
    return "premature family history"


def _emr_context_line(patient):
    parts = []
    if getattr(patient, "rheumatoid_arthritis", False):
        parts.append("RA")
    if getattr(patient, "sle", False):
        parts.append("SLE")
    if getattr(patient, "psoriasis", False):
        parts.append("psoriasis")
    if getattr(patient, "ibd", False):
        parts.append("IBD")
    if getattr(patient, "inflammatory_arthritis", False):
        parts.append("inflammatory arthritis")
    if getattr(patient, "hiv", False):
        parts.append("HIV on ART" if getattr(patient, "stable_art", False) else "HIV")
    if getattr(patient, "osa", False):
        parts.append("OSA")
    if getattr(patient, "masld", False):
        parts.append("MASLD")
    lpa = getattr(patient, "lp_a_value", None)
    lpa_unit = str(getattr(patient, "lp_a_unit", "") or "").strip()
    if (lpa_unit == "nmol/L" and lpa is not None and lpa >= 125) or (
        lpa_unit == "mg/dL" and lpa is not None and lpa >= 50
    ):
        parts.append("elevated Lp(a)")
    if getattr(patient, "smoker", False):
        parts.append("smoking")
    if getattr(patient, "south_asian_ancestry", False):
        parts.append("South Asian ancestry")
    if getattr(patient, "filipino_ancestry", False):
        parts.append("Filipino ancestry")
    if getattr(patient, "suspected_fh_hefh", False):
        parts.append("suspected FH / HeFH")
    ldl_c = getattr(patient, "ldl_c", None)
    if ldl_c is not None and ldl_c >= 190:
        parts.append("LDL-C >=190 / possible FH pathway")
    reproductive_summary = reproductive_history_summary(patient)
    if reproductive_summary:
        if reproductive_summary.lower().startswith("reproductive history"):
            parts.append(reproductive_summary)
        else:
            parts.append(reproductive_summary)
    if getattr(patient, "active_cancer", False):
        parts.append("active cancer")
    if getattr(patient, "cancer_survivor", False):
        if getattr(patient, "cancer_life_expectancy_gt_2y", False):
            parts.append("cancer survivor context with life expectancy >2 years")
        else:
            parts.append("cancer survivor context")
    bac_context = breast_arterial_calcification_context(patient)
    if bac_context:
        parts.append("BAC")
    family = _compact_family_history_context(patient)
    if family:
        parts.append(family)
    if not parts:
        return None
    return f"{EMR_SUMMARY_LABELS['context']}: {'; '.join(parts)}."


def _emr_summary_lines(patient, result):
    return [
        line
        for line in (
            _emr_level_line(patient, result),
            _emr_risk_line(result),
            _emr_ckm_line(patient, result),
            _emr_context_line(patient),
        )
        if line
    ]


def _lipid_target_phrase(patient, result):
    target = (getattr(result, "targets", None) or [None])[0]
    if not target:
        return ""
    parts = []
    ldl_target = _emr_fmt(getattr(target, "ldl_c_target", None))
    apob_target = _emr_fmt(getattr(target, "apob_target", None))
    non_hdl_target = _emr_fmt(getattr(target, "non_hdl_c_target", None))
    if ldl_target:
        parts.append(f"LDL-C <{ldl_target}")
    if apob_target and getattr(patient, "apob", None) is not None:
        parts.append(f"ApoB <{apob_target}")
    if non_hdl_target:
        parts.append(f"non-HDL-C <{non_hdl_target}")
    return ", ".join(parts)


def _short_lipid_action(item, patient, result):
    status = str(getattr(item, "status", "") or "")
    lowered = status.lower()
    if "secondary-prevention" in lowered:
        action = "Intensify secondary-prevention lipid-lowering therapy"
    elif "high-intensity" in lowered:
        action = "High-intensity lipid-lowering therapy indicated"
    elif "discuss starting lipid-lowering therapy" in lowered:
        action = "Lipid-lowering therapy indicated"
    elif "discuss lipid-lowering therapy" in lowered and not getattr(patient, "lipid_lowering", False):
        action = "Lipid-lowering therapy indicated"
    elif "intensify" in lowered:
        action = "Intensify lipid-lowering"
    elif "moderate-intensity" in lowered:
        action = "Discuss moderate-intensity statin"
    elif "continue current lipid treatment" in lowered:
        action = "Continue current lipid treatment"
    elif "no lipid-lowering medication indicated" in lowered:
        action = "No lipid-lowering medication indicated"
    elif "no lipid escalation" in lowered or "lifestyle" in lowered:
        action = "No lipid escalation"
    else:
        action = status.rstrip(".") or "Review lipids"
    triglycerides = getattr(patient, "triglycerides", None)
    apob = getattr(patient, "apob", None)
    target = (getattr(result, "targets", None) or [None])[0]
    apob_target = getattr(target, "apob_target", None) if target else None
    non_hdl = getattr(patient, "non_hdl_c", None)
    non_hdl_target = getattr(target, "non_hdl_c_target", None) if target else None
    ldl_unavailable = getattr(patient, "ldl_c", None) is None and triglycerides is not None and 400 <= triglycerides < 500
    if ldl_unavailable:
        if "high-intensity" in lowered and getattr(patient, "lipid_lowering", False):
            action = "High-intensity lipid-lowering active"
        parts = []
        if apob is not None and apob_target is not None:
            parts.append(f"ApoB {_emr_fmt(apob)}, target <{_emr_fmt(apob_target)}")
        if non_hdl is not None and non_hdl_target is not None:
            parts.append(f"non-HDL-C {_emr_fmt(non_hdl)}, target <{_emr_fmt(non_hdl_target)}")
        targets = "; ".join(parts)
        unavailable = "LDL-C unavailable due to TG"
        return f"{action}; {targets}; {unavailable}" if targets else f"{action}; {unavailable}"
    targets = _lipid_target_phrase(patient, result)
    return f"{action}; {targets}" if targets and "no lipid escalation" not in action.lower() else action


def _short_plaque_action(item, patient):
    cac = _emr_fmt(getattr(patient, "cac", None))
    if cac is not None:
        return f"CAC {cac}"
    status = str(getattr(item, "status", "") or "").strip().rstrip(".")
    lowered = status.lower()
    if lowered in {"not measured", "plaque burden unmeasured"}:
        return "CAC not measured"
    return status or "CAC not measured"


def _short_kidney_action(item, patient):
    uacr = _emr_fmt(getattr(patient, "uacr", None))
    detail = str(getattr(item, "detail", "") or "").strip().rstrip(".")
    status = str(getattr(item, "status", "") or "").strip().rstrip(".")
    if status in {"No kidney-risk signal", "No kidney action", "Stable"}:
        return "Stable"
    if uacr is None and "obtain uacr" in status.lower():
        return "UACR not available; obtain UACR"
    if detail:
        detail = detail.replace("Consider SGLT2 for diabetic CKD.", "consider SGLT2 for diabetic CKD")
        return detail
    if status:
        return status
    return "Stable"


def _short_bp_action(item):
    status = str(getattr(item, "status", "") or "").strip().rstrip(".")
    if status == "Treat toward <130/80":
        return "Treat toward <130/80"
    if status == "At goal":
        return "At goal"
    return status or "BP needed"


def _short_glycemia_action(item):
    status = str(getattr(item, "status", "") or "").strip().rstrip(".")
    detail = str(getattr(item, "detail", "") or "").strip().rstrip(".")
    if detail:
        detail = detail.replace("; weight/activity focus", "")
        return f"{status}; {detail}"
    return status


def _number_or_none(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _short_aspirin_action(item, patient=None):
    status = str(getattr(item, "status", "") or "").strip().rstrip(".")
    detail = str(getattr(item, "detail", "") or "").strip().rstrip(".")
    lowered = f"{status} {detail}".lower()
    if "antiplatelet" in lowered or "clinical ascvd" in lowered:
        return "Secondary-prevention antiplatelet therapy"
    if "aspirin active" in lowered:
        return "Active; confirm indication"
    if "avoid" in lowered:
        return "Avoid routine primary-prevention aspirin"
    if "consider" in lowered:
        cac = _number_or_none(getattr(patient, "cac", None)) if patient is not None else None
        if cac is not None:
            return f"Consider only if bleeding risk is low; CAC {cac:g}"
        return "Consider only if bleeding risk is low"
    return "Not indicated"


def _short_clarifier_action(item):
    lines = list(getattr(item, "detail_lines", None) or getattr(item, "emr_lines", None) or [])
    labels = []
    for line in lines:
        text = str(line or "")
        if "apob" in text.lower():
            labels.append("ApoB")
        elif "lp(a)" in text.lower():
            labels.append("Lp(a)")
        elif "uacr" in text.lower():
            labels.append("UACR")
        elif "cac" in text.lower():
            labels.append("CAC")
        elif "hscrp" in text.lower():
            labels.append("hsCRP")
    return "; ".join(dict.fromkeys(labels))


def _emr_recommendation_text(item, patient, result):
    if item.domain_id == "lipid_lowering":
        return _short_lipid_action(item, patient, result)
    if item.domain_id == "plaque_cac":
        return _short_plaque_action(item, patient)
    if item.domain_id == "kidney_protection":
        return _short_kidney_action(item, patient)
    if item.domain_id == "blood_pressure":
        return _short_bp_action(item)
    if item.domain_id == "glycemia_metabolic":
        return _short_glycemia_action(item)
    if item.domain_id == "aspirin_antiplatelet":
        return _short_aspirin_action(item, patient)
    if item.domain_id == "data_to_clarify":
        return _short_clarifier_action(item)
    return ""


def _emr_recommendation_lines(patient, result):
    domains = {item.domain_id: item for item in build_domain_actions(patient, result)}
    lines = []
    number = 1
    for domain_id in EMR_RECOMMENDATION_DOMAIN_ORDER:
        item = domains.get(domain_id)
        if not item:
            continue
        text = _emr_recommendation_text(item, patient, result)
        if not text:
            continue
        if domain_id == "data_to_clarify" and not text:
            continue
        label = EMR_RECOMMENDATION_DOMAIN_LABELS[domain_id]
        lines.append(f"{number}. {label}: {text}.")
        number += 1
    return lines


def render_emr_note(patient, result):
    """Render the clinician-facing EMR note as compact plain text."""
    lines = [EMR_HEADER, ""]
    lines.extend(_emr_summary_lines(patient, result))
    lines.extend(["", EMR_ASSESSMENT_TITLE])
    diagnosis_entries = prepare_diagnosis_display_entries(result)
    review_state = getattr(result, "diagnosis_review_state", None) or {}
    if review_state:
        diagnosis_entries = apply_diagnosis_review_overrides(
            diagnosis_entries,
            accepted_ids=review_state.get("accepted_ids"),
            suppressed_ids=review_state.get("suppressed_ids"),
            review_ids=review_state.get("review_ids"),
        )
    confirmed_dx, review_dx = split_diagnoses(diagnosis_entries)
    if confirmed_dx or review_dx:
        for line in _emr_assessment_lines(confirmed_dx):
            _append_unique(lines, _albuminuria_assessment_display(line, patient, result))
    else:
        if getattr(patient, "rheumatoid_arthritis", False):
            lines.append("- No new cardiometabolic diagnosis candidates generated.")
        else:
            lines.append("- No diagnosis candidates generated.")

    lines.extend(["", EMR_RECOMMENDATIONS_TITLE])
    recommendations = _emr_recommendation_lines(patient, result)
    if recommendations:
        lines.extend(recommendations)
    else:
        lines.append("1. Additional information: none.")

    return "\n".join(lines)
