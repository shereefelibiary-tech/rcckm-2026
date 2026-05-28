from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ExtractedCandidate:
    """One candidate value with evidence, confidence, and extraction context."""

    field_name: str
    value: Any
    unit: str | None = None
    date: str | None = None
    source_text: str = ""
    source_section: str | None = None
    confidence: float = 0.0
    reason: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass
class ParsedPatientDraft:
    """Adapter-agnostic patient draft before worksheet review."""

    candidates: dict[str, list[ExtractedCandidate]] = field(default_factory=dict)
    resolved: dict[str, Any] = field(default_factory=dict)
    review_flags: list[str] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)
    source_system: str = "unknown"
    raw_text_hash: str = ""

    def add_candidate(self, candidate: ExtractedCandidate) -> None:
        self.candidates.setdefault(candidate.field_name, []).append(candidate)
