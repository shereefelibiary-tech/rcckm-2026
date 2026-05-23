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

    assert "Parse coverage" in html
    assert "Age" in html
    assert "55" in html
    assert "Systolic BP" in html
    assert "132 mmHg" in html
    assert "LDL-C" in html
    assert "132 mg/dL" in html
    assert "Lp(a)" in html
    assert "80 nmol/L" in html
    assert "A1c" in html
    assert "7.1%" in html
    assert "Medication names detected" in html
    assert "metformin, empagliflozin, losartan" in html
    assert "parse-chip-found" in html
    assert "<div class=" not in html.replace("<div class=\"", "")


def test_parse_coverage_missing_fields_are_muted_after_parse():
    report = parse_ingest_report("Age 55. Sex male. LDL 132.")

    html = render_parse_coverage(report)

    assert "Triglycerides" in html
    assert "not found" in html
    assert "parse-chip-missing" in html


def test_parse_coverage_conflict_chip_for_conflicting_parser_output():
    report = parse_smartphrase_report("No diabetes. A1c 7.1.")

    html = render_parse_coverage(report)

    assert "Conflict:" in html
    assert "diabetes" in html
    assert "parse-chip-conflict" in html


def test_parse_coverage_unavailable_reasons_show_verify_chip():
    report = parse_ingest_report(
        "eGFR unavailable due to lab interface failure. UACR not done because no urine sample. LDL 132."
    )

    html = render_parse_coverage(report)

    assert "Verify:" in html
    assert "lab interface failure" in html
    assert "no urine sample" in html
    assert "parse-chip-verify" in html


def test_parse_coverage_medication_detection_appears():
    report = parse_ingest_report("Meds: rosuvastatin 10 mg nightly, Ozempic 0.5 mg weekly.")

    html = render_parse_coverage(report)

    assert "Medication names detected" in html
    assert "rosuvastatin, semaglutide" in html
    assert "Lipid-lowering therapy" in html
    assert "GLP-1/GIP" in html


def test_parse_coverage_has_no_raw_json_dump():
    report = ParseReport(extracted={"age": 55}, field_meta={"age": {"confidence": "parsed", "source": "test"}})

    html = render_parse_coverage(report)

    assert '"extracted"' not in html
    assert '"field_meta"' not in html
    assert "Raw parsed JSON" not in html
