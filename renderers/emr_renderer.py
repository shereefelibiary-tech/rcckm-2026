from core.diagnosis_workflow import (
    apply_diagnosis_review_overrides,
    prepare_diagnosis_display_entries,
    split_diagnoses,
)
from modules.actions.scaffold import build_action_recommendation_lines
from modules.levels.definitions import classify_continuum_position
from modules.risk_enhancers.reproductive import reproductive_history_summary


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
    if getattr(patient, "incidental_cac", False):
        severity = str(getattr(patient, "incidental_cac_severity", "") or "").strip()
        return f"incidental CAC noted{f' ({severity})' if severity else ''}"
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


def _lipid_risk_summary_lines(patient):
    lines = []
    triglycerides = getattr(patient, "triglycerides", None)
    non_hdl_c = getattr(patient, "non_hdl_c", None)
    apob = getattr(patient, "apob", None)
    ldl_c = getattr(patient, "ldl_c", None)

    if triglycerides is not None:
        if triglycerides >= 1000:
            lines.append(f"- TG: {triglycerides:g} mg/dL; pancreatitis-risk range.")
        elif triglycerides >= 500:
            lines.append(f"- TG: {triglycerides:g} mg/dL; severe hypertriglyceridemia.")
        elif triglycerides >= 150:
            lines.append(f"- TG: {triglycerides:g} mg/dL.")

    ldl_unavailable_due_to_tg = ldl_c is None and triglycerides is not None and triglycerides >= 400
    if ldl_unavailable_due_to_tg:
        lines.append("- LDL-C: not calculated due to TG.")

    atherogenic_parts = []
    if apob is not None:
        atherogenic_parts.append(f"ApoB {apob:g} mg/dL")
    if ldl_c is not None:
        atherogenic_parts.append(f"LDL-C {ldl_c:g} mg/dL")
    if non_hdl_c is not None:
        atherogenic_parts.append(f"non-HDL-C {non_hdl_c:g} mg/dL")
    if atherogenic_parts:
        lines.append(f"- Atherogenic burden: {'; '.join(atherogenic_parts)}.")

    lpa_value = getattr(patient, "lp_a_value", None)
    lpa_unit = str(getattr(patient, "lp_a_unit", "") or "").strip()
    if lpa_value is not None:
        unit = f" {lpa_unit}" if lpa_unit else ""
        lines.append(f"- Lp(a): {lpa_value:g}{unit}.")

    return lines


def _lipid_risk_sentence(patient):
    parts = []
    triglycerides = getattr(patient, "triglycerides", None)
    non_hdl_c = getattr(patient, "non_hdl_c", None)
    apob = getattr(patient, "apob", None)
    ldl_c = getattr(patient, "ldl_c", None)
    lpa_value = getattr(patient, "lp_a_value", None)
    lpa_unit = str(getattr(patient, "lp_a_unit", "") or "").strip()

    if apob is not None:
        parts.append(f"ApoB {apob:g} mg/dL")
    if ldl_c is not None:
        parts.append(f"LDL-C {ldl_c:g} mg/dL")
    elif triglycerides is not None and triglycerides >= 400:
        parts.append("LDL-C not calculated due to TG")
    if non_hdl_c is not None:
        parts.append(f"non-HDL-C {non_hdl_c:g} mg/dL")
    if triglycerides is not None:
        tg_label = f"TG {triglycerides:g} mg/dL"
        if triglycerides >= 1000:
            tg_label += " (pancreatitis-risk range)"
        elif triglycerides >= 500:
            tg_label += " (severe)"
        parts.append(tg_label)
    if lpa_value is not None:
        unit = f" {lpa_unit}" if lpa_unit else ""
        parts.append(f"Lp(a) {lpa_value:g}{unit}")

    if not parts:
        return None
    return f"Atherogenic/metabolic burden: {'; '.join(parts)}."


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
    key = "hcc_confirmed" if confirmed else "hcc_suggested"
    labels = [str(label).strip() for label in (entry.get(key) or []) if str(label).strip()]
    if not labels and entry.get("hcc_supported"):
        labels = [str(entry.get("hcc_label") or "HCC-supported").strip()]
    if not labels:
        return None
    return labels[0] if labels[0].lower() == "hcc-supported" else f"HCC-supported: {labels[0]}"


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
        return "PREVENT not used for treatment decisions in established ASCVD."

    fragments = []
    if getattr(result, "prevent_10y_ascvd", None) is not None:
        fragments.append(f"PREVENT 10-year risk {result.prevent_10y_ascvd:g}%")
    if getattr(result, "prevent_30y_ascvd", None) is not None:
        fragments.append(f"30-year risk {result.prevent_30y_ascvd:g}%")
    if not fragments:
        return "PREVENT unavailable or incomplete; interpretation is based on reviewed worksheet data."
    return "; ".join(fragments) + "."


def _disease_context_sentence(patient, result):
    parts = []
    ckm_stage = getattr(result, "ckm_stage", None) or {}
    if ckm_stage.get("stage") is not None:
        parts.append(f"CKM stage {ckm_stage.get('stage')}")

    kidney_summary = _kidney_summary(patient, result)
    if kidney_summary:
        parts.append(f"kidney {kidney_summary}")

    plaque_summary = _plaque_summary(patient, result)
    if plaque_summary:
        plaque_category = str(_display_value(getattr(result, "plaque_category", None)) or "").upper()
        measured_plaque_category = bool(plaque_category and plaque_category != "UNKNOWN")
        important_plaque = (
            getattr(patient, "clinical_ascvd", False)
            or getattr(patient, "cac", None) is not None
            or getattr(patient, "incidental_cac", False)
            or "LDL-C >=190" in plaque_summary
            or measured_plaque_category
        )
        cac_action = "cac_testing" in (getattr(result, "action_domains", None) or {})
        if important_plaque or cac_action:
            parts.append(f"plaque {plaque_summary}")

    if not parts:
        return None
    return "; ".join(parts) + "."


def _history_context_sentence(patient):
    parts = []
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
    if bool(getattr(patient, "premature_fhx_ascvd", False)) or bool(
        getattr(patient, "family_history_premature_ascvd", False)
    ):
        family_summary = str(getattr(patient, "family_history_summary", "") or "").strip()
        if family_summary:
            parts.append(f"premature family history ({family_summary})")
        else:
            parts.append("premature family history")
    if not parts:
        return None
    return "Risk context: " + "; ".join(parts) + "."


def _impression_paragraphs(patient, result):
    risk_level = _risk_level_summary(patient, result)
    first = f"{risk_level}." if risk_level else None
    prevent = _prevent_impression_sentence(patient, result)

    second_parts = [_disease_context_sentence(patient, result), _lipid_risk_sentence(patient)]
    second = " ".join(part for part in second_parts if part)

    third_parts = []
    if _uacr_completion_relevant(patient, result):
        third_parts.append("UACR not available; obtain to complete kidney-risk assessment.")
    history = _history_context_sentence(patient)
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


def _include_monitoring_line(recommendation, recommendations):
    if "Recheck lipid profile 4-12 weeks" not in recommendation:
        return True
    posture = " ".join(item for item in recommendations if item != recommendation).lower()
    return any(token in posture for token in ("intensify", "started", "starting", "initiat"))


def _short_recommendation_line(recommendation):
    replacements = {
        "Moderate-intensity lipid-lowering therapy is reasonable to reduce cumulative atherogenic exposure.": "Moderate-intensity lipid-lowering therapy reasonable.",
        "Moderate-intensity statin therapy is reasonable to reduce cumulative atherogenic exposure.": "Moderate-intensity statin therapy reasonable.",
        "Lipid-lowering therapy is indicated; treat toward high-risk targets.": "Lipid-lowering therapy indicated; treat toward high-risk targets.",
        "High-intensity lipid-lowering therapy indicated; treat toward high-risk targets.": "High-intensity lipid-lowering therapy indicated.",
        "High-intensity or maximally tolerated statin therapy indicated.": "High-intensity or maximally tolerated statin indicated.",
        "Optimize kidney-protective therapy and confirm albuminuria persistence.": "Confirm albuminuria persistence and optimize kidney-protective therapy.",
        "Treat blood pressure toward individualized goal.": "Treat BP toward goal <130/80.",
        "CAC reasonable for risk clarification if treatment decision remains uncertain.": "CAC reasonable if treatment decision remains uncertain.",
        "Recheck lipid profile 4-12 weeks after starting or intensifying therapy, then every 6-12 months.": "Recheck lipids in 4-12 weeks, then every 6-12 months.",
        "Consider hsCRP to clarify inflammatory residual risk.": "Consider hsCRP if inflammatory residual risk would change management.",
    }
    return replacements.get(recommendation, recommendation)


def render_emr_note(patient, result):
    """Render the clinician-facing EMR note as compact plain text."""
    lines = ["RISK CONTINUUM CKM - CLINICAL REPORT", "", "Impression:"]

    impression = _impression_paragraphs(patient, result)
    if impression:
        lines.extend(impression)
    else:
        lines.append("Interpretation limited by available worksheet data.")

    lines.extend(["", "Assessment:"])
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
            _append_unique(lines, line)
    else:
        lines.append("- No diagnosis candidates generated.")

    lines.extend(["", "Recommendations:"])
    recommendations = build_action_recommendation_lines(patient, result)
    if recommendations:
        for recommendation in recommendations:
            if not _include_monitoring_line(recommendation, recommendations):
                continue
            if recommendation == "Plaque burden unmeasured.":
                continue
            lines.append(f"- {_short_recommendation_line(recommendation)}")
    else:
        lines.append("- No escalation indicated.")

    return "\n".join(lines)
