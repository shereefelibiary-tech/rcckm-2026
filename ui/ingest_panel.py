import re

from renderers.parse_coverage import render_parse_coverage
from smartphrase_ingest.parser import ParseReport, parse_smartphrase_report
from ui.html import render_html
from ui.report_state import clear_report_state, hash_text
from ui.theme import section_heading

PARSER_FIELD_TO_WORKSHEET_FIELD = {
    "ldl": "ldl_c",
    "hdl": "hdl_c",
    "tg": "triglycerides",
    "lpa": "lp_a_value",
    "lpa_unit": "lp_a_unit",
    "fhx": "family_history_premature_ascvd",
    "ascvd_clinical": "clinical_ascvd",
    "bpTreated": "bp_treated",
    "lipidLowering": "lipid_lowering",
}

WORKSHEET_KEY_BY_FIELD = {
    "age": "input_age",
    "sex": "input_sex",
    "sbp": "input_sbp",
    "dbp": "input_dbp",
    "tc": "input_tc",
    "ldl_c": "input_ldl_c",
    "hdl_c": "input_hdl_c",
    "triglycerides": "input_triglycerides",
    "apob": "input_apob",
    "lp_a_value": "input_lp_a_value",
    "lp_a_unit": "input_lp_a_unit",
    "a1c": "input_a1c",
    "diabetes": "input_diabetes",
    "diabetes_duration_years": "input_diabetes_duration_years",
    "diabetic_retinopathy": "input_diabetic_retinopathy",
    "diabetic_neuropathy": "input_diabetic_neuropathy",
    "abi": "input_abi",
    "abi_lt_0_9": "input_abi_lt_0_9",
    "bmi": "input_bmi",
    "egfr": "input_egfr",
    "uacr": "input_uacr",
    "cac": "input_cac",
    "cac_not_done": "input_cac_not_done",
    "clinical_ascvd": "input_clinical_ascvd",
    "clinical_ascvd_context": "input_clinical_ascvd_context",
    "smoker": "input_smoker",
    "family_history_premature_ascvd": "input_family_history_premature_ascvd",
    "family_history_relationship": "input_family_history_relationship",
    "family_history_event_type": "input_family_history_event_type",
    "family_history_age_at_event": "input_family_history_age_at_event",
    "early_menopause": "input_early_menopause",
    "menopause_age": "input_menopause_age",
    "premature_menopause": "input_premature_menopause",
    "preeclampsia": "input_preeclampsia",
    "gestational_hypertension": "input_gestational_hypertension",
    "gestational_diabetes": "input_gestational_diabetes",
    "preterm_delivery": "input_preterm_delivery",
    "small_for_gestational_age": "input_small_for_gestational_age",
    "recurrent_pregnancy_loss": "input_recurrent_pregnancy_loss",
    "pcos_or_irregular_menses": "input_pcos_or_irregular_menses",
    "early_menarche": "input_early_menarche",
    "menarche_age": "input_menarche_age",
    "hscrp": "input_hscrp",
    "inflammatory_disease": "input_inflammatory_disease",
    "rheumatoid_arthritis": "input_rheumatoid_arthritis",
    "sle": "input_sle",
    "psoriasis": "input_psoriasis",
    "inflammatory_arthritis": "input_inflammatory_arthritis",
    "ibd": "input_ibd",
    "hiv": "input_hiv",
    "stable_art": "input_stable_art",
    "osa": "input_osa",
    "masld": "input_masld",
    "south_asian_ancestry": "input_south_asian_ancestry",
    "filipino_ancestry": "input_filipino_ancestry",
    "active_cancer": "input_active_cancer",
    "cancer_survivor": "input_cancer_survivor",
    "cancer_life_expectancy_gt_2y": "input_cancer_life_expectancy_gt_2y",
    "suspected_fh_hefh": "input_suspected_fh_hefh",
    "incidental_cac": "input_incidental_cac",
    "incidental_cac_severity": "input_incidental_cac_severity",
    "breast_arterial_calcification": "input_breast_arterial_calcification",
    "cac_percentile": "input_cac_percentile",
    "lipid_lowering": "input_lipid_lowering",
    "bp_treated": "input_bp_treated",
    "sglt2": "input_sglt2",
    "glp1": "input_glp1",
    "ace_arb": "input_ace_arb",
}

EXTRA_SESSION_KEY_BY_FIELD = {
    "medications_raw": "input_medications_raw",
    "dm_meds_raw": "input_dm_meds_raw",
    "statin_intensity": "input_statin_intensity",
    "statin_intolerance": "input_statin_intolerance",
    "fasting_lipids": "input_fasting_lipids",
    "fhx_text": "input_fhx_text",
}

INTEGER_WORKSHEET_FIELDS = {
    "age",
    "sbp",
    "dbp",
    "tc",
    "ldl_c",
    "hdl_c",
    "non_hdl_c",
    "triglycerides",
    "apob",
    "lp_a_value",
    "cac",
    "cac_not_done",
    "uacr",
    "egfr",
    "diabetes_duration_years",
    "family_history_age_at_event",
    "menopause_age",
    "menarche_age",
}

ONE_DECIMAL_WORKSHEET_FIELDS = {"a1c", "bmi", "hscrp"}
TWO_DECIMAL_WORKSHEET_FIELDS = {"creatinine"}
PARSER_CONTROLLED_SESSION_KEYS = (
    set(WORKSHEET_KEY_BY_FIELD.values())
    | set(EXTRA_SESSION_KEY_BY_FIELD.values())
    | {"input_bp_meds", "input_ancestry_context"}
)

BOOLEAN_WORKSHEET_FIELDS = {
    "diabetes",
    "diabetic_retinopathy",
    "diabetic_neuropathy",
    "abi_lt_0_9",
    "clinical_ascvd",
    "smoker",
    "family_history_premature_ascvd",
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
    "inflammatory_disease",
    "rheumatoid_arthritis",
    "sle",
    "psoriasis",
    "inflammatory_arthritis",
    "ibd",
    "hiv",
    "stable_art",
    "osa",
    "masld",
    "south_asian_ancestry",
    "filipino_ancestry",
    "active_cancer",
    "cancer_survivor",
    "cancer_life_expectancy_gt_2y",
    "suspected_fh_hefh",
    "incidental_cac",
    "lipid_lowering",
    "bp_treated",
    "sglt2",
    "glp1",
    "ace_arb",
}

REVIEW_FIELDS = [
    "age",
    "sex",
    "sbp",
    "dbp",
    "tc",
    "ldl_c",
    "hdl_c",
    "triglycerides",
    "apob",
    "lp_a_value",
    "lp_a_unit",
    "a1c",
    "diabetes",
    "diabetes_duration_years",
    "diabetic_retinopathy",
    "diabetic_neuropathy",
    "abi",
    "abi_lt_0_9",
    "bmi",
    "egfr",
    "uacr",
    "cac",
    "clinical_ascvd",
    "clinical_ascvd_context",
    "smoker",
    "family_history_premature_ascvd",
    "family_history_relationship",
    "family_history_event_type",
    "family_history_age_at_event",
    "early_menopause",
    "menopause_age",
    "premature_menopause",
    "preeclampsia",
    "gestational_hypertension",
    "gestational_diabetes",
    "preterm_delivery",
    "small_for_gestational_age",
    "recurrent_pregnancy_loss",
    "pcos_or_irregular_menses",
    "early_menarche",
    "menarche_age",
    "hscrp",
    "inflammatory_disease",
    "rheumatoid_arthritis",
    "sle",
    "psoriasis",
    "inflammatory_arthritis",
    "ibd",
    "hiv",
    "stable_art",
    "osa",
    "masld",
    "south_asian_ancestry",
    "filipino_ancestry",
    "active_cancer",
    "cancer_survivor",
    "cancer_life_expectancy_gt_2y",
    "suspected_fh_hefh",
    "incidental_cac",
    "incidental_cac_severity",
    "cac_percentile",
    "lipid_lowering",
    "bp_treated",
    "sglt2",
    "glp1",
    "ace_arb",
]

NUMERIC_FIELDS = {
    "sbp": r"\b(?:sbp|systolic)\b",
    "dbp": r"\b(?:dbp|diastolic)\b",
    "tc": r"\b(?:tc|total cholesterol|total-c|total chol)\b",
    "ldl_c": r"\b(?:ldl-c|ldl)\b",
    "hdl_c": r"\b(?:hdl-c|hdl)\b",
    "triglycerides": r"\b(?:tg|triglycerides|trigs)\b",
    "apob": r"\b(?:apob|apo\s*b)\b",
    "a1c": r"\b(?:a1c|hba1c)\b",
    "egfr": r"\b(?:egfr|e-gfr)\b",
    "uacr": r"\b(?:uacr|acr|urine albumin creatinine ratio)\b",
    "cac": r"\b(?:cac|coronary calcium|calcium score)\b",
    "bmi": r"\bbmi\b",
    "hscrp": r"\b(?:hscrp|hs-crp|high sensitivity crp)\b",
}

PHI_PATTERNS = [
    r"\b\d{3}-\d{2}-\d{4}\b",
    r"\bMRN\b|\bMedical Record\b",
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",
]


def contains_phi(text):
    if not text:
        return False

    cleaned = re.sub(r"@\w+@", "", text)
    return any(re.search(pattern, cleaned, re.IGNORECASE) for pattern in PHI_PATTERNS)


def _parse_number_after_label(text, label_pattern):
    pattern = rf"{label_pattern}\s*(?:=|:|is|of)?\s*([<>]?\s*\d+(?:\.\d+)?)"
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None

    value = match.group(1).replace(" ", "").lstrip("<>")
    try:
        return float(value)
    except ValueError:
        return None


def _record(parsed, meta, field, value, confidence="parsed", source=""):
    parsed[field] = value
    meta[field] = {"confidence": confidence, "source": source}


def _bool_from_text(text, positive_patterns, negative_patterns=None):
    negative_patterns = negative_patterns or []
    for pattern in negative_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return False
    for pattern in positive_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return None


def _canonical_field_name(field):
    return PARSER_FIELD_TO_WORKSHEET_FIELD.get(field, field)


def _parse_report_to_ingest_report(report: ParseReport):
    parsed = {}
    meta = {}

    for field, value in (report.extracted or {}).items():
        canonical = _canonical_field_name(field)
        parsed[canonical] = value
        meta[canonical] = dict((report.field_meta or {}).get(field) or {})

    for field, field_meta in (report.field_meta or {}).items():
        canonical = _canonical_field_name(field)
        meta.setdefault(canonical, dict(field_meta or {}))

    return {
        "parsed": parsed,
        "meta": meta,
        "warnings": list(report.warnings or []),
        "conflicts": list(report.conflicts or []),
        "source_style": getattr(report, "source_style", "unknown"),
        "raw": report.as_dict(),
    }


def parse_ingest_text(text):
    return parse_ingest_report(text)["parsed"]


def parse_ingest_report(text):
    if not text:
        return {"parsed": {}, "meta": {}, "warnings": [], "conflicts": [], "raw": ParseReport().as_dict()}
    return _parse_report_to_ingest_report(parse_smartphrase_report(text))


def build_parse_review_rows(report):
    parsed = report.get("parsed", {}) or {}
    meta = report.get("meta", {}) or {}
    rows = []
    for field in REVIEW_FIELDS:
        field_meta = meta.get(field, {})
        confidence = field_meta.get("confidence")
        if field in parsed:
            confidence = confidence or "parsed"
            value = parsed[field]
        elif confidence:
            value = ""
        else:
            confidence = "not found"
            value = ""

        rows.append(
            {
                "Field": field,
                "Parsed value": str(value),
                "Confidence": confidence,
                "Source": field_meta.get("source", ""),
            }
        )
    return rows


def clear_parser_controlled_session_state(state):
    for key in PARSER_CONTROLLED_SESSION_KEYS:
        state.pop(key, None)
    for key in list(state.keys()):
        if str(key).startswith("_unknown_"):
            state.pop(key, None)


def _next_parse_id(state):
    parse_id = int(state.get("_worksheet_parse_id", 0) or 0) + 1
    state["_worksheet_parse_id"] = parse_id
    state["_worksheet_field_sources"] = {}
    return parse_id


def _mark_parsed_source(state, widget_key, parse_id):
    state.setdefault("_worksheet_field_sources", {})[widget_key] = {
        "source": "parsed",
        "parse_id": parse_id,
    }


def _sync_ancestry_context_select(state, parsed, parse_id):
    if bool((parsed or {}).get("south_asian_ancestry")):
        value = "South Asian"
    elif bool((parsed or {}).get("filipino_ancestry")):
        value = "Filipino"
    else:
        value = "None / not specified"
    state["input_ancestry_context"] = value
    _mark_parsed_source(state, "input_ancestry_context", parse_id)


def apply_parsed_to_session_state(state, parsed, *, clear_existing=True):
    if clear_existing:
        clear_parser_controlled_session_state(state)
    parse_id = _next_parse_id(state)
    for field, value in (parsed or {}).items():
        widget_key = WORKSHEET_KEY_BY_FIELD.get(field)
        extra_key = EXTRA_SESSION_KEY_BY_FIELD.get(field)
        if widget_key:
            if field == "family_history_event_type" and value == "mi":
                value = "MI"
            elif field in BOOLEAN_WORKSHEET_FIELDS and value is None:
                state[f"_unknown_{widget_key}"] = True
                value = False
            elif field in INTEGER_WORKSHEET_FIELDS and value is not None:
                try:
                    value = int(round(float(value)))
                except (TypeError, ValueError):
                    pass
            elif field in ONE_DECIMAL_WORKSHEET_FIELDS and value is not None:
                try:
                    value = round(float(value), 1)
                except (TypeError, ValueError):
                    pass
            elif field in TWO_DECIMAL_WORKSHEET_FIELDS and value is not None:
                try:
                    value = round(float(value), 2)
                except (TypeError, ValueError):
                    pass
            state[widget_key] = value
            if field in BOOLEAN_WORKSHEET_FIELDS and value is not False:
                state.pop(f"_unknown_{widget_key}", None)
            _mark_parsed_source(state, widget_key, parse_id)
        elif extra_key:
            state[extra_key] = value
            _mark_parsed_source(state, extra_key, parse_id)
        if field == "bp_treated":
            state["input_bp_meds"] = value
            if parsed.get(field) is None:
                state["_unknown_input_bp_meds"] = True
            else:
                state.pop("_unknown_input_bp_meds", None)
            _mark_parsed_source(state, "input_bp_meds", parse_id)
        if field == "cac_not_done" and value:
            state["input_cac"] = None
            state["input_cac_not_done"] = True
            _mark_parsed_source(state, "input_cac", parse_id)
            _mark_parsed_source(state, "input_cac_not_done", parse_id)
        if field == "cac" and value is not None:
            state["input_cac_not_done"] = False
            _mark_parsed_source(state, "input_cac_not_done", parse_id)
    if "south_asian_ancestry" in (parsed or {}) or "filipino_ancestry" in (parsed or {}):
        _sync_ancestry_context_select(state, parsed, parse_id)


def _snapshot_worksheet_state(state):
    worksheet_keys = set(WORKSHEET_KEY_BY_FIELD.values()) | set(EXTRA_SESSION_KEY_BY_FIELD.values())
    worksheet_keys.add("input_bp_meds")
    return {key: state[key] for key in worksheet_keys if key in state}


def _restore_worksheet_state(state, snapshot):
    for key, value in (snapshot or {}).items():
        if key not in state or state.get(key) in ("", None):
            state[key] = value


def render_ingest_panel(st):
    with st.container(border=True):
        if st.session_state.pop("clear_ingest_requested", False):
            worksheet_snapshot = st.session_state.pop("clear_ingest_worksheet_snapshot", {})
            st.session_state["ingest_pasted_text"] = ""
            st.session_state["parsed_ingest"] = {}
            st.session_state["parse_report"] = {
                "parsed": {},
                "meta": {},
                "warnings": [],
                "conflicts": [],
            }
            st.session_state["parsed_needs_review"] = False
            st.session_state["last_parsed_text_hash"] = None
            st.session_state["last_ingest_text_hash"] = hash_text("")
            clear_report_state(st.session_state, dirty=True)
            _restore_worksheet_state(st.session_state, worksheet_snapshot)

        title_col, expand_col = st.columns([0.78, 0.22], vertical_alignment="center")
        with title_col:
            section_heading(
                st,
                "Paste EMR text",
                "Paste labs, vitals, meds, or EMR text. Parsed values fill the worksheet below.",
            )
        with expand_col:
            expanded = st.checkbox("Expand paste box", key="ingest_expand_paste_box")
        pasted_text = st.text_area(
            "Paste labs, vitals, meds, or EMR text",
            height=220 if expanded else 105,
            label_visibility="collapsed",
            key="ingest_pasted_text",
        )
        current_text_hash = hash_text(pasted_text)
        previous_text_hash = st.session_state.get("last_ingest_text_hash")
        if (
            previous_text_hash is not None
            and current_text_hash != previous_text_hash
            and st.session_state.get("report_generated")
        ):
            clear_report_state(st.session_state, dirty=True)
        st.session_state["last_ingest_text_hash"] = current_text_hash

        c1, c2, _spacer = st.columns([0.105, 0.105, 0.79])
        with c1:
            parse_clicked = st.button("Parse", type="primary")
        with c2:
            clear_clicked = st.button("Clear", key="clear_ingest")

        if clear_clicked:
            st.session_state["clear_ingest_worksheet_snapshot"] = _snapshot_worksheet_state(st.session_state)
            st.session_state["clear_ingest_requested"] = True
            st.rerun()

        if parse_clicked:
            try:
                if contains_phi(pasted_text):
                    st.error("Possible PHI detected. Please remove identifiers before parsing.")
                else:
                    report = parse_ingest_report(pasted_text)
                    st.session_state.parsed_ingest = report["parsed"]
                    st.session_state.parse_report = report
                    st.session_state.last_parsed_text_hash = current_text_hash
                    st.session_state.last_ingest_text_hash = current_text_hash
                    clear_report_state(st.session_state, dirty=True)
                    apply_parsed_to_session_state(st.session_state, report["parsed"])
                    for warning in report.get("warnings", []):
                        st.warning(warning)
                    for conflict in report.get("conflicts", []):
                        st.warning(conflict)
            except Exception as exc:
                st.session_state.parsed_ingest = {}
                st.session_state.parse_report = {"parsed": {}, "meta": {}, "warnings": [str(exc)], "conflicts": []}
                st.error("Parser could not process the pasted text. Please enter values manually.")
                st.caption(str(exc))
            else:
                st.session_state.parsed_needs_review = True

        parsed = st.session_state.get("parsed_ingest", {})
        report = st.session_state.get("parse_report") or {"parsed": parsed, "meta": {}, "warnings": [], "conflicts": []}
        render_html(st, render_parse_coverage(report if parsed else None))
        if parsed:
            st.caption("Review parsed values in the worksheet before interpretation.")
            if st.checkbox("Parser debug", value=False, key="parser_debug_json"):
                with st.expander("Raw parsed JSON", expanded=False):
                    st.json(report.get("raw") or report)

    return parsed
