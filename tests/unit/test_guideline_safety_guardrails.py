from core.engine import evaluate_patient
from core.patient import Patient
from modules.actions.engine import build_action_plan
from modules.prevent.calculator import calculate_prevent_summary
from renderers.emr_renderer import render_emr_note
from renderers.prevent_card import render_prevent_card
from smartphrase_ingest.parser import parse_smartphrase_report


def test_clinical_ascvd_cac_zero_secondary_prevention_guardrail():
    patient = Patient(
        age=62,
        sex="male",
        clinical_ascvd=True,
        clinical_ascvd_context="prior NSTEMI and PCI/stent",
        cac=0,
        ldl_c=132,
        non_hdl_c=160,
        apob=105,
        prevent_10y_ascvd=2.0,
    )
    result = evaluate_patient(patient)
    emr = render_emr_note(patient, result)
    prevent_html = render_prevent_card(result)
    diagnosis_text = " ".join(candidate.name for candidate in result.diagnosis_candidates)

    assert "Level: 5 - clinical ASCVD / secondary prevention" in emr
    assert "PREVENT not used for treatment decisions in established ASCVD." in prevent_html
    assert "Plaque: CAC 0." in emr
    assert "Intensify secondary-prevention lipid-lowering therapy" in emr
    assert "Subclinical coronary atherosclerosis" not in diagnosis_text


def test_secondary_prevention_target_tiers_high_and_very_high():
    high_risk = evaluate_patient(Patient(age=60, sex="female", clinical_ascvd=True))
    assert high_risk.targets[0].ldl_c_target == 70
    assert high_risk.targets[0].non_hdl_c_target == 100

    very_high = evaluate_patient(
        Patient(
            age=65,
            sex="female",
            clinical_ascvd=True,
            clinical_ascvd_context="prior MI and ischemic stroke",
            diabetes=True,
            ldl_c=110,
        )
    )
    assert very_high.targets[0].ldl_c_target == 55
    assert very_high.targets[0].non_hdl_c_target == 85


def test_ldl_190_and_suspected_fh_guardrails():
    ldl_case = Patient(age=42, sex="male", ldl_c=204, apob=142, cac=0)
    ldl_result = evaluate_patient(ldl_case)
    ldl_emr = render_emr_note(ldl_case, ldl_result)

    assert ldl_result.level_classification["level"] != "1"
    assert "Context: LDL-C >=190 / possible FH pathway." in ldl_emr
    assert "High-intensity lipid-lowering therapy indicated" in ldl_emr

    treated_fh = Patient(age=48, sex="male", ldl_c=92, lipid_lowering=True, suspected_fh_hefh=True)
    fh_result = evaluate_patient(treated_fh)
    fh_emr = render_emr_note(treated_fh, fh_result)
    fh_plan = build_action_plan(treated_fh, fh_result)

    assert fh_result.level_classification["level"] == "3B"
    assert "High-intensity or maximally tolerated statin therapy indicated." in fh_plan["recommendations"]
    assert "Context: suspected FH / HeFH." in fh_emr


def test_prevent_age_range_guardrails():
    required = dict(
        sex="male",
        tc=190,
        hdl_c=50,
        sbp=120,
        diabetes=False,
        smoker=False,
        bp_treated=False,
    )
    young = calculate_prevent_summary(Patient(age=29, **required))
    older = calculate_prevent_summary(Patient(age=80, **required))

    assert young["available"] is False
    assert young["unsupported_reason"] == (
        "PREVENT not validated for age <30; interpretation should rely on clinical risk factors and guideline-specific pathways."
    )
    assert older["available"] is False
    assert older["unsupported_reason"] == "PREVENT not validated for age >79; individualized clinical judgment required."

    provided_young = calculate_prevent_summary(Patient(age=29, prevent_10y_ascvd=1.2, **required))
    assert provided_young["prevent_10y_ascvd"] is None
    assert provided_young["available"] is False


def test_broad_asian_ancestry_does_not_trigger_specific_enhancer():
    report = parse_smartphrase_report("Asian ancestry: Yes\nSouth Asian ancestry: Unknown\nFilipino ancestry: No")
    assert report.extracted.get("south_asian_ancestry") is None
    assert report.extracted.get("filipino_ancestry") is False
    assert "higher_risk_ancestry_context" not in report.extracted


def test_no_unknown_reproductive_and_inflammatory_markers_do_not_appear():
    report = parse_smartphrase_report(
        "RA: No\nSLE: Unknown\nPsoriasis: No\nIBD: Unknown\n"
        "Small for gestational age infant: No\nPreeclampsia: Unknown\nPCOS: No"
    )
    patient = Patient(age=45, sex="female", **report.extracted)
    result = evaluate_patient(patient)
    emr = render_emr_note(patient, result)

    assert report.extracted["rheumatoid_arthritis"] is False
    assert report.extracted["sle"] is None
    assert report.extracted["small_for_gestational_age"] is False
    assert "SGA infant" not in emr
    assert "Preeclampsia" not in emr
    assert "Inflammatory/immune" not in emr


def test_hiv_stable_art_and_unknown_guardrails():
    positive = Patient(age=55, sex="male", hiv=True, stable_art=True)
    positive_result = evaluate_patient(positive)
    positive_plan = build_action_plan(positive, positive_result)
    assert "Statin therapy recommended/reasonable in HIV; review ART-statin interactions." in positive_plan["recommendations"]

    report = parse_smartphrase_report("HIV: Unknown\nStable ART: Unknown")
    unknown = Patient(age=55, sex="male", **report.extracted)
    unknown_result = evaluate_patient(unknown)
    unknown_plan = build_action_plan(unknown, unknown_result)
    assert "HIV" not in " ".join(unknown_plan["recommendations"])
