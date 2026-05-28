from smartphrase_ingest.coverage import build_parser_coverage_report
from smartphrase_ingest.feedback_queue import build_feedback_events
from smartphrase_ingest.pipeline import parse_to_draft
from smartphrase_ingest.profiles import ParserProfile, apply_profile_hints
from ui.ingest_panel import parse_ingest_report


def _item(report, field_id):
    return {item.field_id: item for item in report.recognition_items}[field_id]


def test_parser_coverage_detects_low_coverage_and_suggests_template():
    report = parse_ingest_report("LDL 132.")
    coverage = build_parser_coverage_report(report)

    assert coverage.total_core_fields == 11
    assert coverage.recognized_core_fields < 5
    assert coverage.confidence_score < 0.7
    assert "age" in coverage.missing_core_fields
    assert "Use the recommended Epic template structure" in coverage.suggestions[0]


def test_epic_placeholder_fixture_coverage_marks_unclear_family_and_missing_addons():
    with open("tests/fixtures/ingest/epic_placeholder_garbage_smartphrase.txt", encoding="utf-8") as fixture:
        report = parse_ingest_report(fixture.read())
    coverage = build_parser_coverage_report(report)

    assert coverage.recognized_core_fields == 11
    assert _item(coverage, "family_history").status == "review"
    assert _item(coverage, "cac").status == "review"
    assert _item(coverage, "apob").status == "missing"
    assert _item(coverage, "lp_a_value").status == "missing"
    assert _item(coverage, "uacr").status == "missing"
    assert "Use Yes / No / Unknown instead of *** for family history." in coverage.suggestions
    assert "Include most recent UACR result." in coverage.suggestions


def test_malformed_a1c_table_is_ambiguous_not_false_diabetes():
    report = parse_ingest_report(
        """
        Hemoglobin A1C
        Reference Range
        Normal <5.7%
        Prediabetes 5.7-6.4%
        Diabetes >6.4%
        """
    )
    coverage = build_parser_coverage_report(report)

    assert "a1c" not in report["parsed"]
    assert report["meta"]["a1c"]["confidence"] == "uncertain"
    assert "diabetes" not in report["parsed"]
    assert _item(coverage, "a1c").status == "review"
    assert "Use structured A1c table or explicit 'A1c: X.X' line." in coverage.suggestions


def test_unsupported_cac_format_generates_numeric_cac_suggestion():
    coverage = build_parser_coverage_report(parse_ingest_report("CAC category: high plaque burden."))

    assert _item(coverage, "cac").status in {"missing", "review"}
    assert "Include numeric CAC score if available." in coverage.suggestions


def test_parser_profile_field_alias_improves_extraction_without_rule_mutation():
    profile = ParserProfile(
        profile_id="clinic-a",
        source_system="epic",
        field_aliases={
            "HGBA1C RESULT": "a1c",
            "CT calcium score": "cac",
        },
    )
    without_profile = parse_ingest_report("HGBA1C RESULT: 6.1\nCT calcium score: 118")
    with_profile = parse_ingest_report("HGBA1C RESULT: 6.1\nCT calcium score: 118", profile=profile)

    assert without_profile["parsed"].get("a1c") is None
    assert with_profile["parsed"]["a1c"] == 6.1
    assert with_profile["parsed"]["cac"] == 118
    assert with_profile["parser_profile_id"] == "clinic-a"
    assert build_parser_coverage_report(with_profile).parser_profile_id == "clinic-a"


def test_profile_hints_preserve_validation_for_impossible_values():
    profile = ParserProfile(profile_id="clinic-a", field_aliases={"Patient age value": "age"})
    report = parse_ingest_report("Patient age value: 765", profile=profile)
    coverage = build_parser_coverage_report(report)

    assert "age" not in report["parsed"]
    assert _item(coverage, "age").status == "invalid"
    assert "age" in coverage.invalid_fields


def test_pipeline_accepts_profile_aliases_for_candidate_generation():
    profile = ParserProfile(profile_id="clinic-a", field_aliases={"HGBA1C RESULT": "a1c"})
    draft = parse_to_draft("HGBA1C RESULT: 6.2", profile=profile)

    assert draft.resolved["a1c"] == 6.2
    assert draft.resolved["prediabetes_context"] is True


def test_feedback_queue_captures_parser_misses_without_mutating_rules():
    coverage = build_parser_coverage_report(
        parse_ingest_report(
            """
            Age: 73
            Sex: male
            Premature ASCVD in first-degree relative: ***
            CAC score: ***
            ApoB: No results found for: APOB
            """
        ),
        parser_profile_id="clinic-a",
    )
    events = build_feedback_events(coverage, expected_behavior={"family_history": "Treat placeholder as unknown."})
    by_field = {event.field_name: event for event in events}

    assert by_field["family_history"].issue_type == "placeholder_detected"
    assert by_field["family_history"].expected_behavior == "Treat placeholder as unknown."
    assert by_field["cac"].issue_type == "placeholder_detected"
    assert by_field["apob"].issue_type == "missing_field"
    assert by_field["family_history"].parser_profile_id == "clinic-a"


def test_profile_alias_expansion_is_auditable_and_append_only():
    profile = ParserProfile(profile_id="clinic-a", field_aliases={"Glycohemoglobin": "a1c"})
    text = apply_profile_hints("Glycohemoglobin: 7.2", profile)

    assert "Glycohemoglobin: 7.2" in text
    assert "Parser profile normalized aliases:" in text
    assert "A1c: 7.2" in text
