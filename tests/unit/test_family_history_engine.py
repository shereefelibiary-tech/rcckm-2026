from core.patient import Patient
from core.results import RCCKMResult
from modules.clarification.engine import build_clarification_ladder
from modules.diagnoses.engine import build_diagnosis_candidates
from modules.drivers.engine import build_top_drivers
from modules.family_history.engine import (
    build_family_history_payload,
    build_family_history_summary,
    is_premature_ascvd_family_history,
)
from modules.levels.definitions import classify_continuum_position
from modules.snapshot.engine import build_snapshot_lines


def test_is_premature_ascvd_family_history_uses_sex_specific_thresholds():
    assert is_premature_ascvd_family_history("father", 54) is True
    assert is_premature_ascvd_family_history("brother", 55) is False
    assert is_premature_ascvd_family_history("mother", 64) is True
    assert is_premature_ascvd_family_history("sister", 65) is False


def test_build_family_history_summary_is_human_readable():
    assert build_family_history_summary("father", "MI", 49) == "Father MI age 49"
    assert build_family_history_summary("mother", "stroke", 61) == "Mother stroke age 61"


def test_family_history_payload_sets_summary_and_boolean():
    patient = Patient(
        age=60,
        sex="male",
        family_history_relationship="father",
        family_history_event_type="MI",
        family_history_age_at_event=49,
    )

    payload = build_family_history_payload(patient)

    assert payload["summary"] == "Father MI age 49"
    assert payload["premature_fhx_ascvd"] is True


def test_family_history_supports_level_drivers_clarification_snapshot_and_diagnoses():
    patient = Patient(
        age=60,
        sex="male",
        family_history_relationship="father",
        family_history_event_type="MI",
        family_history_age_at_event=49,
    )
    payload = build_family_history_payload(patient)
    patient.family_history_summary = payload["summary"]
    patient.premature_fhx_ascvd = payload["premature_fhx_ascvd"]
    patient.family_history_premature_ascvd = payload["premature_fhx_ascvd"]

    result = RCCKMResult(family_history_summary=patient.family_history_summary)

    assert classify_continuum_position(patient, result) == {
        "level": 2,
        "sublevel": "2A",
    }
    assert build_top_drivers(patient, result) == ["Father MI age 49"]

    clarification = build_clarification_ladder(patient, result)
    assert clarification["recommend_cac"] is False
    assert clarification["tier"] == 1

    result.top_drivers = ["Father MI age 49"]
    result.clarification = clarification
    assert "Family history: Father MI age 49" in build_snapshot_lines(result)

    diagnoses = build_diagnosis_candidates(patient)
    assert any(
        candidate.name == "Premature family history of ASCVD"
        and candidate.source == "Father MI age 49"
        for candidate in diagnoses
    )
