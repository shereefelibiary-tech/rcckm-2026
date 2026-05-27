import pytest

from core.engine import evaluate_patient
from renderers.emr_renderer import render_emr_note
from renderers.patient_roadmap import render_patient_roadmap_text
from tools.demo_audit import audit_demo_cases, render_demo_output_snapshot, validate_demo_case
from ui.demo_case_gallery import (
    DEMO_CATEGORIES,
    DEMO_CASES,
    demo_case_category,
    DEMO_PATIENTS,
    build_demo_patient,
    demo_case_description,
    demo_case_metadata,
    demo_case_options,
    demo_case_options_by_category,
    demo_patient_payloads,
)


MANDATORY_BASELINE_FIELDS = (
    "age",
    "sex",
    "height_in",
    "weight_lb",
    "bmi",
    "sbp",
    "dbp",
    "tc",
    "ldl_c",
    "hdl_c",
    "triglycerides",
)


def test_demo_case_gallery_exposes_curated_realistic_cases():
    options = demo_case_options()

    assert 24 <= len(options) <= 35
    assert len(options) == len(DEMO_CASES)
    labels = [label for label, _case_name in options]
    assert "Low-risk clean prevention" in labels
    assert "Multiple enhancers, missing ApoB/Lp(a)" in labels
    assert "Younger patient with premature family history" in labels
    assert "Younger strong family history" not in labels
    assert "ACEi/ARB with persistent albuminuria" in labels
    assert "Severe secondary prevention" in labels
    assert "Incidental CAC on CT" in labels
    assert "Breast arterial calcification" in labels


def test_demo_case_gallery_groups_options_by_category():
    assert set(DEMO_CATEGORIES) == {
        "Foundational prevention",
        "Atherogenic burden",
        "Plaque and imaging",
        "CKM / kidney / metabolic",
        "Treatment-state cases",
        "Special risk enhancers",
    }
    plaque_options = demo_case_options_by_category("Plaque and imaging")

    assert plaque_options
    assert all(demo_case_category(case_name) == "Plaque and imaging" for _label, case_name in plaque_options)
    assert any(case_name == "cac_300_high_plaque_burden" for _label, case_name in plaque_options)


@pytest.mark.parametrize("case_name", [case_name for _label, case_name in DEMO_CASES])
def test_every_demo_case_has_selector_description(case_name):
    assert demo_case_description(case_name)


@pytest.mark.parametrize("case_name", [case_name for _label, case_name in DEMO_CASES])
def test_every_demo_case_has_product_showcase_metadata(case_name):
    metadata = demo_case_metadata(case_name)

    assert metadata["category"] in DEMO_CATEGORIES
    assert metadata["expected_showcase_points"]
    assert metadata["expected_primary_action"]
    assert metadata["expected_level_or_level_range"]
    assert metadata["expected_risk_framing"]


@pytest.mark.parametrize("case_name", [case_name for _label, case_name in DEMO_CASES])
def test_every_demo_case_has_primary_care_baseline_data(case_name):
    payload = DEMO_PATIENTS[case_name]

    for field in MANDATORY_BASELINE_FIELDS:
        assert payload.get(field) not in ("", None), f"{case_name} missing {field}"
    assert payload["sex"] in {"male", "female"}
    assert payload.get("smoker") is not None
    assert payload.get("diabetes") is not None
    assert payload.get("egfr") is not None
    assert payload.get("creatinine") is not None


@pytest.mark.parametrize("case_name", [case_name for _label, case_name in DEMO_CASES])
def test_every_demo_case_builds_patient_with_complete_core_inputs(case_name):
    patient = build_demo_patient(case_name)

    assert patient.age is not None
    assert patient.sex in {"male", "female"}
    assert patient.height_in is not None
    assert patient.weight_lb is not None
    assert patient.bmi is not None
    assert patient.sbp is not None
    assert patient.dbp is not None
    assert patient.tc is not None
    assert patient.ldl_c is not None
    assert patient.hdl_c is not None
    assert patient.triglycerides is not None
    assert patient.non_hdl_c == pytest.approx(patient.tc - patient.hdl_c)


def test_sparse_demo_keeps_clinic_fundamentals_but_omits_advanced_data():
    patient = build_demo_patient("sparse_realistic_pcp_intake")

    assert patient.tc is not None
    assert patient.ldl_c is not None
    assert patient.hdl_c is not None
    assert patient.triglycerides is not None
    assert patient.egfr is not None
    assert patient.apob is None
    assert patient.lp_a_value is None
    assert patient.uacr is None
    assert patient.cac is None
    assert patient.cac_not_done is True


def test_younger_premature_family_history_demo_is_realistic_and_framed():
    payload = DEMO_PATIENTS["younger_strong_family_history"]
    patient = build_demo_patient("younger_strong_family_history")

    for field in MANDATORY_BASELINE_FIELDS:
        assert payload.get(field) not in ("", None)
    assert 35 <= patient.age <= 39
    assert patient.a1c is not None and 5.7 <= patient.a1c < 6.5
    assert patient.family_history_premature_ascvd is True
    assert patient.family_history_relationship == "father"
    assert patient.family_history_event_type == "MI"
    assert patient.family_history_age_at_event == 49
    assert patient.cac is None
    assert patient.cac_not_done is True
    assert "Low short-term ASCVD risk" in demo_case_description("younger_strong_family_history")


def test_younger_premature_family_history_demo_output_uses_lifetime_trajectory_language():
    patient = build_demo_patient("younger_strong_family_history")
    result = evaluate_patient(patient)
    emr = render_emr_note(patient, result)
    roadmap = render_patient_roadmap_text(patient, result)
    combined = f"{emr}\n{roadmap}"

    assert result.level_classification["level"] == "3B"
    assert "Level 3B - elevated lifetime cardiometabolic risk despite low short-term event risk" in combined
    assert "10-year ASCVD risk:" in emr
    assert "30-year ASCVD risk:" in emr
    assert "- 10-year ASCVD risk:" in roadmap
    assert "- 30-year ASCVD risk:" in roadmap
    assert "total cardiovascular risk" not in combined.lower()
    assert "CAC not routinely recommended at this age; consider only if results would change management." in emr
    assert "hsCRP - inflammatory residual risk" not in combined
    assert "Aspirin not indicated for routine primary prevention." in emr
    assert "Risk context: premature family history of ASCVD (Father MI age 49)." in emr


def test_high_apob_discordance_demo_is_apob_driven_and_actionable():
    patient = build_demo_patient("high_apob_discordance")
    result = evaluate_patient(patient)
    text = render_demo_output_snapshot("high_apob_discordance")

    assert patient.apob == 125
    assert patient.family_history_premature_ascvd is True
    assert patient.family_history_relationship == "father"
    assert result.level_classification["label"] == (
        "Level 3B - elevated lifetime ASCVD risk with ApoB-driven atherogenic burden"
    )
    assert "Level 3B - elevated lifetime ASCVD risk with ApoB-driven atherogenic burden." in text
    assert "Moderate-intensity statin therapy is reasonable given elevated ApoB particle burden, premature family history, and elevated 30-year ASCVD risk despite low 10-year ASCVD risk." in text
    assert "elevated ApoB particle burden" in text
    assert "premature family history" in text
    assert "low 10-year ASCVD risk" in text
    assert "CAC may clarify plaque burden if the patient is hesitant or if treatment intensity remains uncertain." in text
    assert "Aspirin not indicated for routine primary prevention." in text
    assert "if risk-enhancing factors or ApoB/LDL-C burden support treatment" not in text
    assert "high near-term risk" not in text.lower()
    assert "High-intensity statin" not in text
    assert demo_case_description("high_apob_discordance") == (
        "Low 10-year risk, but elevated ApoB and premature family history make earlier lipid-lowering reasonable to discuss."
    )


def test_rheumatoid_arthritis_demo_is_inflammatory_context_without_overtreatment():
    patient = build_demo_patient("rheumatoid_arthritis_risk_enhancer")
    result = evaluate_patient(patient)
    text = render_demo_output_snapshot("rheumatoid_arthritis_risk_enhancer")

    assert patient.rheumatoid_arthritis is True
    assert result.level_classification["label"] == (
        "Level 3A - low short-term ASCVD risk with inflammatory risk-enhancer context"
    )
    assert "Level 3A - low short-term ASCVD risk with inflammatory risk-enhancer context." in text
    assert "10-year ASCVD risk: 1.54%" in text
    assert "30-year ASCVD risk: 9.85%" in text
    assert "Risk context: rheumatoid arthritis; premature family history of ASCVD" in text
    assert "Existing rheumatoid arthritis; chronic inflammatory disease risk enhancer." in text
    assert "No new cardiometabolic diagnosis candidates generated." in text
    assert "Continue lifestyle-focused prevention; no lipid escalation today based on current LDL-C/ApoB and ASCVD risk profile." in text
    assert "RA is a risk enhancer; ensure inflammation is clinically controlled and avoid undertreating traditional risk factors." in text
    assert "CAC is not routinely needed at this risk level; use only if results would change lipid-treatment decisions." in text
    assert "Aspirin not indicated for routine primary prevention." in text
    assert "Level 3B - actionable early CKM / atherogenic risk" not in text
    assert "Moderate-intensity statin therapy is reasonable" not in text
    assert "High-intensity statin" not in text
    assert "Consider hsCRP" not in text
    assert "risk-enhancing factors" not in text
    assert "high near-term risk" not in text.lower()


def test_demo_outputs_do_not_use_vague_lipid_fallback_language():
    forbidden = (
        "No medication escalation today",
        "Treatment is reasonable.",
        "may be reasonable if risk-enhancing factors support treatment",
        "if risk-enhancing factors or ApoB/LDL-C burden support treatment",
        "risk-factor control",
        "management as appropriate",
        "follow clinically",
    )
    for _label, case_name in DEMO_CASES:
        text = render_demo_output_snapshot(case_name)
        for phrase in forbidden:
            assert phrase not in text, f"{case_name} used vague phrase: {phrase}"


def test_demo_audit_utility_flags_no_errors_and_expected_sparse_warning():
    report = audit_demo_cases()

    assert report.errors == []
    assert any("sparse advanced prevention data" in warning for warning in report.warnings)
    assert "RCCKM Demo Case Audit" in report.format_summary()
    assert all(0 <= case.coherence_score <= 100 for case in report.cases)
    assert all(0 <= case.completeness_score <= 100 for case in report.cases)
    assert all(0 <= case.patient_readability_score <= 100 for case in report.cases)
    assert all(0 <= case.showcase_value_score <= 100 for case in report.cases)
    assert "Summary table:" in report.format_summary()
    assert "Demos needing rewrite: none" in report.format_summary()


def test_validate_demo_case_accepts_case_name_and_returns_structured_scores():
    finding = validate_demo_case("younger_strong_family_history")

    assert finding.errors == []
    assert finding.label == "Younger patient with premature family history"
    assert finding.coherence_score == 100
    assert finding.completeness_score == 100
    assert finding.patient_readability_score == 100
    assert finding.showcase_value_score == 100
    assert "premature family history" in finding.showcase_concepts


def test_demo_output_snapshot_text_uses_safe_patient_and_emr_wording():
    text = render_demo_output_snapshot("younger_strong_family_history")

    assert "DEMO: Younger patient with premature family history" in text
    assert "10-year ASCVD risk:" in text
    assert "30-year ASCVD risk:" in text
    assert "total cardiovascular risk" not in text.lower()
    assert "heart failure" not in text.lower()
    assert "inflammatory residual risk" not in text.lower()


def test_ckd_albuminuria_demo_is_action_oriented_without_passive_no_escalation():
    patient = build_demo_patient("ckd_albuminuria")
    result = evaluate_patient(patient)
    emr = render_emr_note(patient, result)

    assert result.level_classification["label"] == (
        "Level 3B - CKM stage 3 with albuminuria-mediated kidney and ASCVD risk"
    )
    assert "Level 3B - CKM stage 3 with albuminuria-mediated kidney and ASCVD risk." in emr
    assert "10-year ASCVD risk:" in emr
    assert "30-year ASCVD risk:" in emr
    assert "CKM stage 3 with kidney G2A2 and plaque unmeasured / CAC not performed." in emr
    assert "No medication escalation today." not in emr
    assert "Moderate-intensity statin therapy is reasonable given borderline/intermediate ASCVD risk with albuminuria and metabolic risk-enhancing factors." in emr
    assert "Confirm persistent albuminuria with repeat UACR if not already confirmed; optimize kidney-protective therapy." in emr
    assert "Treat BP toward goal <130/80 if tolerated." in emr
    assert "Continue or optimize ACEi/ARB therapy if hypertension and persistent albuminuria are present." in emr
    assert "Consider SGLT2 inhibitor if UACR is >=200 mg/g" in emr
    assert "hsCRP - inflammatory biomarker clarification" not in emr
    assert "Consider hsCRP only if inflammatory risk clarification would change management." in emr


def test_severe_secondary_prevention_demo_uses_very_high_risk_ascvd_targets():
    patient = build_demo_patient("severe_secondary_prevention")
    result = evaluate_patient(patient)
    emr = render_emr_note(patient, result)
    roadmap = render_patient_roadmap_text(patient, result)
    target = result.targets[0]

    assert patient.clinical_ascvd is True
    assert result.level_classification["level"] == "5"
    assert target.ldl_c_target == 55
    assert target.non_hdl_c_target == 85
    assert target.apob_target == 65
    assert "established ASCVD; CAC 5000 is context only" in emr
    assert "Known cardiovascular disease is present, so treatment decisions are based on secondary-prevention goals rather than risk estimates alone." in emr
    assert "very-high-risk ASCVD targets" in emr
    assert "LDL-C <70 mg/dL remains the minimum secondary-prevention threshold" in emr
    assert "PREVENT-informed primary-prevention target" not in emr
    assert "Because heart artery disease is already established" in roadmap


def test_demo_payloads_are_defensive_copies():
    payloads = demo_patient_payloads()
    payloads["healthy_low_risk_prevention"]["age"] = 999

    assert DEMO_PATIENTS["healthy_low_risk_prevention"]["age"] == 34
