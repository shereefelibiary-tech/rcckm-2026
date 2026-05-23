from core.results import DiagnosisCandidate, RCCKMResult
from diagnosis_workflow import (
    apply_confirmations,
    augment_diagnoses_with_bmi_glp1,
    build_assessment_section,
    build_confirmed_code_exports,
    diagnosis_context_line,
    normalize_diagnosis_entries,
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
                True,
            )
        ]
    )

    rows = normalize_diagnosis_entries(result)

    assert rows == [
            {
                "dx_id": "Type 2 diabetes mellitus",
                "label": "Type 2 diabetes mellitus",
                "label_display": "Type 2 diabetes mellitus",
                "status": "confirmed_by_data",
                "icd10_suggested": ["E11.9"],
                "icd10_confirmed": ["E11.9"],
                "hcc_suggested": ["HCC"],
                "hcc_confirmed": ["HCC"],
                "source": "diabetes flag",
            }
        ]


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


def test_contextual_diagnosis_remains_review_suggested():
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
    assert len(review) == 1
    assert review[0]["status"] == "review_suggested"


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


def test_augment_diagnoses_with_bmi_glp1_adds_obesity_or_overweight():
    obesity = augment_diagnoses_with_bmi_glp1([], {"bmi": 31})
    overweight = augment_diagnoses_with_bmi_glp1([], {"bmi": 28, "a1c": 5.8})
    no_overweight = augment_diagnoses_with_bmi_glp1([], {"bmi": 28})

    assert any(row["dx_id"] == "dx_obesity" for row in obesity)
    assert any(row["dx_id"] == "dx_overweight" for row in overweight)
    assert no_overweight == []
