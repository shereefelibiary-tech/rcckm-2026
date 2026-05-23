try:
    import streamlit as st
except ModuleNotFoundError:
    st = None

from ui.ingest_panel import parse_ingest_text, render_ingest_panel
from ui.input_worksheet import (
    apply_patient_to_session_state,
    build_patient_from_inputs,
    patient_to_payload,
    render_manual_worksheet,
)
from ui.report_layout import demo_patient, render_report
from ui.theme import apply_global_theme, render_brand_header, section_heading
from modules.prevent.calculator import calculate_prevent_summary


def _init_session_state():
    st.session_state.setdefault("parsed_ingest", {})
    st.session_state.setdefault("parse_report", {"parsed": {}, "meta": {}, "warnings": []})
    st.session_state.setdefault("parsed_needs_review", False)
    st.session_state.setdefault("active_patient", None)
    st.session_state.setdefault("active_patient_source", None)
    st.session_state.setdefault("show_raw_renderer_html", False)
    st.session_state.setdefault("demo_defaults_loaded", False)


def _set_active_patient(patient, source):
    st.session_state.active_patient = patient
    st.session_state.active_patient_source = source


def _load_demo_defaults_once():
    if st.session_state.demo_defaults_loaded:
        return
    patient = demo_patient()
    apply_patient_to_session_state(st.session_state, patient, overwrite=False)
    _set_active_patient(patient, "Default demo patient")
    st.session_state.demo_defaults_loaded = True


def _reset_to_demo_patient():
    patient = demo_patient()
    apply_patient_to_session_state(st.session_state, patient, overwrite=True)
    st.session_state.parsed_ingest = {}
    st.session_state.parse_report = {"parsed": {}, "meta": {}, "warnings": []}
    st.session_state.parsed_needs_review = False
    st.session_state.confirmed_diagnosis_names = []
    _set_active_patient(patient, "Default demo patient")


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
        st.markdown("### Worksheet")
        if st.button("Reset to demo patient"):
            _reset_to_demo_patient()
            st.rerun()

        st.markdown("### Debug")
        st.checkbox(
            "Show raw renderer HTML",
            key="show_raw_renderer_html",
            help="Developer-only: show raw renderer HTML in collapsed expanders.",
        )

    parsed = render_ingest_panel(st)

    section_heading(
        st,
        "Review / Edit Worksheet",
        "Parsed values fill the worksheet. Edited values are used for interpretation.",
    )
    inputs = render_manual_worksheet(st, parsed)

    if st.button("Interpret reviewed worksheet", type="primary"):
        st.session_state.parsed_needs_review = False
        st.session_state.confirmed_diagnosis_names = []
        patient = build_patient_from_inputs(inputs)
        _set_active_patient(patient, "Reviewed worksheet")

    if st.session_state.active_patient is not None:
        _render_patient_debug(
            st.session_state.active_patient,
            st.session_state.active_patient_source,
        )
        render_report(st, st.session_state.active_patient)


if __name__ == "__main__":
    main()
