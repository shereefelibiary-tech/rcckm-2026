import re

from core.engine import evaluate_patient
from core.enums import RiskLevel
from core.patient import Patient
from core.results import RCCKMResult
from modules.actions.scaffold import (
    build_action_recommendation_lines,
    build_action_scaffold,
    build_action_instrument_panel,
    build_compact_action_detail_lines,
    build_compact_action_items,
)
from renderers.emr_renderer import render_emr_note
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


def test_cac_missing_intermediate_prevent_frames_cac_as_clarifier():
    patient = Patient(age=55, sex="male", cac=None, prevent_10y_ascvd=6.0)
    result = evaluate_patient(patient)

    sections = build_action_scaffold(patient, result)

    assert _section(sections, "Coronary calcium").line == (
        "CAC reasonable for risk clarification if treatment decision remains uncertain."
    )


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

    assert _section(sections, "Coronary calcium").line == (
        "Plaque burden unmeasured. CAC not routinely recommended at this age; consider only if results would change management."
    )
    assert "CAC - plaque burden clarification" not in all_clarifiers


def test_cac_missing_clear_treatment_indication_keeps_lipid_action_first():
    patient = Patient(age=55, sex="male", cac=None, prevent_10y_ascvd=12.0)
    result = evaluate_patient(patient)

    sections = build_action_scaffold(patient, result)

    assert sections[0].label == "Lipid therapy"
    assert sections[0].line == "Moderate-intensity statin therapy is generally favored for primary prevention."
    cac_section = next(section for section in sections if section.label == "Coronary calcium")
    assert cac_section.line == "CAC may clarify plaque burden if treatment intensity remains uncertain."


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
        "Aspirin not routine for primary prevention."
    )
    assert "Lipid-lowering therapy is reasonable" not in recommendations
    assert "Intensify lipid-lowering" in recommendations
    assert "ApoB <80" in recommendations
    assert "2. Plaque: CAC 145." in recommendations
    assert "CAC reasonable" not in recommendations
    assert "Subclinical coronary atherosclerosis" in note
    assert "Severe subclinical coronary atherosclerosis" not in note


def test_aspirin_default_not_indicated():
    patient = Patient(age=55, sex="male", cac=0)
    result = evaluate_patient(patient)

    assert _section(build_action_scaffold(patient, result), "Aspirin").line == (
        "Aspirin not indicated for routine primary prevention."
    )


def test_aspirin_consideration_only_for_rcckm_high_risk_context():
    patient = Patient(age=55, sex="male", cac=120)
    result = evaluate_patient(patient)

    assert _section(build_action_scaffold(patient, result), "Aspirin").line == (
        "Aspirin not routine for primary prevention."
    )


def test_age_70_aspirin_not_routine_primary_prevention():
    patient = Patient(age=72, sex="male", cac=350)
    result = evaluate_patient(patient)

    assert _section(build_action_scaffold(patient, result), "Aspirin").line == (
        "Aspirin not indicated for routine primary prevention."
    )


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
    aspirin_lead = "Aspirin not routine for primary prevention"
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
    assert "CAC / plaque" in html
    assert "Blood pressure" in html
    assert "Data to clarify" not in html
    assert lipid_lead in html
    assert lipid_detail in html
    assert aspirin_lead in html
    assert "Consider only if low bleeding risk and shared decision-making supports it." in html
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
    assert "High plaque burden; no repeat CAC needed." in html
    assert html.index("Lipid lowering") < html.index("CAC / plaque") < html.index(kidney_line)
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
        "CAC / plaque",
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
    assert next(item for item in panel if item.domain_id == "aspirin_antiplatelet").status == "Not routine for primary prevention"


def test_action_instrument_panel_groups_kidney_cac_and_aspirin_without_empty_clarifier():
    patient = Patient(age=55, sex="male", cac=350, diabetes=True, a1c=7.1, egfr=55, uacr=45, ldl_c=132, apob=110)
    result = evaluate_patient(patient)
    panel = {item.domain_id: item for item in build_action_instrument_panel(patient, result)}

    assert panel["lipid_lowering"].status == "High-intensity therapy indicated"
    assert "LDL-C" in panel["lipid_lowering"].detail
    assert panel["plaque_cac"].status == "CAC 350"
    assert panel["plaque_cac"].detail == ""
    assert panel["plaque_cac"].hover_detail == "High plaque burden; no repeat CAC needed."
    assert panel["kidney_protection"].status == "Optimize kidney protection"
    assert "UACR 45" in panel["kidney_protection"].detail
    assert "Consider SGLT2 for diabetic CKD" in panel["kidney_protection"].detail
    assert "per criteria" not in panel["kidney_protection"].detail
    assert "SGLT2 benefit is strongest" in panel["kidney_protection"].hover_detail
    assert "SGLT2" not in panel["blood_pressure"].status + panel["blood_pressure"].detail
    assert panel["blood_pressure"].status == "BP needed"
    assert panel["aspirin_antiplatelet"].status == "Aspirin not routine for primary prevention"
    assert "low bleeding risk" in panel["aspirin_antiplatelet"].hover_detail
    assert "data_to_clarify" not in panel


def test_action_instrument_panel_shows_decision_relevant_clarifiers():
    patient = Patient(age=55, sex="male", ldl_c=90, triglycerides=250, lp_a_value=20)
    result = evaluate_patient(patient)
    panel = {item.domain_id: item for item in build_action_instrument_panel(patient, result)}

    assert panel["data_to_clarify"].label == "Data to clarify"
    assert "ApoB" in panel["data_to_clarify"].detail


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
    assert "continue ACEi-ARB" in kidney_text
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
    assert panel["aspirin_antiplatelet"].status == "Antiplatelet therapy"
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
    assert lower_item.detail == "UACR 80; continue/optimize ACEi-ARB."
    assert "SGLT2" not in lower_item.status + lower_item.detail
    assert diabetic_item.status == "Optimize kidney protection"
    assert diabetic_item.detail == "UACR 80; continue ACEi-ARB. Consider SGLT2 for diabetic CKD."
    assert "SGLT2 benefit is strongest" in diabetic_item.hover_detail
    assert strong_item.status == "Add SGLT2 if no contraindication"
    assert strong_item.detail == "UACR 220; eGFR 55."
    assert "UACR >=200" in strong_item.hover_detail
    assert low_egfr_item.status == "Do not newly start SGLT2 routinely"
    assert "nephrology guidance" in low_egfr_item.detail
    for item in (lower_item, diabetic_item, strong_item, low_egfr_item):
        assert "per criteria" not in item.status + item.detail


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
    aspirin_line = "6. Aspirin: Not routine for primary prevention."
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
    assert "Aspirin not routine for primary prevention." in lines
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
    assert _section(sections, "Aspirin").line == "Aspirin not indicated for routine primary prevention."
    assert not any(section.label == "Coronary calcium" for section in sections)
    assert "- No diagnosis candidates generated." in note
    assert "1. Lipids: No lipid escalation." in recommendations
    assert "6. Aspirin: Not routine for primary prevention." in recommendations
    assert "CAC reasonable" not in recommendations
    assert "CAC not performed" not in recommendations
    assert "Plaque: unmeasured / CAC not performed" not in note
    assert "UACR not available" not in note
    assert "Check Lp(a)" not in recommendations
