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

    assert note.startswith("RISK CONTINUUM CKM\n\nHIGH.")
    assert "Impression:" not in note
    assert "Assessment:" in note
    assert "Assessment/coding:" not in note
    assert "Recommendations:" in note
    assert "Risk Summary:" not in note
    assert "Context:" not in note
    assert note.index("HIGH.") < note.index("Assessment:") < note.index("Recommendations:")
    assert "HIGH." in note
    assert "10-year ASCVD risk: 8.2%." in note
    assert "30-year ASCVD risk: 24.5%." in note
    assert "CKM stage 3 with kidney G3aA2; albuminuria not measured and CAC 350." in note
    assert "- Clinical ASCVD (ICD: I25.10)" in note
    assert "- Type 2 diabetes mellitus (ICD: E11.9)" in note

    lipid_line = "- High-intensity lipid-lowering therapy indicated."
    cac_line = "- CAC 350; no repeat CAC needed for current decision-making."
    aspirin_line = "- Aspirin only if bleeding risk is low after shared decision-making."
    assert lipid_line in note
    assert "Recheck lipids in 4-12 weeks" not in note
    assert cac_line in note
    assert aspirin_line in note
    assert "- Lipid therapy:" not in note
    assert "- Coronary calcium:" not in note
    assert "- Supporting actions:" not in note
    assert "Aspirin: Aspirin" not in note
    assert note.index(lipid_line) < note.index(aspirin_line)


def test_render_emr_note_marks_hcc_supported_diagnosis_subtly():
    patient = Patient(age=60, sex="male")
    result = RCCKMResult(
        diagnosis_candidates=[
            DiagnosisCandidate(
                name="Type 2 diabetes mellitus with diabetic chronic kidney disease",
                icd10_code="E11.22",
                status="data-derived",
                source="diabetes with eGFR <60",
                hcc_supported=True,
                hcc_label="HCC-supported",
            )
        ]
    )

    note = render_emr_note(patient, result)

    assert "HCC-supported" not in note
    assert "RAF" not in note
    assert "capture" not in note.lower()
    assert "reimbursement" not in note.lower()


def test_render_emr_note_uses_plaque_category_when_cac_missing():
    patient = Patient(age=60, sex="male")
    result = RCCKMResult(plaque_category=PlaqueCategory.SEVERE)

    note = render_emr_note(patient, result)

    assert "plaque SEVERE" in note


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
    assert note.count("- Treat BP toward goal <130/80.") == 1
    assert "No active domain changes" not in note


def test_demo_emr_note_prioritizes_composite_diagnoses_and_decisive_actions():
    from ui.report_layout import demo_patient, run_patient

    patient = demo_patient()
    result, _rss_total, _contributions = run_patient(patient)

    note = render_emr_note(patient, result)
    assessment = note.split("Assessment:", 1)[1].split("Recommendations:", 1)[0]

    assert "Severe subclinical coronary atherosclerosis / high CAC burden" in assessment
    assert "Type 2 diabetes mellitus with CKD G3aA2 and albuminuria" in assessment
    assert "CKD stage 3a ICD: N18.31" in assessment
    assert "- Chronic kidney disease, stage 3a" not in assessment
    assert "Elevated ApoB / atherogenic particle burden" not in assessment
    assert "Premature family history of ASCVD" not in assessment
    assert "Subclinical coronary atherosclerosis (ICD:" not in assessment
    assert "- Type 2 diabetes mellitus (ICD:" not in assessment
    assert "- Type 2 diabetes mellitus with albuminuria" not in assessment
    assert "- Chronic kidney disease (ICD:" not in assessment
    assert "- Albuminuria (ICD:" not in assessment
    assert "data-derived" not in assessment

    assert "High-intensity lipid-lowering therapy indicated." in note
    assert "premature family history" in note
    assert "Lipid-lowering therapy is reasonable." not in note
    assert "Confirm persistent albuminuria" in note
    assert "Optimize diabetes care." in note
    assert "Supporting actions:" not in note


def test_emr_note_omits_verbose_atherogenic_burden_sentence_for_demo():
    from ui.report_layout import demo_patient, run_patient

    patient = demo_patient()
    result, _rss_total, _contributions = run_patient(patient)
    note = render_emr_note(patient, result)

    assert "Atherogenic/metabolic burden:" not in note
    assert "- TG: 180 mg/dL." not in note
    assert "use non-HDL-C/ApoB for atherogenic burden when TG is elevated" not in note


def test_emr_note_is_materially_shorter_than_legacy_risk_summary_shape():
    from ui.report_layout import demo_patient, run_patient

    patient = demo_patient()
    result, _rss_total, _contributions = run_patient(patient)
    note = render_emr_note(patient, result)

    legacy_proxy = "\n".join(
        [
            "RISK CONTINUUM CKM - CLINICAL REPORT",
            "",
            "Risk Summary:",
            "- Level 5 - very high plaque burden",
            "- CKM stage: Stage 3 - Subclinical cardiovascular disease present.",
            "- PREVENT category: high 10-year risk",
            "- PREVENT 10-year atherosclerotic event risk: 10.16%",
            "- PREVENT 30-year atherosclerotic event risk: 30.65%",
            "- Plaque: CAC 350",
            "- Kidney: G3aA2",
            "- RSS: 74/100",
            "- TG: 180 mg/dL.",
            "- Atherogenic burden: ApoB 110 mg/dL; LDL-C 132 mg/dL; non-HDL-C 157 mg/dL.",
            "- Lp(a): 80 nmol/L.",
            "- Risk enhancer: premature family history of ASCVD.",
            "- PREVENT 10-year atherosclerotic event risk is high and supports treatment escalation.",
            "- Diabetes and CKD are present and increase cardiometabolic risk.",
            "- CAC 350 confirms severe plaque burden and high-risk targets.",
            "- Aspirin decision should include individualized bleeding-risk review.",
            "- UACR not available; obtain to complete kidney-risk assessment.",
            "",
            "Assessment:",
            "- Severe subclinical coronary atherosclerosis / high CAC burden (ICD: I25.10)",
            "- Type 2 diabetes mellitus with CKD G3aA2 and albuminuria (ICD: E11.22; CKD stage 3a ICD: N18.31)",
            "- Hypertriglyceridemia (ICD: E78.1)",
            "",
            "Recommendations:",
            "- High-intensity lipid-lowering therapy indicated; treat toward high-risk targets.",
            "- Recheck lipid profile 4-12 weeks after starting or intensifying therapy, then every 6-12 months.",
            "- CAC 350 already measured; no repeat CAC needed for current decision-making.",
            "- Aspirin may be considered only if bleeding risk is low after shared decision-making.",
            "- Optimize kidney-protective therapy.",
            "- Optimize diabetes care.",
        ]
    )

    assert len(note) <= len(legacy_proxy) * 0.7
    assert "Impression:" not in note
    assert "Risk Summary:" not in note


def test_emr_note_excludes_workflow_and_metadata_noise():
    from ui.report_layout import demo_patient, run_patient

    patient = demo_patient()
    result, _rss_total, _contributions = run_patient(patient)
    note = render_emr_note(patient, result)

    forbidden = [
        "Impression:",
        "HCC-supported",
        "Atherogenic/metabolic burden:",
        "Recheck lipid profile",
    ]
    for phrase in forbidden:
        assert phrase not in note

    lines = note.splitlines()
    assert lines[0] == "RISK CONTINUUM CKM"
    assert lines[2].startswith("Level 5 -")
