from html import escape

from modules.levels.definitions import classify_continuum_position
from modules.plaque.engine import format_cac_percentile_context
from modules.risk_enhancers.reproductive import reproductive_marker_items
from ui.html import render_html
from ui.theme import component_theme_css


LPA_THRESHOLD_TEXT = (
    "nmol/L: <75 reference; 75-124 mild; >=125 elevated; >=250 high; >=430 very high. "
    "mg/dL: <30 reference; 30-49 mild; >=50 elevated; >=100 high; >=180 very high"
)


RISK_IMPACT_LABELS = {
    "major driver": "Major driver",
    "very high risk": "Major driver",
    "very high": "Major driver",
    "high": "Major driver",
    "severe particle burden": "Major driver",
    "major driver / risk-enhancing": "Major driver",
    "elevated": "Contributes",
    "mild signal": "Contributes",
    "moderate signal": "Contributes",
    "plaque present": "Contributes",
    "mild/context": "Context only",
    "enhancer context": "Context only",
    "missing": "Context only",
    "clarifier": "Context only",
    "needed": "Context only",
    "no major signal": "Not active",
    "no active signal": "Not active",
}

RISK_IMPACT_PRIORITY = {
    "Major driver": 0,
    "Contributes": 1,
    "Context only": 2,
    "Not active": 3,
}


def normalize_risk_impact_label(effect):
    """Collapse internal audit effects into clinician-facing display labels."""
    raw = str(effect or "").strip().lower()
    return RISK_IMPACT_LABELS.get(raw, str(effect or "").strip())


def _risk_impact_priority(effect):
    """Return display sort priority for a risk-impact label."""
    return RISK_IMPACT_PRIORITY.get(normalize_risk_impact_label(effect), 99)


def _is_not_active_effect(effect):
    """Return True when the display impact is the quiet audit-only state."""
    return normalize_risk_impact_label(effect) == "Not active"


def _fmt_num(value, decimals=0):
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if decimals == 0:
        return f"{number:g}"
    return f"{number:.{decimals}f}"


def _risk_value(value):
    return getattr(value, "value", value)


def _level_badge(patient, result):
    try:
        position = classify_continuum_position(patient, result)
        level = position.get("level")
        sublevel = position.get("sublevel")
    except Exception:
        level = _risk_value(getattr(result, "risk_level", None)) or "-"
        sublevel = None

    label = f"Level {level}" if isinstance(level, int) else str(level)
    if sublevel:
        label = f"{label} ({sublevel})"
    return label


def _is_clarifier(result, flag):
    clarification = getattr(result, "clarification", None) or {}
    return bool(clarification.get(flag))


def _supportive_hscrp_context(patient):
    kidney = (
        getattr(patient, "egfr", None) is not None
        and getattr(patient, "egfr") < 60
    ) or (
        getattr(patient, "uacr", None) is not None
        and getattr(patient, "uacr") >= 30
    )
    inflammatory = any(
        bool(getattr(patient, field, False))
        for field in (
            "inflammatory_disease",
            "rheumatoid_arthritis",
            "sle",
            "psoriasis",
            "ibd",
            "hiv",
        )
    )
    metabolic = bool(getattr(patient, "diabetes", False)) or bool(
        getattr(patient, "hypertension", False)
    )
    return kidney or inflammatory or metabolic


def _effect_for_lpa(value, unit):
    if value is None:
        return "clarifier"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "clarifier"
    unit = str(unit or "").strip()
    if unit == "nmol/L":
        if number >= 430:
            return "very high"
        if number >= 250:
            return "high"
        if number >= 125:
            return "elevated"
        if number >= 75:
            return "mild/context"
        return "no major signal"
    if unit == "mg/dL":
        if number >= 180:
            return "very high"
        if number >= 100:
            return "high"
        if number >= 50:
            return "elevated"
        if number >= 30:
            return "mild/context"
    return "no major signal"


def _effect_for_apob_ldl(apob, ldl):
    if apob is not None:
        if apob >= 140:
            return "severe particle burden"
        if apob >= 120:
            return "major driver / risk-enhancing"
        if apob >= 100:
            return "elevated"
        if apob >= 80:
            return "mild signal"
        return "no major signal"
    if ldl is not None:
        if ldl >= 190:
            return "major driver"
        if ldl >= 130:
            return "moderate signal"
        if ldl >= 100:
            return "mild signal"
        return "no major signal"
    return "missing"


def _effect_for_glycemia(a1c, diabetes):
    if diabetes or (a1c is not None and a1c >= 6.5):
        return "major driver"
    if a1c is not None and a1c >= 5.7:
        return "mild signal"
    if a1c is None:
        return "missing"
    return "no major signal"


def _effect_for_kidney(egfr, uacr):
    if (egfr is not None and egfr < 60) or (uacr is not None and uacr >= 30):
        return "major driver"
    if uacr is not None and 10 <= uacr < 30:
        return "mild signal"
    if egfr is None and uacr is None:
        return "missing"
    if uacr is None:
        return "needed"
    return "no major signal"


def _effect_for_hscrp(hscrp, patient):
    if hscrp is None:
        return "missing"
    if hscrp < 2:
        return "no major signal"
    if _supportive_hscrp_context(patient):
        return "major driver"
    return "mild signal"


def _is_active_effect(effect):
    return effect in {
        "mild signal",
        "moderate signal",
        "major driver",
        "very high risk",
        "mild/context",
        "elevated",
        "high",
        "very high",
        "major driver / risk-enhancing",
        "severe particle burden",
    }


def _signal_line(label, value, effect):
    if not _is_active_effect(effect):
        return ""
    label_text = str(label or "").strip()
    value_text = str(value or "").strip()
    if value_text.lower().startswith(label_text.lower()):
        return f"{value_text} ({effect})".strip()
    return f"{label_text} {value_text} ({effect})".strip()


def _enabled_labels(patient, fields):
    labels = []
    for field, label in fields:
        if bool(getattr(patient, field, False)):
            labels.append(label)
    return labels


def _chip(label):
    display_label = normalize_risk_impact_label(label)
    normalized = (
        display_label.lower()
        .replace(" ", "-")
        .replace("/", "-")
        .replace("(", "")
        .replace(")", "")
    )
    raw_normalized = (
        str(label or "")
        .lower()
        .replace(" ", "-")
        .replace("/", "-")
        .replace("(", "")
        .replace(")", "")
    )
    semantic_class = (
        f" wpf-chip-{escape(raw_normalized)}"
        if raw_normalized and raw_normalized != normalized
        else ""
    )
    return (
        f'<span class="wpf-chip wpf-chip-{escape(normalized)}{semantic_class}">'
        f"{escape(display_label)}</span>"
    )


def _risk_impact_class(effect):
    display_label = normalize_risk_impact_label(effect)
    normalized = (
        display_label.lower()
        .replace(" ", "-")
        .replace("/", "-")
        .replace("(", "")
        .replace(")", "")
    )
    return f"risk-impact-{normalized}"


def _patient_pill(value):
    return f'<span class="wpf-patient-pill">{escape(value)}</span>'


def _plain_value(value, class_name=""):
    cls = f' class="{class_name}"' if class_name else ""
    return f"<span{cls}>{escape(value)}</span>"


def _patient_value_html(value, class_name="", *, uacr_attention=False):
    if uacr_attention and value == "UACR missing":
        return _plain_value(value, "wpf-patient-uacr-missing")
    return _plain_value(value, class_name)


def _patient_values(values, *, active=False, missing=False, uacr_attention=False):
    clean = [str(value).strip() for value in values if str(value).strip()]
    if not clean:
        return _plain_value("Not available", "wpf-patient-muted")
    if missing:
        return "".join(
            _patient_value_html(
                value,
                "wpf-patient-missing",
                uacr_attention=uacr_attention,
            )
            for value in clean
        )
    if active:
        head, *tail = clean
        if uacr_attention and head == "UACR missing":
            html = _patient_value_html(head, uacr_attention=True)
        else:
            html = _patient_pill(head)
        html += "".join(
            _patient_value_html(
                value,
                "wpf-patient-secondary",
                uacr_attention=uacr_attention,
            )
            for value in tail
        )
        return html
    return "".join(
        _patient_value_html(
            value,
            "wpf-patient-line",
            uacr_attention=uacr_attention,
        )
        for value in clean
    )


def _marker(label, threshold=""):
    threshold_html = (
        f'<div class="wpf-threshold">{escape(threshold)}</div>' if threshold else ""
    )
    return f'<div class="wpf-marker-main">{escape(label)}</div>{threshold_html}'


def _row(marker, threshold, values, effect, active=False):
    active_class = " wpf-active" if active and effect != "none" else ""
    impact_class = _risk_impact_class(effect) if effect and effect != "none" else ""
    row_impact_class = f" marker-row-{impact_class.removeprefix('risk-impact-')}" if impact_class else ""
    effect_html = _chip(effect) if effect and effect != "none" else ""
    missing = effect in {"missing", "clarifier"}
    uacr_attention = "UACR missing" in {str(value).strip() for value in values} and effect in {
        "needed",
        "major driver",
    }
    return (
        f'<tr class="wpf-row{active_class}{row_impact_class}">'
        f'<td class="wpf-marker">{_marker(marker, threshold)}</td>'
        f'<td class="wpf-patient">{_patient_values(values, active=active and effect != "none", missing=missing, uacr_attention=uacr_attention)}</td>'
        f'<td class="wpf-effect">{effect_html}</td>'
        "</tr>"
    )


def _domain(label, rows):
    if not rows:
        return ""
    return (
        f'<tr class="wpf-domain-row"><td colspan="3">{escape(label)}</td></tr>'
        + "".join(rows)
    )


def _row_entry(marker, threshold, values, effect, active=False):
    return {
        "html": _row(marker, threshold, values, effect, active=active),
        "effect": effect,
        "priority": _risk_impact_priority(effect),
    }


def _build_grouped_rows(patient, result, *, show_not_active=False):
    groups = {
        "ATHEROGENIC BURDEN": [],
        "GLYCEMIA": [],
        "KIDNEY (EGFR/UACR)": [],
        "LP(A)": [],
        "FAMILY HISTORY": [],
        "SMOKING": [],
        "HSCRP": [],
        "INFLAMMATORY DISEASE": [],
        "HIV": [],
        "REPRODUCTIVE HISTORY": [],
        "SLEEP / HYPOXIA": [],
        "LIVER / MASLD": [],
        "PLAQUE / CAC": [],
    }

    active_signals = []

    def add_signal(label, value, effect):
        line = _signal_line(label, value, effect)
        if line:
            active_signals.append(line)

    def add_row(group_label, marker, threshold, values, effect, active=False):
        groups[group_label].append(
            _row_entry(marker, threshold, values, effect, active=active)
        )

    apob = getattr(patient, "apob", None)
    ldl = getattr(patient, "ldl_c", None)
    values = []
    if apob is not None:
        values.append(f"ApoB {_fmt_num(apob)} mg/dL")
    else:
        values.append("ApoB missing")
    if ldl is not None:
        values.append(f"LDL-C {_fmt_num(ldl)} mg/dL")
    else:
        values.append("LDL-C missing")
    effect = _effect_for_apob_ldl(apob, ldl)
    add_signal("ApoB" if apob is not None else "LDL-C", values[0] if apob is not None else values[1], effect)
    add_row(
        "ATHEROGENIC BURDEN",
        "ApoB / LDL-C",
        "<80 optimal/goal if treated; 80-99 mild; 100-119 elevated; >=120 risk-enhancing; >=140 severe. LDL-C fallback if ApoB unavailable.",
        values,
        effect,
        active=_is_active_effect(effect),
    )

    a1c = getattr(patient, "a1c", None)
    diabetes = bool(getattr(patient, "diabetes", False))
    value = f"A1c {_fmt_num(a1c, 1)}%" if a1c is not None else "A1c missing"
    if diabetes:
        value += "; diabetes reported"
    effect = _effect_for_glycemia(a1c, diabetes)
    add_signal("A1c", value, effect)
    add_row(
        "GLYCEMIA",
        "A1c / diabetes",
        "Prediabetes 5.7-6.4%; diabetes >=6.5%",
        [value],
        effect,
        active=_is_active_effect(effect),
    )

    egfr = getattr(patient, "egfr", None)
    uacr = getattr(patient, "uacr", None)
    values = [
        f"eGFR {_fmt_num(egfr)}" if egfr is not None else "eGFR missing",
        f"UACR {_fmt_num(uacr)} mg/g" if uacr is not None else "UACR missing",
    ]
    effect = _effect_for_kidney(egfr, uacr)
    kidney_signal_value = "; ".join(v for v in values if "missing" not in v) or "kidney data missing"
    add_signal("Kidney", kidney_signal_value, effect)
    add_row(
        "KIDNEY (EGFR/UACR)",
        "eGFR / UACR",
        "mild: UACR 10-29; major: eGFR <60 or UACR >=30",
        values,
        effect,
        active=_is_active_effect(effect),
    )

    lpa = getattr(patient, "lp_a_value", None)
    lpa_unit = getattr(patient, "lp_a_unit", None)
    value = (
        f"Lp(a) {_fmt_num(lpa)} {lpa_unit or ''}".strip()
        if lpa is not None
        else "Lp(a) missing"
    )
    effect = _effect_for_lpa(lpa, lpa_unit)
    add_signal("Lp(a)", value, effect)
    add_row(
        "LP(A)",
        "Lp(a)",
        LPA_THRESHOLD_TEXT,
        [value],
        effect,
        active=_is_active_effect(effect),
    )

    fhx = bool(getattr(patient, "premature_fhx_ascvd", False)) or bool(
        getattr(patient, "family_history_premature_ascvd", False)
    )
    family_summary = getattr(patient, "family_history_summary", None)
    effect = "mild signal" if fhx else "no major signal"
    value = family_summary or ("Yes" if fhx else "No")
    add_signal("Family history", value, effect)
    add_row(
        "FAMILY HISTORY",
        "Premature family history",
        "male first-degree <55; female first-degree <65",
        [value],
        effect,
        active=_is_active_effect(effect),
    )

    smoking = bool(getattr(patient, "smoker", False)) or bool(
        getattr(patient, "smoking", False)
    )
    effect = "major driver" if smoking else "no major signal"
    add_signal("Smoking", "current" if smoking else "No", effect)
    add_row(
        "SMOKING",
        "Current smoking",
        "current use",
        ["Yes" if smoking else "No"],
        effect,
        active=_is_active_effect(effect),
    )

    hscrp = getattr(patient, "hscrp", None)
    effect = _effect_for_hscrp(hscrp, patient)
    value = f"hsCRP {_fmt_num(hscrp, 1)} mg/L" if hscrp is not None else "hsCRP missing"
    add_signal("hsCRP", value, effect)
    add_row(
        "HSCRP",
        "hsCRP",
        ">=2 mg/L is interpreted in clinical context",
        [value],
        effect,
        active=_is_active_effect(effect),
    )

    inflammatory_labels = _enabled_labels(
        patient,
        [
            ("rheumatoid_arthritis", "RA"),
            ("sle", "SLE"),
            ("psoriasis", "psoriasis"),
            ("inflammatory_arthritis", "inflammatory arthritis"),
            ("ibd", "IBD"),
        ],
    )
    inflammatory = bool(getattr(patient, "inflammatory_disease", False))
    value = (
        ", ".join(inflammatory_labels)
        if inflammatory_labels
        else ("Inflammatory disease reported" if inflammatory else "None reported")
    )
    effect = "enhancer context" if inflammatory_labels or inflammatory else "no major signal"
    add_row(
        "INFLAMMATORY DISEASE",
        "Immune/inflammatory context",
        "RA, SLE, psoriasis, inflammatory arthritis, IBD",
        [value],
        effect,
        active=False,
    )

    if bool(getattr(patient, "hiv", False)):
        add_row(
            "HIV",
            "HIV",
            "guideline risk-enhancing pathway",
            ["HIV reported"],
            "enhancer context",
            active=False,
        )

    ancestry_values = _enabled_labels(
        patient,
        [
            ("south_asian_ancestry", "South Asian ancestry"),
            ("filipino_ancestry", "Filipino ancestry"),
        ],
    )
    if getattr(patient, "higher_risk_ancestry_context", None):
        ancestry_values.append(str(patient.higher_risk_ancestry_context))
    if ancestry_values:
        groups.setdefault("RISK ENHANCERS", [])
        add_row(
            "RISK ENHANCERS",
            "Higher-risk ancestry/context",
            "used for personalization, not diagnosis",
            ancestry_values,
            "enhancer context",
            active=True,
        )

    reproductive_items = reproductive_marker_items(patient)
    if reproductive_items:
        values = []
        for item in reproductive_items:
            detail = str(item.get("detail") or "").strip()
            label = str(item.get("label") or "").strip()
            values.append(f"{label} {detail}".strip())
        add_row(
            "REPRODUCTIVE HISTORY",
            "Reproductive history",
            "pregnancy and menopause risk markers",
            values,
            "mild signal",
            active=True,
        )

    if bool(getattr(patient, "osa", False)):
        add_row(
            "SLEEP / HYPOXIA",
            "OSA",
            "sleep/hypoxia context",
            ["OSA reported"],
            "enhancer context",
            active=True,
        )

    if bool(getattr(patient, "masld", False)):
        add_row(
            "LIVER / MASLD",
            "MASLD",
            "liver/metabolic context",
            ["MASLD reported"],
            "enhancer context",
            active=True,
        )

    cac = getattr(patient, "cac", None)
    clinical_ascvd = bool(getattr(patient, "clinical_ascvd", False))
    if clinical_ascvd:
        value = f"CAC {_fmt_num(cac)}; clinical ASCVD" if cac is not None else "Clinical ASCVD"
        effect = "very high risk"
    elif cac is None:
        value = "No CAC performed" if getattr(patient, "cac_not_done", False) else "Plaque unmeasured"
        effect = "missing"
    elif cac >= 300:
        value = f"CAC {_fmt_num(cac)}"
        effect = "very high risk"
    elif cac >= 100:
        value = f"CAC {_fmt_num(cac)}"
        percentile_context = format_cac_percentile_context(
            cac,
            getattr(patient, "cac_percentile", None),
            include_clinician_detail=True,
        )
        if percentile_context:
            value = f"{value}; {percentile_context}"
        effect = "moderate signal"
    elif cac > 0:
        value = f"CAC {_fmt_num(cac)}"
        percentile_context = format_cac_percentile_context(
            cac,
            getattr(patient, "cac_percentile", None),
            include_clinician_detail=True,
        )
        if percentile_context:
            value = f"{value}; {percentile_context}"
        effect = "plaque present"
    else:
        value = "CAC 0"
        effect = "no major signal"
    add_signal("CAC", value, effect)
    add_row(
        "PLAQUE / CAC",
        "CAC",
        "0 absent; 1-99 plaque; 100-299 high burden; >=300 very high burden",
        [value],
        effect,
        active=_is_active_effect(effect),
    )

    rendered_domains = []
    for domain_index, (label, entries) in enumerate(groups.items()):
        visible_entries = [
            entry
            for entry in entries
            if show_not_active or not _is_not_active_effect(entry["effect"])
        ]
        if not visible_entries:
            continue
        visible_entries.sort(key=lambda entry: entry["priority"])
        domain_priority = min(entry["priority"] for entry in visible_entries)
        rendered_domains.append(
            (
                domain_priority,
                domain_index,
                label,
                [entry["html"] for entry in visible_entries],
            )
        )

    rendered_domains.sort(key=lambda item: (item[0], item[1]))
    return "".join(_domain(label, rows) for _priority, _index, label, rows in rendered_domains), active_signals


def build_where_patient_falls_html(patient, result, *, show_not_active=False):
    """Build the clinician audit table showing values, thresholds, and effects."""
    rows_html, active_signal_items = _build_grouped_rows(
        patient,
        result,
        show_not_active=show_not_active,
    )
    if not rows_html:
        rows_html = _domain(
            "CLINICAL AUDIT",
            [_row("Structured signals", "", ["No measured audit signals available"], "none")],
        )

    active_signals = (
        " • ".join(active_signal_items)
        if active_signal_items
        else "No active mild or major signals identified."
    )
    badge = _level_badge(patient, result)

    return f"""\
<style>
{component_theme_css()}
.wpf-card {{
    border: 0;
    border-radius: 0;
    background: var(--rc-panel);
    box-shadow: none;
    margin: 0;
    padding: 2px 0 0;
    font-family: var(--rc-font-body);
}}
.wpf-head {{
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    margin: 0 0 10px;
}}
.wpf-title {{
    color: var(--rc-text);
    font-family: var(--rc-font-body);
    font-size: 1.0rem;
    font-weight: 750;
    letter-spacing: 0;
    line-height: 1.15;
    margin-bottom: 8px;
}}
.wpf-subtitle {{
    color: #526884;
    font-size: 0.72rem;
    font-weight: 600;
    margin-top: 10px;
}}
.wpf-legend {{
    color: rgba(7, 26, 47, 0.56);
    font-size: 0.75rem;
    font-weight: 620;
    line-height: 1.3;
    margin-top: 5px;
    max-width: 920px;
}}
.wpf-badge {{
    border: 2px solid var(--rc-garnet);
    border-radius: 999px;
    background: var(--rc-garnet-tint);
    color: var(--rc-garnet);
    font-size: 0.74rem;
    font-weight: 950;
    padding: 0.18rem 0.68rem;
    white-space: nowrap;
}}
.wpf-table {{
    border-collapse: collapse;
    border: 1px solid var(--rc-line);
    border-radius: 0;
    table-layout: fixed;
    width: 100%;
}}
.wpf-table th {{
    background: rgba(17,17,17,0.035);
    border-bottom: 1px solid var(--rc-line);
    border-right: 1px solid var(--rc-line);
    color: var(--rc-charcoal);
    font-size: 0.68rem;
    font-weight: 900;
    letter-spacing: 0;
    padding: 10px 12px;
    text-align: left;
    text-transform: none;
    width: 33.333%;
}}
.wpf-table th:last-child {{
    border-right: 0;
}}
.wpf-domain-row {{
    background: rgba(115,0,10,0.045);
}}
.wpf-domain-row td {{
    background: rgba(115,0,10,0.045);
    border-bottom: 1px solid var(--rc-line);
    border-left: 3px solid rgba(115,0,10,0.22);
    color: var(--rc-black);
    font-size: 0.66rem;
    font-weight: 760;
    letter-spacing: 0.055em;
    padding: 8px 12px;
}}
.wpf-row {{
    background: var(--rc-panel);
}}
.wpf-row.marker-row-context-only {{
    color: rgba(7, 26, 47, 0.72);
}}
.wpf-row.marker-row-context-only .wpf-marker-main,
.wpf-row.marker-row-context-only .wpf-patient {{
    color: rgba(7, 26, 47, 0.70);
    font-weight: 760;
}}
.wpf-row.marker-row-context-only .wpf-threshold,
.wpf-row.marker-row-context-only .wpf-patient-secondary,
.wpf-row.marker-row-context-only .wpf-patient-line {{
    color: rgba(7, 26, 47, 0.52);
}}
.wpf-row.marker-row-not-active {{
    color: rgba(7, 26, 47, 0.54);
}}
.wpf-row.marker-row-not-active .wpf-marker-main,
.wpf-row.marker-row-not-active .wpf-patient {{
    color: rgba(7, 26, 47, 0.50);
    font-weight: 650;
}}
.wpf-row.marker-row-not-active .wpf-threshold,
.wpf-row.marker-row-not-active .wpf-patient-line,
.wpf-row.marker-row-not-active .wpf-patient-secondary {{
    color: rgba(7, 26, 47, 0.42);
}}
.wpf-row td {{
    border-bottom: 1px solid rgba(17,17,17,0.08);
    border-right: 1px solid var(--rc-line);
    height: 42px;
    padding: 9px 12px;
    vertical-align: middle;
}}
.wpf-row td:last-child {{
    border-right: 0;
}}
.wpf-row.wpf-active {{
    box-shadow: none;
}}
.wpf-marker-main {{
    color: var(--rc-black);
    font-size: 0.73rem;
    font-weight: 950;
    line-height: 1.1;
}}
.wpf-threshold {{
    color: #536b86;
    font-size: 0.68rem;
    font-weight: 600;
    line-height: 1.16;
    margin-top: 4px;
}}
.wpf-patient {{
    color: var(--rc-black);
    font-size: 0.72rem;
    font-weight: 850;
}}
.wpf-patient-pill {{
    border: 2px solid rgba(115,0,10,0.72);
    border-radius: 999px;
    background: #ffffff;
    color: var(--rc-black);
    display: inline-flex;
    font-size: 0.72rem;
    font-weight: 950;
    line-height: 1;
    padding: 6px 10px;
}}
.wpf-patient-secondary,
.wpf-patient-line,
.wpf-patient-muted {{
    display: block;
    color: #536b86;
    font-size: 0.66rem;
    font-weight: 650;
    margin-top: 2px;
}}
.wpf-patient-line {{
    color: var(--rc-black);
    font-size: 0.72rem;
    font-weight: 850;
}}
.wpf-patient-missing {{
    border: 1px solid #cbd5e1;
    border-radius: 999px;
    background: #f1f5f9;
    color: #64748b;
    display: inline-flex;
    font-size: 0.70rem;
    font-weight: 850;
    line-height: 1;
    padding: 5px 9px;
}}
.wpf-patient-uacr-missing {{
    border: 2px solid rgba(115,0,10,0.78);
    border-radius: 999px;
    background: var(--rc-garnet-tint);
    color: var(--rc-garnet-deep);
    display: inline-flex;
    font-size: 0.70rem;
    font-weight: 950;
    line-height: 1;
    margin-top: 4px;
    padding: 3px 9px;
    white-space: nowrap;
}}
.wpf-effect {{
    text-align: left;
}}
.wpf-chip {{
    align-items: center;
    border: 1px solid transparent;
    border-radius: 999px;
    display: inline-flex;
    line-height: 1.1;
    white-space: nowrap;
}}
.wpf-chip-not-active,
.risk-impact-not-active {{
    background: transparent;
    border: 0;
    color: rgba(7, 26, 47, 0.46);
    font-size: 0.72rem;
    font-weight: 650;
    padding: 0;
}}
.wpf-chip-contributes,
.risk-impact-contributes {{
    background: rgba(47, 95, 143, 0.12);
    border-color: rgba(47, 95, 143, 0.14);
    color: #071a2f;
    font-size: 0.74rem;
    font-weight: 750;
    padding: 5px 10px;
}}
.wpf-chip-context-only,
.risk-impact-context-only {{
    background: transparent;
    border-color: rgba(7, 26, 47, 0.12);
    color: rgba(7, 26, 47, 0.58);
    font-size: 0.72rem;
    font-weight: 650;
    padding: 4px 8px;
}}
.wpf-chip-major-driver,
.risk-impact-major-driver {{
    background: var(--rc-garnet);
    border-color: var(--rc-garnet);
    color: #ffffff;
    font-size: 0.76rem;
    font-weight: 800;
    padding: 6px 11px;
}}
@media (max-width: 760px) {{
    .wpf-head {{
        flex-direction: column;
    }}
    .wpf-table th,
    .wpf-row td {{
        padding: 8px 7px;
    }}
}}
</style>
<div class="wpf-card rc-panel-compact">
<div class="wpf-head">
<div>
<div class="wpf-title rc-card-title" aria-label="WHERE THIS PATIENT FALLS">Where this patient falls</div>
<div class="wpf-subtitle">Inputs, missing data, and level-driving findings.</div>
<div class="wpf-legend">Risk impact: Major = changes level/action &middot; Contributes = supports risk &middot; Context = background &middot; Not active = audit only.</div>
</div>
<div class="wpf-badge">{escape(badge)}</div>
</div>
<table class="wpf-table">
<thead><tr><th>Marker</th><th>Patient</th><th>Risk impact</th></tr></thead>
<tbody>
{rows_html}
</tbody>
</table>
</div>
""".strip()


def render_where_patient_falls(patient, result, st_module=None):
    """Render the Where This Patient Falls audit table in Streamlit."""
    if st_module is None:
        import streamlit as st_module

    render_html(st_module, build_where_patient_falls_html(patient, result))
