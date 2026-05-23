from tools.fuzz_rcckm import generate_patient, run_fuzz, validate_patient


def test_fuzz_generator_is_reproducible():
    import random

    first = generate_patient(random.Random(2026))
    second = generate_patient(random.Random(2026))

    assert first == second


def test_fuzz_sample_has_no_validation_failures():
    summary = run_fuzz(n=250, seed=2026)

    assert summary["failure_count"] == 0, summary["first_failures"][:3]


def test_fuzz_validation_catches_contradictory_text_if_it_occurs():
    failures = validate_patient({"age": 55, "sex": "male", "cac": 0, "clinical_ascvd": False})

    assert failures == []
