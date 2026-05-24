from core.enums import RiskLevel
from core.patient import Patient
from core.results import RCCKMResult
from modules.actions.engine import build_action_plan
from modules.risk_enhancers.reproductive import reproductive_history_summary
from modules.rss.engine import get_rss_contributors
from renderers.patient_roadmap import render_patient_roadmap_text
from renderers.rss_renderer import build_rss_panel_html, get_rss_display_items
from renderers.where_patient_falls import build_where_patient_falls_html
from smartphrase_ingest.parser import parse_smartphrase_report
from ui.ingest_panel import apply_parsed_to_session_state, parse_ingest_report
from ui.report_layout import run_patient


def test_parser_detects_early_menopause_from_age():
    report = parse_smartphrase_report("Female. Menopause at age 43.")

    assert report.extracted["menopause_age"] == 43
    assert report.extracted["early_menopause"] is True
    assert report.extracted["premature_menopause"] is False


def test_parser_detects_preeclampsia_and_preserves_negations():
    report = parse_smartphrase_report(
        """
        Preeclampsia: Yes
        Gestational hypertension: No
        No PCOS
        """
    )

    assert report.extracted["preeclampsia"] is True
    assert report.extracted["gestational_hypertension"] is False
    assert report.extracted["pcos_or_irregular_menses"] is False


def test_gestational_diabetes_does_not_equal_current_diabetes():
    report = parse_smartphrase_report(
        """
        Gestational diabetes: Yes
        Diabetes: No
        A1c 5.4%
        """
    )

    assert report.extracted["gestational_diabetes"] is True
    assert report.extracted["diabetes"] is False


def test_reproductive_marker_stacks_in_rss_and_roadmap_context():
    patient = Patient(age=52, sex="female", menopause_age=43)
    result, rss_total, contributions = run_patient(patient)
    html = build_rss_panel_html(rss_total, contributions, result)
    display = get_rss_display_items(result, contributions, rss_total)
    tower = html.split('<div class="rss-tower">', 1)[1].split('<div class="rss-drivers">', 1)[0]
    rows = html.split('<div class="rss-driver-list">', 1)[1]
    roadmap = render_patient_roadmap_text(patient, result)

    assert any(item.label == "Early menopause" for item in get_rss_contributors(result))
    assert rss_total == 2
    assert sum(item["points"] for item in display["contributors"] if item["stack_in_tower"]) == rss_total
    assert "Early menopause age 43" in tower
    assert "Early menopause age 43" in rows
    assert "Early menopause 43" in roadmap
    assert "Pregnancy or menopause history can affect long-term heart risk." in roadmap


def test_where_patient_falls_shows_reproductive_history_domain_when_present():
    patient = Patient(age=48, sex="female", preeclampsia=True)
    result, _rss_total, _contributions = run_patient(patient)

    html = build_where_patient_falls_html(patient, result)

    assert "REPRODUCTIVE HISTORY" in html
    assert "Preeclampsia" in html
    assert "mild signal" in html


def test_male_patient_without_markers_does_not_show_reproductive_history():
    patient = Patient(age=48, sex="male")
    result, _rss_total, _contributions = run_patient(patient)

    html = build_where_patient_falls_html(patient, result)

    assert "REPRODUCTIVE HISTORY" not in html


def test_borderline_prevent_with_reproductive_marker_supports_lipid_discussion():
    patient = Patient(age=48, sex="female", preeclampsia=True)
    result = RCCKMResult(prevent_risk_category=RiskLevel.BORDERLINE)

    plan = build_action_plan(patient, result)

    assert plan["dominant_action"] == "Risk discussion reasonable; consider lipid-lowering therapy."


def test_negative_reproductive_history_does_not_score_rss():
    report = parse_smartphrase_report(
        """
        Early menopause: No
        Preeclampsia: No
        Gestational hypertension: No
        Gestational diabetes: No
        Preterm delivery: No
        Small for gestational age infant: No
        SGA infant: No
        No small-for-gestational-age infant
        Recurrent pregnancy loss: No
        Recurrent miscarriage: No
        PCOS: No
        """
    )
    patient = Patient(
        age=48,
        sex="female",
        early_menopause=report.extracted["early_menopause"],
        preeclampsia=report.extracted["preeclampsia"],
        gestational_hypertension=report.extracted["gestational_hypertension"],
        gestational_diabetes=report.extracted["gestational_diabetes"],
        preterm_delivery=report.extracted["preterm_delivery"],
        small_for_gestational_age=report.extracted["small_for_gestational_age"],
        recurrent_pregnancy_loss=report.extracted["recurrent_pregnancy_loss"],
        pcos_or_irregular_menses=report.extracted["pcos_or_irregular_menses"],
    )
    result, rss_total, _contributions = run_patient(patient)

    assert report.extracted["preterm_delivery"] is False
    assert report.extracted["small_for_gestational_age"] is False
    assert report.extracted["pcos_or_irregular_menses"] is False
    assert rss_total == 0
    assert not get_rss_contributors(result)


def test_rebecca_demo_reproductive_negatives_do_not_become_rss_contributors():
    report = parse_smartphrase_report(
        """
        Female.
        Menopause at age 44.
        Preeclampsia: Yes
        Gestational hypertension: Yes
        Gestational diabetes: No
        Preterm delivery: No
        Small for gestational age infant: No
        Recurrent pregnancy loss: No
        PCOS: No
        """
    )
    patient = Patient(age=52, sex="female", **report.extracted)
    result, rss_total, contributions = run_patient(patient)
    html = build_rss_panel_html(rss_total, contributions, result)
    labels = [item.label for item in get_rss_contributors(result)]

    assert report.extracted["early_menopause"] is True
    assert report.extracted["preeclampsia"] is True
    assert report.extracted["gestational_hypertension"] is True
    assert report.extracted["gestational_diabetes"] is False
    assert report.extracted["preterm_delivery"] is False
    assert report.extracted["small_for_gestational_age"] is False
    assert report.extracted["recurrent_pregnancy_loss"] is False
    assert report.extracted["pcos_or_irregular_menses"] is False
    assert "Early menopause" in labels
    assert "Preeclampsia" in labels
    assert "Gestational hypertension" in labels
    assert "Gestational diabetes" not in labels
    assert "Preterm delivery" not in labels
    assert "SGA infant" not in labels
    assert "Recurrent pregnancy loss" not in labels
    assert "PCOS / irregular menses" not in labels
    assert "SGA infant" not in html


def test_rebecca_demo_reproductive_summary_excludes_explicit_negative_sga():
    report = parse_smartphrase_report(
        """
        Early menopause: Yes
        Menopause at age 44
        History of preeclampsia: Yes
        Gestational hypertension: Yes
        Gestational diabetes: No
        Preterm delivery: No
        Small for gestational age infant: No
        Recurrent pregnancy loss: No
        PCOS: No
        """
    )
    patient = Patient(age=52, sex="female", **report.extracted)

    assert reproductive_history_summary(patient) == "Early menopause 44; Preeclampsia; Gestational hypertension"


def test_sga_explicit_negative_variants_parse_false():
    examples = [
        "Small for gestational age infant: No",
        "Small-for-gestational-age infant: No",
        "SGA infant: No",
        "SGA: No",
        "No small-for-gestational-age infant",
        "Denies history of SGA infant",
    ]

    for text in examples:
        report = parse_smartphrase_report(text)
        assert report.extracted["small_for_gestational_age"] is False


def test_positive_sga_fixture_scores_as_tiny_reproductive_contributor():
    report = parse_smartphrase_report("Female. SGA infant: Yes.")
    patient = Patient(age=48, sex="female", **report.extracted)
    result, rss_total, contributions = run_patient(patient)
    html = build_rss_panel_html(rss_total, contributions, result)
    display = get_rss_display_items(result, contributions, rss_total)

    assert report.extracted["small_for_gestational_age"] is True
    assert any(item.label == "SGA infant" and item.points == 2 for item in get_rss_contributors(result))
    assert 'data-rss-id="small_for_gestational_age"' in html
    assert sum(item["points"] for item in display["contributors"] if item["stack_in_tower"]) == rss_total


def test_reproductive_summary_does_not_treat_string_false_as_present():
    patient = Patient(
        age=52,
        sex="female",
        early_menopause="True",
        menopause_age=44,
        small_for_gestational_age="False",
        gestational_diabetes="no",
    )

    assert reproductive_history_summary(patient) == "Early menopause 44"


def test_sga_parse_apply_back_to_back_clears_prior_true():
    state = {}
    yes_report = parse_ingest_report("Small for gestational age infant: Yes")
    no_report = parse_ingest_report("Small for gestational age infant: No")

    apply_parsed_to_session_state(state, yes_report["parsed"])
    assert state["input_small_for_gestational_age"] is True

    apply_parsed_to_session_state(state, no_report["parsed"])
    assert state["input_small_for_gestational_age"] is False


def test_reproductive_false_values_overwrite_prior_true_session_state():
    state = {
        "input_small_for_gestational_age": True,
        "input_gestational_diabetes": True,
        "input_preterm_delivery": True,
        "input_pcos_or_irregular_menses": True,
    }
    report = parse_ingest_report(
        """
        Small for gestational age infant: No
        Gestational diabetes: No
        Preterm delivery: No
        PCOS: No
        """
    )

    apply_parsed_to_session_state(state, report["parsed"], clear_existing=False)

    assert state["input_small_for_gestational_age"] is False
    assert state["input_gestational_diabetes"] is False
    assert state["input_preterm_delivery"] is False
    assert state["input_pcos_or_irregular_menses"] is False
