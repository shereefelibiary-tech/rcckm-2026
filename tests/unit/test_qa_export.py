import json

from core.engine import evaluate_patient
from core.patient import Patient
from ui.input_worksheet import patient_to_payload
from ui.qa_export import build_qa_export_payload, qa_mode_enabled, render_qa_export
from ui.report_layout import demo_patient, run_patient


class _FakeStreamlit:
    def __init__(self, query_params=None):
        self.query_params = query_params or {}
        self.messages = []

    def markdown(self, value, unsafe_allow_html=False):
        self.messages.append(("markdown", value, unsafe_allow_html))


def _state_with_interpretation(raw_text="Age: 55"):
    patient = demo_patient()
    result, _rss_total, _rss_contributions = run_patient(patient)
    return {
        "ingest_pasted_text": raw_text,
        "active_patient": patient,
        "current_result": result,
        "interpreted_patient_snapshot": patient_to_payload(patient),
        "report_generated": True,
    }


def _click_button_by_label(at, label):
    for button in at.button:
        if button.label == label:
            button.click().run(timeout=15)
            return
    raise AssertionError(f"Button not found: {label}")


def test_qa_mode_enabled_reads_streamlit_query_params():
    assert qa_mode_enabled(_FakeStreamlit({"qa_mode": "1"})) is True
    assert qa_mode_enabled(_FakeStreamlit({"qa_mode": ["0", "1"]})) is True
    assert qa_mode_enabled(_FakeStreamlit({"qa_mode": "0"})) is False
    assert qa_mode_enabled(_FakeStreamlit({})) is False


def test_build_qa_export_payload_is_json_serializable():
    payload = build_qa_export_payload(
        _state_with_interpretation("Lp(a): 148.2 nmol/L"),
        timestamp="2026-06-01T00:00:00+00:00",
        git_commit="abc1234",
    )

    encoded = json.dumps(payload, indent=2, default=str)
    decoded = json.loads(encoded)

    assert decoded["raw_input_text"] == "Lp(a): 148.2 nmol/L"
    assert decoded["parsed_patient_json"]["age"] == 55
    assert decoded["engine_output_json"]["snapshot_lines"]
    assert decoded["final_report_text"].startswith("RISK CONTINUUM CKM")
    assert decoded["visible_ui_text"]
    assert decoded["app_version"]
    assert decoded["git_commit"] == "abc1234"
    assert decoded["timestamp"] == "2026-06-01T00:00:00+00:00"


def test_build_qa_export_payload_uses_compact_obesity_bmi_diagnosis_display():
    patient = Patient(age=55, sex="female", bmi=36.2)
    result = evaluate_patient(patient)
    payload = build_qa_export_payload(
        {"ingest_pasted_text": "BMI: 36.2"},
        patient=patient,
        result=result,
        timestamp="2026-06-01T00:00:00+00:00",
        git_commit="abc1234",
    )

    labels = [entry["label_display"] for entry in payload["diagnoses"]]

    assert "Obesity, BMI 36.0-36.9" in labels
    assert "Obesity" not in labels
    assert "Adult BMI 36.0-36.9" not in labels
    compact = next(entry for entry in payload["diagnoses"] if entry["label_display"] == "Obesity, BMI 36.0-36.9")
    assert compact["icd10_confirmed"] == ["E66.9", "Z68.36"]


def test_render_qa_export_only_in_qa_mode_after_report_generation():
    normal_st = _FakeStreamlit()
    state = _state_with_interpretation()

    assert render_qa_export(normal_st, state) is False
    assert normal_st.messages == []

    qa_st = _FakeStreamlit({"qa_mode": "1"})
    assert render_qa_export(qa_st, state) is True

    rendered = "\n".join(str(message[1]) for message in qa_st.messages)
    assert "RCCKM QA EXPORT" in rendered
    assert 'data-testid="rcckm-qa-export"' in rendered
    assert "raw_input_text" in rendered


def test_render_qa_export_waits_for_interpretation():
    qa_st = _FakeStreamlit({"qa_mode": "1"})

    assert render_qa_export(qa_st, {"report_generated": False}) is False
    assert qa_st.messages == []


def test_render_qa_export_after_parse_without_engine_result():
    qa_st = _FakeStreamlit({"qa_mode": "1"})
    state = {
        "ingest_pasted_text": "LDL-C 142 mg/dL",
        "parsed_ingest": {"ldl_c": 142},
        "parse_report": {"parsed": {"ldl_c": 142}},
        "report_generated": False,
    }

    assert render_qa_export(qa_st, state) is True
    rendered = "\n".join(str(message[1]) for message in qa_st.messages)
    assert 'data-testid="rcckm-qa-export"' in rendered
    assert "parsed_patient_json" in rendered
    assert "engine_output_json" in rendered
    assert "final_report_text" in rendered


def test_app_hides_qa_export_without_query_param():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("app.py")
    at.run(timeout=15)
    _click_button_by_label(at, "Interpret risk")

    markdown_text = "\n".join(str(message.value) for message in at.markdown)
    assert len(at.exception) == 0
    assert at.session_state["report_generated"] is True
    assert "RCCKM QA EXPORT" not in markdown_text
    assert 'data-testid="rcckm-qa-export"' not in markdown_text


def test_app_shows_qa_export_in_qa_mode_after_interpretation():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("app.py")
    at.query_params["qa_mode"] = "1"
    at.run(timeout=15)

    markdown_text = "\n".join(str(message.value) for message in at.markdown)
    assert "RCCKM QA EXPORT" not in markdown_text
    assert 'data-testid="rcckm-qa-export"' not in markdown_text

    _click_button_by_label(at, "Interpret risk")

    markdown_text = "\n".join(str(message.value) for message in at.markdown)
    assert len(at.exception) == 0
    assert at.session_state["report_generated"] is True
    assert "RCCKM QA EXPORT" in markdown_text


def test_app_shows_qa_export_in_qa_mode_after_parse_and_apply():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("app.py")
    at.query_params["qa_mode"] = "1"
    at.run(timeout=15)

    at.text_area[0].set_value("55-year-old male BP 138/84 LDL-C 142 ApoB 116 UACR 84 CAC 0")
    _click_button_by_label(at, "Parse and apply")

    markdown_text = "\n".join(str(message.value) for message in at.markdown)
    assert len(at.exception) == 0
    assert at.session_state["report_generated"] is False
    assert "RCCKM QA EXPORT" in markdown_text
