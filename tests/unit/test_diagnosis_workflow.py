from core.engine import evaluate_patient
from core.patient import Patient
from core.results import DiagnosisCandidate, RCCKMResult
from core.diagnosis_workflow import (
    DIAGNOSIS_DISPLAY_PRIORITY,
    apply_confirmations,
    apply_diagnosis_review_overrides,
    augment_diagnoses_with_bmi_glp1,
    build_assessment_section,
    build_confirmed_code_exports,
    diagnosis_context_line,
    normalize_diagnosis_entries,
    prepare_diagnosis_display_entries,
    prioritize_linked_diagnoses,
    split_diagnoses,
)


def test_normalize_diagnosis_entries_supports_current_result_candidates():
    result = RCCKMResult(
        diagnosis_candidates=[
            DiagnosisCandidate(
                "Type 2 diabetes mellitus",
                "E11.9",
                "data-derived",
                "diabetes flag",
                False,
            )
        ]
    )

    rows = normalize_diagnosis_entries(result)

    assert len(rows) == 1
    assert rows[0]["dx_id"] == "Type 2 diabetes mellitus"
    assert rows[0]["label"] == "Type 2 diabetes mellitus"
    assert rows[0]["diagnosis"] == "Type 2 diabetes mellitus"
    assert rows[0]["status"] == "confirmed_by_data"
    assert rows[0]["icd10_suggested"] == ["E11.9"]
    assert rows[0]["icd10_confirmed"] == ["E11.9"]
    assert rows[0]["hcc_suggested"] == []
    assert rows[0]["hcc_confirmed"] == []
    assert rows[0]["hcc_supported"] is False
    assert rows[0]["hcc_label"] is None
    assert rows[0]["source"] == "diabetes flag"


def test_apply_confirmations_promotes_codes_and_split_lists():
    rows = normalize_diagnosis_entries(
        {
            "diagnosisSynthesis": {
                "diagnoses": [
                    {
                        "dx_id": "dx_dm",
                        "label": "Type 2 diabetes mellitus",
                        "status": "suspected",
                        "icd10_suggested": ["E11.9"],
                        "hcc_suggested": ["HCC 19"],
                    }
                ]
            }
        }
    )

    rows = apply_confirmations(rows, {"dx_dm"})
    confirmed, suspected = split_diagnoses(rows)

    assert len(confirmed) == 1
    assert suspected == []
    assert confirmed[0]["icd10_confirmed"] == ["E11.9"]
    assert confirmed[0]["hcc_confirmed"] == ["HCC 19"]


def test_hcc_supported_metadata_normalizes_to_subtle_badge_label():
    result = RCCKMResult(
        diagnosis_candidates=[
            DiagnosisCandidate(
                name="Type 2 diabetes mellitus with diabetic chronic kidney disease",
                icd10_code="E11.22",
                status="data-derived",
                source="diabetes with eGFR <60",
                hcc_supported=True,
                hcc_label="HCC-supported",
                confidence="data-supported",
                review_status="review_suggested",
            )
        ]
    )

    rows = prepare_diagnosis_display_entries(result)

    assert rows[0]["hcc_suggested"] == ["HCC-supported"]
    assert rows[0]["hcc_supported"] is True
    assert rows[0]["confidence"] == "data-supported"
    assert rows[0]["review_status"] == "review_suggested"


def test_family_history_context_is_not_diagnosis_workflow_item():
    rows = normalize_diagnosis_entries(
        {
            "diagnosisSynthesis": {
                "diagnoses": [
                    {
                        "dx_id": "fhx",
                        "label": "Premature family history of ASCVD",
                        "status": "data-derived",
                    }
                ]
            }
        }
    )

    confirmed, review = split_diagnoses(rows)

    assert confirmed == []
    assert review == []
    assert rows == []


def test_build_confirmed_code_exports_and_assessment_section():
    confirmed = [
        {
            "label_display": "Type 2 diabetes mellitus",
            "icd10_confirmed": ["E11.9"],
            "hcc_confirmed": ["HCC 19"],
        }
    ]
    suspected = [{"label_display": "Albuminuria", "icd10_suggested": ["R80.9"]}]

    assert build_confirmed_code_exports(confirmed) == {
        "codes": {"icd10_confirmed": ["E11.9"], "hcc_confirmed": ["HCC 19"]}
    }
    section = build_assessment_section(confirmed, suspected, include_icd_confirmed=True)

    assert "Assessment:" in section
    assert "Type 2 diabetes mellitus (ICD: E11.9)" in section
    assert "Albuminuria" in section


def test_diagnosis_context_line_uses_relevant_evidence():
    row = {
        "dx_id": "dx_ckd",
        "label_display": "Chronic kidney disease, stage 3a",
        "ev": [
            {"key": "egfr", "value": 55, "unit": "mL/min"},
            {"key": "uacr", "value": 45, "unit": "mg/g"},
            {"key": "bmi", "value": 31},
        ],
    }

    assert diagnosis_context_line(row) == "eGFR 55 mL/min; UACR 45 mg/g"


def test_prioritize_linked_diagnoses_suppresses_fragments():
    rows = normalize_diagnosis_entries(
        {
            "diagnosisSynthesis": {
                "diagnoses": [
                    {"dx_id": "dm", "label": "Type 2 diabetes mellitus"},
                    {
                        "dx_id": "dm_ckd",
                        "label": "Type 2 diabetes mellitus with diabetic chronic kidney disease",
                    },
                    {"dx_id": "ckd", "label": "Chronic kidney disease"},
                    {"dx_id": "ckd3a", "label": "Chronic kidney disease, stage 3a"},
                    {"dx_id": "alb", "label": "Albuminuria"},
                ]
            }
        }
    )

    visible = prioritize_linked_diagnoses(rows)
    names = [row["label_display"] for row in visible]

    assert "Type 2 diabetes mellitus with diabetic chronic kidney disease" in names
    assert "Chronic kidney disease, stage 3a" in names
    assert "Type 2 diabetes mellitus" not in names
    assert "Chronic kidney disease" not in names
    assert "Albuminuria" not in names


def test_diagnosis_display_priority_is_module_level_source():
    assert DIAGNOSIS_DISPLAY_PRIORITY["clinical ascvd"] < DIAGNOSIS_DISPLAY_PRIORITY["albuminuria"]
    assert DIAGNOSIS_DISPLAY_PRIORITY["type 2 diabetes mellitus with diabetic chronic kidney disease"] < (
        DIAGNOSIS_DISPLAY_PRIORITY["type 2 diabetes mellitus"]
    )


def test_composite_diabetes_ckd_albuminuria_suppresses_standalone_fragments_but_keeps_ckd_stage():
    rows = normalize_diagnosis_entries(
        {
            "diagnosisSynthesis": {
                "diagnoses": [
                    {"dx_id": "dm", "label": "Type 2 diabetes mellitus", "icd10_suggested": ["E11.9"]},
                    {
                        "dx_id": "dm_ckd",
                        "label": "Type 2 diabetes mellitus with diabetic chronic kidney disease",
                        "icd10_suggested": ["E11.22"],
                    },
                    {"dx_id": "ckd3a", "label": "Chronic kidney disease, stage 3a", "icd10_suggested": ["N18.31"]},
                    {"dx_id": "alb", "label": "Albuminuria", "icd10_suggested": ["R80.9"]},
                ]
            }
        }
    )

    visible = prioritize_linked_diagnoses(rows)
    names = [row["label_display"] for row in visible]

    assert names == [
        "Type 2 diabetes mellitus with diabetic chronic kidney disease",
        "Chronic kidney disease, stage 3a",
    ]


def test_severe_cac_diagnosis_does_not_suppress_unrelated_metabolic_diagnoses():
    rows = normalize_diagnosis_entries(
        {
            "diagnosisSynthesis": {
                "diagnoses": [
                    {"dx_id": "cac", "label": "Subclinical coronary atherosclerosis"},
                    {"dx_id": "severe_cac", "label": "Severe subclinical coronary atherosclerosis"},
                    {"dx_id": "predm", "label": "Prediabetes"},
                    {"dx_id": "tg", "label": "Hypertriglyceridemia"},
                ]
            }
        }
    )

    names = [row["label_display"] for row in prioritize_linked_diagnoses(rows)]

    assert "Severe subclinical coronary atherosclerosis" in names
    assert "Subclinical coronary atherosclerosis" not in names
    assert "Prediabetes" in names
    assert "Hypertriglyceridemia" in names


def test_review_overrides_accept_reject_and_keep_review_state_without_exporting_unaccepted_codes():
    rows = normalize_diagnosis_entries(
        {
            "diagnosisSynthesis": {
                "diagnoses": [
                    {
                        "dx_id": "dm",
                        "label": "Type 2 diabetes mellitus",
                        "status": "review_suggested",
                        "icd10_suggested": ["E11.9"],
                        "hcc_suggested": ["HCC 19"],
                    },
                    {
                        "dx_id": "alb",
                        "label": "Albuminuria",
                        "status": "confirmed",
                        "icd10_suggested": ["R80.9"],
                    },
                    {
                        "dx_id": "ckd",
                        "label": "Chronic kidney disease, stage 3a",
                        "status": "confirmed",
                        "icd10_suggested": ["N18.31"],
                        "hcc_suggested": ["HCC-supported"],
                    },
                ]
            }
        }
    )

    reviewed = apply_diagnosis_review_overrides(
        rows,
        accepted_ids={"dm"},
        suppressed_ids={"alb"},
        review_ids={"ckd"},
        include_suppressed=True,
    )
    by_id = {row["dx_id"]: row for row in reviewed}

    assert by_id["dm"]["status"] == "clinician_confirmed"
    assert by_id["dm"]["icd10_confirmed"] == ["E11.9"]
    assert by_id["dm"]["hcc_confirmed"] == ["HCC 19"]
    assert by_id["alb"]["status"] == "manually_suppressed"
    assert by_id["alb"]["icd10_confirmed"] == []
    assert by_id["ckd"]["status"] == "review_suggested"
    assert by_id["ckd"]["icd10_confirmed"] == []
    assert by_id["ckd"]["hcc_supported"] is True

    confirmed, review = split_diagnoses(reviewed)
    assert [row["dx_id"] for row in confirmed] == ["dm"]
    assert [row["dx_id"] for row in review] == ["ckd"]
    assert build_confirmed_code_exports(confirmed) == {
        "codes": {"icd10_confirmed": ["E11.9"], "hcc_confirmed": ["HCC 19"]}
    }


def test_augment_diagnoses_with_bmi_glp1_adds_obesity_or_overweight():
    obesity = augment_diagnoses_with_bmi_glp1([], {"bmi": 31})
    overweight = augment_diagnoses_with_bmi_glp1([], {"bmi": 28, "a1c": 5.8})
    no_overweight = augment_diagnoses_with_bmi_glp1([], {"bmi": 28})

    assert any(row["dx_id"] == "dx_obesity" for row in obesity)
    assert any(row["dx_id"] == "dx_overweight" for row in overweight)
    assert no_overweight == []


def test_normalize_diagnosis_entries_combines_obesity_and_bmi_z_code():
    result = RCCKMResult(
        diagnosis_candidates=[
            DiagnosisCandidate(
                name="Obesity",
                icd10_code="E66.9",
                status="data-derived",
                source="BMI >=30 kg/m²",
            ),
            DiagnosisCandidate(
                name="Adult BMI 33.0-33.9",
                icd10_code="Z68.33",
                status="data-derived",
                source="BMI 33.0-33.9 kg/m²",
            ),
        ]
    )

    rows = normalize_diagnosis_entries(result)
    labels = [row["label_display"] for row in rows]

    assert labels == ["Obesity, BMI 33.0-33.9"]
    assert rows[0]["icd10_confirmed"] == ["E66.9", "Z68.33"]
    assert "Obesity" not in labels
    assert "Adult BMI 33.0-33.9" not in labels


def test_evaluate_patient_exposes_normalized_obesity_bmi_entries_for_renderers():
    cases = [
        (33.4, "Obesity, BMI 33.0-33.9", ["E66.9", "Z68.33"], "Adult BMI 33.0-33.9"),
        (36.2, "Obesity, BMI 36.0-36.9", ["E66.9", "Z68.36"], "Adult BMI 36.0-36.9"),
    ]

    for bmi, combined_label, codes, standalone_bmi_label in cases:
        result = evaluate_patient(Patient(age=42, sex="female", bmi=bmi))

        labels = [row["label_display"] for row in result.diagnosis_entries]

        assert combined_label in labels
        assert standalone_bmi_label not in labels
        assert "Obesity" not in labels
        row = next(row for row in result.diagnosis_entries if row["label_display"] == combined_label)
        assert row["icd10_confirmed"] == codes
        assert prepare_diagnosis_display_entries(result) == result.diagnosis_entries


def test_normalize_diagnosis_entries_keeps_bmi_z_code_without_obesity():
    result = RCCKMResult(
        diagnosis_candidates=[
            DiagnosisCandidate(
                name="Adult BMI 33.0-33.9",
                icd10_code="Z68.33",
                status="data-derived",
                source="BMI 33.0-33.9 kg/m²",
            ),
        ]
    )

    rows = normalize_diagnosis_entries(result)

    assert [row["label_display"] for row in rows] == ["Adult BMI 33.0-33.9"]
    assert rows[0]["icd10_confirmed"] == ["Z68.33"]


def test_augment_diagnoses_with_bmi_glp1_overweight_gate_rejects_unrelated_fields():
    unrelated = augment_diagnoses_with_bmi_glp1(
        [],
        {
            "bmi": 28,
            "family_history_premature_ascvd": True,
            "cac": 350,
            "lp_a_value": 180,
        },
    )
    metabolic = augment_diagnoses_with_bmi_glp1([], {"bmi": 28, "triglycerides": 180})
    diabetes = augment_diagnoses_with_bmi_glp1([], {"bmi": 28, "diabetes": True})

    assert unrelated == []
    assert any(row["dx_id"] == "dx_overweight" for row in metabolic)
    assert any(row["dx_id"] == "dx_overweight" for row in diabetes)
