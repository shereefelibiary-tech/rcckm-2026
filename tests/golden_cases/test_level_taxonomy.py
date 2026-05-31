import pytest

from core.engine import evaluate_patient
from core.patient import Patient
from modules.levels.level_classifier import classify_rcckm_level


def _case(patient):
    result = evaluate_patient(patient)
    classification = classify_rcckm_level(patient, result)
    actions = "\n".join(
        [
            result.dominant_action or "",
            *(result.recommendations or []),
            *list((result.action_domains or {}).values()),
        ]
    )
    diagnoses = "\n".join(
        candidate.name or "" for candidate in result.diagnosis_candidates
    )
    return result, classification, actions, diagnoses


@pytest.mark.parametrize(
    ("name", "patient", "expected_level"),
    [
        (
            "level1_low_complete",
            Patient(
                age=36,
                sex="female",
                tc=160,
                hdl_c=62,
                ldl_c=82,
                triglycerides=90,
                apob=68,
                lp_a_value=20,
                lp_a_unit="nmol/L",
                egfr=96,
                uacr=0,
                prevent_10y_ascvd=0.4,
                prevent_30y_ascvd=3.0,
                cac=None,
                cac_not_done=True,
            ),
            "1",
        ),
        (
            "level2a_isolated_prediabetes",
            Patient(
                age=42,
                sex="female",
                a1c=5.8,
                prevent_10y_ascvd=0.6,
                prevent_30y_ascvd=5.0,
            ),
            "2A",
        ),
        (
            "level2b_converging_metabolic",
            Patient(
                age=41,
                sex="female",
                a1c=5.8,
                triglycerides=176,
                apob=84,
                masld=True,
                osa=True,
                prevent_10y_ascvd=0.7,
                prevent_30y_ascvd=5.4,
            ),
            "2B",
        ),
        (
            "level3a_30y_only",
            Patient(
                age=42,
                sex="male",
                ldl_c=118,
                apob=82,
                triglycerides=112,
                prevent_10y_ascvd=1.3,
                prevent_30y_ascvd=12.0,
            ),
            "3A",
        ),
        (
            "level3a_ldl_160",
            Patient(
                age=38,
                sex="male",
                ldl_c=164,
                prevent_10y_ascvd=1.4,
                prevent_30y_ascvd=9.0,
                cac=None,
                cac_not_done=True,
            ),
            "3A",
        ),
        (
            "level3b_albuminuria_prediabetes_bp",
            Patient(
                age=50,
                sex="male",
                uacr=34,
                egfr=76,
                a1c=6.1,
                bp_treated=True,
                triglycerides=162,
                apob=92,
                prevent_10y_ascvd=3.7,
                prevent_30y_ascvd=18.8,
                cac=None,
                cac_not_done=True,
            ),
            "3B",
        ),
        (
            "level3b_reproductive_lpa_uacr_missing",
            Patient(
                age=54,
                sex="female",
                a1c=6.0,
                triglycerides=198,
                apob=106,
                ldl_c=136,
                non_hdl_c=170,
                lp_a_value=132,
                lp_a_unit="nmol/L",
                bp_treated=True,
                egfr=76,
                uacr=None,
                early_menopause=True,
                gestational_hypertension=True,
                gestational_diabetes=True,
                prevent_10y_ascvd=3.42,
                prevent_30y_ascvd=17.0,
                cac=None,
                cac_not_done=True,
            ),
            "3B",
        ),
        (
            "level2b_not_3",
            Patient(
                age=41,
                sex="female",
                a1c=5.8,
                triglycerides=176,
                apob=84,
                masld=True,
                osa=True,
                uacr=12,
                prevent_10y_ascvd=0.7,
                prevent_30y_ascvd=5.4,
                cac=None,
                cac_not_done=True,
            ),
            "2B",
        ),
        (
            "level2b_high_lpa_reproductive_low_prevent",
            Patient(
                age=45,
                sex="female",
                ldl_c=124,
                non_hdl_c=142,
                apob=86,
                lp_a_value=268,
                lp_a_unit="nmol/L",
                early_menopause=True,
                menopause_age=44,
                preeclampsia=True,
                egfr=96,
                uacr=6,
                diabetes=False,
                prevent_10y_ascvd=0.94,
                prevent_30y_ascvd=6.86,
                cac=None,
                cac_not_done=True,
            ),
            "2B",
        ),
        (
            "level2b_converging_early_signals_low_prevent",
            Patient(
                age=44,
                sex="female",
                tc=200,
                hdl_c=50,
                ldl_c=126,
                non_hdl_c=150,
                triglycerides=151,
                apob=88,
                lp_a_value=118,
                lp_a_unit="nmol/L",
                a1c=5.7,
                egfr=96,
                uacr=8,
                preeclampsia=True,
                osa=True,
                hscrp=2.1,
                prevent_10y_ascvd=0.8,
                prevent_30y_ascvd=5.76,
                cac=None,
                cac_not_done=True,
            ),
            "2B",
        ),
        (
            "level2b_near_level3_threshold",
            Patient(
                age=40,
                sex="male",
                ldl_c=158,
                apob=116,
                triglycerides=176,
                uacr=9,
                prevent_10y_ascvd=1.41,
                prevent_30y_ascvd=9.82,
                cac=None,
                cac_not_done=True,
            ),
            "2B",
        ),
        (
            "level3b_midrange_30y_reproductive_lpa_uacr_missing",
            Patient(
                age=54,
                sex="female",
                a1c=6.0,
                triglycerides=198,
                apob=106,
                ldl_c=136,
                non_hdl_c=170,
                lp_a_value=132,
                lp_a_unit="nmol/L",
                bp_treated=True,
                egfr=76,
                uacr=None,
                early_menopause=True,
                gestational_hypertension=True,
                gestational_diabetes=True,
                prevent_10y_ascvd=3.42,
                prevent_30y_ascvd=17.53,
                cac=None,
                cac_not_done=True,
            ),
            "3B",
        ),
        (
            "level3b_atherogenic_30y_ldl_apob",
            Patient(
                age=42,
                sex="male",
                prevent_10y_ascvd=1.73,
                prevent_30y_ascvd=11.85,
                ldl_c=166,
                apob=121,
                non_hdl_c=202,
                triglycerides=182,
                cac=None,
                cac_not_done=True,
                diabetes=False,
                uacr=9,
            ),
            "3B",
        ),
        (
            "level3b_intermediate_prevent_uacr_missing",
            Patient(
                age=56,
                sex="male",
                prevent_10y_ascvd=5.41,
                prevent_30y_ascvd=22.55,
                bp_treated=True,
                a1c=5.9,
                triglycerides=185,
                apob=102,
                non_hdl_c=165,
                lp_a_value=80,
                lp_a_unit="nmol/L",
                egfr=76,
                uacr=None,
                cac=None,
                cac_not_done=True,
            ),
            "3B",
        ),
        (
            "level4_cac_38",
            Patient(age=58, sex="female", cac=38, prevent_10y_ascvd=4.2),
            "4",
        ),
        (
            "level5_cac_350",
            Patient(age=55, sex="male", cac=350, ldl_c=132, non_hdl_c=157),
            "5",
        ),
        (
            "clinical_ascvd_overrides",
            Patient(
                age=60,
                sex="male",
                clinical_ascvd=True,
                cac=0,
                prevent_10y_ascvd=2.0,
                prevent_30y_ascvd=None,
            ),
            "5",
        ),
        (
            "severe_hyperchol_ldl_204_cac0",
            Patient(
                age=42,
                sex="male",
                ldl_c=204,
                apob=142,
                cac=0,
                prevent_10y_ascvd=1.5,
                prevent_30y_ascvd=8.0,
            ),
            "3B",
        ),
    ],
)
def test_level_taxonomy_golden_cases(name, patient, expected_level):
    result, classification, actions, diagnoses = _case(patient)

    assert classification.level == expected_level, name
    assert classification.prevent_category == getattr(
        result.prevent_risk_category, "value", result.prevent_risk_category
    )
    if patient.cac is None:
        assert "unmeasured" in classification.plaque_status.lower()
        assert "subclinical coronary atherosclerosis" not in diagnoses.lower()
        if patient.clinical_ascvd:
            assert "secondary prevention" in classification.treatment_posture
            assert "PREVENT not used for treatment decisions in established ASCVD" in render_note_for(patient)
    if patient.ldl_c is not None and patient.ldl_c >= 190:
        assert classification.level != "1"
        assert "High-intensity or maximally tolerated statin therapy indicated" in actions


def render_note_for(patient):
    from renderers.emr_renderer import render_emr_note

    result = evaluate_patient(patient)
    return render_emr_note(patient, result)


def _hidden_cluster_patient(**overrides):
    values = dict(
        age=43,
        sex="female",
        ldl_c=159,
        apob=126,
        lp_a_value=286,
        lp_a_unit="nmol/L",
        hscrp=3.1,
        rheumatoid_arthritis=True,
        south_asian_ancestry=True,
        gestational_diabetes=True,
        family_history_premature_ascvd=True,
        family_history_relationship="father",
        family_history_event_type="MI",
        family_history_age_at_event=52,
        cac=None,
        prevent_10y_ascvd=0.7,
        prevent_30y_ascvd=5.22,
    )
    values.update(overrides)
    return Patient(**values)


def test_level_3b_albuminuria_case_action_and_clarifiers_are_treatment_forward():
    patient = Patient(
        age=50,
        sex="male",
        uacr=34,
        egfr=76,
        a1c=6.1,
        bp_treated=True,
        triglycerides=162,
        apob=92,
        prevent_10y_ascvd=3.7,
        prevent_30y_ascvd=18.8,
        cac=None,
        cac_not_done=True,
    )
    result, classification, actions, diagnoses = _case(patient)

    assert classification.level == "3B"
    assert classification.prevent_category == "BORDERLINE"
    assert "albuminuria" in " ".join(classification.drivers).lower()
    assert "optimize kidney-protective therapy" in actions
    assert "Short-term ASCVD risk is low, but albuminuria and longer-term risk make lipid-lowering worth discussing" in actions
    assert "CAC reasonable for risk clarification if treatment decision remains uncertain" in actions
    assert "subclinical coronary atherosclerosis" not in diagnoses.lower()


def test_lpa_family_history_pattern_stays_level_2b_without_plaque_diagnosis():
    patient = Patient(
        age=46,
        sex="female",
        ldl_c=124,
        non_hdl_c=142,
        apob=86,
        lp_a_value=188,
        lp_a_unit="nmol/L",
        family_history_premature_ascvd=True,
        prevent_10y_ascvd=0.66,
        prevent_30y_ascvd=5.03,
        cac=None,
        cac_not_done=True,
    )
    result, classification, actions, diagnoses = _case(patient)

    assert classification.level == "2B"
    assert classification.prevent_category == "LOW"
    assert "Plaque unmeasured" in classification.plaque_status
    assert "CAC reasonable for risk clarification" in actions
    assert "subclinical coronary atherosclerosis" not in diagnoses.lower()


def test_high_lpa_reproductive_low_prevent_stays_level_2b_with_cac_clarification():
    patient = Patient(
        age=45,
        sex="female",
        ldl_c=124,
        non_hdl_c=142,
        apob=86,
        lp_a_value=268,
        lp_a_unit="nmol/L",
        early_menopause=True,
        menopause_age=44,
        preeclampsia=True,
        egfr=96,
        uacr=6,
        diabetes=False,
        prevent_10y_ascvd=0.94,
        prevent_30y_ascvd=6.86,
        cac=None,
        cac_not_done=True,
    )
    result, classification, actions, diagnoses = _case(patient)
    note = render_note_for(patient)

    assert classification.level == "2B"
    assert "converging early risk" in classification.label.lower()
    assert "Level: 2B - converging early risk signals." in note
    assert "Elevated lipoprotein(a)" in note
    assert "Context: elevated Lp(a); Early menopause 44; Preeclampsia." in note
    assert "CAC reasonable for risk clarification if treatment decision remains uncertain" in actions
    assert "Lipid lowering: no escalation today; document elevated Lp(a) and reproductive risk markers as risk enhancers" in actions
    assert "Aspirin: Not indicated" in note
    assert "kidney-protective" not in actions
    assert "subclinical coronary atherosclerosis" not in diagnoses.lower()


def test_hidden_high_risk_cluster_upgrades_young_low_prevent_patient():
    from modules.actions.scaffold import build_action_instrument_panel
    from renderers.patient_roadmap import render_patient_roadmap_text

    patient = _hidden_cluster_patient()
    result, classification, actions, diagnoses = _case(patient)
    panel = {item.domain_id: item for item in build_action_instrument_panel(patient, result)}
    roadmap = render_patient_roadmap_text(patient, result)

    assert classification.level == "3B"
    assert "hidden atherogenic risk burden" in classification.label
    assert "ApoB >=120" in classification.drivers
    assert "Lp(a)" in classification.drivers
    assert "premature family history" in classification.drivers
    assert "inflammatory disease" in classification.drivers
    assert "South Asian ancestry" in classification.drivers
    assert "gestational diabetes" in classification.drivers
    assert "Discuss lipid-lowering therapy" in actions
    assert panel["lipid_lowering"].status == "Discuss lipid-lowering therapy"
    assert panel["plaque_cac"].status == "CAC may clarify treatment"
    assert "Coronary plaque: Calcium scan may clarify treatment." in roadmap
    assert (
        "Several inherited and biologic risk factors are present despite a low short-term risk estimate."
        in roadmap
    )
    assert panel["aspirin_antiplatelet"].status == "Not indicated"
    assert "diabetes" not in diagnoses.lower()
    assert "ckd" not in diagnoses.lower()


def test_hidden_risk_lipid_discussion_assigns_targets_and_cac_clarification():
    from modules.actions.scaffold import build_action_instrument_panel
    from ui.report_layout import _build_targets_html

    patient = Patient(
        age=44,
        sex="female",
        ldl_c=147,
        apob=118,
        lp_a_value=282,
        lp_a_unit="nmol/L",
        family_history_premature_ascvd=True,
        family_history_relationship="father",
        family_history_event_type="MI",
        family_history_age_at_event=52,
        preeclampsia=True,
        gestational_diabetes=True,
        cac=None,
        prevent_10y_ascvd=0.7,
        prevent_30y_ascvd=5.2,
        lipid_lowering=False,
    )
    result, classification, _actions, _diagnoses = _case(patient)
    panel = {item.domain_id: item for item in build_action_instrument_panel(patient, result)}
    targets_html = _build_targets_html(result, patient)

    assert classification.level == "3B"
    assert panel["lipid_lowering"].status in {
        "Discuss lipid-lowering therapy",
        "Discuss moderate-intensity statin",
        "Lipid-lowering therapy indicated",
    }
    assert result.targets[0].ldl_c_target == 100
    assert result.targets[0].apob_target == 90
    assert "Not set" not in targets_html
    assert "&lt;100 mg/dL" in targets_html
    assert "&lt;90 mg/dL" in targets_html
    assert panel["plaque_cac"].status == "CAC may clarify treatment"
    assert "CAC not needed" not in panel["plaque_cac"].action_card_line


def test_hidden_risk_cac_zero_does_not_force_cac_clarification():
    from modules.actions.scaffold import build_action_instrument_panel

    patient = Patient(
        age=44,
        sex="female",
        ldl_c=147,
        apob=118,
        lp_a_value=282,
        lp_a_unit="nmol/L",
        family_history_premature_ascvd=True,
        family_history_relationship="father",
        family_history_event_type="MI",
        family_history_age_at_event=52,
        preeclampsia=True,
        gestational_diabetes=True,
        cac=0,
        prevent_10y_ascvd=0.7,
        prevent_30y_ascvd=5.2,
        lipid_lowering=False,
    )
    result, _classification, _actions, _diagnoses = _case(patient)
    panel = {item.domain_id: item for item in build_action_instrument_panel(patient, result)}

    assert panel["plaque_cac"].status == "CAC 0"
    assert "CAC may clarify treatment" not in panel["plaque_cac"].action_card_line


def test_hidden_high_risk_cluster_does_not_fire_when_cac_zero():
    patient = _hidden_cluster_patient(cac=0)
    _result, classification, _actions, diagnoses = _case(patient)

    assert classification.label != "Level 3B - hidden atherogenic risk burden"
    assert classification.level != "3B"
    assert "subclinical coronary atherosclerosis" not in diagnoses.lower()


def test_hidden_high_risk_cluster_requires_lipid_burden():
    patient = _hidden_cluster_patient(ldl_c=120, apob=90)
    _result, classification, _actions, _diagnoses = _case(patient)

    assert classification.label != "Level 3B - hidden atherogenic risk burden"


def test_hidden_high_risk_cluster_does_not_count_generic_family_history():
    patient = _hidden_cluster_patient(
        rheumatoid_arthritis=False,
        south_asian_ancestry=False,
        gestational_diabetes=False,
        family_history_premature_ascvd=False,
        premature_fhx_ascvd=False,
        family_history_summary="Family history of CAD",
        family_history_relationship=None,
        family_history_event_type=None,
        family_history_age_at_event=None,
    )
    _result, classification, _actions, _diagnoses = _case(patient)

    assert classification.label != "Level 3B - hidden atherogenic risk burden"


def test_hidden_high_risk_cluster_requires_at_least_two_enhancers():
    patient = _hidden_cluster_patient(
        rheumatoid_arthritis=False,
        south_asian_ancestry=False,
        gestational_diabetes=False,
        family_history_premature_ascvd=False,
        premature_fhx_ascvd=False,
        family_history_relationship=None,
        family_history_event_type=None,
        family_history_age_at_event=None,
    )
    _result, classification, _actions, _diagnoses = _case(patient)

    assert classification.label != "Level 3B - hidden atherogenic risk burden"


def test_off_treatment_level3b_atherogenic_risk_discusses_lipid_lowering():
    from renderers.emr_renderer import render_emr_note
    from renderers.patient_roadmap import render_patient_roadmap_text

    patient = Patient(
        age=51,
        sex="female",
        ldl_c=137,
        apob=112,
        lp_a_value=176.8,
        lp_a_unit="nmol/L",
        family_history_premature_ascvd=True,
        family_history_relationship="mother",
        family_history_event_type="MI",
        family_history_age_at_event=54,
        gestational_hypertension=True,
        cac=None,
        lipid_lowering=False,
        prevent_10y_ascvd=0.7,
        prevent_30y_ascvd=5.2,
    )
    result, classification, actions, _diagnoses = _case(patient)
    note = render_emr_note(patient, result)
    roadmap = render_patient_roadmap_text(patient, result)

    assert classification.level == "3B"
    assert "Discuss lipid-lowering therapy" in actions
    assert result.targets[0].ldl_c_target == 100
    assert result.targets[0].apob_target == 90
    assert "1. Lipids: Lipid-lowering therapy indicated; LDL-C <100, ApoB <90, non-HDL-C <130." in note
    assert "No lipid escalation" not in note
    assert "1. Cholesterol: Discuss starting cholesterol-lowering therapy." in roadmap
    assert "Continue current lipid treatment" not in roadmap


def test_level_2b_converging_early_signals_low_prevent_uses_formal_taxonomy():
    patient = Patient(
        age=44,
        sex="female",
        tc=200,
        hdl_c=50,
        ldl_c=126,
        non_hdl_c=150,
        triglycerides=151,
        apob=88,
        lp_a_value=118,
        lp_a_unit="nmol/L",
        a1c=5.7,
        egfr=96,
        uacr=8,
        preeclampsia=True,
        osa=True,
        hscrp=2.1,
        prevent_10y_ascvd=0.8,
        prevent_30y_ascvd=5.76,
        cac=None,
        cac_not_done=True,
    )
    result, classification, actions, diagnoses = _case(patient)
    note = render_note_for(patient)

    assert classification.level == "2B"
    assert classification.prevent_category == "LOW"
    assert "Level: 2B - converging early risk signals." in note
    assert "PREVENT: ASCVD 10y 0.8% (Low); 30y 5.76%." in note
    assert "kidney G1A1" in note
    assert "Atherogenic/metabolic burden:" not in note
    assert "Context: OSA; Preeclampsia." in note
    assert "Lipids: No lipid-lowering medication indicated" in note


def test_level_2b_near_level_3_threshold_uses_shared_decision_wording():
    patient = Patient(
        age=40,
        sex="male",
        ldl_c=158,
        apob=116,
        triglycerides=176,
        uacr=9,
        prevent_10y_ascvd=1.41,
        prevent_30y_ascvd=9.82,
        cac=None,
        cac_not_done=True,
    )
    result, classification, actions, diagnoses = _case(patient)
    note = render_note_for(patient)

    assert classification.level == "2B"
    assert classification.prevent_category == "LOW"
    assert result.prevent_30y_ascvd < 10
    assert patient.ldl_c < 160
    assert patient.apob < 120
    assert "Level: 2B - converging early risk signals." in note
    assert "PREVENT: ASCVD 10y 1.41% (Low); 30y 9.82%." in note
    assert "Clinician-patient risk discussion reasonable given near-threshold LDL/ApoB burden and 30-year trajectory" in actions
    assert "CAC reasonable if treatment decision remains uncertain" in actions
    assert "Lipid-lowering therapy is reasonable" not in actions
    assert "Aspirin: Not indicated" in note
    assert "subclinical coronary atherosclerosis" not in diagnoses.lower()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("prevent_30y_ascvd", 10.0),
        ("ldl_c", 160),
        ("apob", 120),
    ],
)
def test_near_level_3_boundary_crossings_escalate_to_level_3_minimum(field, value):
    patient = Patient(
        age=40,
        sex="male",
        ldl_c=158,
        apob=116,
        triglycerides=176,
        uacr=9,
        prevent_10y_ascvd=1.41,
        prevent_30y_ascvd=9.82,
        cac=None,
        cac_not_done=True,
    )
    setattr(patient, field, value)

    _result, classification, _actions, diagnoses = _case(patient)

    assert classification.level in {"3A", "3B"}
    assert "subclinical coronary atherosclerosis" not in diagnoses.lower()


def test_level_3b_atherogenic_30y_ldl_apob_uses_intensity_cac_wording():
    patient = Patient(
        age=42,
        sex="male",
        prevent_10y_ascvd=1.73,
        prevent_30y_ascvd=11.85,
        ldl_c=166,
        apob=121,
        non_hdl_c=202,
        triglycerides=182,
        cac=None,
        cac_not_done=True,
        diabetes=False,
        uacr=9,
    )
    result, classification, actions, diagnoses = _case(patient)
    note = render_note_for(patient)

    assert classification.level == "3B"
    assert classification.prevent_category == "LOW"
    assert "30-year PREVENT ASCVD 11.85%" in classification.drivers
    assert "LDL-C 160-189" in classification.drivers
    assert "ApoB >=120" in classification.drivers
    assert "triglycerides >=150" in classification.drivers
    assert "Level: 3B - actionable early CKM / atherogenic risk." in note
    assert "PREVENT: ASCVD 10y 1.73% (Low); 30y 11.85%." in note
    assert "Moderate-intensity statin therapy is reasonable to reduce cumulative atherogenic exposure" in actions
    assert "CAC may clarify plaque burden if treatment intensity remains uncertain" in actions
    assert "CAC reasonable for risk clarification if treatment decision remains uncertain" not in actions
    assert "Aspirin: Not indicated" in note
    assert "subclinical coronary atherosclerosis" not in diagnoses.lower()
    assert "severe hypercholesterolemia" not in diagnoses.lower()


def test_level_3b_intermediate_prevent_uacr_missing_prioritizes_uacr_and_specific_lipid_wording():
    patient = Patient(
        age=56,
        sex="male",
        prevent_10y_ascvd=5.41,
        prevent_30y_ascvd=22.55,
        bp_treated=True,
        a1c=5.9,
        triglycerides=185,
        apob=102,
        non_hdl_c=165,
        lp_a_value=80,
        lp_a_unit="nmol/L",
        egfr=76,
        uacr=None,
        cac=None,
        cac_not_done=True,
    )
    result, classification, actions, diagnoses = _case(patient)
    note = render_note_for(patient)
    recommendation_lines = [
        line
        for line in note.split("Recommendations:", 1)[1].splitlines()
        if line.strip() and line.lstrip()[0].isdigit()
    ]

    assert classification.level == "3B"
    assert classification.prevent_category == "INTERMEDIATE"
    assert "kidney G2; UACR not available" in note
    assert "UACR not available; obtain UACR" in note
    assert result.dominant_action == (
        "Moderate-intensity statin therapy is reasonable given borderline ASCVD risk with risk-enhancing factors."
    )
    assert recommendation_lines[:7] == [
        "1. Lipids: Discuss moderate-intensity statin; LDL-C <100, ApoB <90, non-HDL-C <130.",
        "2. Plaque: CAC may clarify risk.",
        "3. Kidney: UACR not available; obtain UACR.",
        "4. BP: Treat toward <130/80.",
        "5. Glycemia: Prediabetes prevention; A1c 5.9%.",
        "6. Aspirin: Not indicated.",
        "7. Additional information: UACR.",
    ]
    assert "CAC reasonable for risk clarification if treatment decision remains uncertain" not in actions
    assert "subclinical coronary atherosclerosis" not in diagnoses.lower()


def test_level_3b_emr_not_rendered_as_simple_low_or_borderline():
    patient = Patient(
        age=50,
        sex="male",
        uacr=34,
        egfr=76,
        a1c=6.1,
        bp_treated=True,
        prevent_10y_ascvd=3.7,
        prevent_30y_ascvd=18.8,
        cac=None,
        cac_not_done=True,
    )
    from renderers.emr_renderer import render_emr_note

    result = evaluate_patient(patient)
    note = render_emr_note(patient, result)

    assert "Level: 3B" in note
    assert "BORDERLINE." not in note
    assert "LOW." not in note
