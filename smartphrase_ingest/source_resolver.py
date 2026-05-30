from __future__ import annotations

from typing import Any

from smartphrase_ingest.problem_list_parser import ProblemListSignal


PROOF_RANK = {
    "unknown": 0,
    "narrative": 1,
    "problem_list": 2,
    "active_medication": 3,
    "explicit_structured": 4,
    "data_derived": 5,
}


FIELD_ALIASES = {
    "ascvd_clinical": "clinical_ascvd",
    "fhx": "family_history_premature_ascvd",
}


def canonical_field(field: str) -> str:
    """Return the worksheet-level field name for source hierarchy comparisons."""
    return FIELD_ALIASES.get(field, field)


def source_to_proof_level(source: str | None) -> str:
    """Map existing parser source strings to a proof-level bucket."""
    lowered = str(source or "").lower()
    if "lab" in lowered or "a1c threshold" in lowered or "calculated" in lowered:
        return "data_derived"
    if "explicit" in lowered or "structured" in lowered:
        return "explicit_structured"
    if "med" in lowered or "active" in lowered or "inferred" in lowered:
        return "active_medication"
    if "problem list" in lowered:
        return "problem_list"
    if lowered:
        return "narrative"
    return "unknown"


def existing_proof_rank(report: Any, field: str) -> int:
    """Return the current proof rank for a parsed field."""
    meta = getattr(report, "field_meta", {}) or {}
    field_meta = meta.get(field) or meta.get(canonical_field(field)) or {}
    proof_level = field_meta.get("proof_level") or source_to_proof_level(field_meta.get("source"))
    return PROOF_RANK.get(str(proof_level), 0)


def can_apply_signal(report: Any, signal: ProblemListSignal, *, override_false: bool = False) -> bool:
    """Return whether a problem-list signal can populate the current parse report."""
    extracted = getattr(report, "extracted", {}) or {}
    current = extracted.get(signal.field)
    if current is None:
        return True
    if current is True and signal.value is True:
        return False
    if current is False and signal.value is True and not override_false:
        return False
    return existing_proof_rank(report, signal.field) <= PROOF_RANK[signal.proof_level]


def apply_signal_metadata(report: Any, signal: ProblemListSignal) -> None:
    """Attach consistent source, proof, confidence, and review metadata to a report field."""
    report.field_meta[signal.field] = {
        "confidence": "uncertain" if signal.review_required else "parsed",
        "source": signal.reason if signal.review_required else "problem list diagnosis",
        "source_text": signal.source_text,
        "review_required": "true" if signal.review_required else "false",
        "proof_level": signal.proof_level,
    }
