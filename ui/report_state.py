import hashlib
import json
from dataclasses import asdict, is_dataclass

from ui.input_worksheet import WORKSHEET_KEY_BY_FIELD, patient_to_payload


REPORT_STATE_DEFAULTS = {
    "report_generated": False,
    "current_result": None,
    "interpreted_patient_snapshot": None,
    "worksheet_dirty": False,
    "last_parsed_text_hash": None,
    "last_ingest_text_hash": None,
    "last_interpreted_worksheet_hash": None,
}


def initialize_report_state(state):
    for key, value in REPORT_STATE_DEFAULTS.items():
        state.setdefault(key, value)


def hash_text(text):
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _value_from_source(source, canonical_field, widget_key):
    if canonical_field in source:
        return source.get(canonical_field)
    return source.get(widget_key)


def _normalize_value(value):
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {str(key): _normalize_value(val) for key, val in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_normalize_value(item) for item in value]
    return value


def worksheet_payload_from_source(source):
    payload = {}
    for field, widget_key in WORKSHEET_KEY_BY_FIELD.items():
        payload[field] = _normalize_value(_value_from_source(source, field, widget_key))
    if "input_bp_meds" in source:
        payload["bp_meds"] = _normalize_value(source.get("input_bp_meds"))
    elif "bp_meds" in source:
        payload["bp_meds"] = _normalize_value(source.get("bp_meds"))
    return payload


def hash_worksheet_state(source):
    payload = worksheet_payload_from_source(source)
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def clear_report_state(state, *, dirty=True):
    state["report_generated"] = False
    state["current_result"] = None
    state["interpreted_patient_snapshot"] = None
    state["active_patient"] = None
    state["active_patient_source"] = None
    if dirty:
        state["worksheet_dirty"] = True


def store_interpretation(state, *, patient, result, worksheet_hash, source="Reviewed worksheet"):
    state["active_patient"] = patient
    state["active_patient_source"] = source
    state["current_result"] = result
    state["interpreted_patient_snapshot"] = patient_to_payload(patient)
    state["last_interpreted_worksheet_hash"] = worksheet_hash
    state["report_generated"] = True
    state["worksheet_dirty"] = False


def mark_dirty_if_worksheet_changed(state, current_hash):
    if not state.get("report_generated") or state.get("current_result") is None:
        return False
    interpreted_hash = state.get("last_interpreted_worksheet_hash")
    if interpreted_hash and current_hash != interpreted_hash:
        clear_report_state(state, dirty=True)
        return True
    return False


def report_can_render(state, current_hash=None):
    if not state.get("report_generated"):
        return False
    if state.get("current_result") is None:
        return False
    if state.get("worksheet_dirty"):
        return False
    if current_hash is not None:
        interpreted_hash = state.get("last_interpreted_worksheet_hash")
        if interpreted_hash and current_hash != interpreted_hash:
            return False
    return state.get("active_patient") is not None
