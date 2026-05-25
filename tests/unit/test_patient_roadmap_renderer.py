from core.enums import PlaqueCategory, RiskLevel
from core.patient import Patient
from core.results import RCCKMResult, TargetResult
from renderers.patient_roadmap import (
    render_patient_roadmap,
    render_patient_roadmap_text,
)


def _patient():
    return Patient(
        age=60,
        sex="male",
        cac=350,
        apob=110,
        ldl_c=132,
        non_hdl_c=160,
        lp_a_value=180,
        lp_a_unit="nmol/L",
        a1c=7.1,
        diabetes=True,
        egfr=55,
        uacr=45,
        sbp=138,
        dbp=82,
        bp_treated=True,
        smoker=True,
        hscrp=3.2,
        psoriasis=True,
        osa=True,
        masld=True,
        bmi=31,
    )


def _result():
    result = RCCKMResult(
        prevent_10y_ascvd=8.2,
        prevent_risk_category=RiskLevel.INTERMEDIATE,
        plaque_category=PlaqueCategory.SEVERE,
        kdigo_stage="G3aA2",
        targets=[
            TargetResult(
                ldl_c_target=70,
                non_hdl_c_target=100,
                apob_target=80,
                rationale="High plaque burden.",
            )
        ],
        dominant_action="Lipid-lowering therapy is reasonable.",
        recommendations=[
            "Lipid-lowering therapy is reasonable.",
            "Optimize kidney-protective therapy.",
            "Check Lp(a) once.",
            "Obtain UACR to complete kidney-risk assessment.",
        ],
    )
    result.prevent_10y_total_cvd = 12.4
    result.prevent_30y_ascvd = 24.5
    result.prevent_30y_total_cvd = 31.2
    result.prevent_age = 62
    result.prevent_percentile = 74
    return result


def test_render_patient_roadmap_groups_full_clinical_story_without_raw_html():
    html = render_patient_roadmap(_patient(), _result())

    assert "roadmap-card" in html
    assert "Your Prevention Roadmap" in html
    assert "Your results show where you stand today and the most important steps to lower future heart, kidney, and metabolic risk." in html
    assert "roadmap-subtitle" in html
    assert "roadmap-risk-card" in html
    assert "roadmap-driver-row" in html
    assert html.count('<div class="roadmap-driver-row">') == 3
    assert "roadmap-context-chip" in html
    assert "roadmap-goal-item" in html
    assert "roadmap-step-list" in html
    assert "<li>" in html
    assert "<strong>" not in html
    assert "roadmap-goal-table" not in html
    assert "8.2%" in html
    assert "Total CVD" not in html
    assert "12.4%" not in html
    assert "Longer-term 30-year risk trajectory" in html
    assert "24.5%" in html
    assert "PREVENT Total CVD 30-year" not in html
    assert "roadmap-factor-grid" not in html
    assert "roadmap-goal-strip" in html
    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in html
    assert "ASCVD means artery/plaque-related events" not in html
    assert "PREVENT-age" not in html
    assert "PREVENT percentile" not in html
    assert "About 8 out of 100 similar patients may have a cardiovascular event" in html
    assert "About 25 out of 100 similar patients may have a cardiovascular event" in html
    assert "Level 5" in html
    assert "Coronary calcium score 350" in html
    assert "Coronary calcium score: 350, showing a high amount of plaque." in html
    assert "Level 5 - Very high risk" in html
    assert "Very high risk / high plaque burden" not in html
    assert "Coronary calcium score 350 - high plaque burden" in html
    assert "ApoB 110 - elevated particle burden" in html
    assert "Atherogenic burden" not in html
    assert "Atherogenic particle burden" not in html
    assert "ApoB 110" in html
    assert "LDL-C 132" in html
    assert "Blood sugar / diabetes" not in html
    assert "Kidney protection" not in html
    assert "Diabetes / kidney involvement" in html
    assert "Diabetes with kidney involvement" not in html
    assert "A1c 7.1%" in html
    assert "KDIGO G3aA2" in html
    assert "Lp(a)" in html
    assert "180 nmol/L" in html
    assert "Other context" in html
    assert "Blood pressure" not in html
    assert "BP 138/82; treated" in html
    assert "Sleep / hypoxia" not in html
    assert "Liver / MASLD" not in html
    assert "OSA" in html
    assert "MASLD" in html
    assert "LDL-C" in html
    assert "below 70 mg/dL" in html
    assert "Current 132 mg/dL" in html
    assert "Lower plaque-driving cholesterol" in html
    assert "Treat toward the cholesterol goals above." in html
    assert "No repeat calcium scan is needed for today&#x27;s decision." not in html
    assert "Aspirin safety" in html
    assert "Do not start aspirin unless your clinician recommends it." in html
    assert "Protect the kidneys" in html
    assert "Review kidney protection options with your clinician." in html
    assert "Lp(a) can be checked once to guide long-term prevention." in html
    assert "This roadmap is for discussion with your clinician." in html
    assert "Medication decisions should be individualized." in html
    assert "Dominant action" not in html
    assert 'roadmap-row-label">Next step' not in html
    next_section = html.split('<div class="roadmap-section-title">Next steps</div>', 1)[1]
    assert next_section.index("Lower plaque-driving cholesterol") < next_section.index("Protect the kidneys") < next_section.index("Aspirin safety")
    assert "Supporting actions:" not in html
    assert "Lipid therapy:" not in html
    assert "Aspirin: Aspirin" not in html
    assert "atherogenic" not in html.lower()
    assert "glycemia" not in html.lower()
    assert "clarification" not in html.lower()
    assert "genetic" not in html.lower()
    assert "inherited" not in html.lower()
    assert "phenotype" not in html.lower()
    assert "dominant_action" not in html
    assert "action_domains" not in html
    assert "risk_continuum_sublevel" not in html
    assert "treatment posture" not in html.lower()
    assert "risk enhancer" not in html.lower()
    assert "optimize" not in html.lower()
    assert "intensify" not in html.lower()
    assert "pharmacotherapy" not in html.lower()
    assert "&lt;div" not in html


def test_render_patient_roadmap_section_titles_use_dividers_not_underlines():
    html = render_patient_roadmap(_patient(), _result())

    assert "roadmap-section-title" in html
    assert "border-top: 1px solid rgba(7, 26, 47, 0.10)" in html
    assert "padding-top: 12px" in html
    assert "text-decoration" not in html
    assert "border-bottom" not in html.split(".roadmap-section-title", 1)[1].split(
        ".roadmap-risk-grid", 1
    )[0]


def test_render_patient_roadmap_text_is_copy_ready_plain_text():
    text = render_patient_roadmap_text(_patient(), _result())

    assert "Your Prevention Roadmap" in text
    assert "Your results show where you stand today" in text
    assert "Where you stand:" in text
    assert "- 10-year risk: 8.2%" in text
    assert "- 30-year risk: 24.5%" in text
    assert "About 25 out of 100 similar patients may have a cardiovascular event over the next 30 years." in text
    assert "PREVENT Total CVD" not in text
    assert "ASCVD means artery/plaque-related events" not in text
    assert "PREVENT-age" not in text
    assert "PREVENT percentile" not in text
    assert "- Coronary calcium score: 350, showing a high amount of plaque." in text
    assert "Artery plaque: CAC 350." in text
    assert "Cholesterol particles: ApoB 110; LDL-C 132; non-HDL-C 160." in text
    assert "Blood sugar / diabetes: A1c 7.1%." in text
    assert "phenotype" not in text.lower()
    assert "glycemia" not in text.lower()
    assert "clarification" not in text.lower()
    assert "- LDL-C: 132 mg/dL to <70 mg/dL" in text
    assert "Next steps:" in text
    assert "1. Lower plaque-driving cholesterol: Treat toward the cholesterol goals above." in text
    assert "2. Protect the kidneys: Review kidney protection options with your clinician." in text
    assert "3. Aspirin safety: Do not start aspirin unless your clinician recommends it." in text
    assert "4. Additional testing: Lp(a) can be checked once to guide long-term prevention." in text
    assert "Dominant action" not in text
    assert "dominant_action" not in text
    assert "action_domains" not in text
    assert "risk_continuum_sublevel" not in text
    assert "treatment posture" not in text.lower()
    assert "risk enhancer" not in text.lower()
    assert "optimize" not in text.lower()
    assert "intensify" not in text.lower()
    assert "pharmacotherapy" not in text.lower()
    assert "- Next step:" not in text
    assert "Supporting actions:" not in text
    assert "Lipid therapy:" not in text
    assert "Aspirin: Aspirin" not in text
    assert text.index("1. Lower plaque-driving cholesterol") < text.index(
        "2. Protect the kidneys"
    ) < text.index("3. Aspirin safety")
    assert "<div" not in text


def test_render_patient_roadmap_works_without_30_year_risk():
    result = _result()
    result.prevent_30y_ascvd = None
    result.prevent_30y_total_cvd = None
    result.prevent_unsupported_reason = (
        "30-year PREVENT estimate unavailable for the current data/age range."
    )

    html = render_patient_roadmap(_patient(), result)

    assert "Your Prevention Roadmap" in html
    assert "30-year risk" not in html
    assert "30-year PREVENT estimate unavailable for the current data/age range." in html


def test_render_patient_roadmap_explains_unavailable_prevent():
    result = RCCKMResult(
        prevent_available=False,
        prevent_missing_inputs=["systolic BP", "smoking status"],
    )

    html = render_patient_roadmap(_patient(), result)
    text = render_patient_roadmap_text(_patient(), result)

    assert "Near-term 10-year risk" in html
    assert "Unavailable" in html
    assert "Missing inputs: systolic BP, smoking status" in html
    assert "Missing inputs: systolic BP, smoking status" in text
