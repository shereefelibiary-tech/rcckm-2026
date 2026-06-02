from core.patient import Patient
from ui.report_layout import _build_targets_html, run_patient


def test_target_card_shows_apob_80_for_cac_100_primary_prevention():
    patient = Patient(age=61, sex="female", cac=145, ldl_c=124, non_hdl_c=162, apob=112)
    result, _rss_total, _contributions = run_patient(patient)

    html = _build_targets_html(result, patient)

    assert "LDL-C" in html
    assert "ApoB" in html
    assert "&lt;70" in html
    assert "&lt;80" in html
    assert "non-HDL-C" not in html
    assert html.count('<span class="target-item">') == 2
    assert 'content: "•"' not in html
    assert "RCCKM advanced particle target" not in html


def test_target_card_renders_target_first_without_arrow_text():
    patient = Patient(age=58, sex="female", cac=12, ldl_c=158, apob=121)
    result, _rss_total, _contributions = run_patient(patient)

    html = _build_targets_html(result, patient)

    assert "-&gt;" not in html
    assert "->" not in html
    assert "&lt;100 mg/dL" in html
    assert "&lt;90 mg/dL" in html
    assert "Current 158 mg/dL" in html
    assert "Current 121 mg/dL" in html
    assert html.index("&lt;100 mg/dL") < html.index("Current 158 mg/dL")
    assert html.index("&lt;90 mg/dL") < html.index("Current 121 mg/dL")
    assert html.count("Above goal") >= 2


def test_target_card_always_renders_when_targets_are_not_set():
    patient = Patient(age=55, sex="male", ldl_c=88, apob=70, cac=0)
    result, _rss_total, _contributions = run_patient(patient)

    html = _build_targets_html(result, patient)

    assert "targets-compact" in html
    assert "LDL-C" in html
    assert "ApoB" in html
    assert html.count('<span class="target-item">') == 2
    assert html.count("No target indicated") == 2
    assert "Not set" not in html
    assert "Current 88 mg/dL" in html
    assert "Current 70 mg/dL" in html
    assert "At goal" not in html
    assert "Above goal" not in html


def test_target_card_shows_apob_65_for_very_high_risk_when_advanced_target_shown():
    patient = Patient(
        age=65,
        sex="male",
        clinical_ascvd=True,
        clinical_ascvd_context="prior MI and ischemic stroke",
        diabetes=True,
        apob=90,
    )
    result, _rss_total, _contributions = run_patient(patient)

    html = _build_targets_html(result, patient)

    assert "ApoB" in html
    assert "&lt;65" in html
    assert "Very-high-risk ASCVD targets" in html
    assert "RCCKM advanced particle target" not in html
