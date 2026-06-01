import html
import json
import subprocess
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from enum import Enum

from core.version import RCCKM_VERSION
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


def build_qa_export_payload(state, *, timestamp=None, git_commit=None):
    patient = state.get("active_patient")
    result = state.get("current_result")
    final_report_text = ""
    if patient is not None and result is not None:
        final_report_text = render_emr_note(patient, result)

    return {
        "raw_input_text": state.get("ingest_pasted_text") or "",
        "parsed_patient_json": _json_safe(
            state.get("interpreted_patient_snapshot")
            if state.get("interpreted_patient_snapshot") is not None
            else patient
        ),
        "engine_output_json": _json_safe(result),
        "final_report_text": final_report_text,
        "visible_ui_summary_text": _visible_ui_summary_text(result) if result is not None else "",
        "app_version": RCCKM_VERSION,
        "git_commit": git_commit if git_commit is not None else _git_commit(),
        "timestamp": timestamp
        or datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def render_qa_export(st, state):
    if not qa_mode_enabled(st):
        return False
    if not state.get("report_generated") or state.get("current_result") is None:
        return False

    payload = build_qa_export_payload(state)
    json_text = json.dumps(payload, indent=2, default=str)
    st.markdown("### RCCKM QA EXPORT")
    st.markdown(
        f'<pre data-testid="rcckm-qa-export">{html.escape(json_text)}</pre>',
        unsafe_allow_html=True,
    )
    return True
