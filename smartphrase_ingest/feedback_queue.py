from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from smartphrase_ingest.coverage import ParserCoverageReport, ParserRecognitionItem
from smartphrase_ingest.profiles import PARSER_VERSION


@dataclass(frozen=True)
class ParserFeedbackEvent:
    """Developer-reviewed parser miss or ambiguity; never mutates parser rules."""

    parser_version: str
    source_system: str
    parser_profile_id: str | None
    field_name: str
    issue_type: str
    source_text_snippet: str
    expected_behavior: str | None = None
    recognition_status: str = ""
    confidence: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def _issue_type(item: ParserRecognitionItem) -> str:
    source = (item.source_text or "").lower()
    if item.status == "invalid":
        return "conflicting_values"
    if "placeholder" in source or "***" in source:
        return "placeholder_detected"
    if "unclear" in source or "uncertain" in item.confidence.lower():
        return "ambiguous_section"
    if item.status == "review":
        return "unsupported_format"
    return "missing_field"


def build_feedback_events(
    coverage_report: ParserCoverageReport,
    *,
    expected_behavior: dict[str, str] | None = None,
) -> list[ParserFeedbackEvent]:
    """Create auditable feedback events for review-needed or missing fields."""
    expected_behavior = expected_behavior or {}
    events: list[ParserFeedbackEvent] = []
    for item in coverage_report.recognition_items:
        if item.status == "extracted":
            continue
        if item.status == "missing" and item.field_id not in set(coverage_report.missing_core_fields) | {
            "apob",
            "lp_a_value",
            "uacr",
            "cac",
            "family_history",
            "hscrp",
        }:
            continue
        events.append(
            ParserFeedbackEvent(
                parser_version=PARSER_VERSION,
                source_system=coverage_report.source_system,
                parser_profile_id=coverage_report.parser_profile_id,
                field_name=item.field_id,
                issue_type=_issue_type(item),
                source_text_snippet=(item.source_text or "")[:240],
                expected_behavior=expected_behavior.get(item.field_id),
                recognition_status=item.status,
                confidence=item.confidence,
            )
        )
    return events
