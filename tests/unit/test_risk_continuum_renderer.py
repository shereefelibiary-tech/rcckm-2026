from core.enums import RiskLevel
from core.patient import Patient
from core.results import RCCKMResult
from renderers.continuum_bar import build_continuum_bar_html


def test_build_risk_continuum_html_highlights_plaque_phenotype_level():
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
    assert "transform: translateY(6px)" in html
    assert "rc-marker" not in html
    assert "Plaque present (CAC 50)" in html
    assert "box-sizing: border-box" in html
    assert "grid-template-columns: repeat(5, minmax(118px, 1fr))" in html
    assert "Subclinical atherosclerosis present" in html
    assert "Lower signal / lower urgency" in html
    assert "Higher signal / higher urgency" in html


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
    assert "ASCVD-intensity phenotype" not in html
    assert "High plaque burden (CAC 350)" not in html
    assert "CAC 350" in html
    assert "overflow: visible" in html
    assert "min-height: 126px" in html
    assert "font-size: clamp(0.94rem, 1.0vw, 1.02rem)" in html
    assert "font-size: clamp(0.76rem, 0.86vw, 0.84rem)" in html
    assert "font-size: clamp(0.72rem, 0.78vw, 0.80rem)" in html
    assert "white-space: normal" in html
    assert "clamp(6px, 0.76vw, 12px)" in html


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
    assert "min-height: 126px" in html
    assert "overflow: visible" in html
    assert "white-space: normal" in html
    assert "line-height: 1.24" in html
