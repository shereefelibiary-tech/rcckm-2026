from html import escape

from ui.theme import component_theme_css


CLARIFIER_DEFS = [
    {
        "key": "a1c",
        "label": "A1c",
        "domain": "a1c_testing",
        "clarification_flag": "recommend_a1c",
        "reason": "current glycemia assessment",
        "priority": "High",
    },
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


def get_missing_clarification_tests(patient, result):
    items = build_clarifier_items(result, patient=patient)
    priority = {"A1c": 1, "ApoB": 2, "Lp(a)": 3, "CAC": 4, "UACR": 5, "hsCRP": 6}
    return [
        item["label"]
        for item in sorted(
            (
                item
                for item in items
                if item["status"] != "complete" and item["label"] in priority
            ),
            key=lambda item: priority[item["label"]],
        )
    ]


def should_render_clarification_card(missing_tests):
    return len(list(missing_tests or [])) > 0


def build_clarifier_card_html(result, include_title=True, patient=None):
    missing_tests = get_missing_clarification_tests(patient, result)
    if not should_render_clarification_card(missing_tests):
        return ""

    tests_html = " &bull; ".join(escape(label) for label in missing_tests)

    title_html = (
        '<div class="clarifier-heading">'
        '<div class="clarifier-title rc-card-title">Additional information that may help clarify risk:</div>'
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
    padding: 5px 0 5px 10px;
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
    margin-bottom: 0;
}}
.clarifier-heading {{
    margin-bottom: 3px;
}}
.clarifier-tests {{
    color: rgba(7, 26, 47, 0.78);
    font-size: 12.5px;
    font-weight: 760;
    line-height: 1.25;
}}
</style>
<div class="clarifier-card rc-panel-compact">
{title_html}
<div class="clarifier-tests">{tests_html}</div>
</div>
""".strip()


def render_clarifier_card(result, st_module=None, patient=None):
    if st_module is None:
        import streamlit as st_module

    from ui.html import render_html

    html = build_clarifier_card_html(result, patient=patient)
    if html:
        render_html(st_module, html)

