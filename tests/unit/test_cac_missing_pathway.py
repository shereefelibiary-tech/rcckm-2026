from core.enums import PlaqueCategory, RiskLevel
from core.patient import Patient
from modules.cac_recommendation.engine import build_cac_recommendation
from modules.levels.definitions import classify_continuum_position
from renderers.emr_renderer import render_emr_note
from renderers.patient_roadmap import render_patient_roadmap
from renderers.prevent_card import render_prevent_card
from renderers.where_patient_falls import build_where_patient_falls_html
from ui.report_layout import run_patient


def _diagnosis_names(result):
    return [candidate.name for candidate in result.diagnosis_candidates]


def test_cac_missing_high_prevent_shows_plaque_unmeasured_without_plaque_diagnosis():
    patient = Patient(
        age=60,
        sex="male",
        cac=None,
        prevent_10y_ascvd=12.0,
        prevent_10y_total_cvd=18.0,
    )

    result, rss_total, rss_contributions = run_patient(patient)
    position = classify_continuum_position(patient, result)
    prevent_html = render_prevent_card(result)
    roadmap_html = render_patient_roadmap(patient, result)
    wpf_html = build_where_patient_falls_html(patient, result)
    emr_note = render_emr_note(patient, result)

    assert result.plaque_category == PlaqueCategory.UNKNOWN
    assert result.prevent_risk_category == RiskLevel.HIGH
    assert position["level"] == 3
    assert position["level"] != 4
    assert "subclinical coronary atherosclerosis" not in " ".join(_diagnosis_names(result)).lower()
    assert "Plaque burden is unmeasured" in prevent_html
    assert "Plaque status has not been measured." in roadmap_html
    assert "Plaque: unmeasured" in emr_note
    assert "Plaque unmeasured" in wpf_html
    assert "wpf-chip-missing" in wpf_html
    assert all(contribution.label != "CAC plaque burden" for contribution in rss_contributions)
    assert rss_total == 0
    assert result.dominant_action == "Lipid-lowering therapy is indicated; treat toward high-risk targets."
    assert "Coronary calcium reasonable for plaque clarification." in result.recommendations


def test_cac_missing_borderline_prevent_family_history_recommends_cac_without_plaque_diagnosis():
    patient = Patient(
        age=60,
        sex="male",
        cac=None,
        prevent_10y_ascvd=3.5,
        family_history_premature_ascvd=True,
        family_history_relationship="father",
        family_history_event_type="MI",
        family_history_age_at_event=49,
        lp_a_value=20,
        lp_a_unit="nmol/L",
    )

    result, _rss_total, _rss_contributions = run_patient(patient)

    assert result.prevent_risk_category == RiskLevel.BORDERLINE
    assert result.cac_recommendation == "CAC scoring may help refine preventive risk classification."
    assert result.clarification["recommend_cac"] is True
    assert "Coronary calcium reasonable for plaque clarification." in result.recommendations
    assert "subclinical coronary atherosclerosis" not in " ".join(_diagnosis_names(result)).lower()


def test_cac_zero_is_plaque_absent_not_missing_or_level_4():
    patient = Patient(age=60, sex="male", cac=0, prevent_10y_ascvd=12.0)

    result, _rss_total, rss_contributions = run_patient(patient)
    position = classify_continuum_position(patient, result)
    wpf_html = build_where_patient_falls_html(patient, result)

    assert result.plaque_category == PlaqueCategory.NONE
    assert position["level"] != 4
    assert "CAC 0" in wpf_html
    assert "Plaque unmeasured" not in wpf_html
    assert all(contribution.label != "CAC plaque burden" for contribution in rss_contributions)


def test_cac_25_is_measured_plaque_level_4_when_engine_supports():
    patient = Patient(age=60, sex="male", cac=25)

    result, _rss_total, rss_contributions = run_patient(patient)
    position = classify_continuum_position(patient, result)

    assert result.plaque_category == PlaqueCategory.MILD
    assert position["level"] == 4
    assert any(contribution.label == "CAC plaque burden" for contribution in rss_contributions)
    assert "Subclinical coronary atherosclerosis" in _diagnosis_names(result)


def test_cac_120_uses_cac_100_299_high_risk_targets():
    patient = Patient(age=60, sex="male", cac=120)

    result, _rss_total, _rss_contributions = run_patient(patient)
    target = result.targets[0]

    assert result.plaque_category == PlaqueCategory.MODERATE
    assert target.ldl_c_target == 70
    assert target.non_hdl_c_target == 100
    assert "CAC 100-299" in target.rationale


def test_cac_350_uses_high_plaque_burden_pathway():
    patient = Patient(age=60, sex="male", cac=350)

    result, _rss_total, _rss_contributions = run_patient(patient)
    target = result.targets[0]

    assert result.plaque_category == PlaqueCategory.SEVERE
    assert target.ldl_c_target == 70
    assert target.non_hdl_c_target == 100
    assert "CAC 300-999" in target.rationale
    assert "very-high-risk targets may be reasonable" in target.rationale
    assert "Severe subclinical coronary atherosclerosis" in _diagnosis_names(result)


def test_cac_1200_uses_extreme_cac_targets():
    patient = Patient(age=60, sex="male", cac=1200)

    result, _rss_total, _rss_contributions = run_patient(patient)
    target = result.targets[0]

    assert result.plaque_category == PlaqueCategory.EXTENSIVE
    assert target.ldl_c_target == 55
    assert target.non_hdl_c_target == 85
    assert "CAC >=1000" in target.rationale


def test_cac_not_recommended_to_derisk_clinical_ascvd_or_ldl_190():
    clinical = Patient(age=60, sex="male", cac=None, clinical_ascvd=True)
    severe_ldl = Patient(age=60, sex="male", cac=None, ldl_c=212)

    clinical_result, _rss_total, _rss_contributions = run_patient(clinical)
    severe_ldl_result, _rss_total, _rss_contributions = run_patient(severe_ldl)

    assert build_cac_recommendation(clinical, clinical_result) is None
    assert clinical_result.clarification["recommend_cac"] is False
    assert build_cac_recommendation(severe_ldl, severe_ldl_result) is None
    assert severe_ldl_result.clarification["recommend_cac"] is False
