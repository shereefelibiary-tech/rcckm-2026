from core.enums import RiskLevel
from core.patient import Patient
from core.results import RCCKMResult
from modules.levels.explanation import build_level_explanation
from renderers.continuum_bar import build_continuum_bar_html


def test_build_risk_continuum_html_highlights_plaque_pattern_level():
    patient = Patient(age=60, sex="male", cac=50)
    result = RCCKMResult(risk_level=RiskLevel.HIGH)

    html = build_continuum_bar_html(patient, result)

    assert "Risk Continuum" in html
    assert "Current: Level 4" in html
    assert "rc-level-4 rc-card-active" in html
    assert html.count(" rc-card-active") == 1
    assert "YOU ARE HERE" not in html
    assert "rc-card-active::before" in html
    assert "left: 50%" in html
    assert "transform: translateX(-50%)" in html
    assert "top: -16px" in html
    assert "border-top: 8px solid rgba(7, 26, 47, 0.70)" in html
    assert "border-bottom: 0" in html
    assert "rc-caret" not in html
    assert "transform: translateY(-4px)" in html
    assert "rc-marker" not in html
    assert "Plaque present (CAC 50)" in html
    assert "box-sizing: border-box" in html
    assert "grid-template-columns: repeat(5, minmax(128px, 1fr))" in html
    assert "gap: 0" in html
    assert "border-radius: 14px" in html
    assert ".rc-card-wrap + .rc-card-wrap .rc-card" in html
    assert "Subclinical atherosclerosis present" in html
    assert "Lower signal / lower urgency" in html
    assert "Higher signal / higher urgency" in html
    assert '<span class="rc-level-help"' not in html
    assert "role=\"button\"" in html
    assert "aria-label=" in html
    assert "data-tooltip=" in html
    active_tag = html.split('class="rc-card rc-level-4 rc-card-active"', 1)[1].split(">", 1)[0]
    assert " title=" not in active_tag
    assert "Current level explanation:" in html
    assert "rc-level-why" not in html
    assert "Why?" not in html
    assert "top: calc(100% + 12px)" in html
    assert "z-index: 9999" in html
    assert "white-space: pre-line" in html
    assert ".rc-card-wrap:last-child .rc-card-active::after" in html
    assert "overflow: visible !important" in html


def test_build_risk_continuum_html_defaults_to_level_1():
    html = build_continuum_bar_html(
        Patient(age=60, sex="male"),
        RCCKMResult(),
    )

    assert "Current: Level 1" in html
    assert "rc-level-1 rc-card-active" in html
    assert "YOU ARE HERE" not in html
    assert "rc-card-active::before" in html
    assert "Plaque unmeasured" in html


def test_active_caret_is_anchored_to_active_card_for_each_level():
    cases = [
        (Patient(age=60, sex="male"), RCCKMResult(), "rc-level-1 rc-card-active"),
        (
            Patient(age=60, sex="male", a1c=5.8),
            RCCKMResult(),
            "rc-level-2 rc-card-active",
        ),
        (
            Patient(age=42, sex="male"),
            RCCKMResult(prevent_30y_ascvd=12.0),
            "rc-level-3 rc-card-active",
        ),
        (
            Patient(age=60, sex="male", cac=38),
            RCCKMResult(),
            "rc-level-4 rc-card-active",
        ),
        (
            Patient(age=60, sex="male", cac=350),
            RCCKMResult(),
            "rc-level-5 rc-card-active",
        ),
    ]

    for patient, result, active_class in cases:
        html = build_continuum_bar_html(patient, result)
        assert active_class in html
        assert html.count(" rc-card-active") == 1
        assert "rc-card-active::before" in html
        assert "left: 50%" in html
        assert "transform: translateX(-50%)" in html
        assert "border-top: 8px solid rgba(7, 26, 47, 0.70)" in html
        assert "border-bottom: 0" in html
        assert "position: absolute" in html
        assert "rc-caret" not in html


def test_build_risk_continuum_html_keeps_level_5_inside_responsive_grid():
    html = build_continuum_bar_html(
        Patient(age=60, sex="male", cac=350),
        RCCKMResult(risk_level=RiskLevel.VERY_HIGH),
    )

    assert "rc-level-5 rc-card-active" in html
    assert "Very high risk / high plaque burden" not in html
    assert "Very high risk" in html
    assert "ASCVD-intensity pattern" not in html
    assert "High plaque burden (CAC 350)" not in html
    assert "CAC 350" in html
    assert "overflow: visible" in html
    assert "min-height: 94px" in html
    assert "font-size: clamp(1rem, 1.12vw, 1.12rem)" in html
    assert "font-size: clamp(0.82rem, 0.92vw, 0.90rem)" in html
    assert "font-size: clamp(0.76rem, 0.82vw, 0.84rem)" in html
    assert "white-space: normal" in html
    assert "gap: 0" in html


def test_build_risk_continuum_html_level_5_clinical_ascvd_copy_is_compact():
    html = build_continuum_bar_html(
        Patient(age=60, sex="male", clinical_ascvd=True),
        RCCKMResult(risk_level=RiskLevel.VERY_HIGH),
    )

    assert "rc-level-5 rc-card-active" in html
    assert "Clinical ASCVD" in html
    assert "Secondary prevention" in html
    assert "Very high risk / high plaque burden" not in html


def test_build_risk_continuum_html_level_3_is_attention_getting_not_red_alert():
    html = build_continuum_bar_html(
        Patient(age=42, sex="male"),
        RCCKMResult(
            prevent_risk_category=RiskLevel.LOW,
            prevent_30y_ascvd=12.0,
            level_classification={
                "level": "3A",
                "label": "Level 3A — elevated long-term risk trajectory",
                "plaque_status": "Plaque unmeasured",
            },
        ),
    )

    assert "rc-level-3 rc-card-active" in html
    assert ".rc-level-3.rc-card-active" in html
    assert "Level 3A" in html
    assert "Elevated long-term risk trajectory" in html
    assert "background: linear-gradient(180deg, #fff6e7 0%, #f7dfb5 100%)" in html


def test_build_risk_continuum_html_level_5_cac_1000_copy_is_compact():
    html = build_continuum_bar_html(
        Patient(age=60, sex="male", cac=1200),
        RCCKMResult(risk_level=RiskLevel.VERY_HIGH),
    )

    assert "rc-level-5 rc-card-active" in html
    assert "Very high risk" in html
    assert "CAC &gt;=1000" in html
    assert "High plaque burden (CAC 1200)" not in html


def test_build_risk_continuum_html_level_3b_has_room_for_context_line():
    html = build_continuum_bar_html(
        Patient(
            age=56,
            sex="male",
            cac=None,
            cac_not_done=True,
            bp_treated=True,
            a1c=5.9,
            triglycerides=185,
            apob=102,
            non_hdl_c=165,
            egfr=76,
            uacr=None,
        ),
        RCCKMResult(
            prevent_risk_category=RiskLevel.INTERMEDIATE,
            prevent_30y_ascvd=22.55,
        ),
    )

    assert "Current: Level 3B" in html
    assert "Level 3B" in html
    assert "Actionable early CKM / atherogenic risk" in html
    assert "Plaque unmeasured" in html
    assert "min-height: 94px" in html
    assert "overflow: visible" in html
    assert "white-space: normal" in html
    assert "line-height: 1.22" in html


def test_level_tooltip_explains_level_5_high_cac():
    patient = Patient(age=60, sex="male", cac=350, apob=110, diabetes=True, uacr=45)
    result = RCCKMResult(prevent_30y_ascvd=30.65)

    tooltip = build_level_explanation(patient, result)
    html = build_continuum_bar_html(patient, result)

    assert tooltip.splitlines() == ["CAC 350", "Very high plaque burden"]
    assert escape_for_test(tooltip) in html
    assert 'class="rc-card rc-level-5 rc-card-active" role="button" tabindex="0"' in html
    assert "Current level explanation:" in html
    active_tag = html.split('class="rc-card rc-level-5 rc-card-active"', 1)[1].split(">", 1)[0]
    assert " title=" not in active_tag
    assert '<span class="rc-level-help"' not in html
    assert "Why?" not in html


def test_level_tooltip_explains_cac_zero_without_plaque_positive_language():
    tooltip = build_level_explanation(
        Patient(age=55, sex="female", cac=0, prevent_10y_ascvd=2.0),
        RCCKMResult(prevent_10y_ascvd=2.0),
    )

    assert tooltip == "CAC 0"
    assert "not detected plaque" not in tooltip
    assert "plaque burden" not in tooltip.lower()


def test_level_tooltip_explains_low_10_year_high_30_year_young_patient():
    tooltip = build_level_explanation(
        Patient(
            age=38,
            sex="male",
            prevent_10y_ascvd=3.8,
            prevent_30y_ascvd=24.0,
            family_history_premature_ascvd=True,
            a1c=6.0,
            triglycerides=170,
        ),
        RCCKMResult(
            prevent_10y_ascvd=3.8,
            prevent_30y_ascvd=24.0,
            prevent_risk_category=RiskLevel.BORDERLINE,
        ),
    )

    assert "30y PREVENT 24%" in tooltip
    assert "Premature family history" in tooltip
    assert "Prediabetes (A1c 6%)" in tooltip
    assert "assigned because" not in tooltip


def test_level_tooltip_explains_ckd_albuminuria():
    tooltip = build_level_explanation(
        Patient(age=57, sex="male", uacr=48, egfr=64, a1c=6.0, triglycerides=150),
        RCCKMResult(prevent_10y_ascvd=6.65, prevent_30y_ascvd=26.07),
    )

    assert "UACR 48 mg/g" in tooltip
    assert "Prediabetes (A1c 6%)" in tooltip
    assert "kidney-mediated cardiometabolic risk" not in tooltip


def test_level_tooltip_explains_apob_driven_case():
    tooltip = build_level_explanation(
        Patient(age=52, sex="female", apob=124, ldl_c=132, prevent_10y_ascvd=4.0),
        RCCKMResult(prevent_10y_ascvd=4.0),
    )

    assert tooltip == "ApoB 124 mg/dL"


def test_level_tooltip_omits_missing_data_confidence_sentence():
    tooltip = build_level_explanation(
        Patient(age=56, sex="male", cac=None, cac_not_done=True, ldl_c=132),
        RCCKMResult(prevent_10y_ascvd=4.2),
    )

    assert tooltip == "LDL-C 132 mg/dL"
    assert "ApoB" not in tooltip
    assert "Lp(a)" not in tooltip
    assert "UACR" not in tooltip
    assert "could further clarify risk" not in tooltip


def escape_for_test(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
