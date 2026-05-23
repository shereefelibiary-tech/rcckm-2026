from diagnosis_workflow import (
    apply_diagnosis_review_overrides,
    prepare_diagnosis_display_entries,
    split_diagnoses,
)
from modules.actions.scaffold import build_action_recommendation_lines


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
    if cac is not None:
        return f"CAC {cac:g}"
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


def _codes_for(entry, confirmed):
    key = "icd10_confirmed" if confirmed else "icd10_suggested"
    codes = entry.get(key) or []
    return [str(code).strip() for code in codes if str(code).strip()]


def _candidate_line(entry, confirmed=True):
    label = str(entry.get("label_display") or entry.get("label") or "").strip()
    if not label:
        return ""

    codes = _codes_for(entry, confirmed=confirmed)
    line = f"- {label}"
    if codes:
        line += f" (ICD: {', '.join(codes)})"
    return line


def _append_unique(lines, line):
    if line and line not in lines:
        lines.append(line)


def render_emr_note(patient, result):
    lines = ["RISK CONTINUUM CKM — CLINICAL REPORT", "", "Risk Summary:"]

    risk_level = _display_value(getattr(result, "risk_level", None))
    if risk_level:
        lines.append(f"- Risk level: {risk_level}")

    ckm_summary = _ckm_summary(result)
    if ckm_summary:
        lines.append(f"- CKM stage: {ckm_summary}")

    if getattr(patient, "clinical_ascvd", False):
        lines.append("- PREVENT: not used for treatment decisions in established ASCVD.")
    elif result.prevent_10y_ascvd is not None:
        lines.append(f"- PREVENT 10-year ASCVD risk: {result.prevent_10y_ascvd:g}%")

    if not getattr(patient, "clinical_ascvd", False) and getattr(result, "prevent_30y_ascvd", None) is not None:
        lines.append(
            f"- PREVENT 30-year ASCVD risk: {result.prevent_30y_ascvd:g}%"
        )

    plaque_summary = _plaque_summary(patient, result)
    if plaque_summary:
        lines.append(f"- Plaque: {plaque_summary}")

    if result.kdigo_stage:
        lines.append(f"- Kidney: {result.kdigo_stage}")
    if _uacr_completion_relevant(patient, result):
        lines.append("- UACR not available; obtain to complete kidney-risk assessment.")

    if result.rss_total is not None:
        lines.append(f"- RSS: {result.rss_total:g}/100")

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
        for entry in confirmed_dx:
            _append_unique(lines, _candidate_line(entry, confirmed=True))
    else:
        lines.append("- No diagnosis candidates generated.")

    lines.extend(["", "Recommendations:"])
    recommendations = build_action_recommendation_lines(patient, result)
    if recommendations:
        for recommendation in recommendations:
            lines.append(f"- {recommendation}")
    else:
        lines.append("- No escalation indicated.")

    return "\n".join(lines)
