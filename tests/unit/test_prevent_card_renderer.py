from core.enums import PlaqueCategory, RiskLevel
from core.results import RCCKMResult
from renderers.prevent_card import (
    PREVENT_CVD_SCOPE_EXPLAINER,
    build_prevent_missing_reason,
    render_prevent_card,
)


def test_render_prevent_card_shows_value_category_and_patient_language():
    result = RCCKMResult(
        prevent_10y_ascvd=8.2,
        prevent_risk_category=RiskLevel.INTERMEDIATE,
        plaque_category=PlaqueCategory.UNKNOWN,
    )
    result.prevent_10y_total_cvd = 12.4

    html = render_prevent_card(result)

    assert "prevent-card" in html
    assert "prevent-body" in html
    assert "height: auto" in html
    assert "overflow: visible" in html
    assert "padding: 16px 18px 18px" in html
    assert "10-Year Cardiovascular Risk" in html
    assert "8.2%" in html
    assert "intermediate" in html
    assert "prevent-matrix" in html
    assert "tbody tr:nth-child(odd)" in html
    assert "tbody tr:nth-child(even)" in html
    assert "--rc-garnet: #73000A" in html
    assert "background: rgba(17, 17, 17, 0.045)" in html
    assert "prevent-category-high" in html
    assert '<span class="value">8.2%</span>' in html
    assert "Atherosclerotic event risk" in html
    assert "Cardiovascular event risk" in html
    assert "10-year" in html
    assert "30-year" in html
    assert "12.4%" in html
    assert PREVENT_CVD_SCOPE_EXPLAINER in html
    assert "Atherosclerotic events include heart attack, stroke, or coronary heart disease death. Cardiovascular events include those plus heart failure." in html
    assert "About 8 out of 100 similar patients may experience an atherosclerotic event over 10 years." in html
    assert "near-term estimated risk" in html
    assert "Estimated population risk is elevated." in html
    assert "Plaque burden is unmeasured." in html
    assert "CAC can clarify structural plaque burden" in html
    assert "10-year PREVENT risk:" in html
    assert "Low &lt;3%" in html
    assert "Borderline 3&amp;ndash;" not in html
    assert "Borderline 3&ndash;&lt;5%" in html
    assert "Intermediate 5&ndash;&lt;10%" in html
    assert "High &ge;10%" in html
    assert '<span class="prevent-legend-active">Intermediate 5&ndash;&lt;10%</span>' in html
    assert "\n    <div class=\"prevent-body\"" not in html


def test_render_prevent_card_context_uses_discordance_when_plaque_exceeds_risk():
    result = RCCKMResult(
        prevent_10y_ascvd=4.0,
        prevent_risk_category=RiskLevel.BORDERLINE,
        plaque_category=PlaqueCategory.SEVERE,
        top_drivers=["CAC 350"],
        discordance_insight={
            "type": "plaque_exceeds_population_risk",
        },
    )

    html = render_prevent_card(result)

    assert "About 4 out of 100 similar patients may experience an atherosclerotic event over 10 years." in html
    assert "CAC 350 shows high plaque burden, so treatment intensity should not rely on PREVENT alone." in html


def test_render_prevent_card_handles_unavailable_prevent_risk():
    result = RCCKMResult(
        prevent_10y_ascvd=None,
        prevent_available=False,
        prevent_missing_inputs=["systolic BP", "smoking status"],
    )

    html = render_prevent_card(result)

    assert "--" in html
    assert "unavailable" in html
    assert "PREVENT estimate unavailable" in html
    assert "Missing inputs:" in html
    assert "systolic BP" in html
    assert "smoking status" in html


def test_render_prevent_card_missing_inputs_can_also_show_30_year_age_note():
    result = RCCKMResult(
        prevent_10y_ascvd=None,
        prevent_available=False,
        prevent_missing_inputs=["systolic BP"],
        prevent_warnings=["30-year PREVENT is only available for ages 30-59."],
    )

    html = render_prevent_card(result)

    assert "Missing inputs:" in html
    assert "systolic BP" in html
    assert "30-year PREVENT is only available for ages 30-59." in html


def test_render_prevent_card_shows_30_year_risk_when_available():
    result = RCCKMResult(
        prevent_10y_ascvd=8.2,
        prevent_30y_ascvd=24.5,
        prevent_10y_total_cvd=12.4,
        prevent_30y_total_cvd=31.2,
        prevent_risk_category=RiskLevel.INTERMEDIATE,
    )

    html = render_prevent_card(result)

    assert "8.2%" in html
    assert "Atherosclerotic event risk" in html
    assert "24.5%" in html
    assert "10-year" in html
    assert "12.4%" in html
    assert "Cardiovascular event risk" in html
    assert "31.2%" in html
    assert PREVENT_CVD_SCOPE_EXPLAINER in html
    assert "longer-term risk trajectory" in html
    assert PREVENT_CVD_SCOPE_EXPLAINER in html


def test_render_prevent_card_clinical_ascvd_suppresses_prevent_decision_values():
    result = RCCKMResult(
        clinical_ascvd=True,
        prevent_available=True,
        prevent_10y_ascvd=2.1,
        prevent_30y_ascvd=12.0,
        prevent_10y_total_cvd=3.2,
        prevent_30y_total_cvd=20.0,
        prevent_risk_category=RiskLevel.LOW,
    )

    html = render_prevent_card(result)

    assert "PREVENT is not used for treatment decisions in established ASCVD." in html
    assert "Established ASCVD drives secondary-prevention management" in html
    assert "2.1%" not in html
    assert "12%" not in html
    assert "<table class='prevent-matrix'>" not in html
    assert "10-year PREVENT risk:" not in html


def test_render_prevent_card_shows_prevent_age_and_percentile_when_supplied():
    result = RCCKMResult(
        prevent_10y_ascvd=8.2,
        prevent_age=62,
        prevent_percentile=74,
        prevent_risk_category=RiskLevel.INTERMEDIATE,
    )

    html = render_prevent_card(result)

    assert "PREVENT-age" in html
    assert "62 years" in html
    assert "PREVENT percentile" in html
    assert "74%" in html


def test_render_prevent_card_omits_30_year_when_missing_without_crashing():
    result = RCCKMResult(
        prevent_10y_ascvd=4.2,
        prevent_risk_category=RiskLevel.BORDERLINE,
        prevent_unsupported_reason="30-year PREVENT is only available for ages 30-59.",
    )

    html = render_prevent_card(result)

    assert "4.2%" in html
    assert "PREVENT ASCVD 30-year" not in html
    assert "30-year PREVENT is only available for ages 30-59." in html
    assert "longer-term risk trajectory" not in html
    assert PREVENT_CVD_SCOPE_EXPLAINER not in html


def test_render_prevent_card_uses_30_year_field_names():
    result = RCCKMResult(
        prevent_10y_ascvd=2.1,
        prevent_10y_total_cvd=3.38,
        prevent_30y_ascvd=12.0,
        prevent_30y_total_cvd=20.65,
        prevent_risk_category=RiskLevel.LOW,
    )

    html = render_prevent_card(result)

    assert "Atherosclerotic event risk" in html
    assert "12%" in html
    assert "Cardiovascular event risk" in html
    assert "20.65%" in html


def test_build_prevent_missing_reason_lists_missing_fields():
    result = RCCKMResult(
        prevent_available=False,
        prevent_missing_inputs=["systolic BP", "HDL-C"],
    )

    html = build_prevent_missing_reason(result)

    assert "Missing inputs:" in html
    assert "<li>systolic BP</li>" in html
    assert "<li>HDL-C</li>" in html


def test_build_prevent_missing_reason_shows_unsupported_age():
    result = RCCKMResult(
        prevent_available=False,
        prevent_unsupported_reason="PREVENT is validated for ages 30-79.",
    )

    html = build_prevent_missing_reason(result)

    assert "PREVENT is validated for ages 30-79." in html
