from dataclasses import asdict

from core.patient import Patient
from modules.family_history.engine import (
    build_family_history_payload,
    build_family_history_summary,
)
from modules.risk_enhancers.reproductive import (
    is_reproductive_history_applicable,
    reproductive_history_summary,
)
from ui.optional_values import parse_optional_float, parse_optional_int
from ui.theme import section_heading


UNIT_LABEL_BY_KEY = {
    "sbp": "mmHg",
    "dbp": "mmHg",
    "tc": "mg/dL",
    "ldl_c": "mg/dL",
    "hdl_c": "mg/dL",
    "triglycerides": "mg/dL",
    "apob": "mg/dL",
    "lp_a_value": "value",
    "a1c": "%",
    "bmi": "kg/m²",
    "egfr": "mL/min/1.73m²",
    "uacr": "mg/g",
    "creatinine": "mg/dL",
    "hscrp": "mg/L",
    "cac": "Agatston",
}


def label_with_unit(label: str, unit: str | None) -> str:
    if not unit:
        return label
    return f"{label} :gray[{unit}]"


def _empty_to_none(value):
    return None if value in ("", None) else value


def _optional_bool(values, key, default=False):
    if key not in values:
        return default
    value = values.get(key)
    if value in ("", None):
        return None
    return bool(value)


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
    "ibd": "input_ibd",
    "hiv": "input_hiv",
    "osa": "input_osa",
    "masld": "input_masld",
    "lipid_lowering": "input_lipid_lowering",
    "lipid_supplements": "input_lipid_supplements",
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
        diabetes=_optional_bool(values, "diabetes"),
        diabetes_duration_years=parse_optional_float(values.get("diabetes_duration_years")),
        diabetic_retinopathy=_optional_bool(values, "diabetic_retinopathy"),
        diabetic_neuropathy=_optional_bool(values, "diabetic_neuropathy"),
        abi=parse_optional_float(values.get("abi")),
        abi_lt_0_9=_optional_bool(values, "abi_lt_0_9"),
        hypertension=_optional_bool(values, "hypertension"),
        sbp=parse_optional_float(values.get("sbp")),
        dbp=parse_optional_float(values.get("dbp")),
        bp_treated=_optional_bool(values, "bp_treated"),
        smoker=_optional_bool(values, "smoker"),
        smoking=_optional_bool(values, "smoker"),
        clinical_ascvd=_optional_bool(values, "clinical_ascvd"),
        clinical_ascvd_context=_empty_to_none(values.get("clinical_ascvd_context")),
        hscrp=parse_optional_float(values.get("hscrp")),
        inflammatory_disease=_optional_bool(values, "inflammatory_disease"),
        rheumatoid_arthritis=_optional_bool(values, "rheumatoid_arthritis"),
        sle=_optional_bool(values, "sle"),
        psoriasis=_optional_bool(values, "psoriasis"),
        ibd=_optional_bool(values, "ibd"),
        hiv=_optional_bool(values, "hiv"),
        osa=_optional_bool(values, "osa"),
        masld=_optional_bool(values, "masld"),
        family_history_premature_ascvd=_optional_bool(
            values, "family_history_premature_ascvd"
        ),
        family_history_relationship=_empty_to_none(
            values.get("family_history_relationship")
        ),
        family_history_event_type=_empty_to_none(
            values.get("family_history_event_type")
        ),
        family_history_age_at_event=parse_optional_float(values.get("family_history_age_at_event")),
        early_menopause=_optional_bool(values, "early_menopause"),
        menopause_age=parse_optional_int(values.get("menopause_age")),
        premature_menopause=_optional_bool(values, "premature_menopause"),
        preeclampsia=_optional_bool(values, "preeclampsia"),
        gestational_hypertension=_optional_bool(values, "gestational_hypertension"),
        gestational_diabetes=_optional_bool(values, "gestational_diabetes"),
        preterm_delivery=_optional_bool(values, "preterm_delivery"),
        small_for_gestational_age=_optional_bool(values, "small_for_gestational_age"),
        recurrent_pregnancy_loss=_optional_bool(values, "recurrent_pregnancy_loss"),
        pcos_or_irregular_menses=_optional_bool(values, "pcos_or_irregular_menses"),
        early_menarche=_optional_bool(values, "early_menarche"),
        menarche_age=parse_optional_int(values.get("menarche_age")),
        lipid_lowering=_optional_bool(values, "lipid_lowering"),
        lipid_supplements=_optional_bool(values, "lipid_supplements"),
        medications_raw=_empty_to_none(values.get("medications_raw")),
        dm_meds_raw=_empty_to_none(values.get("dm_meds_raw")),
        statin_intensity=_empty_to_none(values.get("statin_intensity")),
        statin_intolerance=_optional_bool(values, "statin_intolerance"),
        sglt2=_optional_bool(values, "sglt2"),
        glp1=_optional_bool(values, "glp1"),
        ace_arb=_optional_bool(values, "ace_arb"),
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
        ]
    ):
        patient.inflammatory_disease = True
    if patient.menopause_age is not None:
        patient.early_menopause = patient.menopause_age < 45
        patient.premature_menopause = patient.menopause_age < 40
    if patient.menarche_age is not None:
        patient.early_menarche = patient.menarche_age < 10
    if patient.abi is not None:
        patient.abi_lt_0_9 = patient.abi < 0.9
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
    "diabetes_duration_years",
    "family_history_age_at_event",
    "menopause_age",
    "menarche_age",
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
    display_label = label_with_unit(label, UNIT_LABEL_BY_KEY.get(key))
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
    raw = st.text_input(display_label, key=widget_key)
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
    value = st.checkbox(label, **kwargs)
    if st.session_state.get(f"_unknown_{widget_key}") and value is False:
        return None
    if value is True:
        st.session_state.pop(f"_unknown_{widget_key}", None)
    return value


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


def _reproductive_summary_from_inputs(inputs):
    patient = Patient(
        age=None,
        sex=str(inputs.get("sex") or "female"),
        early_menopause=bool(inputs.get("early_menopause", False)),
        menopause_age=parse_optional_int(inputs.get("menopause_age")),
        premature_menopause=bool(inputs.get("premature_menopause", False)),
        preeclampsia=bool(inputs.get("preeclampsia", False)),
        gestational_hypertension=bool(inputs.get("gestational_hypertension", False)),
        gestational_diabetes=bool(inputs.get("gestational_diabetes", False)),
        preterm_delivery=bool(inputs.get("preterm_delivery", False)),
        small_for_gestational_age=bool(inputs.get("small_for_gestational_age", False)),
        recurrent_pregnancy_loss=bool(inputs.get("recurrent_pregnancy_loss", False)),
        pcos_or_irregular_menses=bool(inputs.get("pcos_or_irregular_menses", False)),
        early_menarche=bool(inputs.get("early_menarche", False)),
        menarche_age=parse_optional_int(inputs.get("menarche_age")),
    )
    if patient.menopause_age is not None:
        patient.early_menopause = patient.menopause_age < 45
        patient.premature_menopause = patient.menopause_age < 40
    if patient.menarche_age is not None:
        patient.early_menarche = patient.menarche_age < 10
    return reproductive_history_summary(patient) or "none reported"


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
        st.caption("US lipid units shown; convert mmol/L before entry.")

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
        with st.expander("Edit diabetes-specific risk enhancers", expanded=False):
            d1, d2, d3, d4 = st.columns(4)
            with d1:
                inputs["diabetes_duration_years"] = _numeric_input(
                    st, "Diabetes duration (years)", parsed, "diabetes_duration_years"
                )
            with d2:
                inputs["diabetic_retinopathy"] = _checkbox_input(
                    st, "Retinopathy", parsed, "diabetic_retinopathy"
                )
                inputs["diabetic_neuropathy"] = _checkbox_input(
                    st, "Neuropathy", parsed, "diabetic_neuropathy"
                )
            with d3:
                inputs["abi"] = _numeric_input(st, "ABI", parsed, "abi", step=0.01, decimals=2)
            with d4:
                inputs["abi_lt_0_9"] = _checkbox_input(st, "ABI <0.9", parsed, "abi_lt_0_9")

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

        show_reproductive = is_reproductive_history_applicable(
            Patient(age=None, sex=str(inputs.get("sex") or parsed.get("sex") or "unknown"))
        )
        if show_reproductive:
            st.caption(f"Reproductive history: {_reproductive_summary_from_inputs({**parsed, **inputs})}")
            with st.expander("Edit reproductive history", expanded=False):
                rep1, rep2, rep3, rep4 = st.columns(4)
                with rep1:
                    inputs["early_menopause"] = _checkbox_input(st, "Early menopause", parsed, "early_menopause")
                    inputs["menopause_age"] = _numeric_input(st, "Menopause age", parsed, "menopause_age")
                with rep2:
                    inputs["preeclampsia"] = _checkbox_input(st, "Preeclampsia", parsed, "preeclampsia")
                    inputs["gestational_hypertension"] = _checkbox_input(st, "Gestational HTN", parsed, "gestational_hypertension")
                with rep3:
                    inputs["gestational_diabetes"] = _checkbox_input(st, "Gestational diabetes", parsed, "gestational_diabetes")
                    inputs["preterm_delivery"] = _checkbox_input(st, "Preterm delivery", parsed, "preterm_delivery")
                with rep4:
                    inputs["small_for_gestational_age"] = _checkbox_input(st, "SGA infant", parsed, "small_for_gestational_age")
                    inputs["recurrent_pregnancy_loss"] = _checkbox_input(st, "Recurrent loss", parsed, "recurrent_pregnancy_loss")
                rep5, rep6 = st.columns(2)
                with rep5:
                    inputs["pcos_or_irregular_menses"] = _checkbox_input(st, "PCOS / irregular menses", parsed, "pcos_or_irregular_menses")
                with rep6:
                    inputs["early_menarche"] = _checkbox_input(st, "Early menarche", parsed, "early_menarche")
                    inputs["menarche_age"] = _numeric_input(st, "Menarche age", parsed, "menarche_age")

    with st.container(border=True):
        section_heading(st, "Medications")
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            inputs["lipid_lowering"] = _checkbox_input(
                st, "Lipid lowering", parsed, "lipid_lowering"
            )
        with col2:
            bp_meds_value = st.checkbox(
                "BP meds",
                key="input_bp_meds",
                **(
                    {}
                    if "input_bp_meds" in st.session_state
                        else {"value": bool(inputs.get("bp_treated") or parsed.get("bp_treated"))}
                ),
            )
            if st.session_state.get("_unknown_input_bp_meds") and bp_meds_value is False:
                inputs["bp_treated"] = None
            else:
                if bp_meds_value is True:
                    st.session_state.pop("_unknown_input_bp_meds", None)
                inputs["bp_treated"] = bp_meds_value
        with col3:
            inputs["sglt2"] = _checkbox_input(st, "SGLT2", parsed, "sglt2")
        with col4:
            inputs["glp1"] = _checkbox_input(st, "GLP1", parsed, "glp1")
        with col5:
            inputs["ace_arb"] = _checkbox_input(st, "ACE/ARB", parsed, "ace_arb")
        with col6:
            inputs["lipid_supplements"] = _checkbox_input(
                st, "Lipid supplements", parsed, "lipid_supplements"
            )
        inputs["medications_raw"] = st.session_state.get(
            "input_medications_raw", parsed.get("medications_raw")
        )
        inputs["dm_meds_raw"] = st.session_state.get(
            "input_dm_meds_raw", parsed.get("dm_meds_raw")
        )
        inputs["statin_intensity"] = st.session_state.get(
            "input_statin_intensity", parsed.get("statin_intensity")
        )
        inputs["statin_intolerance"] = bool(
            st.session_state.get(
                "input_statin_intolerance", parsed.get("statin_intolerance", False)
            )
        )

    return inputs
