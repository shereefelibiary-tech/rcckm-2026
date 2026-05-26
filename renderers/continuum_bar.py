from html import escape

from modules.levels.definitions import (
    LEVEL_DEFS,
    classify_continuum_position,
)
from modules.levels.explanation import build_level_explanation
from ui.theme import component_theme_css


def _fmt_num(value):
    try:
        return f"{float(value):g}"
    except (TypeError, ValueError):
        return ""


def _selected_level_copy(patient, level):
    if patient is None:
        return "", ""

    if level == 5 and bool(getattr(patient, "clinical_ascvd", False)):
        return "Clinical ASCVD", "Secondary prevention"

    if bool(getattr(patient, "clinical_ascvd", False)):
        return "", "Clinical ASCVD"

    cac = getattr(patient, "cac", None)
    if cac is None:
        return "", "Plaque unmeasured"
    try:
        cac_value = float(cac)
    except (TypeError, ValueError):
        return "", ""

    if cac_value >= 300:
        context = "CAC >=1000" if cac_value >= 1000 else f"CAC {_fmt_num(cac)}"
        return ("Very high risk", context) if level == 5 else ("", context)
    if cac_value > 0:
        return "", f"Plaque present (CAC {_fmt_num(cac)})"
    return "", "CAC 0"


def build_continuum_bar_html(patient, result):
    position = classify_continuum_position(patient, result)
    active_level = position["level"]
    active_sublevel = position.get("sublevel")
    current_label = f"Level {active_level}"
    if active_sublevel:
        current_label = f"Level {active_sublevel}"
    selected_subtitle, selected_context = _selected_level_copy(patient, active_level)
    level_tooltip = build_level_explanation(patient, result)

    cards = []
    for level, payload in sorted(LEVEL_DEFS.items()):
        title = payload["title"]
        display_label = payload["label"]
        if level == active_level and active_sublevel:
            title = f"Level {active_sublevel}"
            display_label = payload.get("sublevels", {}).get(active_sublevel, display_label)
        if level == 5:
            display_label = "Very high risk"
        if level == active_level and selected_subtitle:
            display_label = selected_subtitle
        active_class = " rc-card-active" if level == active_level else ""
        context = (
            f'<div class="rc-context">{escape(selected_context)}</div>'
            if level == active_level and selected_context
            else ""
        )
        active_attrs = ""
        if level == active_level:
            tooltip_attr = escape(level_tooltip, quote=True)
            active_attrs = (
                ' role="button" tabindex="0"'
                f' aria-label="Current level explanation: {tooltip_attr}"'
                f' title="{tooltip_attr}"'
                f' data-tooltip="{tooltip_attr}"'
            )
        cards.append(
            f"""
            <div class="rc-card-wrap">
                <div class="rc-card rc-level-{level}{active_class}"{active_attrs}>
                    <div class="rc-level-title">{escape(title)}</div>
                    <div class="rc-level-subtitle">{escape(display_label)}</div>
                    {context}
                </div>
            </div>
            """
        )

    return f"""
<style>
{component_theme_css()}
.rc-shell,
.rc-shell * {{
    box-sizing: border-box;
}}
.rc-shell {{
    width: 100%;
    padding: 16px 14px 14px;
    margin: 18px 0 20px;
    overflow: visible !important;
    font-family: var(--rc-font-body);
    position: relative;
    z-index: 3;
}}
.rc-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 12px;
}}
.rc-title {{
    color: var(--rc-text);
    font-family: var(--rc-font-body);
    font-size: 1.04rem;
    font-weight: 750;
    letter-spacing: 0;
    line-height: 1.15;
    margin-bottom: 8px;
}}
.rc-current {{
    align-items: center;
    color: var(--rc-garnet);
    display: inline-flex;
    font-size: 1rem;
    font-weight: 850;
    gap: 6px;
    white-space: nowrap;
}}
.rc-level-help {{
    display: none;
}}
.rc-grid {{
    display: grid;
    grid-template-columns: repeat(5, minmax(118px, 1fr));
    gap: clamp(6px, 0.76vw, 12px);
    align-items: stretch;
    overflow: visible !important;
    position: relative;
}}
.rc-card-wrap {{
    position: relative;
    min-width: 0;
    overflow: visible !important;
    padding-top: 10px;
}}
.rc-card {{
    min-height: 126px;
    border-radius: 10px;
    border: 1px solid rgba(11, 31, 58, 0.18);
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
    padding: 13px 9px;
    color: var(--rc-text);
    height: 100%;
    min-width: 0;
    overflow: visible !important;
    overflow-wrap: anywhere;
    position: relative;
    transition: transform 120ms ease, box-shadow 120ms ease, border-color 120ms ease;
}}
.rc-card-active::before {{
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 8px solid rgba(7, 26, 47, 0.70);
    border-bottom: 0;
    content: "";
    height: 0;
    left: 50%;
    pointer-events: none;
    position: absolute;
    top: -16px;
    transform: translateX(-50%);
    width: 0;
}}
.rc-card-active {{
    border: 2px solid var(--rc-garnet);
    cursor: help;
    box-shadow: 0 9px 18px rgba(115, 0, 10, 0.14);
    transform: translateY(6px);
    z-index: 50;
}}
.rc-card-active:hover,
.rc-card-active:focus {{
    border-color: var(--rc-garnet-deep);
    box-shadow: 0 11px 22px rgba(115, 0, 10, 0.18);
    outline: none;
}}
.rc-card-active:focus-visible {{
    outline: 3px solid rgba(115, 0, 10, 0.22);
    outline-offset: 3px;
}}
.rc-card-active::after {{
    background: rgba(7, 26, 47, 0.96);
    border-radius: 9px;
    top: calc(100% + 12px);
    box-shadow: 0 12px 26px rgba(7, 26, 47, 0.20);
    color: #ffffff;
    content: attr(data-tooltip);
    font-size: 0.78rem;
    font-weight: 650;
    left: 50%;
    line-height: 1.32;
    max-width: min(320px, 72vw);
    min-width: min(260px, 72vw);
    opacity: 0;
    padding: 10px 11px;
    pointer-events: none;
    position: absolute;
    text-align: left;
    transform: translate(-50%, 4px);
    transition: opacity 120ms ease, transform 120ms ease;
    visibility: hidden;
    white-space: normal;
    z-index: 9999;
}}
.rc-card-active:hover::after,
.rc-card-active:focus::after {{
    opacity: 1;
    transform: translate(-50%, 0);
    visibility: visible;
}}
.rc-card-wrap:first-child .rc-card-active::after {{
    left: 0;
    transform: translate(0, 4px);
}}
.rc-card-wrap:first-child .rc-card-active:hover::after,
.rc-card-wrap:first-child .rc-card-active:focus::after {{
    transform: translate(0, 0);
}}
.rc-card-wrap:last-child .rc-card-active::after {{
    left: auto;
    right: 0;
    transform: translate(0, 4px);
}}
.rc-card-wrap:last-child .rc-card-active:hover::after,
.rc-card-wrap:last-child .rc-card-active:focus::after {{
    transform: translate(0, 0);
}}
.rc-level-1 {{ background: #edf3fb; }}
.rc-level-2 {{ background: #eef4ef; }}
.rc-level-3 {{ background: #fbf1df; }}
.rc-level-3.rc-card-active {{
    border-color: rgba(115,0,10,0.72);
    box-shadow: 0 10px 20px rgba(115, 0, 10, 0.13), inset 0 0 0 2px rgba(245, 158, 11, 0.20);
    background: linear-gradient(180deg, #fff6e7 0%, #f7dfb5 100%);
}}
.rc-level-3.rc-card-active .rc-level-title {{
    color: var(--rc-garnet-deep);
}}
.rc-level-4 {{ background: #f8e9df; }}
.rc-level-5 {{
    background: var(--rc-garnet);
    border-color: var(--rc-garnet);
    color: #ffffff;
}}
.rc-level-5.rc-card-active {{
    border-color: var(--rc-garnet-deep);
    box-shadow: 0 9px 18px rgba(75, 0, 7, 0.22);
}}
.rc-level-title {{
    font-size: clamp(0.94rem, 1.0vw, 1.02rem);
    font-weight: 800;
    line-height: 1.12;
    margin-bottom: 6px;
}}
.rc-level-subtitle {{
    font-size: clamp(0.76rem, 0.86vw, 0.84rem);
    font-weight: 650;
    line-height: 1.24;
    max-width: 100%;
}}
.rc-context {{
    border-top: 1px solid rgba(11, 31, 58, 0.13);
    color: rgba(7, 26, 47, 0.68);
    font-size: clamp(0.72rem, 0.78vw, 0.80rem);
    font-weight: 850;
    line-height: 1.18;
    margin-top: 8px;
    max-width: 100%;
    padding-top: 7px;
    white-space: normal;
}}
.rc-level-5 .rc-context {{
    border-top-color: rgba(255, 255, 255, 0.35);
    color: rgba(255, 255, 255, 0.90);
}}
.rc-footer {{
    display: flex;
    justify-content: space-between;
    gap: 14px;
    color: #5D6B7A;
    font-size: 0.82rem;
    font-weight: 700;
    margin-top: 16px;
}}
@media (max-width: 760px) {{
    .rc-shell {{
        padding-left: 10px;
        padding-right: 10px;
    }}
    .rc-grid {{
        grid-template-columns: repeat(5, minmax(96px, 1fr));
        gap: 4px;
        overflow-x: auto;
        overflow-y: visible;
        padding-bottom: 4px;
    }}
    .rc-card {{
        border-radius: 8px;
        min-height: 118px;
        padding: 11px 7px;
    }}
    .rc-card-active {{
        transform: translateY(4px);
    }}
    .rc-current {{
        font-size: 0.92rem;
    }}
    .rc-footer {{
        font-size: 0.76rem;
    }}
}}
</style>
<div class="rc-shell rc-panel">
    <div class="rc-header">
        <div class="rc-title rc-card-title">Risk Continuum</div>
        <div class="rc-current">
            Current: {escape(current_label)}
        </div>
    </div>
    <div class="rc-grid">
        {''.join(cards)}
    </div>
    <div class="rc-footer">
        <div>Lower signal / lower urgency</div>
        <div>Higher signal / higher urgency</div>
    </div>
</div>
"""


def render_continuum_bar(patient, result):
    import streamlit as st

    from ui.html import render_html

    render_html(st, build_continuum_bar_html(patient, result))


def render_continuum_bar_with_streamlit(st_module, patient, result):
    from ui.html import render_html

    render_html(st_module, build_continuum_bar_html(patient, result))
