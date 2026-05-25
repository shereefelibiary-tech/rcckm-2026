from core.diagnosis_workflow import normalize_diagnosis_entries, prepare_diagnosis_display_entries
from core.engine import evaluate_patient
from core.patient import Patient
from ui.diagnosis_confirm_panel import _candidate_html


def _row_for(rows, text):
    return next(
        row
        for row in rows
        if text in row["label_display"] or text in row.get("diagnosis", "")
    )


def test_e1122_assessment_candidate_displays_hcc_supported_badge():
    result = evaluate_patient(Patient(age=60, sex="male", diabetes=True, egfr=55))

    rows = prepare_diagnosis_display_entries(result)
    row = _row_for(rows, "Type 2 diabetes mellitus with diabetic chronic kidney disease")
    html = _candidate_html(row)

    assert row["icd10_suggested"] == ["E11.22"]
    assert row["hcc_supported"] is True
    assert row["hcc_suggested"] == ["HCC-supported"]
    assert "HCC-supported" in html
    assert "capture" not in html.lower()
    assert "reimbursement" not in html.lower()


def test_ckd_stage_3a_assessment_candidate_displays_hcc_supported_badge():
    result = evaluate_patient(Patient(age=60, sex="male", egfr=55))

    rows = prepare_diagnosis_display_entries(result)
    row = _row_for(rows, "Chronic kidney disease, stage 3a")
    html = _candidate_html(row)

    assert row["icd10_suggested"] == ["N18.31"]
    assert row["hcc_supported"] is True
    assert row["hcc_suggested"] == ["HCC-supported"]
    assert "HCC-supported" in html


def test_non_hcc_prevention_diagnoses_do_not_display_hcc_badges():
    result = evaluate_patient(
        Patient(
            age=60,
            sex="male",
            a1c=5.8,
            triglycerides=160,
            apob=120,
        )
    )

    rows = prepare_diagnosis_display_entries(result)
    for label in ("Prediabetes", "Hypertriglyceridemia", "Elevated ApoB"):
        row = _row_for(rows, label)
        html = _candidate_html(row)
        assert row["hcc_supported"] is False
        assert row["hcc_suggested"] == []
        assert "HCC-supported" not in html


def test_missing_or_ambiguous_diagnosis_state_does_not_create_hcc_metadata():
    result = evaluate_patient(Patient(age=60, sex="male"))

    rows = prepare_diagnosis_display_entries(result)

    assert all(row["hcc_supported"] is False for row in rows)
    assert all(row["hcc_suggested"] == [] for row in rows)


def test_legacy_hcc_relevant_boolean_does_not_create_supported_badge_by_itself():
    rows = normalize_diagnosis_entries(
        {
            "diagnosisSynthesis": {
                "diagnoses": [
                    {
                        "dx_id": "apob",
                        "label": "Elevated ApoB / atherogenic particle burden",
                        "status": "data-derived",
                        "icd10_suggested": ["E78.89"],
                        "hcc_relevant": True,
                    }
                ]
            }
        }
    )

    assert rows[0]["hcc_supported"] is False
    assert rows[0]["hcc_suggested"] == []
