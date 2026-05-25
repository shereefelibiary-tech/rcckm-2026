from html import escape
import re

from ui.theme import component_theme_css


PREVENT_CVD_SCOPE_EXPLAINER = (
    "Atherosclerotic events include heart attack, stroke, or coronary heart disease death. "
    "Cardiovascular events include those plus heart failure."
)


def _display_value(value):
    return getattr(value, "value", value)


def _risk_category(result):
    category = _display_value(getattr(result, "prevent_risk_category", None))
    if category:
        return str(category).replace("_", " ").lower()

    risk = getattr(result, "prevent_10y_ascvd", None)
    if risk is None:
        return "unavailable"

    try:
        value = float(risk)
    except (TypeError, ValueError):
        return "unavailable"

    if value < 3:
        return "low"
    if value < 5:
        return "borderline"
    if value < 10:
        return "intermediate"
    return "high"


def _plain_language_line(risk_value, category):
    if risk_value is None:
        return "PREVENT estimate unavailable from the current data."

    try:
        value = float(risk_value)
    except (TypeError, ValueError):
        return "PREVENT estimate unavailable from the current data."

    people = max(0, int(round(value)))
    category_note = {
        "low": "Estimated population risk remains low.",
        "borderline": "Estimated population risk is borderline.",
        "intermediate": "Estimated population risk is elevated.",
        "high": "Estimated population risk is elevated.",
    }.get(category, "")
    sentence = (
        f"About {people} out of 100 similar patients may experience an "
        "atherosclerotic event over 10 years."
    )
    return f"{sentence} This is the near-term estimated risk. {category_note}".strip()


def _trajectory_line(risk_value):
    if risk_value is None:
        return ""
    try:
        people = max(0, int(round(float(risk_value))))
    except (TypeError, ValueError):
        return ""
    return (
        f"About {people} out of 100 similar patients may experience an atherosclerotic event "
        "over 30 years. This is a longer-term risk trajectory."
    )


def build_prevent_missing_reason(result):
    """Return a clinician-readable explanation of unavailable PREVENT inputs."""
    missing = list(getattr(result, "prevent_missing_inputs", None) or [])
    unsupported = str(getattr(result, "prevent_unsupported_reason", "") or "").strip()
    warnings = [
        str(item).strip()
        for item in (getattr(result, "prevent_warnings", None) or [])
        if str(item).strip()
    ]
    warnings_html = "".join(f"<li>{escape(item)}</li>" for item in warnings)
    warnings_block = (
        f"<div class=\"prevent-note\"><strong>Notes:</strong><ul>{warnings_html}</ul></div>"
        if warnings_html
        else ""
    )

    if missing:
        missing_items = [
            str(item).strip()
            for item in missing
            if str(item).strip()
        ]
        missing_summary = ", ".join(missing_items)
        items = "".join(
            f"<li>{escape(str(item))}</li>"
            for item in missing_items
        )
        return (
            "<div class=\"prevent-missing\">"
            f"<strong>PREVENT unavailable: missing {escape(missing_summary)}.</strong>"
            "<div class=\"prevent-missing-subhead\">Missing inputs:</div>"
            f"<ul>{items}</ul>{warnings_block}</div>"
        )

    if unsupported:
        return f"<div class=\"prevent-missing\">{escape(unsupported)}{warnings_block}</div>"

    return (
        "<div class=\"prevent-missing\">Enter the required PREVENT inputs to "
        f"show the estimate.{warnings_block}</div>"
    )


def _context_line(result):
    if _has_clinical_ascvd(result):
        return "Established ASCVD drives secondary-prevention management; PREVENT should not be used to de-risk treatment."
    if bool(getattr(result, "severe_hypercholesterolemia", False)):
        return "PREVENT is not used to de-risk LDL-C >=190 pathway."

    cac_value = _cac_value_from_result(result)
    cac_missing_line = (
        "Plaque burden is unmeasured. CAC can clarify structural plaque burden "
        "if treatment intensity remains uncertain."
    )
    discordance = getattr(result, "discordance_insight", None) or {}
    if discordance.get("type") == "plaque_exceeds_population_risk":
        if cac_value:
            return (
                f"CAC {cac_value} shows high plaque burden, so treatment intensity "
                "should not rely on PREVENT alone."
            )
        return "High plaque burden is present, so treatment intensity should not rely on PREVENT alone."
    if discordance.get("type") == "risk_exceeds_plaque_burden":
        return "CAC 0 suggests low short-term plaque burden despite elevated estimated population risk."
    if discordance.get("type") == "high_population_risk_plaque_unmeasured":
        return cac_missing_line

    plaque_category = str(_display_value(getattr(result, "plaque_category", "")) or "").upper()
    if plaque_category == "NONE":
        return "CAC 0 suggests low short-term plaque burden."
    if plaque_category in {"MILD", "MODERATE", "SEVERE", "HIGH", "EXTENSIVE"}:
        if cac_value:
            return (
                f"CAC {cac_value} shows high plaque burden, so treatment intensity "
                "should not rely on PREVENT alone."
            )
        return "High plaque burden is present, so treatment intensity should not rely on PREVENT alone."
    if plaque_category == "UNKNOWN":
        return cac_missing_line

    kdigo_stage = getattr(result, "kdigo_stage", None)
    ckm_stage = getattr(result, "ckm_stage", None) or {}
    ckm_drivers = " ".join(str(driver).lower() for driver in ckm_stage.get("drivers", []))
    if kdigo_stage or any(term in ckm_drivers for term in ("ckd", "a1c", "diabetes", "tg", "bmi")):
        return "Kidney/metabolic disease contributes to estimated risk."

    return cac_missing_line


def _cac_value_from_result(result):
    candidates = []
    candidates.extend(getattr(result, "top_drivers", None) or [])
    candidates.extend(getattr(result, "snapshot_lines", None) or [])
    ckm_stage = getattr(result, "ckm_stage", None) or {}
    if isinstance(ckm_stage, dict):
        candidates.extend(ckm_stage.get("drivers", []) or [])

    discordance = getattr(result, "discordance_insight", None) or {}
    if isinstance(discordance, dict):
        candidates.extend(str(v) for v in discordance.values() if v is not None)

    for item in candidates:
        match = re.search(r"\bCAC\s*=?\s*(\d+(?:\.\d+)?)\b", str(item), flags=re.I)
        if match:
            try:
                return f"{float(match.group(1)):g}"
            except (TypeError, ValueError):
                return match.group(1)
    return ""


def _has_clinical_ascvd(result):
    if bool(getattr(result, "clinical_ascvd", False)):
        return True
    ckm_stage = getattr(result, "ckm_stage", None) or {}
    if isinstance(ckm_stage, dict):
        return any("clinical ascvd" in str(driver).lower() for driver in ckm_stage.get("drivers", []) or [])
    return False


def _value_from_fields(result, field_names):
    for field_name in field_names:
        value = getattr(result, field_name, None)
        if value is not None:
            return value
    return None


def _total_cvd_value(result):
    return _value_from_fields(
        result,
        (
            "prevent_10y_total_cvd",
            "prevent_total_cvd_10y",
            "prevent_10y_total_cvd_pct",
            "total_cvd_10y_pct",
        ),
    )


def _ascvd_30y_value(result):
    return _value_from_fields(
        result,
        (
            "prevent_30y_ascvd",
            "prevent_30y_ascvd_pct",
            "ascvd_30y_pct",
        ),
    )


def _total_cvd_30y_value(result):
    return _value_from_fields(
        result,
        (
            "prevent_30y_total_cvd",
            "prevent_total_cvd_30y",
            "prevent_30y_total_cvd_pct",
            "total_cvd_30y_pct",
        ),
    )


def _prevent_age_value(result):
    return _value_from_fields(result, ("prevent_age", "prevent_cardiovascular_age"))


def _prevent_percentile_value(result):
    return _value_from_fields(result, ("prevent_percentile", "prevent_risk_percentile"))


def _pct(value):
    if value is None:
        return ""
    try:
        return f"{float(value):g}%"
    except (TypeError, ValueError):
        return ""


def _prevent_matrix_html(risk_value, total_value, ascvd_30y_value, total_cvd_30y_value):
    def cell(value):
        return f'<span class="value">{escape(value or "--")}</span>'

    return (
        "<table class='prevent-matrix'>"
        "<thead><tr><th></th><th>10-year</th><th>30-year</th></tr></thead>"
        "<tbody>"
        f"<tr><th>Atherosclerotic event risk</th><td>{cell(risk_value)}</td><td>{cell(ascvd_30y_value)}</td></tr>"
        f"<tr><th>Cardiovascular event risk</th><td>{cell(total_value)}</td><td>{cell(total_cvd_30y_value)}</td></tr>"
        "</tbody></table>"
    )


def _prevent_category_legend_html(category: str) -> str:
    normalized = str(category or "").strip().lower()
    items = [
        ("low", "Low &lt;3%"),
        ("borderline", "Borderline 3&ndash;&lt;5%"),
        ("intermediate", "Intermediate 5&ndash;&lt;10%"),
        ("high", "High &ge;10%"),
    ]
    parts = []
    for key, label in items:
        cls = "prevent-legend-active" if key == normalized else ""
        parts.append(f'<span class="{cls}">{label}</span>' if cls else f"<span>{label}</span>")
    return (
        '<div class="prevent-line prevent-risk-legend">'
        "10-year PREVENT risk: "
        + " <span class=\"prevent-legend-dot\">&middot;</span> ".join(parts)
        + "</div>"
    )


def _rcckm_level_html(result) -> str:
    classification = getattr(result, "level_classification", None) or {}
    label = str(classification.get("label") or "").strip()
    if not label:
        return ""
    return (
        '<div class="prevent-line prevent-rcckm-note">'
        "<span>RCCKM:</span> "
        + escape(label.replace("—", "-"))
        + "</div>"
    )


def render_prevent_card(result):
    """Render the PREVENT population-risk card as HTML."""
    risk = getattr(result, "prevent_10y_ascvd", None)
    total_cvd = _total_cvd_value(result)
    ascvd_30y = _ascvd_30y_value(result)
    total_cvd_30y = _total_cvd_30y_value(result)
    prevent_age = _prevent_age_value(result)
    prevent_percentile = _prevent_percentile_value(result)
    category = _risk_category(result)
    available = bool(getattr(result, "prevent_available", False)) or risk is not None
    clinical_ascvd = _has_clinical_ascvd(result)
    value = "--"
    if risk is not None:
        try:
            value = f"{float(risk):g}%"
        except (TypeError, ValueError):
            value = "--"
    total_value = _pct(total_cvd)
    ascvd_30y_value = _pct(ascvd_30y)
    total_cvd_30y_value = _pct(total_cvd_30y)
    risk_value = _pct(risk)

    explanation = _plain_language_line(risk, category)
    trajectory = _trajectory_line(ascvd_30y)
    context = _context_line(result)
    category_legend_html = _prevent_category_legend_html(category)
    rcckm_level_html = _rcckm_level_html(result)
    matrix_html = (
        _prevent_matrix_html(risk_value, total_value, ascvd_30y_value, total_cvd_30y_value)
        if any((risk_value, total_value, ascvd_30y_value, total_cvd_30y_value))
        else ""
    )
    extra_metrics = []
    model_used = str(getattr(result, "prevent_model_used", "") or "").strip()
    if model_used.lower() == "provided":
        extra_metrics.append(("Source", "PREVENT values entered directly."))
    if prevent_age is not None:
        extra_metrics.append(("PREVENT-age", f"{float(prevent_age):g} years"))
    if prevent_percentile is not None:
        extra_metrics.append(("PREVENT percentile", f"{float(prevent_percentile):g}%"))
    extra_metrics_html = "".join(
        f'<div class="prevent-metric"><span>{escape(label)}</span><strong>{escape(val)}</strong></div>'
        for label, val in extra_metrics
    )
    trajectory_html = (
        f'<div class="prevent-line prevent-trajectory">{escape(trajectory)}</div>'
        if trajectory
        else ""
    )
    cvd_scope_html = (
        f'<div class="prevent-line prevent-scope">{escape(PREVENT_CVD_SCOPE_EXPLAINER)}</div>'
        if available and risk is not None and (total_value or total_cvd_30y_value)
        else ""
    )
    model_note_items = []
    for item in (getattr(result, "prevent_warnings", None) or []):
        text = str(item).strip()
        if "UACR missing" not in text:
            continue
        if "PREVENT model used" in text:
            text = "UACR missing; PREVENT calculated without UACR."
        model_note_items.append(text)
    model_note_html = (
        f'<div class="prevent-line prevent-model-note">{escape(model_note_items[0])}</div>'
        if available and model_note_items
        else ""
    )
    if available and ascvd_30y is None:
        unsupported = str(getattr(result, "prevent_unsupported_reason", "") or "").strip()
        trajectory_html = (
            '<div class="prevent-line prevent-trajectory">'
            + escape(unsupported or "30-year PREVENT estimate unavailable for the current data/age range.")
            + "</div>"
        )

    unavailable_html = ""
    if not available:
        explanation = "PREVENT estimate unavailable"
        context = "Complete the missing worksheet inputs to calculate estimated population risk."
        unavailable_html = build_prevent_missing_reason(result)

    if clinical_ascvd:
        value = "--"
        category = "established ASCVD"
        explanation = "PREVENT is not used for treatment decisions in established ASCVD."
        matrix_html = ""
        cvd_scope_html = ""
        extra_metrics_html = ""
        trajectory_html = ""
        category_legend_html = ""
        rcckm_level_html = ""

    return f"""\
<style>
{component_theme_css()}
.prevent-card {{
    height: auto;
    margin: 10px 0 14px;
    overflow: visible;
    padding: 16px 18px 18px;
}}
.prevent-top {{
    align-items: start;
    display: grid;
    gap: 14px;
    grid-template-columns: minmax(0, 1fr) auto;
}}
.prevent-title {{
    color: var(--rc-text);
    font-family: var(--rc-font-body);
    font-size: 1.04rem;
    font-weight: 750;
    letter-spacing: 0;
    line-height: 1.15;
    margin-bottom: 8px;
}}
.prevent-subtitle {{
    color: rgba(7, 26, 47, 0.62);
    font-size: 0.86rem;
    font-weight: 700;
    line-height: 1.25;
    margin-top: 0.28rem;
}}
.prevent-kicker {{
    color: rgba(47, 95, 143, 0.88);
    font-family: var(--rc-font-body);
    font-size: 0.74rem;
    font-weight: 780;
    letter-spacing: 0.01em;
    margin-bottom: 0.28rem;
    text-transform: none;
}}
.prevent-primary {{
    align-items: flex-end;
    display: flex;
    flex-direction: column;
    min-width: 150px;
}}
.prevent-value {{
    color: var(--rc-text);
    font-size: 2.18rem;
    font-weight: 900;
    letter-spacing: -0.035em;
    line-height: 0.95;
    white-space: nowrap;
}}
.prevent-category {{
    border: 1px solid rgba(47, 95, 143, 0.24);
    border-radius: 999px;
    background: rgba(47, 95, 143, 0.08);
    color: var(--rc-primary-2);
    display: inline-flex;
    font-size: 0.76rem;
    font-weight: 850;
    line-height: 1;
    margin-top: 0.42rem;
    padding: 0.38rem 0.62rem;
    text-transform: none;
}}
.prevent-category-high {{
    border-color: rgba(115, 0, 10, 0.28);
    background: var(--rc-garnet-tint);
    color: var(--rc-garnet);
}}
.prevent-middle {{
    align-items: start;
    display: grid;
    gap: 10px;
    grid-template-columns: minmax(280px, 1fr) auto;
    margin-top: 12px;
}}
.prevent-matrix {{
    border-collapse: collapse;
    color: var(--rc-text);
    font-size: 0.88rem;
    width: 100%;
}}
.prevent-matrix th,
.prevent-matrix td {{
    border-bottom: 1px solid rgba(11, 31, 58, 0.08);
    padding: 8px 10px;
    text-align: right;
    white-space: nowrap;
}}
.prevent-matrix thead th {{
    background: rgba(17, 17, 17, 0.045);
    border-bottom: 1px solid rgba(17, 17, 17, 0.12);
    color: rgba(17, 17, 17, 0.68);
    font-size: 0.76rem;
    font-weight: 750;
    padding: 7px 10px;
}}
.prevent-matrix tbody tr:nth-child(odd) {{
    background: rgba(255, 253, 248, 0.88);
}}
.prevent-matrix tbody tr:nth-child(even) {{
    background: rgba(115, 0, 10, 0.035);
}}
.prevent-matrix tbody th {{
    color: rgba(7, 26, 47, 0.68);
    font-weight: 850;
    text-align: left;
}}
.prevent-matrix td {{
    font-weight: 900;
}}
.prevent-matrix .value {{
    color: var(--rc-text);
    font-weight: 850;
}}
.prevent-matrix tr:last-child th,
.prevent-matrix tr:last-child td {{
    border-bottom: none;
}}
.prevent-metric {{
    color: rgba(7, 26, 47, 0.64);
    display: flex;
    gap: 8px;
    justify-content: flex-end;
    font-size: 0.78rem;
    font-weight: 700;
    line-height: 1.15;
}}
.prevent-metric strong {{
    color: var(--rc-black);
    font-weight: 900;
}}
.prevent-extra-metrics {{
    min-width: 170px;
    padding-top: 25px;
}}
.prevent-body {{
    display: grid;
    gap: 7px;
    margin-top: 10px;
    overflow: visible;
}}
.prevent-line {{
    color: rgba(7, 26, 47, 0.78);
    font-size: 0.86rem;
    font-weight: 650;
    line-height: 1.3;
}}
.prevent-context {{
    color: rgba(7, 26, 47, 0.66);
}}
.prevent-trajectory {{
    color: rgba(7, 26, 47, 0.66);
}}
.prevent-scope {{
    border-top: 1px solid var(--rc-border-soft);
    color: rgba(7, 26, 47, 0.56);
    font-size: 0.78rem;
    font-weight: 620;
    padding-top: 8px;
}}
.prevent-model-note {{
    color: rgba(138, 75, 0, 0.82);
    font-size: 0.78rem;
    font-weight: 700;
}}
.prevent-rcckm-note {{
    background: rgba(115, 0, 10, 0.055);
    border-left: 3px solid rgba(115, 0, 10, 0.34);
    color: rgba(34, 34, 34, 0.78);
    font-size: 0.80rem;
    font-weight: 650;
    padding: 5px 8px;
}}
.prevent-rcckm-note span {{
    color: var(--rc-garnet);
    font-weight: 850;
}}
.prevent-risk-legend {{
    color: rgba(7, 26, 47, 0.54);
    font-size: 0.76rem;
    font-weight: 620;
}}
.prevent-risk-legend span {{
    white-space: nowrap;
}}
.prevent-risk-legend .prevent-legend-active {{
    color: var(--rc-garnet);
    font-weight: 900;
}}
.prevent-legend-dot {{
    color: rgba(47, 95, 143, 0.48);
    padding: 0 1px;
}}
.prevent-missing {{
    border-top: 1px solid rgba(11, 31, 58, 0.10);
    color: rgba(7, 26, 47, 0.72);
    font-size: 0.84rem;
    font-weight: 650;
    grid-column: 1 / -1;
    line-height: 1.32;
    padding-top: 10px;
}}
.prevent-missing strong {{
    color: var(--rc-black);
    font-weight: 850;
}}
.prevent-missing-subhead {{
    color: rgba(7, 26, 47, 0.66);
    font-weight: 800;
    margin-top: 5px;
}}
.prevent-missing ul {{
    columns: 2;
    margin: 5px 0 0 18px;
    padding: 0;
}}
.prevent-missing li {{
    break-inside: avoid;
    margin: 1px 0;
}}
.prevent-note {{
    margin-top: 7px;
}}
@media (max-width: 760px) {{
    .prevent-top,
    .prevent-middle,
    .prevent-body {{
        grid-template-columns: 1fr;
        display: grid;
    }}
    .prevent-primary {{
        align-items: flex-start;
    }}
    .prevent-value {{
        font-size: 1.95rem;
    }}
    .prevent-extra-metrics {{
        padding-top: 0;
    }}
}}
</style>
<div class="prevent-card rc-panel">
<div class="prevent-top">
<div>
<div class="prevent-kicker">PREVENT population model</div>
<div class="prevent-title rc-card-title">10-Year Cardiovascular Risk</div>
<div class="prevent-subtitle">Estimated population risk before plaque and treatment context.</div>
</div>
<div class="prevent-primary">
<div class="prevent-value rc-metric">{escape(value)}</div>
<div class="prevent-category prevent-category-{escape(category)}">{escape(category)}</div>
</div>
</div>
<div class="prevent-middle">
<div>{matrix_html}</div>
<div class="prevent-extra-metrics">{extra_metrics_html}</div>
</div>
<div class="prevent-body">
<div class="prevent-line">{escape(explanation)}</div>
{trajectory_html}
<div class="prevent-line prevent-context">{escape(context)}</div>
{model_note_html}
{rcckm_level_html}
{category_legend_html}
{cvd_scope_html}
{unavailable_html}
</div>
</div>
""".strip()
