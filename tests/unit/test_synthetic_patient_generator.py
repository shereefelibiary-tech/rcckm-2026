import json

from qa_agent.generate_cases import generate_cases
from qa_agent.synthetic_patient_generator import PHENOTYPES, generate_patient, write_case


def test_generate_patient_returns_json_and_epic_smartphrase_text():
    case = generate_patient(case_id="synthetic_test", phenotype="ckd_focused", seed=42)

    assert case.case_id == "synthetic_test"
    assert case.phenotype == "ckd_focused"
    assert case.patient["age"] is not None
    assert case.patient["sex"] in {"male", "female"}
    assert "=== CARDIOVASCULAR RISK ASSESSMENT ===" in case.smartphrase_text
    assert "Urine ACR:" in case.smartphrase_text
    assert "Coronary artery calcium (CAC) score:" in case.smartphrase_text
    assert "Problem list:" in case.smartphrase_text


def test_all_required_phenotypes_generate_core_fields():
    for phenotype in PHENOTYPES:
        case = generate_patient(case_id=f"synthetic_{phenotype}", phenotype=phenotype, seed=7)
        patient = case.patient

        assert patient["phenotype"] == phenotype
        assert patient["age"] is not None
        assert patient["sbp"] is not None
        assert patient["dbp"] is not None
        assert patient["apob"] is not None
        assert patient["triglycerides"] is not None
        assert patient["hdl"] is not None
        assert patient["a1c"] is not None
        assert patient["egfr"] is not None
        assert "ApoB:" in case.smartphrase_text
        assert "Lp(a):" in case.smartphrase_text


def test_write_case_outputs_patient_json_and_text(tmp_path):
    case = generate_patient(case_id="synthetic_write", phenotype="low_risk", seed=10)

    json_path, txt_path = write_case(case, tmp_path)

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["case_id"] == "synthetic_write"
    assert payload["patient"]["phenotype"] == "low_risk"
    assert txt_path.read_text(encoding="utf-8") == case.smartphrase_text


def test_generate_cases_writes_manifest_and_cycles_phenotypes(tmp_path):
    cases = generate_cases(count=8, output_dir=tmp_path, seed=100)

    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert len(cases) == 8
    assert len(manifest) == 8
    assert {item["phenotype"] for item in manifest} >= {"low_risk", "edge_case"}
    assert (tmp_path / "synthetic_001_low_risk.json").exists()
    assert (tmp_path / "synthetic_001_low_risk.txt").exists()
