from __future__ import annotations

import html
from typing import Any

from smartphrase_ingest.parser import ParseReport


FIELD_SPECS: tuple[tuple[str, str, str | None], ...] = (
    ("Age", "age", None),
    ("Sex", "sex", None),
    ("Systolic BP", "sbp", "mmHg"),
    ("Diastolic BP", "dbp", "mmHg"),
    ("Total cholesterol", "tc", "mg/dL"),
    ("HDL-C", "hdl_c", "mg/dL"),
    ("LDL-C", "ldl_c", "mg/dL"),
    ("Triglycerides", "triglycerides", "mg/dL"),
    ("ApoB", "apob", "mg/dL"),
    ("Lp(a)", "lp_a_value", None),
    ("Lp(a) unit", "lp_a_unit", None),
    ("A1c", "a1c", "%"),
    ("Diabetes", "diabetes", None),
    ("Diabetes duration", "diabetes_duration_years", "years"),
    ("Retinopathy", "diabetic_retinopathy", None),
    ("Neuropathy", "diabetic_neuropathy", None),
    ("ABI", "abi", None),
    ("ABI <0.9", "abi_lt_0_9", None),
    ("BMI", "bmi", None),
    ("eGFR", "egfr", None),
    ("UACR", "uacr", "mg/g"),
    ("Creatinine", "creatinine", "mg/dL"),
    ("Calcium score", "cac", None),
    ("CAC not done", "cac_not_done", None),
    ("Clinical ASCVD", "clinical_ascvd", None),
    ("Smoking", "smoker", None),
    ("Family history", "family_history_premature_ascvd", None),
    ("hsCRP", "hscrp", "mg/L"),
    ("Lipid-lowering therapy", "lipid_lowering", None),
    ("Lipid supplements", "lipid_supplements", None),
    ("BP treated", "bp_treated", None),
    ("SGLT2", "sglt2", None),
    ("GLP-1/GIP", "glp1", None),
    ("ACE/ARB", "ace_arb", None),
    ("Medication names detected", "medications_raw", None),
    ("Early menopause", "early_menopause", None),
    ("Menopause age", "menopause_age", None),
    ("Premature menopause", "premature_menopause", None),
    ("Preeclampsia", "preeclampsia", None),
    ("Gestational hypertension", "gestational_hypertension", None),
    ("Gestational diabetes", "gestational_diabetes", None),
    ("Preterm delivery", "preterm_delivery", None),
    ("SGA infant", "small_for_gestational_age", None),
    ("Recurrent pregnancy loss", "recurrent_pregnancy_loss", None),
    ("PCOS / irregular menses", "pcos_or_irregular_menses", None),
    ("Early menarche", "early_menarche", None),
    ("Menarche age", "menarche_age", None),
)

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


def _normalize_report(parse_report: ParseReport | dict[str, Any] | None) -> dict[str, Any]:
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
    }


def _fmt_bool(value: bool) -> str:
    return "Yes" if value else "No"


def _fmt_number(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number.is_integer():
        return str(int(number))
    return f"{number:g}"


def _format_value(field: str, value: Any, parsed: dict[str, Any], unit: str | None) -> str:
    if value is None or value == "":
        if field == "cac" and parsed.get("cac_not_done") is True:
            return "No CAC performed"
        return ""
    if isinstance(value, bool):
        return _fmt_bool(value)
    if field == "sex":
        return str(value).capitalize()
    if field == "lp_a_value":
        unit_value = parsed.get("lp_a_unit")
        return f"{_fmt_number(value)} {unit_value}" if unit_value else _fmt_number(value)
    value_text = _fmt_number(value)
    if unit == "%":
        return f"{value_text}%"
    return f"{value_text} {unit}" if unit else value_text


def _conflict_fields(conflicts: list[str]) -> set[str]:
    fields: set[str] = set()
    for conflict in conflicts:
        field = str(conflict).split(":", 1)[0].strip()
        if field:
            fields.add(RAW_TO_CANONICAL.get(field, field))
    return fields


def _status_for(field: str, parsed: dict[str, Any], meta: dict[str, Any], conflicts: set[str]) -> tuple[str, str]:
    if field in conflicts:
        return "conflict", "conflict"
    field_meta = meta.get(field) or {}
    confidence = str(field_meta.get("confidence") or "").strip().lower()
    source = str(field_meta.get("source") or "").strip().lower()
    if field in parsed:
        if confidence in {"inferred"}:
            return "inferred", "inferred"
        if confidence in {"uncertain"}:
            return "verify", "verify"
        if field in {"lp_a_unit", "cac_not_done"}:
            return "complete", "complete"
        return "found", "found"
    if confidence or "unavailable" in source or "not done" in source:
        return "verify", "verify"
    return "not found", "missing"


def _chip(label: str, status_class: str) -> str:
    return f'<span class="parse-chip parse-chip-{html.escape(status_class)}">{html.escape(label)}</span>'


def _coverage_row(label: str, field: str, value: str, status: str, status_class: str, source: str) -> str:
    value_html = html.escape(value or "not found")
    source_html = html.escape(source or "")
    source_attr = f' title="{source_html}"' if source_html else ""
    return (
        f'<div class="parse-row"{source_attr}>'
        f'<div class="parse-name">{html.escape(label)}</div>'
        f'<div class="parse-value">{value_html}</div>'
        f'<div class="parse-status">{_chip(status, status_class)}</div>'
        "</div>"
    )


def render_parse_coverage(parse_report: ParseReport | dict[str, Any] | None) -> str:
    report = _normalize_report(parse_report)
    parsed = report["parsed"]
    meta = report["meta"]
    warnings = [str(x) for x in report.get("warnings") or [] if str(x).strip()]
    conflicts = [str(x) for x in report.get("conflicts") or [] if str(x).strip()]

    if not parsed and not meta and not warnings and not conflicts:
        return """
<style>
.parse-coverage-empty { margin: 2px 0 3px; color: rgba(7,26,47,.54); font: 650 .74rem Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
</style>
<div class="parse-coverage-empty">Nothing parsed yet.</div>
"""

    conflict_fields = _conflict_fields(conflicts)
    rows = []
    for label, field, unit in FIELD_SPECS:
        status, status_class = _status_for(field, parsed, meta, conflict_fields)
        value = _format_value(field, parsed.get(field), parsed, unit)
        source = str((meta.get(field) or {}).get("source") or "")
        rows.append(_coverage_row(label, field, value, status, status_class, source))

    notices = []
    for warning in warnings[:4]:
        notices.append(f'<div class="parse-notice parse-notice-verify">Verify: {html.escape(warning)}</div>')
    for conflict in conflicts[:4]:
        notices.append(f'<div class="parse-notice parse-notice-conflict">Conflict: {html.escape(conflict)}</div>')

    source_style = str(report.get("source_style") or "unknown").replace("_", " ")
    source_html = (
        f'<span class="parse-source">Detected format: {html.escape(source_style.title())}-style text</span>'
        if source_style and source_style != "unknown"
        else ""
    )

    return f"""
<style>
.parse-coverage {{
    border: 1px solid rgba(11,31,58,.12);
    border-radius: 14px;
    background: rgba(255,253,248,.68);
    color: #071A2F;
    font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    margin: 6px 0 12px;
    padding: 10px 12px;
}}
.parse-head {{
    align-items: baseline;
    display: flex;
    gap: 10px;
    justify-content: space-between;
    margin-bottom: 8px;
}}
.parse-title {{
    color: var(--rc-text, #071A2F);
    font-family: var(--rc-font-body, Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif);
    font-size: 1.0rem;
    font-weight: 750;
    letter-spacing: 0;
    line-height: 1.15;
}}
.parse-source {{
    color: rgba(7,26,47,.52);
    font-size: .72rem;
    font-weight: 700;
}}
.parse-grid {{
    display: grid;
    gap: 6px;
    grid-template-columns: repeat(3, minmax(0, 1fr));
}}
.parse-row {{
    align-items: center;
    border-bottom: 1px solid rgba(11,31,58,.08);
    column-gap: 7px;
    display: grid;
    grid-template-columns: minmax(74px, .78fr) minmax(52px, .7fr) auto;
    min-height: 26px;
    padding: 2px 0 5px;
}}
.parse-name {{
    color: rgba(7,26,47,.70);
    font-size: .73rem;
    font-weight: 780;
    line-height: 1.12;
}}
.parse-value {{
    color: rgba(7,26,47,.92);
    font-size: .78rem;
    font-weight: 850;
    line-height: 1.15;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}
.parse-chip {{
    border-radius: 999px;
    display: inline-flex;
    font-size: .62rem;
    font-weight: 880;
    line-height: 1;
    padding: .18rem .42rem;
    white-space: nowrap;
}}
.parse-chip-found, .parse-chip-complete {{
    background: rgba(47,95,143,.09);
    border: 1px solid rgba(47,95,143,.24);
    color: #132F55;
}}
.parse-chip-inferred {{
    background: rgba(15,139,141,.09);
    border: 1px solid rgba(15,139,141,.24);
    color: #075d60;
}}
.parse-chip-missing {{
    background: rgba(93,107,122,.08);
    border: 1px solid rgba(93,107,122,.16);
    color: rgba(7,26,47,.46);
}}
.parse-chip-verify {{
    background: rgba(217,119,6,.13);
    border: 1px solid rgba(217,119,6,.26);
    color: #7c3f00;
}}
.parse-chip-conflict {{
    background: rgba(193,18,31,.10);
    border: 1px solid rgba(193,18,31,.28);
    color: #9f111b;
}}
.parse-notices {{
    display: grid;
    gap: 4px;
    margin-top: 8px;
}}
.parse-notice {{
    border-radius: 9px;
    font-size: .73rem;
    font-weight: 720;
    line-height: 1.25;
    padding: 5px 7px;
}}
.parse-notice-verify {{
    background: rgba(217,119,6,.08);
    color: #7c3f00;
}}
.parse-notice-conflict {{
    background: rgba(193,18,31,.08);
    color: #9f111b;
}}
@media (max-width: 940px) {{
    .parse-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
}}
@media (max-width: 620px) {{
    .parse-grid {{ grid-template-columns: 1fr; }}
}}
</style>
<section class="parse-coverage">
  <div class="parse-head">
    <div class="parse-title rc-card-title">Parse coverage</div>
    {source_html}
  </div>
  <div class="parse-grid">
    {''.join(rows)}
  </div>
  <div class="parse-notices">{''.join(notices)}</div>
</section>
"""
