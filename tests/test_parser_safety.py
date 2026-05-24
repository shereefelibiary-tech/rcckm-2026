from pathlib import Path

from smartphrase_ingest.parser import parse_explicit_bool_line, parse_smartphrase_report
from ui.ingest_panel import parse_ingest_text
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
    assert parsed["inflammatory_disease"] is True


def test_family_history_is_not_clinical_ascvd():
    parsed = parse_ingest_text("Clinical ASCVD: No. Father MI age 49.")

    assert parsed["clinical_ascvd"] is False
    assert parsed["family_history_premature_ascvd"] is True


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
