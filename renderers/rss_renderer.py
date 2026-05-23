import html

import streamlit as st
from ui.html import render_html
from ui.theme import component_theme_css


DOMAIN_COLORS = {
    "CAC": "var(--rc-garnet)",
    "ApoB": "#D97706",
    "Lp(a)": "#4F46E5",
    "Inflammatory Disease": "#EA580C",
    "hsCRP": "#B45309",
    "Sleep / Hypoxia": "#0891B2",
    "Liver / MASLD": "#65A30D",
    "Kidney": "#0F8B8D",
    "Lipids": "#2F5F8F",
    "Metabolic": "#7C3AED",
    "Behavioral": "#5D6B7A",
}


CONTRIBUTION_ORDER = {
    "CAC plaque burden": 10,
    "ApoB elevation": 20,
    "Reduced eGFR": 30,
    "Albuminuria": 40,
    "Diabetes": 50,
    "A1c elevation": 50,
    "Elevated Lp(a)": 60,
    "Hypertriglyceridemia": 70,
    "Inflammatory risk": 80,
    "Smoking": 90,
}

RSS_DISPLAY_ORDER_TOP_TO_BOTTOM = {
    "Diabetes": 10,
    "A1c elevation": 10,
    "Albuminuria": 20,
    "Reduced eGFR": 30,
    "ApoB elevation": 40,
    "CAC plaque burden": 50,
}


def ordered_contributions(rss_contributions):
    return sorted(
        [contribution for contribution in rss_contributions if contribution.points > 0],
        key=lambda contribution: (
            CONTRIBUTION_ORDER.get(contribution.label, 500),
            -contribution.points,
            contribution.label,
        ),
    )


def get_rss_display_contributions(rss_contributions):
    """Return tower/list contributions in the visual top-to-bottom display order."""
    return sorted(
        [
            contribution
            for contribution in rss_contributions
            if contribution.points > 0
            and contribution.label in RSS_DISPLAY_ORDER_TOP_TO_BOTTOM
        ],
        key=lambda contribution: (
            RSS_DISPLAY_ORDER_TOP_TO_BOTTOM.get(contribution.label, 500),
            contribution.label,
        ),
    )


def format_signal(contribution):
    value = contribution.actual_value
    if contribution.label == "Diabetes" and value is not None and not isinstance(value, bool):
        return f"{contribution.label} (A1c {value}%)"
    if value is None or isinstance(value, bool):
        return contribution.label

    value_labels = {
        "CAC plaque burden": f"CAC {value}",
        "ApoB elevation": f"ApoB {value} mg/dL",
        "Elevated Lp(a)": f"Lp(a) {value}",
        "Inflammatory risk": f"hsCRP {value} mg/L",
        "Reduced eGFR": f"eGFR {value}",
        "Albuminuria": f"UACR {value} mg/g",
        "Hypertriglyceridemia": f"Triglycerides {value} mg/dL",
    }
    value_label = value_labels.get(contribution.label, str(value))
    return f"{contribution.label} ({value_label})"


def format_tower_value(contribution):
    value = contribution.actual_value
    if contribution.label == "Diabetes" and value is not None and not isinstance(value, bool):
        return f"A1c {value}%"
    if contribution.label == "Diabetes":
        return "Diabetes"
    if value is None:
        return contribution.label
    if isinstance(value, bool):
        return contribution.label

    value_labels = {
        "CAC plaque burden": f"CAC {value}",
        "ApoB elevation": f"ApoB {value} mg/dL",
        "Elevated Lp(a)": f"Lp(a) {value}",
        "Inflammatory risk": f"hsCRP {value} mg/L",
        "Reduced eGFR": f"eGFR {value}",
        "Albuminuria": f"UACR {value} mg/g",
        "Hypertriglyceridemia": f"TG {value} mg/dL",
        "A1c elevation": f"A1c {value}%",
    }
    return value_labels.get(contribution.label, "")


def teaching_label(contribution):
    value = format_tower_value(contribution) or contribution.label
    label = contribution.label
    notes = {
        "CAC plaque burden": "high plaque burden" if numeric_value(contribution) and numeric_value(contribution) >= 300 else "plaque present",
        "ApoB elevation": "elevated particle burden",
        "Albuminuria": "albuminuria",
        "Reduced eGFR": "reduced kidney function",
        "Diabetes": "diabetes-range A1c",
        "A1c elevation": "diabetes-range A1c",
        "Elevated Lp(a)": "Lp(a)",
        "Inflammatory risk": "elevated inflammatory biomarker",
        "Hypertriglyceridemia": "elevated triglycerides",
        "Smoking": "modifiable risk driver",
    }
    return f"{value}: {notes.get(label, contribution.rationale)}"


def contributor_explanation(contribution):
    label = contribution.label
    primary = {
        "CAC plaque burden": "High plaque burden"
        if numeric_value(contribution) and numeric_value(contribution) >= 100
        else "Plaque present",
        "ApoB elevation": "Elevated particle burden",
        "Reduced eGFR": "Reduced kidney function",
        "Albuminuria": "Albuminuria",
        "Diabetes": "Diabetes-range A1c",
        "A1c elevation": "Diabetes-range A1c",
        "Elevated Lp(a)": "Lp(a)",
        "Hypertriglyceridemia": "Elevated triglycerides",
        "Inflammatory risk": "Elevated inflammatory biomarker",
        "Smoking": "Current smoking",
    }.get(label, contribution.rationale or label)
    detail = format_tower_value(contribution) or contribution.label
    return primary, detail


def numeric_value(contribution):
    value = contribution.actual_value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        try:
            return float(value.split()[0])
        except (ValueError, IndexError):
            return None
    return None


def evidence_note(contribution):
    value = numeric_value(contribution)
    label = contribution.label

    if label == "CAC plaque burden":
        if value is not None and value >= 1000:
            return (
                "CAC >=1000 band",
                "CAC at this level often indicates very high plaque burden and event risk.",
            )
        if value is not None and value >= 300:
            return (
                "CAC 300-999 band",
                "CAC >300 may approach secondary-prevention event-risk territory in cohort data.",
            )
        if value is not None and value >= 100:
            return (
                "CAC 100-299 band",
                "Moderate CAC indicates established coronary plaque and higher artery-event risk.",
            )
        return (
            "CAC 1-99 band",
            "Any CAC confirms coronary plaque and refines risk beyond traditional factors.",
        )

    if label == "ApoB elevation":
        if value is not None and value >= 130:
            return (
                "ApoB >=130 band",
                "High ApoB reflects increased atherogenic particle number.",
            )
        if value is not None and value >= 100:
            return (
                "ApoB 100-129 band",
                "ApoB reflects atherogenic particle number and can reveal residual risk when LDL-C is discordant.",
            )
        return (
            "ApoB 80-99 band",
            "Borderline ApoB can identify early atherogenic particle burden.",
        )

    if label == "Elevated Lp(a)":
        if value is not None and value >= 430:
            return (
                "Lp(a) >=430 nmol/L band",
                "Very high Lp(a) is a risk enhancer.",
            )
        if value is not None and value >= 250:
            return (
                "Lp(a) 250-429 nmol/L band",
                "Higher Lp(a) adds risk beyond standard lipid measures.",
            )
        return (
            "Lp(a) 125-249 nmol/L band",
            "Elevated Lp(a) is an independent risk enhancer.",
        )

    if label == "Inflammatory risk":
        if value is not None and value >= 5:
            return (
                "hsCRP >=5 mg/L band",
                "Marked inflammation can amplify cardiometabolic risk.",
            )
        return (
            "hsCRP 2-4.9 mg/L band",
            "hsCRP is an inflammatory biomarker interpreted in clinical context.",
        )

    if label == "Reduced eGFR":
        if value is not None and value < 15:
            return (
                "CKD G5 range",
                "Severely reduced kidney function is a major CKM and artery-event risk driver.",
            )
        if value is not None and value < 30:
            return (
                "CKD G4 range",
                "Advanced CKD substantially increases cardiovascular risk.",
            )
        if value is not None and value < 45:
            return (
                "CKD G3b range",
                "Reduced eGFR contributes to CKM and artery-event risk estimation.",
            )
        return (
            "CKD G3a range",
            "Reduced eGFR contributes to CKM and artery-event risk estimation.",
        )

    if label == "Albuminuria":
        if value is not None and value >= 300:
            return (
                "A3 albuminuria range",
                "Severe albuminuria strongly predicts cardiovascular and kidney risk.",
            )
        return (
            "A2 albuminuria range",
            "Albuminuria predicts cardiovascular and kidney risk even before major eGFR decline.",
        )

    if label == "Hypertriglyceridemia":
        if value is not None and value >= 500:
            return (
                "TG >=500 mg/dL band",
                "Severe hypertriglyceridemia can mark metabolic risk and pancreatitis concern.",
            )
        return (
            "TG 150-499 mg/dL band",
            "Elevated TG often tracks insulin resistance and atherogenic remnant burden.",
        )

    if label in {"Diabetes", "A1c elevation"}:
        return (
            "Diabetes-range A1c",
            "Dysglycemia adds cardiometabolic risk beyond lipid burden alone.",
        )

    return (
        contribution.domain,
        contribution.rationale,
    )


def format_tower_tooltip(contribution):
    value_label = format_tower_value(contribution)
    if not value_label:
        value_label = contribution.label
    band, pearl = evidence_note(contribution)

    return (
        f"{contribution.label}\n"
        f"{value_label} | {band} | {pearl}\n"
        f"{contribution.points:g} RSS points"
    )


def domain_color(domain):
    return DOMAIN_COLORS.get(domain, "#6b7280")


def rss_interpretation(rss_total):
    if rss_total >= 75:
        return "Severe"
    if rss_total >= 50:
        return "High"
    if rss_total >= 25:
        return "Moderate"
    return "Low"


def build_rss_tower_html(rss_contributions):
    segments = []
    filled_points = sum(contribution.points for contribution in rss_contributions)
    empty_capacity = max(0, 100 - filled_points)
    if empty_capacity:
        segments.append(
            f'<div class="rss-tower-empty" '
            f'title="Unused RSS capacity" '
            f'style="height: {empty_capacity:.2f}%;"></div>'
        )

    for contribution in rss_contributions:
        percentage = contribution.points
        tooltip = format_tower_tooltip(contribution)
        label = ""
        tower_value = format_tower_value(contribution)
        if tower_value:
            label = (
                f'<span class="rss-tower-label">'
                f'{html.escape(tower_value)}'
                f"</span>"
            )
        segments.append(
            f'<div class="rss-tower-segment" '
            f'title="{html.escape(tooltip, quote=True)}" '
            f'style="height: {percentage:.2f}%; '
            f'background: {domain_color(contribution.domain)};">'
            f"{label}</div>"
        )

    return f"""
<div class="rss-tower-wrap">
    <div class="rss-tower-axis">
        <span>100</span>
        <span>50</span>
        <span>0</span>
    </div>
    <div class="rss-tower">{''.join(segments)}</div>
</div>
"""


def render_rss_tower(rss_total, rss_contributions):
    if rss_total <= 0 or not rss_contributions:
        return

    interpretation = rss_interpretation(rss_total)
    tower_html = f"""
<style>
    .rss-score-header {{
        display: flex;
        align-items: flex-end;
        justify-content: space-between;
        gap: 1.5rem;
        margin: 0.75rem 0 1.25rem;
        padding-bottom: 0.85rem;
        border-bottom: 1px solid #e5e7eb;
    }}
    .rss-score-title {{
        color: #111827;
        font-size: 1.02rem;
        font-weight: 650;
        letter-spacing: 0;
        margin-bottom: 0.15rem;
    }}
    .rss-score-subtitle {{
        color: #6b7280;
        font-size: 0.84rem;
        line-height: 1.35;
    }}
    .rss-score-value-wrap {{
        display: flex;
        align-items: center;
        gap: 0.85rem;
        white-space: nowrap;
    }}
    .rss-score-value {{
        color: #0f172a;
        font-size: 2.4rem;
        font-weight: 700;
        line-height: 1;
    }}
    .rss-score-denominator {{
        color: #64748b;
        font-size: 1rem;
        font-weight: 500;
        margin-left: 0.1rem;
    }}
    .rss-score-chip {{
        border: 1px solid #cbd5e1;
        border-radius: 999px;
        color: #334155;
        background: #f8fafc;
        font-size: 0.78rem;
        font-weight: 650;
        padding: 0.28rem 0.65rem;
    }}
    .rss-tower-wrap {{
        display: flex;
        align-items: center;
        gap: 1.15rem;
        margin: 0.35rem 0 1.5rem;
        padding: 0.25rem 0 0.35rem;
    }}
    .rss-tower {{
        display: flex;
        flex-direction: column;
        width: 190px;
        height: 430px;
        overflow: hidden;
        border-radius: 18px;
        background: linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
        border: 1px solid #cbd5e1;
        box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.08);
    }}
    .rss-tower-segment {{
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        border-top: 1px solid rgba(255, 255, 255, 0.72);
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.24);
    }}
    .rss-tower-empty {{
        width: 100%;
        background: linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
        border-bottom: 1px solid rgba(15, 23, 42, 0.10);
    }}
    .rss-tower-label {{
        color: white;
        font-size: 0.72rem;
        font-weight: 700;
        line-height: 1;
        overflow: hidden;
        padding: 0 0.35rem;
        text-align: center;
        text-shadow: 0 1px 1px rgba(15, 23, 42, 0.24);
        text-overflow: ellipsis;
        white-space: nowrap;
    }}
    .rss-tower-axis {{
        align-self: stretch;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        color: #94a3b8;
        font-size: 0.78rem;
        font-weight: 600;
        height: 430px;
        padding: 0.15rem 0;
        text-align: right;
    }}
</style>
<div class="rss-score-header">
    <div>
        <div class="rss-score-title">Risk Score</div>
        <div class="rss-score-subtitle">Contribution-weighted clinical burden</div>
    </div>
    <div class="rss-score-value-wrap">
        <div class="rss-score-value">{rss_total:g}<span class="rss-score-denominator">/100</span></div>
        <div class="rss-score-chip">{interpretation}</div>
    </div>
</div>
{build_rss_tower_html(rss_contributions)}
"""
    render_html(st, tower_html)


def build_rss_panel_html(rss_total, rss_contributions):
    interpretation = rss_interpretation(rss_total)
    display_contributions = get_rss_display_contributions(rss_contributions)
    driver_row_parts = []
    for contribution in display_contributions:
        primary, detail = contributor_explanation(contribution)
        color = domain_color(contribution.domain)
        driver_row_parts.append(
            f'<div class="rss-driver-row">'
            f'<div class="rss-driver-color" style="background:{color};"></div>'
            f'<div class="rss-driver-copy">'
            f'<strong>{html.escape(primary)}</strong>'
            f'<span>{html.escape(detail)}</span></div>'
            f'<div class="rss-driver-points" style="color:{color};">+{contribution.points:g}</div>'
            f'</div>'
        )
    driver_rows = "".join(driver_row_parts)
    return f"""
<style>
{component_theme_css()}
.rss-module {{
    margin: 12px 0 16px;
    padding: 14px 16px 16px;
}}
.rss-module-head {{
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 16px;
    border-bottom: 1px solid rgba(11, 31, 58, 0.12);
    padding-bottom: 10px;
    margin-bottom: 12px;
}}
.rss-module-title {{
    color: var(--rc-text);
    font-family: var(--rc-font-body);
    font-size: 1.04rem;
    font-weight: 750;
    letter-spacing: 0;
    line-height: 1.15;
    margin-bottom: 8px;
}}
.rss-module-subtitle {{
    color: rgba(7, 26, 47, 0.60);
    font-size: 0.78rem;
    font-weight: 700;
    margin-top: 4px;
}}
.rss-score-compact {{
    display: flex;
    align-items: center;
    gap: 10px;
    white-space: nowrap;
}}
.rss-score-number {{
    color: var(--rc-text);
    font-size: 2.05rem;
    font-weight: 850;
    letter-spacing: -0.04em;
    line-height: 0.95;
}}
.rss-score-den {{
    color: #5D6B7A;
    font-size: 0.95rem;
    font-weight: 650;
    letter-spacing: 0;
    margin-left: 1px;
}}
.rss-score-band {{
    border: 1px solid rgba(115, 0, 10, 0.22);
    border-radius: 999px;
    background: var(--rc-garnet-tint);
    color: var(--rc-garnet);
    font-size: 0.74rem;
    font-weight: 850;
    padding: 0.22rem 0.58rem;
}}
.rss-module-body {{
    display: grid;
    grid-template-columns: 205px 1fr;
    gap: 18px;
    align-items: start;
}}
.rss-tower-wrap {{
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.62rem;
    margin: 0;
    padding: 0;
}}
.rss-tower {{
    display: flex;
    flex-direction: column;
    width: 112px;
    height: 330px;
    overflow: hidden;
    border-radius: 17px;
    background: linear-gradient(180deg, #fffdf8 0%, #eef2f7 100%);
    border: 1px solid rgba(11, 31, 58, 0.18);
    box-shadow: inset 0 1px 2px rgba(11, 31, 58, 0.08);
}}
.rss-tower-segment {{
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    border-top: 1px solid rgba(255, 255, 255, 0.72);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.24);
}}
.rss-tower-empty {{
    width: 100%;
    background: linear-gradient(180deg, rgba(255, 253, 248, 0.96), rgba(238, 242, 247, 0.92));
    border-bottom: 1px solid rgba(11, 31, 58, 0.10);
}}
.rss-tower-label {{
    color: white;
    font-size: 0.70rem;
    font-weight: 800;
    line-height: 1;
    overflow: hidden;
    padding: 0 0.32rem;
    text-align: center;
    text-shadow: 0 1px 1px rgba(7, 26, 47, 0.28);
    text-overflow: ellipsis;
    white-space: nowrap;
}}
.rss-tower-axis {{
    align-self: stretch;
    color: #5D6B7A;
    display: flex;
    flex-direction: column;
    font-size: 0.74rem;
    font-weight: 800;
    height: 330px;
    justify-content: space-between;
    padding: 0.12rem 0;
    text-align: right;
}}
.rss-drivers {{
    min-width: 0;
    align-self: start;
    border-left: 1px solid rgba(11, 31, 58, 0.10);
    padding-left: 16px;
}}
.rss-driver-heading {{
    color: var(--rc-black);
    font-family: var(--rc-font-title);
    font-size: 0.92rem;
    font-weight: 720;
    letter-spacing: -0.01em;
    margin: 1px 0 7px;
    text-transform: none;
}}
.rss-driver-list {{
    display: flex;
    flex-direction: column;
    gap: 2px;
}}
.rss-driver-row {{
    display: grid;
    grid-template-columns: 11px minmax(0, 1fr) auto;
    gap: 10px;
    align-items: center;
    border-bottom: 1px solid rgba(11, 31, 58, 0.10);
    padding: 5px 0 6px;
}}
.rss-driver-row:last-child {{
    border-bottom: 0;
}}
.rss-driver-color {{
    border-radius: 3px;
    height: 11px;
    width: 11px;
}}
.rss-driver-copy {{
    color: rgba(7, 26, 47, 0.74);
    font-size: 0.84rem;
    font-weight: 650;
    line-height: 1.18;
    min-width: 0;
    border-left: 0 solid transparent;
}}
.rss-driver-copy strong {{
    color: var(--rc-black);
    display: block;
    font-weight: 880;
}}
.rss-driver-copy span {{
    color: rgba(7, 26, 47, 0.56);
    display: block;
    font-size: 0.74rem;
    font-weight: 720;
    margin-top: 2px;
}}
.rss-driver-points {{
    font-size: 0.88rem;
    font-weight: 900;
    text-align: right;
}}
.rss-empty-drivers {{
    color: rgba(7, 26, 47, 0.62);
    font-size: 0.86rem;
    font-weight: 650;
}}
@media (max-width: 560px) {{
    .rss-module-body {{
        grid-template-columns: 1fr;
    }}
    .rss-drivers {{
        border-left: 0;
        border-top: 1px solid rgba(11, 31, 58, 0.10);
        padding-left: 0;
        padding-top: 11px;
    }}
    .rss-tower {{
        height: 350px;
    }}
    .rss-tower-axis {{
        height: 350px;
    }}
}}
</style>
<div class="rss-module rc-panel">
    <div class="rss-module-head">
        <div>
            <div class="rss-module-title rc-card-title">Why Risk Is Elevated</div>
        </div>
        <div class="rss-score-compact">
            <div class="rss-score-number">{rss_total:g}<span class="rss-score-den">/100</span></div>
            <div class="rss-score-band">{html.escape(interpretation)}</div>
        </div>
    </div>
    <div class="rss-module-body">
        {build_rss_tower_html(display_contributions) if rss_total > 0 and display_contributions else '<div class="rss-empty-drivers">No active RSS contributions.</div>'}
        <div class="rss-drivers">
            <div class="rss-driver-heading">Contributors</div>
            <div class="rss-driver-list">{driver_rows or '<div class="rss-empty-drivers">No active RSS contributors.</div>'}</div>
        </div>
    </div>
</div>
"""


def render_rss_panel(rss_total, rss_contributions):
    render_html(st, build_rss_panel_html(rss_total, rss_contributions))

    domain_points = {}
    for contribution in rss_contributions:
        domain_points[contribution.domain] = (
            domain_points.get(contribution.domain, 0) + contribution.points
        )
    domain_rows = sorted(
        [
            {"Domain": domain, "Points": points}
            for domain, points in domain_points.items()
        ],
        key=lambda row: row["Points"],
        reverse=True,
    )

    with st.expander("RSS contribution details", expanded=False):
        st.dataframe(domain_rows, hide_index=True, width="stretch")
        st.dataframe(
            [
                {
                    "Points": contribution.points,
                    "Domain": contribution.domain,
                    "Finding": format_signal(contribution),
                    "Severity": contribution.severity or "",
                    "Rationale": contribution.rationale,
                }
                for contribution in rss_contributions
            ],
            hide_index=True,
            width="stretch",
        )

