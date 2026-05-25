from ui.demo_case_gallery import DEMO_CASES, build_demo_patient, demo_case_options


def test_demo_case_gallery_uses_available_golden_cases():
    options = demo_case_options()

    assert len(options) == len(DEMO_CASES)
    labels = [label for label, _case_name in options]
    assert "Low risk / complete data" in labels
    assert "Severe hypertriglyceridemia" in labels


def test_demo_case_gallery_builds_patient_from_golden_case():
    patient = build_demo_patient("tg_1000_very_severe")

    assert patient.triglycerides is not None
    assert patient.triglycerides >= 1000
    assert patient.age == 50
    assert patient.sex == "male"
