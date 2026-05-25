from core.engine import evaluate_patient
from core.patient import Patient
from modules.actions.engine import build_action_plan
from modules.risk_enhancers.engine import identify_risk_enhancers
from modules.rss.engine import build_rss_contributions
from renderers.emr_renderer import render_emr_note
from renderers.patient_roadmap import render_patient_roadmap_text
from smartphrase_ingest.parser import parse_smartphrase_report


def labels(contributions):
    return {item.label for item in contributions if item.points > 0}


def test_higher_risk_ancestry_appears_as_context_not_diagnosis():
    patient = Patient(age=48, sex="female", south_asian_ancestry=True, filipino_ancestry=True)
    result = evaluate_patient(patient)
    rss_labels = labels(build_rss_contributions(patient, result))
    enhancers = identify_risk_enhancers(patient)
    emr = render_emr_note(patient, result)
    roadmap = render_patient_roadmap_text(patient, result)

    assert "South Asian ancestry" in rss_labels
    assert "Filipino ancestry" in rss_labels
    assert "Higher-risk ancestry/context: South Asian ancestry" in enhancers
    assert "Higher-risk ancestry/context: Filipino ancestry" in enhancers
    assert "risk-enhancing ancestry/context: South Asian ancestry; Filipino ancestry" in emr
    assert "South Asian ancestry" in roadmap
    assert "Assessment:" not in emr or "South Asian ancestry" not in emr.split("Assessment:", 1)[-1]


def test_hiv_stable_art_triggers_specific_pathway_but_unknown_does_not():
    patient = Patient(age=55, sex="male", hiv=True, stable_art=True)
    result = evaluate_patient(patient)
    plan = build_action_plan(patient, result)

    assert "HIV" in labels(build_rss_contributions(patient, result))
    assert "HIV on stable ART" in identify_risk_enhancers(patient)
    assert plan["dominant_action"] == "Statin therapy recommended/reasonable in HIV; review ART-statin interactions."

    report = parse_smartphrase_report("HIV: Unknown\nStable ART: Unknown")
    unknown_patient = Patient(age=55, sex="male", **report.extracted)
    unknown_result = evaluate_patient(unknown_patient)
    unknown_plan = build_action_plan(unknown_patient, unknown_result)

    assert report.extracted["hiv"] is None
    assert report.extracted["stable_art"] is None
    assert "HIV" not in labels(build_rss_contributions(unknown_patient, unknown_result))
    assert "HIV" not in " ".join(unknown_plan["recommendations"])


def test_inflammatory_conditions_yes_no_unknown_are_specific_and_hiv_separate():
    report = parse_smartphrase_report(
        "RA: Yes\nSLE: No\nPsoriasis: Unknown\nInflammatory arthritis: Yes\nIBD: No\nHIV: Yes\nInflammatory disease: No"
    )
    parsed = report.extracted

    assert parsed["rheumatoid_arthritis"] is True
    assert parsed["sle"] is False
    assert parsed["psoriasis"] is None
    assert parsed["inflammatory_arthritis"] is True
    assert parsed["ibd"] is False
    assert parsed["hiv"] is True
    assert parsed["inflammatory_disease"] is True
    assert any("specific condition present" in conflict for conflict in report.conflicts)

    patient = Patient(age=55, sex="male", hiv=True, inflammatory_disease=False)
    result = evaluate_patient(patient)
    rss = build_rss_contributions(patient, result)
    assert "HIV" in labels(rss)
    assert all(item.domain != "Inflammatory Disease" for item in rss if item.label == "HIV")


def test_reproductive_no_unknown_does_not_create_false_positive_sga():
    report = parse_smartphrase_report(
        "Small for gestational age infant: No\n"
        "Gestational diabetes: Unknown\n"
        "Preeclampsia: Unknown\n"
        "Early menopause: No"
    )
    patient = Patient(age=45, sex="female", **report.extracted)
    result = evaluate_patient(patient)
    text = render_emr_note(patient, result) + "\n" + render_patient_roadmap_text(patient, result)

    assert report.extracted["small_for_gestational_age"] is False
    assert report.extracted["gestational_diabetes"] is None
    assert report.extracted["preeclampsia"] is None
    assert "SGA infant" not in labels(build_rss_contributions(patient, result))
    assert "SGA infant" not in text


def test_suspected_fh_and_ldl_190_cac0_remain_treatment_forward():
    patient = Patient(age=42, sex="male", ldl_c=204, apob=142, cac=0, suspected_fh_hefh=True)
    result = evaluate_patient(patient)
    emr = render_emr_note(patient, result)

    assert result.possible_fh_pathway is True
    assert result.level_classification["level"] == "3B"
    assert "High-intensity or maximally tolerated statin indicated." in emr
    assert "do not use CAC 0 to defer lipid-lowering therapy" in emr
    assert "PREVENT should not be used to de-risk LDL-C >=190 pathway." in emr


def test_incidental_cac_creates_qualitative_plaque_context_without_score():
    patient = Patient(age=62, sex="female", incidental_cac=True, incidental_cac_severity="severe")
    result = evaluate_patient(patient)
    rss = build_rss_contributions(patient, result)
    emr = render_emr_note(patient, result)

    assert any(item.label == "Incidental CAC" and item.actual_value == "severe on noncardiac CT" for item in rss)
    assert "incidental CAC noted (severe)" in emr
    assert "CAC 0" not in emr


def test_cancer_survivor_is_context_only_unless_otherwise_treatment_eligible():
    patient = Patient(age=52, sex="female", cancer_survivor=True, cancer_life_expectancy_gt_2y=True)
    result = evaluate_patient(patient)
    plan = build_action_plan(patient, result)
    emr = render_emr_note(patient, result)

    assert "Cancer survivor context; life expectancy >2 years" in identify_risk_enhancers(patient)
    assert "cancer survivor context with life expectancy >2 years" in emr
    assert "cancer" not in " ".join(plan["recommendations"]).lower()


def test_prevent_category_remains_separate_from_rcckm_level_with_enhancers():
    patient = Patient(
        age=54,
        sex="female",
        sbp=132,
        dbp=78,
        bp_treated=True,
        tc=220,
        hdl_c=50,
        ldl_c=136,
        triglycerides=198,
        apob=106,
        a1c=6.0,
        lp_a_value=132,
        lp_a_unit="nmol/L",
        early_menopause=True,
        gestational_hypertension=True,
        prevent_10y_ascvd=3.42,
        prevent_30y_ascvd=17.53,
    )
    result = evaluate_patient(patient)
    emr = render_emr_note(patient, result)

    assert result.level_classification["level"] == "3B"
    assert str(result.prevent_risk_category.value).lower() == "borderline"
    assert "Level 3B" in emr
    assert "PREVENT 10-year risk 3.42%" in emr
