from ui.ingest_panel import apply_parsed_to_session_state, parse_ingest_report


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


def test_family_history_conflict_when_explicit_premature_flag_disagrees_with_age():
    report = parse_ingest_report(
        "Premature ASCVD in first-degree relative: Yes\nFather MI age 61"
    )

    assert report["parsed"]["family_history_premature_ascvd"] is False
    assert any(
        "Family history conflict" in conflict
        for conflict in report["conflicts"]
    )
