import inspect

from qa_agent.guideline_oracle import (
    albuminuria_category,
    aspirin_action,
    ckm_stage,
    egfr_stage,
    kdigo_stage,
    lipid_action_and_targets,
    oracle_from_patient,
    plaque_status,
    prevent_category,
)


def test_guideline_oracle_does_not_import_engine_modules():
    import qa_agent.guideline_oracle as oracle

    source = inspect.getsource(oracle)

    assert "from core.engine" not in source
    assert "import core.engine" not in source
    assert "from modules." not in source
    assert "import modules." not in source


def test_prevent_category_thresholds():
    assert prevent_category(None) is None
    assert prevent_category(2.9) == "Low"
    assert prevent_category(5.0) == "Borderline"
    assert prevent_category(7.5) == "Intermediate"
    assert prevent_category(20.0) == "High"


def test_kdigo_thresholds():
    assert egfr_stage(95) == "G1"
    assert egfr_stage(72) == "G2"
    assert egfr_stage(55) == "G3a"
    assert egfr_stage(35) == "G3b"
    assert egfr_stage(16) == "G4"
    assert egfr_stage(10) == "G5"
    assert albuminuria_category(10) == "A1"
    assert albuminuria_category(84) == "A2"
    assert albuminuria_category(300) == "A3"
    assert kdigo_stage(72, 84) == "G2A2"


def test_plaque_and_aspirin_framework():
    assert plaque_status(None) == "not measured"
    assert plaque_status(0) == "not detected"
    assert plaque_status(18) == "present"
    assert plaque_status(145) == "high burden"
    assert plaque_status(350) == "very high burden"
    assert aspirin_action({"age": 55, "cac": 0, "clinical_ascvd": False}) == (
        "not indicated",
        False,
    )
    assert aspirin_action({"age": 55, "cac": 145, "clinical_ascvd": False}) == (
        "consider only if bleeding risk is low",
        False,
    )


def test_ckm_and_apob_first_lipid_logic_for_golden_case():
    patient = {
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
        "lipid_lowering": False,
    }

    assert ckm_stage(patient) == (
        3,
        "Subclinical cardiovascular disease or CKD is present.",
    )
    assert lipid_action_and_targets(patient, "3B") == (
        "discuss moderate-intensity statin",
        100,
        90,
    )
    oracle = oracle_from_patient(patient)
    assert oracle["prevent_category"] is None
    assert oracle["ckm_stage"] == 3
    assert oracle["kdigo_stage"] == "G2A2"
    assert oracle["risk_level"] == "3B"
    assert oracle["albuminuria_present"] is True
    assert oracle["structural_plaque_detected"] is False
    assert oracle["diabetes_range"] is False
    assert oracle["prediabetes_range"] is True
    assert oracle["aspirin_action"] == "not indicated"
    assert "Moderately increased albuminuria" in oracle["diagnoses"]
