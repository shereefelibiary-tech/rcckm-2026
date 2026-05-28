from ui.ingest_panel import (
    apply_parsed_to_session_state,
    build_parse_review_rows,
    contains_phi,
    parse_ingest_report,
    parse_ingest_text,
)


def test_ingest_phi_warning_detects_common_identifiers():
    assert contains_phi("MRN TEST-0000")
    assert contains_phi("patient@example.com")
    assert contains_phi("555-010-0000")


def test_parse_ingest_text_family_history_structured_fields():
    parsed = parse_ingest_text("Mother stroke age 61, ApoB 110")

    assert parsed["family_history_relationship"] == "mother"
    assert parsed["family_history_event_type"] == "stroke"
    assert parsed["family_history_age_at_event"] == 61
    assert parsed["apob"] == 110


def test_parsed_values_can_be_stringified_for_review_table():
    report = parse_ingest_report("60M Father MI age 49")

    rows = build_parse_review_rows(report)

    assert all(isinstance(row["Parsed value"], str) for row in rows)
    assert {row["Confidence"] for row in rows} >= {"parsed", "inferred", "not found"}


def test_parse_report_marks_uncertain_family_history():
    report = parse_ingest_report("family history of heart disease")

    row = [
        row
        for row in build_parse_review_rows(report)
        if row["Field"] == "family_history_premature_ascvd"
    ][0]

    assert row["Confidence"] == "uncertain"


def test_parser_handles_negated_diabetes_and_smoking():
    parsed = parse_ingest_text("No diabetes. Never smoker. LDL-C 135. On rosuvastatin.")

    assert parsed["diabetes"] is False
    assert parsed["smoker"] is False
    assert parsed["ldl_c"] == 135
    assert parsed["lipid_lowering"] is True


def test_parser_explicit_negative_condition_booleans_do_not_check_boxes():
    report = parse_ingest_report(
        """
        Inflammatory disease: No
        HIV: No
        Rheumatoid arthritis: No
        RA: No
        SLE: No
        Psoriasis: No
        IBD: No
        Obstructive sleep apnea: No
        OSA: No
        MASLD: No
        Fatty liver: No
        Smoking: No
        Diabetes: No
        Clinical ASCVD: No
        BP treated: No
        Lipid-lowering therapy: No
        SGLT2: No
        GLP-1: No
        ACE/ARB: No
        """
    )
    parsed = report["parsed"]
    expected_false = [
        "inflammatory_disease",
        "hiv",
        "rheumatoid_arthritis",
        "sle",
        "psoriasis",
        "ibd",
        "osa",
        "masld",
        "smoker",
        "diabetes",
        "clinical_ascvd",
        "bp_treated",
        "lipid_lowering",
        "sglt2",
        "glp1",
        "ace_arb",
    ]

    for field in expected_false:
        assert parsed[field] is False

    state = {}
    apply_parsed_to_session_state(state, parsed)

    for field in expected_false:
        assert state[f"input_{field}"] is False


def test_parser_positive_osa_masld_only_does_not_infer_inflammatory_conditions():
    parsed = parse_ingest_text(
        """
        Inflammatory disease: No
        HIV: No
        RA: No
        SLE: No
        Psoriasis: No
        IBD: No
        OSA: Yes
        MASLD: Yes
        """
    )

    assert parsed["osa"] is True
    assert parsed["masld"] is True
    assert parsed["inflammatory_disease"] is False
    assert parsed["hiv"] is False
    assert parsed["rheumatoid_arthritis"] is False
    assert parsed["sle"] is False
    assert parsed["psoriasis"] is False
    assert parsed["ibd"] is False


def test_parser_inflammatory_no_and_ra_no_stays_false():
    parsed = parse_ingest_text("Inflammatory disease: No\nRheumatoid arthritis: No")

    assert parsed["inflammatory_disease"] is False
    assert parsed["rheumatoid_arthritis"] is False


def test_parser_ra_yes_sets_ra_and_inflammatory_group():
    parsed = parse_ingest_text("Rheumatoid arthritis: Yes")

    assert parsed["rheumatoid_arthritis"] is True
    assert parsed["inflammatory_disease"] is True


def test_parser_hiv_yes_does_not_create_inflammatory_conflict():
    report = parse_ingest_report(
        """
        HIV: Yes
        Inflammatory disease: No
        RA: No
        SLE: No
        Psoriasis: No
        IBD: No
        """
    )
    parsed = report["parsed"]

    assert parsed["hiv"] is True
    assert parsed["inflammatory_disease"] is False
    assert parsed["rheumatoid_arthritis"] is False
    assert parsed["sle"] is False
    assert parsed["psoriasis"] is False
    assert parsed["ibd"] is False
    assert report["conflicts"] == []


def test_parser_hiv_no_and_inflammatory_no_are_both_false():
    report = parse_ingest_report("HIV: No\nInflammatory disease: No")

    assert report["parsed"]["hiv"] is False
    assert report["parsed"]["inflammatory_disease"] is False
    assert report["conflicts"] == []


def test_parser_specific_inflammatory_positive_with_generic_no_uses_clear_conflict():
    report = parse_ingest_report("Inflammatory disease: No\nRA: Yes")

    assert report["parsed"]["rheumatoid_arthritis"] is True
    assert report["parsed"]["inflammatory_disease"] is True
    assert report["conflicts"] == [
        "Inflammatory disease conflict: specific condition present despite generic inflammatory disease marked No."
    ]


def test_parser_diabetes_no_high_a1c_reports_conflict():
    report = parse_ingest_report("Diabetes: No. A1c 6.9.")

    assert report["parsed"]["diabetes"] is False
    assert any("A1c is >=6.5" in conflict for conflict in report["conflicts"])


def test_family_history_mi_does_not_trigger_clinical_ascvd():
    parsed = parse_ingest_text("Clinical ASCVD: No. Father MI age 49.")

    assert parsed["clinical_ascvd"] is False
    assert parsed["family_history_premature_ascvd"] is True


def test_parser_captures_clinical_ascvd_event_and_procedure_context():
    parsed = parse_ingest_text("Clinical ASCVD: Yes. NSTEMI with PCI/stent history. CAC 0.")

    assert parsed["clinical_ascvd"] is True
    assert parsed["clinical_ascvd_context"] == "prior NSTEMI and PCI/stent"


def test_parser_clinical_ascvd_event_negation_does_not_add_cabg_or_pad():
    parsed = parse_ingest_text("History of STEMI with PCI/stent. No history of PAD or CABG.")

    assert parsed["clinical_ascvd"] is True
    assert parsed["clinical_ascvd_context"] == "prior STEMI and PCI/stent"


def test_parser_all_negated_ascvd_events_returns_false():
    parsed = parse_ingest_text("No history of MI, stroke, TIA, PAD, PCI, stent, or CABG.")

    assert parsed["clinical_ascvd"] is False
    assert "clinical_ascvd_context" not in parsed


def test_parser_ischemic_stroke_with_negated_cabg_pad_context():
    parsed = parse_ingest_text("History of ischemic stroke. Denies CAD, PAD, CABG.")

    assert parsed["clinical_ascvd"] is True
    assert parsed["clinical_ascvd_context"] == "ischemic stroke"


def test_apply_parsed_to_session_state_populates_worksheet_keys():
    state = {}

    apply_parsed_to_session_state(
        state,
        {
            "ldl_c": 142,
            "bp_treated": True,
            "family_history_relationship": "father",
        },
    )

    assert state["input_ldl_c"] == 142
    assert state["input_bp_treated"] is True
    assert state["input_bp_meds"] is True
    assert state["input_family_history_relationship"] == "father"


def test_apply_parsed_to_session_state_normalizes_event_type_for_widget():
    state = {}

    apply_parsed_to_session_state(state, {"family_history_event_type": "mi"})

    assert state["input_family_history_event_type"] == "MI"


def test_apply_parsed_to_session_state_rounds_integer_fields_but_preserves_a1c_precision():
    state = {}

    apply_parsed_to_session_state(
        state,
        {
            "ldl_c": 132.4,
            "apob": 110.0,
            "uacr": 45.0,
            "egfr": 55.0,
            "cac": 350.2,
            "lp_a_value": 179.6,
            "a1c": 7.14,
            "bmi": 28.04,
        },
    )

    assert state["input_ldl_c"] == 132
    assert state["input_apob"] == 110
    assert state["input_uacr"] == 45
    assert state["input_egfr"] == 55
    assert state["input_cac"] == 350
    assert state["input_lp_a_value"] == 180
    assert state["input_a1c"] == 7.1
    assert state["input_bmi"] == 28.0


def test_smartphrase_report_extracts_core_fields_and_maps_to_worksheet_names():
    report = parse_ingest_report(
        """
        55M BP 132/82 TC 205 LDL 132 HDL 48 TG 180.
        ApoB 110. Lp(a) 80 nmol/L. A1c 7.1.
        eGFR 55. UACR 45 mg/g. CAC 350.
        Father MI age 49. On lisinopril and metformin. Fasting lipids.
        """
    )

    parsed = report["parsed"]

    assert parsed["age"] == 55
    assert parsed["sex"] == "male"
    assert parsed["sbp"] == 132
    assert parsed["dbp"] == 82
    assert parsed["tc"] == 205
    assert parsed["ldl_c"] == 132
    assert parsed["hdl_c"] == 48
    assert parsed["triglycerides"] == 180
    assert parsed["apob"] == 110
    assert parsed["lp_a_value"] == 80
    assert parsed["lp_a_unit"] == "nmol/L"
    assert parsed["a1c"] == 7.1
    assert parsed["diabetes"] is True
    assert parsed["egfr"] == 55
    assert parsed["uacr"] == 45
    assert parsed["cac"] == 350
    assert parsed["family_history_premature_ascvd"] is True
    assert parsed["bp_treated"] is True
    assert parsed["medications_raw"] == "metformin, lisinopril"
    assert parsed["dm_meds_raw"] == "metformin"
    assert parsed["fasting_lipids"] is True


def test_diabetes_reference_table_does_not_create_false_diabetes():
    parsed = parse_ingest_text("A1c reference range: diabetes >=6.5; prediabetes 5.7-6.4.")

    assert "a1c" not in parsed
    assert "diabetes" not in parsed


def test_epic_placeholder_garbage_smartphrase_parses_only_real_values():
    text = (
        "Epic cardiovascular SmartPhrase synthetic example\n"
        "73-year-old male\n"
        "Race/Ethnicity: White / non-Hispanic\n"
        "BP Readings from Last 3 Encounters:\n"
        "05/01/26 132/77\n"
        "04/24/26 148/82\n"
        "BMI: @LAST_BMI@\n"
        "Estimated body mass index is 30.81 kg/m2.\n"
        "Smoking status: Former\n"
        "Quit date: 1/18/1975\n"
        "2.8 pack-years\n"
        "Premature ASCVD in first-degree relative: ***\n"
        "Coronary artery calcium (CAC) score: ***\n"
        "TC 198\n"
        "TG 323\n"
        "HDL 44\n"
        "LDL 90\n"
        "ApoB: No results found for: \"APOB\"\n"
        "Lp(a): No results found for: \"LIPOA\"\n"
        "hsCRP: No results found for: \"CRPHS\"\n"
        "Hemoglobin A1c\n"
        "04/24/2026 5.8 (H)\n"
        "Reference range:\n"
        "Normal <5.7%\n"
        "Prediabetes 5.7-6.4%\n"
        "Diabetes >6.4%\n"
        "LABGLOM 71\n"
        "eGFR Cre 71\n"
        "Creatinine clearance 69\n"
        "Urine ACR: No results found for: \"ALBCREAT\"\n"
        "Current medications:\n"
        "amlodipine 5 mg daily\n"
        "lisinopril-HCTZ 20-12.5 mg daily\n"
    )

    report = parse_ingest_report(text)
    parsed = report["parsed"]
    meta = report["meta"]

    assert parsed["age"] == 73
    assert parsed["sex"] == "male"
    assert parsed["smoker"] is False
    assert parsed["former_smoker"] is True
    assert parsed["pack_years"] == 2.8
    assert parsed["sbp"] == 132
    assert parsed["dbp"] == 77
    assert parsed["bmi"] == 30.81
    assert parsed["tc"] == 198
    assert parsed["triglycerides"] == 323
    assert parsed["hdl_c"] == 44
    assert parsed["ldl_c"] == 90
    assert parsed["a1c"] == 5.8
    assert parsed.get("diabetes") is not True
    assert parsed["egfr"] == 71
    assert parsed.get("uacr") is None
    assert parsed.get("apob") is None
    assert parsed.get("lp_a_value") is None
    assert parsed.get("hscrp") is None
    assert parsed["cac"] is None
    assert parsed["cac_not_done"] is True
    assert parsed["family_history_premature_ascvd"] is None
    assert parsed["bp_treated"] is True
    assert parsed["ace_arb"] is True
    assert meta["bmi"]["source"] == "labeled value"
    assert meta["apob"]["confidence"] == "not found"
    assert meta["lp_a_value"]["confidence"] == "not found"
    assert meta["uacr"]["confidence"] == "not found"


def test_unavailable_reasons_are_preserved_in_metadata():
    report = parse_ingest_report(
        "eGFR unavailable due to lab interface failure. UACR not done because no urine sample. CAC not done."
    )

    assert "lab interface failure" in report["meta"]["egfr"]["source"]
    assert "no urine sample" in report["meta"]["uacr"]["source"]
    assert report["parsed"]["cac"] is None
    assert report["parsed"]["cac_not_done"] is True
    assert report["meta"]["cac"]["confidence"] == "not found"
    assert any("egFR".lower() in warning.lower() or "egfr" in warning.lower() for warning in report["warnings"])


def test_cac_not_done_phrases_populate_no_cac_state():
    for text in [
        "CAC not done.",
        "Calcium score not performed.",
        "CAC unknown.",
        "No calcium score available.",
    ]:
        report = parse_ingest_report(text)

        assert report["parsed"]["cac"] is None
        assert report["parsed"]["cac_not_done"] is True


def test_apply_parsed_to_session_state_sets_and_clears_no_cac_state():
    state = {}

    apply_parsed_to_session_state(state, {"cac": None, "cac_not_done": True})

    assert state["input_cac"] is None
    assert state["input_cac_not_done"] is True

    apply_parsed_to_session_state(state, {"cac": 0})

    assert state["input_cac"] == 0
    assert state["input_cac_not_done"] is False


def test_apply_parsed_to_session_state_stores_raw_parser_extras():
    state = {}

    apply_parsed_to_session_state(
        state,
        {
            "medications_raw": "metformin, lisinopril",
            "dm_meds_raw": "metformin",
            "fasting_lipids": True,
        },
    )

    assert state["input_medications_raw"] == "metformin, lisinopril"
    assert state["input_dm_meds_raw"] == "metformin"
    assert state["input_fasting_lipids"] is True


def test_manual_override_wins_after_parser_populates_session_state():
    state = {}

    apply_parsed_to_session_state(state, {"ldl_c": 132})
    state["input_ldl_c"] = 118

    assert state["input_ldl_c"] == 118
