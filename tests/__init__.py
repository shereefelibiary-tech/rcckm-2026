from __future__ import annotations

from html.parser import HTMLParser

from core.engine import evaluate_patient
from core.patient import Patient
from renderers.emr_renderer import render_emr_note
from renderers.patient_roadmap import render_patient_roadmap, render_patient_roadmap_text
from renderers.prevent_card import render_prevent_card
from renderers.where_patient_falls import build_where_patient_falls_html


class _VisibleTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self._ignored_tag_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"style", "script"}:
            self._ignored_tag_depth += 1

    def handle_endtag(self, tag):
        if tag in {"style", "script"} and self._ignored_tag_depth:
            self._ignored_tag_depth -= 1

    def handle_data(self, data):
        if self._ignored_tag_depth:
            return
        text = str(data or "").strip()
        if text:
            self.parts.append(text)


def html_visible_text(html: str) -> str:
    parser = _VisibleTextParser()
    parser.feed(html or "")
    return " ".join(parser.parts)


def evaluate_dict(patient_dict: dict):
    patient = Patient(**patient_dict)
    result = evaluate_patient(patient)
    return patient, result


def diagnosis_names(result) -> list[str]:
    return [
        str(candidate.name or "")
        for candidate in getattr(result, "diagnosis_candidates", []) or []
    ]


def action_lines(result) -> list[str]:
    return [
        str(getattr(result, "dominant_action", "") or ""),
        *[str(item or "") for item in (getattr(result, "recommendations", []) or [])],
    ]


def clinical_visible_text(patient, result) -> str:
    html_outputs = [
        render_prevent_card(result),
        build_where_patient_falls_html(patient, result),
        render_patient_roadmap(patient, result),
    ]
    text_outputs = [
        render_emr_note(patient, result),
        render_patient_roadmap_text(patient, result),
        "\n".join(action_lines(result)),
        "\n".join(diagnosis_names(result)),
        "\n".join(getattr(result, "top_drivers", []) or []),
    ]
    return "\n".join([*(html_visible_text(html) for html in html_outputs), *text_outputs])


def assert_no_raw_html_visible(text: str):
    assert "<div" not in text
    assert "<ul" not in text
    assert "<li" not in text
    assert "</" not in text
