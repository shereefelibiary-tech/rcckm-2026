from smartphrase_ingest.parser import parse_smartphrase_report
from ui.ingest_panel import parse_ingest_text


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
    assert parsed["inflammatory_disease"] is True


def test_family_history_is_not_clinical_ascvd():
    parsed = parse_ingest_text("Clinical ASCVD: No. Father MI age 49.")

    assert parsed["clinical_ascvd"] is False
    assert parsed["family_history_premature_ascvd"] is True


def test_diabetes_no_with_high_a1c_creates_visible_conflict():
    report = parse_smartphrase_report("Diabetes: No. A1c 6.9.")

    assert report.extracted["diabetes"] is False
    assert any("A1c is >=6.5" in conflict for conflict in report.conflicts)
