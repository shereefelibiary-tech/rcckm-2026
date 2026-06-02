import json

from qa_agent import discrepancy_review


def _actual_payload(**overrides):
    payload = {
        "parsed_patient_json": {
            "age": 55,
            "sex": "male",
            "ldl_c": 142,
            "apob": 116,
            "a1c": 6.3,
            "egfr": 72,
            "uacr": 84,
            "cac": 0,
            "family_history_premature_ascvd": True,
            "clinical_ascvd": False,
            "bmi": 31,
        },
        "final_report_text": (
            "Level: 3B.\n"
            "CKM/Kidney/Plaque: CKM stage 3; kidney G2A2; CAC 0.\n"
            "1. Lipids: Discuss moderate-intensity statin.\n"
            "6. Aspirin: Not indicated."
        ),
        "recommendations_text": "Discuss moderate-intensity statin. Aspirin: Not indicated.",
        "ckm_stage": {"stage": 3},
        "risk_level": {"level": "3B"},
        "diagnoses": [
            {"name": "Prediabetes"},
            {"name": "Obesity"},
            {"name": "Moderately increased albuminuria"},
        ],
    }
    payload.update(overrides)
    return payload


def test_review_case_passes_when_oracle_and_rcckm_outputs_align(tmp_path, monkeypatch):
    output_dir = tmp_path / "outputs"
    discrepancy_dir = tmp_path / "discrepancies"
    output_dir.mkdir()
    (output_dir / "golden_001_actual.json").write_text(
        json.dumps(_actual_payload()),
        encoding="utf-8",
    )
    monkeypatch.setattr(discrepancy_review, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(discrepancy_review, "DISCREPANCY_DIR", discrepancy_dir)

    review = discrepancy_review.review_case("golden_001")
    path = discrepancy_review.write_review("golden_001", review)

    assert review["status"] == "PASS"
    assert review["discrepancies"] == []
    assert "No discrepancies found." in path.read_text(encoding="utf-8")


def test_review_case_explains_mismatch_without_fixing_it(tmp_path, monkeypatch):
    output_dir = tmp_path / "outputs"
    discrepancy_dir = tmp_path / "discrepancies"
    output_dir.mkdir()
    (output_dir / "golden_001_actual.json").write_text(
        json.dumps(
            _actual_payload(
                ckm_stage={"stage": 2},
                risk_level={"level": "3A"},
                final_report_text="Aspirin: Not indicated.",
                recommendations_text="",
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(discrepancy_review, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(discrepancy_review, "DISCREPANCY_DIR", discrepancy_dir)

    review = discrepancy_review.review_case("golden_001")
    path = discrepancy_review.write_review("golden_001", review)
    markdown = path.read_text(encoding="utf-8")

    assert review["status"] == "FAIL"
    assert any(item["domain"] == "CKM stage" for item in review["discrepancies"])
    assert any(item["domain"] == "risk level" for item in review["discrepancies"])
    assert "Expected:" in markdown
    assert "Actual:" in markdown
    assert "Clinical significance:" in markdown
    assert "Suspected source:" in markdown
