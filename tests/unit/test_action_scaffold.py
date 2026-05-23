from core.engine import evaluate_patient
from core.enums import RiskLevel
from core.patient import Patient
from core.results import RCCKMResult
from modules.actions.scaffold import build_action_recommendation_lines, build_action_scaffold
from renderers.emr_renderer import render_emr_note
from ui.report_layout import _build_action_html


def _section(sections, label):
    for section in sections:
        if section.label == label:
            return section
    raise AssertionError(f"Missing action section: {label}")


def test_cac_missing_intermediate_prevent_frames_cac_as_clarifier():
    patient = Patient(age=55, sex="male", cac=None, prevent_10y_ascvd=6.0)
    result = evaluate_patient(patient)

    sections = build_action_scaffold(patient, result)

    assert _section(sections, "Coronary calcium").line == (
        "Plaque burden unmeasured. CAC reasonable if treatment decision or intensity remains uncertain."
    )
    assert "CAC - plaque burden clarification" in _section(sections, "Clarifiers").items


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
        "Plaque burden unmeasured. CAC below usual age threshold; consider only if result would change management."
    )
    assert "CAC - plaque burden clarification" not in all_clarifiers


def test_cac_missing_clear_treatment_indication_keeps_lipid_action_first():
    patient = Patient(age=55, sex="male", cac=None, prevent_10y_ascvd=12.0)
    result = evaluate_patient(patient)

    sections = build_action_scaffold(patient, result)

    assert sections[0].label == "Lipid therapy"
    assert sections[0].line == "Lipid-lowering therapy is indicated; treat toward high-risk targets."
    assert sections[1].label == "Coronary calcium"
    assert sections[1].line.endswith(
        "CAC reasonable if treatment decision or intensity remains uncertain."
    )


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
        "Aspirin may be considered if bleeding risk is low after shared decision-making."
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
        "Antiplatelet therapy indicated for secondary prevention if clinically appropriate."
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
        "Secondary-prevention lipid-lowering therapy indicated; treat toward ASCVD targets."
    )
    assert _section(sections, "Coronary calcium").line == (
        "CAC 0 is discordant/historical and should not be used to de-risk established ASCVD."
    )
    assert _section(sections, "Aspirin").line == (
        "Antiplatelet therapy indicated for secondary prevention if clinically appropriate."
    )
    assert "PREVENT: not used for treatment decisions in established ASCVD." in note
    assert "PREVENT 10-year ASCVD risk" not in note
    assert "CAC 0 does not de-risk secondary prevention" in note
    assert "Clinical ASCVD / coronary artery disease with prior NSTEMI and PCI/stent" in diagnosis_text
    assert "Subclinical coronary atherosclerosis" not in diagnosis_text


def test_primary_prevention_cac_zero_still_means_no_calcified_plaque_detected():
    patient = Patient(age=55, sex="male", clinical_ascvd=False, cac=0)
    result = evaluate_patient(patient)

    assert _section(build_action_scaffold(patient, result), "Coronary calcium").line == (
        "CAC 0 measured; no calcified plaque detected."
    )


def test_action_html_renders_structured_sections_without_loose_duplicate_list():
    patient = Patient(age=55, sex="male", cac=350, diabetes=True, a1c=7.1, egfr=55, uacr=45)
    result = evaluate_patient(patient)

    html = _build_action_html(result, patient)

    lipid_lead = "High-intensity lipid-lowering therapy indicated."
    lipid_detail = "Treat toward high-risk targets."
    cac_lead = "CAC 350 already measured."
    cac_detail = "No repeat CAC needed for current decision-making."
    aspirin_lead = "Aspirin may be considered only if bleeding risk is low."
    aspirin_detail = "Use shared decision-making."
    kidney_line = "Optimize kidney-protective therapy."
    glycemia_line = "Optimize glycemic therapy."

    assert "Lipid therapy:" not in html
    assert "Coronary calcium:" not in html
    assert "Aspirin:" not in html
    assert "Supporting actions:" not in html
    assert "Aspirin: Aspirin" not in html
    assert "Lipid therapy: Lipid" not in html
    assert "action-number" in html
    assert "action-lead" in html
    assert "action-detail" in html
    assert lipid_lead in html
    assert lipid_detail in html
    assert cac_lead in html
    assert cac_detail in html
    assert aspirin_lead in html
    assert aspirin_detail in html
    assert kidney_line in html
    assert glycemia_line in html
    assert html.index(lipid_lead) < html.index(cac_lead) < html.index(aspirin_lead)
    assert "CAC 350 already measured; no repeat CAC needed" not in html
    assert "\n            <div" not in html


def test_emr_recommendations_use_action_scaffold():
    patient = Patient(age=55, sex="male", cac=350, diabetes=True, a1c=7.1, egfr=55, uacr=45)
    result = evaluate_patient(patient)

    note = render_emr_note(patient, result)

    lipid_line = "- High-intensity lipid-lowering therapy indicated; treat toward high-risk targets."
    cac_line = "- CAC 350 already measured; no repeat CAC needed for current decision-making."
    aspirin_line = "- Aspirin may be considered if bleeding risk is low after shared decision-making."
    assert lipid_line in note
    assert cac_line in note
    assert aspirin_line in note
    assert "- Lipid therapy:" not in note
    assert "- Coronary calcium:" not in note
    assert "- Supporting actions:" not in note
    assert "Aspirin: Aspirin" not in note
    assert note.index(lipid_line) < note.index(cac_line) < note.index(aspirin_line)


def test_flat_recommendation_lines_keep_order_without_visible_scaffold_labels():
    patient = Patient(age=55, sex="male", cac=350, diabetes=True, a1c=7.1, egfr=55, uacr=45)
    result = evaluate_patient(patient)

    lines = build_action_recommendation_lines(patient, result)

    assert lines[:3] == [
        "High-intensity lipid-lowering therapy indicated; treat toward high-risk targets.",
        "CAC 350 already measured; no repeat CAC needed for current decision-making.",
        "Aspirin may be considered if bleeding risk is low after shared decision-making.",
    ]
    assert "Optimize kidney-protective therapy." in lines
    assert "Optimize glycemic therapy." in lines
    assert not any(line.startswith(("Lipid therapy:", "Coronary calcium:", "Aspirin:", "Supporting actions:")) for line in lines)
    assert "lipid" not in lines[1].lower()


def test_no_action_result_can_still_build_clear_scaffold():
    patient = Patient(age=55, sex="male", cac=None)
    result = RCCKMResult(prevent_risk_category=RiskLevel.LOW)

    sections = build_action_scaffold(patient, result)

    assert _section(sections, "Lipid therapy").line == "No medication escalation today."
    assert _section(sections, "Coronary calcium").line == "Plaque burden unmeasured."
