from pathlib import Path

from smartphrase_ingest.parser import parse_explicit_bool_line, parse_smartphrase_report
from ui.ingest_panel import apply_parsed_to_session_state, parse_ingest_report, parse_ingest_text, render_parser_recognition_strip
from ui.input_worksheet import build_patient_from_inputs
from ui.report_layout import run_patient
from modules.actions.engine import build_action_plan
from renderers.emr_renderer import render_emr_note
from renderers.rss_renderer import get_rss_display_contributions


def test_arbitrary_text_returns_warning_without_crashing():
    report = parse_smartphrase_report("Patient brought a printed note but no values were visible.")

    assert report.extracted == {}
    assert report.conflicts == []
    assert any("No supported RCCKM fields" in warning for warning in report.warnings)


def test_a1c_reference_table_does_not_trigger_diabetes():
    report = parse_smartphrase_report("A1c reference range: diabetes >=6.5; prediabetes 5.7-6.4.")

    assert "a1c" not in report.extracted
    assert "diabetes" not in report.extracted


def test_explicit_no_condition_lines_remain_false():
    parsed = parse_ingest_text(
        """
        HIV: No
        RA: No
        SLE: No
        Psoriasis: No
        IBD: No
        Inflammatory disease: No
        OSA: No
        MASLD: No
        Clinical ASCVD: No
        Diabetes: No
        Current smoker: No
        """
    )

    for field in (
        "hiv",
        "rheumatoid_arthritis",
        "sle",
        "psoriasis",
        "ibd",
        "inflammatory_disease",
        "osa",
        "masld",
        "clinical_ascvd",
        "diabetes",
        "smoker",
    ):
        assert parsed[field] is False


def test_positive_osa_and_masld_do_not_imply_inflammatory_disease():
    parsed = parse_ingest_text("OSA: Yes. MASLD: Yes. HIV: No. RA: No. SLE: No. Psoriasis: No. IBD: No.")

    assert parsed["osa"] is True
    assert parsed["masld"] is True
    assert parsed["hiv"] is False
    assert parsed["rheumatoid_arthritis"] is False
    assert parsed["sle"] is False
    assert parsed["psoriasis"] is False
    assert parsed["ibd"] is False
    assert "inflammatory_disease" not in parsed


def test_ra_yes_sets_inflammatory_context():
    parsed = parse_ingest_text("Rheumatoid arthritis: Yes.")

    assert parsed["rheumatoid_arthritis"] is True
    assert parsed["inflammatory_disease"] is False


def test_family_history_is_not_clinical_ascvd():
    parsed = parse_ingest_text("Clinical ASCVD: No. Father MI age 49.")

    assert parsed["clinical_ascvd"] is False
    assert parsed["family_history_premature_ascvd"] is True


def test_ascvd_calculator_failure_text_is_review_only_not_clinical_ascvd():
    report = parse_ingest_report(
        """
        Epic ASCVD calculator
        ASCVD Risk score failed to calculate because patient has a medical history suggesting prior/existing ASCVD
        Age: 67
        Sex: male
        BP 142/84
        TC 244
        HDL 38
        TG 180
        LDL 132
        Smoking status: Never
        Diabetes: No
        """
    )
    parsed = report["parsed"]
    state = {}
    apply_parsed_to_session_state(state, parsed, parse_report=report)
    patient = build_patient_from_inputs(parsed)
    result, _rss_total, _contributions = run_patient(patient)
    emr_note = render_emr_note(patient, result)
    recognition_html = render_parser_recognition_strip(report)

    assert parsed["clinical_ascvd"] is False
    assert parsed["clinical_ascvd_review"] is True
    assert state["input_clinical_ascvd"] is False
    assert result.clinical_ascvd is False
    assert result.prevention_context != "secondary_prevention_clinical_ascvd"
    assert result.risk_level != "Level 5"
    assert "Level: 5 - clinical ASCVD / secondary prevention" not in emr_note
    assert "secondary-prevention antiplatelet" not in emr_note.lower()
    assert "Possible ASCVD history; review" in recognition_html


def test_ascvd_calculator_review_does_not_suppress_explicit_event_evidence():
    parsed = parse_ingest_text(
        """
        ASCVD Risk score failed to calculate because patient has a medical history suggesting prior/existing ASCVD
        History of NSTEMI with PCI/stent.
        """
    )

    assert parsed["clinical_ascvd_review"] is True
    assert parsed["clinical_ascvd"] is True
    assert parsed["clinical_ascvd_context"] == "prior NSTEMI and PCI/stent"


def test_problem_list_conditions_fill_unknown_fields_without_confirming_ascvd():
    report = parse_ingest_report(
        """
        Clinical ASCVD: Unknown
        OSA: Unknown
        Diabetes: Unknown
        Problem List:
        - Coronary artery disease
        - Lacunar infarction
        - Type 2 diabetes mellitus
        - Obstructive sleep apnea
        - CKD stage 3
        - Fatty liver
        ASCVD Risk score failed to calculate because patient has a medical history suggesting prior/existing ASCVD
        """
    )
    parsed = report["parsed"]
    meta = report["meta"]
    recognition_html = render_parser_recognition_strip(report)

    assert parsed["clinical_ascvd"] is False
    assert parsed["clinical_ascvd_review"] is True
    assert parsed["osa"] is True
    assert parsed["diabetes"] is True
    assert parsed["masld"] is True
    assert parsed["ckd"] is True
    assert meta["clinical_ascvd_review"]["source"] == "Clinical ASCVD found in problem list; confirm."
    assert meta["clinical_ascvd_review"]["source_text"] == "Coronary artery disease"
    assert meta["clinical_ascvd_review"]["review_required"] == "true"
    assert meta["osa"]["source"] == "problem list diagnosis"
    assert meta["diabetes"]["source"] == "problem list diagnosis"
    assert meta["masld"]["source"] == "problem list diagnosis"
    assert "Possible ASCVD history; review" in recognition_html
    assert "OSA Yes" in recognition_html
    assert "MASLD Yes" in recognition_html
    assert report["conflicts"] == []


def test_problem_list_ascvd_does_not_activate_secondary_prevention():
    report = parse_ingest_report(
        """
        Age: 67
        Sex: male
        TC 210
        HDL 42
        LDL 132
        BP 142/84
        Problem List:
        - CAD
        - PAD
        - TIA
        """
    )
    parsed = report["parsed"]
    patient = build_patient_from_inputs(parsed)
    result, _rss_total, _contributions = run_patient(patient)

    assert parsed["clinical_ascvd"] is not True
    assert parsed["clinical_ascvd_review"] is True
    assert result.clinical_ascvd is False
    assert result.prevention_context != "secondary_prevention_clinical_ascvd"
    assert result.risk_level != "Level 5"


def test_problem_list_generic_family_history_is_review_not_premature():
    report = parse_ingest_report(
        """
        Problem list:
        - Family history of ischemic heart disease
        """
    )
    parsed = report["parsed"]
    recognition_html = render_parser_recognition_strip(report)

    assert parsed["family_history_review"] is True
    assert parsed.get("family_history_premature_ascvd") is not True
    assert "Family history of CAD; premature status not specified" in recognition_html


def test_problem_list_premature_family_history_is_review_without_detail():
    parsed = parse_ingest_text(
        """
        Problem list:
        - Family history of premature coronary artery disease
        """
    )

    assert parsed["family_history_premature_review"] is True
    assert parsed.get("family_history_premature_ascvd") is not True


def test_problem_list_family_history_detail_binds_relationship_event_age():
    parsed = parse_ingest_text(
        """
        Problem list:
        - Father MI age 49
        """
    )

    assert parsed["family_history_premature_ascvd"] is True
    assert parsed["family_history_relationship"] == "father"
    assert parsed["family_history_event_type"] == "mi"
    assert parsed["family_history_age_at_event"] == 49


def test_problem_list_suspected_sleep_apnea_is_review_not_osa():
    parsed = parse_ingest_text(
        """
        Problem list:
        - Suspected sleep apnea
        - Snoring
        - Hypersomnia
        """
    )

    assert parsed["sleep_apnea_review"] is True
    assert parsed.get("osa") is not True


def test_problem_list_confirmed_osa_sets_osa():
    parsed = parse_ingest_text(
        """
        Problem list:
        - Obstructive sleep apnea
        """
    )

    assert parsed["osa"] is True


def test_problem_list_sah_aneurysm_is_not_clinical_ascvd():
    parsed = parse_ingest_text(
        """
        Problem list:
        - Subarachnoid hemorrhage from aneurysm
        - Ruptured middle cerebral artery aneurysm
        """
    )

    assert parsed.get("clinical_ascvd") is not True
    assert parsed.get("ascvd_clinical") is not True
    assert parsed["cerebrovascular_review"] is True


def test_problem_list_diabetes_overrides_a1c_prediabetes_range():
    parsed = parse_ingest_text(
        """
        A1c: 6.1
        Problem list:
        - Type 2 diabetes mellitus with hyperglycemia
        """
    )

    assert parsed["a1c"] == 6.1
    assert parsed["diabetes"] is True
    assert parsed["diabetes_source"] == "problem_list"


def test_explicit_diabetes_no_beats_problem_list_diabetes_with_conflict():
    report = parse_ingest_report(
        """
        Diabetes: No
        Problem list:
        - Type 2 diabetes mellitus
        """
    )

    assert report["parsed"]["diabetes"] is False
    assert any("diabetes: explicit false vs problem list diagnosis" in conflict for conflict in report["conflicts"])


def test_problem_list_ckd_stage_conflict_keeps_lab_derived_stage_authority():
    report = parse_ingest_report(
        """
        eGFR: 16
        Urine ACR: 2417
        Problem list:
        - CKD stage 2
        """
    )
    parsed = report["parsed"]

    assert parsed["egfr"] == 16
    assert parsed["uacr"] == 2417
    assert parsed["ckd_stage_review"] is True
    assert any("labs show G4A3" in warning for warning in report["warnings"])


def test_problem_list_history_of_cancer_does_not_set_active_cancer():
    parsed = parse_ingest_text(
        """
        Problem list:
        - History of renal cell carcinoma
        """
    )

    assert parsed.get("active_cancer") is not True


def test_recommended_epic_template_placeholders_do_not_become_values():
    text = Path("tests/fixtures/ingest/recommended_epic_template_placeholders.txt").read_text(encoding="utf-8")
    report = parse_ingest_report(text)
    parsed = report["parsed"]

    assert parsed["lp_a_unit"] == "nmol/L"
    assert parsed["cac"] is None
    assert parsed["cac_not_done"] is True
    assert parsed["clinical_ascvd"] is None
    assert parsed["family_history_premature_ascvd"] is None
    for field in (
        "age",
        "sbp",
        "dbp",
        "bmi",
        "tc",
        "ldl_c",
        "hdl_c",
        "triglycerides",
        "apob",
        "lp_a_value",
        "a1c",
        "egfr",
        "uacr",
    ):
        assert field not in parsed or parsed[field] is None


def test_lpa_unit_on_following_epic_table_line_suppresses_unit_review():
    report = parse_ingest_report(
        """
        Lp(a):
        Lab Results
        Component Value Date
        LIPOA 148.2 (H) 05/22/2026
        nmol/L
        """
    )

    parsed = report["parsed"]
    assert parsed["lp_a_value"] == 148.2
    assert parsed["lp_a_unit"] == "nmol/L"
    assert "Confirm Lp(a) units." not in " ".join(report["warnings"])
    assert "Lp(a) value parsed without units" not in " ".join(report["warnings"])
    assert parsed.get("lp_a_review") is not True


def test_lpa_inline_units_are_normalized_and_missing_units_still_review():
    nmol = parse_ingest_report("Lp(a): 22.4 nmol/L")
    assert nmol["parsed"]["lp_a_value"] == 22.4
    assert nmol["parsed"]["lp_a_unit"] == "nmol/L"
    assert not any("Lp(a) value parsed without units" in warning for warning in nmol["warnings"])

    mgdl = parse_ingest_report("Lp(a): 56 mg/dL")
    assert mgdl["parsed"]["lp_a_value"] == 56
    assert mgdl["parsed"]["lp_a_unit"] == "mg/dL"
    assert not any("Lp(a) value parsed without units" in warning for warning in mgdl["warnings"])

    missing = parse_ingest_report("Lp(a): 180")
    assert missing["parsed"]["lp_a_value"] == 180
    assert "lp_a_unit" not in missing["parsed"]
    assert missing["parsed"]["lp_a_review"] is True
    assert any("Lp(a) value parsed without units" in warning for warning in missing["warnings"])


def test_explicit_osa_no_beats_problem_list_osa_with_conflict():
    report = parse_ingest_report(
        """
        OSA: No
        Problem List:
        - Obstructive sleep apnea
        """
    )

    assert report["parsed"]["osa"] is False
    assert any("osa: explicit false vs problem list diagnosis" in conflict for conflict in report["conflicts"])


def test_diabetes_no_with_high_a1c_creates_visible_conflict():
    report = parse_smartphrase_report("Diabetes: No. A1c 6.9.")

    assert report.extracted["diabetes"] is False
    assert any("A1c is >=6.5" in conflict for conflict in report.conflicts)


def test_explicit_unknown_boolean_lines_return_none():
    cases = [
        ("HIV: Unknown", [r"hiv"]),
        ("History of preeclampsia: Unknown", [r"preeclampsia"]),
        ("Current smoker: Unknown", [r"current\s+smoker", r"smoker"]),
        (
            "Premature ASCVD in first-degree relative: Unknown",
            [r"premature\s+ascvd\s+in\s+first[-\s]?degree\s+relative"],
        ),
        ("Family history not documented", [r"family\s+history"]),
    ]

    for text, labels in cases:
        assert parse_explicit_bool_line(text, labels) is None


def test_explicit_boolean_yes_no_still_parse():
    assert parse_explicit_bool_line("HIV: No", [r"hiv"]) is False
    assert parse_explicit_bool_line("HIV: Yes", [r"hiv"]) is True
    assert parse_explicit_bool_line("History of preeclampsia: No", [r"preeclampsia"]) is False
    assert parse_explicit_bool_line("History of preeclampsia: Yes", [r"preeclampsia"]) is True
    assert parse_explicit_bool_line("Current smoker: No", [r"current\s+smoker", r"smoker"]) is False
    assert parse_explicit_bool_line("Current smoker: Yes", [r"current\s+smoker", r"smoker"]) is True


def test_heavily_incomplete_unknowns_do_not_become_risk_factors():
    text = Path("tests/fixtures/ingest/heavily_incomplete_unknowns.txt").read_text(
        encoding="utf-8"
    )
    parsed = parse_ingest_text(text)

    unknown_fields = (
        "smoker",
        "diabetes",
        "bp_treated",
        "lipid_lowering",
        "clinical_ascvd",
        "family_history_premature_ascvd",
        "early_menopause",
        "preeclampsia",
        "gestational_hypertension",
        "gestational_diabetes",
        "preterm_delivery",
        "small_for_gestational_age",
        "recurrent_pregnancy_loss",
        "pcos_or_irregular_menses",
        "osa",
        "masld",
        "inflammatory_disease",
        "hiv",
        "rheumatoid_arthritis",
        "sle",
        "psoriasis",
        "ibd",
    )
    for field in unknown_fields:
        assert field in parsed
        assert parsed[field] is None

    patient = build_patient_from_inputs(parsed)
    result, rss_total, _contributions = run_patient(patient)
    recommendations = build_action_plan(patient, result)["recommendations"]
    emr_note = render_emr_note(patient, result)
    rss_labels = {item.label for item in get_rss_display_contributions(result)}

    assert result.prevent_available is False
    assert "diabetes status" in result.prevent_missing_inputs
    assert "smoking status" in result.prevent_missing_inputs
    assert "BP treatment status" in result.prevent_missing_inputs
    assert rss_total == 4
    assert rss_labels == {"Hypertriglyceridemia"}
    assert "3B" not in str(result.risk_level)

    forbidden_text = "\n".join(recommendations + [emr_note])
    assert "HIV" not in forbidden_text
    assert "smoking cessation" not in forbidden_text.lower()
    assert "premature family history" not in forbidden_text.lower()
    assert "Reproductive risk" not in forbidden_text
    assert "Gestational" not in forbidden_text
