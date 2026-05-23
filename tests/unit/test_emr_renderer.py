from core.enums import PlaqueCategory, RiskLevel
from core.patient import Patient
from core.results import DiagnosisCandidate, RCCKMResult
from renderers.emr_renderer import render_emr_note


def test_render_emr_note_outputs_plain_text_sections_in_order():
    patient = Patient(age=60, sex="male", cac=350)
    result = RCCKMResult(
        risk_level=RiskLevel.HIGH,
        prevent_10y_ascvd=8.2,
        prevent_30y_ascvd=24.5,
        kdigo_stage="G3aA2",
        ckm_stage={
            "stage": 3,
            "headline": "Subclinical cardiovascular disease present.",
            "drivers": ["CAC 350"],
        },
        rss_total=57,
        diagnosis_candidates=[
            DiagnosisCandidate(
                name="Type 2 diabetes mellitus",
                icd10_code="E11.9",
                status="data-derived",
            ),
            DiagnosisCandidate(
                name="Clinical ASCVD",
                icd10_code="I25.10",
                status="reported",
            ),
        ],
        dominant_action="Lipid-lowering therapy is reasonable.",
        recommendations=[
            "Lipid-lowering therapy is reasonable.",
            "Optimize kidney-protective therapy.",
        ],
    )

    note = render_emr_note(patient, result)

    expected_note = "\n".join(
        [
            "RISK CONTINUUM CKM — CLINICAL REPORT",
            "",
            "Risk Summary:",
            "- Risk level: HIGH",
            "- CKM stage: Stage 3 - Subclinical cardiovascular disease present.",
            "- PREVENT 10-year ASCVD risk: 8.2%",
            "- PREVENT 30-year ASCVD risk: 24.5%",
            "- Plaque: CAC 350",
            "- Kidney: G3aA2",
            "- RSS: 57/100",
            "",
            "Assessment:",
            "- Clinical ASCVD (ICD: I25.10)",
            "- Type 2 diabetes mellitus (ICD: E11.9)",
            "",
            "Recommendations:",
            "- Lipid-lowering therapy is reasonable.",
            "- Optimize kidney-protective therapy.",
        ]
    )
    assert expected_note
    assert "Risk Summary:" in note
    assert "- Risk level: HIGH" in note
    assert "- PREVENT 10-year ASCVD risk: 8.2%" in note
    assert "- PREVENT 30-year ASCVD risk: 24.5%" in note
    assert "- Plaque: CAC 350" in note
    assert "- Kidney: G3aA2" in note
    assert "- RSS: 57/100" in note
    assert "- Clinical ASCVD (ICD: I25.10)" in note
    assert "- Type 2 diabetes mellitus (ICD: E11.9)" in note
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


def test_render_emr_note_uses_plaque_category_when_cac_missing():
    patient = Patient(age=60, sex="male")
    result = RCCKMResult(plaque_category=PlaqueCategory.SEVERE)

    note = render_emr_note(patient, result)

    assert "- Plaque: SEVERE" in note


def test_render_emr_note_avoids_duplicate_recommendations_and_generic_action():
    patient = Patient(age=60, sex="male")
    result = RCCKMResult(
        dominant_action="Treatment is reasonable.",
        recommendations=[
            "Treatment is reasonable.",
            "Optimize BP to <130/80.",
            "Optimize BP to <130/80.",
        ],
    )

    note = render_emr_note(patient, result)

    assert "Treatment is reasonable." not in note
    assert "Supporting actions:" not in note
    assert note.count("- Treat blood pressure toward individualized goal.") == 1


def test_demo_emr_note_prioritizes_composite_diagnoses_and_decisive_actions():
    from ui.report_layout import demo_patient, run_patient

    patient = demo_patient()
    result, _rss_total, _contributions = run_patient(patient)

    note = render_emr_note(patient, result)
    assessment = note.split("Assessment:", 1)[1].split("Recommendations:", 1)[0]

    assert "Severe subclinical coronary atherosclerosis / high CAC burden" in assessment
    assert "Type 2 diabetes mellitus with CKD G3aA2 and albuminuria" in assessment
    assert "Chronic kidney disease, stage 3a" in assessment
    assert "Elevated ApoB / atherogenic particle burden" in assessment
    assert "Subclinical coronary atherosclerosis (ICD:" not in assessment
    assert "- Type 2 diabetes mellitus (ICD:" not in assessment
    assert "- Type 2 diabetes mellitus with albuminuria" not in assessment
    assert "- Chronic kidney disease (ICD:" not in assessment
    assert "- Albuminuria (ICD:" not in assessment
    assert "data-derived" not in assessment

    assert "High-intensity lipid-lowering therapy indicated; treat toward high-risk targets." in note
    assert "Lipid-lowering therapy is reasonable." not in note
    assert "Optimize glycemic therapy." in note
    assert "Supporting actions:" not in note
