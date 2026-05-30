from pathlib import Path

from ui.ingest_panel import (
    EPIC_SMARTPHRASE_TEMPLATE,
    apply_parsed_to_session_state,
    build_parser_recognition_items,
    build_parse_review_rows,
    contains_phi,
    parse_ingest_report,
    parse_ingest_text,
    render_parser_recognition_strip,
)


FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


def test_ingest_phi_warning_detects_common_identifiers():
    assert contains_phi("MRN TEST-0000")
    assert contains_phi("patient@example.com")
    assert contains_phi("555-010-0000")


def test_recommended_epic_smartphrase_template_contains_core_sections():
    for section in (
        "=== CARDIOVASCULAR RISK ASSESSMENT ===",
        "Age: @AGE@",
        "Sex: @SEX@",
        "Race/Ethnicity: @RACE@",
        "Smoking status: @SMOKINGSTATUS@",
        "Blood pressure (most recent): @LASTBP(3)@",
        "BMI",
        "Clinical ASCVD: Unknown",
        "Family History:",
        "Lipids",
        "@RESUFAST(CHLPL,CHOL,TRIG,HDL,LDLCHOLESTEROL,LDL,LABVLDL,VLDL,CHOLHDLRATIO)@",
        "A1c",
        "@LASTHBA1C@",
        "ApoB",
        "Lp(a)",
        "hsCRP",
        "eGFR",
        "Urine ACR",
        "Coronary artery calcium (CAC) score: Unknown",
        "Medications",
        "@MEDSCONDENSED@",
        "Problem list:",
        "@PROB@",
    ):
        assert section in EPIC_SMARTPHRASE_TEMPLATE
    for removed in (
        "OSA:",
        "MASLD/fatty liver:",
        "Inflammatory/autoimmune disease:",
        "Heart failure:",
    ):
        assert removed not in EPIC_SMARTPHRASE_TEMPLATE


def test_parse_ingest_text_family_history_structured_fields():
    parsed = parse_ingest_text("Mother stroke age 61, ApoB 110")

    assert parsed["family_history_relationship"] == "mother"
    assert parsed["family_history_event_type"] == "stroke"
    assert parsed["family_history_age_at_event"] == 61
    assert parsed["apob"] == 110


def test_parser_preserves_compact_family_history_detail():
    report = parse_ingest_report("Family History:\nFather MI age 49")
    parsed = report["parsed"]
    by_field = {item.field_id: item for item in build_parser_recognition_items(report)}

    assert parsed["family_history_premature_ascvd"] is True
    assert parsed["family_history_relationship"] == "father"
    assert parsed["family_history_event_type"] == "mi"
    assert parsed["family_history_age_at_event"] == 49
    assert by_field["family_history"].value == "Father MI age 49"


def test_parser_nonpremature_family_history_age_does_not_create_premature_flag():
    parsed = parse_ingest_text("Mother stroke age 73")

    assert parsed["family_history_relationship"] == "mother"
    assert parsed["family_history_event_type"] == "stroke"
    assert parsed["family_history_age_at_event"] == 73
    assert parsed["family_history_premature_ascvd"] is False


def test_parser_ancestry_explicit_no_overrides_keyword_presence():
    report = parse_ingest_report("South Asian ancestry:\nNo\nFilipino ancestry:\nNo")
    parsed = report["parsed"]
    html = render_parser_recognition_strip(report)

    assert parsed["south_asian_ancestry"] is False
    assert parsed["filipino_ancestry"] is False
    assert "South Asian" not in html
    assert "Filipino" not in html


def test_parser_race_ethnicity_south_asian_still_counts_positive():
    parsed = parse_ingest_text("Race/Ethnicity: South Asian")

    assert parsed["south_asian_ancestry"] is True


def test_parser_multiline_hscrp_value_preserved_over_later_no_results():
    report = parse_ingest_report(
        """
        hsCRP
        4.8
        Reference:
        <2.0
        hsCRP: No results found for: "CRPHS"
        """
    )
    parsed = report["parsed"]
    by_field = {item.field_id: item for item in build_parser_recognition_items(report)}

    assert parsed["hscrp"] == 4.8
    assert by_field["hscrp"].status == "extracted"
    assert by_field["hscrp"].value == "4.8 mg/L"


def test_epic_case_problem_list_hierarchy_and_review_states():
    text = (FIXTURES_DIR / "epic_case_61f_black_female.txt").read_text(encoding="utf-8")

    report = parse_ingest_report(text)
    parsed = report["parsed"]
    items = {item.field_id: item for item in build_parser_recognition_items(report)}
    recognition_html = render_parser_recognition_strip(report)

    assert parsed["age"] == 61
    assert parsed["sex"] == "female"
    assert "Black" in parsed["race_ethnicity"]
    assert parsed["smoker"] is False
    assert parsed["sbp"] == 134
    assert parsed["dbp"] == 81
    assert parsed["bmi"] == 35.04
    assert parsed["ldl_c"] == 187
    assert parsed["hdl_c"] == 67
    assert parsed["triglycerides"] == 57
    assert parsed["a1c"] == 6.1
    assert parsed["diabetes"] is True
    assert parsed["diabetes_source"] == "problem_list"
    assert parsed["apob"] == 134
    assert parsed["lp_a_value"] == 346.7
    assert parsed["lp_a_review"] is True
    assert parsed.get("hscrp") is None
    assert parsed["egfr"] == 79
    assert parsed.get("uacr") is None
    assert parsed["uacr_status"] == "indeterminate"
    assert parsed["masld"] is True
    assert parsed.get("osa") is not True
    assert parsed["sleep_apnea_review"] is True
    assert parsed["rheumatoid_arthritis"] is False
    assert parsed["inflammatory_arthritis_review"] is True
    assert parsed.get("clinical_ascvd") is not True
    assert parsed.get("clinical_ascvd_review") is not True

    assert items["age"].value == "61"
    assert items["bp"].value == "134/81"
    assert items["ldl_c"].value == "187 mg/dL"
    assert items["apob"].value == "134 mg/dL"
    assert items["lp_a_value"].status == "extracted"
    assert items["lp_a_value"].value == "346.7"
    assert items["lp_a_review"].status == "review"
    assert items["diabetes"].value == "Diabetes detected"
    assert items["masld"].status == "extracted"
    assert items["uacr"].status == "review"
    assert items["osa"].status == "review"
    assert items["inflammatory"].status == "review"
    assert items["hscrp"].status == "missing"

    assert "Diabetes detected" in recognition_html
    assert "MASLD" in recognition_html
    assert "UACR not calculable" in recognition_html
    assert "Confirm Lp(a) units" in recognition_html
    assert "Possible sleep apnea" in recognition_html
    assert "Inflammatory arthritis review" in recognition_html
    assert "hsCRP not available" in recognition_html
    assert "OSA Yes" not in recognition_html
    assert "Rheumatoid arthritis" not in recognition_html
    assert "Clinical ASCVD" not in recognition_html


def test_epic_case_35f_diabetes_albuminuria_parser_regression():
    text = (FIXTURES_DIR / "epic_case_35f_diabetes_albuminuria.txt").read_text(encoding="utf-8")

    report = parse_ingest_report(text)
    parsed = report["parsed"]
    items = {item.field_id: item for item in build_parser_recognition_items(report)}

    assert parsed["age"] == 35
    assert parsed["sex"] == "female"
    assert not any(conflict.startswith("sex:") for conflict in report["conflicts"])
    assert parsed["sbp"] == 166
    assert parsed["dbp"] == 100
    assert parsed["lp_a_value"] == 22.4
    assert parsed["uacr"] == 362
    assert parsed["sglt2"] is True
    assert parsed["ace_arb"] is True
    assert parsed.get("cac") is None
    assert parsed.get("cac_not_done") is True

    assert items["bp"].value == "166/100"
    assert items["lp_a_value"].status == "extracted"
    assert items["lp_a_value"].value == "22.4"
    assert items["uacr"].value == "362 mg/g"
    assert items["sex"].value == "female"


def test_parsed_values_can_be_stringified_for_review_table():
    report = parse_ingest_report("60M Father MI age 49")

    rows = build_parse_review_rows(report)

    assert all(isinstance(row["Parsed value"], str) for row in rows)
    assert {row["Confidence"] for row in rows} >= {"parsed", "inferred", "not found"}


def test_parser_recognition_items_prioritize_real_extracted_signals():
    report = parse_ingest_report(
        "Age: 73. Sex: male. Smoking status: Former. BP 132/77 LDL 90 HDL 44 TG 323 "
        "A1c 5.8 eGFR 71 BMI 30.81 ApoB: No results found for: APOB "
        "Lp(a): No results found for: LIPOA UACR: No results found for: ALBCREAT\n"
        "Premature ASCVD in first-degree relative: ***\nMeds: amlodipine and lisinopril-HCTZ"
    )

    items = build_parser_recognition_items(report)
    by_field = {item.field_id: item for item in items}

    assert [item.field_id for item in items[:5]] == ["age", "sex", "bp", "ldl_c", "hdl_c"]
    assert by_field["bp"].status == "extracted"
    assert by_field["bp"].value == "132/77"
    assert by_field["smoking"].status == "extracted"
    assert by_field["smoking"].value == "Former smoker"
    assert by_field["medications"].status == "extracted"
    assert by_field["apob"].status == "missing"
    assert by_field["lp_a_value"].status == "missing"
    assert by_field["uacr"].status == "missing"
    assert by_field["family_history"].status == "review"


def test_parser_recognition_strip_uses_status_classes_without_fake_success():
    report = parse_ingest_report(
        "CAC score: ***\nApoB: No results found for: APOB\nSmoking status: Former. BP 132/77."
    )

    html = render_parser_recognition_strip(report)

    assert "parser-recognition-strip" in html
    assert "parser-recognition-chip extracted" in html
    assert "BP 132/77" in html
    assert "Former smoker" in html
    assert "ApoB not available" in html
    assert "CAC placeholder detected" in html
    assert "&#10003;</span>CAC" not in html
    assert "Current smoker" not in html


def test_age_label_does_not_concatenate_nearby_digits():
    report = parse_ingest_report(
        """
        Age: 73 y.o.
        Sex: male
        Race/Ethnicity: White (non-Hispanic)
        BMI 30.81
        BP 132/77
        """
    )
    by_field = {item.field_id: item for item in build_parser_recognition_items(report)}

    assert report["parsed"]["age"] == 73
    assert report["parsed"]["sex"] == "male"
    assert report["parsed"]["bmi"] == 30.81
    assert by_field["age"].status == "extracted"
    assert by_field["age"].value == "73"


def test_invalid_age_is_rejected_and_flagged_for_review():
    report = parse_ingest_report("Age: 765 y.o.\nSex: male\nBP 132/77")
    by_field = {item.field_id: item for item in build_parser_recognition_items(report)}

    assert "age" not in report["parsed"]
    assert report["meta"]["age"]["confidence"] == "uncertain"
    assert "Age parsed value invalid; review needed." in report["warnings"]
    assert any("Age parsed value invalid" in conflict for conflict in report["conflicts"])
    assert by_field["age"].status == "invalid"


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


def test_parser_ra_yes_sets_ra_without_generic_inflammatory_bucket():
    parsed = parse_ingest_text("Rheumatoid arthritis: Yes")

    assert parsed["rheumatoid_arthritis"] is True
    assert parsed["inflammatory_disease"] is False


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


def test_parser_specific_inflammatory_positive_with_generic_no_keeps_generic_false():
    report = parse_ingest_report("Inflammatory disease: No\nRA: Yes")

    assert report["parsed"]["rheumatoid_arthritis"] is True
    assert report["parsed"]["inflammatory_disease"] is False
    assert report["conflicts"] == []


def test_parser_stress_smartphrase_uses_aliases_sections_and_exclusivity():
    with open("tests/fixtures/ingest/rcckm_parser_stress_smartphrase.txt", encoding="utf-8") as fixture:
        report = parse_ingest_report(fixture.read())
    parsed = report["parsed"]
    items = {item.field_id: item for item in build_parser_recognition_items(report)}

    assert parsed["age"] == 58
    assert parsed["sex"] == "female"
    assert parsed["sbp"] == 138
    assert parsed["dbp"] == 84
    assert parsed["ldl_c"] == 141
    assert parsed["hdl_c"] == 41
    assert parsed["triglycerides"] == 212
    assert parsed["family_history_premature_ascvd"] is True
    assert parsed["family_history_relationship"] == "father"
    assert parsed["family_history_event_type"] == "mi"
    assert parsed["family_history_age_at_event"] == 52
    assert parsed["south_asian_ancestry"] is True
    assert parsed["uacr"] == 86
    assert parsed["egfr"] == 52
    assert parsed["rheumatoid_arthritis"] is True
    assert parsed["inflammatory_disease"] is False
    assert parsed["diabetes"] is False
    assert parsed["prediabetes_context"] is True
    assert parsed["cac"] == 125
    assert parsed["cac_percentile"] == 91
    assert parsed["osa"] is True
    assert parsed["masld"] is True
    assert parsed["bmi"] == 31.9
    assert parsed["a1c"] == 6.4
    assert parsed["apob"] == 118
    assert parsed["lp_a_value"] == 168
    assert parsed["hscrp"] == 3.1
    assert items["age"].status == "extracted"
    assert items["age"].value == "58"
    assert items["cac"].status == "extracted"
    assert items["cac"].value == "125"
    assert items["uacr"].status == "extracted"
    assert items["uacr"].value == "86 mg/g"
    assert items["family_history"].status == "extracted"
    assert items["ancestry"].value == "South Asian"
    assert items["inflammatory"].value == "RA"
    assert items["osa"].status == "extracted"
    assert items["masld"].status == "extracted"


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


def test_multiline_epic_a1c_table_extracts_result_not_reference_range():
    report = parse_ingest_report(
        """
        A1c:
        Hemoglobin A1C
        Date    Value    Ref Range    Status
        04/24/2026    5.8 (H)    0 - 5.6 %    Final
                Comment:
                Reference Range
        Normal       <5.7%
        Prediabetes  5.7-6.4%
        Diabetes     >6.4%
        """
    )
    parsed = report["parsed"]
    by_field = {item.field_id: item for item in build_parser_recognition_items(report)}
    strip = render_parser_recognition_strip(report)

    assert parsed["a1c"] == 5.8
    assert parsed.get("diabetes") is not True
    assert "A1c section found; result unclear" not in report["warnings"]
    assert by_field["a1c"].status == "extracted"
    assert by_field["a1c"].value == "5.8%"
    assert "A1c 5.8%" in strip
    assert "A1c missing" not in strip


def test_a1c_one_line_and_table_values_parse_without_reference_range_leakage():
    one_line = parse_ingest_report("A1c: 6.1")
    table = parse_ingest_report(
        """
        Hemoglobin A1C
        Date Value Ref Range Status
        5/1/2026 7.2 0 - 5.6 % Final
        Reference Range
        Diabetes >6.4%
        """
    )
    reference_only = parse_ingest_report(
        """
        Hemoglobin A1C
        Reference Range
        Normal <5.7%
        Prediabetes 5.7-6.4%
        Diabetes >6.4%
        """
    )

    assert one_line["parsed"]["a1c"] == 6.1
    assert table["parsed"]["a1c"] == 7.2
    assert "a1c" not in reference_only["parsed"]
    assert "diabetes" not in reference_only["parsed"]
    assert reference_only["meta"]["a1c"]["confidence"] == "uncertain"


def test_a1c_table_uses_most_recent_dated_row():
    report = parse_ingest_report(
        """
        A1c:
        Hemoglobin A1C
        Date Value Ref Range Status
        04/24/2026 5.8 (H) 0 - 5.6 % Final
        05/01/2026 6.2 (H) 0 - 5.6 % Final
        Reference Range
        Prediabetes 5.7-6.4%
        Diabetes >6.4%
        """
    )

    assert report["parsed"]["a1c"] == 6.2


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
    assert "family_history_relationship" not in parsed
    assert "family_history_event_type" not in parsed
    assert "family_history_age_at_event" not in parsed
    assert "osa" not in parsed
    assert "masld" not in parsed
    assert parsed["bp_treated"] is True
    assert parsed["ace_arb"] is True
    assert meta["bmi"]["source"] == "labeled value"
    assert meta["apob"]["confidence"] == "not found"
    assert meta["lp_a_value"]["confidence"] == "not found"
    assert meta["uacr"]["confidence"] == "not found"

    items = {item.field_id: item for item in build_parser_recognition_items(report)}
    assert items["a1c"].status == "extracted"
    assert items["a1c"].value == "5.8%"
    assert items["family_history"].status == "review"
    assert items["cac"].status == "review"
    assert items["apob"].status == "missing"
    assert items["lp_a_value"].status == "missing"
    assert items["uacr"].status == "missing"
    assert items["hscrp"].status == "missing"
    assert "osa" not in items
    assert "masld" not in items

    recognition_html = render_parser_recognition_strip(report)
    assert "Family history unclear" in recognition_html
    assert "CAC placeholder detected" in recognition_html
    assert "ApoB not available" in recognition_html
    assert "Lp(a) not available" in recognition_html
    assert "UACR not available" in recognition_html
    assert "hsCRP not available" in recognition_html
    assert "OSA" not in recognition_html
    assert "MASLD" not in recognition_html
    assert "Father &lt;55" not in recognition_html


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
