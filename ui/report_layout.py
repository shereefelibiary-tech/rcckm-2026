import importlib
from html import escape

from core.engine import evaluate_patient
from core.patient import Patient
from modules.actions.scaffold import (
    build_action_instrument_panel,
    build_compact_action_detail_lines,
)
from modules.lipids.non_hdl import (
    format_non_hdl_display,
    should_show_non_hdl_default,
)
from modules.rss.engine import (
    build_rss_contributions,
    build_rss_transparency,
    calculate_rss_total,
)
from modules.snapshot.engine import build_snapshot_lines

from ui.diagnosis_confirm_panel import render_diagnosis_confirm_panel
from ui.emr_copy_box import render_emr_copy_box
from ui.export_print import render_export_print_section
from ui.html import render_component_html, render_html
from ui.theme import component_theme_css


def demo_patient():
    return Patient(
        age=55,
        sex="male",
        sbp=132,
        dbp=82,
        bp_treated=True,
        tc=205,
        ldl_c=132,
        hdl_c=48,
        triglycerides=180,
        non_hdl_c=157,
        apob=110,
        lp_a_value=80,
        lp_a_unit="nmol/L",
        a1c=7.1,
        diabetes=True,
        height_in=69,
        weight_lb=210,
        bmi=31,
        creatinine=1.15,
        egfr=55,
        uacr=45,
        cac=350,
        cac_percentile=94,
        clinical_ascvd=False,
        smoker=False,
        smoking=False,
        family_history_premature_ascvd=True,
        premature_fhx_ascvd=True,
        family_history_relationship="father",
        family_history_event_type="mi",
        family_history_age_at_event=49,
        family_history_summary="Father MI age 49",
        hscrp=2.4,
        inflammatory_disease=False,
        rheumatoid_arthritis=False,
        sle=False,
        psoriasis=False,
        ibd=False,
        hiv=False,
        osa=True,
        masld=True,
        lipid_lowering=False,
        sglt2=False,
        glp1=False,
        ace_arb=True,
    )


def run_patient(patient):
    result = evaluate_patient(patient)
    rss_contributions = build_rss_contributions(patient, result)
    for contribution in rss_contributions:
        if contribution.label == "Diabetes" and getattr(patient, "a1c", None):
            contribution.actual_value = patient.a1c
    rss_total = calculate_rss_total(rss_contributions)
    result.rss_total = rss_total
    result.rss_category = _rss_interpretation(rss_total)
    build_rss_transparency(patient, result, rss_contributions)
    result.snapshot_lines = build_snapshot_lines(result)
    return result, rss_total, rss_contributions


def _rss_interpretation(rss_total):
    if rss_total >= 75:
        return "Severe"
    if rss_total >= 50:
        return "High"
    if rss_total >= 25:
        return "Moderate"
    return "Low"


def _display_value(value):
    return getattr(value, "value", value)


def _fmt(value, suffix=""):
    if value is None:
        return "-"
    try:
        return f"{float(value):g}{suffix}"
    except (TypeError, ValueError):
        return f"{value}{suffix}"


def _metric(label, value, note=""):
    return (
        '<div class="rcckm-metric">'
        f'<div class="rcckm-metric-label">{escape(label)}</div>'
        f'<div class="rcckm-metric-value">{escape(str(value))}</div>'
        f'<div class="rcckm-metric-note">{escape(str(note))}</div>'
        "</div>"
    )


def _section_header_html(title, subtitle):
    return f"""
<div class="rc-report" style="margin: 14px 0 7px;">
    <div class="rc-eyebrow">{escape(title)}</div>
    <div class="rc-muted">{escape(subtitle)}</div>
</div>
"""


def _details_header_html():
    return """
<style>
/*COMPONENT_THEME*/
.details-band {
    border-top: 1px solid var(--rc-line);
    color: var(--rc-black);
    font-family: var(--rc-font-title);
    font-size: 1.05rem;
    font-weight: 700;
    letter-spacing: -0.01em;
    margin: 18px 0 6px;
    padding-top: 10px;
}
.detail-section-head {
    align-items: baseline;
    border-top: 1px solid rgba(11,31,58,0.10);
    display: flex;
    gap: 10px;
    justify-content: space-between;
    margin: 12px 0 6px;
    padding-top: 9px;
}
.detail-section-title {
    color: var(--rc-black);
    font-family: var(--rc-font-body);
    font-size: 1.0rem;
    font-weight: 750;
    letter-spacing: 0;
    line-height: 1.15;
}
.detail-section-note {
    color: rgba(7,26,47,0.52);
    font-size: 0.74rem;
    font-weight: 700;
    line-height: 1.2;
    text-align: right;
}
.ckm-kdigo-strip {
    border: 1px solid var(--rc-line);
    border-radius: 12px;
    background: rgba(255,253,248,0.72);
    color: var(--rc-black);
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px 16px;
    padding: 10px 12px;
}
.ckm-kdigo-item {
    min-width: 0;
}
.ckm-kdigo-label {
    color: rgba(47,95,143,0.88);
    font-size: 0.68rem;
    font-weight: 900;
    letter-spacing: 0.08em;
    line-height: 1;
    text-transform: uppercase;
}
.ckm-kdigo-value {
    color: var(--rc-black);
    font-size: 0.95rem;
    font-weight: 900;
    line-height: 1.15;
    margin-top: 3px;
}
.ckm-kdigo-desc {
    color: rgba(7,26,47,0.62);
    font-size: 0.76rem;
    font-weight: 650;
    line-height: 1.22;
    margin-top: 3px;
}
.ckm-kdigo-muted {
    grid-column: 1 / -1;
    color: rgba(7,26,47,0.58);
    font-size: 0.76rem;
    font-weight: 680;
    line-height: 1.22;
    padding-top: 2px;
}
@media (max-width: 560px) {
    .ckm-kdigo-strip {
        grid-template-columns: 1fr;
    }
}
</style>
<div class="details-band">Details</div>
""".replace("/*COMPONENT_THEME*/", component_theme_css())


def _detail_section_header_html(title, note=""):
    note_html = f'<div class="detail-section-note">{escape(note)}</div>' if note else ""
    return (
        '<div class="detail-section-head">'
        f'<div class="detail-section-title">{escape(title)}</div>'
        f"{note_html}"
        "</div>"
    )


def _snapshot_synthesis_lines(result):
    lines = []

    ckm_stage = getattr(result, "ckm_stage", None)
    if ckm_stage:
        drivers = ckm_stage.get("drivers") or []
        line = f"CKM stage: Stage {ckm_stage.get('stage')}"
        if drivers:
            line = f"{line} - {'; '.join(drivers[:2])}"
        lines.append(line)

    clarification = getattr(result, "clarification", None) or {}
    if clarification.get("tier", 0) >= 2 and clarification.get("summary"):
        lines.append(f"Clarification: {clarification.get('summary')}")

    discordance = getattr(result, "discordance_insight", None) or {}
    if discordance.get("status") in {"discordant", "uncertain"} and discordance.get("headline"):
        lines.append(f"Discordance: {discordance.get('headline')}")

    return lines


def _build_snapshot_card_html(patient, result):
    metrics = [
        _metric("Risk level", _display_value(result.risk_level) or "-"),
        _metric("RSS", f"{_fmt(result.rss_total)}/100", result.rss_category or ""),
        _metric("PREVENT", _fmt(result.prevent_10y_ascvd, "%"), "10-year artery-event"),
        _metric("CAC", _fmt(getattr(patient, "cac", None)), "plaque burden"),
        _metric("ApoB", _fmt(getattr(patient, "apob", None), " mg/dL"), "particle burden"),
        _metric("A1c", _fmt(getattr(patient, "a1c", None), "%"), "glycemia"),
        _metric("Kidney", result.kdigo_stage or "-", "KDIGO"),
        _metric(
            "UACR/eGFR",
            f"{_fmt(getattr(patient, 'uacr', None))}/{_fmt(getattr(patient, 'egfr', None))}",
            "mg/g / mL/min",
        ),
    ]
    synthesis_rows = "".join(
        f'<div class="rcckm-list-row">{escape(line)}</div>'
        for line in _snapshot_synthesis_lines(result)
    )
    synthesis_block = (
        f'<div style="height:10px;"></div><div class="rcckm-compact-list">{synthesis_rows}</div>'
        if synthesis_rows
        else ""
    )
    return f"""
<div class="rcckm-card rc-panel">
    <div class="rc-eyebrow">Clinical synthesis</div>
    <div class="rc-card-title">Snapshot</div>
    <div class="rcckm-metric-grid">{''.join(metrics)}</div>
    {synthesis_block}
</div>
"""


def _target_context_line(result, target, patient=None):
    rationale = (getattr(target, "rationale", None) or "").strip()
    cac = getattr(patient, "cac", None) if patient is not None else None
    clinical_ascvd = bool(getattr(patient, "clinical_ascvd", False)) if patient is not None else False

    if clinical_ascvd:
        if getattr(target, "ldl_c_target", None) == 55:
            return (
                "Very-high-risk ASCVD targets; <70 mg/dL is the minimum "
                "secondary-prevention LDL threshold."
            )
        return "Secondary-prevention targets; LDL-C <70 mg/dL is the minimum threshold."

    if "Clinical ASCVD" in rationale or "Very-high-risk ASCVD" in rationale:
        return rationale

    if cac is not None:
        try:
            cac_value = float(cac)
        except (TypeError, ValueError):
            cac_value = None
        if cac_value is not None and cac_value >= 300:
            return f"High plaque burden (CAC {cac_value:g})."
        if cac_value is not None and cac_value > 0:
            return f"Structural plaque burden (CAC {cac_value:g})."
        if cac_value == 0:
            return "CAC 0: no plaque-derived lipid target assigned."

    if "PREVENT" in rationale:
        prevent_value = getattr(result, "prevent_10y_ascvd", None)
        if prevent_value is not None:
            return f"PREVENT-informed primary-prevention target range ({float(prevent_value):g}%)."
        return "PREVENT-informed primary-prevention target range."

    if "primary prevention" in rationale.lower():
        return "Primary-prevention target range."

    return rationale or "No target pathway assigned yet."


def _num_or_none(value):
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def build_primary_targets_display(patient, result, detail_mode=False):
    """Build display-only target rows without changing target assignment logic."""
    target = result.targets[0] if getattr(result, "targets", None) else None
    if not target:
        return []

    items = []
    ldl_current = _num_or_none(getattr(patient, "ldl_c", None)) if patient is not None else None
    apob_current = _num_or_none(getattr(patient, "apob", None)) if patient is not None else None
    triglycerides = (
        _num_or_none(getattr(patient, "triglycerides", None)) if patient is not None else None
    )

    if target.ldl_c_target is not None:
        items.append(
            {
                "label": "LDL-C",
                "target": target.ldl_c_target,
                "current_value": ldl_current,
                "unit": "mg/dL",
                "display_priority": "primary",
                "show_default": True,
                "rationale": "Primary actionable cholesterol target.",
            }
        )

    if target.apob_target is not None:
        apob_detail = ""
        if apob_current is None:
            apob_detail = "Obtain for particle burden clarification."
        items.append(
            {
                "label": "ApoB",
                "target": target.apob_target,
                "current_value": apob_current,
                "unit": "mg/dL",
                "display_priority": "primary",
                "show_default": True,
                "rationale": apob_detail or "RCCKM advanced particle target.",
            }
        )

    severe_tg = triglycerides is not None and triglycerides >= 500
    dominant_tg = "triglyceride" in str(getattr(result, "dominant_action", "") or "").lower()
    if triglycerides is not None and (severe_tg or dominant_tg or detail_mode):
        tg_goal = 500 if triglycerides >= 500 else 150
        items.append(
            {
                "label": "Triglycerides",
                "target": tg_goal,
                "current_value": triglycerides,
                "unit": "mg/dL",
                "display_priority": "primary" if severe_tg or dominant_tg else "secondary",
                "show_default": severe_tg or dominant_tg,
                "rationale": (
                    "Pancreatitis-risk TG pathway active."
                    if triglycerides >= 1000
                    else "Severe hypertriglyceridemia pathway active."
                    if severe_tg
                    else "Clinician detail lipid marker."
                ),
            }
        )

    show_non_hdl = False
    if patient is not None:
        show_non_hdl = should_show_non_hdl_default(
            patient,
            result,
            {"clinician_detail_mode": detail_mode},
        )
    if show_non_hdl:
        non_hdl = format_non_hdl_display(patient, result)
        if non_hdl:
            apob_missing = apob_current is None
            items.append(
                {
                    "label": "non-HDL-C",
                    "target": non_hdl["target_value"],
                    "current_value": non_hdl["current_value"],
                    "unit": "mg/dL",
                    "display_priority": "secondary",
                    "show_default": detail_mode or apob_missing,
                    "rationale": non_hdl["subtitle"],
                }
            )

    return [item for item in items if detail_mode or item["show_default"]]


def _build_targets_html(result, patient=None, *, clinician_detail_mode=False):
    assigned_targets = build_primary_targets_display(
        patient,
        result,
        detail_mode=clinician_detail_mode,
    )
    if not assigned_targets:
        return ""

    target = result.targets[0] if result.targets else None
    context_line = _target_context_line(result, target, patient)

    def _fmt_target_number(value):
        try:
            return f"{float(value):g}"
        except (TypeError, ValueError):
            return str(value)

    def _target_item(item):
        label = item["label"]
        target_value = item.get("target")
        current_value = item.get("current_value")
        unit = item.get("unit") or "mg/dL"
        rationale = item.get("rationale") or ""
        apob_missing = label == "ApoB" and current_value is None
        target_html = ""
        if target_value is not None and not apob_missing:
            target_html = (
                f'<span class="target-goal">&lt;{_fmt_target_number(target_value)} {escape(unit)}</span>'
            )
        current_html = ""
        if current_value is not None:
            current_html = (
                f'<span class="target-current">Current {_fmt_target_number(current_value)}</span>'
            )
        elif apob_missing:
            current_html = '<span class="target-current">Obtain for particle burden clarification</span>'
        rationale_html = ""
        if rationale and label in {"Triglycerides", "non-HDL-C"}:
            rationale_html = f'<span class="target-note">{escape(rationale)}</span>'
        return (
            '<span class="target-item">'
            '<span class="target-main">'
            f'<span class="target-name">{escape(label)}</span>'
            f"{target_html}"
            "</span>"
            f"{current_html}"
            f"{rationale_html}"
            "</span>"
        )

    primary_targets = " ".join(
        _target_item(item)
        for item in assigned_targets
        if item["display_priority"] == "primary"
    )
    secondary_targets = " ".join(
        _target_item(item)
        for item in assigned_targets
        if item["display_priority"] == "secondary"
    )
    secondary_html = ""
    if secondary_targets:
        secondary_html = (
            '<details class="target-details">'
            '<summary>Show lipid details</summary>'
            f'<div class="target-secondary">{secondary_targets}</div>'
            "</details>"
        )
    rationale_html = ""
    if context_line:
        rationale_html = (
            '<details class="target-details target-rationale-details">'
            '<summary>Show target rationale</summary>'
            f'<div class="targets-context">{escape(context_line)}</div>'
            "</details>"
        )
    return f"""
<style>
{component_theme_css()}
.targets-compact {{
    padding: 15px 17px 16px;
    margin: 12px 0 14px;
}}
.targets-title {{
    color: var(--rc-text);
    font-family: var(--rc-font-body);
    font-size: 1.04rem;
    font-weight: 750;
    letter-spacing: 0;
    line-height: 1.15;
    margin-bottom: 8px;
}}
.target-line {{
    color: var(--rc-black);
    display: grid;
    gap: 7px;
    font-family: var(--rc-font-body);
    font-size: 0.94rem;
    font-weight: 650;
    line-height: 1.35;
}}
.target-item {{
    align-items: baseline;
    display: grid;
    gap: 8px;
    grid-template-columns: minmax(130px, 1fr) auto;
}}
.target-main {{
    display: inline-flex;
    gap: 6px;
    min-width: 0;
}}
.target-name {{
    font-weight: 800;
}}
.target-current {{
    color: rgba(7, 26, 47, 0.56);
    font-size: 0.82rem;
    font-weight: 600;
    text-align: right;
}}
.target-secondary {{
    color: rgba(7, 26, 47, 0.58);
    display: grid;
    gap: 5px;
    font-size: 0.78rem;
    font-weight: 600;
    line-height: 1.3;
    margin-top: 5px;
}}
.target-secondary .target-name,
.target-secondary .target-goal {{
    font-weight: 680;
}}
.target-note {{
    margin-left: 8px;
}}
.target-details {{
    color: rgba(7, 26, 47, 0.58);
    font-size: 0.78rem;
    font-weight: 600;
    margin-top: 5px;
}}
.target-details summary {{
    cursor: pointer;
    display: inline-flex;
    font-weight: 680;
    list-style: none;
}}
.target-details summary::-webkit-details-marker {{
    display: none;
}}
.targets-context {{
    color: rgba(7, 26, 47, 0.68);
    font-size: 0.86rem;
    font-weight: 650;
    line-height: 1.32;
    margin-top: 5px;
}}
@media(max-width: 520px) {{
    .target-item {{
        align-items: start;
        grid-template-columns: 1fr;
        gap: 1px;
    }}
    .target-current {{
        text-align: left;
    }}
}}
</style>
<div class="targets-compact rc-panel">
<div class="targets-title rc-card-title">Targets</div>
<div class="target-line">{primary_targets}</div>
{secondary_html}
{rationale_html}
</div>
"""


def _build_action_html(result, patient=None):
    if not result.dominant_action and not result.recommendations:
        return ""

    items = build_action_instrument_panel(patient, result)
    details = build_compact_action_detail_lines(patient, result)
    line_html = "".join(
        (
            f'<div class="action-domain action-domain-{escape(item.state)} action-priority-{escape(item.priority)}">'
            f'<div class="action-domain-label">{escape(item.label)}:</div>'
            '<div class="action-copy">'
            f'<div class="action-status">{escape(item.status)}</div>'
            + (f'<div class="action-detail">{escape(item.detail)}</div>' if item.detail else "")
            + "</div>"
            + "</div>"
        )
        for item in items
    )
    detail_html = ""
    if details:
        rows = "".join(f"<li>{escape(detail)}</li>" for detail in details)
        detail_html = (
            '<details class="action-details">'
            '<summary>Show details</summary>'
            f"<ul>{rows}</ul>"
            "</details>"
        )

    style = (
        "<style>"
        ".action-card{padding:14px 16px 15px;}"
        ".action-readout{display:grid;gap:0;}"
        ".action-domain{border-top:1px solid rgba(7,26,47,0.075);display:grid;grid-template-columns:148px minmax(0,1fr);padding:8px 0 9px;}"
        ".action-domain:first-child{border-top:0;padding-top:2px;}"
        ".action-domain-label{color:rgba(7,26,47,0.70);font-family:var(--rc-font-body);font-size:0.86rem;font-weight:800;line-height:1.24;}"
        ".action-copy{min-width:0;}"
        ".action-status{color:var(--rc-black);font-family:var(--rc-font-body);font-size:0.90rem;font-weight:760;line-height:1.24;overflow-wrap:anywhere;}"
        ".action-detail{color:rgba(7,26,47,0.60);font-family:var(--rc-font-body);font-size:0.80rem;font-weight:580;line-height:1.24;margin-top:2px;}"
        ".action-domain-neutral .action-status,.action-domain-complete .action-status{color:rgba(7,26,47,0.66);font-weight:700;}"
        ".action-details{border-top:1px solid rgba(7,26,47,0.08);color:rgba(7,26,47,0.62);font-family:var(--rc-font-body);font-size:0.76rem;font-weight:620;line-height:1.28;margin-top:8px;padding-top:8px;}"
        ".action-details summary{cursor:pointer;font-weight:800;color:rgba(47,95,143,0.82);}"
        ".action-details ul{margin:5px 0 0 18px;padding:0;}"
        ".action-details li{margin:2px 0;}"
        "@media(max-width:760px){.action-domain{grid-template-columns:1fr;gap:2px;padding:8px 0;}}"
        "</style>"
    )
    return (
        style
        + '<div class="rcckm-card rc-panel action-card">'
        + '<div class="rcckm-card-title rc-card-title">Action</div>'
        + f'<div class="action-readout">{line_html}</div>'
        + detail_html
        + "</div>"
    )


def _build_ckm_rail_html(result):
    ckm_stage = getattr(result, "ckm_stage", None)
    if not ckm_stage:
        return ""

    stage = ckm_stage.get("stage")
    drivers = ckm_stage.get("drivers") or []
    headline = ckm_stage.get("headline") or f"Stage {stage}"
    stage_rows = []
    for level in [4, 3, 2, 1, 0]:
        active = level == stage
        driver_line = ""
        if active and drivers:
            driver_line = f"<div class='ckm-driver'>{escape('; '.join(drivers[:2]))}</div>"
        stage_rows.append(
            f"""
            <div class="ckm-row{' ckm-active' if active else ''}">
                <div class="ckm-dot"></div>
                <div>
                    <div class="ckm-stage">Stage {level}</div>
                    {driver_line}
                </div>
            </div>
            """
        )

    return f"""
<style>
{component_theme_css()}
.ckm-card {{
    padding: 16px 18px 18px;
    font-family: var(--rc-font-body);
}}
.ckm-title {{
    color: var(--rc-primary);
    font-family: var(--rc-font-title);
    font-size: 1.08rem;
    font-weight: 700;
    margin-bottom: 4px;
}}
.ckm-headline {{
    color: rgba(7, 26, 47, 0.68);
    font-size: 0.82rem;
    font-weight: 650;
    line-height: 1.28;
    margin-bottom: 12px;
}}
.ckm-stack {{
    display: flex;
    flex-direction: column;
    gap: 8px;
}}
.ckm-row {{
    display: grid;
    grid-template-columns: 13px minmax(0, 1fr);
    gap: 9px;
    align-items: start;
    border: 1px solid rgba(11, 31, 58, 0.10);
    border-radius: 11px;
    background: rgba(255, 253, 248, 0.72);
    padding: 8px 10px;
}}
.ckm-row.ckm-active {{
    border-color: rgba(11, 31, 58, 0.28);
    background: rgba(47, 95, 143, 0.08);
}}
.ckm-dot {{
    width: 10px;
    height: 10px;
    border-radius: 999px;
    border: 2px solid rgba(11, 31, 58, 0.30);
    margin-top: 3px;
}}
.ckm-active .ckm-dot {{
    background: var(--rc-garnet);
    border-color: var(--rc-garnet);
}}
.ckm-stage {{
    color: var(--rc-black);
    font-size: 0.84rem;
    font-weight: 850;
    line-height: 1.18;
}}
.ckm-driver {{
    color: rgba(7, 26, 47, 0.64);
    font-size: 0.74rem;
    font-weight: 650;
    line-height: 1.2;
    margin-top: 2px;
}}
</style>
<div class="ckm-card rc-panel">
    <div class="ckm-title">CKM Rail</div>
    <div class="ckm-headline">{escape(headline)}</div>
    <div class="ckm-stack">{''.join(stage_rows)}</div>
</div>
"""


def _build_ckm_kdigo_summary_html(result, patient=None):
    ckm_stage = getattr(result, "ckm_stage", None) or {}
    stage = ckm_stage.get("stage")
    headline = ckm_stage.get("headline") or ""
    kdigo_raw = getattr(result, "kdigo_stage", None)
    kdigo = kdigo_raw or "-"

    ckm_value = f"CKM Stage {stage}" if stage is not None else "CKM stage not available"
    ckm_desc = headline or "CKM stage not available."
    if stage == 3:
        ckm_desc = "Subclinical cardiovascular disease or CKD is present."

    kidney_values = []
    egfr = getattr(patient, "egfr", None) if patient is not None else None
    uacr = getattr(patient, "uacr", None) if patient is not None else None
    if egfr is not None:
        kidney_values.append(f"eGFR {float(egfr):g}")
    if uacr is not None:
        kidney_values.append(f"UACR {float(uacr):g} mg/g")
    elif egfr is not None:
        kidney_values.append("UACR missing; albuminuria not measured")
        egfr_stage = getattr(result, "egfr_stage", None) or kdigo_raw or "eGFR"
        kdigo = f"KDIGO incomplete: {egfr_stage}; UACR missing"
    if not kidney_values:
        if getattr(result, "egfr_stage", None):
            kidney_values.append(str(result.egfr_stage))
        if getattr(result, "albuminuria_stage", None):
            kidney_values.append(str(result.albuminuria_stage))
        if getattr(result, "egfr_stage", None) and not getattr(result, "albuminuria_stage", None):
            kdigo = f"KDIGO incomplete: {result.egfr_stage}; UACR missing"
    kidney_desc = "; ".join(kidney_values) if kidney_values else "Kidney staging not available."

    plaque_context = ""
    for driver in ckm_stage.get("drivers") or []:
        driver_text = str(driver)
        if driver_text.upper().startswith("CAC "):
            plaque_context = f"{driver_text} indicates high plaque burden."
            break
    muted_html = (
        f'<div class="ckm-kdigo-muted">{escape(plaque_context)}</div>'
        if plaque_context
        else ""
    )

    return (
        "<style>"
        + component_theme_css()
        + """
.ckm-kdigo-strip {
    border: 1px solid var(--rc-line);
    border-radius: 12px;
    background: rgba(255,253,248,0.72);
    color: var(--rc-black);
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px 16px;
    padding: 10px 12px;
}
.ckm-kdigo-item {
    min-width: 0;
}
.ckm-kdigo-label {
    color: rgba(47,95,143,0.88);
    font-size: 0.68rem;
    font-weight: 900;
    letter-spacing: 0.08em;
    line-height: 1;
    text-transform: uppercase;
}
.ckm-kdigo-value {
    color: var(--rc-black);
    font-size: 0.95rem;
    font-weight: 900;
    line-height: 1.15;
    margin-top: 3px;
}
.ckm-kdigo-desc {
    color: rgba(7,26,47,0.62);
    font-size: 0.76rem;
    font-weight: 650;
    line-height: 1.22;
    margin-top: 3px;
}
.ckm-kdigo-muted {
    grid-column: 1 / -1;
    color: rgba(7,26,47,0.58);
    font-size: 0.76rem;
    font-weight: 680;
    line-height: 1.22;
    padding-top: 2px;
}
@media (max-width: 560px) {
    .ckm-kdigo-strip {
        grid-template-columns: 1fr;
    }
}
</style>
"""
        '<div class="ckm-kdigo-strip">'
        '<div class="ckm-kdigo-item">'
        '<div class="ckm-kdigo-label">CKM</div>'
        f'<div class="ckm-kdigo-value">{escape(ckm_value)}</div>'
        f'<div class="ckm-kdigo-desc">{escape(ckm_desc)}</div>'
        '</div>'
        '<div class="ckm-kdigo-item">'
        '<div class="ckm-kdigo-label">KDIGO</div>'
        f'<div class="ckm-kdigo-value">{escape(str(kdigo))}</div>'
        f'<div class="ckm-kdigo-desc">{escape(kidney_desc)}</div>'
        '</div>'
        f"{muted_html}"
        "</div>"
    )


def _safe_panel(st, title, render_fn, *, component=False, height=420, scrolling=False):
    try:
        html = render_fn()
        if isinstance(html, str):
            if component:
                render_component_html(st, html, height=height, scrolling=scrolling)
            else:
                render_html(st, html)
    except Exception as exc:
        st.markdown(f"### {title}")
        st.caption(f"{title} unavailable for this patient view.")
        st.caption(str(exc))


def _load_renderer_function(module_name, function_name):
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        raise RuntimeError(f"{module_name} could not be loaded: {exc}") from exc

    function = getattr(module, function_name, None)
    if not callable(function):
        raise RuntimeError(f"{module_name}.{function_name} is unavailable.")

    return function


def _build_clarifier_card_html(result, patient=None):
    renderer = _load_renderer_function(
        "renderers.clarifier_renderer", "build_clarifier_card_html"
    )
    try:
        return renderer(result, patient=patient)
    except TypeError:
        return renderer(result)


def _build_continuum_bar_html(patient, result):
    renderer = _load_renderer_function(
        "renderers.continuum_bar", "build_continuum_bar_html"
    )
    return renderer(patient, result)


def _render_emr_note_text(patient, result):
    renderer = _load_renderer_function("renderers.emr_renderer", "render_emr_note")
    return renderer(patient, result)


def _build_where_patient_falls_html(patient, result, *, show_not_active=False):
    renderer = _load_renderer_function(
        "renderers.where_patient_falls", "build_where_patient_falls_html"
    )
    return renderer(patient, result, show_not_active=show_not_active)


def _build_rss_html(rss_total, rss_contributions, result=None):
    renderer = _load_renderer_function("renderers.rss_renderer", "build_rss_panel_html")
    return renderer(rss_total, rss_contributions, result)


def _build_prevent_card_html(result):
    renderer = _load_renderer_function("renderers.prevent_card", "render_prevent_card")
    return renderer(result)


def _build_patient_roadmap_html(patient, result):
    renderer = _load_renderer_function(
        "renderers.patient_roadmap", "render_patient_roadmap"
    )
    return renderer(patient, result)


def _render_patient_roadmap_text(patient, result):
    renderer = _load_renderer_function(
        "renderers.patient_roadmap", "render_patient_roadmap_text"
    )
    return renderer(patient, result)


def render_report(st, patient):
    result, rss_total, rss_contributions = run_patient(patient)

    _safe_panel(
        st,
        "Risk Continuum",
        lambda: _build_continuum_bar_html(patient, result),
        component=True,
        height=350,
    )

    _safe_panel(
        st,
        "PREVENT",
        lambda: _build_prevent_card_html(result),
    )

    _safe_panel(
        st,
        "Where the Risk Is Coming From",
        lambda: _build_rss_html(rss_total, rss_contributions, result),
    )

    render_html(st, _detail_section_header_html("CKM / KDIGO"))
    _safe_panel(
        st,
        "CKM / KDIGO",
        lambda: _build_ckm_kdigo_summary_html(result, patient),
    )

    _wpf_spacer, wpf_control = st.columns([1, 0.34])
    with wpf_control:
        show_not_active_markers = st.checkbox(
            "Show not-active markers",
            value=False,
            key="where_patient_falls_show_not_active",
        )
    _safe_panel(
        st,
        "Where this patient falls",
        lambda: _build_where_patient_falls_html(
            patient,
            result,
            show_not_active=show_not_active_markers,
        ),
    )

    _safe_panel(
        st,
        "Risk clarifiers",
        lambda: _build_clarifier_card_html(result, patient),
    )

    target_col, action_col = st.columns([1, 1.15])
    with target_col:
        _safe_panel(st, "Targets", lambda: _build_targets_html(result, patient))
    with action_col:
        _safe_panel(st, "Action", lambda: _build_action_html(result, patient))

    render_diagnosis_confirm_panel(st, result, include_title=True)

    emr_note_text = _render_emr_note_text(patient, result)
    patient_roadmap_text = _render_patient_roadmap_text(patient, result)

    render_html(st, _detail_section_header_html("EMR note", "Copy-ready clinical text"))
    _safe_panel(
        st,
        "EMR note",
        lambda: render_emr_copy_box(st, emr_note_text),
    )

    render_html(st, _detail_section_header_html("Patient roadmap", "Patient-facing handout"))
    _safe_panel(
        st,
        "Patient Prevention Roadmap",
        lambda: _build_patient_roadmap_html(patient, result),
    )
    _safe_panel(
        st,
        "Copy patient roadmap",
        lambda: render_emr_copy_box(
            st,
            patient_roadmap_text,
            title="Patient roadmap text",
            height_px=420,
            button_label="Copy patient roadmap",
        ),
    )
    render_export_print_section(
        st,
        emr_text=emr_note_text,
        roadmap_text=patient_roadmap_text,
    )

    return result
