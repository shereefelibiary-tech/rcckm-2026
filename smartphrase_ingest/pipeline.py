from __future__ import annotations

from smartphrase_ingest.extractors import EXTRACTORS
from smartphrase_ingest.models import ParsedPatientDraft
from smartphrase_ingest.parser import detect_source_style
from smartphrase_ingest.preprocess import normalize_text, raw_text_hash
from smartphrase_ingest.resolver import resolve_candidates
from smartphrase_ingest.sections import detect_sections


def parse_to_draft(raw_text: str) -> ParsedPatientDraft:
    """Run preprocess -> section detection -> extraction -> resolver."""
    normalized = normalize_text(raw_text)
    draft = ParsedPatientDraft(
        source_system=detect_source_style(normalized),
        raw_text_hash=raw_text_hash(raw_text),
    )
    sections = detect_sections(normalized)
    for extractor in EXTRACTORS:
        for candidate in extractor(sections):
            draft.add_candidate(candidate)
    return resolve_candidates(draft)
