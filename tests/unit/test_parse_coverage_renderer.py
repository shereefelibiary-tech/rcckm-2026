from renderers.parse_coverage import render_parse_coverage
from smartphrase_ingest.parser import ParseReport, parse_smartphrase_report
from ui.ingest_panel import parse_ingest_report


def test_parse_coverage_empty_state_is_compact():
    html = render_parse_coverage(None)

    assert "Nothing parsed yet." in html
    assert "Age" not in html
    assert "<div class=\"parse-row\"" not in html


def test_parse_coverage_complete_demo_shows_found_values():
    report = parse_ingest_report(
        """
        55M BP 132/82 TC 205 LDL 132 HDL 48 TG 180.
        ApoB 110. Lp(a) 80 nmol/L. A1c 7.1.
        eGFR 55. UACR 45 mg/g. Creatinine 1.15. CAC 350.
        Father MI age 49. No diabetes. Never smoker.
        Meds: losartan 50 mg daily, metformin, Jardiance 10 mg daily.
        """
    )

    html = render_parse_coverage(report)

    assert "Parsed" in html
    assert "Smartphrase understood" not in html
    assert "Core fields recognized:" in html
    assert "Core essentials" in html
    assert "Important risk enhancers" in html
    assert "Advanced/contextual" in html
    assert html.index("Core essentials") < html.index("Important risk enhancers") < html.index("Advanced/contextual")
    assert "Age" in html
    assert "55" in html
    assert "BP" in html
    assert "132/82" in html
    assert "LDL-C" in html
    assert "132 mg/dL" in html
    assert "Lp(a)" in html
    assert "80 nmol/L" in html
    assert "A1c" in html
    assert "7.1%" in html
    assert "Current medications" in html
    assert "metformin, empagliflozin, losartan" in html
    assert "parse-item-found" in html
    assert "&#10003;" in html
    assert "<div class=" not in html.replace("<div class=\"", "")


def test_parse_coverage_missing_fields_are_muted_after_parse():
    report = parse_ingest_report("Age 55. Sex male. LDL 132.")

    html = render_parse_coverage(report)

    assert "Core fields recognized:" in html
    assert "Generic EMR text detected. Some fields may need review." in html
    assert "TG" in html
    assert "not found" in html
    assert "parse-item-missing" in html
    assert "&#9675;" in html


def test_parse_coverage_conflict_chip_for_conflicting_parser_output():
    report = parse_smartphrase_report("No diabetes. A1c 7.1.")

    html = render_parse_coverage(report)

    assert "diabetes" in html
    assert "parse-item-conflict" in html
    assert "parse-notice-conflict" in html


def test_parse_coverage_unavailable_reasons_show_verify_chip():
    report = parse_ingest_report(
        "eGFR unavailable due to lab interface failure. UACR not done because no urine sample. LDL 132."
    )

    html = render_parse_coverage(report)

    assert "lab interface failure" in html
    assert "no urine sample" in html
    assert "parse-notice-review" in html


def test_parse_coverage_medication_detection_appears():
    report = parse_ingest_report("Meds: rosuvastatin 10 mg nightly, Ozempic 0.5 mg weekly.")

    html = render_parse_coverage(report)

    assert "Current medications" in html
    assert "rosuvastatin, semaglutide" in html
    assert "parse-item-found" in html


def test_parse_coverage_has_no_raw_json_dump():
    report = ParseReport(extracted={"age": 55}, field_meta={"age": {"confidence": "parsed", "source": "test"}})

    html = render_parse_coverage(report)

    assert '"extracted"' not in html
    assert '"field_meta"' not in html
    assert "Raw parsed JSON" not in html


def test_parse_coverage_epic_placeholder_fixture_is_calm_and_ordered():
    fixture_path = "tests/fixtures/ingest/epic_placeholder_garbage_smartphrase.txt"
    with open(fixture_path, encoding="utf-8") as fixture:
        report = parse_ingest_report(fixture.read())

    html = render_parse_coverage(report)

    assert "Parsed" in html
    assert "Smartphrase understood" not in html
    assert "BP" in html
    assert "132/77" in html
    assert "BMI" in html
    assert "30.81" in html
    assert "A1c" in html
    assert "5.8%" in html
    assert "LDL-C" in html
    assert "90 mg/dL" in html
    assert "ApoB" in html
    assert "ApoB missing" in html
    assert "Add ApoB for atherogenic burden interpretation." in html
    assert "Lp(a)" in html
    assert "Lp(a) missing" in html
    assert "Add Lp(a) for inherited lipid-risk context." in html
    assert "Family history" in html
    assert "parse-item-review" in html
    assert "parse-item-missing" in html
    assert "Core fields recognized: 11/11" in html
