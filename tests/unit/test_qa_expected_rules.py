from qa_agent.expected_rules import (
    albuminuria_category,
    aspirin_primary_prevention_indicated,
    diabetes_range,
    derived_expectations,
    lipid_therapy_reasonable,
    prediabetes_range,
    structural_plaque_detected,
)


def test_albuminuria_category_thresholds():
    assert albuminuria_category(None) is None
    assert albuminuria_category(12) == "A1"
    assert albuminuria_category(30) == "A2"
    assert albuminuria_category(299) == "A2"
    assert albuminuria_category(300) == "A3"


def test_a1c_range_rules():
    assert diabetes_range(6.5) is True
    assert diabetes_range(6.4) is False
    assert prediabetes_range(5.7) is True
    assert prediabetes_range(6.4) is True
    assert prediabetes_range(6.5) is False


def test_cac_and_aspirin_primary_prevention_rules():
    assert structural_plaque_detected(None) is None
    assert structural_plaque_detected(0) is False
    assert structural_plaque_detected(1) is True
    assert aspirin_primary_prevention_indicated(cac=0, known_ascvd=False) is False
    assert aspirin_primary_prevention_indicated(cac=0, known_ascvd=True) is True


def test_lipid_therapy_reasonable_rule():
    assert lipid_therapy_reasonable(
        ldl_c=142,
        apob=None,
        uacr=None,
        family_history_premature_ascvd=False,
        known_ascvd=False,
    )
    assert not lipid_therapy_reasonable(
        ldl_c=88,
        apob=70,
        uacr=5,
        family_history_premature_ascvd=False,
        known_ascvd=False,
    )


def test_derived_expectations_for_golden_case():
    derived = derived_expectations(
        {
            "a1c": 6.3,
            "uacr": 84,
            "cac": 0,
            "ldl_c": 142,
            "apob": 116,
            "clinical_ascvd": False,
            "family_history_premature_ascvd": True,
        }
    )

    assert derived["albuminuria_category"] == "A2"
    assert derived["diabetes_range"] is False
    assert derived["prediabetes_range"] is True
    assert derived["structural_plaque_detected"] is False
    assert derived["aspirin_primary_prevention_indicated"] is False
    assert derived["lipid_therapy_reasonable"] is True
