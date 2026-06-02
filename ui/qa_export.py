import html
import json
import subprocess
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from enum import Enum

from core.diagnosis_workflow import prepare_diagnosis_display_entries
from core.version import RCCKM_VERSION
from ui.input_worksheet import patient_to_payload
from renderers.emr_renderer import render_emr_note


def qa_mode_enabled(st):
    query_params = getattr(st, "query_params", {}) or {}
    try:
        value = query_params.get("qa_mode")
    except AttributeError:
        value = None
    if isinstance(value, (list, tuple)):
        return "1" in {str(item) for item in value}
    return str(value) == "1"


def _git_commit():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=1,
        ).strip()
    except Exception:
        return None


def _json_safe(value):
    if is_dataclass(value):
        return _json_safe(asdict(value))
    if isinstance(value, Enum):
        return getattr(value, "value", str(value))
    if isinstance(value, dict):
        return {str(key): _json_safe(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        try:
            return _json_safe(to_dict())
        except Exception:
            return str(value)
    return str(value)


def _visible_ui_summary_text(result):
    lines = [str(line) for line in (getattr(result, "snapshot_lines", None) or []) if line]
    domains = getattr(result, "action_domains", None) or {}
    for item in domains.values():
        label = getattr(item, "label", None)
        status = getattr(item, "status", None)
        if label and status:
            lines.append(f"{label}: {status}")
    return "\n".join(lines)


def _recommendations_text(result):
    if result is None:
        return ""
    lines = [str(line) for line in (getattr(result, "recommendations", None) or []) if line]
    domains = getattr(result, "action_domains", None) or {}
    for item in domains.values():
        label = getattr(item, "label", None)
        status = getattr(item, "status", None)
        detail = getattr(item, "detail", None)
        if label and status:
            line = f"{label}: {status}"
            if detail:
                line = f"{line}. {detail}"
            lines.append(line)
    return "\n".join(lines)


def build_qa_export_payload(state, *, patient=None, result=None, timestamp=None, git_commit=None):
    patient = patient if patient is not None else state.get("active_patient")
    result = result if result is not None else state.get("current_result")
    final_report_text = ""
    if patient is not None and result is not None:
        final_report_text = render_emr_note(patient, result)
    parsed_patient = state.get("interpreted_patient_snapshot")
    if parsed_patient is None and patient is not None:
        parsed_patient = patient_to_payload(patient)
    if parsed_patient is None:
        parsed_patient = state.get("parsed_ingest") or {}
    visible_ui_text = _visible_ui_summary_text(result) if result is not None else ""
    if not visible_ui_text:
        visible_ui_text = state.get("parse_recognition_html") or ""

    return {
        "raw_input_text": state.get("ingest_pasted_text") or "",
        "parsed_patient_json": _json_safe(parsed_patient),
        "engine_output_json": _json_safe(result),
        "final_report_text": final_report_text,
        "recommendations_text": _recommendations_text(result),
        "diagnoses": _json_safe(prepare_diagnosis_display_entries(result) if result is not None else []),
        "targets": _json_safe(getattr(result, "targets", None) or []),
        "ckm_stage": _json_safe(getattr(result, "ckm_stage", None)),
        "risk_level": _json_safe(
            getattr(result, "level_classification", None)
            or getattr(result, "risk_level", None)
        ),
        "visible_ui_text": visible_ui_text,
        "app_version": RCCKM_VERSION,
        "git_commit": git_commit if git_commit is not None else _git_commit(),
        "timestamp": timestamp
        or datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def render_qa_export(st, state, *, patient=None, result=None):
    if not qa_mode_enabled(st):
        return False
    has_report = bool(state.get("report_generated") and (result or state.get("current_result")) is not None)
    has_parse = bool(state.get("parsed_ingest") or state.get("parse_report", {}).get("parsed"))
    if not has_report and not has_parse:
        return False

    payload = build_qa_export_payload(state, patient=patient, result=result)
    json_text = json.dumps(payload, indent=2, default=str)
    pre_html = f'<pre data-testid="rcckm-qa-export">{html.escape(json_text)}</pre>'
    st.markdown("### RCCKM QA EXPORT")
    html_renderer = getattr(st, "html", None)
    if callable(html_renderer):
        html_renderer(pre_html)
    else:
        st.markdown(pre_html, unsafe_allow_html=True)
    return True
