from __future__ import annotations

import re
from dataclasses import dataclass


SECTION_RULES: tuple[tuple[str, str], ...] = (
    ("demographics", r"\b(?:demographics|patient information|race/ethnicity)\b"),
    ("smoking", r"\b(?:smoking status|tobacco)\b"),
    ("vitals", r"\b(?:vitals|bp readings|blood pressure readings)\b"),
    ("bmi", r"\b(?:bmi|body mass index)\b"),
    ("family_history", r"\b(?:family history|premature ascvd)\b"),
    ("labs", r"\b(?:labs|results|chemistry)\b"),
    ("a1c", r"\b(?:a1c|hba1c|hemoglobin a1c)\b"),
    ("lipids", r"\b(?:lipids|cholesterol|ldl|hdl|triglycerides|apob|lp\(a\))\b"),
    ("kidney", r"\b(?:egfr|labglom|uacr|urine acr|albumin|creatinine)\b"),
    ("imaging", r"\b(?:cac|calcium|ct|imaging|mammogram)\b"),
    ("medications", r"\b(?:medications|current meds|outpatient medications|rx)\b"),
    ("diagnoses", r"\b(?:problem list|diagnoses|past medical history)\b"),
)


@dataclass(frozen=True)
class TextSection:
    """A detected EMR section with its original lines."""

    name: str
    text: str


def detect_sections(text: str) -> dict[str, TextSection]:
    """Detect broad EMR territories using headers and line-level fallbacks."""
    buckets: dict[str, list[str]] = {"all": [text]}
    current = "all"
    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        for name, pattern in SECTION_RULES:
            if re.search(pattern, stripped, re.IGNORECASE):
                current = name
                buckets.setdefault(name, []).append(stripped)
                break
        else:
            buckets.setdefault(current, []).append(stripped)
    return {name: TextSection(name, "\n".join(lines)) for name, lines in buckets.items()}
