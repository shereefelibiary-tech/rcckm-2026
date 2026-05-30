from __future__ import annotations

import html
from typing import Any

from smartphrase_ingest.coverage import build_parser_coverage_report
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

FIELD_TIERS: tuple[tuple[str, tuple[tuple[str, str, str | None], ...]], ...] = (
    (
        "Core essentials",
        (
            ("Age", "age", None),
            ("Sex", "sex", None),
            ("BP", "bp", None),
            ("LDL-C", "ldl_c", "mg/dL"),
            ("HDL-C", "hdl_c", "mg/dL"),
            ("TG", "triglycerides", "mg/dL"),
            ("A1c", "a1c", "%"),
            ("eGFR", "egfr", None),
            ("BMI", "bmi", None),
            ("Smoking", "smoker", None),
            ("Current medications", "current_medications", None),
        ),
    ),
    (
        "Important risk enhancers",
        (
            ("ApoB", "apob", "mg/dL"),
            ("CAC", "cac", None),
            ("UACR", "uacr", "mg/g"),
            ("Family history", "family_history_premature_ascvd", None),
            ("Diabetes status", "diabetes", None),
        ),
    ),
    (
        "Advanced/contextual",
        (
            ("Lp(a)", "lp_a_value", None),
            ("hsCRP", "hscrp", "mg/L"),
            ("Inflammatory disease", "inflammatory_context", None),
            ("OSA", "osa", None),
            ("MASLD", "masld", None),
            ("Ancestry", "ancestry_context", None),
            ("Reproductive markers", "reproductive_context", None),
        ),
    ),
)

INFLAMMATORY_FIELDS = (
    "inflammatory_disease",
    "rheumatoid_arthritis",
    "sle",
    "psoriasis",
    "inflammatory_arthritis",
    "ibd",
)

REPRODUCTIVE_FIELDS = (
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
)

STATUS_META = {
    "found": ("&#10003;", "extracted"),
    "review": ("&#9888;", "review"),
    "missing": ("&#9675;", "not available"),
    "conflict": ("&#10005;", "conflict"),
}

CORE_COVERAGE_FIELDS = FIELD_TIERS[0][1]

IMPROVEMENT_TIPS = {
    "uacr": "Add UACR for kidney-risk interpretation.",
    "apob": "Add ApoB for better atherogenic burden assessment.",
    "lp_a_value": "Add Lp(a) for inherited lipid-risk context.",
    "cac": "Add CAC score if available.",
    "family_history_premature_ascvd": "Family history field unclear; use Yes/No/Unknown.",
    "hscrp": "Add hsCRP only when inflammatory risk clarification would change management.",
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


def _format_scalar(field: str, value: Any, parsed: dict[str, Any], unit: str | None) -> str:
    if value is None or value == "":
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


def _field_value(field: str, parsed: dict[str, Any], unit: str | None) -> str:
    if field == "bp":
        sbp = parsed.get("sbp")
        dbp = parsed.get("dbp")
        if sbp is not None and dbp is not None:
            return f"{_fmt_number(sbp)}/{_fmt_number(dbp)}"
        return ""
    if field == "current_medications":
        raw = parsed.get("medications_raw")
        if raw:
            return str(raw)
        meds = []
        for label, key in (
            ("BP meds", "bp_treated"),
            ("ACE/ARB", "ace_arb"),
            ("lipid-lowering", "lipid_lowering"),
            ("SGLT2", "sglt2"),
            ("GLP-1", "glp1"),
        ):
            if parsed.get(key) is True:
                meds.append(label)
        return ", ".join(meds)
    if field == "inflammatory_context":
        labels = []
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
    if field == "ancestry_context":
        labels = []
        if parsed.get("south_asian_ancestry") is True:
            labels.append("South Asian")
        if parsed.get("filipino_ancestry") is True:
            labels.append("Filipino")
        return ", ".join(labels)
    if field == "reproductive_context":
        labels = []
        for label, key in (
            ("early menopause", "early_menopause"),
            ("premature menopause", "premature_menopause"),
            ("preeclampsia", "preeclampsia"),
            ("gestational HTN", "gestational_hypertension"),
            ("GDM", "gestational_diabetes"),
            ("preterm birth", "preterm_delivery"),
            ("SGA infant", "small_for_gestational_age"),
            ("pregnancy loss", "recurrent_pregnancy_loss"),
            ("PCOS", "pcos_or_irregular_menses"),
        ):
            if parsed.get(key) is True:
                labels.append(label)
        return ", ".join(labels)
    if field == "cac" and parsed.get("cac") is None and parsed.get("cac_not_done") is True:
        return ""
    return _format_scalar(field, parsed.get(field), parsed, unit)


def _field_keys(field: str) -> tuple[str, ...]:
    if field == "bp":
        return ("sbp", "dbp")
    if field == "current_medications":
        return ("medications_raw", "bp_treated", "ace_arb", "lipid_lowering", "sglt2", "glp1")
    if field == "inflammatory_context":
        return INFLAMMATORY_FIELDS
    if field == "ancestry_context":
        return ("south_asian_ancestry", "filipino_ancestry", "higher_risk_ancestry_context")
    if field == "reproductive_context":
        return REPRODUCTIVE_FIELDS
    return (field,)


def _conflict_fields(conflicts: list[str]) -> set[str]:
    fields: set[str] = set()
    for conflict in conflicts:
        field = str(conflict).split(":", 1)[0].strip()
        if field:
            fields.add(RAW_TO_CANONICAL.get(field, field))
    return fields


def _source_detail(field: str, meta: dict[str, Any]) -> str:
    details = []
    for key in _field_keys(field):
        source = str((meta.get(key) or {}).get("source") or "").strip()
        confidence = str((meta.get(key) or {}).get("confidence") or "").strip()
        if source or confidence:
            if confidence and source:
                details.append(f"{key}: {confidence} - {source}")
            else:
                details.append(f"{key}: {source or confidence}")
    return "; ".join(details[:3])


def _status_for(field: str, parsed: dict[str, Any], meta: dict[str, Any], conflicts: set[str]) -> str:
    keys = _field_keys(field)
    if any(key in conflicts for key in keys):
        return "conflict"
    if field == "bp":
        if parsed.get("sbp") is not None and parsed.get("dbp") is not None:
            return "found"
    elif _field_value(field, parsed, None):
        if any(str((meta.get(key) or {}).get("confidence") or "").lower() == "uncertain" for key in keys):
            return "review"
        return "found"
    if field == "cac" and parsed.get("cac") is None and parsed.get("cac_not_done") is True:
        return "missing"
    if any(str((meta.get(key) or {}).get("confidence") or "").lower() == "uncertain" for key in keys):
        return "review"
    if any((meta.get(key) or {}).get("confidence") for key in keys):
        confidence_values = {
            str((meta.get(key) or {}).get("confidence") or "").strip().lower()
            for key in keys
        }
        return "missing" if "not found" in confidence_values else "review"
    return "missing"


def _coverage_summary(parsed: dict[str, Any], meta: dict[str, Any], conflicts: set[str]) -> tuple[int, int, str]:
    total = len(CORE_COVERAGE_FIELDS)
    found = sum(
        1
        for _label, field, _unit in CORE_COVERAGE_FIELDS
        if _status_for(field, parsed, meta, conflicts) == "found"
    )
    ratio = found / total if total else 0
    tone = "strong" if ratio >= 0.8 else "partial" if ratio >= 0.5 else "low"
    return found, total, tone


def _improvement_tips(parsed: dict[str, Any], meta: dict[str, Any], conflicts: set[str]) -> list[str]:
    tips: list[str] = []
    for field in ("uacr", "apob", "lp_a_value", "cac", "family_history_premature_ascvd", "hscrp"):
        status = _status_for(field, parsed, meta, conflicts)
        if status == "found":
            continue
        if field == "hscrp" and field not in meta:
            continue
        tip = IMPROVEMENT_TIPS.get(field)
        if tip and tip not in tips:
            tips.append(tip)
    return tips[:4]


def _item(label: str, field: str, value: str, status: str, detail: str) -> str:
    icon, status_text = STATUS_META[status]
    value_html = html.escape(value or f"{label} not available")
    detail_attr = f' data-detail="{html.escape(detail)}"' if detail else ""
    focus_attr = ' tabindex="0"' if detail else ""
    aria = f'{label}: {status_text}. {value or "not available"}'
    return (
        f'<div class="parse-item parse-item-{status}"{detail_attr}{focus_attr} aria-label="{html.escape(aria)}">'
        f'<span class="parse-icon" aria-hidden="true">{icon}</span>'
        '<span class="parse-item-main">'
        f'<span class="parse-item-label">{html.escape(label)}</span>'
        f'<span class="parse-item-value">{value_html}</span>'
        "</span>"
        "</div>"
    )


def _notices(warnings: list[str], conflicts: list[str]) -> str:
    parts = []
    for warning in warnings[:4]:
        parts.append(f'<div class="parse-notice parse-notice-review">&#9888; {html.escape(warning)}</div>')
    for conflict in conflicts[:4]:
        parts.append(f'<div class="parse-notice parse-notice-conflict">&#10005; {html.escape(conflict)}</div>')
    return "".join(parts)


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
    coverage = build_parser_coverage_report(report)
    coverage_found = coverage.recognized_core_fields
    coverage_total = coverage.total_core_fields
    coverage_tone = "strong" if coverage.confidence_score >= 0.8 else "partial" if coverage.confidence_score >= 0.5 else "low"
    tips = coverage.suggestions
    tier_html = []
    for tier_title, fields in FIELD_TIERS:
        items = []
        for label, field, unit in fields:
            value = _field_value(field, parsed, unit)
            status = _status_for(field, parsed, meta, conflict_fields)
            detail = _source_detail(field, meta)
            items.append(_item(label, field, value, status, detail))
        tier_html.append(
            '<div class="parse-tier">'
            f'<div class="parse-tier-title">{html.escape(tier_title)}</div>'
            f'<div class="parse-tier-grid">{"".join(items)}</div>'
            "</div>"
        )

    source_style = str(report.get("source_style") or "unknown").replace("_", " ")
    is_generic = source_style in {"unknown", "generic"}
    source_html = (
        f'<span class="parse-source">{html.escape(source_style.title())}-style text</span>'
        if source_style and not is_generic
        else ""
    )
    generic_notice = (
        '<div class="parse-generic-notice">Generic EMR text detected. Some fields may need review.</div>'
        if is_generic
        else ""
    )
    tips_html = (
        '<div class="parse-tips">'
        + "".join(f'<div class="parse-tip">{html.escape(tip)}</div>' for tip in tips)
        + "</div>"
        if tips
        else ""
    )

    return f"""
<style>
.parse-coverage {{
    border: 1px solid rgba(11,31,58,.11);
    border-radius: 14px;
    background: rgba(255,253,248,.72);
    color: #071A2F;
    font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    margin: 6px 0 12px;
    padding: 10px 12px 11px;
}}
.parse-head {{
    align-items: baseline;
    display: flex;
    gap: 10px;
    justify-content: space-between;
    margin-bottom: 8px;
}}
.parse-head-main {{
    display: grid;
    gap: 4px;
    min-width: 0;
}}
.parse-title {{
    color: var(--rc-text, #071A2F);
    font-size: 1.0rem;
    font-weight: 780;
    letter-spacing: 0;
    line-height: 1.15;
}}
.parse-source {{
    color: rgba(7,26,47,.52);
    font-size: .72rem;
    font-weight: 700;
}}
.parse-coverage-score {{
    align-items: center;
    border: 1px solid rgba(11,31,58,.10);
    border-radius: 999px;
    display: inline-flex;
    font-size: .75rem;
    font-weight: 850;
    line-height: 1;
    padding: 6px 9px;
    white-space: nowrap;
}}
.parse-coverage-score-strong {{
    background: rgba(29,126,84,.09);
    color: #14734c;
}}
.parse-coverage-score-partial {{
    background: rgba(217,119,6,.10);
    color: #7c3f00;
}}
.parse-coverage-score-low {{
    background: rgba(93,107,122,.08);
    color: rgba(7,26,47,.62);
}}
.parse-generic-notice {{
    background: rgba(93,107,122,.07);
    border-radius: 9px;
    color: rgba(7,26,47,.64);
    font-size: .74rem;
    font-weight: 720;
    line-height: 1.25;
    margin: 0 0 8px;
    padding: 6px 8px;
}}
.parse-tier {{
    border-top: 1px solid rgba(11,31,58,.08);
    padding-top: 7px;
}}
.parse-tier:first-of-type {{
    border-top: 0;
    padding-top: 0;
}}
.parse-tier + .parse-tier {{
    margin-top: 8px;
}}
.parse-tier-title {{
    color: rgba(7,26,47,.58);
    font-size: .72rem;
    font-weight: 850;
    line-height: 1.1;
    margin-bottom: 5px;
}}
.parse-tier-grid {{
    display: grid;
    gap: 5px 7px;
    grid-template-columns: repeat(5, minmax(0, 1fr));
}}
.parse-item {{
    align-items: center;
    border: 1px solid rgba(11,31,58,.08);
    border-radius: 9px;
    display: grid;
    grid-template-columns: 18px minmax(0, 1fr);
    min-height: 34px;
    padding: 5px 7px;
    position: relative;
}}
.parse-item-found {{
    background: rgba(29,126,84,.075);
}}
.parse-item-review {{
    background: rgba(217,119,6,.10);
}}
.parse-item-missing {{
    background: rgba(93,107,122,.055);
}}
.parse-item-conflict {{
    background: rgba(193,18,31,.08);
}}
.parse-icon {{
    font-size: .82rem;
    font-weight: 900;
    line-height: 1;
}}
.parse-item-found .parse-icon {{ color: #14734c; }}
.parse-item-review .parse-icon {{ color: #996000; }}
.parse-item-missing .parse-icon {{ color: rgba(7,26,47,.38); }}
.parse-item-conflict .parse-icon {{ color: #9f111b; }}
.parse-item-main {{
    display: grid;
    gap: 1px;
    min-width: 0;
}}
.parse-item-label {{
    color: rgba(7,26,47,.70);
    font-size: .68rem;
    font-weight: 800;
    line-height: 1.05;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}
.parse-item-value {{
    color: rgba(7,26,47,.94);
    font-size: .78rem;
    font-weight: 850;
    line-height: 1.08;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}
.parse-item-missing .parse-item-value {{
    color: rgba(7,26,47,.46);
    font-weight: 760;
}}
.parse-item[data-detail]:hover::after,
.parse-item[data-detail]:focus::after,
.parse-item[data-detail]:focus-within::after {{
    background: #111827;
    border-radius: 8px;
    bottom: calc(100% + 6px);
    color: #ffffff;
    content: attr(data-detail);
    font-size: .70rem;
    font-weight: 650;
    left: 0;
    line-height: 1.25;
    max-width: 260px;
    min-width: 190px;
    padding: 7px 8px;
    position: absolute;
    z-index: 20;
}}
.parse-item[data-detail]:focus {{
    outline: 2px solid rgba(23,92,211,.35);
    outline-offset: 2px;
}}
.parse-notices {{
    display: grid;
    gap: 4px;
    margin-top: 8px;
}}
.parse-tips {{
    display: grid;
    gap: 4px;
    margin-top: 8px;
}}
.parse-tip {{
    background: rgba(47,95,143,.07);
    border-radius: 9px;
    color: rgba(7,26,47,.70);
    font-size: .73rem;
    font-weight: 720;
    line-height: 1.25;
    padding: 5px 7px;
}}
.parse-notice {{
    border-radius: 9px;
    font-size: .73rem;
    font-weight: 720;
    line-height: 1.25;
    padding: 5px 7px;
}}
.parse-notice-review {{
    background: rgba(217,119,6,.08);
    color: #7c3f00;
}}
.parse-notice-conflict {{
    background: rgba(193,18,31,.08);
    color: #9f111b;
}}
@media (max-width: 1120px) {{
    .parse-tier-grid {{ grid-template-columns: repeat(4, minmax(0, 1fr)); }}
}}
@media (max-width: 860px) {{
    .parse-tier-grid {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
}}
@media (max-width: 620px) {{
    .parse-tier-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
}}
</style>
<section class="parse-coverage" aria-label="Parsed EMR text coverage">
  <div class="parse-head">
    <div class="parse-head-main">
      <div class="parse-title rc-card-title">Parsed</div>
      {source_html}
    </div>
    <div class="parse-coverage-score parse-coverage-score-{coverage_tone}">
      Core fields recognized: {coverage_found}/{coverage_total}
    </div>
  </div>
  {generic_notice}
  {''.join(tier_html)}
  {tips_html}
  <div class="parse-notices">{_notices(warnings, conflicts)}</div>
</section>
"""
