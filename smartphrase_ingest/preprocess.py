from __future__ import annotations

import hashlib
import re


PLACEHOLDER_RE = re.compile(
    r"^\s*(?:\*{2,}|@[A-Z0-9_]+@|no\s+results\s+found(?:\s+for:?.*)?)\s*$",
    re.IGNORECASE,
)


def raw_text_hash(raw_text: str) -> str:
    """Return a stable hash for traceability without storing PHI-heavy text."""
    return hashlib.sha256((raw_text or "").encode("utf-8")).hexdigest()


def normalize_text(raw_text: str) -> str:
    """Normalize spacing and common EMR table artifacts while preserving evidence lines."""
    text = (raw_text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def is_placeholder_value(value: str | None) -> bool:
    """Return whether a field value is an Epic placeholder or no-result sentinel."""
    if value is None:
        return True
    return bool(PLACEHOLDER_RE.match(str(value).strip()))
