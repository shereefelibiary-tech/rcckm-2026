from html import unescape

from core.enums import RiskLevel
from core.patient import Patient
from renderers.emr_renderer import render_emr_note
from renderers.prevent_card import render_prevent_card
from ui.report_layout import run_patient


def _severe_hypercholesterolemia_cac_zero_patient():
    return Patient(
        age=42,
        sex="male",
        sbp=120,
        bp_treated=False,
        tc=260,
        hdl_c=45,
        ldl_c=204,
        apob=142,
        cac=0,
        clinical_ascvd=False,
        diabetes=False,
        lipid_lowering=False,
        smoker=False,
        bmi=28,
        egfr=90,
        family_history_relationship="father",
        family_history_event_type="MI",
        family_history_age_at_event=54,
    )


def test_ldl_190_pathway_dominates_low_prevent_and_cac_zero():
    patient = _severe_hypercholesterolemia_cac_zero_patient()

    result, _, _ = run_patient(patient)
    emr = render_emr_note(patient, result)
    prevent_card_text = unescape(render_prevent_card(result))

    assert result.prevent_risk_category == RiskLevel.LOW
    assert result.risk_level != RiskLevel.LOW
    assert result.risk_level == RiskLevel.HIGH
    assert result.severe_hypercholesterolemia is True
    assert result.possible_fh_pathway is True
    assert result.targets[0].ldl_c_target == 70
    assert result.targets[0].non_hdl_c_target == 100

    assert "Severe hypercholesterolemia / LDL-C 204 mg/dL (>=190)" in result.top_drivers
    assert "LDL-C >=190 / possible FH pathway: PREVENT should not be used to de-risk treatment." in prevent_card_text
    assert "LDL-C >=190 / possible FH pathway" in emr
    assert "2. Plaque: CAC 0." in emr

    severe_index = emr.index("Severe hypercholesterolemia")
    apob_index = emr.index("Elevated ApoB")
    assert severe_index < apob_index

    assert "High-intensity lipid-lowering therapy indicated" in emr
    assert "Recheck lipids in 4-12 weeks" not in emr
