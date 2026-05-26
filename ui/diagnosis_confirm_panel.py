from html import escape

from core.diagnosis_workflow import (
    apply_diagnosis_review_overrides,
    diagnosis_entry_id,
    diagnosis_context_line,
    prepare_diagnosis_display_entries,
    prioritize_linked_diagnoses,
    split_diagnoses,
)
from ui.html import render_html
from ui.theme import component_theme_css


def _panel_css():
    return """
<style>
/*COMPONENT_THEME*/
.dx-title {
    color: var(--rc-text);
    font-family: var(--rc-font-body);
    font-size: 1.04rem;
    font-weight: 800;
    letter-spacing: 0;
    line-height: 1.15;
    margin: 0;
}
.dx-note {
    color: rgba(7, 26, 47, 0.52);
    font-size: 0.76rem;
    font-weight: 620;
    line-height: 1.28;
    margin: 4px 0 0;
}
.dx-panel {
    background: rgba(255, 253, 248, 0.84);
    border: 1px solid rgba(11, 31, 58, 0.10);
    border-radius: 14px;
    box-shadow: 0 10px 28px rgba(7, 26, 47, 0.045);
    padding: 14px 15px 15px;
    margin: 10px 0 14px;
}
.dx-panel-head {
    border-bottom: 1px solid rgba(7, 26, 47, 0.08);
    margin-bottom: 12px;
    padding-bottom: 10px;
}
.dx-col-title {
    color: rgba(7, 26, 47, 0.78);
    font-size: 0.76rem;
    font-weight: 820;
    letter-spacing: 0.01em;
    margin: 0 0 8px;
}
.dx-column-panel {
    background: rgba(255, 255, 255, 0.58);
    border: 1px solid rgba(7, 26, 47, 0.08);
    border-radius: 12px;
    padding: 10px;
    min-height: 100%;
}
.dx-row {
    background: rgba(255, 255, 255, 0.72);
    border: 1px solid rgba(11, 31, 58, 0.09);
    border-radius: 10px;
    color: #071A2F;
    font-family: var(--rc-font-body);
    margin: 0 0 8px;
    padding: 9px 10px 10px;
}
.dx-row-shell {
    margin: 0 0 8px;
}
.dx-action-row {
    display: flex;
    justify-content: flex-end;
    gap: 6px;
    padding-top: 2px;
}
.dx-row:last-child {
    margin-bottom: 0;
}
.dx-name {
    font-size: 0.86rem;
    font-weight: 820;
    line-height: 1.2;
    margin-bottom: 6px;
}
.dx-meta {
    align-items: center;
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    margin-top: 2px;
}
.dx-code-chip {
    background: rgba(47, 95, 143, 0.08);
    border: 1px solid rgba(47, 95, 143, 0.16);
    border-radius: 999px;
    color: rgba(7, 26, 47, 0.74);
    display: inline-flex;
    font-size: 0.72rem;
    font-weight: 760;
    line-height: 1;
    padding: 4px 7px;
}
.dx-context {
    color: rgba(7, 26, 47, 0.54);
    font-size: 0.72rem;
    font-weight: 610;
    line-height: 1.24;
    margin-top: 6px;
}
.dx-badge,
.dx-status {
    display: inline-flex;
    font-size: 0.64rem;
    font-weight: 800;
    line-height: 1;
}
.dx-badge {
    border-radius: 999px;
    border: 1px solid rgba(47, 95, 143, 0.24);
    background: rgba(47, 95, 143, 0.08);
    color: #132F55;
    font-weight: 900;
    padding: 1px 5px;
}
.dx-status {
    color: rgba(7, 26, 47, 0.48);
    margin-left: 5px;
    vertical-align: 1px;
}
.dx-empty {
    background: rgba(7, 26, 47, 0.035);
    border: 1px solid rgba(7, 26, 47, 0.07);
    border-radius: 999px;
    color: rgba(7, 26, 47, 0.54);
    display: inline-flex;
    font-size: 0.76rem;
    font-weight: 650;
    padding: 5px 9px;
}
.dx-suppressed-title {
    color: rgba(7, 26, 47, 0.58);
    font-size: 0.72rem;
    font-weight: 850;
    margin-top: 6px;
}
div[data-testid="stButton"] > button[kind="secondary"] {
    min-height: 1.55rem;
    padding: 0.08rem 0.42rem;
    white-space: nowrap;
    font-size: 0.72rem;
}
@media (max-width: 760px) {
    .dx-panel {
        padding: 12px;
    }
    .dx-column-panel {
        margin-bottom: 10px;
    }
}
</style>
""".replace("/*COMPONENT_THEME*/", component_theme_css())


def _codes_text(entry, *, confirmed):
    codes = entry.get("icd10_confirmed" if confirmed else "icd10_suggested") or []
    return f"ICD: {', '.join(codes)}" if codes else "ICD: -"


def _hcc_badge(entry, *, confirmed):
    codes = entry.get("hcc_confirmed" if confirmed else "hcc_suggested") or []
    if not codes:
        return ""
    text = " / ".join(codes)
    return f"<span class='dx-badge'>{escape(text)}</span>"


def _status_label(entry, *, confirmed):
    status = str(entry.get("status") or "").strip()
    if status == "clinician_confirmed":
        return "Clinician confirmed"
    if status in {"low_confidence", "low-confidence"}:
        return "Low confidence"
    if status in {"manually_suppressed", "manual_suppressed", "suppressed"}:
        return "Manually suppressed"
    if confirmed:
        return ""
    return "Needs review"


def _evidence_text(entry):
    context = diagnosis_context_line(entry)
    replacements = {
        "diabetes flag": "Diabetes documented",
        "Diabetes documented with eGFR <60": "Diabetes documented; eGFR <60",
        "diabetes with eGFR <60": "Diabetes documented; eGFR <60",
        "diabetes flag with eGFR <60": "Diabetes documented; eGFR <60",
        "uacr": "UACR",
        "egfr": "eGFR",
        "tg": "triglycerides",
        ">=": "≥",
        "<=": "≤",
    }
    cleaned = str(context or "").strip()
    for source, target in replacements.items():
        cleaned = cleaned.replace(source, target)
    label = str(entry.get("label_display") or entry.get("label") or "").lower()
    if "albuminuria" in label and "albuminuria" not in cleaned.lower():
        cleaned = f"{cleaned}; albuminuria present" if cleaned else "albuminuria present"
    return cleaned


def _candidate_html(entry, *, confirmed=False, include_row=True):
    label = entry.get("label_display") or entry.get("label") or "Diagnosis"
    code_text = _codes_text(entry, confirmed=confirmed)
    context = _evidence_text(entry)
    context_html = (
        f"<div class='dx-context'>Evidence: {escape(context)}</div>" if context else ""
    )
    status_label = _status_label(entry, confirmed=confirmed)
    status_html = (
        f"<span class='dx-status'>{escape(status_label)}</span>" if status_label else ""
    )
    body = (
        f"<div class='dx-name'>{escape(label)}"
        f"{status_html}</div>"
        f"<div class='dx-meta'><span class='dx-code-chip'>{escape(code_text)}</span>"
        f"{_hcc_badge(entry, confirmed=confirmed)}</div>"
        f"{context_html}"
    )
    if not include_row:
        return body
    return f"<div class='dx-row'>{body}</div>"


def _state_set(st, key):
    st.session_state.setdefault(key, [])
    return {str(x) for x in (st.session_state.get(key) or []) if str(x).strip()}


def _save_state_set(st, key, values):
    st.session_state[key] = sorted({str(x) for x in values if str(x).strip()})


def _diagnosis_review_state(st):
    return {
        "accepted": _state_set(st, "dx_review_accepted_ids"),
        "suppressed": set(),
        "review": set(),
    }


def _apply_action(st, entry, action):
    dx_id = diagnosis_entry_id(entry)
    if not dx_id:
        return

    accepted = _state_set(st, "dx_review_accepted_ids")

    if action == "accept":
        accepted.add(dx_id)

    _save_state_set(st, "dx_review_accepted_ids", accepted)
    if hasattr(st, "rerun"):
        st.rerun()


def _emit_result_review_state(st, result):
    state = _diagnosis_review_state(st)
    setattr(
        result,
        "diagnosis_review_state",
        {
            "accepted_ids": sorted(state["accepted"]),
            "suppressed_ids": sorted(state["suppressed"]),
            "review_ids": sorted(state["review"]),
        },
    )
    return state


def _render_action_buttons(st, entry, *, confirmed=False, suppressed=False):
    dx_id = diagnosis_entry_id(entry)
    if not dx_id or confirmed or suppressed:
        return
    if st.button("Confirm", key=f"dx_accept__{dx_id}", help="Move to confirmed / accepted"):
        _apply_action(st, entry, "accept")


def _render_candidate_list(st, rows, *, confirmed=False, suppressed=False):
    if not rows:
        empty_text = "None." if confirmed else "No review items."
        render_html(st, f"<div class='dx-empty'>{escape(empty_text)}</div>")
        return
    for row in rows:
        if confirmed:
            render_html(
                st,
                "<div class='dx-row dx-row-shell'>"
                + _candidate_html(row, confirmed=confirmed, include_row=False)
                + "</div>",
            )
        else:
            left, right = st.columns([5.2, 1.0])
            with left:
                render_html(
                    st,
                    "<div class='dx-row dx-row-shell'>"
                    + _candidate_html(row, confirmed=confirmed, include_row=False)
                    + "</div>",
                )
            with right:
                _render_action_buttons(st, row, confirmed=confirmed, suppressed=suppressed)


def render_diagnosis_confirm_panel(st, result, include_title=True):
    rows = prepare_diagnosis_display_entries(result)
    if not rows:
        return

    state = _emit_result_review_state(st, result)
    rows = apply_diagnosis_review_overrides(
        rows,
        accepted_ids=state["accepted"],
        suppressed_ids=state["suppressed"],
        review_ids=state["review"],
    )
    confirmed, review = split_diagnoses(rows)
    visible_review = review[:5]
    extra_review = review[5:]

    render_html(st, _panel_css())
    if include_title:
        render_html(
            st,
            "<div class='dx-panel'><div class='dx-panel-head'>"
            "<div class='dx-title rc-card-title'>Assessment candidates</div>"
            "<div class='dx-note'>Clinical diagnoses and coding support</div>"
            "</div></div>",
        )

    if any(state.values()):
        if st.button("Reset diagnosis review", key="dx_review_reset"):
            st.session_state["dx_review_accepted_ids"] = []
            _emit_result_review_state(st, result)
            if hasattr(st, "rerun"):
                st.rerun()

    col1, col2 = st.columns(2)
    with col1:
        render_html(st, "<div class='dx-column-panel'><div class='dx-col-title'>Accepted</div></div>")
        _render_candidate_list(st, confirmed, confirmed=True)

    with col2:
        render_html(st, "<div class='dx-column-panel'><div class='dx-col-title'>Needs review</div></div>")
        _render_candidate_list(st, visible_review, confirmed=False)
        if extra_review:
            with st.expander("More candidates", expanded=False):
                _render_candidate_list(st, extra_review, confirmed=False)
