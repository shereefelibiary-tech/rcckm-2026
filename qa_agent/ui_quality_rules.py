from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


FILLER_PHRASES = (
    "consider optimizing risk factors",
    "risk-factor control",
    "may benefit from lifestyle",
    "as clinically appropriate",
    "follow up with your doctor",
    "ai-generated",
    "consult guidelines",
    "based on the information provided",
)

DUPLICATED_SECTION_HEADERS = (
    "Assessment",
    "Recommendations",
    "Objective",
    "Patient roadmap",
)

VISIBLE_ERROR_PATTERNS = (
    "streamlit exception",
    "traceback",
    "uncaught exception",
    "keyerror:",
    "typeerror:",
    "valueerror:",
)

RAW_OBJECT_PATTERNS = (
    r"<[A-Za-z_][\w.]* object at 0x[0-9a-fA-F]+>",
    r"\bNone\b",
    r"\bnan\b",
    r"\bundefined\b",
    r"\[object Object\]",
)

CONSUMER_OR_FLUFF_PATTERNS = (
    "phenotype",
    "journey",
    "empower",
    "wellness",
    "optimize your health",
)


@dataclass(frozen=True)
class RuleHit:
    category: str
    severity: str
    finding: str
    evidence_excerpt: str
    suggested_fix_direction: str
    codex_ready: bool


def normalize_text(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def excerpt(text: str, needle: str, *, radius: int = 90) -> str:
    lower = text.lower()
    index = lower.find(needle.lower())
    if index < 0:
        return needle
    start = max(0, index - radius)
    end = min(len(text), index + len(needle) + radius)
    return normalize_text(text[start:end])


def find_filler_language(text: str) -> list[RuleHit]:
    hits = []
    for phrase in FILLER_PHRASES:
        if phrase in text.lower():
            hits.append(
                RuleHit(
                    category="wording",
                    severity="medium",
                    finding=f"Filler phrase visible: {phrase}",
                    evidence_excerpt=excerpt(text, phrase),
                    suggested_fix_direction="Replace filler with a specific domain action or remove the sentence.",
                    codex_ready=True,
                )
            )
    return hits


def find_duplicate_sections(text: str) -> list[RuleHit]:
    hits = []
    for header in DUPLICATED_SECTION_HEADERS:
        pattern = re.compile(rf"(^|\n)\s*{re.escape(header)}\s*:?\s*($|\n)", re.IGNORECASE)
        count = len(pattern.findall(text))
        if count > 1:
            hits.append(
                RuleHit(
                    category="duplication",
                    severity="medium",
                    finding=f"Repeated section header: {header}",
                    evidence_excerpt=f"{header} appears {count} times.",
                    suggested_fix_direction="Render the section once or separate similarly named UI regions more explicitly.",
                    codex_ready=True,
                )
            )
    prevent_count = len(re.findall(r"\bPREVENT\b", text, flags=re.IGNORECASE))
    if prevent_count > 4:
        hits.append(
            RuleHit(
                category="duplication",
                severity="low",
                finding="PREVENT appears repeatedly.",
                evidence_excerpt=f"PREVENT appears {prevent_count} times.",
                suggested_fix_direction="Keep PREVENT in fixed summary/report locations and avoid duplicate explanatory blocks.",
                codex_ready=True,
            )
        )
    return hits


def find_contradictions(payload: dict[str, Any], text: str) -> list[RuleHit]:
    parsed = payload.get("parsed_patient_json") or {}
    lower = text.lower()
    hits = []
    cac = parsed.get("cac")
    clinical_ascvd = bool(parsed.get("clinical_ascvd"))
    diabetes = bool(parsed.get("diabetes"))
    a1c = parsed.get("a1c")
    aspirin_not_indicated = "aspirin: not indicated" in lower or "aspirin not indicated" in lower

    if cac == 0 and any(phrase in lower for phrase in ("plaque present", "coronary plaque: present", "high burden", "very high burden")):
        hits.append(
            RuleHit(
                category="contradiction",
                severity="high",
                finding="CAC 0 appears with plaque-positive wording.",
                evidence_excerpt="CAC 0 plus plaque-positive language detected.",
                suggested_fix_direction="Use not detected wording when CAC is 0.",
                codex_ready=True,
            )
        )
    if not clinical_ascvd and any(
        phrase in lower
        for phrase in (
            "secondary-prevention",
            "secondary prevention",
            "secondary-prevention antiplatelet",
            "secondary-prevention lipid",
        )
    ):
        hits.append(
            RuleHit(
                category="contradiction",
                severity="high",
                finding="No confirmed ASCVD appears with secondary-prevention language.",
                evidence_excerpt="clinical_ascvd=false with secondary-prevention/clinical ASCVD wording.",
                suggested_fix_direction="Gate secondary-prevention wording to confirmed clinical ASCVD.",
                codex_ready=True,
            )
        )
    if aspirin_not_indicated and re.search(r"\b(start|initiate|begin)\s+aspirin\b", lower):
        hits.append(
            RuleHit(
                category="contradiction",
                severity="high",
                finding="Aspirin not indicated coexists with start aspirin language.",
                evidence_excerpt="Aspirin not indicated and start aspirin language both detected.",
                suggested_fix_direction="Render one aspirin action from the ActionDomainReadout source of truth.",
                codex_ready=True,
            )
        )
    if (diabetes or (isinstance(a1c, (int, float)) and a1c >= 6.5)) and "prediabetes" in lower and "diabetes" in lower:
        hits.append(
            RuleHit(
                category="contradiction",
                severity="medium",
                finding="Diabetes-range data appears with prediabetes language.",
                evidence_excerpt="Diabetes and prediabetes both appear in visible text.",
                suggested_fix_direction="Suppress dominant prediabetes language when diabetes criteria are met unless explicitly contextualized.",
                codex_ready=True,
            )
        )
    return hits


def find_report_structure(final_report_text: str, payload: dict[str, Any]) -> list[RuleHit]:
    hits = []
    lower = final_report_text.lower()
    assessment_idx = lower.find("assessment")
    recommendations_idx = lower.find("recommendations")
    objective_idx = lower.find("objective")

    if not final_report_text.strip():
        return [
            RuleHit(
                category="report",
                severity="high",
                finding="Final report text is empty.",
                evidence_excerpt="final_report_text is empty.",
                suggested_fix_direction="Ensure the full interpretation step ran before exporting QA.",
                codex_ready=False,
            )
        ]
    if recommendations_idx < 0:
        hits.append(
            RuleHit(
                category="structure",
                severity="high",
                finding="Recommendations header not found.",
                evidence_excerpt=final_report_text[:200],
                suggested_fix_direction="Render a stable Recommendations section in final_report_text.",
                codex_ready=True,
            )
        )
    if assessment_idx >= 0 and recommendations_idx >= 0 and assessment_idx > recommendations_idx:
        hits.append(
            RuleHit(
                category="structure",
                severity="high",
                finding="Assessment appears after Recommendations.",
                evidence_excerpt="Assessment index is after Recommendations index.",
                suggested_fix_direction="Keep report order: Objective, Assessment, Recommendations.",
                codex_ready=True,
            )
        )
    if objective_idx >= 0 and assessment_idx >= 0 and objective_idx > assessment_idx:
        hits.append(
            RuleHit(
                category="structure",
                severity="medium",
                finding="Objective appears after Assessment.",
                evidence_excerpt="Objective index is after Assessment index.",
                suggested_fix_direction="Move Objective before Assessment when Objective is rendered.",
                codex_ready=True,
            )
        )
    if re.search(r"(^|\n)\s*plan\s*:?\s*($|\n)", final_report_text, flags=re.IGNORECASE):
        hits.append(
            RuleHit(
                category="structure",
                severity="medium",
                finding="Old Plan header appears.",
                evidence_excerpt=excerpt(final_report_text, "Plan"),
                suggested_fix_direction="Use the fixed Recommendations header unless Plan is intentionally retained.",
                codex_ready=True,
            )
        )
    if "prevent" in lower and "ascvd" not in lower:
        hits.append(
            RuleHit(
                category="structure",
                severity="low",
                finding="PREVENT appears without clear ASCVD labeling.",
                evidence_excerpt=excerpt(final_report_text, "PREVENT"),
                suggested_fix_direction="Label PREVENT with ASCVD time horizon and percent when available.",
                codex_ready=True,
            )
        )
    if payload.get("ckm_stage") and "ckm" not in lower:
        hits.append(
            RuleHit(
                category="structure",
                severity="medium",
                finding="CKM stage missing from final report.",
                evidence_excerpt=final_report_text[:200],
                suggested_fix_direction="Include CKM stage in the fixed report summary.",
                codex_ready=True,
            )
        )
    parsed = payload.get("parsed_patient_json") or {}
    kidney_signal = (parsed.get("egfr") is not None and parsed.get("egfr") < 60) or (
        parsed.get("uacr") is not None and parsed.get("uacr") >= 30
    )
    if kidney_signal and not re.search(r"\bG\d(?:a|b)?A\d\b", final_report_text):
        hits.append(
            RuleHit(
                category="structure",
                severity="medium",
                finding="KDIGO G/A category missing despite kidney signal.",
                evidence_excerpt=final_report_text[:240],
                suggested_fix_direction="Render KDIGO G/A category when eGFR or UACR indicates kidney risk.",
                codex_ready=True,
            )
        )
    return hits


def find_language_quality(text: str) -> list[RuleHit]:
    hits = []
    lower = text.lower()
    for phrase in CONSUMER_OR_FLUFF_PATTERNS:
        if phrase in lower:
            hits.append(
                RuleHit(
                    category="wording",
                    severity="low" if phrase != "phenotype" else "medium",
                    finding=f"Non-preferred language visible: {phrase}",
                    evidence_excerpt=excerpt(text, phrase),
                    suggested_fix_direction="Use concise clinical wording and avoid vague consumer-app or unsupported terms.",
                    codex_ready=True,
                )
            )
    if len(re.findall(r"\bmay\b", lower)) > 5:
        hits.append(
            RuleHit(
                category="wording",
                severity="low",
                finding="Frequent hedging language.",
                evidence_excerpt="The word 'may' appears more than 5 times.",
                suggested_fix_direction="Keep only decision-relevant uncertainty and remove generic hedging.",
                codex_ready=True,
            )
        )
    return hits


def find_visual_smoke_issues(*, page_text: str, final_report_text: str, screenshot_exists: bool | None) -> list[RuleHit]:
    hits = []
    if not page_text.strip():
        hits.append(
            RuleHit(
                category="visual",
                severity="high",
                finding="Page text artifact is empty.",
                evidence_excerpt="page_text is empty.",
                suggested_fix_direction="Capture page text after full interpretation.",
                codex_ready=False,
            )
        )
    if not final_report_text.strip():
        hits.append(
            RuleHit(
                category="visual",
                severity="high",
                finding="Report text artifact is empty.",
                evidence_excerpt="final_report_text is empty.",
                suggested_fix_direction="Wait for final report before reading QA export.",
                codex_ready=False,
            )
        )
    if screenshot_exists is False:
        hits.append(
            RuleHit(
                category="visual",
                severity="low",
                finding="Screenshot artifact not available.",
                evidence_excerpt="No screenshot path or file was available.",
                suggested_fix_direction="Save screenshots for failed QA cases or when running visual review explicitly.",
                codex_ready=False,
            )
        )
    combined = f"{page_text}\n{final_report_text}"
    lower = combined.lower()
    for pattern in VISIBLE_ERROR_PATTERNS:
        if pattern in lower:
            hits.append(
                RuleHit(
                    category="visual",
                    severity="high",
                    finding=f"Visible error text: {pattern}",
                    evidence_excerpt=excerpt(combined, pattern),
                    suggested_fix_direction="Fix the visible exception before evaluating clinical output.",
                    codex_ready=True,
                )
            )
    for pattern in RAW_OBJECT_PATTERNS:
        match = re.search(pattern, combined, flags=re.IGNORECASE)
        if match:
            hits.append(
                RuleHit(
                    category="visual",
                    severity="medium",
                    finding=f"Raw value/object text visible: {match.group(0)}",
                    evidence_excerpt=excerpt(combined, match.group(0)),
                    suggested_fix_direction="Render a user-facing fallback instead of raw Python/JS values.",
                    codex_ready=True,
                )
            )
    if "rcckm qa export" not in page_text.lower() and re.search(
        r"\{\s*\"(?:raw_input_text|parsed_patient_json|engine_output_json)\"",
        page_text,
    ):
        hits.append(
            RuleHit(
                category="visual",
                severity="low",
                finding="QA JSON appears in visible page text.",
                evidence_excerpt="QA export JSON is present in the page text artifact.",
                suggested_fix_direction="Acceptable in qa_mode; ensure this does not appear when qa_mode is absent.",
                codex_ready=False,
            )
        )
    return hits
