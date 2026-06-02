import json

from qa_agent import comparator


def test_compare_case_includes_interpretation_level_findings(tmp_path, monkeypatch):
    outputs = tmp_path / "outputs"
    expected_dir = tmp_path / "expected"
    outputs.mkdir()
    expected_dir.mkdir()
    actual = {
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
        },
        "engine_output_json": {"ok": True},
        "final_report_text": (
            "CKM/Kidney/Plaque: CKM stage 3; kidney G2A2; CAC 0.\n"
            "1. Lipids: Discuss moderate-intensity statin.\n"
            "6. Aspirin: Not indicated."
        ),
        "recommendations_text": "Discuss moderate-intensity statin therapy.",
        "ckm_stage": {"stage": 3},
        "risk_level": {"level": "3B"},
        "diagnoses": [{"name": "Prediabetes"}],
        "visible_ui_text": "Recognized",
    }
    expected = {
        "age": 55,
        "sex": "male",
        "ldl_c": 142,
        "apob": 116,
        "a1c": 6.3,
        "egfr": 72,
        "uacr_mg_g": 84,
        "cac_score": 0,
        "family_history_premature_ascvd": True,
        "known_ascvd": False,
        "albuminuria_category": "A2",
        "diabetes_range": False,
        "prediabetes_range": True,
        "aspirin_primary_prevention_indicated": False,
        "lipid_therapy_reasonable": True,
        "ckm_stage": 3,
        "risk_level": "3B",
        "kdigo_stage": "G2A2",
        "aspirin_recommendation": "Not indicated",
        "lipid_recommendation_contains": "Discuss moderate-intensity statin",
    }
    (outputs / "golden_001_actual.json").write_text(json.dumps(actual), encoding="utf-8")
    (expected_dir / "golden_001_expected.json").write_text(
        json.dumps(expected),
        encoding="utf-8",
    )
    monkeypatch.setattr(comparator, "OUTPUT_DIR", outputs)
    monkeypatch.setattr(comparator, "EXPECTED_DIR", expected_dir)

    comparison = comparator.compare_case("golden_001")

    assert comparison["status"] == "PASS"
    keys = {item["key"] for item in comparison["findings"]}
    assert {"ckm_stage", "risk_level", "kdigo_stage", "aspirin_recommendation"} <= keys


def test_compare_case_fails_on_wrong_interpretation_signal(tmp_path, monkeypatch):
    outputs = tmp_path / "outputs"
    expected_dir = tmp_path / "expected"
    outputs.mkdir()
    expected_dir.mkdir()
    actual = {
        "parsed_patient_json": {"uacr": 84, "a1c": 6.3, "cac": 0},
        "engine_output_json": {"ok": True},
        "final_report_text": "Aspirin: Not indicated.",
        "recommendations_text": "",
        "ckm_stage": {"stage": 2},
        "risk_level": {"level": "3A"},
        "diagnoses": [],
        "visible_ui_text": "",
    }
    expected = {"ckm_stage": 3, "risk_level": "3B"}
    (outputs / "golden_001_actual.json").write_text(json.dumps(actual), encoding="utf-8")
    (expected_dir / "golden_001_expected.json").write_text(
        json.dumps(expected),
        encoding="utf-8",
    )
    monkeypatch.setattr(comparator, "OUTPUT_DIR", outputs)
    monkeypatch.setattr(comparator, "EXPECTED_DIR", expected_dir)

    comparison = comparator.compare_case("golden_001")

    assert comparison["status"] == "FAIL"
    assert comparison["counts"]["fail"] == 2
