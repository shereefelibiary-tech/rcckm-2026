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
    "age": r"\bage\b",
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


def parse_explicit_bool_line(raw: str, labels: list[str]) -> bool | None:
    """Parse explicit yes/no condition lines without treating label mentions as positive."""
    if not raw or not labels:
        return None

    label = _label_regex(labels)
    negative_value = r"(?:no|false|absent|negative|none|never|denies|denied|not present)"
    positive_value = r"(?:yes|true|present|positive|active)"
    negative_prefix = r"(?:no|denies|denied|without|negative for|absent|no history of|not present)"
    positive_prefix = r"(?:has|with|known|history of|hx of|diagnosed with|positive for|present)"

    for segment in _bool_segments(raw):
        if not re.search(rf"\b{label}\b", segment, re.IGNORECASE):
            continue

        negative_patterns = [
            rf"\b{label}\b\s*(?:=|:|-|is|was)?\s*{negative_value}\b",
            rf"\b{negative_prefix}\b[^\n.;]*\b{label}\b",
            rf"\b{label}\b[^\n.;]*\b(?:negative|absent|denied|none|not present)\b",
        ]
        if any(re.search(pattern, segment, re.IGNORECASE) for pattern in negative_patterns):
            return False

        positive_patterns = [
            rf"\b{label}\b\s*(?:=|:|-|is|was)?\s*{positive_value}\b",
            rf"\b{positive_prefix}\b[^\n.;]*\b{label}\b",
        ]
        if any(re.search(pattern, segment, re.IGNORECASE) for pattern in positive_patterns):
            return True

    return None


def _keyword_present_without_explicit_negation(raw: str, labels: list[str]) -> bool | None:
    if not raw or not labels:
        return None

    label = _label_regex(labels)
    for segment in _bool_segments(raw):
        if not re.search(rf"\b{label}\b", segment, re.IGNORECASE):
            continue
        negative_patterns = [
            rf"\b{label}\b\s*(?:=|:|-|is|was)?\s*(?:no|false|absent|negative|none|never|denies|denied|not present)\b",
            rf"\b(?:no|denies|denied|without|negative for|absent|no history of|not present)\b[^\n.;]*\b{label}\b",
            rf"\b{label}\b[^\n.;]*\b(?:negative|absent|denied|none|not present)\b",
        ]
        if any(re.search(pattern, segment, re.IGNORECASE) for pattern in negative_patterns):
            return False
        return True
    return None


def _clinical_ascvd_explicit_bool(raw: str) -> bool | None:
    labels = [
        r"clinical\s+ascvd",
        r"personal\s+ascvd",
        r"known\s+ascvd",
        r"prior\s+mi",
        r"prior\s+stroke",
        r"history\s+of\s+cva",
        r"pad",
    ]
    for segment in _bool_segments(raw):
        if re.search(r"\b(?:family history|fhx|father|mother|brother|sister)\b", segment, re.IGNORECASE):
            continue
        value = parse_explicit_bool_line(segment, labels)
        if value is not None:
            return value
    return None


def _clinical_ascvd_context(raw: str) -> str:
    text = raw or ""
    parts: list[str] = []
    if re.search(r"\bnstemi\b", text, re.IGNORECASE):
        parts.append("prior NSTEMI")
    elif re.search(r"\bstemi\b", text, re.IGNORECASE):
        parts.append("prior STEMI")
    elif re.search(r"\b(?:prior|history of|hx of)\s+(?:mi|myocardial infarction)\b", text, re.IGNORECASE):
        parts.append("prior MI")

    if re.search(r"\b(?:pci|percutaneous coronary intervention)\b", text, re.IGNORECASE) and re.search(
        r"\b(?:stent|stents|des)\b", text, re.IGNORECASE
    ):
        parts.append("PCI/stent")
    elif re.search(r"\b(?:pci|percutaneous coronary intervention)\b", text, re.IGNORECASE):
        parts.append("PCI")
    elif re.search(r"\b(?:stent|stents|des)\b", text, re.IGNORECASE):
        parts.append("coronary stent")

    if re.search(r"\bcabg\b", text, re.IGNORECASE):
        parts.append("CABG")
    if re.search(r"\b(?:prior|history of|hx of)\s+(?:stroke|cva)\b", text, re.IGNORECASE):
        parts.append("prior stroke")
    if re.search(r"\b(?:pad|peripheral artery disease)\b", text, re.IGNORECASE):
        parts.append("PAD")

    return " and ".join(dict.fromkeys(parts))


def _extract_unavailable_reason(text: str, label: str) -> str | None:
    if label == "CAC" and re.search(
        r"\bno\s+(?:cac|coronary calcium|calcium score)\s+(?:available|performed|done|reported)\b",
        text,
        re.IGNORECASE,
    ):
        return f"{label} unavailable or not done"
    unavailable_terms = r"not available|unavailable|not done|deferred|unable to calculate|not reported|not performed|unknown|no [a-z ]{0,30}available"
    label_pattern = r"(?:CAC|coronary calcium|calcium score)" if label == "CAC" else re.escape(label)
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

    inactive_mentions = [
        f"{m.get('normalized_name')} {str(m.get('source_line') or '').strip()}"
        for m in detected
        if m.get("active") is False
    ]
    for mention in inactive_mentions:
        report.warnings.append(f"Medication mentioned but not counted as active: {mention}.")


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

    for field, label in (("egfr", "eGFR"), ("uacr", "UACR"), ("cac", "CAC")):
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
    if fhx_match:
        _record(report, "fhx", True, "inferred", "structured family history")
        _record(report, "fhx_text", fhx_match.group(0), "parsed", "family history")
        _record(report, "family_history_relationship", fhx_match.group(1).lower(), "parsed", "family history")
        event = fhx_match.group(2).lower()
        if event in {"pci", "cabg"}:
            event = "PCI/CABG"
        elif event == "scd":
            event = "sudden cardiac death"
        _record(report, "family_history_event_type", event, "parsed", "family history")
        _record(report, "family_history_age_at_event", float(fhx_match.group(3)), "parsed", "family history")
    elif re.search(r"\bfamily history\b|\bfhx\b", text, re.IGNORECASE):
        report.field_meta["fhx"] = {
            "confidence": "uncertain",
            "source": "family history mentioned without complete relationship/event/age",
        }
        report.warnings.append("Family history mentioned but relationship, event, or age was incomplete.")

    diabetes_explicit = parse_explicit_bool_line(
        text,
        [r"type\s+2\s+diabetes", r"diabetes", r"dm2", r"t2dm"],
    )
    diabetes_positive = bool(
        re.search(
            r"\b(?:has|history of|hx of|known|with|treated for|type 2|t2dm|dm2)\s+(?:diabetes|dm2|t2dm|type 2 diabetes)\b",
            lowered,
        )
    )
    if diabetes_explicit is False:
        _record(report, "diabetes", False, "parsed", "diabetes negation")
        if "a1c" in report.extracted and report.extracted["a1c"] >= 6.5:
            report.conflicts.append("diabetes: text says no diabetes but A1c is >=6.5")
    elif diabetes_explicit is True or diabetes_positive:
        _record(report, "diabetes", True, "parsed", "diabetes text")
    elif "a1c" in report.extracted and report.extracted["a1c"] >= 6.5:
        _record(report, "diabetes", True, "inferred", "A1c >=6.5")

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
    }
    for field, labels in explicit_bool_labels.items():
        value = parse_explicit_bool_line(text, labels)
        if value is not None:
            confidence = "inferred" if field in {"bpTreated", "lipidLowering", "sglt2", "glp1", "ace_arb"} else "parsed"
            _record(report, field, value, confidence, "explicit boolean line")

    clinical_ascvd_value = _clinical_ascvd_explicit_bool(text)
    if clinical_ascvd_value is not None:
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

    for field in ("rheumatoid_arthritis", "sle", "psoriasis", "ibd", "hiv", "osa", "masld"):
        if field in report.extracted:
            continue
        value = _keyword_present_without_explicit_negation(text, explicit_bool_labels[field])
        if value is True:
            _record(report, field, True, "parsed", "condition mention")

    if any(report.extracted.get(key) is True for key in ("rheumatoid_arthritis", "sle", "psoriasis", "ibd", "hiv")):
        _record(report, "inflammatory_disease", True, "inferred", "inflammatory/immune condition")

    _parse_medications(report, text)

    if re.search(r"\bfasting\b", lowered) and re.search(r"\b(?:lipids|lipid panel|tc|ldl|hdl|tg)\b", lowered):
        _record(report, "fasting_lipids", True, "parsed", "fasting lipid language")
    if re.search(r"\bnon[-\s]?fasting\b", lowered) and re.search(r"\b(?:lipids|lipid panel|tg|triglycerides)\b", lowered):
        _record(report, "fasting_lipids", False, "parsed", "nonfasting lipid language")

    if text.strip() and not report.extracted and not report.field_meta:
        report.warnings.append("No supported RCCKM fields were confidently parsed from pasted text.")

    return report


def parse_smartphrase(text: str) -> ParseReport:
    return parse_smartphrase_report(text)
