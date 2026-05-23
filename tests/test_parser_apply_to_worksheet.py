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
