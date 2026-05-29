from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from smartphrase_ingest.parser import ParseReport


RAW_TO_CANONICAL = {
    "ldl": "ldl_c",
    "hdl": "hdl_c",
    "tg": "triglycerides",
    "lpa": "lp_a_value",
    "lpa_unit": "lp_a_unit",
    "fhx": "family_history_premature_ascvd",
    "ascvd_clinical": "clinical_ascvd",
    "bpTreated": "bp_treated",
    "lipidLowering": "lipid_lowering",
    "glp1_gip": "glp1",
}


@dataclass(frozen=True)
class ParserRecognitionItem:
    """One parser-recognition field for coverage UI, audit, and feedback."""

    field_id: str
    label: str
    value: str
    status: str
    confidence: str
    source_text: str
    display_priority: int


@dataclass(frozen=True)
class ParserCoverageReport:
    """Structured parser coverage summary with deterministic suggestions."""

    total_core_fields: int
    recognized_core_fields: int
    missing_core_fields: list[str] = field(default_factory=list)
    ambiguous_fields: list[str] = field(default_factory=list)
    invalid_fields: list[str] = field(default_factory=list)
    confidence_score: float = 0.0
    parser_profile_id: str | None = None
    source_system: str = "unknown"
    suggestions: list[str] = field(default_factory=list)
    recognition_items: list[ParserRecognitionItem] = field(default_factory=list)


CORE_FIELDS: tuple[tuple[str, str, tuple[str, ...], str | None], ...] = (
    ("age", "Age", ("age",), None),
    ("sex", "Sex", ("sex",), None),
    ("bp", "BP", ("sbp", "dbp"), None),
    ("ldl_c", "LDL-C", ("ldl_c",), "mg/dL"),
    ("hdl_c", "HDL-C", ("hdl_c",), "mg/dL"),
    ("triglycerides", "TG", ("triglycerides",), "mg/dL"),
    ("a1c", "A1c", ("a1c",), "%"),
    ("egfr", "eGFR", ("egfr",), None),
    ("bmi", "BMI", ("bmi",), None),
    ("smoking", "Smoking", ("smoker", "former_smoker", "pack_years"), None),
    (
        "medications",
        "Meds",
        ("medications_raw", "bp_treated", "ace_arb", "lipid_lowering", "sglt2", "glp1"),
        None,
    ),
)

IMPORTANT_ADD_ON_FIELDS: tuple[tuple[str, str, tuple[str, ...], str | None], ...] = (
    ("apob", "ApoB", ("apob",), "mg/dL"),
    ("lp_a_value", "Lp(a)", ("lp_a_value",), None),
    ("uacr", "UACR", ("uacr",), "mg/g"),
    ("cac", "CAC", ("cac", "cac_not_done"), None),
    ("family_history", "Family history", ("family_history_premature_ascvd",), None),
)

ADVANCED_CONTEXT_FIELDS: tuple[tuple[str, str, tuple[str, ...], str | None], ...] = (
    ("hscrp", "hsCRP", ("hscrp",), "mg/L"),
    ("osa", "OSA", ("osa",), None),
    ("masld", "MASLD", ("masld",), None),
    (
        "inflammatory",
        "Inflammatory disease",
        (
            "inflammatory_disease",
            "rheumatoid_arthritis",
            "sle",
            "psoriasis",
            "inflammatory_arthritis",
            "ibd",
        ),
        None,
    ),
    ("ancestry", "Ancestry", ("south_asian_ancestry", "filipino_ancestry"), None),
    (
        "reproductive",
        "Reproductive markers",
        (
            "early_menopause",
            "premature_menopause",
            "preeclampsia",
            "gestational_hypertension",
            "gestational_diabetes",
            "preterm_delivery",
            "small_for_gestational_age",
            "recurrent_pregnancy_loss",
            "pcos_or_irregular_menses",
            "early_menarche",
        ),
        None,
    ),
)

ALL_RECOGNITION_FIELDS = CORE_FIELDS + IMPORTANT_ADD_ON_FIELDS + ADVANCED_CONTEXT_FIELDS

SUGGESTIONS = {
    "apob": "Add ApoB for atherogenic burden interpretation.",
    "lp_a_value": "Add Lp(a) for inherited lipid-risk context.",
    "uacr": "Include most recent UACR result.",
    "cac": "Include numeric CAC score if available.",
    "family_history": "Use Yes / No / Unknown instead of *** for family history.",
    "a1c": "Use structured A1c table or explicit 'A1c: X.X' line.",
    "medications": "Use a clear Current medications section.",
}

SUGGESTION_PRIORITY = (
    "uacr",
    "apob",
    "cac",
    "family_history",
    "lp_a_value",
    "a1c",
    "medications",
)


def normalize_parse_report(parse_report: ParseReport | dict[str, Any] | None) -> dict[str, Any]:
    """Return canonical parsed/meta/conflict fields from parser or UI reports."""
    if parse_report is None:
        return {"parsed": {}, "meta": {}, "warnings": [], "conflicts": [], "source_style": "unknown"}
    if isinstance(parse_report, ParseReport):
        parsed: dict[str, Any] = {}
        meta: dict[str, Any] = {}
        for field, value in (parse_report.extracted or {}).items():
            canonical = RAW_TO_CANONICAL.get(field, field)
            parsed[canonical] = value
            meta[canonical] = dict((parse_report.field_meta or {}).get(field) or {})
        for field, field_meta in (parse_report.field_meta or {}).items():
            canonical = RAW_TO_CANONICAL.get(field, field)
            meta.setdefault(canonical, dict(field_meta or {}))
        return {
            "parsed": parsed,
            "meta": meta,
            "warnings": list(parse_report.warnings or []),
            "conflicts": list(parse_report.conflicts or []),
            "source_style": getattr(parse_report, "source_style", "unknown"),
        }
    return {
        "parsed": dict(parse_report.get("parsed") or parse_report.get("extracted") or {}),
        "meta": dict(parse_report.get("meta") or parse_report.get("field_meta") or {}),
        "warnings": list(parse_report.get("warnings") or []),
        "conflicts": list(parse_report.get("conflicts") or []),
        "source_style": str(parse_report.get("source_style") or "unknown"),
        "parser_profile_id": parse_report.get("parser_profile_id"),
    }


def _compact(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return str(int(number)) if number.is_integer() else f"{number:g}"


def _field_value(field_id: str, keys: tuple[str, ...], parsed: dict[str, Any], unit: str | None) -> str:
    if field_id == "bp":
        if parsed.get("sbp") is not None and parsed.get("dbp") is not None:
            return f"{_compact(parsed.get('sbp'))}/{_compact(parsed.get('dbp'))}"
        return ""
    if field_id == "smoking":
        if parsed.get("smoker") is True:
            return "Current smoker"
        if parsed.get("former_smoker") is True:
            return "Former smoker"
        if parsed.get("smoker") is False:
            return "Not current"
        return ""
    if field_id == "medications":
        if parsed.get("medications_raw"):
            return "Meds detected"
        labels = []
        for label, key in (
            ("BP meds", "bp_treated"),
            ("ACE/ARB", "ace_arb"),
            ("lipid-lowering", "lipid_lowering"),
            ("SGLT2", "sglt2"),
            ("GLP-1", "glp1"),
        ):
            if parsed.get(key) is True:
                labels.append(label)
        return ", ".join(labels)
    if field_id == "cac":
        return _compact(parsed.get("cac")) if parsed.get("cac") is not None else ""
    if field_id == "family_history":
        value = parsed.get("family_history_premature_ascvd")
        if value is True:
            relationship = str(parsed.get("family_history_relationship") or "").strip().lower()
            event = str(parsed.get("family_history_event_type") or "").strip()
            age = parsed.get("family_history_age_at_event")
            if relationship and event and age not in (None, ""):
                event_label = "MI" if event.lower() == "mi" else event.upper() if len(event) <= 4 else event
                return f"{relationship.title()} {event_label} age {_compact(age)}"
            return "Present"
        if value is False:
            return "Not reported"
        return ""
    if field_id == "inflammatory":
        labels = [
            label
            for label, key in (
                ("RA", "rheumatoid_arthritis"),
                ("SLE", "sle"),
                ("psoriasis", "psoriasis"),
                ("IBD", "ibd"),
                ("inflammatory arthritis", "inflammatory_arthritis"),
                ("inflammatory disease", "inflammatory_disease"),
            )
            if parsed.get(key) is True
        ]
        return ", ".join(labels)
    if field_id == "ancestry":
        labels = []
        if parsed.get("south_asian_ancestry") is True:
            labels.append("South Asian")
        if parsed.get("filipino_ancestry") is True:
            labels.append("Filipino")
        return ", ".join(labels)
    if field_id == "reproductive":
        return "Present" if any(parsed.get(key) is True for key in keys) else ""

    for key in keys:
        value = parsed.get(key)
        if value not in (None, "", False):
            if isinstance(value, bool):
                return "Yes"
            text = _compact(value)
            if field_id == "lp_a_value" and parsed.get("lp_a_unit"):
                return f"{text} {parsed.get('lp_a_unit')}"
            if unit == "%":
                return f"{text}%"
            return f"{text} {unit}" if unit else text
    return ""


def _confidence(keys: tuple[str, ...], meta: dict[str, Any]) -> str:
    for key in keys:
        value = str((meta.get(key) or {}).get("confidence") or "").strip()
        if value:
            return value
    return ""


def _source(keys: tuple[str, ...], meta: dict[str, Any]) -> str:
    for key in keys:
        value = str((meta.get(key) or {}).get("source") or "").strip()
        if value:
            return value
    return ""


def _conflict_fields(conflicts: list[str]) -> set[str]:
    fields = set()
    for conflict in conflicts:
        field = str(conflict).split(":", 1)[0].strip()
        if field:
            fields.add(RAW_TO_CANONICAL.get(field, field))
    return fields


def _status(field_id: str, keys: tuple[str, ...], parsed: dict[str, Any], meta: dict[str, Any], conflicts: set[str]) -> str:
    if any(key in conflicts for key in keys):
        return "invalid"
    confidence_values = {
        str((meta.get(key) or {}).get("confidence") or "").strip().lower()
        for key in keys
        if (meta.get(key) or {}).get("confidence")
    }
    source_text = " ".join(str((meta.get(key) or {}).get("source") or "").lower() for key in keys)
    value = _field_value(field_id, keys, parsed, None)
    if field_id == "cac" and parsed.get("cac_not_done") is True and parsed.get("cac") is None:
        return "review" if "placeholder" in source_text or "***" in source_text else "missing"
    if field_id == "medications" and parsed.get("medications_raw"):
        return "extracted"
    if field_id == "family_history" and parsed.get("family_history_premature_ascvd") is True and value:
        return "extracted"
    if value:
        return "review" if confidence_values & {"uncertain", "inferred"} else "extracted"
    if confidence_values:
        return "missing" if "not found" in confidence_values else "review"
    return "missing"


def build_parser_coverage_report(
    parse_report: ParseReport | dict[str, Any] | None,
    *,
    parser_profile_id: str | None = None,
) -> ParserCoverageReport:
    """Build deterministic parser coverage, recognition, and improvement suggestions."""
    report = normalize_parse_report(parse_report)
    parsed = report["parsed"]
    meta = report["meta"]
    conflicts = _conflict_fields([str(x) for x in report.get("conflicts") or []])
    profile_id = parser_profile_id or report.get("parser_profile_id")

    recognition_items: list[ParserRecognitionItem] = []
    for priority, (field_id, label, keys, unit) in enumerate(ALL_RECOGNITION_FIELDS):
        value = _field_value(field_id, keys, parsed, unit)
        status = _status(field_id, keys, parsed, meta, conflicts)
        recognition_items.append(
            ParserRecognitionItem(
                field_id=field_id,
                label=label,
                value=value,
                status=status,
                confidence=_confidence(keys, meta),
                source_text=_source(keys, meta),
                display_priority=priority,
            )
        )

    core_ids = {field_id for field_id, _label, _keys, _unit in CORE_FIELDS}
    core_items = [item for item in recognition_items if item.field_id in core_ids]
    recognized_core = [item for item in core_items if item.status == "extracted"]
    missing_core = [item.field_id for item in core_items if item.status == "missing"]
    ambiguous = [item.field_id for item in recognition_items if item.status == "review"]
    invalid = [item.field_id for item in recognition_items if item.status == "invalid"]

    weighted = sum(1.0 if item.status == "extracted" else 0.5 if item.status == "review" else 0.0 for item in core_items)
    total_core = len(core_items)
    confidence_score = round(weighted / total_core, 3) if total_core else 0.0

    by_item = {item.field_id: item for item in recognition_items}
    suggestions: list[str] = []
    for item in recognition_items:
        if item.status not in {"review", "invalid"}:
            continue
        tip = SUGGESTIONS.get(item.field_id)
        if tip and tip not in suggestions:
            suggestions.append(tip)
    for field_id in SUGGESTION_PRIORITY:
        item = by_item.get(field_id)
        if item is None:
            continue
        if item.status == "extracted":
            continue
        tip = SUGGESTIONS.get(item.field_id)
        if tip and tip not in suggestions:
            suggestions.append(tip)
    if confidence_score < 0.7:
        suggestions.insert(0, "Use the recommended Epic template structure for stronger parser coverage.")

    return ParserCoverageReport(
        total_core_fields=total_core,
        recognized_core_fields=len(recognized_core),
        missing_core_fields=missing_core,
        ambiguous_fields=ambiguous,
        invalid_fields=invalid,
        confidence_score=confidence_score,
        parser_profile_id=profile_id,
        source_system=str(report.get("source_style") or "unknown"),
        suggestions=suggestions[:5],
        recognition_items=recognition_items,
    )
