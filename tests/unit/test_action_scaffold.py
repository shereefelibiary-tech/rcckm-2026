import re

from core.engine import evaluate_patient
from core.diagnosis_workflow import prepare_diagnosis_display_entries
from core.enums import RiskLevel
from core.patient import Patient
from core.results import RCCKMResult
from modules.actions.scaffold import (
    action_domain_clinician_text,
    action_domain_patient_text,
    build_action_recommendation_lines,
    build_action_scaffold,
    build_action_instrument_panel,
    build_compact_action_detail_lines,
    build_compact_action_items,
    build_domain_actions,
    render_action_domain_text,
)
from modules.risk_enhancers.reproductive import reproductive_history_summary
from renderers.emr_renderer import render_emr_note
from renderers.patient_roadmap import render_patient_roadmap_text
from renderers.render_modes import RenderMode
from ui.report_layout import _build_action_html


def _section(sections, label):
    for section in sections:
        if section.label == label:
            return section
    raise AssertionError(f"Missing action section: {label}")


def _visible_action_readout_text(html):
    readout = html.split('<div class="action-readout">', 1)[1].split("</details>", 1)[0]
    readout = readout.split("<details", 1)[0]
    readout = re.sub(r"<[^>]+>", " ", readout)
    return " ".join(readout.split())


def _domain(panel, domain_id):
    return next(item for item in panel if item.domain_id == domain_id)


def test_cac_missing_intermediate_prevent_frames_cac_as_clarifier():
    patient = Patient(age=55, sex="male", cac=None, prevent_10y_ascvd=6.0)
    result = evaluate_patient(patient)

    sections = build_action_scaffold(patient, result)

    assert _section(sections, "Coronary calcium").line == "CAC may clarify risk."


def test_cac_unmeasured_age_40_or_older_with_meaningful_signal_clarifies_risk():
    cases = [
        Patient(age=42, sex="female", apob=100),
        Patient(age=42, sex="female", ldl_c=130),
        Patient(age=42, sex="female", triglycerides=175),
        Patient(age=42, sex="female", non_hdl_c=130),
        Patient(age=42, sex="female", family_history_premature_ascvd=True),
        Patient(age=42, sex="female", hscrp=2.0),
        Patient(age=42, sex="female", a1c=5.7),
        Patient(age=42, sex="female", bmi=30),
        Patient(age=42, sex="female", osa=True),
        Patient(age=42, sex="female", masld=True),
        Patient(age=42, sex="female", smoker=True),
        Patient(age=42, sex="female", diabetes=True),
        Patient(age=42, sex="female", uacr=30),
        Patient(age=42, sex="female", rheumatoid_arthritis=True),
        Patient(age=42, sex="female", prevent_10y_ascvd=5.0),
    ]

    for patient in cases:
        result = evaluate_patient(patient)
        plaque = _domain(build_action_instrument_panel(patient, result), "plaque_cac")
        assert plaque.status == "CAC may clarify risk"
        assert "treatment intensity" not in plaque.action_card_line.lower()
        assert "statin intensity" not in plaque.action_card_line.lower()


def test_cac_unmeasured_pristine_cases_can_say_not_needed():
    pristine_age_40 = Patient(age=42, sex="female", prevent_10y_ascvd=0.3)
    pristine_under_40 = Patient(age=35, sex="female", prevent_10y_ascvd=0.2)

    for patient in (pristine_age_40, pristine_under_40):
        result = evaluate_patient(patient)
        plaque = _domain(build_action_instrument_panel(patient, result), "plaque_cac")
        assert plaque.status == "CAC not needed"


def test_cac_unmeasured_under_40_with_major_signal_can_clarify_risk():
    patient = Patient(age=35, sex="female", ldl_c=170, family_history_premature_ascvd=True)
    result = evaluate_patient(patient)

    plaque = _domain(build_action_instrument_panel(patient, result), "plaque_cac")

    assert plaque.status == "CAC may clarify risk"


def test_cac_unmeasured_clustered_early_risk_case_clarifies_risk():
    patient = Patient(
        age=42,
        sex="female",
        ldl_c=136,
        apob=112,
        triglycerides=178,
        hscrp=2.8,
        a1c=6.1,
        bmi=33.4,
        osa=True,
        masld=True,
        family_history_premature_ascvd=True,
    )
    result = evaluate_patient(patient)

    plaque = _domain(build_action_instrument_panel(patient, result), "plaque_cac")

    assert plaque.status == "CAC may clarify risk"
    assert "CAC not needed" not in plaque.action_card_line
    assert "treatment intensity" not in plaque.action_card_line.lower()


def test_below_cac_age_gate_soft_note_without_routine_cac_clarifier():
    patient = Patient(
        age=39,
        sex="male",
        cac=None,
        prevent_10y_ascvd=6.0,
        family_history_premature_ascvd=True,
    )
    result = evaluate_patient(patient)

    sections = build_action_scaffold(patient, result)
    all_clarifiers = " ".join(item for section in sections for item in section.items)

    assert _section(sections, "Coronary calcium").line == "CAC may clarify risk."
    assert "CAC - plaque burden clarification" not in all_clarifiers


def test_cac_missing_clear_treatment_indication_keeps_lipid_action_first():
    patient = Patient(age=55, sex="male", cac=None, prevent_10y_ascvd=12.0)
    result = evaluate_patient(patient)

    sections = build_action_scaffold(patient, result)

    assert sections[0].label == "Lipid therapy"
    assert sections[0].line == "Moderate-intensity statin therapy is generally favored for primary prevention."
    cac_section = next(section for section in sections if section.label == "Coronary calcium")
    assert cac_section.line == "CAC may clarify risk."


def test_cac_zero_does_not_recommend_cac():
    patient = Patient(age=55, sex="male", cac=0, prevent_10y_ascvd=6.0)
    result = evaluate_patient(patient)

    sections = build_action_scaffold(patient, result)

    assert _section(sections, "Coronary calcium").line == (
        "CAC 0 measured; no calcified plaque detected."
    )
    assert "CAC - plaque burden clarification" not in " ".join(
        item for section in sections for item in section.items
    )


def test_cac_350_uses_severe_plaque_line_without_cac_recommendation():
    patient = Patient(age=55, sex="male", cac=350)
    result = evaluate_patient(patient)

    sections = build_action_scaffold(patient, result)

    assert _section(sections, "Lipid therapy").line == (
        "High-intensity lipid-lowering therapy indicated; treat toward high-risk targets."
    )
    assert _section(sections, "Coronary calcium").line == (
        "CAC 350 already measured; no repeat CAC needed for current decision-making."
    )
    assert "CAC - plaque burden clarification" not in " ".join(
        item for section in sections for item in section.items
    )


def test_cac_1200_uses_extensive_plaque_target_line():
    patient = Patient(age=55, sex="male", cac=1200)
    result = evaluate_patient(patient)

    assert _section(build_action_scaffold(patient, result), "Coronary calcium").line == (
        "CAC 1200 already measured; no repeat CAC needed for current decision-making."
    )


def test_cac_100_299_on_treatment_above_target_uses_intensification_wording():
    patient = Patient(
        age=61,
        sex="female",
        cac=145,
        tc=218,
        ldl_c=124,
        hdl_c=56,
        non_hdl_c=162,
        triglycerides=190,
        apob=112,
        lp_a_value=238,
        lp_a_unit="nmol/L",
        lipid_lowering=True,
        statin_intensity="moderate",
        statin_intolerance=True,
    )
    result = evaluate_patient(patient)
    sections = build_action_scaffold(patient, result)
    note = render_emr_note(patient, result)
    recommendations = _recommendations_block(note)
    target = result.targets[0]

    assert result.risk_level in {RiskLevel.INTERMEDIATE, RiskLevel.HIGH}
    assert target.ldl_c_target == 70
    assert target.non_hdl_c_target == 100
    assert target.apob_target == 80
    assert result.dominant_action == (
        "Intensify lipid-lowering therapy; treat toward LDL-C <70 and non-HDL-C <100."
    )
    assert _section(sections, "Lipid therapy").line == result.dominant_action
    assert _section(sections, "Statin intolerance").line == (
        "Given prior high-intensity statin intolerance, consider maximally tolerated statin strategy and nonstatin intensification."
    )
    assert _section(sections, "Coronary calcium").line == (
        "CAC 145 already measured; no repeat CAC needed for current decision-making."
    )
    assert _section(sections, "Aspirin").line == (
        "Aspirin may be considered only if bleeding risk is low."
    )
    assert "Lipid-lowering therapy is reasonable" not in recommendations
    assert "Intensify lipid-lowering" in recommendations
    assert "ApoB <80" in recommendations
    assert "2. Plaque: CAC 145." in recommendations
    assert "6. Aspirin: Consider only if bleeding risk is low; CAC 145." in recommendations
    assert "CAC reasonable" not in recommendations
    assert "Subclinical coronary atherosclerosis" in note
    assert "Severe subclinical coronary atherosclerosis" not in note


def test_aspirin_default_not_indicated():
    patient = Patient(age=55, sex="male", cac=0)
    result = evaluate_patient(patient)

    assert _section(build_action_scaffold(patient, result), "Aspirin").line == "Not indicated."


def test_aspirin_consideration_only_for_rcckm_high_risk_context():
    patient = Patient(age=55, sex="male", cac=120)
    result = evaluate_patient(patient)

    assert _section(build_action_scaffold(patient, result), "Aspirin").line == (
        "Aspirin may be considered only if bleeding risk is low."
    )


def test_age_70_aspirin_not_routine_primary_prevention():
    patient = Patient(age=72, sex="male", cac=350)
    result = evaluate_patient(patient)

    assert _section(build_action_scaffold(patient, result), "Aspirin").line == "Not indicated."


def test_cac_guided_primary_prevention_aspirin_branches_align_surfaces():
    cases = [
        (Patient(age=54, sex="male", cac=0), "Not indicated.", "Not indicated", "Not indicated."),
        (Patient(age=54, sex="male", cac=50), "Not indicated.", "Not indicated", "Not indicated."),
        (Patient(age=54, sex="male", cac=184), "Aspirin may be considered only if bleeding risk is low.", "Consider only if bleeding risk is low; CAC 184", "Discuss only if bleeding risk is low."),
        (Patient(age=58, sex="male", cac=350), "Aspirin may be considered if bleeding risk is low; plaque burden is high.", "Consider only if bleeding risk is low; CAC 350", "May be considered if bleeding risk is low."),
        (Patient(age=75, sex="male", cac=350), "Not indicated.", "Not indicated", "Not indicated."),
        (Patient(age=58, sex="male", cac=350, aspirin_bleeding_risk_high=True), "Avoid routine primary-prevention aspirin.", "Avoid routine primary-prevention aspirin", "Avoid routine aspirin."),
    ]

    for patient, scaffold_line, emr_fragment, roadmap_fragment in cases:
        result = evaluate_patient(patient)
        assert _section(build_action_scaffold(patient, result), "Aspirin").line == scaffold_line
        assert f"6. Aspirin: {emr_fragment}." in render_emr_note(patient, result)
        assert f"6. Aspirin: {roadmap_fragment}" in render_patient_roadmap_text(patient, result)


def test_no_lipid_change_wording_is_medication_state_aware_across_surfaces():
    untreated = Patient(
        age=34,
        sex="female",
        ldl_c=88,
        apob=99,
        lp_a_value=400,
        lp_a_unit="nmol/L",
        lipid_lowering=False,
        prevent_10y_ascvd=0.2,
        prevent_30y_ascvd=2.0,
    )
    untreated_result = evaluate_patient(untreated)
    untreated_lipids = next(
        item for item in build_action_instrument_panel(untreated, untreated_result)
        if item.domain_id == "lipid_lowering"
    )
    untreated_emr = render_emr_note(untreated, untreated_result)
    untreated_roadmap = render_patient_roadmap_text(untreated, untreated_result)

    assert untreated_lipids.status == "No lipid-lowering medication indicated"
    assert "1. Lipids: No lipid-lowering medication indicated." in untreated_emr
    assert "1. Cholesterol: No medication indicated." in untreated_roadmap
    assert "No cholesterol medicine change" not in untreated_roadmap
    assert "Continue current lipid treatment" not in untreated_roadmap
    assert "No lipid escalation" not in untreated_roadmap

    treated = Patient(
        age=55,
        sex="male",
        ldl_c=75,
        apob=70,
        lipid_lowering=True,
        statin_intensity="moderate",
        prevent_10y_ascvd=1.0,
        prevent_30y_ascvd=4.0,
    )
    treated_result = evaluate_patient(treated)
    treated_lipids = next(
        item for item in build_action_instrument_panel(treated, treated_result)
        if item.domain_id == "lipid_lowering"
    )
    treated_emr = render_emr_note(treated, treated_result)
    treated_roadmap = render_patient_roadmap_text(treated, treated_result)

    assert treated_lipids.status == "Continue current lipid treatment"
    assert "1. Lipids: Continue current lipid treatment." in treated_emr
    assert "1. Cholesterol: Continue current lipid treatment." in treated_roadmap


def test_cac_positive_lipid_wording_is_medication_state_aware():
    untreated = Patient(
        age=44,
        sex="female",
        cac=38,
        ldl_c=117,
        apob=92,
        lipid_lowering=False,
    )
    untreated_result = evaluate_patient(untreated)
    untreated_lipid = next(
        item for item in build_action_instrument_panel(untreated, untreated_result)
        if item.domain_id == "lipid_lowering"
    )
    untreated_action = untreated_lipid.action_card_line
    untreated_emr = render_emr_note(untreated, untreated_result)
    untreated_roadmap = render_patient_roadmap_text(untreated, untreated_result)

    assert untreated_result.level_classification["level"] == "4"
    assert "Lipid-lowering therapy indicated" in untreated_action
    assert "intensify" not in untreated_action.lower()
    assert "1. Lipids: Lipid-lowering therapy indicated; LDL-C <100, ApoB <90, non-HDL-C <130." in untreated_emr
    assert "Intensify" not in untreated_emr
    assert "1. Cholesterol: Discuss starting cholesterol-lowering therapy." in untreated_roadmap
    assert "stronger" not in untreated_roadmap.lower()
    assert "continue current lipid treatment" not in untreated_roadmap.lower()
    assert "escalation" not in untreated_roadmap.lower()

    treated_above = Patient(
        age=44,
        sex="female",
        cac=38,
        ldl_c=117,
        apob=92,
        lipid_lowering=True,
        statin_intensity="low",
    )
    treated_above_result = evaluate_patient(treated_above)
    treated_above_lipid = next(
        item for item in build_action_instrument_panel(treated_above, treated_above_result)
        if item.domain_id == "lipid_lowering"
    )

    assert "Intensify lipid-lowering" in treated_above_lipid.action_card_line
    assert "1. Lipids: Intensify lipid-lowering; LDL-C <100, ApoB <90, non-HDL-C <130." in render_emr_note(treated_above, treated_above_result)
    assert "1. Cholesterol: Discuss stronger cholesterol-lowering therapy." in render_patient_roadmap_text(treated_above, treated_above_result)

    treated_at_target = Patient(
        age=44,
        sex="female",
        cac=38,
        ldl_c=82,
        apob=70,
        lipid_lowering=True,
        statin_intensity="low",
    )
    treated_at_target_result = evaluate_patient(treated_at_target)
    treated_at_target_lipid = next(
        item for item in build_action_instrument_panel(treated_at_target, treated_at_target_result)
        if item.domain_id == "lipid_lowering"
    )

    assert "Continue current lipid treatment" in treated_at_target_lipid.action_card_line
    assert "1. Cholesterol: Continue current lipid treatment." in render_patient_roadmap_text(treated_at_target, treated_at_target_result)


def test_clinical_ascvd_uses_secondary_prevention_antiplatelet_wording():
    patient = Patient(age=55, sex="male", clinical_ascvd=True, cac=None)
    result = evaluate_patient(patient)

    assert _section(build_action_scaffold(patient, result), "Aspirin").line == (
        "Antiplatelet therapy is indicated for secondary prevention if clinically appropriate and no contraindication is present."
    )


def test_clinical_ascvd_with_cac_zero_uses_secondary_prevention_not_derisking():
    patient = Patient(
        age=55,
        sex="male",
        clinical_ascvd=True,
        clinical_ascvd_context="prior NSTEMI and PCI/stent",
        cac=0,
        tc=205,
        ldl_c=132,
        hdl_c=48,
        sbp=132,
        diabetes=False,
        smoker=False,
    )
    result = evaluate_patient(patient)

    sections = build_action_scaffold(patient, result)
    note = render_emr_note(patient, result)
    diagnosis_text = " ".join(candidate.name for candidate in result.diagnosis_candidates)

    assert result.risk_level == RiskLevel.VERY_HIGH
    assert result.ckm_stage["stage"] == 4
    assert _section(sections, "Lipid therapy").line == (
        "Intensify secondary-prevention lipid-lowering therapy; treat toward very-high-risk ASCVD targets."
    )
    assert _section(sections, "Coronary calcium").line == (
        "CAC 0 is discordant/historical and should not be used to de-risk established ASCVD."
    )
    assert _section(sections, "Aspirin").line == (
        "Antiplatelet therapy is indicated for secondary prevention if clinically appropriate and no contraindication is present."
    )
    assert "Level: 5 - clinical ASCVD / secondary prevention" in note
    assert "PREVENT 10-year ASCVD risk" not in note
    assert "2. Plaque: CAC 0." in note
    assert "Clinical ASCVD / coronary artery disease with prior NSTEMI and PCI/stent" in diagnosis_text
    assert "Subclinical coronary atherosclerosis" not in diagnosis_text


def test_primary_prevention_cac_zero_still_means_no_calcified_plaque_detected():
    patient = Patient(age=55, sex="male", clinical_ascvd=False, cac=0)
    result = evaluate_patient(patient)

    assert _section(build_action_scaffold(patient, result), "Coronary calcium").line == (
        "CAC 0 measured; no calcified plaque detected."
    )


def test_action_html_renders_structured_sections_without_loose_duplicate_list():
    patient = Patient(age=55, sex="male", cac=350, diabetes=True, a1c=7.1, egfr=55, uacr=45, ldl_c=132, apob=110)
    result = evaluate_patient(patient)

    html = _build_action_html(result, patient)

    lipid_lead = "High-intensity therapy indicated"
    lipid_detail = "LDL-C"
    aspirin_lead = "Consider if bleeding risk is low"
    kidney_line = "Kidney protection"
    kidney_detail = "UACR 45"
    glycemia_line = "Optimize diabetes care"

    assert "Lipid therapy:" not in html
    assert "Coronary calcium:" not in html
    assert "Supporting actions:" not in html
    assert "Aspirin: Aspirin" not in html
    assert "Lipid therapy: Lipid" not in html
    assert html.count('class="action-domain ') == 6
    assert "action-number" in html
    assert '<div class="action-number" aria-hidden="true">1</div>' in html
    assert '<div class="action-number" aria-hidden="true">6</div>' in html
    assert "<ol" not in html
    assert "<li>High-intensity lipid-lowering therapy indicated" not in html
    assert "action-readout" in html
    assert "action-grid" not in html
    assert "action-domain-label" in html
    assert "action-status" in html
    assert "action-detail" in html
    assert "text-transform:uppercase" not in html
    assert "action-indicator" not in html
    assert "grid-template-columns:32px 150px minmax(0,1fr)" in html
    assert "Lipid lowering" in html
    assert "Plaque" in html
    assert "Blood pressure" in html
    assert "Data to clarify" not in html
    assert lipid_lead in html
    assert lipid_detail in html
    assert aspirin_lead in html
    assert "CAC &gt;=100 may identify patients more likely to benefit from aspirin when bleeding risk is low." in html
    assert "Primary-prevention aspirin is selective." not in html
    assert kidney_line in html
    assert kidney_detail in html
    assert glycemia_line in html
    assert "A1c 7.1%; goal &lt;7.0." in html
    assert "suggested goal" not in html
    assert "when safe" not in html
    assert "if appropriate" not in html
    assert "High-intensity lipid-lowering therapy indicated." not in html
    assert "Recheck lipid profile 4-12 weeks" not in html
    visible_action_text = _visible_action_readout_text(html)
    assert "CAC 350" in visible_action_text
    assert "CAC 350 already measured" not in visible_action_text
    assert "already measured" not in visible_action_text
    assert "High plaque burden; no repeat CAC needed." not in visible_action_text
    assert "Treat BP toward <130/80 if tolerated" not in visible_action_text
    assert "if tolerated" not in visible_action_text
    assert "per criteria" not in visible_action_text
    assert "when safe" not in visible_action_text
    assert "suggested goal" not in visible_action_text
    assert "No kidney-risk signal" not in visible_action_text
    assert "eGFR/UACR available" not in visible_action_text
    assert "Do not start routine aspirin" not in visible_action_text
    assert "Use only if it would change lipid-treatment intensity" not in visible_action_text
    assert "High plaque burden; no repeat CAC needed." in html
    assert html.index("Lipid lowering") < html.index("Plaque") < html.index(kidney_line)
    assert "Show details" in html
    assert "\n            <div" not in html


def test_action_instrument_panel_has_fixed_domain_order_without_empty_clarifier_slot():
    patient = Patient(age=55, sex="male", cac=0, sbp=118, dbp=72, tc=180, hdl_c=55)
    result = evaluate_patient(patient)

    panel = build_action_instrument_panel(patient, result)

    assert [item.domain_id for item in panel] == [
        "lipid_lowering",
        "plaque_cac",
        "kidney_protection",
        "blood_pressure",
        "glycemia_metabolic",
        "aspirin_antiplatelet",
    ]
    assert [item.label for item in panel] == [
        "Lipid lowering",
        "Plaque",
        "Kidney protection",
        "Blood pressure",
        "Glycemia / metabolic",
        "Aspirin / antiplatelet",
    ]
    assert all(item.status for item in panel)
    assert all("None" not in item.status + item.detail for item in panel)
    assert all("if tolerated" not in item.status + item.detail for item in panel)
    assert all("No urgent clarifiers" not in item.status + item.detail for item in panel)
    assert all("reviewed." not in item.status + item.detail for item in panel)
    assert next(item for item in panel if item.domain_id == "blood_pressure").status == "At goal"
    assert next(item for item in panel if item.domain_id == "glycemia_metabolic").status == "A1c needed"
    kidney = next(item for item in panel if item.domain_id == "kidney_protection")
    aspirin = next(item for item in panel if item.domain_id == "aspirin_antiplatelet")
    assert kidney.status == "Kidney context not available"
    assert kidney.detail == ""
    assert aspirin.status == "Not indicated"
    assert aspirin.detail == ""


def test_action_card_suppresses_low_value_cac_kidney_and_aspirin_details():
    patient = Patient(age=55, sex="male", prevent_10y_ascvd=6.0, egfr=80, uacr=10)
    result = evaluate_patient(patient)
    panel = {item.domain_id: item for item in build_action_instrument_panel(patient, result)}

    assert panel["plaque_cac"].status == "CAC may clarify risk"
    assert panel["plaque_cac"].detail == ""
    assert panel["plaque_cac"].hover_detail == ""
    assert panel["kidney_protection"].status == "Stable"
    assert panel["kidney_protection"].detail == ""
    assert panel["aspirin_antiplatelet"].status == "Not indicated"
    assert panel["aspirin_antiplatelet"].detail == ""
    assert panel["aspirin_antiplatelet"].hover_detail == ""

    visible_action_text = _visible_action_readout_text(_build_action_html(result, patient))
    assert "Use only if it would change lipid-treatment intensity" not in visible_action_text
    assert "No kidney-risk signal" not in visible_action_text
    assert "eGFR/UACR available" not in visible_action_text
    assert "Do not start routine aspirin" not in visible_action_text


def test_action_instrument_panel_groups_kidney_cac_and_aspirin_without_empty_clarifier():
    patient = Patient(age=55, sex="male", cac=350, diabetes=True, a1c=7.1, egfr=55, uacr=45, ldl_c=132, apob=110)
    result = evaluate_patient(patient)
    panel = {item.domain_id: item for item in build_action_instrument_panel(patient, result)}

    assert panel["lipid_lowering"].status == "High-intensity therapy indicated"
    assert "LDL-C" in panel["lipid_lowering"].detail
    assert panel["plaque_cac"].status == "Very high burden (CAC 350)"
    assert panel["plaque_cac"].detail == ""
    assert panel["plaque_cac"].hover_detail == "High plaque burden; no repeat CAC needed."
    assert panel["kidney_protection"].status == "Optimize kidney protection"
    assert "UACR 45" in panel["kidney_protection"].detail
    assert "Consider SGLT2 for diabetic CKD" in panel["kidney_protection"].detail
    assert "per criteria" not in panel["kidney_protection"].detail
    assert "SGLT2 benefit is strongest" in panel["kidney_protection"].hover_detail
    assert "SGLT2" not in panel["blood_pressure"].status + panel["blood_pressure"].detail
    assert panel["blood_pressure"].status == "BP needed"
    assert panel["aspirin_antiplatelet"].status == "Consider if bleeding risk is low"
    assert panel["aspirin_antiplatelet"].detail == "High plaque burden."
    assert panel["aspirin_antiplatelet"].hover_detail == (
        "CAC >=100 may identify patients more likely to benefit from aspirin when bleeding risk is low."
    )
    assert "data_to_clarify" not in panel


def test_action_domain_render_modes_separate_clinician_and_patient_language():
    patient = Patient(age=58, sex="male", cac=350)
    result = evaluate_patient(patient)
    plaque_panel = next(item for item in build_action_instrument_panel(patient, result) if item.domain_id == "plaque_cac")
    plaque_domain = next(item for item in build_domain_actions(patient, result) if item.domain_id == "plaque_cac")

    assert action_domain_clinician_text(plaque_panel) == "Plaque: Very high burden (CAC 350)."
    assert action_domain_patient_text(plaque_domain) == "Very high burden (CAC 350)."
    assert render_action_domain_text(plaque_panel, RenderMode.CLINICIAN) == "Plaque: Very high burden (CAC 350)."
    assert render_action_domain_text(plaque_domain, RenderMode.PATIENT) == "Very high burden (CAC 350)."


def test_plaque_action_uses_burden_language_for_low_positive_cac():
    patient = Patient(age=58, sex="female", cac=12)
    result = evaluate_patient(patient)
    plaque_panel = next(item for item in build_action_instrument_panel(patient, result) if item.domain_id == "plaque_cac")

    assert plaque_panel.label == "Plaque"
    assert plaque_panel.status == "Present (CAC 12)"


def test_action_instrument_panel_shows_decision_relevant_clarifiers():
    patient = Patient(age=55, sex="male", ldl_c=90, triglycerides=250, lp_a_value=20)
    result = evaluate_patient(patient)
    panel = {item.domain_id: item for item in build_action_instrument_panel(patient, result)}

    assert panel["data_to_clarify"].label == "Additional information that may help clarify risk"
    assert "ApoB" in panel["data_to_clarify"].status


def test_missing_data_priority_layer_surfaces_needed_a1c_uacr_and_lpa():
    patient = Patient(
        age=43,
        sex="female",
        ldl_c=146,
        apob=122,
        sbp=124,
        dbp=76,
        bmi=28.1,
        egfr=96,
        a1c=None,
        uacr=None,
        lp_a_value=None,
        cac=None,
        cac_not_done=True,
    )
    result = evaluate_patient(patient)
    panel = {item.domain_id: item for item in build_action_instrument_panel(patient, result)}

    assert panel["kidney_protection"].status in {"Obtain UACR", "UACR needed"}
    assert "Stable" not in panel["kidney_protection"].action_card_line
    assert panel["glycemia_metabolic"].status == "A1c needed"
    assert panel["plaque_cac"].status == "CAC may clarify risk"
    assert panel["data_to_clarify"].status == "A1c, Lp(a), UACR"
    assert "A1c" in panel["data_to_clarify"].detail_lines
    assert any("Lp(a)" in line for line in panel["data_to_clarify"].detail_lines)
    assert any("UACR" in line for line in panel["data_to_clarify"].detail_lines)


def test_action_instrument_panel_keeps_kidney_and_bp_messages_separate():
    patient = Patient(
        age=62,
        sex="male",
        diabetes=True,
        ace_arb=True,
        egfr=55,
        uacr=45,
        sbp=132,
        dbp=82,
    )
    result = evaluate_patient(patient)
    panel = {item.domain_id: item for item in build_action_instrument_panel(patient, result)}

    kidney_text = panel["kidney_protection"].status + " " + panel["kidney_protection"].detail
    bp_text = panel["blood_pressure"].status + " " + panel["blood_pressure"].detail

    assert panel["kidney_protection"].status == "Optimize kidney protection"
    assert "UACR 45" in kidney_text
    assert "ACEi/ARB active" in kidney_text
    assert "Consider SGLT2 for diabetic CKD" in kidney_text
    assert "BP" not in kidney_text
    assert "<130/80" not in kidney_text
    assert panel["blood_pressure"].status == "Treat toward <130/80"
    assert panel["blood_pressure"].detail == "Current 132/82."
    assert "BP goals should be individualized" in panel["blood_pressure"].hover_detail


def test_action_instrument_panel_secondary_prevention_antiplatelet_slot():
    patient = Patient(age=62, sex="male", clinical_ascvd=True, clinical_ascvd_context="prior MI")
    result = evaluate_patient(patient)
    panel = {item.domain_id: item for item in build_action_instrument_panel(patient, result)}

    assert panel["lipid_lowering"].status == "Secondary-prevention lipid therapy"
    assert panel["aspirin_antiplatelet"].status == "Indicated"
    assert panel["aspirin_antiplatelet"].hover_detail == "Clinical ASCVD."
    assert "primary prevention" not in panel["aspirin_antiplatelet"].status.lower()


def test_action_kidney_sglt2_branches_are_specific_and_hovered():
    lower_a2 = Patient(age=64, sex="male", egfr=55, uacr=80, diabetes=False, ace_arb=True)
    diabetic_ckd = Patient(age=64, sex="male", egfr=55, uacr=80, diabetes=True, ace_arb=True)
    strong = Patient(age=64, sex="male", egfr=55, uacr=220, diabetes=False, ace_arb=True)
    low_egfr = Patient(age=64, sex="male", egfr=18, uacr=350, diabetes=True, ace_arb=True)

    lower_item = {item.domain_id: item for item in build_action_instrument_panel(lower_a2, evaluate_patient(lower_a2))}[
        "kidney_protection"
    ]
    diabetic_item = {
        item.domain_id: item for item in build_action_instrument_panel(diabetic_ckd, evaluate_patient(diabetic_ckd))
    }["kidney_protection"]
    strong_item = {item.domain_id: item for item in build_action_instrument_panel(strong, evaluate_patient(strong))}[
        "kidney_protection"
    ]
    low_egfr_item = {
        item.domain_id: item for item in build_action_instrument_panel(low_egfr, evaluate_patient(low_egfr))
    }["kidney_protection"]

    assert lower_item.status == "Monitor albuminuria"
    assert lower_item.detail == "UACR 80; ACEi/ARB active."
    assert "SGLT2" not in lower_item.status + lower_item.detail
    assert diabetic_item.status == "Optimize kidney protection"
    assert diabetic_item.detail == "UACR 80; ACEi/ARB active. Consider SGLT2 for diabetic CKD."
    assert "SGLT2 benefit is strongest" in diabetic_item.hover_detail
    assert strong_item.status == "Add SGLT2 if no contraindication"
    assert strong_item.detail == "UACR 220; eGFR 55."
    assert "UACR >=200" in strong_item.hover_detail
    assert low_egfr_item.status == "Do not newly start SGLT2 routinely"
    assert "nephrology guidance" in low_egfr_item.detail
    for item in (lower_item, diabetic_item, strong_item, low_egfr_item):
        assert "per criteria" not in item.status + item.detail


def test_severe_ckd_diabetes_actions_are_active_med_aware():
    patient = Patient(
        age=61,
        sex="female",
        tc=210,
        hdl_c=43,
        ldl_c=None,
        triglycerides=478,
        apob=80,
        diabetes=True,
        a1c=11.8,
        egfr=16,
        uacr=2417,
        sglt2=True,
        ace_arb=True,
        lipid_lowering=True,
        statin_intensity="high",
        aspirin=True,
        sbp=142,
        dbp=84,
        prevent_10y_ascvd=29.03,
    )
    result = evaluate_patient(patient)
    panel = {item.domain_id: item for item in build_action_instrument_panel(patient, result)}
    note = render_emr_note(patient, result)
    diagnosis_text = "\n".join(candidate.name for candidate in result.diagnosis_candidates)

    assert result.kdigo_stage == "G4A3"
    assert result.level_classification["label"] == "Level 3B - advanced CKM / severe kidney-risk pattern"
    assert result.ckm_stage["stage"] == 3
    assert "N18.4" in note
    assert "clinical ascvd" not in diagnosis_text.lower()

    assert panel["kidney_protection"].status == "Continue kidney-protective therapy"
    assert panel["kidney_protection"].detail == "eGFR 16; UACR 2417; ACEi/ARB + SGLT2 active."
    assert "Do not newly start" not in panel["kidney_protection"].status + panel["kidney_protection"].detail
    assert "nephrology" in panel["kidney_protection"].hover_detail

    assert panel["aspirin_antiplatelet"].status == "Aspirin active; confirm indication"
    assert "Do not start" not in panel["aspirin_antiplatelet"].status + panel["aspirin_antiplatelet"].detail
    assert "Primary-prevention benefit uncertain" in panel["aspirin_antiplatelet"].detail

    assert "LDL-C unavailable due to TG 478" in panel["lipid_lowering"].detail
    assert "ApoB 80; target <80" in panel["lipid_lowering"].detail
    assert "CKM/Kidney/Plaque: CKM 3; kidney G4A3; CAC not measured." in note
    assert "1. Lipids: High-intensity lipid-lowering active; ApoB 80, target <80" in note
    assert "LDL-C unavailable due to TG" in note
    assert "3. Kidney: eGFR 16; UACR 2417; ACEi/ARB + SGLT2 active." in note
    assert "6. Aspirin: Active; confirm indication." in note
    assert "no repeat CAC" not in note.lower()
    assert "secondary-prevention" not in note.lower()


def test_35f_diabetes_albuminuria_actions_active_sglt2_and_no_duplicate_diagnosis():
    patient = Patient(
        age=35,
        sex="female",
        tc=236,
        hdl_c=42,
        ldl_c=125,
        triglycerides=265,
        apob=88,
        lp_a_value=22.4,
        diabetes=True,
        a1c=8.2,
        egfr=95,
        uacr=362,
        sglt2=True,
        ace_arb=True,
        sbp=166,
        dbp=100,
        pcos_or_irregular_menses=True,
        cac=None,
        cac_not_done=True,
    )
    result = evaluate_patient(patient)
    panel = {item.domain_id: item for item in build_action_instrument_panel(patient, result)}
    note = render_emr_note(patient, result)
    diagnoses = prepare_diagnosis_display_entries(result)
    labels = [entry.get("label_display") or entry.get("label") for entry in diagnoses]

    assert panel["kidney_protection"].status == "Continue kidney-protective therapy"
    assert panel["kidney_protection"].detail == "UACR 362; ACEi/ARB + SGLT2 active."
    assert "Add SGLT2" not in panel["kidney_protection"].status + panel["kidney_protection"].detail
    assert "hsCRP" not in " ".join(item.status + " " + item.detail for item in panel.values())
    assert "hsCRP" not in note

    assert any("Type 2 diabetes mellitus with albuminuria" in str(label) for label in labels)
    assert "Type 2 diabetes mellitus" not in labels
    assert "PCOS / irregular menses" == reproductive_history_summary(patient)


def test_compact_action_items_group_priorities_and_preserve_details():
    patient = Patient(age=55, sex="male", cac=350, diabetes=True, a1c=7.1, egfr=55, uacr=45)
    result = evaluate_patient(patient)

    items = build_compact_action_items(patient, result)
    details = build_compact_action_detail_lines(patient, result)
    titles = [item.title for item in items]
    subtitles = [item.subtitle for item in items]

    assert len(items) <= 5
    assert titles[:3] == [
        "Intensify lipid-lowering",
        "Protect kidneys",
        "Optimize glycemia",
    ]
    assert "Monitor UACR; optimize ACEi-ARB." in subtitles
    assert "Aspirin: only if low bleeding risk" not in titles
    assert all("Recheck lipid profile 4-12 weeks" not in item.title + item.subtitle for item in items)
    assert all("CAC 350 already measured" not in item.title + item.subtitle for item in items)
    assert "CAC 350 already measured; no repeat CAC needed for current decision-making." not in details
    assert "Monitor lipids after therapy change." in details


def test_compact_action_omits_routine_primary_prevention_aspirin():
    patient = Patient(age=55, sex="male", cac=0)
    result = evaluate_patient(patient)

    text = " ".join(item.title + " " + item.subtitle for item in build_compact_action_items(patient, result))

    assert "Aspirin not indicated for routine primary prevention" not in text
    assert "Aspirin safety" not in text


def test_compact_action_keeps_secondary_prevention_antiplatelet_visible():
    patient = Patient(age=62, sex="male", clinical_ascvd=True, clinical_ascvd_context="prior MI")
    result = evaluate_patient(patient)

    items = build_compact_action_items(patient, result)

    assert any(item.title == "Antiplatelet therapy" for item in items)
    assert any("no contraindication" in item.subtitle for item in items)


def test_emr_recommendations_use_action_scaffold():
    patient = Patient(age=55, sex="male", cac=350, diabetes=True, a1c=7.1, egfr=55, uacr=45)
    result = evaluate_patient(patient)

    note = render_emr_note(patient, result)

    lipid_line = "1. Lipids: High-intensity lipid-lowering therapy indicated; LDL-C <70, non-HDL-C <100."
    cac_line = "2. Plaque: CAC 350."
    aspirin_line = "6. Aspirin: Consider only if bleeding risk is low; CAC 350."
    assert lipid_line in note
    assert "Recheck lipids in 4-12 weeks" not in note
    assert cac_line in note
    assert aspirin_line in note
    assert "- Lipid therapy:" not in note
    assert "- Coronary calcium:" not in note
    assert "- Supporting actions:" not in note
    assert "Aspirin: Aspirin" not in note
    assert note.index(lipid_line) < note.index(aspirin_line)


def test_flat_recommendation_lines_keep_order_without_visible_scaffold_labels():
    patient = Patient(age=55, sex="male", cac=350, diabetes=True, a1c=7.1, egfr=55, uacr=45)
    result = evaluate_patient(patient)

    lines = build_action_recommendation_lines(patient, result)

    assert lines[:4] == [
        "High-intensity lipid-lowering therapy indicated; treat toward high-risk targets.",
        "Recheck lipid profile 4-12 weeks after starting or intensifying therapy, then every 6-12 months.",
        "Confirm persistent albuminuria with repeat UACR if not already confirmed; optimize kidney-protective therapy.",
        "Optimize diabetes care.",
    ]
    assert any("optimize kidney-protective therapy" in line for line in lines)
    assert "Optimize diabetes care." in lines
    assert "CAC 350 already measured; no repeat CAC needed for current decision-making." in lines
    assert "Aspirin may be considered if bleeding risk is low; plaque burden is high." in lines
    assert not any(line.startswith(("Lipid therapy:", "Coronary calcium:", "Aspirin:", "Supporting actions:")) for line in lines)
    assert "lipid" not in lines[2].lower()


def test_emr_very_severe_hypertriglyceridemia_uses_pancreatitis_pathway():
    patient = Patient(
        age=55,
        sex="male",
        tc=286,
        hdl_c=32,
        triglycerides=1040,
        ldl_c=None,
        apob=138,
        diabetes=True,
        a1c=8.2,
        lipid_lowering=False,
    )
    result = evaluate_patient(patient)
    note = render_emr_note(patient, result)

    assert patient.non_hdl_c == 254
    assert "Atherogenic/metabolic burden:" not in note
    assert "Severe hypertriglyceridemia" in note
    assert "Lower triglycerides urgently" in note
    assert "1. Lipids:" in note
    assert "5. Glycemia: Optimize diabetes care; A1c 8.2%; goal <7.0." in note


def test_no_action_result_can_still_build_clear_scaffold():
    patient = Patient(age=55, sex="male", cac=None)
    result = RCCKMResult(prevent_risk_category=RiskLevel.LOW)

    sections = build_action_scaffold(patient, result)

    assert _section(sections, "Lipid therapy").line == "Lipid lowering: no escalation based on current LDL-C/ApoB and ASCVD risk profile."
    assert _section(sections, "Lifestyle").line == "Continue lifestyle-based prevention."
    assert _section(sections, "Coronary calcium").line == "Plaque burden unmeasured."


def _recommendations_block(note):
    return note.split("Recommendations:", 1)[1]


def test_low_risk_complete_data_below_cac_age_threshold_stays_calm_without_cac_recommendation():
    patient = Patient(
        age=36,
        sex="female",
        sbp=108,
        dbp=68,
        bp_treated=False,
        tc=158,
        ldl_c=82,
        hdl_c=62,
        triglycerides=70,
        non_hdl_c=96,
        apob=68,
        lp_a_value=18,
        lp_a_unit="nmol/L",
        a1c=5.2,
        egfr=105,
        uacr=5,
        cac=None,
        cac_not_done=True,
        clinical_ascvd=False,
        smoker=False,
        diabetes=False,
        prevent_10y_ascvd=1.0,
    )
    result = evaluate_patient(patient)
    sections = build_action_scaffold(patient, result)
    note = render_emr_note(patient, result)
    recommendations = _recommendations_block(note)

    assert result.prevent_risk_category == RiskLevel.LOW
    assert _section(sections, "Lipid therapy").line == "Lipid lowering: no escalation based on current LDL-C/ApoB and ASCVD risk profile."
    assert _section(sections, "Lifestyle").line == "Continue lifestyle-based prevention."
    assert _section(sections, "Aspirin").line == "Not indicated."
    assert _section(sections, "Coronary calcium").line == "CAC not needed."
    assert "- No diagnosis candidates generated." in note
    assert "1. Lipids: No lipid-lowering medication indicated." in recommendations
    assert "6. Aspirin: Not indicated." in recommendations
    assert "CAC reasonable" not in recommendations
    assert "CAC not performed" not in recommendations
    assert "Plaque: unmeasured / CAC not performed" not in note
    assert "UACR not available" not in note
    assert "Check Lp(a)" not in recommendations
