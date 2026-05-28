from __future__ import annotations

import re
from typing import Iterable

from smartphrase_ingest.med_vocab import extract_medications_structured
from smartphrase_ingest.models import ExtractedCandidate
from smartphrase_ingest.preprocess import is_placeholder_value
from smartphrase_ingest.sections import TextSection


def _candidate(field, value, source_text, section, *, unit=None, date=None, confidence=0.9, reason=""):
    return ExtractedCandidate(
        field_name=field,
        value=value,
        unit=unit,
        date=date,
        source_text=source_text.strip(),
        source_section=section,
        confidence=confidence,
        reason=reason,
    )


def _lines(sections: dict[str, TextSection], names: Iterable[str] = ("all",)) -> list[str]:
    seen = []
    used = set()
    for name in names:
        section = sections.get(name)
        if not section:
            continue
        for line in section.text.splitlines():
            clean = line.strip()
            if clean and clean not in used:
                used.add(clean)
                seen.append(clean)
    return seen


def _first_number(text: str) -> float | None:
    match = re.search(r"[<>]?\s*(\d+(?:\.\d+)?)", text)
    if not match:
        return None
    return float(match.group(1))


def extract_demographics(sections):
    out = []
    text = sections["all"].text
    age_sex = re.search(r"\b(\d{2,3})[-\s]*(?:year-old|yo|y/o)?\s*(male|female|man|woman|m|f)\b", text, re.IGNORECASE)
    if age_sex:
        sex_token = age_sex.group(2).lower()
        out.append(_candidate("age", float(age_sex.group(1)), age_sex.group(0), "demographics", confidence=0.95, reason="age/sex phrase"))
        out.append(_candidate("sex", "male" if sex_token in {"m", "male", "man"} else "female", age_sex.group(0), "demographics", confidence=0.95, reason="age/sex phrase"))
    return out


def extract_smoking(sections):
    out = []
    for line in _lines(sections, ("smoking", "all")):
        status = re.search(r"\bsmoking\s+status\s*(?:=|:)?\s*(current|former|never|none|not current)\b", line, re.IGNORECASE)
        if status:
            value = status.group(1).lower()
            out.append(_candidate("smoker", value == "current", line, "smoking", confidence=0.95, reason="explicit smoking status"))
            if value == "former":
                out.append(_candidate("former_smoker", True, line, "smoking", confidence=0.95, reason="former smoking status"))
        pack_years = re.search(r"\b(\d+(?:\.\d+)?)\s*pack[-\s]?years?\b", line, re.IGNORECASE)
        if pack_years:
            out.append(_candidate("pack_years", float(pack_years.group(1)), line, "smoking", confidence=0.9, reason="pack-year phrase"))
    return out


def extract_blood_pressure(sections):
    out = []
    for line in _lines(sections, ("vitals", "all")):
        dated = re.search(r"\b(\d{1,2}/\d{1,2}/\d{2,4})\s+(\d{2,3})\s*/\s*(\d{2,3})\b", line)
        if dated:
            out.append(_candidate("bp_pair", (float(dated.group(2)), float(dated.group(3))), line, "vitals", date=dated.group(1), confidence=0.95, reason="dated BP reading"))
            continue
        labeled = re.search(r"\b(?:bp|blood pressure)\s*(?:=|:)?\s*(\d{2,3})\s*/\s*(\d{2,3})\b", line, re.IGNORECASE)
        if labeled:
            out.append(_candidate("bp_pair", (float(labeled.group(1)), float(labeled.group(2))), line, "vitals", confidence=0.9, reason="labeled BP reading"))
    return out


def extract_bmi(sections):
    out = []
    for line in _lines(sections, ("bmi", "all")):
        if re.search(r"\b(?:estimated\s+)?body mass index\b", line, re.IGNORECASE):
            value = _first_number(line)
            if value is not None:
                out.append(_candidate("bmi", value, line, "bmi", unit="kg/m2", confidence=0.9, reason="calculated BMI prose"))
        elif re.search(r"\bbmi\b", line, re.IGNORECASE):
            tail = line.split(":", 1)[-1] if ":" in line else line
            if is_placeholder_value(tail):
                continue
            value = _first_number(tail)
            if value is not None:
                out.append(_candidate("bmi", value, line, "bmi", unit="kg/m2", confidence=0.85, reason="labeled BMI"))
    return out


def _extract_lab_value(sections, field, labels, section_name, *, unit=None, confidence=0.95):
    out = []
    pending_label = None
    for line in _lines(sections, (section_name, "labs", "all")):
        clean = line.strip()
        if re.search(r"\b(?:reference|normal|prediabetes|diabetes\s*[>=]|no results found|not available|unavailable)\b", clean, re.IGNORECASE):
            continue
        matched = any(re.search(label, clean, re.IGNORECASE) for label in labels)
        active = matched or pending_label
        if not active:
            continue
        clean_for_values = re.sub(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", " ", clean)
        if matched:
            for label in labels:
                clean_for_values = re.sub(label, " ", clean_for_values, flags=re.IGNORECASE)
        value = _first_number(clean_for_values)
        if value is not None:
            out.append(_candidate(field, value, line, section_name, unit=unit, confidence=confidence, reason="lab result"))
            pending_label = None
        elif matched:
            pending_label = True
    return out


def extract_lipids(sections):
    specs = (
        ("tc", (r"\b(?:TC|CHOL(?:ESTEROL)?|TOTAL\s+CHOLESTEROL)\b",)),
        ("triglycerides", (r"\b(?:TG|TRIG(?:LYCERIDES)?)\b",)),
        ("hdl_c", (r"\bHDL\b",)),
        ("ldl_c", (r"\bLDL\b",)),
    )
    out = []
    for field, labels in specs:
        out.extend(_extract_lab_value(sections, field, labels, "lipids", unit="mg/dL"))
    return out


def extract_a1c(sections):
    return _extract_lab_value(sections, "a1c", (r"\b(?:A1C|HBA1C|HEMOGLOBIN\s+A1C)\b",), "a1c", unit="%")


def extract_apob(sections):
    return _extract_lab_value(sections, "apob", (r"\b(?:APOB|Apo\s*B|apolipoprotein\s*B)\b",), "lipids", unit="mg/dL")


def extract_lpa(sections):
    out = []
    for line in _lines(sections, ("lipids", "all")):
        match = re.search(r"\b(?:Lp\(a\)|LIPOA|lipoprotein\s*\(a\))\b[^\n]*?([<>]?\s*\d+(?:\.\d+)?)\s*(nmol/L|mg/dL)?", line, re.IGNORECASE)
        if match and "no results found" not in line.lower():
            out.append(_candidate("lp_a_value", float(match.group(1).replace(" ", "").lstrip("<>")), line, "lipids", unit=match.group(2), confidence=0.9, reason="Lp(a) result"))
    return out


def extract_hscrp(sections):
    return _extract_lab_value(sections, "hscrp", (r"\b(?:hsCRP|hs-CRP|CRPHS)\b",), "labs", unit="mg/L")


def extract_egfr(sections):
    out = []
    for line in _lines(sections, ("kidney", "labs", "all")):
        if re.search(r"\b(?:crcl|creatinine\s+clearance)\b", line, re.IGNORECASE):
            continue
        if re.search(r"\b(?:LABGLOM|eGFR\s+Cre|eGFR(?:\s+CREATININE)?)\b", line, re.IGNORECASE):
            value = _first_number(re.sub(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", " ", line))
            if value is not None:
                out.append(_candidate("egfr", value, line, "kidney", confidence=0.95, reason="eGFR lab result"))
    return out


def extract_uacr(sections):
    return _extract_lab_value(sections, "uacr", (r"\b(?:UACR|urine\s+ACR|ALBCREAT|albumin/creatinine)\b",), "kidney", unit="mg/g")


def extract_cac(sections):
    out = []
    for line in _lines(sections, ("imaging", "all")):
        if re.search(r"\b(?:CAC|coronary(?:\s+artery)?\s+calcium|calcium score)\b", line, re.IGNORECASE):
            tail = line.split(":", 1)[-1] if ":" in line else line
            if is_placeholder_value(tail):
                continue
            value = _first_number(tail)
            if value is not None:
                out.append(_candidate("cac", value, line, "imaging", confidence=0.95, reason="numeric CAC"))
    return out


def extract_medications(sections):
    text = sections["all"].text
    structured = extract_medications_structured(text)
    out = []
    if structured.get("bpTreated") is True:
        out.append(_candidate("bp_treated", True, "medication vocabulary", "medications", confidence=0.85, reason="active antihypertensive medication"))
    if structured.get("ace_arb") is True:
        out.append(_candidate("ace_arb", True, "medication vocabulary", "medications", confidence=0.85, reason="active ACEi/ARB medication"))
    if structured.get("lipidLowering") is True:
        out.append(_candidate("lipid_lowering", True, "medication vocabulary", "medications", confidence=0.85, reason="active lipid-lowering medication"))
    for field in ("sglt2", "glp1"):
        if structured.get(field) is True:
            out.append(_candidate(field, True, "medication vocabulary", "medications", confidence=0.85, reason=f"active {field.upper()} medication"))
    return out


def extract_family_history(sections):
    out = []
    text = sections["all"].text
    explicit = re.search(r"\bpremature\s+ascvd\s+in\s+first[-\s]?degree\s+relative\s*(?:=|:)?\s*(yes|no|\*{2,}|@[A-Z0-9_]+@)\b", text, re.IGNORECASE)
    if explicit:
        token = explicit.group(1).lower()
        if token in {"yes", "no"}:
            out.append(_candidate("premature_fhx_ascvd", token == "yes", explicit.group(0), "family_history", confidence=0.95, reason="explicit family history field"))
        return out
    event = re.search(r"\b(father|mother|brother|sister)\s+(MI|PCI/CABG|PCI|CABG|stroke)\s+(?:at\s+)?(?:age\s+)?(\d{2,3})\b", text, re.IGNORECASE)
    if event:
        relationship = event.group(1).lower()
        age = float(event.group(3))
        premature = (relationship in {"father", "brother"} and age < 55) or (relationship in {"mother", "sister"} and age < 65)
        out.append(_candidate("premature_fhx_ascvd", premature, event.group(0), "family_history", confidence=0.9, reason="relationship/event/age family history"))
    return out


EXTRACTORS = (
    extract_demographics,
    extract_smoking,
    extract_blood_pressure,
    extract_bmi,
    extract_lipids,
    extract_a1c,
    extract_apob,
    extract_lpa,
    extract_hscrp,
    extract_egfr,
    extract_uacr,
    extract_cac,
    extract_medications,
    extract_family_history,
)
