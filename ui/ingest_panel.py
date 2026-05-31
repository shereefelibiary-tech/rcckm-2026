from dataclasses import dataclass
import html
import re
import time
import uuid

from renderers.parse_coverage import render_parse_coverage
from modules.family_history.engine import infer_compact_family_history_option
from smartphrase_ingest.coverage import build_parser_coverage_report
from smartphrase_ingest.parser import ParseReport, parse_smartphrase_report
from smartphrase_ingest.profiles import ParserProfile, apply_profile_hints
from ui.html import render_component_html, render_html
from ui.report_state import clear_report_state, hash_text
from ui.theme import section_heading

PARSER_FIELD_TO_WORKSHEET_FIELD = {
    "ldl": "ldl_c",
    "hdl": "hdl_c",
    "tg": "triglycerides",
    "lpa": "lp_a_value",
    "lpa_unit": "lp_a_unit",
    "fhx": "family_history_premature_ascvd",
    "ascvd_clinical": "clinical_ascvd",
    "bpTreated": "bp_treated",
    "lipidLowering": "lipid_lowering",
}

WORKSHEET_KEY_BY_FIELD = {
    "age": "input_age",
    "sex": "input_sex",
    "sbp": "input_sbp",
    "dbp": "input_dbp",
    "tc": "input_tc",
    "ldl_c": "input_ldl_c",
    "hdl_c": "input_hdl_c",
    "triglycerides": "input_triglycerides",
    "apob": "input_apob",
    "lp_a_value": "input_lp_a_value",
    "lp_a_unit": "input_lp_a_unit",
    "a1c": "input_a1c",
    "diabetes": "input_diabetes",
    "diabetes_duration_years": "input_diabetes_duration_years",
    "diabetic_retinopathy": "input_diabetic_retinopathy",
    "diabetic_neuropathy": "input_diabetic_neuropathy",
    "abi": "input_abi",
    "abi_lt_0_9": "input_abi_lt_0_9",
    "bmi": "input_bmi",
    "egfr": "input_egfr",
    "uacr": "input_uacr",
    "cac": "input_cac",
    "cac_not_done": "input_cac_not_done",
    "clinical_ascvd": "input_clinical_ascvd",
    "clinical_ascvd_context": "input_clinical_ascvd_context",
    "clinical_ascvd_review": "input_clinical_ascvd_review",
    "smoker": "input_smoker",
    "family_history_premature_ascvd": "input_family_history_premature_ascvd",
    "family_history_relationship": "input_family_history_relationship",
    "family_history_event_type": "input_family_history_event_type",
    "family_history_age_at_event": "input_family_history_age_at_event",
    "early_menopause": "input_early_menopause",
    "menopause_age": "input_menopause_age",
    "premature_menopause": "input_premature_menopause",
    "preeclampsia": "input_preeclampsia",
    "gestational_hypertension": "input_gestational_hypertension",
    "gestational_diabetes": "input_gestational_diabetes",
    "preterm_delivery": "input_preterm_delivery",
    "small_for_gestational_age": "input_small_for_gestational_age",
    "recurrent_pregnancy_loss": "input_recurrent_pregnancy_loss",
    "pcos_or_irregular_menses": "input_pcos_or_irregular_menses",
    "early_menarche": "input_early_menarche",
    "menarche_age": "input_menarche_age",
    "hscrp": "input_hscrp",
    "inflammatory_disease": "input_inflammatory_disease",
    "rheumatoid_arthritis": "input_rheumatoid_arthritis",
    "sle": "input_sle",
    "psoriasis": "input_psoriasis",
    "inflammatory_arthritis": "input_inflammatory_arthritis",
    "ibd": "input_ibd",
    "hiv": "input_hiv",
    "stable_art": "input_stable_art",
    "osa": "input_osa",
    "masld": "input_masld",
    "south_asian_ancestry": "input_south_asian_ancestry",
    "filipino_ancestry": "input_filipino_ancestry",
    "active_cancer": "input_active_cancer",
    "cancer_survivor": "input_cancer_survivor",
    "cancer_life_expectancy_gt_2y": "input_cancer_life_expectancy_gt_2y",
    "suspected_fh_hefh": "input_suspected_fh_hefh",
    "incidental_cac": "input_incidental_cac",
    "incidental_cac_severity": "input_incidental_cac_severity",
    "breast_arterial_calcification": "input_breast_arterial_calcification",
    "cac_percentile": "input_cac_percentile",
    "lipid_lowering": "input_lipid_lowering",
    "bp_treated": "input_bp_treated",
    "sglt2": "input_sglt2",
    "glp1": "input_glp1",
    "ace_arb": "input_ace_arb",
}

EXTRA_SESSION_KEY_BY_FIELD = {
    "medications_raw": "input_medications_raw",
    "dm_meds_raw": "input_dm_meds_raw",
    "statin_intensity": "input_statin_intensity",
    "statin_intolerance": "input_statin_intolerance",
    "fasting_lipids": "input_fasting_lipids",
    "fhx_text": "input_fhx_text",
}

INTEGER_WORKSHEET_FIELDS = {
    "age",
    "sbp",
    "dbp",
    "tc",
    "ldl_c",
    "hdl_c",
    "non_hdl_c",
    "triglycerides",
    "apob",
    "lp_a_value",
    "cac",
    "cac_not_done",
    "uacr",
    "egfr",
    "diabetes_duration_years",
    "family_history_age_at_event",
    "menopause_age",
    "menarche_age",
}

ONE_DECIMAL_WORKSHEET_FIELDS = {"a1c", "bmi", "hscrp"}
TWO_DECIMAL_WORKSHEET_FIELDS = {"creatinine"}
PARSER_CONTROLLED_SESSION_KEYS = (
    set(WORKSHEET_KEY_BY_FIELD.values())
    | set(EXTRA_SESSION_KEY_BY_FIELD.values())
    | {
        "input_bp_meds",
        "input_ancestry_context",
        "input_family_history_pattern",
        "input_family_history_helper",
        "input_family_history_summary",
    }
)

PARSER_APPLY_METADATA_KEYS = (
    "parsed_ingest",
    "parse_report",
    "parsed_needs_review",
    "parse_recognition_html",
    "parse_recognition_visible",
    "last_parsed_text_hash",
    "_worksheet_field_sources",
)

BOOLEAN_WORKSHEET_FIELDS = {
    "diabetes",
    "diabetic_retinopathy",
    "diabetic_neuropathy",
    "abi_lt_0_9",
    "clinical_ascvd",
    "smoker",
    "family_history_premature_ascvd",
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
    "inflammatory_disease",
    "rheumatoid_arthritis",
    "sle",
    "psoriasis",
    "inflammatory_arthritis",
    "ibd",
    "hiv",
    "stable_art",
    "osa",
    "masld",
    "south_asian_ancestry",
    "filipino_ancestry",
    "active_cancer",
    "cancer_survivor",
    "cancer_life_expectancy_gt_2y",
    "suspected_fh_hefh",
    "incidental_cac",
    "cac_not_done",
    "clinical_ascvd_review",
    "lipid_lowering",
    "bp_treated",
    "sglt2",
    "glp1",
    "ace_arb",
    "statin_intolerance",
}

PARSER_CONTROLLED_BOOLEAN_FIELDS = tuple(sorted(BOOLEAN_WORKSHEET_FIELDS))

REVIEW_FIELDS = [
    "age",
    "sex",
    "sbp",
    "dbp",
    "tc",
    "ldl_c",
    "hdl_c",
    "triglycerides",
    "apob",
    "lp_a_value",
    "lp_a_unit",
    "a1c",
    "diabetes",
    "diabetes_duration_years",
    "diabetic_retinopathy",
    "diabetic_neuropathy",
    "abi",
    "abi_lt_0_9",
    "bmi",
    "egfr",
    "uacr",
    "cac",
    "clinical_ascvd",
    "clinical_ascvd_context",
    "clinical_ascvd_review",
    "smoker",
    "family_history_premature_ascvd",
    "family_history_relationship",
    "family_history_event_type",
    "family_history_age_at_event",
    "early_menopause",
    "menopause_age",
    "premature_menopause",
    "preeclampsia",
    "gestational_hypertension",
    "gestational_diabetes",
    "preterm_delivery",
    "small_for_gestational_age",
    "recurrent_pregnancy_loss",
    "pcos_or_irregular_menses",
    "early_menarche",
    "menarche_age",
    "hscrp",
    "inflammatory_disease",
    "rheumatoid_arthritis",
    "sle",
    "psoriasis",
    "inflammatory_arthritis",
    "ibd",
    "hiv",
    "stable_art",
    "osa",
    "masld",
    "south_asian_ancestry",
    "filipino_ancestry",
    "active_cancer",
    "cancer_survivor",
    "cancer_life_expectancy_gt_2y",
    "suspected_fh_hefh",
    "incidental_cac",
    "incidental_cac_severity",
    "cac_percentile",
    "lipid_lowering",
    "bp_treated",
    "sglt2",
    "glp1",
    "ace_arb",
]

NUMERIC_FIELDS = {
    "sbp": r"\b(?:sbp|systolic)\b",
    "dbp": r"\b(?:dbp|diastolic)\b",
    "tc": r"\b(?:tc|total cholesterol|total-c|total chol)\b",
    "ldl_c": r"\b(?:ldl-c|ldl)\b",
    "hdl_c": r"\b(?:hdl-c|hdl)\b",
    "triglycerides": r"\b(?:tg|triglycerides|trigs)\b",
    "apob": r"\b(?:apob|apo\s*b)\b",
    "a1c": r"\b(?:a1c|hba1c)\b",
    "egfr": r"\b(?:egfr|e-gfr)\b",
    "uacr": r"\b(?:uacr|acr|urine albumin creatinine ratio)\b",
    "cac": r"\b(?:cac|coronary calcium|calcium score)\b",
    "bmi": r"\bbmi\b",
    "hscrp": r"\b(?:hscrp|hs-crp|high sensitivity crp)\b",
}

PHI_PATTERNS = [
    r"\b\d{3}-\d{2}-\d{4}\b",
    r"\bMRN\b|\bMedical Record\b",
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",
]


@dataclass(frozen=True)
class ParserRecognitionItem:
    field_id: str
    label: str
    value: str
    status: str
    confidence: str
    source_text: str
    display_priority: int


RECOGNITION_FIELD_ORDER = (
    ("age", "Age", ("age",), None),
    ("sex", "Sex", ("sex",), None),
    ("bp", "BP", ("sbp", "dbp"), None),
    ("ldl_c", "LDL-C", ("ldl_c",), "mg/dL"),
    ("hdl_c", "HDL-C", ("hdl_c",), "mg/dL"),
    ("triglycerides", "TG", ("triglycerides",), "mg/dL"),
    ("a1c", "A1c", ("a1c",), "%"),
    ("egfr", "eGFR", ("egfr",), None),
    ("bmi", "BMI", ("bmi",), None),
    ("diabetes", "Diabetes", ("diabetes", "diabetes_source"), None),
    ("smoking", "Smoking", ("smoker", "former_smoker", "pack_years"), None),
    (
        "medications",
        "Meds",
        ("medications_raw", "bp_treated", "ace_arb", "lipid_lowering", "sglt2", "glp1"),
        None,
    ),
    ("apob", "ApoB", ("apob",), "mg/dL"),
    ("lp_a_value", "Lp(a)", ("lp_a_value",), None),
    ("lp_a_review", "Lp(a) units", ("lp_a_review",), None),
    ("uacr", "UACR", ("uacr", "uacr_status"), "mg/g"),
    ("cac", "CAC", ("cac", "cac_not_done"), None),
    (
        "family_history",
        "Family history",
        (
            "family_history_review",
            "family_history_premature_review",
            "family_history_premature_ascvd",
        ),
        None,
    ),
    ("clinical_ascvd_review", "Clinical ASCVD", ("clinical_ascvd_review",), None),
    ("hscrp", "hsCRP", ("hscrp",), "mg/L"),
    ("osa", "OSA", ("osa", "sleep_apnea_review"), None),
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
            "inflammatory_arthritis_review",
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


EPIC_SMARTPHRASE_TEMPLATE = """Recommended RCCKM Epic template

=== CARDIOVASCULAR RISK ASSESSMENT ===

Age: @AGE@
Sex: @SEX@
Race/Ethnicity: @RACE@

Smoking status: @SMOKINGSTATUS@

Blood pressure (most recent): @LASTBP(3)@
BMI: @LAST_BMI@
@BMI@
@BMIE@

Clinical ASCVD: Unknown
Clinical ASCVD details:

Family History:
Premature ASCVD in first-degree relative: Unknown
Relationship:
Event type:
Age at event:

Lipids:
@RESUFAST(CHLPL,CHOL,TRIG,HDL,LDLCHOLESTEROL,LDL,LABVLDL,VLDL,CHOLHDLRATIO)@

A1c:
@LASTHBA1C@

ApoB:
@RESUFAST(APOB,APOB)@

Lp(a):
@RESUFAST(LIPOA)@ nmol/L

hsCRP:
@RESUFAST(CRPHS)@

eGFR:
@RESUFAST(LABGLOM,LABGLOM)@

Urine ACR:
@RESUFAST(ALBCREAT)@

@EGFR@
@GFRCG@
@EGFRCRE@

Coronary artery calcium (CAC) score: Unknown
CAC percentile:

Medications:
@MEDSCONDENSED@

Problem list:
@PROB@
"""


def contains_phi(text):
    if not text:
        return False

    cleaned = re.sub(r"@\w+@", "", text)
    return any(re.search(pattern, cleaned, re.IGNORECASE) for pattern in PHI_PATTERNS)


def _parse_number_after_label(text, label_pattern):
    pattern = rf"{label_pattern}\s*(?:=|:|is|of)?\s*([<>]?\s*\d+(?:\.\d+)?)"
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None

    value = match.group(1).replace(" ", "").lstrip("<>")
    try:
        return float(value)
    except ValueError:
        return None


def _record(parsed, meta, field, value, confidence="parsed", source=""):
    parsed[field] = value
    meta[field] = {"confidence": confidence, "source": source}


def _bool_from_text(text, positive_patterns, negative_patterns=None):
    negative_patterns = negative_patterns or []
    for pattern in negative_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return False
    for pattern in positive_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return None


def _canonical_field_name(field):
    return PARSER_FIELD_TO_WORKSHEET_FIELD.get(field, field)


def _parse_report_to_ingest_report(report: ParseReport):
    parsed = {}
    meta = {}

    for field, value in (report.extracted or {}).items():
        canonical = _canonical_field_name(field)
        parsed[canonical] = value
        meta[canonical] = dict((report.field_meta or {}).get(field) or {})

    for field, field_meta in (report.field_meta or {}).items():
        canonical = _canonical_field_name(field)
        meta.setdefault(canonical, dict(field_meta or {}))

    return {
        "parsed": parsed,
        "meta": meta,
        "warnings": list(report.warnings or []),
        "conflicts": list(report.conflicts or []),
        "source_style": getattr(report, "source_style", "unknown"),
        "raw": report.as_dict(),
    }


def parse_ingest_text(text):
    return parse_ingest_report(text)["parsed"]


def parse_ingest_report(text, profile: ParserProfile | None = None):
    if not text:
        return {"parsed": {}, "meta": {}, "warnings": [], "conflicts": [], "raw": ParseReport().as_dict()}
    parsed_text = apply_profile_hints(text, profile)
    report = _parse_report_to_ingest_report(parse_smartphrase_report(parsed_text))
    if profile is not None:
        report["parser_profile_id"] = profile.profile_id
        report["parser_profile_source_system"] = profile.source_system
    coverage = build_parser_coverage_report(report, parser_profile_id=profile.profile_id if profile else None)
    report["coverage"] = coverage
    return report


def render_recommended_smartphrase_template(st):
    components = getattr(getattr(st, "components", None), "v1", None)
    if components is None:
        import streamlit.components.v1 as components

    uid = uuid.uuid4().hex[:10]
    safe_template = html.escape(EPIC_SMARTPHRASE_TEMPLATE)
    components.html(
        f"""
<style>
.recommended-smartphrase {{
  border: 1px solid rgba(11,31,58,.10);
  border-radius: 12px;
  background: rgba(255,253,248,.70);
  color: #071A2F;
  font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  margin: 0 0 10px;
  padding: 10px 12px;
}}
.recommended-smartphrase-head {{
  align-items: center;
  display: flex;
  gap: 12px;
  justify-content: space-between;
}}
.recommended-smartphrase-title {{
  font-size: .90rem;
  font-weight: 850;
  line-height: 1.15;
}}
.recommended-smartphrase-subtitle {{
  color: rgba(7,26,47,.58);
  font-size: .76rem;
  font-weight: 680;
  line-height: 1.25;
  margin-top: 2px;
}}
.recommended-smartphrase-copy {{
  border: 1px solid rgba(11,31,58,.16);
  border-radius: 999px;
  background: #fffefa;
  color: #0B5B45;
  cursor: pointer;
  font-size: .76rem;
  font-weight: 850;
  line-height: 1;
  padding: 7px 11px;
  white-space: nowrap;
}}
.recommended-smartphrase-msg {{
  color: rgba(7,26,47,.56);
  font-size: .72rem;
  font-weight: 680;
  min-height: 14px;
  margin-top: 6px;
}}
.recommended-smartphrase-hidden {{
  display: none;
}}
@media (max-width: 640px) {{
  .recommended-smartphrase-head {{ align-items: flex-start; flex-direction: column; }}
}}
</style>
<section class="recommended-smartphrase" aria-label="Recommended Epic template">
  <div class="recommended-smartphrase-head">
    <div>
      <div class="recommended-smartphrase-title">Recommended Epic template</div>
      <div class="recommended-smartphrase-subtitle">Use this structure for best parser coverage.</div>
    </div>
    <button id="copyEpicTemplate_{uid}" class="recommended-smartphrase-copy">Copy Epic template</button>
  </div>
  <textarea id="epicTemplate_{uid}" class="recommended-smartphrase-hidden" aria-hidden="true">{safe_template}</textarea>
  <div id="epicTemplateMsg_{uid}" class="recommended-smartphrase-msg"></div>
</section>
<script>
(function() {{
  const btn = document.getElementById("copyEpicTemplate_{uid}");
  const template = document.getElementById("epicTemplate_{uid}");
  const msg = document.getElementById("epicTemplateMsg_{uid}");
  async function copyTemplate() {{
    const text = template.value || template.textContent || "";
    try {{
      await navigator.clipboard.writeText(text);
      msg.textContent = "Template copied.";
    }} catch (e) {{
      template.classList.remove("recommended-smartphrase-hidden");
      template.focus();
      template.select();
      const ok = document.execCommand("copy");
      msg.textContent = ok ? "Template copied." : "Copy unavailable - select the template manually.";
      template.classList.add("recommended-smartphrase-hidden");
    }}
    setTimeout(function() {{ msg.textContent = ""; }}, 1800);
  }}
  btn.addEventListener("click", copyTemplate);
}})();
</script>
        """,
        height=112,
    )
    with st.expander("Preview Epic template", expanded=False):
        st.code(EPIC_SMARTPHRASE_TEMPLATE, language="text")


def _recognition_field_value(field_id, keys, parsed, unit):
    def compact(value):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)
        return str(int(number)) if number.is_integer() else f"{number:g}"

    if field_id == "bp":
        if parsed.get("sbp") is not None and parsed.get("dbp") is not None:
            return f"{compact(parsed.get('sbp'))}/{compact(parsed.get('dbp'))}"
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
    if field_id == "diabetes":
        if parsed.get("diabetes") is True:
            return "Diabetes detected" if parsed.get("diabetes_source") == "problem_list" else "Diabetes"
        if parsed.get("diabetes") is False:
            return "No diabetes"
        return ""
    if field_id == "cac":
        if parsed.get("cac") is not None:
            return compact(parsed.get("cac"))
        if parsed.get("cac_not_done") is True:
            return ""
    if field_id == "uacr":
        if parsed.get("uacr") is not None:
            return f"{compact(parsed.get('uacr'))} {unit}" if unit else compact(parsed.get("uacr"))
        if parsed.get("uacr_status") == "indeterminate":
            return "not calculable"
        return ""
    if field_id == "family_history":
        if parsed.get("family_history_premature_review") is True:
            return "Premature family history; confirm"
        if parsed.get("family_history_review") is True:
            return "Family history of CAD; premature status not specified"
        value = parsed.get("family_history_premature_ascvd")
        if value is True:
            relationship = str(parsed.get("family_history_relationship") or "").strip().lower()
            event = str(parsed.get("family_history_event_type") or "").strip()
            age = parsed.get("family_history_age_at_event")
            if relationship and event and age not in (None, ""):
                event_label = "MI" if event.lower() == "mi" else event.upper() if len(event) <= 4 else event
                return f"{relationship.title()} {event_label} age {compact(age)}"
            return "Present"
        if value is False:
            return "Not reported"
        return ""
    if field_id == "clinical_ascvd_review":
        return "Possible ASCVD history; review" if parsed.get("clinical_ascvd_review") is True else ""
    if field_id == "osa":
        if parsed.get("osa") is True:
            return "Yes"
        if parsed.get("sleep_apnea_review") is True:
            return "Possible sleep apnea"
        return ""
    if field_id == "inflammatory":
        labels = []
        if parsed.get("inflammatory_arthritis_review") is True:
            return "Inflammatory arthritis review"
        for label, key in (
            ("RA", "rheumatoid_arthritis"),
            ("SLE", "sle"),
            ("psoriasis", "psoriasis"),
            ("IBD", "ibd"),
            ("inflammatory arthritis", "inflammatory_arthritis"),
            ("inflammatory disease", "inflammatory_disease"),
        ):
            if parsed.get(key) is True:
                labels.append(label)
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
    if field_id == "lp_a_review":
        return "Confirm Lp(a) units" if parsed.get("lp_a_review") is True else ""

    for key in keys:
        value = parsed.get(key)
        if value not in (None, "", False):
            if isinstance(value, bool):
                return "Yes"
            value_text = compact(value)
            if field_id == "lp_a_value" and parsed.get("lp_a_unit"):
                return f"{value_text} {parsed.get('lp_a_unit')}"
            if unit == "%":
                return f"{value_text}%"
            return f"{value_text} {unit}" if unit else value_text
    return ""


def _recognition_confidence(keys, meta):
    for key in keys:
        confidence = str((meta.get(key) or {}).get("confidence") or "").strip()
        if confidence:
            return confidence
    return ""


def _recognition_source(keys, meta):
    for key in keys:
        source = str((meta.get(key) or {}).get("source") or "").strip()
        if source:
            return source
    return ""


def _recognition_status(field_id, keys, parsed, meta, conflict_fields, value):
    if any(key in conflict_fields for key in keys):
        return "invalid"
    confidence_values = {
        str((meta.get(key) or {}).get("confidence") or "").strip().lower()
        for key in keys
        if (meta.get(key) or {}).get("confidence")
    }
    source_text = " ".join(str((meta.get(key) or {}).get("source") or "").lower() for key in keys)
    if field_id == "cac" and parsed.get("cac_not_done") is True and parsed.get("cac") is None:
        return "review" if "placeholder" in source_text or "***" in source_text else "missing"
    if field_id == "medications" and parsed.get("medications_raw"):
        return "extracted"
    if value:
        return "review" if confidence_values & {"uncertain", "inferred"} else "extracted"
    if confidence_values:
        return "missing" if "not found" in confidence_values else "review"
    return "missing"


def build_parser_recognition_items(report) -> list[ParserRecognitionItem]:
    parsed = (report or {}).get("parsed") or {}
    meta = (report or {}).get("meta") or {}
    conflicts = (report or {}).get("conflicts") or []
    conflict_fields = {
        PARSER_FIELD_TO_WORKSHEET_FIELD.get(str(conflict).split(":", 1)[0].strip(), str(conflict).split(":", 1)[0].strip())
        for conflict in conflicts
    }
    items = []
    for priority, (field_id, label, keys, unit) in enumerate(RECOGNITION_FIELD_ORDER):
        if field_id == "diabetes" and parsed.get("diabetes") is not True:
            continue
        value = _recognition_field_value(field_id, keys, parsed, unit)
        status = _recognition_status(field_id, keys, parsed, meta, conflict_fields, value)
        if status == "missing" and not any(key in meta for key in keys):
            continue
        items.append(
            ParserRecognitionItem(
                field_id=field_id,
                label=label,
                value=value,
                status=status,
                confidence=_recognition_confidence(keys, meta),
                source_text=_recognition_source(keys, meta),
                display_priority=priority,
            )
        )
    status_order = {"extracted": 0, "review": 1, "missing": 2, "invalid": 3}
    return sorted(items, key=lambda item: (status_order.get(item.status, 9), item.display_priority))[:20]


def render_parser_recognition_strip(report) -> str:
    items = build_parser_recognition_items(report)
    if not items:
        return ""

    status_icon = {
        "extracted": "&#10003;",
        "review": "&#9888;",
        "missing": "&#9675;",
        "invalid": "&#10005;",
    }
    chips = []
    for index, item in enumerate(items):
        label = item.value if item.status == "extracted" and item.value else (
            f"{item.label} not available" if item.status == "missing" else item.label
        )
        if item.status == "extracted" and item.label not in str(label):
            label = f"{item.label} {label}"
        if item.status == "review":
            if item.field_id == "family_history":
                label = "Family history unclear"
            elif item.field_id == "clinical_ascvd_review":
                label = "Possible ASCVD history; review"
            elif item.field_id == "cac":
                label = "CAC placeholder detected" if "placeholder" in item.source_text.lower() else "CAC review"
            elif item.field_id == "lp_a_review":
                label = "Confirm Lp(a) units"
            elif item.field_id == "uacr" and "calculable" in item.value.lower():
                label = "UACR not calculable"
            elif item.field_id == "osa":
                label = "Possible sleep apnea"
            elif item.field_id == "inflammatory":
                label = "Inflammatory arthritis review"
            else:
                label = f"{item.label} review"
        detail_attr = f' data-detail="{html.escape(item.source_text)}"' if item.source_text else ""
        chips.append(
            f'<span class="parser-recognition-chip {html.escape(item.status)}" '
            f'style="--chip-index:{index}"{detail_attr}>'
            f'<span aria-hidden="true">{status_icon[item.status]}</span>'
            f'{html.escape(label)}'
            "</span>"
        )
    return (
        '<div class="parser-recognition-strip" aria-live="polite">'
        '<span class="parser-recognition-label">Recognized</span>'
        f'{"".join(chips)}'
        "</div>"
    )


def build_parse_review_rows(report):
    parsed = report.get("parsed", {}) or {}
    meta = report.get("meta", {}) or {}
    rows = []
    for field in REVIEW_FIELDS:
        field_meta = meta.get(field, {})
        confidence = field_meta.get("confidence")
        if field in parsed:
            confidence = confidence or "parsed"
            value = parsed[field]
        elif confidence:
            value = ""
        else:
            confidence = "not found"
            value = ""

        rows.append(
            {
                "Field": field,
                "Parsed value": str(value),
                "Confidence": confidence,
                "Source": field_meta.get("source", ""),
            }
        )
    return rows


def clear_parser_controlled_session_state(state):
    for key in PARSER_CONTROLLED_SESSION_KEYS:
        state.pop(key, None)
    for key in list(state.keys()):
        if str(key).startswith("_unknown_"):
            state.pop(key, None)


def reset_worksheet_state_for_new_parse(state):
    """Clear parser-owned worksheet and parser metadata before a new paste applies."""
    clear_parser_controlled_session_state(state)
    for key in PARSER_APPLY_METADATA_KEYS:
        state.pop(key, None)


def _next_parse_id(state):
    parse_id = int(state.get("_worksheet_parse_id", 0) or 0) + 1
    state["_worksheet_parse_id"] = parse_id
    state["_worksheet_field_sources"] = {}
    return parse_id


def _mark_parsed_source(state, widget_key, parse_id):
    state.setdefault("_worksheet_field_sources", {})[widget_key] = {
        "source": "parsed",
        "parse_id": parse_id,
    }


def _sync_ancestry_context_select(state, parsed, parse_id):
    if bool((parsed or {}).get("south_asian_ancestry")):
        value = "South Asian"
    elif bool((parsed or {}).get("filipino_ancestry")):
        value = "Filipino"
    else:
        value = "None / not specified"
    state["input_ancestry_context"] = value
    _mark_parsed_source(state, "input_ancestry_context", parse_id)


def _family_history_recognition_status(parse_report):
    if not parse_report:
        return None
    coverage = parse_report.get("coverage") if isinstance(parse_report, dict) else None
    if coverage is None:
        coverage = build_parser_coverage_report(parse_report)
    for item in coverage.recognition_items:
        if item.field_id == "family_history":
            return item.status
    return None


def _apply_neutral_family_history_state(state, parse_id, *, helper=None, unknown=False):
    for key in (
        "input_family_history_relationship",
        "input_family_history_event_type",
        "input_family_history_age_at_event",
        "input_fhx_text",
        "input_family_history_summary",
    ):
        state.pop(key, None)
    state["input_family_history_pattern"] = "none_unknown"
    state["input_family_history_premature_ascvd"] = False
    if unknown:
        state["_unknown_input_family_history_premature_ascvd"] = True
    else:
        state.pop("_unknown_input_family_history_premature_ascvd", None)
    if helper:
        state["input_family_history_helper"] = helper
        _mark_parsed_source(state, "input_family_history_helper", parse_id)
    else:
        state.pop("input_family_history_helper", None)
    for key in (
        "input_family_history_pattern",
        "input_family_history_premature_ascvd",
    ):
        _mark_parsed_source(state, key, parse_id)


def _initialize_absent_parser_booleans(state, parsed, parse_id):
    parsed = parsed or {}
    for field in PARSER_CONTROLLED_BOOLEAN_FIELDS:
        if field in parsed:
            continue
        widget_key = WORKSHEET_KEY_BY_FIELD.get(field) or EXTRA_SESSION_KEY_BY_FIELD.get(field)
        if not widget_key:
            continue
        state[widget_key] = False
        state.pop(f"_unknown_{widget_key}", None)
        _mark_parsed_source(state, widget_key, parse_id)
    if "bp_treated" not in parsed:
        state["input_bp_meds"] = False
        state.pop("_unknown_input_bp_meds", None)
        _mark_parsed_source(state, "input_bp_meds", parse_id)
    if "south_asian_ancestry" not in parsed and "filipino_ancestry" not in parsed:
        state["input_ancestry_context"] = "None / not specified"
        _mark_parsed_source(state, "input_ancestry_context", parse_id)


def apply_parsed_to_session_state(state, parsed, *, clear_existing=True, parse_report=None):
    if clear_existing:
        reset_worksheet_state_for_new_parse(state)
    parse_id = _next_parse_id(state)
    if clear_existing:
        _initialize_absent_parser_booleans(state, parsed, parse_id)
    family_history_status = _family_history_recognition_status(parse_report)
    for field, value in (parsed or {}).items():
        widget_key = WORKSHEET_KEY_BY_FIELD.get(field)
        extra_key = EXTRA_SESSION_KEY_BY_FIELD.get(field)
        if widget_key:
            if field == "family_history_event_type" and value == "mi":
                value = "MI"
            elif field in BOOLEAN_WORKSHEET_FIELDS and value is None:
                state[f"_unknown_{widget_key}"] = True
                value = False
            elif field in INTEGER_WORKSHEET_FIELDS and value is not None:
                try:
                    value = int(round(float(value)))
                except (TypeError, ValueError):
                    pass
            elif field in ONE_DECIMAL_WORKSHEET_FIELDS and value is not None:
                try:
                    value = round(float(value), 1)
                except (TypeError, ValueError):
                    pass
            elif field in TWO_DECIMAL_WORKSHEET_FIELDS and value is not None:
                try:
                    value = round(float(value), 2)
                except (TypeError, ValueError):
                    pass
            state[widget_key] = value
            if field in BOOLEAN_WORKSHEET_FIELDS and value is not False:
                state.pop(f"_unknown_{widget_key}", None)
            _mark_parsed_source(state, widget_key, parse_id)
        elif extra_key:
            state[extra_key] = value
            _mark_parsed_source(state, extra_key, parse_id)
        if field == "bp_treated":
            state["input_bp_meds"] = value
            if parsed.get(field) is None:
                state["_unknown_input_bp_meds"] = True
            else:
                state.pop("_unknown_input_bp_meds", None)
            _mark_parsed_source(state, "input_bp_meds", parse_id)
        if field == "cac_not_done" and value:
            state["input_cac"] = None
            state["input_cac_not_done"] = True
            _mark_parsed_source(state, "input_cac", parse_id)
            _mark_parsed_source(state, "input_cac_not_done", parse_id)
        if field == "cac" and value is not None:
            state["input_cac_not_done"] = False
            _mark_parsed_source(state, "input_cac_not_done", parse_id)
    if family_history_status in {"review", "missing", "invalid"}:
        _apply_neutral_family_history_state(
            state,
            parse_id,
            helper="Family history unclear" if family_history_status in {"review", "invalid"} else None,
            unknown=family_history_status in {"review", "missing", "invalid"},
        )
    elif (
        "family_history_premature_ascvd" in (parsed or {})
        and (parsed or {}).get("family_history_premature_ascvd") is None
    ):
        _apply_neutral_family_history_state(
            state,
            parse_id,
            helper="Family history unclear",
            unknown=True,
        )
    elif (
        "family_history_premature_ascvd" in (parsed or {})
        and
        (parsed or {}).get("family_history_premature_ascvd") is False
        and not any(
            (parsed or {}).get(key)
            for key in (
                "family_history_relationship",
                "family_history_event_type",
                "family_history_age_at_event",
                "fhx_text",
            )
        )
    ):
        _apply_neutral_family_history_state(state, parse_id, helper=None, unknown=False)
    elif (parsed or {}).get("family_history_premature_ascvd") is True:
        option = infer_compact_family_history_option(
            True,
            (parsed or {}).get("family_history_relationship"),
            (parsed or {}).get("family_history_age_at_event"),
        )
        state["input_family_history_pattern"] = option
        state.pop("input_family_history_helper", None)
        _mark_parsed_source(state, "input_family_history_pattern", parse_id)
    if "south_asian_ancestry" in (parsed or {}) or "filipino_ancestry" in (parsed or {}):
        _sync_ancestry_context_select(state, parsed, parse_id)


def _snapshot_worksheet_state(state):
    worksheet_keys = set(WORKSHEET_KEY_BY_FIELD.values()) | set(EXTRA_SESSION_KEY_BY_FIELD.values())
    worksheet_keys.add("input_bp_meds")
    return {key: state[key] for key in worksheet_keys if key in state}


def _restore_worksheet_state(state, snapshot):
    for key, value in (snapshot or {}).items():
        if key not in state or state.get(key) in ("", None):
            state[key] = value


def render_ingest_panel(st):
    with st.container(border=True):
        if st.session_state.pop("clear_ingest_requested", False):
            worksheet_snapshot = st.session_state.pop("clear_ingest_worksheet_snapshot", {})
            st.session_state["ingest_pasted_text"] = ""
            st.session_state["parsed_ingest"] = {}
            st.session_state["parse_report"] = {
                "parsed": {},
                "meta": {},
                "warnings": [],
                "conflicts": [],
            }
            st.session_state["parsed_needs_review"] = False
            st.session_state["parse_processing"] = False
            st.session_state["parse_recognition_html"] = ""
            st.session_state["parse_recognition_visible"] = False
            st.session_state["last_parsed_text_hash"] = None
            st.session_state["last_ingest_text_hash"] = hash_text("")
            clear_report_state(st.session_state, dirty=True)
            _restore_worksheet_state(st.session_state, worksheet_snapshot)

        title_col, expand_col = st.columns([0.78, 0.22], vertical_alignment="center")
        with title_col:
            section_heading(
                st,
                "Paste EMR text",
                "Paste EMR text. Parsed values fill the worksheet below.",
            )
        with expand_col:
            expanded = st.checkbox("Expand paste box", key="ingest_expand_paste_box")
        render_recommended_smartphrase_template(st)
        pasted_text = st.text_area(
            "Paste labs, vitals, meds, or EMR text",
            height=220 if expanded else 105,
            label_visibility="collapsed",
            key="ingest_pasted_text",
        )
        current_text_hash = hash_text(pasted_text)
        previous_text_hash = st.session_state.get("last_ingest_text_hash")
        if (
            previous_text_hash is not None
            and current_text_hash != previous_text_hash
            and st.session_state.get("report_generated")
        ):
            clear_report_state(st.session_state, dirty=True)
        st.session_state["last_ingest_text_hash"] = current_text_hash

        is_parsing = bool(st.session_state.get("parse_processing", False))
        c1, c2, _spacer = st.columns([0.16, 0.105, 0.735])
        with c1:
            parse_label = "Parsing..." if is_parsing else "Parse and apply"
            parse_clicked = st.button(parse_label, type="primary", disabled=is_parsing, key="parse_smartphrase")
        with c2:
            clear_clicked = st.button("Clear", key="clear_ingest")

        if clear_clicked:
            st.session_state["clear_ingest_worksheet_snapshot"] = _snapshot_worksheet_state(st.session_state)
            st.session_state["clear_ingest_requested"] = True
            st.rerun()

        if parse_clicked:
            st.session_state["parse_processing"] = True
            st.session_state["parse_pending_text"] = pasted_text
            st.session_state["parse_pending_text_hash"] = current_text_hash
            st.session_state["parse_started_at"] = time.perf_counter()
            st.session_state["parse_recognition_visible"] = False
            st.rerun()

        if is_parsing:
            try:
                pending_text = st.session_state.get("parse_pending_text", "")
                pending_hash = st.session_state.get("parse_pending_text_hash") or hash_text(pending_text)
                if contains_phi(pending_text):
                    st.error("Possible PHI detected. Please remove identifiers before parsing.")
                else:
                    report = parse_ingest_report(pending_text)
                    clear_report_state(st.session_state, dirty=True)
                    apply_parsed_to_session_state(st.session_state, report["parsed"], parse_report=report)
                    st.session_state.parse_recognition_html = render_parser_recognition_strip(report)
                    st.session_state.parsed_ingest = report["parsed"]
                    st.session_state.parse_report = report
                    st.session_state.last_parsed_text_hash = pending_hash
                    st.session_state.last_ingest_text_hash = pending_hash
                    for warning in report.get("warnings", []):
                        st.warning(warning)
                    for conflict in report.get("conflicts", []):
                        st.warning(conflict)
            except Exception as exc:
                st.session_state.parsed_ingest = {}
                st.session_state.parse_report = {"parsed": {}, "meta": {}, "warnings": [str(exc)], "conflicts": []}
                st.session_state.parse_recognition_html = ""
                st.error("Parser could not process the pasted text. Please enter values manually.")
                st.caption(str(exc))
            else:
                st.session_state.parsed_needs_review = True
                st.session_state.parse_recognition_visible = True
            finally:
                started = st.session_state.get("parse_started_at") or time.perf_counter()
                elapsed = time.perf_counter() - started
                if elapsed < 0.7:
                    time.sleep(0.7 - elapsed)
                st.session_state.parse_processing = False
                st.session_state.parse_started_at = None
                st.session_state.pop("parse_pending_text", None)
                st.session_state.pop("parse_pending_text_hash", None)
                st.rerun()

        parsed = st.session_state.get("parsed_ingest", {})
        report = st.session_state.get("parse_report") or {"parsed": parsed, "meta": {}, "warnings": [], "conflicts": []}
        if st.session_state.get("parse_recognition_visible") and st.session_state.get("parse_recognition_html"):
            render_html(st, st.session_state.get("parse_recognition_html"))
        has_parse_report = bool(parsed or report.get("meta") or report.get("warnings") or report.get("conflicts"))
        render_component_html(
            st,
            render_parse_coverage(report if has_parse_report else None),
            height=560 if has_parse_report else 64,
            scrolling=has_parse_report,
        )
        if parsed:
            st.caption("Review parsed values in the worksheet before interpretation.")
            if st.checkbox("Developer parser debug", value=False, key="parser_debug_json"):
                with st.expander("Raw parsed JSON", expanded=False):
                    st.json(report.get("raw") or report)

    return parsed
