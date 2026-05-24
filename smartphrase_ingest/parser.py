from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from smartphrase_ingest.med_vocab import extract_medications_structured


@dataclass
class ParseReport:
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
    "a1c": r"\b(?:a1c|hba1c)\b",
    "egfr": r"\b(?:egfr|e-gfr)\b",
    "uacr": r"\b(?:uacr|acr|urine albumin creatinine ratio)\b",
    "cac": r"\b(?:cac|coronary calcium|calcium score)\b",
    "bmi": r"\bbmi\b",
    "creatinine": r"\b(?:creatinine|cr)\b",
    "hscrp": r"\b(?:hscrp|hs-crp|high sensitivity crp)\b",
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
    r"not\s+assessed|unclear|unable\s+to\s+determine|not\s+reported|missing)"
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


def _extract_unavailable_reason(text: str, label: str) -> str | None:
    if label == "CAC" and re.search(
        r"\bno\s+(?:cac|coronary calcium|calcium score)\s+(?:available|performed|done|reported)\b",
        text,
        re.IGNORECASE,
    ):
        return f"{label} unavailable or not done"
    unavailable_terms = r"not available|unavailable|not done|deferred|unable to calculate|not reported|not performed|unknown|no [a-z ]{0,30}available"
    if label == "CAC":
        label_pattern = r"(?:CAC|coronary calcium|calcium score)"
    elif label == "LDL-C":
        label_pattern = r"(?:LDL-C|LDL|low density lipoprotein)"
    else:
        label_pattern = re.escape(label)
    pattern = rf"\b{label_pattern}\b[^\n.;:]*?\b(?:{unavailable_terms})\b(?:\s*(?:because|due to|reason:?)\s*([^.;\n]+))?"
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        pattern = rf"\b(?:{unavailable_terms})\b[^\n.;:]*?\b{label_pattern}\b(?:\s*(?:because|due to|reason:?)\s*([^.;\n]+))?"
        match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    detail = (match.group(1) or "").strip()
    if detail:
        return f"{label} unavailable: {detail}"
    return f"{label} unavailable or not done"


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
    report = ParseReport()
    if not text:
        return report

    report.source_style = detect_source_style(text)
    lowered = text.lower()

    age_sex_match = re.search(r"\b(\d{2,3})\s*[/\s-]*([mf])\b", text, re.IGNORECASE)
    if age_sex_match:
        _record(report, "age", float(age_sex_match.group(1)), "inferred", "compact age/sex token")
        _record(
            report,
            "sex",
            "male" if age_sex_match.group(2).lower() == "m" else "female",
            "inferred",
            "compact age/sex token",
        )

    age_year_old = re.search(r"\b(\d{2,3})[-\s]*(?:year-old|yo|y/o)\s*(male|female|man|woman|m|f)\b", text, re.IGNORECASE)
    if age_year_old:
        _record(report, "age", float(age_year_old.group(1)), "parsed", "age/sex prose")
        sex_value = age_year_old.group(2).lower()
        _record(report, "sex", "male" if sex_value in {"m", "male", "man"} else "female", "parsed", "age/sex prose")

    age_explicit = re.search(r"\bage\s*(?:=|:)?\s*(\d{2,3})\b", text, re.IGNORECASE)
    if age_explicit and "age" not in report.extracted:
        age_context = text[max(0, age_explicit.start() - 24): age_explicit.start()].lower()
        if re.search(r"\b(?:menopause|menopausal|menarche)\b", age_context):
            age_explicit = None
    if age_explicit and "age" not in report.extracted:
        _record(report, "age", float(age_explicit.group(1)), "parsed", "explicit age")

    sex_match = re.search(r"\b(?:sex|gender)\s*(?:=|:|is)?\s*(male|female|m|f)\b", text, re.IGNORECASE)
    if sex_match:
        sex = sex_match.group(1).lower()
        _record(report, "sex", "male" if sex == "m" else "female" if sex == "f" else sex, "parsed", "explicit sex")

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

    for field, label_pattern in NUMERIC_PATTERNS.items():
        if field in report.extracted:
            continue
        value = _parse_number_after_label(text, label_pattern)
        if value is not None:
            _record(report, field, value, "parsed", "labeled value")

    actual_a1c = re.search(r"\bactual\s+(?:a1c|hba1c)\s*(?:=|:)?\s*(\d+(?:\.\d+)?)\b", text, re.IGNORECASE)
    if actual_a1c:
        _record(report, "a1c", float(actual_a1c.group(1)), "parsed", "actual A1c")

    apob_explicit = re.search(r"\b(?:apob|apo\s*b|apolipoprotein\s*b)\s*(?:=|:|\|)?\s*(\d+(?:\.\d+)?)\b", text, re.IGNORECASE)
    if apob_explicit:
        _record(report, "apob", float(apob_explicit.group(1)), "parsed", "ApoB")

    alb_cr = re.search(r"\b(?:albumin/creatinine|alb/cr|microalbumin/creatinine|microalbumin creatinine)\s*(?:ratio)?\s*(?:=|:|-|\|)?\s*(\d+(?:\.\d+)?)", text, re.IGNORECASE)
    if alb_cr and "uacr" not in report.extracted:
        _record(report, "uacr", float(alb_cr.group(1)), "parsed", "albumin/creatinine ratio")

    agatston = re.search(r"\b(?:agatston(?:\s+score)?|coronary artery calcium score)\s*(?:=|:|-)?\s*(\d+(?:\.\d+)?)", text, re.IGNORECASE)
    if agatston and "cac" not in report.extracted:
        _record(report, "cac", float(agatston.group(1)), "parsed", "Agatston/CAC score")

    lpa_match = re.search(r"\b(?:lp\(a\)|lpa|lp a|lipoprotein\s*\(a\))\s*(?:=|:|is|\|)?\s*([<>]?\s*\d+(?:\.\d+)?)\s*(nmol/L|mg/dL)?", text, re.IGNORECASE)
    if lpa_match:
        _record(report, "lpa", float(lpa_match.group(1).replace(" ", "").lstrip("<>")), "parsed", "Lp(a)")
        if lpa_match.group(2):
            unit = lpa_match.group(2).lower()
            _record(report, "lpa_unit", "nmol/L" if unit == "nmol/l" else "mg/dL", "parsed", "Lp(a) unit")
        else:
            report.field_meta["lpa_unit"] = {
                "confidence": "uncertain",
                "source": "Lp(a) value present but unit missing",
            }
            report.warnings.append("Lp(a) value parsed without units; please review nmol/L vs mg/dL.")

    for field, label in (("egfr", "eGFR"), ("uacr", "UACR"), ("cac", "CAC"), ("ldl", "LDL-C")):
        if field not in report.extracted:
            reason = _extract_unavailable_reason(text, label)
            if reason:
                _mark_unavailable(report, field, reason, label)
                if field == "cac":
                    report.extracted["cac"] = None
                    _record(report, "cac_not_done", True, "parsed", reason)

    _parse_height_weight_bmi(report, text)

    fhx_match = re.search(
        r"\b(father|mother|brother|sister)\s+"
        r"(MI|PCI/CABG|PCI|CABG|stroke|sudden cardiac death|SCD)"
        r"\s+(?:at\s+)?(?:age\s+)?(\d{2,3})\b",
        text,
        re.IGNORECASE,
    )
    explicit_premature_fhx_found, explicit_premature_fhx = _parse_explicit_bool_line_status(
        text,
        [
            r"premature\s+family\s+history",
            r"premature\s+ascvd\s+in\s+first[-\s]?degree\s+relative",
            r"premature\s+first[-\s]?degree\s+(?:family\s+)?history",
            r"family\s+history",
        ],
    )
    if fhx_match:
        relationship = fhx_match.group(1).lower()
        event_age = float(fhx_match.group(3))
        premature = _premature_family_history_from_event(relationship, event_age)
        if explicit_premature_fhx is not None and explicit_premature_fhx != premature:
            report.conflicts.append(
                "Family history conflict: explicit premature flag differs from event age."
            )
        _record(report, "fhx", premature, "inferred", "structured family history")
        _record(report, "fhx_text", fhx_match.group(0), "parsed", "family history")
        _record(report, "family_history_relationship", relationship, "parsed", "family history")
        event = fhx_match.group(2).lower()
        if event in {"pci", "cabg"}:
            event = "PCI/CABG"
        elif event == "scd":
            event = "sudden cardiac death"
        _record(report, "family_history_event_type", event, "parsed", "family history")
        _record(report, "family_history_age_at_event", event_age, "parsed", "family history")
    elif explicit_premature_fhx_found:
        _record(report, "fhx", explicit_premature_fhx, "parsed", "explicit premature family history")
    elif re.search(r"\bfamily history\b|\bfhx\b", text, re.IGNORECASE):
        report.field_meta["fhx"] = {
            "confidence": "uncertain",
            "source": "family history mentioned without complete relationship/event/age",
        }
        report.warnings.append("Family history mentioned but relationship, event, or age was incomplete.")

    diabetes_text = _without_gestational_diabetes_context(text)
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
        "sle": [r"sle", r"lupus"],
        "psoriasis": [r"psoriasis"],
        "ibd": [r"ibd", r"inflammatory\s+bowel\s+disease", r"crohn'?s", r"ulcerative\s+colitis"],
        "hiv": [r"hiv"],
        "osa": [r"osa", r"obstructive\s+sleep\s+apnea", r"sleep\s+apnea"],
        "masld": [r"masld", r"nafld", r"fatty\s+liver", r"metabolic\s+dysfunction-associated\s+steatotic\s+liver\s+disease"],
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
            confidence = "inferred" if field in {"bpTreated", "lipidLowering", "sglt2", "glp1", "ace_arb"} else "parsed"
            _record(report, field, value, confidence, "explicit boolean line")

    clinical_found, clinical_ascvd_value = _parse_explicit_bool_line_status(
        text,
        [r"clinical\s+ascvd", r"personal\s+ascvd", r"known\s+ascvd", r"ascvd"],
    )
    if not clinical_found:
        clinical_ascvd_value = _clinical_ascvd_explicit_bool(text)
    if clinical_found or clinical_ascvd_value is not None:
        _record(report, "ascvd_clinical", clinical_ascvd_value, "parsed", "explicit clinical ASCVD line")
        if clinical_ascvd_value is True:
            context = _clinical_ascvd_context(text)
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
        value = _bool_from_text(lowered, positive, negative)
        if value is not None:
            confidence = "inferred" if field in {"bpTreated", "lipidLowering", "sglt2", "glp1", "ace_arb"} else "parsed"
            _record(report, field, value, confidence, "text pattern")
            if field == "ascvd_clinical" and value is True:
                context = _clinical_ascvd_context(text)
                if context:
                    _record(report, "clinical_ascvd_context", context, "parsed", "clinical ASCVD event/procedure")

    ascvd_events = extract_ascvd_events(text)
    if "ascvd_clinical" not in report.extracted and ascvd_events["clinical_ascvd"] is not None:
        _record(report, "ascvd_clinical", ascvd_events["clinical_ascvd"], "parsed", "structured ASCVD event extraction")
    if ascvd_events["event_summary"] and "clinical_ascvd_context" not in report.extracted:
        _record(report, "clinical_ascvd_context", ascvd_events["event_summary"], "parsed", "structured ASCVD event extraction")

    for field in ("rheumatoid_arthritis", "sle", "psoriasis", "ibd", "hiv", "osa", "masld"):
        if field in report.extracted:
            continue
        value = _keyword_present_without_explicit_negation(text, explicit_bool_labels[field])
        if value is True:
            _record(report, field, True, "parsed", "condition mention")

    specific_inflammatory_present = any(
        report.extracted.get(key) is True
        for key in ("rheumatoid_arthritis", "sle", "psoriasis", "ibd")
    )
    if specific_inflammatory_present:
        if report.extracted.get("inflammatory_disease") is False:
            report.conflicts.append(
                "Inflammatory disease conflict: specific condition present despite generic inflammatory disease marked No."
            )
            report.extracted["inflammatory_disease"] = True
            report.field_meta["inflammatory_disease"] = {
                "confidence": "inferred",
                "source": "specific inflammatory condition",
            }
        elif "inflammatory_disease" not in report.extracted:
            _record(report, "inflammatory_disease", True, "inferred", "specific inflammatory condition")

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
    return parse_smartphrase_report(text)
