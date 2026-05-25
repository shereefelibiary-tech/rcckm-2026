from __future__ import annotations

from dataclasses import asdict, is_dataclass
from html.parser import HTMLParser
import re
from typing import Any

from core.engine import evaluate_patient as run_engine
from core.patient import Patient
from modules.actions.scaffold import build_action_recommendation_lines
from renderers.emr_renderer import render_emr_note
from renderers.patient_roadmap import render_patient_roadmap, render_patient_roadmap_text
from renderers.prevent_card import render_prevent_card
from renderers.where_patient_falls import build_where_patient_falls_html


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"style", "script"}:
            self._ignored_depth += 1

    def handle_endtag(self, tag):
        if tag in {"style", "script"} and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data):
        if self._ignored_depth:
            return
        text = str(data or "").strip()
        if text:
            self.parts.append(text)


def html_visible_text(html: str) -> str:
    """Extract user-visible text from renderer HTML for output assertions."""
    parser = _VisibleTextParser()
    parser.feed(str(html or ""))
    return " ".join(parser.parts)


def evaluate_case(patient_dict_or_patient: dict[str, Any] | Patient) -> tuple[Patient, Any]:
    """Build a Patient when needed and run the RCCKM engine."""
    patient = (
        patient_dict_or_patient
        if isinstance(patient_dict_or_patient, Patient)
        else Patient(**patient_dict_or_patient)
    )
    return patient, run_engine(patient)


def evaluate_patient_case(patient_or_dict: dict[str, Any] | Patient) -> tuple[Patient, Any]:
    """Compatibility helper for validation tests that evaluate a patient case."""
    return evaluate_case(patient_or_dict)


def render_emr(patient: Patient, result: Any) -> str:
    """Render the EMR note as plain text."""
    return render_emr_note(patient, result)


def render_roadmap(patient: Patient, result: Any) -> str:
    """Render the patient roadmap as plain text."""
    return render_patient_roadmap_text(patient, result)


def diagnosis_text(result: Any) -> str:
    """Return diagnosis candidate names as plain text."""
    return "\n".join(
        str(getattr(candidate, "name", "") or "")
        for candidate in (getattr(result, "diagnosis_candidates", None) or [])
    )


def action_text(result: Any, patient: Patient | None = None) -> str:
    """Return the flattened clinical action text used by report renderers."""
    lines = build_action_recommendation_lines(patient, result)
    if lines:
        return "\n".join(str(line or "") for line in lines)
    return "\n".join(
        [
            str(getattr(result, "dominant_action", "") or ""),
            *[str(item or "") for item in (getattr(result, "recommendations", None) or [])],
        ]
    )


def render_all_outputs(patient: Patient, result: Any) -> dict[str, str]:
    """Render major report surfaces into independently assertable text buckets."""
    prevent_html = render_prevent_card(result)
    where_html = build_where_patient_falls_html(patient, result)
    roadmap_html = render_patient_roadmap(patient, result)
    emr = render_emr_note(patient, result)
    roadmap_text = render_patient_roadmap_text(patient, result)
    actions = action_text(result, patient)
    diagnoses = diagnosis_text(result)
    global_text = "\n".join(
        [
            html_visible_text(prevent_html),
            html_visible_text(where_html),
            html_visible_text(roadmap_html),
            emr,
            roadmap_text,
            actions,
            diagnoses,
            "\n".join(str(item or "") for item in (getattr(result, "top_drivers", None) or [])),
        ]
    )
    return {
        "prevent": html_visible_text(prevent_html),
        "where": html_visible_text(where_html),
        "roadmap": roadmap_text,
        "roadmap_html_visible": html_visible_text(roadmap_html),
        "emr": emr,
        "actions": actions,
        "diagnoses": diagnoses,
        "visible": global_text,
    }


def visible_text(patient: Patient, result: Any) -> str:
    """Return combined visible clinical text across major report sections."""
    return render_all_outputs(patient, result)["visible"]


def assert_absent(text: str, phrases: list[str] | tuple[str, ...]) -> None:
    """Assert each phrase is absent using case-insensitive matching."""
    haystack = str(text or "").lower()
    for phrase in phrases or []:
        assert str(phrase).lower() not in haystack


def assert_present(text: str, phrases: list[str] | tuple[str, ...]) -> None:
    """Assert each phrase is present using case-insensitive matching."""
    haystack = str(text or "").lower()
    for phrase in phrases or []:
        assert str(phrase).lower() in haystack


CONTRADICTORY_PHRASE_PAIRS = (
    ("No escalation", "high-intensity"),
    ("No escalation", "lipid-lowering therapy indicated"),
    ("Subclinical coronary atherosclerosis", "CAC not performed"),
    ("aspirin not indicated", "aspirin may be considered"),
)


def assert_no_contradictions(text: str) -> None:
    """Fail when mutually incompatible output phrases appear together."""
    haystack = str(text or "").lower()
    for left, right in CONTRADICTORY_PHRASE_PAIRS:
        assert not (left.lower() in haystack and right.lower() in haystack), (
            f"Contradictory output pair found: {left!r} with {right!r}"
        )
    cac_zero_measured = re.search(
        r"\b(cac 0 measured|plaque:\s*cac 0|coronary calcium score:\s*0)\b",
        haystack,
    )
    assert not ("cac not performed" in haystack and cac_zero_measured), (
        "Contradictory output pair found: 'CAC not performed' with measured CAC 0 language"
    )


def assert_no_contradictory_phrases(text: str) -> None:
    """Compatibility alias for never-cross validation language checks."""
    assert_no_contradictions(text)


def patient_to_dict(patient: Patient) -> dict[str, Any]:
    """Return a stable patient dict for failure messages and fuzz artifacts."""
    if is_dataclass(patient):
        return asdict(patient)
    return dict(getattr(patient, "__dict__", {}) or {})
