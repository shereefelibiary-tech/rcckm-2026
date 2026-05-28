from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re


PARSER_VERSION = "0.1.0-beta"


@dataclass(frozen=True)
class ParserProfile:
    """User/EMR parsing hints that do not mutate base extraction rules."""

    profile_id: str
    source_system: str = "unknown"
    organization_name: str | None = None
    user_defined_aliases: dict[str, str] = field(default_factory=dict)
    section_aliases: dict[str, str] = field(default_factory=dict)
    field_aliases: dict[str, str] = field(default_factory=dict)
    known_patterns: dict[str, str] = field(default_factory=dict)
    preferred_lab_labels: dict[str, list[str]] = field(default_factory=dict)
    custom_medication_headers: list[str] = field(default_factory=list)
    parser_version: str = PARSER_VERSION
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


CANONICAL_LABELS = {
    "age": "Age",
    "sex": "Sex",
    "sbp": "SBP",
    "dbp": "DBP",
    "bp": "BP",
    "ldl_c": "LDL-C",
    "hdl_c": "HDL-C",
    "triglycerides": "TG",
    "tc": "TC",
    "a1c": "A1c",
    "egfr": "eGFR",
    "bmi": "BMI",
    "apob": "ApoB",
    "lp_a_value": "Lp(a)",
    "uacr": "UACR",
    "cac": "CAC",
    "family_history_premature_ascvd": "Premature ASCVD in first-degree relative",
    "medications_raw": "Current medications",
}


def _canonical_label(field_name: str) -> str:
    return CANONICAL_LABELS.get(field_name, field_name)


def _alias_patterns(profile: ParserProfile) -> dict[str, str]:
    patterns: dict[str, str] = {}
    patterns.update(profile.field_aliases or {})
    for field, aliases in (profile.preferred_lab_labels or {}).items():
        for alias in aliases:
            patterns[alias] = field
    for alias, field in (profile.user_defined_aliases or {}).items():
        patterns[alias] = field
    return patterns


def apply_profile_hints(raw_text: str, profile: ParserProfile | None = None) -> str:
    """Append deterministic alias-derived lines while preserving original text."""
    if profile is None:
        return raw_text or ""

    text = raw_text or ""
    additions: list[str] = []

    for alias, canonical_section in (profile.section_aliases or {}).items():
        pattern = rf"^\s*{re.escape(alias)}\s*:?\s*$"
        replacement = f"{canonical_section}:"
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE | re.MULTILINE)

    for header in profile.custom_medication_headers or []:
        pattern = rf"^\s*{re.escape(header)}\s*:?\s*$"
        text = re.sub(pattern, "Current medications:", text, flags=re.IGNORECASE | re.MULTILINE)

    for alias, field_name in _alias_patterns(profile).items():
        canonical_label = _canonical_label(field_name)
        line_pattern = re.compile(
            rf"^\s*{re.escape(alias)}\s*(?:=|:)?\s*(?P<value>[^\n]+?)\s*$",
            re.IGNORECASE | re.MULTILINE,
        )
        for match in line_pattern.finditer(text):
            value = match.group("value").strip()
            if not value:
                continue
            additions.append(f"{canonical_label}: {value}")

    if not additions:
        return text

    return text.rstrip() + "\n\nParser profile normalized aliases:\n" + "\n".join(dict.fromkeys(additions))
