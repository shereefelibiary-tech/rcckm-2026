from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import re
from typing import Any

from smartphrase_ingest.aliases import (
    A1C_ALIASES,
    ANCESTRY_ALIASES,
    CAC_ALIASES,
    HSCRP_ALIASES,
    INFLAMMATORY_DISEASE_ALIASES,
    MASLD_ALIASES,
    OSA_ALIASES,
    UACR_ALIASES,
)
from smartphrase_ingest.med_vocab import extract_medications_structured
from smartphrase_ingest.problem_list_parser import ProblemListSignal, extract_problem_list_signals
from smartphrase_ingest.source_resolver import apply_signal_metadata, can_apply_signal
from modules.kdigo.engine import classify_albuminuria_stage, classify_egfr_stage


@dataclass
class ParseReport:
    """Structured parser output containing extracted fields and review metadata."""
    extracted: dict[str, Any] = field(default_factory=dict)
    field_meta: dict[str, dict[str, str]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    source_style: str = "unknown"

    @property
    def parsed(self) -> dict[str, Any]:
        return self.extracted

    @property
    def meta(self) -> dict[str, dict[str, str]]:
        return self.field_meta

    def as_dict(self) -> dict[str, Any]:
        return {
            "extracted": self.extracted,
            "parsed": self.extracted,
            "field_meta": self.field_meta,
            "meta": self.field_meta,
            "warnings": self.warnings,
            "conflicts": self.conflicts,
            "source_style": self.source_style,
        }


NUMERIC_PATTERNS = {
    "sbp": r"\b(?:sbp|systolic)\b",
    "dbp": r"\b(?:dbp|diastolic)\b",
    "tc": r"\b(?:tc|total cholesterol|cholesterol,\s*total|total-c|total chol)\b",
    "ldl": r"\b(?:ldl-c|ldl[-\s]?chol(?:esterol)?|ldl(?:\s*chol(?:esterol)?)?)\b",
    "hdl": r"\b(?:hdl-c|hdl[-\s]?chol(?:esterol)?|hdl(?:\s*chol(?:esterol)?)?)\b",
    "tg": r"\b(?:tg|triglycerides|trigs)\b",
    "apob": r"\b(?:apob|apo\s*b|apolipoprotein\s*b)\b",
    "a1c": r"\b(?:a1c|hba1c|hgba1c|hemoglobin\s+a1c)\b",
    "egfr": r"\b(?:egfr|e-gfr)\b",
    "uacr": r"\b(?:uacr|acr|urine\s+acr|urine albumin creatinine ratio|albumin/creatinine ratio|albumin creatinine ratio|microalbumin/creatinine ratio|albcreat)\b",
    "cac": r"\b(?:cac|coronary artery calcium|coronary calcium|coronary calcium score|ct calcium score|calcium score)\b",
    "bmi": r"\b(?:bmi|body mass index)\b",
    "creatinine": r"\b(?:creatinine|cr)\b",
    "hscrp": r"\b(?:hscrp|hs-crp|high sensitivity crp|high-sensitivity crp|c-reactive protein,\s*high sensitivity|crp high sensitivity|crphs)\b",
}

MEDICATION_TERMS = (
    "atorvastatin",
    "rosuvastatin",
    "simvastatin",
    "pravastatin",
    "ezetimibe",
    "repatha",
    "praluent",
    "pcsk9",
    "metformin",
    "empagliflozin",
    "jardiance",
    "dapagliflozin",
    "farxiga",
    "semaglutide",
    "ozempic",
    "wegovy",
    "tirzepatide",
    "mounjaro",
    "lisinopril",
    "losartan",
    "valsartan",
    "amlodipine",
    "hydrochlorothiazide",
)


SOURCE_PATTERNS = {
    "epic": [r"\bepic\b", r"\bsmartphrase\b", r"\bmychart\b"],
    "cerner": [r"\bcerner\b", r"\bpowerchart\b", r"\bpower chart\b"],
    "meditech": [r"\bmeditech\b", r"\bexpanse\b"],
    "athena": [r"\bathenahealth\b", r"\bathena\b"],
    "eclinicalworks": [r"\beclinicalworks\b", r"\becw\b"],
    "nextgen": [r"\bnextgen\b"],
    "allscripts": [r"\ballscripts\b", r"\bveradigm\b"],
    "va_cprs": [r"\bva cprs\b", r"\bcprs\b", r"\bvista\b"],
    "labcorp": [r"\blabcorp\b"],
    "quest": [r"\bquest diagnostics\b", r"\bquest\b"],
    "generic": [r"\bportal\b", r"\bpatient portal\b", r"\blab copy\b"],
}


def detect_source_style(raw_text: str) -> str:
    """Classify pasted text into a known EMR/lab style when recognizable."""
    text = raw_text or ""
    for source, patterns in SOURCE_PATTERNS.items():
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
            return source
    return "unknown"


def _record(report: ParseReport, field: str, value: Any, confidence: str = "parsed", source: str = "") -> None:
    if field in report.extracted and report.extracted[field] != value:
        report.conflicts.append(
            f"{field}: {report.extracted[field]} vs {value} ({source or 'additional source'})"
        )
    report.extracted[field] = value
    report.field_meta[field] = {"confidence": confidence, "source": source}


def _record_source_meta(
    report: ParseReport,
    field: str,
    value: Any,
    confidence: str,
    source: str,
    *,
    source_text: str = "",
    review_required: bool = False,
) -> None:
    _record(report, field, value, confidence, source)
    if source_text:
        report.field_meta[field]["source_text"] = source_text
    if review_required:
        report.field_meta[field]["review_required"] = "true"


def _record_age(report: ParseReport, value: Any, confidence: str, source: str) -> None:
    """Record age only when it is a plausible single age value."""
    try:
        age = float(value)
    except (TypeError, ValueError):
        return
    if 0 <= age <= 120:
        _record(report, "age", age, confidence, source)
        return
    report.field_meta["age"] = {
        "confidence": "uncertain",
        "source": "Age parsed value invalid; review needed.",
    }
    if "Age parsed value invalid; review needed." not in report.warnings:
        report.warnings.append("Age parsed value invalid; review needed.")
    report.conflicts.append("age: Age parsed value invalid; review needed.")


def extract_demographics_age(text: str) -> tuple[float | None, str, str]:
    """Extract patient age with demographic labels outranking family-history ages."""
    candidates: list[tuple[int, float, str, str]] = []
    lines = (text or "").splitlines()
    excluded_context = re.compile(
        r"\b(?:age\s+at\s+event|father|mother|sibling|brother|sister|relative|family\s+history)\b",
        re.IGNORECASE,
    )

    for index, line in enumerate(lines):
        clean = line.strip()
        if not clean or excluded_context.search(clean):
            continue
        section_bonus = 20 if any(
            re.search(r"\bdemographics\b", prior, re.IGNORECASE)
            for prior in lines[max(0, index - 4): index + 1]
        ) else 0
        explicit = re.match(r"^\s*age\s*:?\s*(\d{1,3})\s*(?:y\.?o\.?|years?|yrs?|yr)?\b", clean, re.IGNORECASE)
        if explicit:
            candidates.append((100 + section_bonus, float(explicit.group(1)), "parsed", "explicit demographic age"))
            continue
        narrative = re.search(r"\b(\d{1,3})\s*(?:-?\s*year-old|y\.?o\.?|y/o)\b", clean, re.IGNORECASE)
        if narrative:
            candidates.append((80 + section_bonus, float(narrative.group(1)), "parsed", "age/sex prose"))
            continue
        compact = re.search(r"\b(\d{1,3})\s*[/\s-]*([mf])\b", clean, re.IGNORECASE)
        if compact:
            candidates.append((60 + section_bonus, float(compact.group(1)), "inferred", "compact age/sex token"))

    plausible = [candidate for candidate in candidates if 0 <= candidate[1] <= 120]
    if not plausible:
        return None, "", ""
    plausible.sort(key=lambda item: item[0], reverse=True)
    _priority, value, confidence, source = plausible[0]
    return value, confidence, source


def _mark_unavailable(report: ParseReport, field: str, reason: str, source: str) -> None:
    report.field_meta[field] = {"confidence": "not found", "source": reason or source}
    if reason:
        report.warnings.append(f"{field}: {reason}")


def _parse_number_after_label(text: str, label_pattern: str) -> float | None:
    pattern = rf"{label_pattern}(?:\s*(?:\([^)]*\))|\s+chol(?:esterol)?|\s+calc|\s+calculated|\s+ratio|\s+score|\s+value)?\s*(?:=|:|is|of|-|\|)?\s*([<>]?\s*\d+(?:\.\d+)?)"
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    window = text[max(0, match.start() - 40): min(len(text), match.end() + 40)].lower()
    if any(term in window for term in ("reference", "threshold", "normal range", "diagnostic")):
        return None
    label_value_window = text[match.start():match.start(1)]
    if ":" in label_value_window and PLACEHOLDER_VALUE_RE.search(label_value_window.split(":", 1)[-1]):
        return None
    try:
        return float(match.group(1).replace(" ", "").lstrip("<>"))
    except ValueError:
        return None


def _near_negation(text: str, term_start: int) -> bool:
    window = text[max(0, term_start - 45):term_start].lower()
    return bool(
        re.search(
            r"\b(no|not on|denies|without|stopped|discontinued|dc'd|d/c|held|allergy to)\b",
            window,
        )
    )


def _bool_from_text(text: str, positive_patterns: list[str], negative_patterns: list[str] | None = None) -> bool | None:
    for pattern in negative_patterns or []:
        if re.search(pattern, text, re.IGNORECASE):
            return False
    for pattern in positive_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return None


def _bool_segments(raw: str) -> list[str]:
    segments: list[str] = []
    for line in (raw or "").splitlines():
        for segment in re.split(r"[.;]", line):
            segment = segment.strip()
            if segment:
                segments.append(segment)
    return segments


def _label_regex(labels: list[str]) -> str:
    parts = []
    for label in labels:
        label = label.strip()
        if not label:
            continue
        if re.search(r"[\\()[\]|?+*{}^$]", label):
            parts.append(label)
        else:
            parts.append(re.escape(label))
    return r"(?:" + "|".join(parts) + r")"


UNKNOWN_VALUE_RE = (
    r"(?:unknown|not\s+documented|unavailable|not\s+available|not\s+found|"
    r"no\s+results\s+found|not\s+assessed|unclear|unable\s+to\s+determine|"
    r"not\s+reported|missing|\*{2,}|@[A-Z0-9_]+@)"
)

PLACEHOLDER_VALUE_RE = re.compile(
    r"^\s*(?:\*{2,}|@[A-Z0-9_]+@|no\s+results\s+found(?:\s+for:?.*)?)\s*$",
    re.IGNORECASE,
)


def _parse_explicit_bool_line_status(raw: str, labels: list[str]) -> tuple[bool, bool | None]:
    """Parse explicit boolean condition lines.

    Returns (found_labeled_line, value). Unknown/not documented returns (True, None);
    absent labels return (False, None).
    """
    if not raw or not labels:
        return False, None

    label = _label_regex(labels)
    negative_value = r"(?:no|n|false|absent|negative|none|never|denies|denied|not present)"
    positive_value = r"(?:yes|y|true|present|positive|active|current)"
    negative_prefix = r"(?:no|denies|denied|without|negative for|absent|no history of|not present)"
    positive_prefix = r"(?:has|with|known|history of|hx of|diagnosed with|positive for|present)"

    for segment in _bool_segments(raw):
        if not re.search(rf"\b{label}\b", segment, re.IGNORECASE):
            continue
        found = True

        negative_patterns = [
            rf"\b{label}\b\s*(?:=|:|-|is|was)?\s*{negative_value}\b",
            rf"\b{negative_prefix}\b[^\n.;]*\b{label}\b",
            rf"\b{label}\b[^\n.;]*\b(?:negative|absent|denied|none|not present)\b",
        ]
        if any(re.search(pattern, segment, re.IGNORECASE) for pattern in negative_patterns):
            return True, False

        direct_positive_patterns = [
            rf"\b{label}\b\s*(?:=|:|-|is|was)?\s*{positive_value}\b",
        ]
        if any(re.search(pattern, segment, re.IGNORECASE) for pattern in direct_positive_patterns):
            return True, True

        unknown_patterns = [
            rf"\b{label}\b\s*(?:=|:|-|is|was)?\s*{UNKNOWN_VALUE_RE}\b",
            rf"\b{UNKNOWN_VALUE_RE}\b[^\n.;]*\b{label}\b",
            rf"\b{label}\b[^\n.;]*\b{UNKNOWN_VALUE_RE}\b",
        ]
        if any(re.search(pattern, segment, re.IGNORECASE) for pattern in unknown_patterns):
            return found, None

        prefix_positive_patterns = [
            rf"\b{positive_prefix}\b[^\n.;]*\b{label}\b",
        ]
        if any(re.search(pattern, segment, re.IGNORECASE) for pattern in prefix_positive_patterns):
            return True, True

    return False, None


def parse_explicit_bool_line(raw: str, labels: list[str]) -> bool | None:
    """Parse a labeled boolean field while preserving explicit no/unknown states."""
    """Parse explicit yes/no condition lines without treating label mentions as positive."""
    _found, value = _parse_explicit_bool_line_status(raw, labels)
    return value


def _keyword_present_without_explicit_negation(raw: str, labels: list[str]) -> bool | None:
    if not raw or not labels:
        return None

    label = _label_regex(labels)
    for segment in _bool_segments(raw):
        if not re.search(rf"\b{label}\b", segment, re.IGNORECASE):
            continue
        unknown_patterns = [
            rf"\b{label}\b\s*(?:=|:|-|is|was)?\s*{UNKNOWN_VALUE_RE}\b",
            rf"\b{UNKNOWN_VALUE_RE}\b[^\n.;]*\b{label}\b",
            rf"\b{label}\b[^\n.;]*\b{UNKNOWN_VALUE_RE}\b",
        ]
        if any(re.search(pattern, segment, re.IGNORECASE) for pattern in unknown_patterns):
            return None
        negative_patterns = [
            rf"\b{label}\b\s*(?:=|:|-|is|was)?\s*(?:no|false|absent|negative|none|never|denies|denied|not present)\b",
            rf"\b(?:no|denies|denied|without|negative for|absent|no history of|not present)\b[^\n.;]*\b{label}\b",
            rf"\b{label}\b[^\n.;]*\b(?:negative|absent|denied|none|not present)\b",
        ]
        if any(re.search(pattern, segment, re.IGNORECASE) for pattern in negative_patterns):
            return False
        return True
    return None


def parse_yes_no_context(raw: str, labels: list[str]) -> bool | None:
    """Parse split-line yes/no fields where the value may sit below the label."""
    if not raw or not labels:
        return None
    label = _label_regex(labels)
    lines = (raw or "").splitlines()
    negative = re.compile(r"^(?:no|n|false|absent|negative|none|denies|denied|not present)\b", re.IGNORECASE)
    positive = re.compile(r"^(?:yes|y|true|present|positive|active|current)\b", re.IGNORECASE)
    unknown = re.compile(UNKNOWN_VALUE_RE, re.IGNORECASE)

    for index, line in enumerate(lines):
        match = re.search(rf"\b{label}\b", line, re.IGNORECASE)
        if not match:
            continue
        prefix = line[: match.start()]
        if re.search(r"\b(?:no|denies|denied|without|negative for|absent|not present)\b", prefix, re.IGNORECASE):
            return False
        tail = re.sub(r"^\s*(?:=|:|-|is|was)\s*", "", line[match.end():].strip(), flags=re.IGNORECASE)
        candidates = [tail] if tail else []
        for lookahead in lines[index + 1: min(len(lines), index + 3)]:
            clean = lookahead.strip()
            if clean:
                candidates.append(clean)
        for candidate in candidates:
            if not candidate:
                continue
            if unknown.search(candidate):
                return None
            if negative.search(candidate):
                return False
            if positive.search(candidate):
                return True
    return None


ASCVD_CALCULATOR_REVIEW_RE = re.compile(
    r"\b(?:ascvd\s+risk\s+score\s+failed\s+to\s+calculate|risk\s+calculator[^\n.;]*ascvd|"
    r"history\s+suggesting\s+prior/existing\s+ascvd|prior/existing\s+ascvd)\b",
    re.IGNORECASE,
)


def _has_ascvd_calculator_review_text(raw: str) -> bool:
    """Detect calculator disclaimer text that requires review, not diagnosis."""
    return bool(ASCVD_CALCULATOR_REVIEW_RE.search(raw or ""))


def _strip_ascvd_calculator_review_text(raw: str) -> str:
    """Remove ASCVD calculator-disclaimer segments before clinical ASCVD parsing."""
    safe_segments = []
    for segment in _bool_segments(raw):
        if ASCVD_CALCULATOR_REVIEW_RE.search(segment):
            continue
        safe_segments.append(segment)
    return "\n".join(safe_segments)


PROBLEM_LIST_HEADER_RE = re.compile(
    r"\b(?:problem\s+list|diagnoses|diagnosis|past\s+medical\s+history|pmh|relevant\s+diagnoses/problem\s+list)\b",
    re.IGNORECASE,
)

SECTION_HEADER_RE = re.compile(
    r"^\s*(?:Demographics|Smoking|Vitals|BMI|Family history|Lipids|A1c|ApoB|Lp\(a\)|hsCRP|eGFR|UACR|Kidney|Imaging|Medications|Calcification|Plaque|Assessment|Plan|Notes)\s*:?\s*$",
    re.IGNORECASE,
)


def _problem_list_block(text: str) -> str:
    """Return the diagnosis/problem-list block without pulling in later sections."""
    lines = (text or "").splitlines()
    for index, line in enumerate(lines):
        if not PROBLEM_LIST_HEADER_RE.search(line):
            continue
        block = []
        for item in lines[index : min(len(lines), index + 40)]:
            clean = item.strip()
            if not clean:
                continue
            if block and SECTION_HEADER_RE.match(clean):
                break
            block.append(clean)
        return "\n".join(block)
    return ""


def _strip_problem_list_block(text: str) -> str:
    """Remove problem-list sections so review-only diagnoses do not become confirmed fields."""
    lines = (text or "").splitlines()
    output: list[str] = []
    skipping = False
    for line in lines:
        clean = line.strip()
        if not skipping and PROBLEM_LIST_HEADER_RE.search(clean):
            skipping = True
            continue
        if skipping and clean and SECTION_HEADER_RE.match(clean):
            skipping = False
        if not skipping:
            output.append(line)
    return "\n".join(output)


def _problem_list_evidence(block: str, patterns: tuple[str, ...]) -> str:
    for line in (block or "").splitlines():
        if any(re.search(pattern, line, re.IGNORECASE) for pattern in patterns):
            return line.strip(" -\t")
    return ""


def _record_problem_list_bool(
    report: ParseReport,
    field: str,
    evidence: str,
    *,
    override_false: bool = False,
) -> None:
    if not evidence:
        return
    current = report.extracted.get(field)
    if current is True:
        return
    if current is False and not override_false:
        report.conflicts.append(f"{field}: explicit false vs problem list diagnosis ({evidence})")
        return
    report.extracted[field] = True
    report.field_meta[field] = {
        "confidence": "parsed",
        "source": "problem list diagnosis",
        "source_text": evidence,
    }
    if field == "diabetes":
        report.extracted["diabetes_source"] = "problem_list"
        report.field_meta["diabetes_source"] = {
            "confidence": "parsed",
            "source": "problem list diagnosis",
            "source_text": evidence,
        }


def _problem_list_positive_evidence(
    block: str,
    patterns: tuple[str, ...],
    exclude_patterns: tuple[str, ...] = (),
) -> str:
    for line in (block or "").splitlines():
        if any(re.search(pattern, line, re.IGNORECASE) for pattern in exclude_patterns):
            continue
        if any(re.search(pattern, line, re.IGNORECASE) for pattern in patterns):
            return line.strip(" -\t")
    return ""


def _apply_problem_list_signal(report: ParseReport, signal: ProblemListSignal) -> None:
    if signal.field == "clinical_ascvd_review":
        _record_source_meta(
            report,
            "clinical_ascvd_review",
            True,
            "uncertain",
            signal.reason,
            source_text=signal.source_text,
            review_required=True,
        )
        if signal.reason not in report.warnings:
            report.warnings.append(signal.reason)
        if report.extracted.get("ascvd_clinical") is not True:
            report.extracted["ascvd_clinical"] = False
            report.field_meta["ascvd_clinical"] = {
                "confidence": "parsed",
                "source": "problem list ASCVD review-only text",
                "source_text": signal.source_text,
                "review_required": "true",
                "proof_level": "problem_list",
            }
        return

    if signal.field in {
        "sleep_apnea_review",
        "inflammatory_arthritis_review",
        "family_history_review",
        "family_history_premature_review",
        "cerebrovascular_review",
    }:
        report.extracted[signal.field] = True
        apply_signal_metadata(report, signal)
        if signal.reason not in report.warnings:
            report.warnings.append(signal.reason)
        if signal.field == "inflammatory_arthritis_review" and report.extracted.get("rheumatoid_arthritis") is not True:
            report.extracted["rheumatoid_arthritis"] = False
            report.field_meta["rheumatoid_arthritis"] = {
                "confidence": "uncertain",
                "source": "polyarthritis/RF is review-only for RA",
                "source_text": signal.source_text,
                "review_required": "true",
                "proof_level": "problem_list",
            }
        return

    if signal.field == "family_history_detail":
        detail = _find_family_history_event_detail(signal.source_text)
        if not detail:
            return
        _record(report, "fhx", detail["premature_fhx_ascvd"], "parsed", "problem list family history detail")
        _record(report, "family_history_relationship", detail["relationship"], "parsed", "problem list family history detail")
        _record(report, "family_history_event_type", detail["event_type"], "parsed", "problem list family history detail")
        _record(report, "family_history_age_at_event", int(detail["age_at_event"]), "parsed", "problem list family history detail")
        _record(report, "fhx_text", signal.source_text, "parsed", "problem list family history detail")
        for field in ("fhx", "family_history_relationship", "family_history_event_type", "family_history_age_at_event", "fhx_text"):
            report.field_meta.setdefault(field, {})
            report.field_meta[field].update({"source_text": signal.source_text, "proof_level": "problem_list"})
        return

    current_source = str((report.field_meta.get(signal.field) or {}).get("source") or "")
    override_false = signal.field == "diabetes" and current_source.startswith("A1c ")
    if not can_apply_signal(report, signal, override_false=override_false):
        current = report.extracted.get(signal.field)
        if current is False and signal.value is True:
            report.conflicts.append(f"{signal.field}: explicit false vs problem list diagnosis ({signal.source_text})")
        return
    report.extracted[signal.field] = signal.value
    apply_signal_metadata(report, signal)
    if signal.field == "diabetes":
        report.extracted["diabetes_source"] = "problem_list"
        report.field_meta["diabetes_source"] = {
            "confidence": "parsed",
            "source": "problem list diagnosis",
            "source_text": signal.source_text,
            "proof_level": "problem_list",
        }


def apply_problem_list_diagnoses(report: ParseReport, text: str) -> None:
    """Extract controlled problem-list signals without overriding higher-proof data."""
    block = _problem_list_block(text)
    if not block:
        return
    for signal in extract_problem_list_signals(block):
        _apply_problem_list_signal(report, signal)
    _review_problem_list_ckd_stage_conflict(report, block)


def _review_problem_list_ckd_stage_conflict(report: ParseReport, block: str) -> None:
    match = re.search(r"\bCKD\s+stage\s+(?P<stage>[2345][ab]?)\b", block or "", re.IGNORECASE)
    if not match:
        return
    egfr = report.extracted.get("egfr")
    uacr = report.extracted.get("uacr")
    egfr_stage = classify_egfr_stage(egfr) if egfr is not None else None
    uacr_stage = classify_albuminuria_stage(uacr) if uacr is not None else None
    if not egfr_stage:
        return
    problem_g = f"G{match.group('stage')}".replace("G3A", "G3a").replace("G3B", "G3b")
    if problem_g.lower() == str(egfr_stage).lower():
        return
    lab_stage = egfr_stage + (uacr_stage or "")
    warning = f"CKD stage conflict: labs show {lab_stage}."
    if warning not in report.warnings:
        report.warnings.append(warning)
    report.conflicts.append(f"ckd: problem list {problem_g} vs labs {lab_stage}")
    report.extracted["ckd_stage_review"] = True
    report.field_meta["ckd_stage_review"] = {
        "confidence": "uncertain",
        "source": warning,
        "source_text": match.group(0),
        "review_required": "true",
        "proof_level": "problem_list",
    }


def _without_gestational_diabetes_context(raw: str) -> str:
    """Remove reproductive-history diabetes segments before current-diabetes parsing."""
    segments = [
        segment
        for segment in _bool_segments(raw)
        if not re.search(r"\b(?:gestational\s+diabetes|gdm)\b", segment, re.IGNORECASE)
    ]
    return "\n".join(segments)


ASCVD_EVENT_LABELS = {
    "stemi": [r"stemi", r"st[-\s]+elevation\s+mi", r"st[-\s]+elevation\s+myocardial\s+infarction"],
    "nstemi": [r"nstemi", r"non[-\s]+st[-\s]+elevation\s+mi", r"non[-\s]+st[-\s]+elevation\s+myocardial\s+infarction"],
    "mi": [r"myocardial\s+infarction", r"\bmi\b", r"heart\s+attack", r"\bacs\b", r"acute\s+coronary\s+syndrome"],
    "pci": [r"\bpci\b", r"percutaneous\s+coronary\s+intervention"],
    "stent": [r"\bstent(?:s|ed)?\b", r"drug[-\s]+eluting\s+stent", r"\bdes\b"],
    "cabg": [r"\bcabg\b", r"coronary\s+artery\s+bypass"],
    "ischemic_stroke": [r"ischemic\s+stroke", r"ischaemic\s+stroke", r"\bstroke\b", r"\bcva\b"],
    "tia": [r"\btia\b", r"transient\s+ischemic\s+attack"],
    "pad": [r"\bpad\b", r"peripheral\s+artery\s+disease"],
}

ASCVD_EVENT_DISPLAY = {
    "stemi": "prior STEMI",
    "nstemi": "prior NSTEMI",
    "mi": "prior MI",
    "pci_stent": "PCI/stent",
    "pci": "PCI",
    "stent": "coronary stent",
    "cabg": "CABG",
    "ischemic_stroke": "ischemic stroke",
    "tia": "TIA",
    "pad": "PAD",
}


def _segment_has_event_term(segment: str, labels: list[str]) -> bool:
    return any(re.search(rf"\b{label}\b", segment, re.IGNORECASE) for label in labels)


def _segment_negates_event(segment: str, labels: list[str]) -> bool:
    label = _label_regex(labels)
    return bool(
        re.search(rf"\b(?:no|denies|denied|without|negative for|absent|no history of)\b[^\n.;]*\b{label}\b", segment, re.IGNORECASE)
        or re.search(rf"\b{label}\b[^\n.;]*\b(?:no|false|absent|negative|none|denies|denied|not present)\b", segment, re.IGNORECASE)
    )


def _segment_affirms_event(segment: str, labels: list[str]) -> bool:
    label = _label_regex(labels)
    return bool(
        re.search(rf"\b(?:history of|hx of|prior|previous|s/p|status post|with|known|personal history of)\b[^\n.;]*\b{label}\b", segment, re.IGNORECASE)
        or re.search(rf"\b{label}\b[^\n.;]*\b(?:history|prior|s/p|status post|treated with|in \d{{4}})\b", segment, re.IGNORECASE)
    )


def extract_ascvd_events(raw: str) -> dict:
    """Extract clinical ASCVD event flags and a concise event summary from text."""
    events = {key: None for key in ASCVD_EVENT_LABELS}
    events["acs"] = None
    for segment in _bool_segments(raw):
        if re.search(r"\b(?:family history|fhx|father|mother|brother|sister)\b", segment, re.IGNORECASE):
            continue
        for event, labels in ASCVD_EVENT_LABELS.items():
            if not _segment_has_event_term(segment, labels):
                continue
            if _segment_negates_event(segment, labels):
                events[event] = False
            elif _segment_affirms_event(segment, labels) or re.search(
                r"\b(?:stemi|nstemi|pci|stent|cabg|ischemic\s+stroke|ischaemic\s+stroke)\b",
                segment,
                re.IGNORECASE,
            ):
                events[event] = True
        if re.search(r"\b(?:acs|acute\s+coronary\s+syndrome)\b", segment, re.IGNORECASE):
            events["acs"] = False if _segment_negates_event(segment, [r"acs", r"acute\s+coronary\s+syndrome"]) else True
            if events["acs"] is True and events["mi"] is None:
                events["mi"] = True

    clinical_explicit = parse_explicit_bool_line(
        raw,
        [r"clinical\s+ascvd", r"personal\s+ascvd", r"known\s+ascvd", r"ascvd"],
    )
    positives = {key for key, value in events.items() if value is True}
    clinical_ascvd = clinical_explicit
    if positives:
        clinical_ascvd = True
    elif clinical_explicit is None and any(value is False for value in events.values()):
        clinical_ascvd = False

    parts: list[str] = []
    if events.get("stemi") is True:
        parts.append(ASCVD_EVENT_DISPLAY["stemi"])
    elif events.get("nstemi") is True:
        parts.append(ASCVD_EVENT_DISPLAY["nstemi"])
    elif events.get("mi") is True:
        parts.append(ASCVD_EVENT_DISPLAY["mi"])
    if events.get("pci") is True and events.get("stent") is True:
        parts.append(ASCVD_EVENT_DISPLAY["pci_stent"])
    else:
        if events.get("pci") is True:
            parts.append(ASCVD_EVENT_DISPLAY["pci"])
        if events.get("stent") is True:
            parts.append(ASCVD_EVENT_DISPLAY["stent"])
    for event in ("cabg", "ischemic_stroke", "tia", "pad"):
        if events.get(event) is True:
            parts.append(ASCVD_EVENT_DISPLAY[event])

    if len(parts) == 2:
        event_summary = f"{parts[0]} and {parts[1]}"
    elif len(parts) > 2:
        event_summary = ", ".join(parts[:-1]) + f", and {parts[-1]}"
    elif parts:
        event_summary = parts[0]
    else:
        event_summary = ""
    return {"clinical_ascvd": clinical_ascvd, "events": events, "event_summary": event_summary}


def _clinical_ascvd_explicit_bool(raw: str) -> bool | None:
    return extract_ascvd_events(raw)["clinical_ascvd"]


def _clinical_ascvd_context(raw: str) -> str:
    return extract_ascvd_events(raw)["event_summary"]


def _premature_family_history_from_event(relationship: str, age_at_event: float) -> bool:
    relationship_value = str(relationship or "").strip().lower()
    try:
        age_value = float(age_at_event)
    except (TypeError, ValueError):
        return False
    if relationship_value in {"father", "brother"}:
        return age_value < 55
    if relationship_value in {"mother", "sister"}:
        return age_value < 65
    return False


def _alias_pattern(aliases: tuple[str, ...]) -> str:
    return r"(?:" + "|".join(re.escape(alias).replace(r"\ ", r"\s+") for alias in aliases) + r")"


def normalize_family_history_relationship(value: str | None) -> str | None:
    """Normalize family-history relationship labels to worksheet canonical values."""
    token = str(value or "").strip().lower()
    if token in {"father", "dad", "paternal father"}:
        return "father"
    if token in {"mother", "mom", "maternal mother"}:
        return "mother"
    if token in {"brother", "sister", "sibling"}:
        return "sibling"
    if token in {"multiple", "multiple first-degree relatives", "multiple first degree relatives"}:
        return "multiple_first_degree"
    if token:
        return "other"
    return None


def _normalize_family_history_event(value: str | None) -> str | None:
    token = str(value or "").strip().lower()
    if not token or PLACEHOLDER_VALUE_RE.search(token):
        return None
    if token in {"mi", "myocardial infarction", "heart attack"}:
        return "mi"
    if token in {"pci", "cabg", "pci/cabg", "stent", "bypass"}:
        return "PCI/CABG"
    if token in {"stroke", "cva"}:
        return "stroke"
    if token in {"pad", "peripheral artery disease"}:
        return "PAD"
    if token in {"ascvd", "cvd"}:
        return "ascvd"
    return token


def _family_history_event_pattern() -> str:
    return r"(?:MI|myocardial\s+infarction|heart\s+attack|PCI/CABG|PCI|CABG|stroke|sudden\s+cardiac\s+death|SCD|ASCVD|PAD)"


def _find_family_history_event_detail(text: str) -> dict[str, Any] | None:
    """Extract relationship/event/age detail from compact family-history prose."""
    relation = r"(father|mother|brother|sister|sibling)"
    event = _family_history_event_pattern()
    patterns = (
        rf"\b{relation}\b\s+(?:with\s+)?(?P<event>{event})\s+(?:at\s+)?(?:age\s+)?(?P<age>\d{{1,3}})\b",
        rf"\b{relation}\b[^\n.;]{{0,35}}\b(?P<event>{event})\b[^\n.;]{{0,20}}\b(?:at|age)\s*(?P<age>\d{{1,3}})\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text or "", re.IGNORECASE)
        if not match:
            continue
        relationship = normalize_family_history_relationship(match.group(1))
        event_value = _normalize_family_history_event(match.group("event"))
        age_value = float(match.group("age"))
        if relationship and event_value and 0 <= age_value <= 120:
            return {
                "relationship": relationship,
                "event_type": event_value,
                "age_at_event": age_value,
                "premature_fhx_ascvd": _premature_family_history_from_event(relationship, age_value),
                "source_text": match.group(0),
            }
    sibling_premature = re.search(r"\b(?:sibling|brother|sister)\b[^\n.;]{0,40}\bpremature\s+ASCVD\b", text or "", re.IGNORECASE)
    if sibling_premature:
        return {
            "relationship": "sibling",
            "event_type": "ascvd",
            "age_at_event": None,
            "premature_fhx_ascvd": True,
            "source_text": sibling_premature.group(0),
        }
    return None


def _family_history_block(text: str) -> str:
    lines = (text or "").splitlines()
    for index, line in enumerate(lines):
        if re.search(r"\b(?:family history|premature\s+ascvd\s+in\s+first[-\s]?degree\s+relative)\b", line, re.IGNORECASE):
            block = []
            for item in lines[index : min(len(lines), index + 12)]:
                clean = item.strip()
                if not clean:
                    continue
                if block and re.match(
                    r"^(?:Demographics|Smoking|Vitals|BMI|Lipids|A1c|ApoB|Lp\(a\)|hsCRP|eGFR|UACR|Kidney|Imaging|Medications|Diagnoses|Problem List)\s*:?\s*$",
                    clean,
                    re.IGNORECASE,
                ):
                    break
                if block and re.search(
                    r"^[A-Z][A-Za-z /()_-]{2,40}:\s*$",
                    clean,
                ) and not re.search(r"\b(?:relationship|event|age|premature|family)\b", clean, re.IGNORECASE):
                    break
                block.append(clean)
            return "\n".join(block)
    return ""


def extract_family_history(section_lines: str) -> dict[str, Any]:
    """Bind premature family-history flag, relationship, event, and age from one block."""
    block = section_lines or ""
    if not block:
        return {}

    result: dict[str, Any] = {}
    explicit = re.search(
        r"\bpremature\s+ascvd\s+in\s+first[-\s]?degree\s+relative\s*(?:=|:|-)?\s*([^\n;]+)",
        block,
        re.IGNORECASE,
    )
    if explicit:
        token = explicit.group(1).strip()
        if PLACEHOLDER_VALUE_RE.search(token) or re.search(r"\b(?:unknown|not documented|not specified|blank)\b", token, re.IGNORECASE):
            result["premature_fhx_ascvd"] = None
            result["source"] = "placeholder family history"
            return result
        if re.search(r"\b(?:no|false|negative|denies|none)\b", token, re.IGNORECASE):
            result["premature_fhx_ascvd"] = False
        elif re.search(r"\b(?:yes|true|positive|present)\b", token, re.IGNORECASE):
            result["premature_fhx_ascvd"] = True

    relationship_match = re.search(r"\brelationship\s*(?:=|:|-)?\s*([A-Za-z -]+)", block, re.IGNORECASE)
    event_match = re.search(r"\bevent\s+type\s*(?:=|:|-)?\s*([A-Za-z /-]+)", block, re.IGNORECASE)
    age_match = re.search(r"\bage\s+at\s+event(?:\s*\([^)]*\))?\s*(?:=|:|-)?\s*(\d{1,3})", block, re.IGNORECASE)

    relationship = normalize_family_history_relationship(relationship_match.group(1) if relationship_match else None)
    event = _normalize_family_history_event(event_match.group(1) if event_match else None)
    age = float(age_match.group(1)) if age_match else None

    if relationship:
        result["relationship"] = relationship
    if event:
        result["event_type"] = event
    if age is not None:
        result["age_at_event"] = age
    if relationship and age is not None:
        result["premature_fhx_ascvd"] = _premature_family_history_from_event(relationship, age)
    elif relationship and result.get("premature_fhx_ascvd") is True:
        result["premature_fhx_ascvd"] = True

    if result:
        result.setdefault("source", "structured family history section")
    return result


def resolve_inflammatory_context(report: ParseReport, text: str) -> None:
    """Apply specificity rules so named inflammatory diagnoses do not imply generic disease."""
    specific_keys = ("rheumatoid_arthritis", "sle", "psoriasis", "ibd")
    specific_present = any(report.extracted.get(key) is True for key in specific_keys)
    if not specific_present:
        return

    separate_generic = re.search(
        r"\b(?:other\s+chronic\s+inflammatory\s+disease|other\s+systemic\s+inflammatory\s+disease|vasculitis|sarcoidosis)\b"
        r"[^\n.;]*(?:yes|present|active|history|diagnosed|vasculitis|sarcoidosis)",
        text,
        re.IGNORECASE,
    )
    if separate_generic:
        _record(report, "inflammatory_disease", True, "parsed", "separate chronic inflammatory disease")
        return

    if report.extracted.get("inflammatory_disease") is True:
        report.extracted["inflammatory_disease"] = False
        report.field_meta["inflammatory_disease"] = {
            "confidence": "inferred",
            "source": "specific inflammatory diagnosis suppresses generic bucket",
        }
    elif "inflammatory_disease" not in report.extracted:
        _record(
            report,
            "inflammatory_disease",
            False,
            "inferred",
            "specific inflammatory diagnosis suppresses generic bucket",
        )


def _extract_unavailable_reason(text: str, label: str) -> str | None:
    if label == "CAC" and re.search(
        r"\bno\s+(?:cac|coronary calcium|calcium score)\s+(?:available|performed|done|reported)\b",
        text,
        re.IGNORECASE,
    ):
        return f"{label} unavailable or not done"
    unavailable_terms = (
        r"not available|unavailable|not done|deferred|unable to calculate|cannot calculate|"
        r"not reported|not performed|unknown|no results found(?:\s+for:?)?|"
        r"outside reportable range|no [a-z ]{0,30}available|\*{2,}|@[A-Z0-9_]+@"
    )
    if label == "CAC":
        label_pattern = r"(?:CAC|coronary(?:\s+artery)?\s+calcium(?:\s+\(CAC\))?|coronary calcium|calcium score)"
    elif label == "LDL-C":
        label_pattern = r"(?:LDL-C|LDL|low density lipoprotein)"
    elif label == "UACR":
        label_pattern = r"(?:UACR|urine\s+ACR|urine\s+albumin(?:/|\s+)creatinine|albumin/creatinine(?:\s+ratio)?|albumin\s+creatinine\s+ratio|alb/cr(?:\s+ratio)?|microalbumin/creatinine(?:\s+ratio)?|ALBCREAT)"
    elif label == "ApoB":
        label_pattern = r"(?:ApoB|Apo\s*B|apolipoprotein\s*B|APOB)"
    elif label == "Lp(a)":
        label_pattern = r"(?:Lp\(a\)|Lp\s*a|LIPOA|lipoprotein\s*\(a\))"
    elif label == "hsCRP":
        label_pattern = r"(?:hsCRP|hs-CRP|CRPHS|high sensitivity CRP)"
    else:
        label_pattern = re.escape(label)
    if re.search(
        rf"\b{label_pattern}[^\n]*:\s*(?:\*{{2,}}|@[A-Z0-9_]+@)\s*$",
        text,
        re.IGNORECASE | re.MULTILINE,
    ):
        return f"{label} placeholder detected"
    pattern = rf"\b{label_pattern}[^\n.;]*?\b(?:{unavailable_terms})\b(?:\s*(?:because|due to|reason:?)\s*([^.;\n]+))?"
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        pattern = rf"\b(?:{unavailable_terms})\b[^\n.;]*?\b{label_pattern}(?:\s*(?:because|due to|reason:?)\s*([^.;\n]+))?"
        match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    detail = (match.group(1) or "").strip()
    if detail:
        return f"{label} unavailable: {detail}"
    return f"{label} unavailable or not done"


def _parse_epic_table_labs(report: ParseReport, text: str) -> None:
    """Extract common Epic result-table values while ignoring reference ranges."""
    table_patterns = (
        ("tc", r"\b(?:TC|CHOL(?:ESTEROL)?|TOTAL\s+CHOLESTEROL)\b", "Epic lipid table"),
        ("tg", r"\b(?:TG|TRIG(?:LYCERIDES)?)\b", "Epic lipid table"),
        ("hdl", r"\bHDL\b", "Epic lipid table"),
        ("ldl", r"\bLDL\b", "Epic lipid table"),
        ("a1c", r"\b(?:A1C|HBA1C|HEMOGLOBIN\s+A1C)\b", "Epic A1c table"),
        ("egfr", r"\b(?:LABGLOM|eGFR\s+Cre|eGFR(?:\s+CREATININE)?)\b", "Epic kidney table"),
        ("uacr", r"\b(?:UACR|urine\s+ACR|albumin/creatinine(?:\s+ratio)?|albumin\s+creatinine\s+ratio|alb/cr(?:\s+ratio)?|microalbumin/creatinine(?:\s+ratio)?|ALBCREAT)\b", "Epic UACR table"),
    )
    pending: tuple[str, str] | None = None
    for line in (text or "").splitlines():
        clean = line.strip()
        if not clean or re.search(
            r"\b(?:reference|normal|prediabetes|diabetes\s*[>=]|unavailable|not done|no results found|not available)\b",
            clean,
            re.IGNORECASE,
        ):
            continue
        if PLACEHOLDER_VALUE_RE.search(clean):
            continue
        matched = None
        for field, label_pattern, source in table_patterns:
            label_match = re.search(label_pattern, clean, re.IGNORECASE)
            if field not in report.extracted and label_match:
                matched = (field, source, label_match.start(), label_match.end(), label_pattern)
                break
        if pending and not matched and not re.match(
            r"^\s*(?:\d{1,2}/\d{1,2}/\d{2,4}\s+)?[<>]?\d+(?:\.\d+)?(?:\s|\(|$)",
            clean,
        ):
            pending = None
            continue
        active = matched or pending
        if not active:
            continue
        field, source = active[0], active[1]
        if field == "egfr" and re.search(r"\b(?:crcl|creatinine\s+clearance)\b", clean, re.IGNORECASE):
            pending = None
            continue
        clean_for_values = clean
        if matched:
            clean_for_values = clean[matched[3]:]
        clean_for_values = re.sub(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", " ", clean_for_values)
        numbers = re.findall(r"(?<!/)\b\d+(?:\.\d+)?\b(?!/)", clean_for_values)
        value = None
        for number in numbers:
            try:
                candidate = float(number)
            except ValueError:
                continue
            if candidate > 1900:
                continue
            value = candidate
            break
        if value is not None and field not in report.extracted:
            _record(report, field, value, "parsed", source)
            pending = None
        elif matched:
            pending = matched
        else:
            pending = None


def _parse_date_token(date_text: str) -> datetime | None:
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_text, fmt)
        except ValueError:
            continue
    return None


def _is_plausible_a1c(value: float) -> bool:
    return 3.0 <= value <= 20.0


def _parse_a1c_section_table(report: ParseReport, text: str) -> None:
    """Extract dated A1c result rows while ignoring reference-range text."""
    if "a1c" in report.extracted:
        return

    lines = (text or "").splitlines()
    anchors = [
        index
        for index, line in enumerate(lines)
        if re.search(r"\b(?:A1c|A1C|HbA1c|HgbA1c|Hemoglobin\s+A1c|Hemoglobin\s+A1C)\b\s*:?", line, re.IGNORECASE)
    ]
    if not anchors:
        return

    dated_rows: list[tuple[datetime | None, int, float]] = []
    section_found = False
    stop_header = re.compile(
        r"^\s*(?:ApoB|Apo\s*B|Lp\(a\)|LIPOA|hsCRP|CRPHS|eGFR|Urine\s+ACR|UACR|Imaging|Medications|Family History|Labs)\s*:",
        re.IGNORECASE,
    )
    skip_reference = re.compile(r"\b(?:Reference Range|Ref Range|Normal|Prediabetes|Diabetes|Comment)\b", re.IGNORECASE)
    dated_result = re.compile(
        r"\b(?P<date>(?:\d{4}-\d{1,2}-\d{1,2})|(?:\d{1,2}/\d{1,2}/\d{2,4}))\b"
        r"\s+(?P<value>\d+(?:\.\d+)?)\b"
    )

    for anchor in anchors:
        block = lines[anchor : min(len(lines), anchor + 22)]
        for offset, line in enumerate(block):
            clean = line.strip()
            if offset > 0 and stop_header.search(clean):
                break
            if not clean or PLACEHOLDER_VALUE_RE.search(clean):
                continue
            if offset > 0 and skip_reference.search(clean) and not dated_result.search(clean):
                continue
            match = dated_result.search(clean)
            if not match:
                continue
            section_found = True
            value = float(match.group("value"))
            if _is_plausible_a1c(value):
                dated_rows.append((_parse_date_token(match.group("date")), anchor + offset, value))

    if dated_rows:
        dated_rows.sort(key=lambda row: (row[0] or datetime.min, -row[1]), reverse=True)
        _record(report, "a1c", dated_rows[0][2], "parsed", "A1c dated result table")
        return

    if section_found or anchors:
        report.field_meta.setdefault(
            "a1c",
            {"confidence": "uncertain", "source": "A1c section found; result unclear"},
        )
        if "A1c section found; result unclear" not in report.warnings:
            report.warnings.append("A1c section found; result unclear")


def extract_uacr(report: ParseReport, text: str) -> None:
    """Extract UACR from aliases with nearby dated rows or Result lines."""
    if "uacr" in report.extracted:
        return
    lines = (text or "").splitlines()
    alias_pattern = re.compile(r"\b" + _alias_pattern(UACR_ALIASES) + r"\b", re.IGNORECASE)
    dated_result = re.compile(
        r"\b(?:\d{4}-\d{1,2}-\d{1,2}|\d{1,2}/\d{1,2}/\d{2,4})\b\s+(?P<value>\d+(?:\.\d+)?)\b"
    )
    result_line = re.compile(r"\bresult\s*(?:=|:|-)?\s*(?P<value>\d+(?:\.\d+)?)\b", re.IGNORECASE)
    skip_line = re.compile(r"\b(?:reference|normal range|comment|units?)\b", re.IGNORECASE)

    for index, line in enumerate(lines):
        label_match = alias_pattern.search(line)
        if not label_match:
            continue
        block = lines[index : min(len(lines), index + 15)]
        block_text = "\n".join(block)
        if re.search(r"\b(?:cannot|unable\s+to)\s+calculate\b|\boutside\s+reportable\s+range\b", block_text, re.IGNORECASE):
            _record_source_meta(
                report,
                "uacr_status",
                "indeterminate",
                "uncertain",
                "UACR not calculable.",
                source_text=line.strip(),
                review_required=True,
            )
            if "UACR not calculable." not in report.warnings:
                report.warnings.append("UACR not calculable.")
            return
        candidates: list[tuple[int, float, str]] = []
        pending_result = False
        for offset, block_line in enumerate(block):
            clean = block_line.strip()
            if not clean or PLACEHOLDER_VALUE_RE.search(clean) or skip_line.search(clean):
                continue
            if re.search(r"\b(?:not done|no results found|unavailable|unknown)\b", clean, re.IGNORECASE):
                continue
            match = dated_result.search(clean)
            if match:
                value = float(match.group("value"))
                if 0 <= value <= 10000:
                    candidates.append((100 - offset, value, clean))
                continue
            match = result_line.search(clean)
            if match:
                value = float(match.group("value"))
                if 0 <= value <= 10000:
                    candidates.append((90 - offset, value, clean))
                continue
            if pending_result:
                value_match = re.search(r"^(\d+(?:\.\d+)?)\b", clean)
                if value_match:
                    value = float(value_match.group(1))
                    if 0 <= value <= 10000:
                        candidates.append((88 - offset, value, clean))
                        pending_result = False
                        continue
            if re.match(r"^result\s*:?\s*$", clean, re.IGNORECASE):
                pending_result = True
                continue
            if offset == 0:
                tail = clean[label_match.end():]
                value_match = re.search(r"(?:=|:|-|\|)?\s*(\d+(?:\.\d+)?)\b", tail)
                if value_match:
                    value = float(value_match.group(1))
                    if 0 <= value <= 10000:
                        candidates.append((80, value, clean))
        if candidates:
            candidates.sort(key=lambda item: item[0], reverse=True)
            _record(report, "uacr", candidates[0][1], "parsed", candidates[0][2])
            return


def extract_hscrp(report: ParseReport, text: str) -> None:
    """Extract hsCRP from labeled lines or short multiline blocks."""
    if "hscrp" in report.extracted:
        return
    lines = (text or "").splitlines()
    alias_pattern = re.compile(r"\b" + _alias_pattern(HSCRP_ALIASES) + r"\b", re.IGNORECASE)
    skip_line = re.compile(r"\b(?:reference|ref\s+range|normal|comment|units?)\b", re.IGNORECASE)
    no_results = re.compile(r"\b(?:no\s+results\s+found|not\s+done|unavailable|unknown)\b", re.IGNORECASE)

    for index, line in enumerate(lines):
        alias_match = alias_pattern.search(line)
        if not alias_match:
            continue
        candidates: list[tuple[int, float, str]] = []
        block = lines[index : min(len(lines), index + 8)]
        for offset, block_line in enumerate(block):
            clean = block_line.strip()
            if not clean:
                continue
            if no_results.search(clean):
                if not candidates:
                    break
                continue
            if PLACEHOLDER_VALUE_RE.search(clean):
                continue
            if skip_line.search(clean):
                continue
            if offset > 0 and re.search(r"\b(?:\d{4}-\d{1,2}-\d{1,2}|\d{1,2}/\d{1,2}/\d{2,4})\b", clean):
                continue
            value_area = clean[alias_match.end():] if offset == 0 else clean
            if re.match(r"^\s*<\s*\d", value_area):
                continue
            value_match = re.search(r"(?<![<>=])\b(\d+(?:\.\d+)?)\b", value_area)
            if not value_match:
                continue
            value = float(value_match.group(1))
            if 0 <= value <= 100:
                priority = 100 - offset
                candidates.append((priority, value, clean))
        if candidates:
            candidates.sort(key=lambda item: item[0], reverse=True)
            _record(report, "hscrp", candidates[0][1], "parsed", candidates[0][2])
            return


def _parse_smoking_details(report: ParseReport, text: str) -> None:
    """Parse current/former smoking fields without treating former use as active use."""
    status = re.search(r"\bsmoking\s+status\s*(?:=|:)?\s*(current|former|never|none|not current)\b", text, re.IGNORECASE)
    if status:
        value = status.group(1).lower()
        if value == "current":
            _record(report, "smoker", True, "parsed", "smoking status")
        else:
            _record(report, "smoker", False, "parsed", "smoking status")
            if value == "former":
                _record(report, "former_smoker", True, "parsed", "smoking status")
    pack_years = re.search(r"\b(\d+(?:\.\d+)?)\s*pack[-\s]?years?\b", text, re.IGNORECASE)
    if pack_years:
        _record(report, "pack_years", float(pack_years.group(1)), "parsed", "tobacco history")


def _parse_bp_readings_table(report: ParseReport, text: str) -> None:
    """Use the first BP pair after a BP readings heading as the most recent BP."""
    in_bp_table = False
    for line in (text or "").splitlines():
        clean = line.strip()
        if re.search(r"\bBP\s+Readings?\b|\bBlood Pressure Readings?\b", clean, re.IGNORECASE):
            in_bp_table = True
            continue
        if not in_bp_table:
            continue
        if not clean:
            continue
        clean = re.sub(r"\(!\)", " ", clean)
        match = re.search(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b\s+(?:\S+\s+)?(\d{2,3})\s*/\s*(\d{2,3})\b", clean)
        if match:
            _record(report, "sbp", float(match.group(1)), "parsed", "most recent BP readings table")
            _record(report, "dbp", float(match.group(2)), "parsed", "most recent BP readings table")
            return
        if re.search(r"^[A-Za-z].*:", clean) and not re.search(r"\b(?:BP|blood pressure)\b", clean, re.IGNORECASE):
            in_bp_table = False


def _parse_height_weight_bmi(report: ParseReport, text: str) -> None:
    if "bmi" in report.extracted:
        return

    height_in = None
    feet_inches = re.search(r"\b(\d)\s*'\s*(\d{1,2})\s*(?:\"|in|inches)?\b", text, re.IGNORECASE)
    if feet_inches:
        height_in = int(feet_inches.group(1)) * 12 + int(feet_inches.group(2))
    else:
        inches = re.search(r"\b(?:height|ht)\s*(?:=|:)?\s*(\d{2,3})\s*(?:in|inches)\b", text, re.IGNORECASE)
        if inches:
            height_in = int(inches.group(1))

    weight_lb = None
    weight = re.search(r"\b(?:weight|wt)\s*(?:=|:)?\s*(\d{2,3}(?:\.\d+)?)\s*(?:lb|lbs|pounds)\b", text, re.IGNORECASE)
    if weight:
        weight_lb = float(weight.group(1))

    if height_in and weight_lb:
        bmi = weight_lb * 703 / (height_in * height_in)
        _record(report, "bmi", round(bmi, 1), "inferred", "height/weight")


def _parse_medications(report: ParseReport, text: str) -> None:
    structured = extract_medications_structured(text)
    detected = structured.get("medications_detected") or []
    if detected:
        _record(report, "medications_detected", detected, "parsed", "medication vocabulary")

    if structured.get("medications_raw"):
        _record(report, "medications_raw", structured["medications_raw"], "parsed", "medication vocabulary")

    dm_classes = {"sglt2", "sglt2_metformin_combo", "sglt2_dpp4_combo", "glp1_gip", "metformin", "dpp4_metformin_combo"}
    dm_meds = [
        str(m.get("normalized_name"))
        for m in detected
        if m.get("active") is True and str(m.get("class") or "") in dm_classes
    ]
    if dm_meds:
        _record(report, "dm_meds_raw", ", ".join(dict.fromkeys(dm_meds)), "parsed", "diabetes medication vocabulary")

    bool_fields = {
        "lipidLowering",
        "statin",
        "ezetimibe",
        "pcsk9",
        "bempedoic_acid",
        "sglt2",
        "glp1_gip",
        "metformin",
        "ace_arb",
        "bpTreated",
        "mra",
    }
    for field in bool_fields:
        value = structured.get(field)
        if value is True:
            _record(report, field, True, "inferred", "active medication vocabulary")

    lipid_classes = {
        "statin",
        "ezetimibe",
        "pcsk9",
        "inclisiran",
        "bempedoic_acid",
        "bempedoic_acid_ezetimibe",
        "icosapent_ethyl",
        "omega3",
        "fibrate",
        "niacin",
        "bile_acid_sequestrant",
    }
    if structured.get("lipidLowering") is not True and any(
        m.get("active") is False and str(m.get("class") or "") in lipid_classes
        for m in detected
    ):
        _record(report, "lipidLowering", False, "inferred", "inactive lipid medication mention")

    if structured.get("glp1_gip") is True:
        _record(report, "glp1", True, "inferred", "active GLP-1/GIP medication vocabulary")

    if structured.get("statin_intensity"):
        _record(report, "statin_intensity", structured["statin_intensity"], "inferred", "active statin dose")
    if structured.get("statin_intolerance") is True:
        _record(report, "statin_intolerance", True, "inferred", "inactive statin intolerance/allergy")

    inactive_mentions = [
        f"{m.get('normalized_name')} {str(m.get('source_line') or '').strip()}"
        for m in detected
        if m.get("active") is False
    ]
    for mention in inactive_mentions:
        report.warnings.append(f"Medication mentioned but not counted as active: {mention}.")


def _parse_reproductive_history(report: ParseReport, text: str) -> None:
    reproductive_labels = {
        "early_menopause": [r"early\s+menopause"],
        "premature_menopause": [r"premature\s+menopause", r"primary\s+ovarian\s+insufficiency", r"poi"],
        "preeclampsia": [r"preeclampsia", r"pre-eclampsia"],
        "gestational_hypertension": [r"gestational\s+hypertension", r"hypertensive\s+disorder\s+of\s+pregnancy"],
        "gestational_diabetes": [r"gestational\s+diabetes", r"gdm"],
        "preterm_delivery": [r"preterm[-\s]+(?:delivery|birth)", r"delivery\s+before\s+37\s+weeks"],
        "small_for_gestational_age": [
            r"small[-\s]+for[-\s]+gestational[-\s]+age(?:[-\s]+(?:infant|baby|birth))?",
            r"\bsga\s+(?:infant|baby|birth)",
            r"\bsga\b",
        ],
        "recurrent_pregnancy_loss": [
            r"recurrent[-\s]+(?:pregnancy[-\s]+loss|miscarriage)",
            r"recurrent\s+spontaneous\s+pregnancy\s+loss",
        ],
        "pcos_or_irregular_menses": [r"pcos", r"polycystic\s+ovary\s+syndrome", r"irregular\s+menses", r"irregular\s+periods"],
        "early_menarche": [r"early\s+menarche"],
    }

    for field, labels in reproductive_labels.items():
        found, value = _parse_explicit_bool_line_status(text, labels)
        if found:
            _record(report, field, value, "parsed", "reproductive history")

    menopause_age = re.search(
        r"\b(?:menopause|menopausal)\s+(?:at\s+)?(?:age\s+)?(\d{1,2})\b",
        text,
        re.IGNORECASE,
    )
    if not menopause_age:
        menopause_age = re.search(
            r"\b(?:menopause_age|menopause\s+age)\s*(?:=|:)?\s*(\d{1,2})\b",
            text,
            re.IGNORECASE,
        )
    if menopause_age:
        age = float(menopause_age.group(1))
        _record(report, "menopause_age", age, "parsed", "menopause age")
        _record(report, "early_menopause", age < 45, "inferred", "menopause age")
        _record(report, "premature_menopause", age < 40, "inferred", "menopause age")

    menarche_age = re.search(
        r"\b(?:menarche)\s+(?:at\s+)?(?:age\s+)?(\d{1,2})\b",
        text,
        re.IGNORECASE,
    )
    if menarche_age:
        age = float(menarche_age.group(1))
        _record(report, "menarche_age", age, "parsed", "menarche age")
        _record(report, "early_menarche", age < 10, "inferred", "menarche age")

    for field, labels in reproductive_labels.items():
        if field in report.extracted:
            continue
        value = _keyword_present_without_explicit_negation(text, labels)
        if value is not None:
            _record(report, field, value, "parsed", "reproductive history mention")


def parse_smartphrase_report(text: str) -> ParseReport:
    """Parse pasted EMR/lab text into a reviewable SmartPhrase ParseReport."""
    report = ParseReport()
    if not text:
        return report

    report.source_style = detect_source_style(text)
    lowered = text.lower()
    text_without_problem_list = _strip_problem_list_block(text)
    clinical_text = _strip_ascvd_calculator_review_text(text_without_problem_list)
    clinical_lowered = clinical_text.lower()
    ascvd_calculator_review = _has_ascvd_calculator_review_text(text)
    if ascvd_calculator_review:
        _record_source_meta(
            report,
            "clinical_ascvd_review",
            True,
            "uncertain",
            "Possible ASCVD history referenced by risk calculator; confirm clinical ASCVD.",
            source_text="ASCVD Risk score failed to calculate",
            review_required=True,
        )

    patient_age, age_confidence, age_source = extract_demographics_age(text)
    if patient_age is not None:
        _record_age(report, patient_age, age_confidence, age_source)
    else:
        invalid_age = re.search(
            r"^\s*age\s*:?\s*(\d{1,4})\s*(?:y\.?o\.?|years?|yrs?|yr)?\b",
            text,
            re.IGNORECASE | re.MULTILINE,
        )
        if invalid_age and not re.search(r"\bage\s+at\s+event\b", invalid_age.group(0), re.IGNORECASE):
            _record_age(report, invalid_age.group(1), "parsed", "explicit demographic age")

    age_year_old = re.search(
        r"\b(\d{1,3})\s*(?:-?\s*year-old|y\.?o\.?|y/o)\b(?:\s*(male|female|man|woman|m|f))?",
        text,
        re.IGNORECASE,
    )
    if age_year_old:
        if "age" not in report.extracted:
            _record_age(report, age_year_old.group(1), "parsed", "age/sex prose")
        if age_year_old.group(2):
            sex_value = age_year_old.group(2).lower()
            _record(report, "sex", "male" if sex_value in {"m", "male", "man"} else "female", "parsed", "age/sex prose")

    age_sex_match = re.search(r"\b(\d{1,3})\s*[/\s-]*([mf])\b", text, re.IGNORECASE)
    if age_sex_match:
        context = text[max(0, age_sex_match.start() - 45): age_sex_match.start()].lower()
        if not re.search(r"\b(?:father|mother|brother|sister|sibling|relative|family history|age at event)\b", context):
            if "age" not in report.extracted:
                _record_age(report, age_sex_match.group(1), "inferred", "compact age/sex token")
            if "sex" not in report.extracted:
                _record(
                    report,
                    "sex",
                    "male" if age_sex_match.group(2).lower() == "m" else "female",
                    "inferred",
                    "compact age/sex token",
                )

    sex_match = re.search(r"\b(?:sex|gender)\s*(?:=|:|is)?\s*(male|female|m|f)\b", text, re.IGNORECASE)
    if sex_match:
        sex = sex_match.group(1).lower()
        sex_value = "male" if sex == "m" else "female" if sex == "f" else sex
        current_source = str((report.field_meta.get("sex") or {}).get("source") or "").lower()
        if report.extracted.get("sex") not in {None, sex_value} and "explicit" not in current_source:
            report.extracted["sex"] = sex_value
            report.field_meta["sex"] = {"confidence": "parsed", "source": "explicit sex"}
            report.conflicts = [conflict for conflict in report.conflicts if not conflict.startswith("sex:")]
        else:
            _record(report, "sex", sex_value, "parsed", "explicit sex")
    race_match = re.search(r"\b(?:race(?:/ethnicity)?|ethnicity)\s*(?:=|:|is)?\s*([^\n]+)", text, re.IGNORECASE)
    if race_match:
        race = race_match.group(1).strip().strip(".")
        if race and not PLACEHOLDER_VALUE_RE.fullmatch(race):
            _record(report, "race_ethnicity", race, "parsed", "explicit race/ethnicity")

    bp_match = re.search(r"\b(?:bp|blood pressure)\s*(?:=|:)?\s*(\d{2,3})\s*/\s*(\d{2,3})", text, re.IGNORECASE)
    if bp_match:
        _record(report, "sbp", float(bp_match.group(1)), "parsed", "blood pressure pair")
        _record(report, "dbp", float(bp_match.group(2)), "parsed", "blood pressure pair")

    if "sbp" not in report.extracted or "dbp" not in report.extracted:
        bp_match = re.search(r"\b(\d{2,3})\s*/\s*(\d{2,3})\s*(?:mmhg)?\b", text, re.IGNORECASE)
        if bp_match:
            window = text[max(0, bp_match.start() - 30): min(len(text), bp_match.end() + 30)].lower()
            if "bp" in window or "blood pressure" in window or "vitals" in window:
                _record(report, "sbp", float(bp_match.group(1)), "parsed", "blood pressure pair")
                _record(report, "dbp", float(bp_match.group(2)), "parsed", "blood pressure pair")

    if "sbp" not in report.extracted or "dbp" not in report.extracted:
        _parse_bp_readings_table(report, text)

    for field, label_pattern in NUMERIC_PATTERNS.items():
        if field in report.extracted:
            continue
        if field == "hscrp":
            continue
        value = _parse_number_after_label(text, label_pattern)
        if value is not None:
            _record(report, field, value, "parsed", "labeled value")

    _parse_epic_table_labs(report, text)
    _parse_a1c_section_table(report, text)
    extract_uacr(report, text)
    extract_hscrp(report, text)

    actual_a1c = re.search(r"\bactual\s+(?:a1c|hba1c)\s*(?:=|:)?\s*(\d+(?:\.\d+)?)\b", text, re.IGNORECASE)
    if actual_a1c and "a1c" not in report.extracted:
        _record(report, "a1c", float(actual_a1c.group(1)), "parsed", "actual A1c")

    apob_explicit = re.search(r"\b(?:apob|apo\s*b|apolipoprotein\s*b)\s*(?:=|:|\|)?\s*(\d+(?:\.\d+)?)\b", text, re.IGNORECASE)
    if apob_explicit:
        _record(report, "apob", float(apob_explicit.group(1)), "parsed", "ApoB")

    uacr_alias_pattern = _alias_pattern(UACR_ALIASES)
    alb_cr = re.search(rf"\b{uacr_alias_pattern}\b[^\n.;]*?(?:=|:|-|\|)?\s*(\d+(?:\.\d+)?)", text, re.IGNORECASE)
    if alb_cr and "uacr" not in report.extracted and not re.search(r"\b(?:not done|no results found|unavailable|unknown|\*{2,})\b", alb_cr.group(0), re.IGNORECASE):
        _record(report, "uacr", float(alb_cr.group(1)), "parsed", "albumin/creatinine ratio")

    cac_alias_pattern = _alias_pattern(CAC_ALIASES)
    agatston = re.search(
        rf"\b(?:agatston(?:\s+score)?|{cac_alias_pattern}(?:\s+\(CAC\))?(?:\s+score)?)\b\s*(?:=|:|-)?\s*(\d+(?:\.\d+)?)",
        text,
        re.IGNORECASE,
    )
    if agatston and "cac" not in report.extracted:
        _record(report, "cac", float(agatston.group(1)), "parsed", "Agatston/CAC score")

    lpa_match = re.search(r"\b(?:lp\(a\)|lpa|lp a|lipoa|lipoprotein\s*\(a\))\s*(?:=|:|is|\|)?\s*([<>]?\s*\d+(?:\.\d+)?)\s*(nmol/L|mg/dL)?", text, re.IGNORECASE)
    if lpa_match:
        _record(report, "lpa", float(lpa_match.group(1).replace(" ", "").lstrip("<>")), "parsed", "Lp(a)")
        if lpa_match.group(2):
            unit = lpa_match.group(2).lower()
            _record(report, "lpa_unit", "nmol/L" if unit == "nmol/l" else "mg/dL", "parsed", "Lp(a) unit")
        else:
            _record_source_meta(
                report,
                "lp_a_review",
                True,
                "uncertain",
                "Confirm Lp(a) units.",
                source_text=lpa_match.group(0),
                review_required=True,
            )
            report.field_meta["lpa_unit"] = {
                "confidence": "uncertain",
                "source": "Lp(a) value present but unit missing",
            }
            report.warnings.append("Lp(a) value parsed without units; please review nmol/L vs mg/dL.")

    for field, label in (
        ("egfr", "eGFR"),
        ("uacr", "UACR"),
        ("cac", "CAC"),
        ("ldl", "LDL-C"),
        ("apob", "ApoB"),
        ("lpa", "Lp(a)"),
        ("hscrp", "hsCRP"),
    ):
        if field not in report.extracted:
            reason = _extract_unavailable_reason(text, label)
            if reason:
                _mark_unavailable(report, field, reason, label)
                if field == "uacr":
                    if "calculate" in reason.lower() or "reportable" in reason.lower():
                        _record_source_meta(
                            report,
                            "uacr_status",
                            "indeterminate",
                            "uncertain",
                            "UACR not calculable.",
                            review_required=True,
                        )
                if field == "cac":
                    report.extracted["cac"] = None
                    _record(report, "cac_not_done", True, "parsed", reason)

    _parse_height_weight_bmi(report, text)

    family_section = extract_family_history(_family_history_block(text))
    fhx_detail = _find_family_history_event_detail(text)
    explicit_premature_fhx_found, explicit_premature_fhx = _parse_explicit_bool_line_status(
        text,
        [
            r"premature\s+family\s+history",
            r"premature\s+ascvd\s+in\s+first[-\s]?degree\s+relative",
            r"premature\s+first[-\s]?degree\s+(?:family\s+)?history",
            r"family\s+history",
        ],
    )
    if family_section:
        if fhx_detail:
            premature = fhx_detail["premature_fhx_ascvd"]
            if family_section.get("premature_fhx_ascvd") is not None and family_section["premature_fhx_ascvd"] != premature:
                report.conflicts.append(
                    "Family history conflict: explicit premature flag differs from event age."
                )
            family_section["premature_fhx_ascvd"] = premature
            family_section["relationship"] = fhx_detail["relationship"]
            family_section["event_type"] = fhx_detail["event_type"]
            family_section["age_at_event"] = fhx_detail["age_at_event"]
            family_section["source"] = "structured family history"
            family_section["source_text"] = fhx_detail["source_text"]
        if "premature_fhx_ascvd" in family_section:
            _record(report, "fhx", family_section["premature_fhx_ascvd"], "parsed", family_section["source"])
        if family_section.get("relationship"):
            _record(report, "family_history_relationship", family_section["relationship"], "parsed", "family history")
        if family_section.get("event_type"):
            _record(report, "family_history_event_type", family_section["event_type"], "parsed", "family history")
        if family_section.get("age_at_event") is not None:
            _record(report, "family_history_age_at_event", family_section["age_at_event"], "parsed", "family history")
        if family_section.get("relationship") or family_section.get("event_type") or family_section.get("age_at_event") is not None:
            _record(report, "fhx_text", family_section.get("source_text") or _family_history_block(text), "parsed", "family history")
    elif fhx_detail:
        relationship = fhx_detail["relationship"]
        event_age = fhx_detail["age_at_event"]
        premature = fhx_detail["premature_fhx_ascvd"]
        if explicit_premature_fhx is not None and explicit_premature_fhx != premature:
            report.conflicts.append(
                "Family history conflict: explicit premature flag differs from event age."
            )
        _record(report, "fhx", premature, "inferred", "structured family history")
        _record(report, "fhx_text", fhx_detail["source_text"], "parsed", "family history")
        _record(report, "family_history_relationship", relationship, "parsed", "family history")
        _record(report, "family_history_event_type", fhx_detail["event_type"], "parsed", "family history")
        if event_age is not None:
            _record(report, "family_history_age_at_event", event_age, "parsed", "family history")
    elif explicit_premature_fhx_found:
        _record(report, "fhx", explicit_premature_fhx, "parsed", "explicit premature family history")
    elif re.search(
        r"\b(?:premature\s+family\s+history|premature\s+ascvd\s+in\s+first[-\s]?degree\s+relative|family\s+history)\b[^\n.;]*:\s*(?:\*{2,}|@[A-Z0-9_]+@)\s*$",
        text,
        re.IGNORECASE | re.MULTILINE,
    ):
        _record(report, "fhx", None, "parsed", "placeholder family history")
    elif re.search(r"\bfamily history\b|\bfhx\b", text, re.IGNORECASE):
        report.field_meta["fhx"] = {
            "confidence": "uncertain",
            "source": "family history mentioned without complete relationship/event/age",
        }
        report.warnings.append("Family history mentioned; relationship, event, or age not specified.")

    diabetes_text = _without_gestational_diabetes_context(text_without_problem_list)
    diabetes_lowered = diabetes_text.lower()
    diabetes_found, diabetes_explicit = _parse_explicit_bool_line_status(
        diabetes_text,
        [r"type\s+2\s+diabetes", r"diabetes", r"dm2", r"t2dm"],
    )
    diabetes_positive = bool(
        re.search(
            r"\b(?:has|history of|hx of|known|with|treated for|type 2|t2dm|dm2)\s+(?:diabetes|dm2|t2dm|type 2 diabetes)\b",
            diabetes_lowered,
        )
    )
    if diabetes_found and diabetes_explicit is None:
        _record(report, "diabetes", None, "parsed", "diabetes unknown/not documented")
    elif diabetes_explicit is False:
        _record(report, "diabetes", False, "parsed", "diabetes negation")
        if "a1c" in report.extracted and report.extracted["a1c"] >= 6.5:
            report.conflicts.append("diabetes: text says no diabetes but A1c is >=6.5")
    elif diabetes_explicit is True or diabetes_positive:
        _record(report, "diabetes", True, "parsed", "diabetes text")
    elif "a1c" in report.extracted and report.extracted["a1c"] >= 6.5:
        _record(report, "diabetes", True, "inferred", "A1c >=6.5")
    elif "a1c" in report.extracted and 5.7 <= report.extracted["a1c"] < 6.5:
        _record(report, "diabetes", False, "inferred", "A1c 5.7-6.4")
        _record(report, "prediabetes_context", True, "inferred", "A1c 5.7-6.4")

    diabetes_duration = re.search(
        r"\b(?:diabetes|t2dm|dm2)\s+(?:duration\s*)?(?:for\s*)?(\d{1,2})\s*(?:years|yrs|y)\b",
        text,
        re.IGNORECASE,
    )
    if not diabetes_duration:
        diabetes_duration = re.search(
            r"\bdiabetes\s+duration\s*(?:=|:)?\s*(\d{1,2})\s*(?:years|yrs|y)?\b",
            text,
            re.IGNORECASE,
        )
    if diabetes_duration:
        _record(report, "diabetes_duration_years", float(diabetes_duration.group(1)), "parsed", "diabetes duration")

    abi_match = re.search(r"\bABI\s*(?:=|:)?\s*(0?\.\d+|1(?:\.0+)?)\b", text, re.IGNORECASE)
    if abi_match:
        abi_value = float(abi_match.group(1))
        _record(report, "abi", abi_value, "parsed", "ABI")
        _record(report, "abi_lt_0_9", abi_value < 0.9, "inferred", "ABI")

    explicit_bool_labels = {
        "smoker": [r"current\s+smoker", r"smoker", r"smoking", r"tobacco"],
        "bpTreated": [r"bp\s+treated", r"bp\s+meds?", r"htn\s+meds?", r"antihypertensive"],
        "lipidLowering": [r"lipid[-\s]?lowering(?:\s+(?:therapy|medication))?", r"statin"],
        "rheumatoid_arthritis": [r"rheumatoid\s+arthritis", r"ra"],
        "sle": [r"sle", r"systemic\s+lupus", r"lupus"],
        "psoriasis": [r"psoriasis"],
        "inflammatory_arthritis": [r"inflammatory\s+arthritis"],
        "ibd": [r"ibd", r"inflammatory\s+bowel\s+disease", r"crohn'?s", r"ulcerative\s+colitis"],
        "hiv": [r"hiv"],
        "stable_art": [r"stable\s+art", r"stable\s+antiretroviral\s+therapy", r"antiretroviral\s+therapy", r"\bart\b"],
        "osa": [re.escape(alias).replace(r"\ ", r"\s+") for alias in OSA_ALIASES],
        "masld": [re.escape(alias).replace(r"\ ", r"\s+") for alias in MASLD_ALIASES]
        + [r"\bmetabolic\s+dysfunction-associated\s+steatotic\s+liver\s+disease\b"],
        "south_asian_ancestry": [
            r"south\s+asian\s+ancestry",
            r"south\s+asian",
            r"asian\s+indian",
            r"indian\s+ancestry",
            r"\bindian\b",
            r"\bpakistani\b",
            r"\bbangladeshi\b",
        ],
        "filipino_ancestry": [r"filipino\s+ancestry", r"filipino"],
        "active_cancer": [r"active\s+cancer", r"current\s+cancer"],
        "cancer_survivor": [r"cancer\s+survivor", r"history\s+of\s+cancer", r"prior\s+cancer"],
        "cancer_life_expectancy_gt_2y": [r"life\s+expectancy\s*(?:>|greater\s+than|over)\s*2\s*y", r"life\s+expectancy\s+at\s+least\s+2\s*y"],
        "suspected_fh_hefh": [r"suspected\s+(?:fh|hefh)", r"heterozygous\s+familial\s+hypercholesterolemia", r"familial\s+hypercholesterolemia", r"\bhefh\b"],
        "incidental_cac": [r"incidental\s+cac", r"incidental\s+coronary\s+(?:artery\s+)?calcification", r"coronary\s+(?:artery\s+)?calcification\s+(?:on|noted\s+on)\s+(?:ct|noncardiac\s+ct)"],
        "breast_arterial_calcification": [
            r"breast\s+arterial\s+calcification",
            r"mammary\s+artery\s+calcification",
            r"breast\s+artery\s+calcification",
            r"vascular\s+calcification\s+on\s+mammogram",
            r"arterial\s+calcifications?\s+on\s+mammogram",
        ],
        "sglt2": [r"sglt2", r"sglt-2"],
        "glp1": [r"glp1", r"glp-1", r"incretin"],
        "ace_arb": [r"ace\s+inhibitor", r"arb", r"ace/arb"],
        "inflammatory_disease": [r"inflammatory\s+disease", r"inflammatory\s+condition", r"inflammatory/immune\s+condition"],
        "diabetic_retinopathy": [r"(?:diabetic\s+)?retinopathy"],
        "diabetic_neuropathy": [r"(?:diabetic\s+)?neuropathy"],
        "abi_lt_0_9": [r"abi\s*<\s*0\.9", r"abi\s+less\s+than\s+0\.9"],
    }
    for field, labels in explicit_bool_labels.items():
        found, value = _parse_explicit_bool_line_status(text, labels)
        if found:
            if (
                value is None
                and report.extracted.get(field) is True
                and (report.field_meta.get(field) or {}).get("source") == "problem list diagnosis"
            ):
                continue
            confidence = "inferred" if field in {"bpTreated", "lipidLowering", "sglt2", "glp1", "ace_arb"} else "parsed"
            _record(report, field, value, confidence, "explicit boolean line")

    apply_problem_list_diagnoses(report, text)

    for field, labels in {
        "south_asian_ancestry": [r"south\s+asian\s+ancestry", r"indian\s+ancestry", r"pakistani\s+ancestry", r"bangladeshi\s+ancestry"],
        "filipino_ancestry": [r"filipino\s+ancestry"],
    }.items():
        if field in report.extracted:
            continue
        value = parse_yes_no_context(text, labels)
        if value is not None:
            _record(report, field, value, "parsed", "explicit ancestry field")

    bac_direct = re.search(
        r"\b(?:breast\s+arterial\s+calcification|mammary\s+artery\s+calcification|breast\s+artery\s+calcification|vascular\s+calcification\s+on\s+mammogram|arterial\s+calcifications?\s+on\s+mammogram)\s*(?:=|:|is|noted)?\s*(unknown|absent|present|mild|moderate|severe|yes|no)?\b",
        text,
        re.IGNORECASE,
    )
    if bac_direct:
        value = (bac_direct.group(1) or "present").lower()
        if value == "yes":
            value = "present"
        elif value == "no":
            value = "absent"
        _record(report, "breast_arterial_calcification", value, "parsed", "breast arterial calcification context")

    clinical_found, clinical_ascvd_value = _parse_explicit_bool_line_status(
        clinical_text,
        [r"clinical\s+ascvd", r"personal\s+ascvd", r"known\s+ascvd", r"ascvd"],
    )
    if not clinical_found:
        clinical_ascvd_value = _clinical_ascvd_explicit_bool(clinical_text)
    if clinical_found or clinical_ascvd_value is not None:
        if clinical_ascvd_value is None and report.extracted.get("clinical_ascvd_review") is True:
            _record(report, "ascvd_clinical", False, "parsed", "clinical ASCVD review-only text")
        else:
            _record(report, "ascvd_clinical", clinical_ascvd_value, "parsed", "explicit clinical ASCVD line")
        if clinical_ascvd_value is True:
            context = _clinical_ascvd_context(clinical_text)
            if context:
                _record(report, "clinical_ascvd_context", context, "parsed", "clinical ASCVD event/procedure")

    fallback_boolean_patterns = {
        "smoker": (
            [r"\b(?:current smoker|active smoker|current(?:ly)? smoking)\b"],
            [r"\b(?:never smoker|non-smoker|nonsmoker|former smoker|quit smoking|denies smoking|no smoking)\b"],
        ),
        "bpTreated": (
            [
                r"\bbp\s+treated\b",
                r"\bantihypertensive\s*(?:=|:|-)?\s*[a-z]",
                r"\b(?:on|taking|current(?:ly)?|active|continue|started)\b[^\n.;]{0,60}\b(?:bp meds?|htn meds?|antihypertensive)\b",
            ],
            [r"\b(?:no|not on|denies|without|stopped|discontinued|held|off)\s+(?:bp meds?|htn meds?|antihypertensive)\b"],
        ),
        "lipidLowering": (
            [r"\b(?:on|taking|current(?:ly)?|active|continue|started)\s+(?:a\s+)?(?:statin|lipid[-\s]?lowering)\b"],
            [r"\b(?:no|not on|denies|without|stopped|discontinued|held|off)\s+(?:statin|lipid[-\s]?lowering)\b"],
        ),
        "ascvd_clinical": (
            [r"\b(?:known ascvd|personal history of mi|prior mi|personal history of stroke|prior stroke|history of cva|peripheral artery disease|pad)\b"],
            [r"\b(?:no|denies|without)\s+(?:clinical\s+)?(?:ascvd|prior\s+mi|mi|stroke|pad)\b"],
        ),
        "sglt2": ([r"\b(?:on|taking|current(?:ly)?|active|continue|started)\b[^\n.;]{0,60}\b(?:sglt2|sglt-2)\b"], []),
        "glp1": ([r"\b(?:on|taking|current(?:ly)?|active|continue|started)\b[^\n.;]{0,60}\b(?:glp1|glp-1|incretin)\b"], []),
        "ace_arb": ([r"\b(?:on|taking|current(?:ly)?|active|continue|started)\b[^\n.;]{0,60}\b(?:ace inhibitor|arb)\b"], []),
    }
    for field, (positive, negative) in fallback_boolean_patterns.items():
        if field in report.extracted:
            continue
        bool_source_text = clinical_lowered if field == "ascvd_clinical" else lowered
        value = _bool_from_text(bool_source_text, positive, negative)
        if value is not None:
            confidence = "inferred" if field in {"bpTreated", "lipidLowering", "sglt2", "glp1", "ace_arb"} else "parsed"
            _record(report, field, value, confidence, "text pattern")
            if field == "ascvd_clinical" and value is True:
                context = _clinical_ascvd_context(clinical_text)
                if context:
                    _record(report, "clinical_ascvd_context", context, "parsed", "clinical ASCVD event/procedure")

    _parse_smoking_details(report, text)

    cac_percentile = re.search(
        r"\b(?:cac\s+percentile|coronary\s+calcium\s+percentile)\s*(?:=|:|is)?\s*(\d{1,3})(?:th|st|nd|rd)?\b",
        text,
        re.IGNORECASE,
    )
    if cac_percentile and report.extracted.get("cac") is not None:
        _record(report, "cac_percentile", float(cac_percentile.group(1)), "parsed", "CAC percentile")
    elif report.extracted.get("cac") is not None and re.search(r"\bcac\b[^\n.;]{0,40}\b(?:>=|at\s+or\s+above)\s*75(?:th)?\s+percentile\b", text, re.IGNORECASE):
        _record(report, "cac_percentile", 75.0, "parsed", "CAC percentile")

    if report.extracted.get("incidental_cac") is True:
        severity = "severe" if re.search(r"\bsevere\b[^\n.;]{0,40}\b(?:incidental\s+)?(?:cac|coronary\s+(?:artery\s+)?calcification)\b|\b(?:incidental\s+)?(?:cac|coronary\s+(?:artery\s+)?calcification)\b[^\n.;]{0,40}\bsevere\b", text, re.IGNORECASE) else "present"
        _record(report, "incidental_cac_severity", severity, "parsed", "incidental CAC context")

    if report.extracted.get("breast_arterial_calcification") is True:
        bac_severity = "present"
        for severity in ("severe", "moderate", "mild"):
            pattern = rf"\b{severity}\b[^\n.;]{{0,60}}\b(?:breast\s+arterial|mammary\s+artery|breast\s+artery|vascular\s+calcification\s+on\s+mammogram|arterial\s+calcifications?\s+on\s+mammogram)|(?:breast\s+arterial|mammary\s+artery|breast\s+artery|vascular\s+calcification\s+on\s+mammogram|arterial\s+calcifications?\s+on\s+mammogram)[^\n.;]{{0,60}}\b{severity}\b"
            if re.search(pattern, text, re.IGNORECASE):
                bac_severity = severity
                break
        _record(report, "breast_arterial_calcification", bac_severity, "parsed", "breast arterial calcification context")

    ascvd_events = extract_ascvd_events(clinical_text)
    if "ascvd_clinical" not in report.extracted and ascvd_events["clinical_ascvd"] is not None:
        _record(report, "ascvd_clinical", ascvd_events["clinical_ascvd"], "parsed", "structured ASCVD event extraction")
    if ascvd_events["event_summary"] and "clinical_ascvd_context" not in report.extracted:
        _record(report, "clinical_ascvd_context", ascvd_events["event_summary"], "parsed", "structured ASCVD event extraction")
    if ascvd_calculator_review and "ascvd_clinical" not in report.extracted:
        _record(report, "ascvd_clinical", False, "parsed", "ASCVD calculator review-only text")
        warning = "Possible ASCVD history referenced by risk calculator; confirm clinical ASCVD."
        if warning not in report.warnings:
            report.warnings.append(warning)

    for field in (
        "rheumatoid_arthritis",
        "sle",
        "psoriasis",
        "inflammatory_arthritis",
        "ibd",
        "hiv",
        "osa",
        "masld",
        "south_asian_ancestry",
        "filipino_ancestry",
    ):
        if field in report.extracted:
            continue
        if field == "osa" and report.extracted.get("sleep_apnea_review") is True:
            continue
        value = _keyword_present_without_explicit_negation(text, explicit_bool_labels[field])
        if value is True:
            _record(report, field, True, "parsed", "condition mention")

    resolve_inflammatory_context(report, text)

    _parse_medications(report, text)
    _parse_reproductive_history(report, text)

    if re.search(
        r"\b(?:red\s+yeast\s+rice|garlic|berberine|plant\s+sterols?|fish\s+oil|omega[-\s]?3\s+supplements?|dietary\s+supplements?)\b",
        text,
        re.IGNORECASE,
    ) and re.search(r"\b(?:cholesterol|lipid|ldl|triglycerides?|tg|lowering)\b", text, re.IGNORECASE):
        _record(report, "lipid_supplements", True, "parsed", "lipid-lowering supplement mention")
        report.warnings.append(
            "Dietary supplement mentioned for lipid lowering; do not count as evidence-based lipid-lowering therapy."
        )

    if re.search(r"\bfasting\b", lowered) and re.search(r"\b(?:lipids|lipid panel|tc|ldl|hdl|tg)\b", lowered):
        _record(report, "fasting_lipids", True, "parsed", "fasting lipid language")
    if re.search(r"\bnon[-\s]?fasting\b", lowered) and re.search(r"\b(?:lipids|lipid panel|tg|triglycerides)\b", lowered):
        _record(report, "fasting_lipids", False, "parsed", "nonfasting lipid language")

    if text.strip() and not report.extracted and not report.field_meta:
        report.warnings.append("No supported RCCKM fields were confidently parsed from pasted text.")

    return report


def parse_smartphrase(text: str) -> ParseReport:
    """Backward-compatible wrapper for parse_smartphrase_report."""
    return parse_smartphrase_report(text)
