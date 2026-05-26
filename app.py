try:
    import streamlit as st
except ModuleNotFoundError:
    st = None

from ui.ingest_panel import parse_ingest_text, render_ingest_panel
from ui.demo_case_gallery import build_demo_patient, demo_case_description, demo_case_options
from ui.input_worksheet import (
    apply_patient_to_session_state,
    build_patient_from_inputs,
    patient_to_payload,
    WORKSHEET_KEY_BY_FIELD,
    render_manual_worksheet,
)
from ui.html import render_html
from ui.report_layout import demo_patient, render_report, run_patient
from ui.report_state import (
    clear_report_state,
    hash_worksheet_state,
    initialize_report_state,
    mark_dirty_if_worksheet_changed,
    report_can_render,
    store_interpretation,
)
from ui.theme import apply_global_theme, render_brand_header, section_heading
from ui.validation_safety import render_validation_safety
from modules.prevent.calculator import calculate_prevent_summary


def _init_session_state():
    st.session_state.setdefault("parsed_ingest", {})
    st.session_state.setdefault("parse_report", {"parsed": {}, "meta": {}, "warnings": []})
    st.session_state.setdefault("parsed_needs_review", False)
    st.session_state.setdefault("active_patient", None)
    st.session_state.setdefault("active_patient_source", None)
    st.session_state.setdefault("show_raw_renderer_html", False)
    st.session_state.setdefault("demo_defaults_loaded", False)
    initialize_report_state(st.session_state)


def _set_active_patient(patient, source):
    st.session_state.active_patient = patient
    st.session_state.active_patient_source = source


def _load_demo_defaults_once():
    if st.session_state.demo_defaults_loaded:
        return
    patient = demo_patient()
    apply_patient_to_session_state(st.session_state, patient, overwrite=False)
    st.session_state.demo_defaults_loaded = True
    clear_report_state(st.session_state, dirty=False)


def _reset_to_demo_patient():
    patient = demo_patient()
    _clear_worksheet_state()
    apply_patient_to_session_state(st.session_state, patient, overwrite=True)
    st.session_state.parsed_ingest = {}
    st.session_state.parse_report = {"parsed": {}, "meta": {}, "warnings": []}
    st.session_state.parsed_needs_review = False
    st.session_state.confirmed_diagnosis_names = []
    clear_report_state(st.session_state, dirty=True)


def _clear_worksheet_state():
    for widget_key in WORKSHEET_KEY_BY_FIELD.values():
        st.session_state.pop(widget_key, None)
    st.session_state.pop("input_bp_meds", None)
    for key in list(st.session_state.keys()):
        if str(key).startswith("_unknown_input_"):
            st.session_state.pop(key, None)


def _load_demo_case(case_label, case_name):
    patient = build_demo_patient(case_name)
    _clear_worksheet_state()
    apply_patient_to_session_state(st.session_state, patient, overwrite=True)
    st.session_state.parsed_ingest = {}
    st.session_state.parse_report = {"parsed": {}, "meta": {}, "warnings": []}
    st.session_state.parsed_needs_review = False
    st.session_state.confirmed_diagnosis_names = []
    st.session_state.loaded_demo_case_label = case_label
    clear_report_state(st.session_state, dirty=True)


def _render_patient_debug(patient, source=None):
    with st.expander("Debug: patient payload", expanded=False):
        if source:
            st.caption(f"Source: {source}")
        st.json(patient_to_payload(patient))
    with st.expander("Debug: PREVENT result", expanded=False):
        summary = calculate_prevent_summary(patient)
        st.json(
            {
                "age": getattr(patient, "age", None),
                "model_used": summary.get("model_used"),
                "prevent_10y_ascvd": summary.get("prevent_10y_ascvd"),
                "prevent_10y_total_cvd": summary.get("prevent_10y_total_cvd"),
                "prevent_30y_ascvd": summary.get("prevent_30y_ascvd"),
                "prevent_30y_total_cvd": summary.get("prevent_30y_total_cvd"),
                "missing_inputs": summary.get("missing_inputs") or [],
                "unavailable_reason": summary.get("unavailable_reason"),
                "warnings": summary.get("warnings") or [],
            }
        )


def main():
    if st is None:
        raise RuntimeError("Streamlit is required to run the RCCKM app.")

    st.set_page_config(page_title="RCCKM 2026", layout="wide")
    apply_global_theme(st)
    render_brand_header(st)
    _init_session_state()
    _load_demo_defaults_once()

    with st.sidebar:
        st.markdown("### Navigation")
        active_section = st.radio(
            "Section",
            ["Worksheet", "Validation & Safety"],
            key="app_section",
            label_visibility="collapsed",
        )

        st.markdown("### Worksheet")
        if st.button("Reset to demo patient"):
            _reset_to_demo_patient()
            st.rerun()

        st.markdown("### Demo Case Gallery")
        st.caption(
            "Load a realistic primary-care scenario with standard vitals and lipids to see how RCCKM structures risk, action, EMR documentation, and the patient roadmap."
        )
        demo_options = demo_case_options()
        labels = [label for label, _case_name in demo_options]
        selected_label = st.selectbox(
            "Demo case",
            labels,
            key="demo_case_gallery_selection",
        )
        selected_case_name = dict(demo_options).get(selected_label)
        if selected_case_name:
            description = demo_case_description(selected_case_name)
            if description:
                st.caption(description)
        if st.button("Load demo case", disabled=selected_case_name is None):
            _load_demo_case(selected_label, selected_case_name)

        st.markdown("### Debug")
        st.checkbox(
            "Show raw renderer HTML",
            key="show_raw_renderer_html",
            help="Developer-only: show raw renderer HTML in collapsed expanders.",
        )

    if active_section == "Validation & Safety":
        render_validation_safety(st)
        return

    loaded_demo_case_label = st.session_state.pop("loaded_demo_case_label", None)
    if loaded_demo_case_label:
        st.success(f"Loaded demo case: {loaded_demo_case_label}.")

    parsed = render_ingest_panel(st)

    section_heading(
        st,
        "Review / Edit Worksheet",
        "Parsed values fill the worksheet. Edited values are used for interpretation.",
    )
    inputs = render_manual_worksheet(st, parsed)
    current_worksheet_hash = hash_worksheet_state(inputs)
    worksheet_changed = mark_dirty_if_worksheet_changed(
        st.session_state, current_worksheet_hash
    )

    if st.button("Interpret reviewed worksheet", type="primary"):
        st.session_state.parsed_needs_review = False
        st.session_state.confirmed_diagnosis_names = []
        patient = build_patient_from_inputs(inputs)
        result, _rss_total, _rss_contributions = run_patient(patient)
        store_interpretation(
            st.session_state,
            patient=patient,
            result=result,
            worksheet_hash=current_worksheet_hash,
            source="Reviewed worksheet",
        )
        worksheet_changed = False

    if report_can_render(st.session_state, current_worksheet_hash):
        render_report(st, st.session_state.active_patient)
        _render_patient_debug(
            st.session_state.active_patient,
            st.session_state.active_patient_source,
        )
    else:
        message = "Review the worksheet, then click Interpret reviewed worksheet."
        if worksheet_changed or (
            st.session_state.get("worksheet_dirty")
            and st.session_state.get("last_interpreted_worksheet_hash")
        ):
            message = "Worksheet changed. Click Interpret reviewed worksheet to update the report."
        render_html(
            st,
            f"""
            <div class="rc-panel-compact" style="margin-top: 14px;">
              <div class="rc-muted">{message}</div>
            </div>
            """,
        )


if __name__ == "__main__":
    main()
