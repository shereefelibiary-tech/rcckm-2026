from html import escape

from ui.theme import component_theme_css


CLARIFIER_DEFS = [
    {
        "key": "apob",
        "label": "ApoB",
        "domain": "apob_testing",
        "clarification_flag": "recommend_apob",
        "reason": "LDL present but particle burden unmeasured",
        "priority": "High",
    },
    {
        "key": "lpa",
        "label": "Lp(a)",
        "domain": "lpa_testing",
        "clarification_flag": "recommend_lpa",
        "reason": "once-in-lifetime Lp(a) measurement",
        "priority": "High",
    },
    {
        "key": "cac",
        "label": "CAC",
        "domain": "cac_testing",
        "clarification_flag": "recommend_cac",
        "reason": "plaque status unmeasured and risk decision may change",
        "priority": "High",
    },
    {
        "key": "uacr",
        "label": "UACR",
        "domain": "uacr_testing",
        "clarification_flag": "recommend_uacr",
        "reason": "complete kidney-risk assessment",
        "priority": "High",
    },
    {
        "key": "hscrp",
        "label": "hsCRP",
        "domain": "hscrp_testing",
        "clarification_flag": None,
        "reason": "inflammatory risk context",
        "priority": "Medium",
    },
    {
        "key": "fasting_lipids",
        "label": "Repeat fasting lipids",
        "domain": "fasting_lipids",
        "clarification_flag": None,
        "reason": "triglyceride uncertainty requires confirmation",
        "priority": "Medium",
    },
]


def _is_recommended(result, definition):
    action_domains = getattr(result, "action_domains", {}) or {}
    if definition["domain"] in action_domains:
        return True

    clarification = getattr(result, "clarification", None) or {}
    flag = definition.get("clarification_flag")
    return bool(flag and clarification.get(flag))


def _has_measured_cac(patient):
    if patient is None:
        return False
    cac = getattr(patient, "cac", None)
    if cac is None:
        return False
    try:
        return float(cac) >= 0
    except (TypeError, ValueError):
        return False


def build_clarifier_items(result, patient=None):
    patient = patient or getattr(result, "patient", None)
    items = []
    for definition in CLARIFIER_DEFS:
        recommended = _is_recommended(result, definition)
        if definition["key"] == "cac" and _has_measured_cac(patient):
            recommended = False
        items.append(
            {
                "label": definition["label"],
                "status": "recommended" if recommended else "complete",
                "reason": definition["reason"],
                "priority": definition["priority"] if recommended else "Low",
            }
        )
    return items


def build_clarifier_card_html(result, include_title=True, patient=None):
    items = build_clarifier_items(result, patient=patient)
    recommended_items = [item for item in items if item["status"] != "complete"]
    completed_items = [item for item in items if item["status"] == "complete"]

    def _short_reason(item):
        label = item["label"]
        reason_map = {
            "ApoB": "particle burden clarification",
            "Lp(a)": "Lp(a) measurement",
            "CAC": "plaque burden clarification",
            "UACR": "complete kidney-risk assessment",
            "hsCRP": "inflammatory risk context",
            "Repeat fasting lipids": "triglyceride confirmation",
        }
        return reason_map.get(label, item["reason"])

    def _bullet(item):
        return (
            f'<li title="{escape(item["reason"], quote=True)}">'
            f'<span class="clarifier-name">{escape(item["label"])}</span>'
            f'<span class="clarifier-dash">&mdash;</span>'
            f'<span class="clarifier-reason">{escape(_short_reason(item))}</span>'
            "</li>"
        )

    visible_rows = [_bullet(item) for item in recommended_items]
    if visible_rows:
        visible_html = f'<ul class="clarifier-list">{"".join(visible_rows)}</ul>'
    else:
        visible_html = (
            '<div class="clarifier-empty">Key clarifying data are available.</div>'
        )

    important_completed = [
        item
        for item in completed_items
        if item["label"] in {"ApoB", "Lp(a)", "CAC", "UACR", "hsCRP"}
    ]
    completed_html = ""
    if important_completed:
        available = " &bull; ".join(escape(item["label"]) for item in important_completed)
        completed_html = (
            '<div class="clarifier-available">'
            "<span>Already available:</span> "
            f"{available}"
            + "</div>"
        )

    title_html = (
        '<div class="clarifier-heading">'
        '<div class="clarifier-title rc-card-title">Data that could clarify risk</div>'
        '<div class="clarifier-subtitle">These items may improve confidence in the prevention plan.</div>'
        '</div>'
        if include_title
        else ""
    )

    return f"""\
<style>
{component_theme_css()}
.clarifier-card {{
    border: 0;
    border-left: 3px solid rgba(47, 95, 143, 0.36);
    border-radius: 0;
    background: rgba(255, 253, 248, 0.72);
    padding: 4px 0 4px 10px;
    margin: 2px 0 4px;
    box-shadow: none;
    font-family: var(--rc-font-body);
}}
.clarifier-title {{
    color: var(--rc-text);
    font-family: var(--rc-font-body);
    font-size: 1.0rem;
    font-weight: 750;
    letter-spacing: 0;
    line-height: 1.15;
    margin-bottom: 2px;
}}
.clarifier-heading {{
    margin-bottom: 7px;
}}
.clarifier-subtitle {{
    color: rgba(7, 26, 47, 0.54);
    font-family: var(--rc-font-body);
    font-size: 11px;
    font-weight: 600;
    line-height: 1.25;
}}
.clarifier-list {{
    list-style: none;
    margin: 0;
    padding: 0;
}}
.clarifier-list li {{
    color: rgba(7, 26, 47, 0.78);
    font-size: 12px;
    font-weight: 650;
    line-height: 1.32;
    margin: 1px 0;
}}
.clarifier-list li::before {{
    color: #2F5F8F;
    content: "\\2022";
    font-weight: 950;
    margin-right: 6px;
}}
.clarifier-name {{
    color: #071A2F;
    font-weight: 900;
}}
.clarifier-dash {{
    color: rgba(7, 26, 47, 0.46);
    padding: 0 4px;
}}
.clarifier-reason {{
    color: rgba(7, 26, 47, 0.72);
}}
.clarifier-empty {{
    color: rgba(7, 26, 47, 0.62);
    font-size: 12px;
    font-weight: 650;
    line-height: 1.32;
}}
.clarifier-available {{
    color: rgba(7, 26, 47, 0.52);
    font-size: 11px;
    font-weight: 650;
    line-height: 1.28;
    margin-top: 4px;
}}
.clarifier-available span {{
    color: rgba(7, 26, 47, 0.60);
    font-weight: 850;
}}
</style>
<div class="clarifier-card rc-panel-compact">
{title_html}
{visible_html}
{completed_html}
</div>
""".strip()


def render_clarifier_card(result, st_module=None, patient=None):
    if st_module is None:
        import streamlit as st_module

    from ui.html import render_html

    render_html(st_module, build_clarifier_card_html(result, patient=patient))

