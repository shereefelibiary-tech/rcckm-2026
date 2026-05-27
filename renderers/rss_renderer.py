import html

import streamlit as st
from modules.risk_enhancers.masld import (
    MASLD_PATIENT_LABEL,
    MASLD_SHORT_LABEL,
    MASLD_TOOLTIP,
)
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
    "Family History": "#9333EA",
    "Reproductive History": "#C2410C",
    "HIV": "#7C2D12",
    "Ancestry / SDOH": "#64748B",
    "Kidney": "#0F8B8D",
    "Lipids": "#2F5F8F",
    "Metabolic": "#7C3AED",
    "Behavioral": "#5D6B7A",
}


CONTRIBUTION_ORDER = {
    "CAC plaque burden": 10,
    "ApoB elevation": 20,
    "LDL-C": 21,
    "Reduced eGFR": 30,
    "Albuminuria": 40,
    "Diabetes": 50,
    "A1c elevation": 50,
    "Elevated Lp(a)": 60,
    "Hypertriglyceridemia": 70,
    "Inflammatory risk": 80,
    "Premature family history": 82,
    "RA": 84,
    "SLE": 85,
    "Psoriasis": 86,
    "IBD": 87,
    "HIV": 88,
    "Inflammatory arthritis": 88.5,
    "South Asian ancestry": 90,
    "Filipino ancestry": 90.1,
    "Suspected FH / HeFH": 22,
    "Incidental CAC": 11,
    "Inflammatory disease": 89,
    "OSA": 92,
    "MASLD": 94,
    "Premature menopause": 95,
    "Early menopause": 95.1,
    "Preeclampsia": 95.2,
    "Gestational hypertension": 95.3,
    "Gestational diabetes": 95.4,
    "Preterm delivery": 95.5,
    "SGA infant": 95.6,
    "Recurrent pregnancy loss": 95.7,
    "PCOS / irregular menses": 95.8,
    "Early menarche": 95.9,
    "Smoking": 81,
}

RSS_DISPLAY_ORDER_TOP_TO_BOTTOM = {
    "Diabetes": 10,
    "A1c elevation": 10,
    "Inflammatory risk": 20,
    "OSA": 24,
    "MASLD": 25,
    "Inflammatory disease": 26,
    "RA": 26.1,
    "SLE": 26.2,
    "Psoriasis": 26.3,
    "IBD": 26.4,
    "HIV": 26.5,
    "Inflammatory arthritis": 26.6,
    "South Asian ancestry": 29.1,
    "Filipino ancestry": 29.2,
    "Suspected FH / HeFH": 69,
    "Incidental CAC": 81,
    "Premature menopause": 28.1,
    "Early menopause": 28.2,
    "Preeclampsia": 28.3,
    "Gestational hypertension": 28.4,
    "Gestational diabetes": 28.5,
    "Preterm delivery": 28.6,
    "SGA infant": 28.7,
    "Recurrent pregnancy loss": 28.8,
    "PCOS / irregular menses": 28.9,
    "Early menarche": 29.0,
    "Premature family history": 30,
    "Smoking": 35,
    "Hypertriglyceridemia": 40,
    "Albuminuria": 50,
    "Reduced eGFR": 51,
    "Elevated Lp(a)": 60,
    "ApoB elevation": 70,
    "LDL-C": 71,
    "CAC plaque burden": 80,
}


def ordered_contributions(rss_contributions):
    """Return RSS contributions in the canonical display order."""
    return sorted(
        [contribution for contribution in rss_contributions if contribution.points > 0],
        key=lambda contribution: (
            CONTRIBUTION_ORDER.get(contribution.label, 500),
            -contribution.points,
            contribution.label,
        ),
    )


def get_rss_display_contributions(result=None, rss_contributions=None):
    """Return the complete point-contributor list used by both RSS tower and rows."""
    """Return the canonical scored RSS display list used by both tower and rows."""
    if rss_contributions is None and isinstance(result, (list, tuple)):
        rss_contributions = result
        result = None
    if rss_contributions is None and result is not None:
        rss_contributions = getattr(result, "rss_contributors", None) or []
    return sorted(
        [
            contribution
            for contribution in rss_contributions
            if contribution.points > 0
        ],
        key=lambda contribution: (
            RSS_DISPLAY_ORDER_TOP_TO_BOTTOM.get(contribution.label, 500),
            -contribution.points,
            contribution.label,
        ),
    )


def _contribution_id(contribution):
    ids = {
        "CAC plaque burden": "cac",
        "ApoB elevation": "apob",
        "LDL-C": "ldl_c",
        "Elevated Lp(a)": "lpa",
        "Reduced eGFR": "egfr",
        "Albuminuria": "uacr",
        "Diabetes": "diabetes",
        "A1c elevation": "a1c",
        "Hypertriglyceridemia": "triglycerides",
        "Inflammatory risk": "hscrp",
        "Premature family history": "family_history",
        "Inflammatory disease": "inflammatory_disease",
        "RA": "ra",
        "SLE": "sle",
        "Psoriasis": "psoriasis",
        "IBD": "ibd",
        "HIV": "hiv",
        "OSA": "osa",
        "MASLD": "masld",
        "Premature menopause": "premature_menopause",
        "Early menopause": "early_menopause",
        "Preeclampsia": "preeclampsia",
        "Gestational hypertension": "gestational_hypertension",
        "Gestational diabetes": "gestational_diabetes",
        "Preterm delivery": "preterm_delivery",
        "SGA infant": "small_for_gestational_age",
        "Recurrent pregnancy loss": "recurrent_pregnancy_loss",
        "PCOS / irregular menses": "pcos_or_irregular_menses",
        "Early menarche": "early_menarche",
        "Smoking": "smoking",
    }
    return ids.get(contribution.label, contribution.label.lower().replace(" ", "_"))


def _domain_key(contribution):
    keys = {
        "CAC": "plaque",
        "ApoB": "atherogenic_burden",
        "Lp(a)": "lpa",
        "Kidney": "kidney",
        "Metabolic": "metabolic",
        "Lipids": "lipids",
        "hsCRP": "inflammation",
        "Family History": "family_history",
        "Inflammatory Disease": "inflammatory",
        "Sleep / Hypoxia": "sleep_hypoxia",
        "Liver / MASLD": "liver_metabolic",
        "Reproductive History": "reproductive_history",
        "Behavioral": "behavioral",
    }
    return keys.get(contribution.domain, str(contribution.domain or "").lower())


def _color_key(contribution):
    keys = {
        "CAC": "cac",
        "ApoB": "apob",
        "Lp(a)": "lpa",
        "Kidney": "kidney",
        "Metabolic": "metabolic",
        "Lipids": "lipids",
        "hsCRP": "hscrp",
        "Family History": "family_history",
        "Inflammatory Disease": "inflammatory",
        "Sleep / Hypoxia": "osa",
        "Liver / MASLD": "masld",
        "Reproductive History": "reproductive",
        "Behavioral": "behavioral",
    }
    return keys.get(contribution.domain, str(contribution.domain or "").lower())


def _contribution_to_display_item(contribution):
    row = format_rss_contributor_label(contribution)
    return {
        "id": _contribution_id(contribution),
        "domain": _domain_key(contribution),
        "label": row["title"],
        "subtitle": row["subtitle"],
        "value_label": row["tower_value"],
        "points": contribution.points,
        "severity": contribution.severity or _severity_for_points(contribution.points),
        "color_key": _color_key(contribution),
        "display": getattr(contribution, "display", True),
        "stack_in_tower": contribution.points > 0,
        "contribution": contribution,
    }


def _severity_for_points(points):
    if points >= 30:
        return "very_high"
    if points >= 8:
        return "major"
    if points >= 5:
        return "moderate"
    if points >= 3:
        return "mild"
    return "tiny"


def get_rss_display_items(result=None, rss_contributions=None, rss_total=None):
    """Build the canonical RSS display payload for score, contributors, and context."""
    contributors = [
        _contribution_to_display_item(contribution)
        for contribution in get_rss_display_contributions(result, rss_contributions)
    ]
    score = rss_total
    if score is None:
        score = sum(item["points"] for item in contributors if item["stack_in_tower"])
    interpretation = rss_interpretation(score)
    return {
        "score": score,
        "score_label": interpretation,
        "contributors": contributors,
        "context": [],
        "missing_clarifiers": [],
    }


def format_signal(contribution):
    """Format a contribution label for compact row display."""
    value = contribution.actual_value
    if contribution.label == "Diabetes" and value is not None and not isinstance(value, bool):
        return f"{contribution.label} (A1c {_format_number(value)}%)"
    if value is None or isinstance(value, bool):
        return contribution.label

    value_labels = {
        "CAC plaque burden": f"CAC {_format_number(value)}",
        "ApoB elevation": f"ApoB {_format_number(value)} mg/dL",
        "LDL-C": f"LDL-C {_format_number(value)} mg/dL",
        "Elevated Lp(a)": f"Lp(a) {value}",
        "Inflammatory risk": f"hsCRP {_format_number(value)} mg/L",
        "Reduced eGFR": f"eGFR {_format_number(value)}",
        "Albuminuria": f"UACR {_format_number(value)} mg/g",
        "Hypertriglyceridemia": f"Triglycerides {_format_number(value)} mg/dL",
        "Premature family history": str(value),
    }
    value_label = value_labels.get(contribution.label, str(value))
    return f"{contribution.label} ({value_label})"


def format_tower_value(contribution):
    """Format the shortest readable in-tower label for an RSS contribution."""
    value = contribution.actual_value
    if contribution.label == "MASLD":
        return MASLD_PATIENT_LABEL
    if contribution.label == "Diabetes" and value is not None and not isinstance(value, bool):
        return f"A1c {_format_number(value)}%"
    if contribution.label == "Diabetes":
        return "Diabetes"
    if value is None:
        return contribution.label
    if isinstance(value, bool):
        return contribution.label
    if contribution.domain == "Reproductive History":
        detail = str(value)
        if detail and detail.lower() not in contribution.label.lower():
            return f"{contribution.label} {detail}"
        return contribution.label

    value_labels = {
        "CAC plaque burden": f"CAC {_format_number(value)}",
        "ApoB elevation": f"ApoB {_format_number(value)} mg/dL",
        "LDL-C": f"LDL-C {_format_number(value)} mg/dL",
        "Elevated Lp(a)": f"Lp(a) {value}",
        "Inflammatory risk": f"hsCRP {_format_number(value)} mg/L",
        "Reduced eGFR": f"eGFR {_format_number(value)}",
        "Albuminuria": f"UACR {_format_number(value)} mg/g",
        "Hypertriglyceridemia": f"TG {_format_number(value)} mg/dL",
        "A1c elevation": f"A1c {_format_number(value)}%",
        "Premature family history": str(value),
    }
    return value_labels.get(contribution.label, "")


def _format_number(value):
    try:
        return f"{float(value):g}"
    except (TypeError, ValueError):
        return str(value)


def teaching_label(contribution):
    """Return patient/clinician-facing teaching copy for an RSS contribution."""
    value = format_tower_value(contribution) or contribution.label
    label = contribution.label
    notes = {
        "CAC plaque burden": "coronary calcium",
        "ApoB elevation": "ApoB / particle burden",
        "LDL-C": "LDL-C",
        "Albuminuria": "albuminuria",
        "Reduced eGFR": "eGFR",
        "Diabetes": "A1c",
        "A1c elevation": "A1c",
        "Elevated Lp(a)": "Lp(a)",
        "Inflammatory risk": "hsCRP",
        "Hypertriglyceridemia": "triglycerides",
        "Premature family history": "family history",
        "RA": "inflammatory risk enhancer",
        "SLE": "inflammatory risk enhancer",
        "Psoriasis": "inflammatory risk enhancer",
        "IBD": "inflammatory risk enhancer",
        "HIV": "HIV-related risk enhancer",
        "Inflammatory disease": "inflammatory risk enhancer",
        "OSA": "sleep-hypoxia risk enhancer",
        "MASLD": "liver-metabolic risk enhancer",
        "Premature menopause": "reproductive risk marker",
        "Early menopause": "reproductive risk marker",
        "Preeclampsia": "reproductive risk marker",
        "Gestational hypertension": "reproductive risk marker",
        "Gestational diabetes": "reproductive risk marker",
        "Preterm delivery": "reproductive risk marker",
        "SGA infant": "reproductive risk marker",
        "Recurrent pregnancy loss": "reproductive risk marker",
        "PCOS / irregular menses": "reproductive risk marker",
        "Early menarche": "reproductive risk marker",
        "Smoking": "modifiable risk driver",
    }
    return f"{value}: {notes.get(label, contribution.rationale)}"


def contributor_explanation(contribution):
    """Return the muted value/explanation line for an RSS contributor row."""
    row = format_rss_contributor_label(contribution)
    return row["title"], row["subtitle"]


def _clean_duplicate_text(value):
    return " ".join(
        str(value or "")
        .lower()
        .replace("-", " ")
        .replace("/", " ")
        .replace("(", " ")
        .replace(")", " ")
        .replace(",", " ")
        .split()
    )


def _meaningful_subtitle(title, subtitle):
    """Suppress RSS subtitles that only repeat the contributor title."""
    title = str(title or "").strip()
    subtitle = str(subtitle or "").strip()
    if not subtitle:
        return ""
    clean_title = _clean_duplicate_text(title)
    clean_subtitle = _clean_duplicate_text(subtitle)
    if clean_title == clean_subtitle:
        return ""
    if clean_subtitle and clean_subtitle in clean_title:
        return ""
    return subtitle


def format_rss_contributor_label(contribution):
    """Return scan-first display text for an RSS contributor row."""
    label = contribution.label
    tower_value = format_tower_value(contribution)
    title = {
        "CAC plaque burden": f"Coronary calcium {tower_value.replace('CAC ', '')}" if tower_value else "Coronary calcium",
        "ApoB elevation": tower_value or "ApoB",
        "LDL-C": tower_value or "LDL-C",
        "Reduced eGFR": f"Kidney filtration, {tower_value}" if tower_value else "Kidney filtration",
        "Albuminuria": f"Albuminuria, {tower_value}" if tower_value else "Albuminuria",
        "Diabetes": tower_value or "Diabetes",
        "A1c elevation": tower_value or "A1c",
        "Elevated Lp(a)": tower_value or "Lp(a)",
        "Hypertriglyceridemia": tower_value.replace("TG ", "Triglycerides ") if tower_value else "Triglycerides",
        "Inflammatory risk": tower_value or "hsCRP",
        "Premature family history": "Premature family history",
        "RA": "Rheumatoid arthritis",
        "SLE": "Systemic lupus erythematosus",
        "Psoriasis": "Psoriasis",
        "IBD": "Inflammatory bowel disease",
        "HIV": "HIV",
        "Inflammatory arthritis": "Inflammatory arthritis",
        "Inflammatory disease": "Chronic inflammatory disease",
        "OSA": "Obstructive sleep apnea",
        "MASLD": MASLD_PATIENT_LABEL,
        "Incidental CAC": "Incidental coronary calcium on CT",
        "Premature menopause": "Premature menopause",
        "Early menopause": "Early menopause",
        "Preeclampsia": "Preeclampsia",
        "Gestational hypertension": "Gestational hypertension",
        "Gestational diabetes": "Gestational diabetes",
        "Preterm delivery": "Preterm delivery",
        "SGA infant": "Small-for-gestational-age infant",
        "Recurrent pregnancy loss": "Recurrent pregnancy loss",
        "PCOS / irregular menses": "PCOS / irregular menses",
        "Early menarche": "Early menarche",
        "Smoking": "Current smoking",
    }.get(label, contribution.rationale or label)
    if contribution.domain == "Reproductive History" and tower_value:
        title = tower_value
    subtitle = {
        "ApoB elevation": "Particle burden",
        "Premature family history": "" if isinstance(contribution.actual_value, bool) else str(contribution.actual_value or ""),
        "RA": "Chronic inflammatory disease risk enhancer",
        "SLE": "Chronic inflammatory disease risk enhancer",
        "Psoriasis": "Chronic inflammatory disease risk enhancer",
        "IBD": "Chronic inflammatory disease risk enhancer",
        "Inflammatory arthritis": "Chronic inflammatory disease risk enhancer",
        "Inflammatory disease": "Chronic inflammatory disease risk enhancer",
        "HIV": "HIV-related risk enhancer",
        "MASLD": "",
        "Incidental CAC": "Qualitative plaque evidence",
    }.get(label, "")
    return {
        "title": title,
        "subtitle": _meaningful_subtitle(title, subtitle),
        "points": contribution.points,
        "severity": contribution.severity,
        "tower_value": tower_value or title,
        "color": domain_color(contribution.domain),
    }


def numeric_value(contribution):
    """Extract the numeric value carried by an RSS contribution when available."""
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
    """Return a compact evidence note for the contribution source value."""
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

    if label == "LDL-C":
        return (
            "LDL-C >=190 mg/dL band",
            "Severe LDL-C elevation is shown when ApoB is unavailable.",
        )

    if label == "Elevated Lp(a)":
        if value is not None and value < 125:
            return (
                "Borderline Lp(a) band",
                "Borderline Lp(a) is shown as a small RSS contributor.",
            )
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
        if label == "A1c elevation" and value is not None and value < 6.5:
            return (
                "A1c 5.7-6.4% band",
                "A1c is shown as a small metabolic contributor in this range.",
            )
        return (
            "A1c >=6.5% band",
            "Dysglycemia adds cardiometabolic risk beyond lipid burden alone.",
        )

    if label == "Premature family history":
        return (
            "Premature family history",
            "Premature first-degree family history is shown as a small risk-enhancing contributor.",
        )

    if label == "HIV":
        return (
            "HIV-related risk enhancer",
            "HIV is shown as its own guideline risk-enhancing pathway.",
        )

    if label in {"RA", "SLE", "Psoriasis", "IBD", "Inflammatory disease"}:
        return (
            "Inflammatory condition",
            f"{label} is shown as a small inflammatory risk-enhancing contributor.",
        )

    if label == "OSA":
        return (
            "Sleep-hypoxia context",
            "OSA is shown as a small sleep and cardiometabolic risk contributor.",
        )

    if label == "MASLD":
        return (
            "Liver-metabolic context",
            f"{MASLD_TOOLTIP} It is shown as a small liver-metabolic risk contributor.",
        )

    if contribution.domain == "Reproductive History":
        return (
            "Reproductive risk marker",
            f"{label} is shown as a small reproductive risk-enhancing contributor.",
        )

    return (
        contribution.domain,
        contribution.rationale,
    )


def format_tower_tooltip(contribution):
    """Build the hover/title text for an RSS tower segment."""
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
    """Resolve a contribution domain to its configured display color."""
    return DOMAIN_COLORS.get(domain, "#6b7280")


def rss_interpretation(rss_total):
    """Map an RSS numeric score to a compact interpretation label."""
    if rss_total >= 75:
        return "Severe"
    if rss_total >= 50:
        return "High"
    if rss_total >= 25:
        return "Moderate"
    return "Low"


def build_rss_tower_html(rss_contributions):
    """Render the vertical RSS tower from canonical point contributors."""
    segments = []
    tower_items = [item for item in (rss_contributions or []) if item["points"] > 0 and item["stack_in_tower"]]
    filled_points = sum(item["points"] for item in tower_items)
    empty_capacity = max(0, 100 - filled_points)
    tower_height_px = 440
    label_height_threshold_px = 24
    if empty_capacity:
        segments.append(
            f'<div class="rss-tower-empty" '
            f'title="Unused RSS capacity" '
            f'style="height: {empty_capacity:.2f}%;"></div>'
        )

    for item in tower_items:
        contribution = item["contribution"]
        percentage = item["points"]
        label = ""
        tower_value = item["value_label"]
        segment_height_px = (percentage / 100) * tower_height_px
        label_visible = bool(tower_value and segment_height_px >= label_height_threshold_px)
        if label_visible:
            label = (
                f'<span class="rss-tower-label">'
                f'{html.escape(tower_value)}'
                f"</span>"
            )
        compact_bits = [str(item["label"])]
        if tower_value and _clean_duplicate_text(tower_value) != _clean_duplicate_text(item["label"]):
            compact_bits.append(str(tower_value))
        compact_bits.append(f'+{item["points"]:g} RSS points')
        compact_title = " - ".join(compact_bits)
        segments.append(
            f'<div class="rss-tower-segment" '
            f'data-rss-id="{html.escape(str(item["id"]), quote=True)}" '
            f'data-rss-value="{html.escape(str(tower_value), quote=True)}" '
            f'data-rss-points="{item["points"]:g}" '
            f'data-rss-severity="{html.escape(str(item["severity"]), quote=True)}" '
            f'data-rss-label-visible="{str(bool(label_visible)).lower()}" '
            f'title="{html.escape(compact_title, quote=True)}" '
            f'style="height: max(4px, {percentage:.2f}%); '
            f'background: {domain_color(contribution.domain)};">'
            f"{label}</div>"
        )

    low_score_callout = ""
    if 0 < filled_points < 25 and tower_items:
        top_item = max(
            tower_items,
            key=lambda item: (
                item["points"],
                str(item["value_label"] or item["label"]),
            ),
        )
        top_label = top_item["value_label"] or top_item["label"]
        contributor_count = len(tower_items)
        contributor_word = "contributor" if contributor_count == 1 else "contributors"
        low_score_callout = (
            '<div class="rss-low-callout" data-rss-low-callout="true">'
            f'<span><strong>Top:</strong> {html.escape(str(top_label))} '
            f'<em>(+{top_item["points"]:g})</em></span>'
            f'<span>{contributor_count} {contributor_word} total</span>'
            "</div>"
        )

    return (
        '<div class="rss-tower-zone">'
        '<div class="rss-tower-wrap">'
        '<div class="rss-tower-stack">'
        '<div class="rss-tower-row">'
        '<div class="rss-tower-axis"><span>100</span><span>50</span><span>0</span></div>'
        f'<div class="rss-tower">{"".join(segments)}</div>'
        "</div>"
        f"{low_score_callout}"
        "</div>"
        "</div>"
        "</div>"
    )


def render_rss_tower(rss_total, rss_contributions):
    """Render RSS tower HTML for Streamlit display."""
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
{build_rss_tower_html(get_rss_display_items(None, rss_contributions, rss_total)["contributors"])}
"""
    render_html(st, tower_html)


def _context_row(item, class_name="rss-context-row"):
    label = html.escape(str(item.get("label", "") if isinstance(item, dict) else getattr(item, "label", "") or ""))
    detail_raw = item.get("value_label", "") if isinstance(item, dict) else getattr(item, "detail", "") or ""
    note_raw = item.get("note", "") if isinstance(item, dict) else getattr(item, "note", "") or ""
    detail = html.escape(str(detail_raw))
    note = html.escape(str(note_raw))
    return (
        f'<div class="{class_name}" title="{note}">'
        f'<strong>{label}</strong>'
        f'<span>{detail}</span>'
        f'</div>'
    )


def build_rss_panel_html(rss_total, rss_contributions, result=None):
    """Render the complete RSS panel with tower and contributor list."""
    display = get_rss_display_items(result, rss_contributions, rss_total)
    interpretation = display["score_label"]
    display_contributors = display["contributors"]
    stacked_points = sum(
        item["points"]
        for item in display_contributors
        if item["points"] > 0 and item["stack_in_tower"]
    )
    if round(stacked_points, 1) != round(float(display["score"] or 0), 1):
        raise ValueError("RSS display item points do not match visible RSS score.")
    driver_row_parts = []
    for item in display_contributors:
        contribution = item["contribution"]
        primary = item["label"]
        detail = item.get("subtitle", "")
        detail_html = (
            f'<span class="rss-row-value rss-muted">{html.escape(detail)}</span>'
            if detail
            else ""
        )
        evidence_heading, evidence_detail = evidence_note(contribution)
        row_title = f"{evidence_heading}. {evidence_detail}".strip()
        color = domain_color(contribution.domain)
        driver_row_parts.append(
            f'<div class="rss-row rss-driver-row rss-driver-row--{html.escape(str(item["severity"]))}" '
            f'data-rss-id="{html.escape(str(item["id"]), quote=True)}" '
            f'data-rss-points="{item["points"]:g}" '
            f'title="{html.escape(row_title, quote=True)}">'
            f'<div class="rss-marker rss-driver-color" style="background:{color};"></div>'
            f'<div class="rss-driver-copy">'
            f'<strong class="rss-row-label">{html.escape(primary)}</strong>'
            f'{detail_html}</div>'
            f'<div class="rss-row-points rss-driver-points">+{contribution.points:g}</div>'
            f'</div>'
        )
    driver_rows = "".join(driver_row_parts)
    driver_list_class = "rss-driver-list"
    if len(display_contributors) > 12:
        driver_list_class += " rss-driver-list--scroll"
    if rss_total > 0 and display_contributors:
        rss_body_content = f"""
{build_rss_tower_html(display_contributors)}
<div class="rss-list-zone rss-drivers">
<div class="rss-contributor-heading rss-driver-heading">RSS contributors</div>
<div class="{driver_list_class}">{driver_rows}</div>
</div>
"""
    else:
        rss_body_content = '<div class="rss-empty-drivers">No active RSS contributors.</div>'
    return f"""
<style>
{component_theme_css()}
.rss-card,
.rss-module {{
    font-family: var(--rc-font-body);
    margin: 12px 0 16px;
    padding: 14px 16px 16px;
}}
.rss-card,
.rss-card * {{
    font-family: var(--rc-font-body);
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
.rss-title,
.rss-module-title {{
    color: var(--rc-text);
    font-family: var(--rc-font-body);
    font-size: 1.04rem;
    font-weight: 800;
    letter-spacing: -0.01em;
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
.rss-score,
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
.rss-score-chip,
.rss-score-band {{
    border: 1px solid rgba(115, 0, 10, 0.22);
    border-radius: 999px;
    background: var(--rc-garnet-tint);
    color: var(--rc-garnet);
    font-size: 0.74rem;
    font-weight: 850;
    padding: 0.22rem 0.58rem;
}}
.rss-body,
.rss-module-body {{
    display: grid;
    grid-template-columns: 220px minmax(0, 1fr);
    gap: 28px;
    align-items: start;
}}
.rss-module-body--empty {{
    display: block;
}}
.rss-tower-zone {{
    min-width: 180px;
}}
.rss-tower-wrap {{
    display: grid;
    align-items: start;
    justify-content: center;
    margin: 0;
    padding: 0;
}}
.rss-tower-stack {{
    display: grid;
    gap: 8px;
    justify-items: center;
}}
.rss-tower-row {{
    display: flex;
    align-items: center;
    gap: 0.72rem;
}}
.rss-tower {{
    display: flex;
    flex-direction: column;
    width: 136px;
    height: 440px;
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
    box-sizing: border-box;
    min-height: 4px;
    overflow: hidden;
    position: relative;
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
    display: block;
    font-size: 0.72rem;
    font-weight: 800;
    line-height: 1;
    max-width: 100%;
    overflow: hidden;
    padding: 0 0.32rem;
    pointer-events: none;
    position: relative;
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
    height: 440px;
    justify-content: space-between;
    padding: 0.12rem 0;
    text-align: right;
}}
.rss-low-callout {{
    border-top: 1px solid rgba(11, 31, 58, 0.12);
    color: rgba(7, 26, 47, 0.64);
    display: grid;
    font-size: 0.76rem;
    font-weight: 640;
    gap: 2px;
    line-height: 1.18;
    max-width: 168px;
    padding-top: 7px;
    text-align: left;
}}
.rss-low-callout strong {{
    color: var(--rc-black);
    font-weight: 820;
}}
.rss-low-callout em {{
    color: var(--rc-garnet);
    font-style: normal;
    font-weight: 860;
}}
.rss-low-callout span:last-child {{
    color: rgba(7, 26, 47, 0.48);
    font-size: 0.72rem;
    font-weight: 620;
}}
.rss-drivers {{
    min-width: 0;
    align-self: start;
    border-left: 1px solid rgba(11, 31, 58, 0.10);
    padding-left: 16px;
}}
.rss-list-zone {{
    min-width: 0;
    overflow: visible;
}}
.rss-contributor-heading,
.rss-driver-heading {{
    color: var(--rc-black);
    font-family: var(--rc-font-body);
    font-size: 1.0rem;
    font-weight: 800;
    letter-spacing: -0.01em;
    margin: 1px 0 7px;
    text-transform: none;
}}
.rss-driver-list {{
    display: flex;
    flex-direction: column;
    gap: 2px;
    overflow: visible;
    padding-bottom: 3px;
}}
.rss-driver-list--scroll {{
    max-height: none;
    overflow: visible;
    padding-right: 7px;
}}
.rss-row,
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
.rss-driver-row--tiny,
.rss-driver-row--mild {{
    border-bottom-color: rgba(11, 31, 58, 0.07);
}}
.rss-driver-row--tiny {{
    grid-template-columns: 11px minmax(0, 1fr) auto;
    gap: 10px;
    padding: 3px 0 4px;
}}
.rss-driver-row--mild {{
    padding: 4px 0 5px;
}}
.rss-driver-row--tiny .rss-driver-copy strong {{
    color: var(--rc-black);
    font-size: 0.86rem;
    font-weight: 750;
}}
.rss-driver-row--tiny .rss-driver-copy span {{
    color: rgba(7, 26, 47, 0.52);
    font-size: 0.76rem;
    font-weight: 500;
    margin-top: 2px;
}}
.rss-driver-row--tiny .rss-driver-points {{
    font-size: 0.82rem;
    font-weight: 800;
}}
.rss-driver-row--mild .rss-driver-copy strong {{
    color: var(--rc-black);
    font-size: 0.86rem;
    font-weight: 750;
}}
.rss-driver-row--mild .rss-driver-points {{
    font-size: 0.82rem;
    font-weight: 800;
}}
.rss-driver-row--major .rss-driver-copy strong,
.rss-driver-row--very_high .rss-driver-copy strong {{
    font-weight: 750;
}}
.rss-driver-row--major .rss-driver-points,
.rss-driver-row--very_high .rss-driver-points {{
    font-weight: 800;
}}
.rss-marker,
.rss-driver-color {{
    border-radius: 3px;
    flex: 0 0 auto;
    height: 9px;
    width: 9px;
}}
.rss-driver-copy {{
    color: rgba(7, 26, 47, 0.74);
    font-family: var(--rc-font-body);
    font-size: 0.86rem;
    font-weight: 500;
    line-height: 1.18;
    min-width: 0;
    border-left: 0 solid transparent;
}}
.rss-row-label,
.rss-driver-copy strong {{
    color: var(--rc-black);
    display: block;
    font-family: var(--rc-font-body);
    font-size: 0.86rem;
    font-weight: 750;
    line-height: 1.12;
}}
.rss-muted,
.rss-row-value,
.rss-driver-copy span {{
    color: rgba(7, 26, 47, 0.56);
    display: block;
    font-family: var(--rc-font-body);
    font-size: 0.76rem;
    font-weight: 500;
    line-height: 1.15;
    margin-top: 2px;
}}
.rss-row-points,
.rss-driver-points {{
    color: var(--rc-black);
    font-family: var(--rc-font-body);
    font-size: 0.82rem;
    font-variant-numeric: tabular-nums;
    font-weight: 800;
    line-height: 1;
    text-align: right;
}}
.rss-empty-drivers {{
    color: rgba(7, 26, 47, 0.62);
    font-size: 0.86rem;
    font-weight: 650;
    padding: 4px 0 2px;
}}
.rss-context-block {{
    border-top: 1px solid rgba(11, 31, 58, 0.10);
    margin-top: 9px;
    padding-top: 8px;
}}
.rss-context-heading {{
    color: var(--rc-black);
    font-family: var(--rc-font-body);
    font-size: 0.86rem;
    font-weight: 720;
    margin-bottom: 4px;
}}
.rss-context-list {{
    display: grid;
    gap: 3px;
}}
.rss-context-row {{
    display: grid;
    grid-template-columns: minmax(120px, 0.72fr) minmax(0, 1fr);
    gap: 10px;
    align-items: baseline;
    color: rgba(7, 26, 47, 0.66);
    font-size: 0.78rem;
    line-height: 1.2;
    padding: 2px 0;
}}
.rss-context-row strong {{
    color: var(--rc-black);
    font-weight: 820;
}}
.rss-context-row span {{
    color: rgba(7, 26, 47, 0.55);
    font-weight: 650;
}}
.rss-missing-row strong {{
    color: #9A6700;
}}
@media (max-width: 760px) {{
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
        height: 260px;
        width: 118px;
    }}
    .rss-tower-axis {{
        height: 260px;
    }}
}}
@media (min-width: 761px) and (max-width: 900px) {{
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
        height: 330px;
        width: 122px;
    }}
    .rss-tower-axis {{
        height: 330px;
    }}
}}
</style>
<div class="rss-card rss-module rc-panel">
<div class="rss-module-head">
<div>
<div class="rss-title rss-module-title rc-card-title">Where the Risk Is Coming From</div>
</div>
<div class="rss-score-compact">
<div class="rss-score rss-score-number">{rss_total:g}<span class="rss-score-den">/100</span></div>
<div class="rss-score-chip rss-score-band">{html.escape(interpretation)}</div>
</div>
</div>
<div class="rss-body rss-module-body{' rss-module-body--empty' if not (rss_total > 0 and display_contributors) else ''}">
{rss_body_content}
</div>
</div>
"""


def render_rss_panel(rss_total, rss_contributions):
    """Emit the RSS panel into the active Streamlit page."""
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

