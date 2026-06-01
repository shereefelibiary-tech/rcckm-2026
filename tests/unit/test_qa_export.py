import json

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
    assert decoded["visible_ui_summary_text"]
    assert decoded["app_version"]
    assert decoded["git_commit"] == "abc1234"
    assert decoded["timestamp"] == "2026-06-01T00:00:00+00:00"


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
    assert 'data-testid="rcckm-qa-export"' in markdown_text
    assert "parsed_patient_json" in markdown_text
    assert "engine_output_json" in markdown_text
