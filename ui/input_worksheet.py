from dataclasses import asdict

from core.patient import Patient
from modules.lipids.non_hdl import calculate_non_hdl
from modules.lipids.statin_intensity import statin_intensity_help_text
from modules.risk_enhancers.breast_arterial_calcification import (
    BAC_ALLOWED_VALUES,
    BAC_HELP_TEXT,
    breast_arterial_calcification_display,
    normalize_breast_arterial_calcification,
)
from modules.risk_enhancers.incidental_cac import (
    INCIDENTAL_CAC_SEVERITY_OPTIONS,
    normalize_incidental_cac_severity,
)
from modules.risk_enhancers.masld import MASLD_SHORT_LABEL, MASLD_TOOLTIP
from modules.family_history.engine import (
    PREMATURE_FAMILY_HISTORY_HELP,
    build_family_history_payload,
    build_family_history_summary,
    compact_family_history_label,
    compact_family_history_option_values,
    compact_family_history_payload,
    infer_compact_family_history_option,
)
from modules.plaque.engine import normalize_cac_percentile
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
    "height_in": "in",
    "weight_lb": "lb",
    "bmi": "kg/m²",
    "egfr": "mL/min/1.73m²",
    "uacr": "mg/g",
    "creatinine": "mg/dL",
    "hscrp": "mg/L",
    "cac": "Agatston",
}

OTHER_INFLAMMATORY_DISEASE_HELP = (
    "Persistent systemic inflammation can act as an ASCVD risk enhancer."
)
RHEUMATOID_ARTHRITIS_HELP = (
    "Rheumatoid arthritis is associated with higher ASCVD risk, especially with active or longstanding disease."
)
SLE_HELP = (
    "Lupus is associated with higher premature ASCVD risk, especially with active disease or kidney involvement."
)
PSORIASIS_HELP = (
    "Psoriasis is associated with higher ASCVD risk, especially when moderate-to-severe or with psoriatic arthritis."
)
IBD_HELP = (
    "Inflammatory bowel disease is associated with higher ASCVD risk, especially during active inflammation."
)
INFLAMMATORY_ARTHRITIS_HELP = (
    "Chronic inflammatory arthritis can raise ASCVD risk, especially when active or longstanding."
)
DIABETES_DURATION_HELP = (
    "Longer diabetes duration can increase cardiovascular and kidney risk, especially when complications or other risk enhancers are present."
)
DIABETIC_RETINOPATHY_HELP = (
    "Diabetic retinopathy is a microvascular complication and can indicate higher overall diabetes-related vascular risk."
)
DIABETIC_NEUROPATHY_HELP = (
    "Diabetic neuropathy is a diabetes complication and can indicate more established metabolic/vascular disease."
)
ABI_PAD_EVIDENCE_HELP = (
    "ABI <0.9 may indicate peripheral artery disease. If PAD is confirmed, this is clinical ASCVD / secondary prevention."
)
SUSPECTED_FH_HEFH_HELP = (
    "Familial hypercholesterolemia / heterozygous FH. Consider with LDL-C >=190 mg/dL, premature ASCVD, or supportive family history."
)
LIFE_EXPECTANCY_GT_2Y_HELP = (
    "Helps determine whether preventive treatment is likely to provide meaningful benefit over the patient's expected time horizon."
)
ANCESTRY_CONTEXT_OPTIONS = (
    "None / not specified",
    "South Asian",
    "Filipino",
    "Other / not listed",
)


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
    "height": "height_in",
    "height_inches": "height_in",
    "weight": "weight_lb",
    "weight_lbs": "weight_lb",
    "smoking": "smoker",
    "premature_family_history": "family_history_premature_ascvd",
    "premature_fhx_ascvd": "family_history_premature_ascvd",
    "mammary_artery_calcification": "breast_arterial_calcification",
    "breast_artery_calcification": "breast_arterial_calcification",
    "vascular_calcification_on_mammogram": "breast_arterial_calcification",
    "arterial_calcifications_on_mammogram": "breast_arterial_calcification",
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
    "height_in": "input_height_in",
    "weight_lb": "input_weight_lb",
    "bmi": "input_bmi",
    "creatinine": "input_creatinine",
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
    "medications_raw": "input_medications_raw",
    "dm_meds_raw": "input_dm_meds_raw",
    "statin_intensity": "input_statin_intensity",
    "statin_intolerance": "input_statin_intolerance",
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
        "mammary_artery_calcification": patient.breast_arterial_calcification,
        "breast_artery_calcification": patient.breast_arterial_calcification,
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
    if overwrite or "input_ancestry_context" not in state:
        state["input_ancestry_context"] = infer_ancestry_context_option(payload)


def build_patient_from_inputs(inputs):
    values = normalize_input_aliases(inputs)
    sex = values.get("sex") or "male"
    cac_value = parse_optional_float(values.get("cac"))
    cac_not_done = bool(values.get("cac_not_done", False)) if cac_value is None else False
    height_in = parse_optional_float(values.get("height_in"))
    weight_lb = parse_optional_float(values.get("weight_lb"))
    bmi = parse_optional_float(values.get("bmi"))
    a1c_value = parse_optional_float(values.get("a1c"))
    diabetes_value = _optional_bool(values, "diabetes")
    clinical_ascvd_value = _optional_bool(values, "clinical_ascvd")
    clinical_ascvd_context = _empty_to_none(values.get("clinical_ascvd_context"))
    confirmed_pad_context = bool(clinical_ascvd_value) and any(
        token in str(clinical_ascvd_context or "").lower()
        for token in ("pad", "peripheral artery", "claudication")
    )
    diabetes_specific_context = bool(diabetes_value) or (
        a1c_value is not None and a1c_value >= 6.5
    )
    if bmi is None and height_in and weight_lb:
        bmi = round(weight_lb * 703 / (height_in * height_in), 1)
    incidental_cac = _optional_bool(values, "incidental_cac")
    incidental_cac_severity = (
        normalize_incidental_cac_severity(values.get("incidental_cac_severity"))
        if incidental_cac
        else None
    )
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
        a1c=a1c_value,
        height_in=height_in,
        weight_lb=weight_lb,
        bmi=bmi,
        creatinine=parse_optional_float(values.get("creatinine")),
        diabetes=diabetes_value,
        diabetes_duration_years=parse_optional_float(values.get("diabetes_duration_years")) if diabetes_specific_context else None,
        diabetic_retinopathy=_optional_bool(values, "diabetic_retinopathy") if diabetes_specific_context else None,
        diabetic_neuropathy=_optional_bool(values, "diabetic_neuropathy") if diabetes_specific_context else None,
        abi=parse_optional_float(values.get("abi")) if (diabetes_specific_context or confirmed_pad_context) else None,
        abi_lt_0_9=_optional_bool(values, "abi_lt_0_9") if (diabetes_specific_context or confirmed_pad_context) else None,
        hypertension=_optional_bool(values, "hypertension"),
        sbp=parse_optional_float(values.get("sbp")),
        dbp=parse_optional_float(values.get("dbp")),
        bp_treated=_optional_bool(values, "bp_treated"),
        smoker=_optional_bool(values, "smoker"),
        smoking=_optional_bool(values, "smoker"),
        clinical_ascvd=clinical_ascvd_value,
        clinical_ascvd_context=clinical_ascvd_context,
        hscrp=parse_optional_float(values.get("hscrp")),
        inflammatory_disease=_optional_bool(values, "inflammatory_disease"),
        rheumatoid_arthritis=_optional_bool(values, "rheumatoid_arthritis"),
        sle=_optional_bool(values, "sle"),
        psoriasis=_optional_bool(values, "psoriasis"),
        inflammatory_arthritis=_optional_bool(values, "inflammatory_arthritis"),
        ibd=_optional_bool(values, "ibd"),
        hiv=_optional_bool(values, "hiv"),
        stable_art=_optional_bool(values, "stable_art"),
        osa=_optional_bool(values, "osa"),
        masld=_optional_bool(values, "masld"),
        south_asian_ancestry=_optional_bool(values, "south_asian_ancestry"),
        filipino_ancestry=_optional_bool(values, "filipino_ancestry"),
        higher_risk_ancestry_context=None,
        active_cancer=_optional_bool(values, "active_cancer"),
        cancer_survivor=_optional_bool(values, "cancer_survivor"),
        cancer_life_expectancy_gt_2y=_optional_bool(values, "cancer_life_expectancy_gt_2y"),
        suspected_fh_hefh=_optional_bool(values, "suspected_fh_hefh"),
        incidental_cac=incidental_cac,
        incidental_cac_severity=incidental_cac_severity,
        breast_arterial_calcification=normalize_breast_arterial_calcification(
            values.get("breast_arterial_calcification")
        ),
        cac_percentile=normalize_cac_percentile(parse_optional_float(values.get("cac_percentile"))),
        zip_code=None,
        neighborhood_sdoh_context=None,
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
    if patient.non_hdl_c is None:
        patient.non_hdl_c = calculate_non_hdl(patient.tc, patient.hdl_c)

    family_history = build_family_history_payload(patient)
    patient.family_history_summary = family_history["summary"]
    patient.premature_fhx_ascvd = family_history["premature_fhx_ascvd"]
    patient.family_history_premature_ascvd = family_history["premature_fhx_ascvd"]
    if any(
        [
            patient.rheumatoid_arthritis,
            patient.sle,
            patient.psoriasis,
            patient.inflammatory_arthritis,
            patient.ibd,
        ]
    ):
        patient.inflammatory_disease = True
    if patient.menopause_age is not None:
        patient.early_menopause = patient.menopause_age < 45
        patient.premature_menopause = patient.menopause_age < 40
    if patient.menarche_age is not None:
        patient.early_menarche = patient.menarche_age < 10
    if patient.abi is not None and (diabetes_specific_context or confirmed_pad_context):
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
    "height_in",
    "weight_lb",
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


def _numeric_input(st, label, parsed, key, step=1, min_value=None, decimals=None, help=None):
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
    kwargs = {"key": widget_key}
    if help:
        kwargs["help"] = help
    raw = st.text_input(display_label, **kwargs)
    parsed_value = parse_optional_int(raw) if integer else parse_optional_float(raw)
    if parsed_value is not None and min_value is not None and parsed_value < min_value:
        return min_value
    if decimals is not None and parsed_value is not None:
        return round(float(parsed_value), decimals)
    return parsed_value


def _bmi_from_height_weight(height_in, weight_lb):
    height = parse_optional_float(height_in)
    weight = parse_optional_float(weight_lb)
    if not height or not weight:
        return None
    return round(weight * 703 / (height * height), 1)


def _parsed_with_bmi_fallback(parsed):
    values = dict(parsed)
    if parse_optional_float(values.get("bmi")) is None:
        calculated_bmi = _bmi_from_height_weight(
            values.get("height_in"),
            values.get("weight_lb"),
        )
        if calculated_bmi is not None:
            values["bmi"] = calculated_bmi
    return values


def _checkbox_input(st, label, parsed, key, help=None):
    widget_key = f"input_{key}"
    kwargs = {"key": widget_key}
    if help:
        kwargs["help"] = help
    if widget_key not in st.session_state:
        kwargs["value"] = bool(parsed.get(key, False))
    value = st.checkbox(label, **kwargs)
    if st.session_state.get(f"_unknown_{widget_key}") and value is False:
        return None
    if value is True:
        st.session_state.pop(f"_unknown_{widget_key}", None)
    return value


def _control_label_spacer(st):
    st.markdown('<div class="worksheet-control-label-spacer"></div>', unsafe_allow_html=True)


def render_incidental_cac_control(st, parsed):
    with st.container():
        st.markdown(
            '<span class="incidental-cac-control-marker"></span>',
            unsafe_allow_html=True,
        )
        incidental_cac = _checkbox_input(
            st, "Incidental CAC on CT", parsed, "incidental_cac"
        )
        incidental_checked = bool(incidental_cac)
        if incidental_checked:
            severity_options = list(INCIDENTAL_CAC_SEVERITY_OPTIONS)
            if st.session_state.get("input_incidental_cac_severity") not in severity_options:
                st.session_state["input_incidental_cac_severity"] = "present"
            parsed_severity = normalize_incidental_cac_severity(
                parsed.get("incidental_cac_severity")
            )
            severity_kwargs = (
                {}
                if "input_incidental_cac_severity" in st.session_state
                else {"index": severity_options.index(parsed_severity) if parsed_severity in severity_options else 0}
            )
        else:
            severity_options = ["not applicable"]
            st.session_state["input_incidental_cac_severity"] = "not applicable"
            severity_kwargs = {}

        st.markdown(
            '<span class="incidental-cac-severity-label">Severity:</span>',
            unsafe_allow_html=True,
        )
        severity = st.selectbox(
            "Severity",
            severity_options,
            key="input_incidental_cac_severity",
            disabled=not incidental_checked,
            label_visibility="collapsed",
            **severity_kwargs,
        )
    return incidental_cac, severity if incidental_checked else None


def infer_ancestry_context_option(values):
    """Map legacy ancestry booleans into the compact worksheet select value."""
    if bool(values.get("south_asian_ancestry")):
        return "South Asian"
    if bool(values.get("filipino_ancestry")):
        return "Filipino"
    return "None / not specified"


def ancestry_context_to_flags(option):
    """Preserve canonical boolean fields while keeping the worksheet compact."""
    return {
        "south_asian_ancestry": option == "South Asian",
        "filipino_ancestry": option == "Filipino",
        "higher_risk_ancestry_context": None,
    }


def render_ancestry_context_control(st, parsed):
    option = st.selectbox(
        "Ancestry context",
        ANCESTRY_CONTEXT_OPTIONS,
        key="input_ancestry_context",
        **(
            {}
            if "input_ancestry_context" in st.session_state
            else {"index": ANCESTRY_CONTEXT_OPTIONS.index(infer_ancestry_context_option(parsed))}
        ),
    )
    flags = ancestry_context_to_flags(option)
    return flags["south_asian_ancestry"], flags["filipino_ancestry"]


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
        patient = Patient(
            age=parse_optional_int(parsed.get("age")),
            sex=str(parsed.get("sex") or ""),
            family_history_premature_ascvd=True,
            family_history_relationship=relationship,
            family_history_event_type=event_type,
            family_history_age_at_event=None,
        )
        return build_family_history_payload(patient)["summary"] or "Premature family history of ASCVD"
    return "No premature family history"


def _current_compact_family_history_option(st, parsed):
    return infer_compact_family_history_option(
        premature=st.session_state.get(
            "input_family_history_premature_ascvd",
            parsed.get("family_history_premature_ascvd", False),
        ),
        relationship=st.session_state.get(
            "input_family_history_relationship",
            parsed.get("family_history_relationship"),
        ),
        age_at_event=st.session_state.get(
            "input_family_history_age_at_event",
            parsed.get("family_history_age_at_event"),
        ),
    )


def _apply_compact_family_history_selection(inputs, option, st, parsed):
    payload = compact_family_history_payload(option)
    current_relationship = st.session_state.get(
        "input_family_history_relationship",
        parsed.get("family_history_relationship"),
    )
    current_event = st.session_state.get(
        "input_family_history_event_type",
        parsed.get("family_history_event_type"),
    )
    current_age = st.session_state.get(
        "input_family_history_age_at_event",
        parsed.get("family_history_age_at_event"),
    )
    inferred_current = infer_compact_family_history_option(
        premature=True,
        relationship=current_relationship,
        age_at_event=current_age,
    )

    inputs.update(payload)
    if option != "none_unknown" and option == inferred_current:
        inputs["family_history_relationship"] = current_relationship or payload["family_history_relationship"]
        inputs["family_history_event_type"] = current_event or payload["family_history_event_type"]
        inputs["family_history_age_at_event"] = current_age
    return inputs


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
        core = st.columns([0.72, 0.95, 0.72, 0.72, 0.95, 0.78, 1.18])
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
        with core[6]:
            inputs["clinical_ascvd"] = _checkbox_input(
                st, "Clinical ASCVD", parsed, "clinical_ascvd"
            )
            inputs["clinical_ascvd_context"] = st.session_state.get(
                "input_clinical_ascvd_context",
                parsed.get("clinical_ascvd_context"),
            )

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
        bmi_parsed = _parsed_with_bmi_fallback(parsed)
        metabolic_cols = st.columns([0.9, 0.9, 0.9, 0.9], gap="small")
        with metabolic_cols[0]:
            inputs["bmi"] = _numeric_input(st, "BMI", bmi_parsed, "bmi", step=0.1, decimals=1)
            if parse_optional_float(parsed.get("bmi")) is None and parse_optional_float(bmi_parsed.get("bmi")) is not None:
                st.caption("Calculated from height/weight.")
        with metabolic_cols[1]:
            inputs["a1c"] = _numeric_input(st, "A1c", parsed, "a1c", step=0.1, decimals=1)
        with metabolic_cols[2]:
            inputs["egfr"] = _numeric_input(st, "eGFR", parsed, "egfr")
        with metabolic_cols[3]:
            inputs["uacr"] = _numeric_input(st, "UACR", parsed, "uacr")
            if inputs["uacr"] is None:
                st.caption("UACR missing - needed for kidney risk completion.")
            elif inputs["uacr"] == 0:
                st.caption("Measured UACR 0 mg/g.")
        diabetes_cols = st.columns([0.9, 3.0], gap="small")
        with diabetes_cols[0]:
            inputs["diabetes"] = _checkbox_input(st, "Diabetes", parsed, "diabetes")
        with st.expander("Edit height/weight source", expanded=False):
            source_cols = st.columns(2)
            with source_cols[0]:
                inputs["height_in"] = _numeric_input(st, "Height", parsed, "height_in")
            with source_cols[1]:
                inputs["weight_lb"] = _numeric_input(st, "Weight", parsed, "weight_lb")
        diabetes_specific_context = bool(inputs.get("diabetes")) or (
            inputs.get("a1c") is not None and inputs["a1c"] >= 6.5
        )
        if diabetes_specific_context:
            with st.expander("Edit diabetes-specific risk enhancers", expanded=False):
                d1, d2, d3, d4 = st.columns(4)
                with d1:
                    inputs["diabetes_duration_years"] = _numeric_input(
                        st,
                        "Diabetes duration",
                        parsed,
                        "diabetes_duration_years",
                        help=DIABETES_DURATION_HELP,
                    )
                with d2:
                    inputs["diabetic_retinopathy"] = _checkbox_input(
                        st,
                        "Retinopathy",
                        parsed,
                        "diabetic_retinopathy",
                        help=DIABETIC_RETINOPATHY_HELP,
                    )
                    inputs["diabetic_neuropathy"] = _checkbox_input(
                        st,
                        "Neuropathy",
                        parsed,
                        "diabetic_neuropathy",
                        help=DIABETIC_NEUROPATHY_HELP,
                    )
                with d3:
                    inputs["abi"] = _numeric_input(st, "ABI", parsed, "abi", step=0.01, decimals=2)
                with d4:
                    inputs["abi_lt_0_9"] = _checkbox_input(
                        st,
                        "ABI <0.9 / PAD evidence",
                        parsed,
                        "abi_lt_0_9",
                        help=ABI_PAD_EVIDENCE_HELP,
                    )

    with st.container(border=True):
        section_heading(st, "Calcification / plaque imaging")
        cac_cols = st.columns([2.15, 0.72, 0.52, 1.0], gap="small")
        with cac_cols[0]:
            inputs["cac"] = _numeric_input(st, "CAC score", parsed, "cac")
        with cac_cols[1]:
            _control_label_spacer(st)
            if st.button(
                "No CAC",
                key="input_no_cac",
                help="No coronary calcium test has been performed.",
                on_click=_set_no_cac_state,
                type="secondary",
                use_container_width=False,
            ):
                st.rerun()
        with cac_cols[2]:
            _control_label_spacer(st)
            if st.button(
                "Clear",
                key="input_clear_cac",
                help="Clear CAC state.",
                on_click=_clear_cac_state,
                type="secondary",
                use_container_width=False,
            ):
                st.rerun()
        with cac_cols[3]:
            inputs["cac_percentile"] = _numeric_input(
                st, "CAC percentile", parsed, "cac_percentile"
            )

        if inputs["cac"] is not None:
            inputs["cac_not_done"] = False
            st.session_state["input_cac_not_done"] = False
            st.caption("CAC 0 entered." if inputs["cac"] == 0 else "CAC score entered.")
        else:
            inputs["cac_not_done"] = bool(st.session_state.get("input_cac_not_done", parsed.get("cac_not_done", False)))
            st.caption("Plaque burden unmeasured." if inputs["cac_not_done"] else "CAC unknown.")

        calcification_cols = st.columns([3.15, 2.2], gap="small")
        with calcification_cols[0]:
            inputs["incidental_cac"], inputs["incidental_cac_severity"] = (
                render_incidental_cac_control(st, parsed)
            )
        with calcification_cols[1]:
            bac_options = list(BAC_ALLOWED_VALUES)
            parsed_bac = normalize_breast_arterial_calcification(
                parsed.get("breast_arterial_calcification")
            )
            inputs["breast_arterial_calcification"] = st.selectbox(
                "Breast arterial calcification",
                bac_options,
                format_func=lambda value: breast_arterial_calcification_display(value).title(),
                key="input_breast_arterial_calcification",
                help=BAC_HELP_TEXT,
                **(
                    {}
                    if "input_breast_arterial_calcification" in st.session_state
                    else {"index": bac_options.index(parsed_bac) if parsed_bac in bac_options else 0}
                ),
            )

    with st.container(border=True):
        section_heading(st, "Family history / lipid genetics")
        family_cols = st.columns([1.35, 3.65], gap="small")
        with family_cols[0]:
            family_options = compact_family_history_option_values()
            default_family_option = _current_compact_family_history_option(st, parsed)
            selected_family_option = st.selectbox(
                "Premature family history",
                family_options,
                format_func=compact_family_history_label,
                key="input_family_history_pattern",
                help=PREMATURE_FAMILY_HISTORY_HELP,
                **(
                    {}
                    if "input_family_history_pattern" in st.session_state
                    else {
                        "index": family_options.index(default_family_option)
                        if default_family_option in family_options
                        else 0
                    }
                ),
            )
            _apply_compact_family_history_selection(inputs, selected_family_option, st, parsed)
            if selected_family_option == "none_unknown":
                st.caption("No premature family history selected.")
            else:
                st.caption(_family_history_summary_from_state(st, {**parsed, **inputs}))
        genetics_cols = st.columns([1.35, 1.35, 2.3], gap="small")
        with genetics_cols[0]:
            _control_label_spacer(st)
            inputs["suspected_fh_hefh"] = _checkbox_input(
                st,
                "Suspected FH / HeFH",
                parsed,
                "suspected_fh_hefh",
                help=SUSPECTED_FH_HEFH_HELP,
            )
        with genetics_cols[1]:
            (
                inputs["south_asian_ancestry"],
                inputs["filipino_ancestry"],
            ) = render_ancestry_context_control(st, parsed)

    with st.container(border=True):
        section_heading(
            st,
            "Inflammation / immune context",
            "Inflammatory, autoimmune, HIV, cancer, and related risk modifiers.",
        )
        context_cols = st.columns([1.25, 0.62, 0.74], gap="small")
        with context_cols[0]:
            inputs["hscrp"] = _numeric_input(st, "hsCRP", parsed, "hscrp", step=0.1)
        with context_cols[1]:
            _control_label_spacer(st)
            inputs["osa"] = _checkbox_input(st, "OSA", parsed, "osa")
        with context_cols[2]:
            _control_label_spacer(st)
            inputs["masld"] = _checkbox_input(
                st,
                MASLD_SHORT_LABEL,
                parsed,
                "masld",
                help=MASLD_TOOLTIP,
            )
        inputs["inflammatory_disease"] = bool(inputs.get("inflammatory_disease")) or any(
            [
                inputs.get("rheumatoid_arthritis"),
                inputs.get("sle"),
                inputs.get("psoriasis"),
                inputs.get("ibd"),
            ]
        )
        with st.expander("More immune / inflammatory context", expanded=False):
            advanced_cols = st.columns([1.25, 1.15], gap="medium")
            with advanced_cols[0]:
                st.markdown("**Inflammatory / autoimmune**")
                inputs["rheumatoid_arthritis"] = _checkbox_input(
                    st,
                    "RA",
                    parsed,
                    "rheumatoid_arthritis",
                    help=RHEUMATOID_ARTHRITIS_HELP,
                )
                inputs["sle"] = _checkbox_input(st, "SLE", parsed, "sle", help=SLE_HELP)
                inputs["psoriasis"] = _checkbox_input(
                    st, "Psoriasis", parsed, "psoriasis", help=PSORIASIS_HELP
                )
                inputs["ibd"] = _checkbox_input(st, "IBD", parsed, "ibd", help=IBD_HELP)
                inputs["inflammatory_arthritis"] = _checkbox_input(
                    st,
                    "Inflammatory arthritis",
                    parsed,
                    "inflammatory_arthritis",
                    help=INFLAMMATORY_ARTHRITIS_HELP,
                )
                inputs["inflammatory_disease"] = _checkbox_input(
                    st,
                    "Other chronic inflammatory disease",
                    parsed,
                    "inflammatory_disease",
                    help=OTHER_INFLAMMATORY_DISEASE_HELP,
                )
            with advanced_cols[1]:
                st.markdown("**HIV / cancer context**")
                inputs["hiv"] = _checkbox_input(st, "HIV", parsed, "hiv")
                inputs["stable_art"] = _checkbox_input(st, "Stable ART", parsed, "stable_art")
                inputs["active_cancer"] = _checkbox_input(st, "Active cancer", parsed, "active_cancer")
                inputs["cancer_survivor"] = _checkbox_input(st, "Cancer survivor", parsed, "cancer_survivor")
                inputs["cancer_life_expectancy_gt_2y"] = _checkbox_input(
                    st,
                    "Life expectancy >2y",
                    parsed,
                    "cancer_life_expectancy_gt_2y",
                    help=LIFE_EXPECTANCY_GT_2Y_HELP,
                )
        inputs["inflammatory_disease"] = bool(inputs.get("inflammatory_disease")) or any(
            [
                inputs.get("rheumatoid_arthritis"),
                inputs.get("sle"),
                inputs.get("psoriasis"),
                inputs.get("ibd"),
                inputs.get("inflammatory_arthritis"),
            ]
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
        col1, col2, col3, col4, col5 = st.columns(5)
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
        med_cols = st.columns([1.8, 1.3, 0.9, 0.9])
        with med_cols[0]:
            inputs["medications_raw"] = st.text_input(
                "Medication list",
                key="input_medications_raw",
                **(
                    {}
                    if "input_medications_raw" in st.session_state
                    else {"value": parsed.get("medications_raw") or ""}
                ),
            )
        with med_cols[1]:
            inputs["dm_meds_raw"] = st.text_input(
                "Diabetes meds",
                key="input_dm_meds_raw",
                **(
                    {}
                    if "input_dm_meds_raw" in st.session_state
                    else {"value": parsed.get("dm_meds_raw") or ""}
                ),
            )
        with med_cols[2]:
            statin_options = ["", "low", "moderate", "high"]
            parsed_statin = parsed.get("statin_intensity") or ""
            inputs["statin_intensity"] = st.selectbox(
                "Statin intensity",
                statin_options,
                key="input_statin_intensity",
                help=statin_intensity_help_text(),
                **(
                    {}
                    if "input_statin_intensity" in st.session_state
                    else {"index": statin_options.index(parsed_statin) if parsed_statin in statin_options else 0}
                ),
            )
        with med_cols[3]:
            inputs["statin_intolerance"] = _checkbox_input(
                st, "Statin intolerance", parsed, "statin_intolerance"
            )
        inputs["medications_raw"] = _empty_to_none(inputs.get("medications_raw"))
        inputs["dm_meds_raw"] = _empty_to_none(inputs.get("dm_meds_raw"))
        inputs["statin_intensity"] = _empty_to_none(inputs.get("statin_intensity"))

    return inputs
