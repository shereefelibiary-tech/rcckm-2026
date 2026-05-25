from core.patient import Patient
from ui.report_layout import _build_targets_html, run_patient


def test_target_card_shows_apob_80_for_cac_100_primary_prevention():
    patient = Patient(age=61, sex="female", cac=145, ldl_c=124, non_hdl_c=162, apob=112)
    result, _rss_total, _contributions = run_patient(patient)

    html = _build_targets_html(result, patient)

    assert "LDL-C" in html
    assert "non-HDL-C" in html
    assert "ApoB" in html
    assert "&lt;70" in html
    assert "&lt;100" in html
    assert "&lt;80" in html
    assert "RCCKM advanced particle target" in html


def test_target_card_shows_apob_60_for_very_high_risk_when_advanced_target_shown():
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
    assert "&lt;60" in html
    assert "RCCKM advanced particle target" in html
