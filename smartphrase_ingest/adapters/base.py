from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceAdapter:
    """Minimal adapter descriptor for source-specific normalization."""

    source_system: str

    def normalize(self, text: str) -> str:
        return text
