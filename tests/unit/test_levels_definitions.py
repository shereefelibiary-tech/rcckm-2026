from core.enums import RiskLevel
from core.patient import Patient
from core.results import RCCKMResult
from modules.levels.definitions import (
    LEVEL_DEFS,
    classify_continuum_position,
    get_level_definition_payload,
    levels_legend_compact,
)


def test_level_definitions_include_prevent_era_labels_and_sublevels():
    assert LEVEL_DEFS[1]["label"] == "Minimal risk signal"
    assert LEVEL_DEFS[2]["sublevels"]["2A"] == "Early isolated risk signal"
    assert LEVEL_DEFS[2]["sublevels"]["2B"] == "Converging early risk signals"
    assert LEVEL_DEFS[3]["sublevels"]["3A"] == "Elevated long-term risk trajectory"
    assert LEVEL_DEFS[3]["sublevels"]["3B"] == "Actionable early CKM / atherogenic risk"
    assert "estimated population risk" in LEVEL_DEFS[3]["description"]


def test_get_level_definition_payload_adds_sublevel_label():
    payload = get_level_definition_payload(3, "3B")

    assert payload["label"] == "Actionable biologic risk"
    assert payload["sublevel"] == "3B"
    assert payload["sublevel_label"] == "Actionable early CKM / atherogenic risk"


def test_levels_legend_compact_returns_all_levels():
    assert levels_legend_compact() == [
        "Level 1: Minimal risk signal",
        "Level 2: Emerging risk signals",
        "Level 3: Actionable biologic risk",
        "Level 4: Subclinical atherosclerosis present",
        "Level 5: Very high risk / ASCVD intensity",
    ]


def test_prevent_high_with_missing_cac_does_not_become_level_4():
    patient = Patient(age=60, sex="male", cac=None)
    result = RCCKMResult(prevent_risk_category=RiskLevel.HIGH)

    position = classify_continuum_position(patient, result)

    assert position["level"] == 3
    assert position["level"] != 4


def test_prevent_intermediate_with_missing_cac_becomes_emerging_signal():
    patient = Patient(age=60, sex="male", cac=None)
    result = RCCKMResult(prevent_risk_category=RiskLevel.INTERMEDIATE)

    position = classify_continuum_position(patient, result)

    assert position == {"level": 2, "sublevel": "2A"}


def test_elevated_30_year_prevent_trajectory_becomes_level_3a_without_other_burden():
    patient = Patient(age=45, sex="male", cac=None)
    result = RCCKMResult(prevent_risk_category=RiskLevel.LOW, prevent_30y_ascvd=10.5)

    position = classify_continuum_position(patient, result)

    assert position == {"level": 3, "sublevel": "3A"}


def test_elevated_30_year_prevent_with_biologic_burden_becomes_level_3b():
    patient = Patient(age=38, sex="male", cac=None, ldl_c=164)
    result = RCCKMResult(prevent_risk_category=RiskLevel.LOW, prevent_30y_ascvd=10.8)

    position = classify_continuum_position(patient, result)

    assert position == {"level": 3, "sublevel": "3B"}


def test_elevated_30_year_prevent_does_not_override_cac_or_clinical_ascvd():
    cac_position = classify_continuum_position(
        Patient(age=45, sex="male", cac=25),
        RCCKMResult(prevent_risk_category=RiskLevel.LOW, prevent_30y_ascvd=10.5),
    )
    ascvd_position = classify_continuum_position(
        Patient(age=45, sex="male", clinical_ascvd=True),
        RCCKMResult(prevent_risk_category=RiskLevel.LOW, prevent_30y_ascvd=10.5),
    )

    assert cac_position == {"level": 4, "sublevel": None}
    assert ascvd_position == {"level": 5, "sublevel": None}


def test_cac_50_becomes_level_4():
    position = classify_continuum_position(
        Patient(age=60, sex="male", cac=50),
        RCCKMResult(),
    )

    assert position == {"level": 4, "sublevel": None}


def test_cac_350_becomes_level_5():
    position = classify_continuum_position(
        Patient(age=60, sex="male", cac=350),
        RCCKMResult(),
    )

    assert position == {"level": 5, "sublevel": None}


def test_diabetes_apob_smoking_without_cac_can_become_level_3():
    position = classify_continuum_position(
        Patient(age=60, sex="male", diabetes=True, apob=118, smoker=True),
        RCCKMResult(),
    )

    assert position == {"level": 3, "sublevel": "3B"}


def test_isolated_mild_signal_becomes_2a():
    position = classify_continuum_position(
        Patient(age=60, sex="male", apob=90),
        RCCKMResult(),
    )

    assert position == {"level": 2, "sublevel": "2A"}


def test_converging_mild_signals_become_2b():
    position = classify_continuum_position(
        Patient(age=60, sex="male", apob=90, a1c=5.9),
        RCCKMResult(),
    )

    assert position == {"level": 2, "sublevel": "2B"}
