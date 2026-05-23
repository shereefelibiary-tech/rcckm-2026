from dataclasses import asdict

from core.patient import Patient
from modules.family_history.engine import (
    build_family_history_payload,
    build_family_history_summary,
)
from ui.optional_values import parse_optional_float, parse_optional_int
from ui.theme import section_heading


def _empty_to_none(value):
    return None if value in ("", None) else value


FIELD_ALIASES = {
    "total_cholesterol": "tc",
    "total_cholesterol_mgdl": "tc",
    "ldl": "ldl_c",
    "hdl": "hdl_c",
    "tg": "triglycerides",
    "lpa": "lp_a_value",
    "lpa_value": "lp_a_value",
    "lpa_unit": "lp_a_unit",
    "smoking": "smoker",
    "premature_family_history": "family_history_premature_ascvd",
    "premature_fhx_ascvd": "family_history_premature_ascvd",
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
    "hscrp": "input_hscrp",
    "inflammatory_disease": "input_inflammatory_disease",
    "rheumatoid_arthritis": "input_rheumatoid_arthritis",
    "sle": "input_sle",
    "psoriasis": "input_psoriasis",
    "ibd": "input_ibd",
    "hiv": "input_hiv",
    "osa": "input_osa",
    "masld": "input_masld",
    "lipid_lowering": "input_lipid_lowering",
    "bp_treated": "input_bp_treated",
    "sglt2": "input_sglt2",
    "glp1": "input_glp1",
    "ace_arb": "input_ace_arb",
}


def normalize_input_aliases(inputs):
    values = dict(inputs or {})
    for source, target in FIELD_ALIASES.items():
        if target not in values or values.get(target) in ("", None):
            if source in values and values.get(source) not in ("", None):
                values[target] = values[source]

    return values


def patient_to_payload(patient):
    payload = asdict(patient)
    aliases = {
        "total_cholesterol": patient.tc,
        "ldl": patient.ldl_c,
        "hdl": patient.hdl_c,
        "tg": patient.triglycerides,
        "lpa": patient.lp_a_value,
        "lpa_unit": patient.lp_a_unit,
        "smoking": patient.smoking,
        "premature_family_history": patient.family_history_premature_ascvd,
    }
    payload.update(aliases)
    return payload


def apply_patient_to_session_state(state, patient, *, overwrite=False):
    payload = patient_to_payload(patient)
    for field, widget_key in WORKSHEET_KEY_BY_FIELD.items():
        if field not in payload:
            continue
        value = payload.get(field)
        if value is None:
            continue
        if overwrite or widget_key not in state:
            state[widget_key] = value

    if patient.bp_treated is not None and (overwrite or "input_bp_meds" not in state):
        state["input_bp_meds"] = bool(patient.bp_treated)


def build_patient_from_inputs(inputs):
    values = normalize_input_aliases(inputs)
    sex = values.get("sex") or "male"
    cac_value = parse_optional_float(values.get("cac"))
    cac_not_done = bool(values.get("cac_not_done", False)) if cac_value is None else False
    patient = Patient(
        age=parse_optional_int(values.get("age")),
        sex=str(sex).lower(),
        tc=parse_optional_float(values.get("tc")),
        ldl_c=parse_optional_float(values.get("ldl_c")),
        hdl_c=parse_optional_float(values.get("hdl_c")),
        triglycerides=parse_optional_float(values.get("triglycerides")),
        non_hdl_c=parse_optional_float(values.get("non_hdl_c")),
        apob=parse_optional_float(values.get("apob")),
        lp_a_value=parse_optional_float(values.get("lp_a_value")),
        lp_a_unit=_empty_to_none(values.get("lp_a_unit")),
        cac=cac_value,
        cac_not_done=cac_not_done,
        egfr=parse_optional_float(values.get("egfr")),
        uacr=parse_optional_float(values.get("uacr")),
        a1c=parse_optional_float(values.get("a1c")),
        bmi=parse_optional_float(values.get("bmi")),
        diabetes=bool(values.get("diabetes", False)),
        hypertension=bool(values.get("hypertension", False)),
        sbp=parse_optional_float(values.get("sbp")),
        dbp=parse_optional_float(values.get("dbp")),
        bp_treated=bool(values.get("bp_treated", False)),
        smoker=bool(values.get("smoker", False)),
        smoking=bool(values.get("smoker", False)),
        clinical_ascvd=bool(values.get("clinical_ascvd", False)),
        clinical_ascvd_context=_empty_to_none(values.get("clinical_ascvd_context")),
        hscrp=parse_optional_float(values.get("hscrp")),
        inflammatory_disease=bool(values.get("inflammatory_disease", False)),
        rheumatoid_arthritis=bool(values.get("rheumatoid_arthritis", False)),
        sle=bool(values.get("sle", False)),
        psoriasis=bool(values.get("psoriasis", False)),
        ibd=bool(values.get("ibd", False)),
        hiv=bool(values.get("hiv", False)),
        osa=bool(values.get("osa", False)),
        masld=bool(values.get("masld", False)),
        family_history_premature_ascvd=bool(
            values.get("family_history_premature_ascvd", False)
        ),
        family_history_relationship=_empty_to_none(
            values.get("family_history_relationship")
        ),
        family_history_event_type=_empty_to_none(
            values.get("family_history_event_type")
        ),
        family_history_age_at_event=parse_optional_float(values.get("family_history_age_at_event")),
        lipid_lowering=bool(values.get("lipid_lowering", False)),
        sglt2=bool(values.get("sglt2", False)),
        glp1=bool(values.get("glp1", False)),
        ace_arb=bool(values.get("ace_arb", False)),
        prevent_10y_ascvd=parse_optional_float(values.get("prevent_10y_ascvd")),
        prevent_10y_total_cvd=parse_optional_float(values.get("prevent_10y_total_cvd")),
        prevent_30y_ascvd=parse_optional_float(values.get("prevent_30y_ascvd")),
        prevent_30y_total_cvd=parse_optional_float(values.get("prevent_30y_total_cvd")),
        prevent_age=parse_optional_float(values.get("prevent_age")),
        prevent_percentile=parse_optional_float(values.get("prevent_percentile")),
    )
    if patient.non_hdl_c is None and patient.tc is not None and patient.hdl_c is not None:
        patient.non_hdl_c = patient.tc - patient.hdl_c

    family_history = build_family_history_payload(patient)
    patient.family_history_summary = family_history["summary"]
    patient.premature_fhx_ascvd = family_history["premature_fhx_ascvd"]
    patient.family_history_premature_ascvd = family_history["premature_fhx_ascvd"]
    if any(
        [
            patient.rheumatoid_arthritis,
            patient.sle,
            patient.psoriasis,
            patient.ibd,
            patient.hiv,
        ]
    ):
        patient.inflammatory_disease = True
    return patient


INTEGER_INPUT_FIELDS = {
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
    "uacr",
    "egfr",
    "family_history_age_at_event",
}


def _coerce_widget_value(value, *, integer=False, decimals=None):
    if value in ("", None):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return value
    if integer:
        return int(round(number))
    if decimals is not None:
        return round(number, decimals)
    return number


def _format_widget_value(value, *, integer=False, decimals=None):
    if value in ("", None):
        return ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if integer:
        return str(int(round(number)))
    if decimals is not None:
        return f"{round(number, decimals):.{decimals}f}"
    return f"{number:g}"


def _numeric_input(st, label, parsed, key, step=1, min_value=None, decimals=None):
    widget_key = f"input_{key}"
    integer = key in INTEGER_INPUT_FIELDS
    value = _coerce_widget_value(parsed.get(key), integer=integer, decimals=decimals)
    if widget_key not in st.session_state:
        st.session_state[widget_key] = _format_widget_value(
            value,
            integer=integer,
            decimals=decimals,
        )
    else:
        st.session_state[widget_key] = _format_widget_value(
            st.session_state[widget_key],
            integer=integer,
            decimals=decimals,
        )
    raw = st.text_input(label, key=widget_key)
    parsed_value = parse_optional_int(raw) if integer else parse_optional_float(raw)
    if parsed_value is not None and min_value is not None and parsed_value < min_value:
        return min_value
    if decimals is not None and parsed_value is not None:
        return round(float(parsed_value), decimals)
    return parsed_value


def _checkbox_input(st, label, parsed, key):
    widget_key = f"input_{key}"
    kwargs = {"key": widget_key}
    if widget_key not in st.session_state:
        kwargs["value"] = bool(parsed.get(key, False))
    return st.checkbox(label, **kwargs)


def _set_no_cac_state():
    import streamlit as st

    st.session_state["input_cac"] = ""
    st.session_state["input_cac_not_done"] = True


def _clear_cac_state():
    import streamlit as st

    st.session_state["input_cac"] = ""
    st.session_state["input_cac_not_done"] = False


def _family_history_summary_from_state(st, parsed):
    relationship = st.session_state.get(
        "input_family_history_relationship",
        parsed.get("family_history_relationship") or "father",
    )
    event_type = st.session_state.get(
        "input_family_history_event_type",
        parsed.get("family_history_event_type") or "MI",
    )
    age_at_event = st.session_state.get(
        "input_family_history_age_at_event",
        parsed.get("family_history_age_at_event"),
    )
    summary = build_family_history_summary(
        relationship,
        event_type,
        parse_optional_float(age_at_event),
    )
    if summary:
        return summary
    if parsed.get("fhx_text"):
        return str(parsed.get("fhx_text"))
    if bool(st.session_state.get("input_family_history_premature_ascvd", parsed.get("family_history_premature_ascvd", False))):
        return "Premature family history"
    return "No premature family history"


def render_manual_worksheet(st, parsed):
    inputs = {}

    with st.container(border=True):
        section_heading(st, "Core inputs")
        core = st.columns([0.8, 1.05, 0.8, 0.8, 1.05, 0.9])
        with core[0]:
            inputs["age"] = _numeric_input(st, "Age", parsed, "age", min_value=0)
        with core[1]:
            sex_default = str(parsed.get("sex") or "male").lower()
            sex_options = ["male", "female"]
            inputs["sex"] = st.selectbox(
                "Sex",
                sex_options,
                key="input_sex",
                **(
                    {}
                    if "input_sex" in st.session_state
                    else {
                        "index": sex_options.index(sex_default)
                        if sex_default in sex_options
                        else 0
                    }
                ),
            )
        with core[2]:
            inputs["sbp"] = _numeric_input(st, "SBP", parsed, "sbp")
        with core[3]:
            inputs["dbp"] = _numeric_input(st, "DBP", parsed, "dbp")
        with core[4]:
            inputs["bp_treated"] = _checkbox_input(st, "BP treated", parsed, "bp_treated")
        with core[5]:
            inputs["smoker"] = _checkbox_input(st, "Smoking", parsed, "smoker")

    with st.container(border=True):
        section_heading(st, "Lipids")
        lipid_cols = st.columns([0.85, 0.85, 0.85, 0.85, 0.85, 0.85, 1.0])
        with lipid_cols[0]:
            inputs["tc"] = _numeric_input(st, "TC", parsed, "tc")
        with lipid_cols[1]:
            inputs["ldl_c"] = _numeric_input(st, "LDL-C", parsed, "ldl_c")
        with lipid_cols[2]:
            inputs["hdl_c"] = _numeric_input(st, "HDL-C", parsed, "hdl_c")
        with lipid_cols[3]:
            inputs["triglycerides"] = _numeric_input(st, "TG", parsed, "triglycerides")
        with lipid_cols[4]:
            inputs["apob"] = _numeric_input(st, "ApoB", parsed, "apob")
        with lipid_cols[5]:
            inputs["lp_a_value"] = _numeric_input(st, "Lp(a)", parsed, "lp_a_value")
        with lipid_cols[6]:
            lp_unit = parsed.get("lp_a_unit") or "nmol/L"
            inputs["lp_a_unit"] = st.selectbox(
                "Lp(a) unit",
                ["nmol/L", "mg/dL"],
                key="input_lp_a_unit",
                **({} if "input_lp_a_unit" in st.session_state else {"index": 0 if lp_unit == "nmol/L" else 1}),
            )

    with st.container(border=True):
        section_heading(st, "Metabolic / Kidney")
        mk_cols = st.columns([0.8, 1.0, 0.8, 0.8, 0.8])
        with mk_cols[0]:
            inputs["a1c"] = _numeric_input(st, "A1c", parsed, "a1c", step=0.1, decimals=1)
        with mk_cols[1]:
            inputs["diabetes"] = _checkbox_input(st, "Diabetes", parsed, "diabetes")
        with mk_cols[2]:
            inputs["bmi"] = _numeric_input(st, "BMI", parsed, "bmi", step=0.1, decimals=1)
        with mk_cols[3]:
            inputs["egfr"] = _numeric_input(st, "eGFR", parsed, "egfr")
        with mk_cols[4]:
            inputs["uacr"] = _numeric_input(st, "UACR", parsed, "uacr")
            if inputs["uacr"] is None:
                st.caption("UACR missing - needed for kidney risk completion.")
            elif inputs["uacr"] == 0:
                st.caption("Measured UACR 0 mg/g.")

    with st.container(border=True):
        section_heading(st, "Plaque / History / Enhancers")
        cac_cols = st.columns([1.0, 1.18, 0.62, 1.2])
        with cac_cols[0]:
            inputs["cac"] = _numeric_input(st, "CAC score", parsed, "cac")
        with cac_cols[1]:
            if st.button(
                "No CAC performed",
                key="input_no_cac",
                help="No coronary calcium test has been performed.",
                on_click=_set_no_cac_state,
                type="secondary",
                use_container_width=True,
            ):
                st.rerun()
        with cac_cols[2]:
            if st.button(
                "Clear",
                key="input_clear_cac",
                help="Clear CAC state.",
                on_click=_clear_cac_state,
                type="secondary",
                use_container_width=True,
            ):
                st.rerun()
        with cac_cols[3]:
            inputs["clinical_ascvd"] = _checkbox_input(
                st, "Clinical ASCVD", parsed, "clinical_ascvd"
            )
            inputs["clinical_ascvd_context"] = st.session_state.get(
                "input_clinical_ascvd_context",
                parsed.get("clinical_ascvd_context"),
            )

        if inputs["cac"] is not None:
            inputs["cac_not_done"] = False
            st.session_state["input_cac_not_done"] = False
            st.caption("CAC 0 entered." if inputs["cac"] == 0 else "CAC score entered.")
        else:
            inputs["cac_not_done"] = bool(st.session_state.get("input_cac_not_done", parsed.get("cac_not_done", False)))
            st.caption("Plaque burden unmeasured." if inputs["cac_not_done"] else "CAC unknown.")

        pe_cols = st.columns([1.25, 1.75, 0.8, 0.75, 0.8, 1.25])
        with pe_cols[0]:
            inputs["family_history_premature_ascvd"] = _checkbox_input(
                st, "Premature family history", parsed, "family_history_premature_ascvd"
            )
        with pe_cols[1]:
            st.caption(_family_history_summary_from_state(st, parsed))
        with pe_cols[2]:
            inputs["hscrp"] = _numeric_input(st, "hsCRP", parsed, "hscrp", step=0.1)
        with pe_cols[3]:
            inputs["osa"] = _checkbox_input(st, "OSA", parsed, "osa")
        with pe_cols[4]:
            inputs["masld"] = _checkbox_input(st, "MASLD", parsed, "masld")
        with pe_cols[5]:
            inputs["inflammatory_disease"] = _checkbox_input(
                st, "Inflammatory disease", parsed, "inflammatory_disease"
            )

        inf1, inf2, inf3, inf4, inf5 = st.columns(5)
        with inf1:
            inputs["hiv"] = _checkbox_input(st, "HIV", parsed, "hiv")
        with inf2:
            inputs["rheumatoid_arthritis"] = _checkbox_input(
                st, "RA", parsed, "rheumatoid_arthritis"
            )
        with inf3:
            inputs["sle"] = _checkbox_input(st, "SLE", parsed, "sle")
        with inf4:
            inputs["psoriasis"] = _checkbox_input(st, "Psoriasis", parsed, "psoriasis")
        with inf5:
            inputs["ibd"] = _checkbox_input(st, "IBD", parsed, "ibd")
        inputs["inflammatory_disease"] = bool(inputs.get("inflammatory_disease")) or any(
            [
                inputs.get("rheumatoid_arthritis"),
                inputs.get("sle"),
                inputs.get("psoriasis"),
                inputs.get("ibd"),
                inputs.get("hiv"),
            ]
        )
        with st.expander("Edit family history details", expanded=False):
            fam1, fam2, fam3 = st.columns([1, 1, 0.8])
            with fam1:
                relationship = parsed.get("family_history_relationship") or "father"
                relationship_options = ["father", "mother", "brother", "sister"]
                inputs["family_history_relationship"] = st.selectbox(
                    "Relationship",
                    relationship_options,
                    key="input_family_history_relationship",
                    **(
                        {}
                        if "input_family_history_relationship" in st.session_state
                        else {
                            "index": relationship_options.index(relationship)
                            if relationship in relationship_options
                            else 0
                        }
                    ),
                )
            with fam2:
                event = parsed.get("family_history_event_type") or "MI"
                event_options = ["MI", "PCI/CABG", "stroke", "sudden cardiac death"]
                inputs["family_history_event_type"] = st.selectbox(
                    "Event type",
                    event_options,
                    key="input_family_history_event_type",
                    **(
                        {}
                        if "input_family_history_event_type" in st.session_state
                        else {"index": event_options.index(event) if event in event_options else 0}
                    ),
                )
            with fam3:
                inputs["family_history_age_at_event"] = _numeric_input(
                    st,
                    "Age at event",
                    parsed,
                    "family_history_age_at_event",
                )

    with st.container(border=True):
        section_heading(st, "Medications")
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            inputs["lipid_lowering"] = _checkbox_input(
                st, "Lipid lowering", parsed, "lipid_lowering"
            )
        with col2:
            inputs["bp_treated"] = st.checkbox(
                "BP meds",
                key="input_bp_meds",
                **(
                    {}
                    if "input_bp_meds" in st.session_state
                    else {"value": bool(inputs.get("bp_treated") or parsed.get("bp_treated"))}
                ),
            )
        with col3:
            inputs["sglt2"] = _checkbox_input(st, "SGLT2", parsed, "sglt2")
        with col4:
            inputs["glp1"] = _checkbox_input(st, "GLP1", parsed, "glp1")
        with col5:
            inputs["ace_arb"] = _checkbox_input(st, "ACE/ARB", parsed, "ace_arb")

    return inputs
