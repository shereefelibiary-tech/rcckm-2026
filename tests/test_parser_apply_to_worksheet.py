from pathlib import Path

from modules.diagnoses.engine import build_diagnosis_candidates
from ui.input_worksheet import build_patient_from_inputs
from ui.ingest_panel import (
    apply_parsed_to_session_state,
    build_parser_recognition_items,
    parse_ingest_report,
)


EPIC_PLACEHOLDER_SMARTPHRASE = """
Age: 73 y.o.
Sex: male

BP Readings from Last 3 Encounters:
05/01/26 132/77
04/24/26 148/82

BMI: @LAST_BMI@
Estimated body mass index is 30.81 kg/m2.

Smoking status: Former
Quit date: 1/18/1975
2.8 pack-years

Family History:
Premature ASCVD in first-degree relative: ***
Age at event (if yes): ***

Calcification / plaque
Coronary artery calcium (CAC) score: ***

Lipids
TC 198
TG 323
HDL 44
LDL 90
ApoB: No results found for: "APOB"
Lp(a): No results found for: "LIPOA"
hsCRP: No results found for: "CRPHS"

A1c:
Hemoglobin A1C
Date    Value    Ref Range    Status
04/24/2026    5.8 (H)    0 - 5.6 %    Final
        Comment:
        Reference Range
Normal       <5.7%
Prediabetes  5.7-6.4%
Diabetes     >6.4%

Kidney
LABGLOM 71
eGFR Cre 71
Creatinine clearance 69
Urine ACR: No results found for: "ALBCREAT"

Current medications:
amlodipine 5 mg daily
lisinopril-HCTZ 20-12.5 mg daily
"""


def _patient_from_worksheet_state(state):
    return build_patient_from_inputs(
        {
            key.removeprefix("input_"): value
            for key, value in state.items()
            if str(key).startswith("input_")
        }
    )


def _diagnosis_names(patient):
    return {candidate.name for candidate in build_diagnosis_candidates(patient)}


def test_false_values_apply_to_worksheet_state():
    report = parse_ingest_report(
        """
        Clinical ASCVD: No
        Diabetes: No
        Smoking: No
        HIV: No
        RA: No
        SLE: No
        Psoriasis: No
        IBD: No
        OSA: No
        MASLD: No
        BP treated: No
        Lipid-lowering therapy: No
        """
    )
    state = {}

    apply_parsed_to_session_state(state, report["parsed"])

    for key in (
        "input_clinical_ascvd",
        "input_diabetes",
        "input_smoker",
        "input_hiv",
        "input_rheumatoid_arthritis",
        "input_sle",
        "input_psoriasis",
        "input_ibd",
        "input_osa",
        "input_masld",
        "input_bp_treated",
        "input_lipid_lowering",
    ):
        assert state[key] is False


def test_cac_not_done_populates_no_cac_state():
    report = parse_ingest_report("CAC not done.")
    state = {"input_cac": 0, "input_cac_not_done": False}

    apply_parsed_to_session_state(state, report["parsed"])

    assert state["input_cac"] is None
    assert state["input_cac_not_done"] is True


def test_numeric_cac_zero_clears_no_cac_state():
    state = {"input_cac_not_done": True}

    apply_parsed_to_session_state(state, {"cac": 0})

    assert state["input_cac"] == 0
    assert state["input_cac_not_done"] is False


def test_new_parse_clears_stale_family_history_values():
    state = {}
    first = parse_ingest_report("Father MI age 49")
    second = parse_ingest_report("Father MI age 61")

    apply_parsed_to_session_state(state, first["parsed"])
    apply_parsed_to_session_state(state, second["parsed"])

    assert state["input_fhx_text"] == "Father MI age 61"
    assert state["input_family_history_relationship"] == "father"
    assert state["input_family_history_event_type"] == "MI"
    assert state["input_family_history_age_at_event"] == 61
    assert state["input_family_history_premature_ascvd"] is False


def test_new_parse_replaces_cac_values_and_not_done_state():
    state = {}

    apply_parsed_to_session_state(state, parse_ingest_report("CAC: 350")["parsed"])
    apply_parsed_to_session_state(state, parse_ingest_report("CAC: 0")["parsed"])

    assert state["input_cac"] == 0
    assert state["input_cac_not_done"] is False

    apply_parsed_to_session_state(state, parse_ingest_report("CAC not done.")["parsed"])

    assert state["input_cac"] is None
    assert state["input_cac_not_done"] is True


def test_new_parse_applies_false_booleans_over_old_true_values():
    state = {}

    apply_parsed_to_session_state(
        state,
        parse_ingest_report("OSA: Yes\nMASLD: Yes")["parsed"],
    )
    apply_parsed_to_session_state(
        state,
        parse_ingest_report("OSA: No\nMASLD: No")["parsed"],
    )

    assert state["input_osa"] is False
    assert state["input_masld"] is False


def test_ancestry_parse_syncs_compact_dropdown_state():
    state = {}

    apply_parsed_to_session_state(
        state,
        parse_ingest_report("South Asian ancestry: Yes\nFilipino ancestry: Yes")["parsed"],
    )

    assert state["input_south_asian_ancestry"] is True
    assert state["input_filipino_ancestry"] is True
    assert state["input_ancestry_context"] == "South Asian"

    apply_parsed_to_session_state(
        state,
        parse_ingest_report("South Asian ancestry: No\nFilipino ancestry: Yes")["parsed"],
    )

    assert state["input_south_asian_ancestry"] is False
    assert state["input_filipino_ancestry"] is True
    assert state["input_ancestry_context"] == "Filipino"


def test_new_parse_applies_unknown_booleans_over_old_true_values():
    state = {}

    apply_parsed_to_session_state(
        state,
        parse_ingest_report(
            "HIV: Yes\nCurrent smoker: Yes\nHistory of preeclampsia: Yes"
        )["parsed"],
    )
    apply_parsed_to_session_state(
        state,
        parse_ingest_report(
            "HIV: Unknown\nCurrent smoker: Unknown\nHistory of preeclampsia: Unknown"
        )["parsed"],
    )

    assert state["input_hiv"] is False
    assert state["input_smoker"] is False
    assert state["input_preeclampsia"] is False
    assert state["_unknown_input_hiv"] is True
    assert state["_unknown_input_smoker"] is True
    assert state["_unknown_input_preeclampsia"] is True


def test_new_parse_clears_stale_missing_numeric_fields():
    state = {}

    apply_parsed_to_session_state(
        state,
        parse_ingest_report("UACR: 45\nLp(a): 142 nmol/L")["parsed"],
    )
    apply_parsed_to_session_state(state, parse_ingest_report("Age: 55")["parsed"])

    assert state.get("input_uacr") is None
    assert state.get("input_lp_a_value") is None
    assert state.get("input_lp_a_unit") is None
    assert state["input_age"] == 55


def test_new_parse_clears_stale_medications_and_medication_booleans():
    state = {}
    first = parse_ingest_report("Current medications:\nlisinopril 10 mg daily")
    second = parse_ingest_report("Age: 55\nSex: male\nLDL-C 90")

    apply_parsed_to_session_state(state, first["parsed"], parse_report=first)

    assert state["input_medications_raw"] == "lisinopril"
    assert state["input_ace_arb"] is True
    assert state["input_bp_treated"] is True
    assert state["input_bp_meds"] is True

    apply_parsed_to_session_state(state, second["parsed"], parse_report=second)

    patient = _patient_from_worksheet_state(state)
    names = _diagnosis_names(patient)

    assert state.get("input_medications_raw") is None
    assert state.get("input_dm_meds_raw") is None
    assert state["input_ace_arb"] is False
    assert state["input_bp_treated"] is False
    assert state["input_bp_meds"] is False
    assert "Essential hypertension" not in names


def test_new_parse_clears_stale_cac_and_plaque_diagnosis():
    state = {}
    first = parse_ingest_report("CAC: 350")
    second = parse_ingest_report("Coronary artery calcium (CAC) score: Unknown")

    apply_parsed_to_session_state(state, first["parsed"], parse_report=first)
    assert state["input_cac"] == 350

    apply_parsed_to_session_state(state, second["parsed"], parse_report=second)

    patient = _patient_from_worksheet_state(state)
    names = _diagnosis_names(patient)

    assert state.get("input_cac") is None
    assert state["input_cac_not_done"] is True
    assert patient.cac is None
    assert "Subclinical coronary atherosclerosis" not in names
    assert "Severe subclinical coronary atherosclerosis" not in names


def test_family_history_conflict_when_explicit_premature_flag_disagrees_with_age():
    report = parse_ingest_report(
        "Premature ASCVD in first-degree relative: Yes\nFather MI age 61"
    )

    assert report["parsed"]["family_history_premature_ascvd"] is False
    assert any(
        "Family history conflict" in conflict
        for conflict in report["conflicts"]
    )


def test_epic_placeholder_parse_clears_stale_family_osa_masld_state():
    state = {
        "input_family_history_pattern": "father_premature_ascvd",
        "input_family_history_premature_ascvd": True,
        "input_family_history_relationship": "father",
        "input_family_history_event_type": "MI",
        "input_family_history_age_at_event": 49,
        "input_osa": True,
        "input_masld": True,
        "input_cac": 350,
        "input_apob": 110,
        "input_lp_a_value": 80,
        "input_uacr": 45,
        "input_hscrp": 2.4,
    }

    report = parse_ingest_report(EPIC_PLACEHOLDER_SMARTPHRASE)
    parsed = report["parsed"]

    assert parsed["age"] == 73
    assert parsed["a1c"] == 5.8
    assert parsed["egfr"] == 71
    assert parsed["bmi"] == 30.81
    assert parsed["smoker"] is False
    assert parsed["former_smoker"] is True
    assert parsed["pack_years"] == 2.8
    assert parsed["family_history_premature_ascvd"] is None
    assert "family_history_relationship" not in parsed
    assert "family_history_event_type" not in parsed
    assert "family_history_age_at_event" not in parsed
    assert "osa" not in parsed
    assert "masld" not in parsed
    assert parsed["cac"] is None
    assert parsed.get("apob") is None
    assert parsed.get("lp_a_value") is None
    assert parsed.get("uacr") is None
    assert parsed.get("hscrp") is None
    assert parsed["bp_treated"] is True
    assert parsed["ace_arb"] is True

    apply_parsed_to_session_state(state, parsed, parse_report=report)

    assert state["input_family_history_pattern"] == "none_unknown"
    assert state["input_family_history_premature_ascvd"] is False
    assert state["_unknown_input_family_history_premature_ascvd"] is True
    assert state["input_family_history_helper"] == "Family history unclear"
    assert state.get("input_family_history_relationship") is None
    assert state.get("input_family_history_event_type") is None
    assert state.get("input_family_history_age_at_event") is None
    assert state.get("input_osa") in (None, False)
    assert state.get("input_masld") in (None, False)
    assert state.get("input_cac") is None
    assert state.get("input_apob") is None
    assert state.get("input_lp_a_value") is None
    assert state.get("input_uacr") is None
    assert state.get("input_hscrp") is None


def test_new_parse_without_osa_masld_unchecks_prior_parser_values():
    state = {}
    stress_report = parse_ingest_report(
        Path("tests/fixtures/ingest/ugly_epic_smartphrase_02.txt").read_text(encoding="utf-8")
    )
    no_osa_masld_report = parse_ingest_report(EPIC_PLACEHOLDER_SMARTPHRASE)

    apply_parsed_to_session_state(state, stress_report["parsed"], parse_report=stress_report)
    assert state["input_osa"] is True
    assert state["input_masld"] is True

    apply_parsed_to_session_state(
        state,
        no_osa_masld_report["parsed"],
        parse_report=no_osa_masld_report,
    )
    fields = {item.field_id for item in build_parser_recognition_items(no_osa_masld_report)}

    assert "osa" not in no_osa_masld_report["parsed"]
    assert "masld" not in no_osa_masld_report["parsed"]
    assert "osa" not in fields
    assert "masld" not in fields
    assert state["input_osa"] is False
    assert state["input_masld"] is False


def test_family_history_positive_applies_compact_positive_option():
    report = parse_ingest_report("Father MI age 49")
    state = {}

    apply_parsed_to_session_state(state, report["parsed"], parse_report=report)

    assert state["input_family_history_premature_ascvd"] is True
    assert state["input_family_history_relationship"] == "father"
    assert state["input_family_history_event_type"] == "MI"
    assert state["input_family_history_age_at_event"] == 49
    assert state.get("input_family_history_pattern") != "none_unknown"
    assert "input_family_history_helper" not in state


def test_family_history_explicit_negative_applies_neutral_negative_state():
    report = parse_ingest_report("Premature ASCVD in first-degree relative: No")
    state = {
        "input_family_history_pattern": "father_premature_ascvd",
        "input_family_history_premature_ascvd": True,
        "input_family_history_relationship": "father",
        "input_family_history_event_type": "ASCVD",
        "input_family_history_age_at_event": 49,
    }

    apply_parsed_to_session_state(state, report["parsed"], parse_report=report)

    assert state["input_family_history_pattern"] == "none_unknown"
    assert state["input_family_history_premature_ascvd"] is False
    assert "_unknown_input_family_history_premature_ascvd" not in state
    assert state.get("input_family_history_relationship") is None
    assert state.get("input_family_history_event_type") is None
    assert state.get("input_family_history_age_at_event") is None
    assert "input_family_history_helper" not in state


def test_family_history_placeholder_applies_neutral_unclear_state():
    report = parse_ingest_report("Premature ASCVD in first-degree relative: ***\nAge at event: ***")
    state = {
        "input_family_history_pattern": "father_premature_ascvd",
        "input_family_history_premature_ascvd": True,
        "input_family_history_relationship": "father",
        "input_family_history_event_type": "ASCVD",
        "input_family_history_age_at_event": 49,
    }

    apply_parsed_to_session_state(state, report["parsed"], parse_report=report)

    assert state["input_family_history_pattern"] == "none_unknown"
    assert state["input_family_history_premature_ascvd"] is False
    assert state["_unknown_input_family_history_premature_ascvd"] is True
    assert state.get("input_family_history_relationship") is None
    assert state.get("input_family_history_event_type") is None
    assert state.get("input_family_history_age_at_event") is None
    assert state["input_family_history_helper"] == "Family history unclear"
