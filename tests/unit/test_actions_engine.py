from core.patient import Patient
from core.results import RCCKMResult
from modules.actions.engine import build_action_plan


def test_build_action_plan_prioritizes_lipid_action_for_high_cac():
    patient = Patient(age=60, sex="male", cac=350, a1c=7.1)

    plan = build_action_plan(patient, RCCKMResult())

    assert (
        plan["dominant_action"]
        == "Lipid-lowering therapy is indicated; treat toward high-risk targets."
    )
    assert (
        plan["recommendations"][0]
        == "Lipid-lowering therapy is indicated; treat toward high-risk targets."
    )
    assert (
        plan["domains"]["lipids"]
        == "Lipid-lowering therapy is indicated; treat toward high-risk targets."
    )


def test_build_action_plan_uses_kidney_action_for_diabetes_ckd():
    patient = Patient(age=60, sex="male", diabetes=True, egfr=55, uacr=45)
    result = RCCKMResult(egfr_stage="G3a", albuminuria_stage="A2")

    plan = build_action_plan(patient, result)

    assert plan["dominant_action"] == "Optimize kidney-protective therapy."
    assert plan["domains"]["kidney"] == "Optimize kidney-protective therapy."


def test_build_action_plan_uses_glycemic_action_for_a1c_7():
    patient = Patient(age=60, sex="male", a1c=7.0)

    plan = build_action_plan(patient, RCCKMResult())

    assert plan["dominant_action"] == "Optimize glycemic therapy."
    assert plan["domains"]["glycemia"] == "Optimize glycemic therapy."


def test_build_action_plan_uses_bp_action_when_bp_above_target():
    patient = Patient(age=60, sex="male", sbp=132, dbp=78)

    plan = build_action_plan(patient, RCCKMResult())

    assert plan["dominant_action"] == "Optimize BP to <130/80."
    assert plan["domains"]["blood_pressure"] == "Optimize BP to <130/80."


def test_build_action_plan_suppresses_borderline_untreated_bp_line():
    patient = Patient(age=60, sex="male", sbp=130, dbp=80, bp_treated=False)

    plan = build_action_plan(patient, RCCKMResult())

    assert "blood_pressure" not in plan["domains"]


def test_build_action_plan_uses_tg_action_for_severe_hypertriglyceridemia():
    patient = Patient(age=60, sex="male", triglycerides=500)

    plan = build_action_plan(patient, RCCKMResult())

    assert (
        plan["dominant_action"]
        == "Severe hypertriglyceridemia: lower TG to reduce pancreatitis risk; evaluate secondary causes and consider fibrate or prescription omega-3 therapy."
    )
    assert (
        plan["domains"]["triglycerides"]
        == "Severe hypertriglyceridemia: lower TG to reduce pancreatitis risk; evaluate secondary causes and consider fibrate or prescription omega-3 therapy."
    )


def test_build_action_plan_uses_tg_action_for_very_severe_hypertriglyceridemia():
    patient = Patient(age=60, sex="male", triglycerides=1000)

    plan = build_action_plan(patient, RCCKMResult())

    assert (
        plan["dominant_action"]
        == "Very severe hypertriglyceridemia: lower TG to reduce pancreatitis risk."
    )
    assert (
        plan["domains"]["triglycerides"]
        == "Very severe hypertriglyceridemia: lower TG to reduce pancreatitis risk."
    )
    assert "Very-low-fat diet; eliminate alcohol and added sugars/refined carbohydrates." in plan["recommendations"]
    assert "Refer to registered dietitian nutritionist." in plan["recommendations"]
    assert "Consider fibrate or prescription omega-3 therapy to lower TG." in plan["recommendations"]
    assert "Recheck fasting lipid profile after treatment changes." in plan["recommendations"]


def test_build_action_plan_uses_non_hdl_apob_when_ldl_not_calculable_from_tg():
    patient = Patient(
        age=55,
        sex="male",
        tc=286,
        hdl_c=32,
        triglycerides=1040,
        ldl_c=None,
        apob=138,
        diabetes=True,
        a1c=8.2,
        lipid_lowering=False,
    )
    patient.non_hdl_c = 254

    plan = build_action_plan(patient, RCCKMResult())

    assert "Address ASCVD risk with lipid-lowering therapy guided by non-HDL-C/ApoB." in plan["recommendations"]
    assert plan["domains"]["lipids"] == "Address ASCVD risk with lipid-lowering therapy guided by non-HDL-C/ApoB."


def test_clinical_ascvd_above_target_intensifies_secondary_prevention():
    patient = Patient(age=60, sex="male", clinical_ascvd=True, ldl_c=132, non_hdl_c=160, apob=105)
    result = RCCKMResult()
    from modules.targets.engine import build_target_result

    result.targets = [build_target_result(patient)]

    plan = build_action_plan(patient, result)

    assert plan["dominant_action"] == "Intensify secondary-prevention lipid-lowering therapy; treat toward ASCVD targets."


def test_hiv_pathway_uses_specific_statin_wording():
    plan = build_action_plan(Patient(age=55, sex="male", hiv=True), RCCKMResult())

    assert plan["dominant_action"] == "Statin therapy reasonable in HIV; review antiretroviral drug interactions."


def test_triglyceride_action_boundaries():
    assert "triglycerides" not in build_action_plan(
        Patient(age=60, sex="male", triglycerides=499),
        RCCKMResult(),
    )["domains"]

    for tg in (500, 999):
        plan = build_action_plan(Patient(age=60, sex="male", triglycerides=tg), RCCKMResult())
        assert plan["domains"]["triglycerides"].startswith("Severe hypertriglyceridemia")
        assert "fibrate or prescription omega-3" in plan["domains"]["triglycerides"]

    plan = build_action_plan(Patient(age=60, sex="male", triglycerides=1000), RCCKMResult())
    assert plan["domains"]["triglycerides"] == "Very severe hypertriglyceridemia: lower TG to reduce pancreatitis risk."
    assert "Very-low-fat diet; eliminate alcohol and added sugars/refined carbohydrates." in plan["recommendations"]


def test_build_action_plan_uses_clarification_when_no_treatment_escalation():
    result = RCCKMResult(
        prevent_risk_category="INTERMEDIATE",
        clarification={
            "tier": 2,
            "recommend_cac": True,
        }
    )

    plan = build_action_plan(Patient(age=60, sex="male"), result)

    assert plan["dominant_action"] == "Check Lp(a) once."
    assert "CAC reasonable for risk clarification if treatment decision remains uncertain." in plan["recommendations"]
    assert (
        plan["domains"]["cac_testing"]
        == "CAC reasonable for risk clarification if treatment decision remains uncertain."
    )


def test_build_action_plan_returns_no_escalation_when_no_signal():
    plan = build_action_plan(
        Patient(age=60, sex="male", lp_a_value=20, lp_a_unit="nmol/L"),
        RCCKMResult(),
    )

    assert plan == {
        "dominant_action": "No escalation indicated.",
        "recommendations": ["No escalation indicated."],
        "domains": {"none": "No escalation indicated."},
    }


def test_build_action_plan_limits_recommendations_to_four_by_priority():
    patient = Patient(
        age=60,
        sex="male",
        cac=350,
        diabetes=True,
        egfr=55,
        uacr=45,
        a1c=7.1,
        sbp=140,
        triglycerides=500,
    )
    result = RCCKMResult(
        egfr_stage="G3a",
        albuminuria_stage="A2",
        clarification={
            "tier": 2,
            "summary": "Next useful clarifier(s): ApoB.",
        },
    )

    plan = build_action_plan(patient, result)

    assert plan["recommendations"] == [
        "Lipid-lowering therapy is indicated; treat toward high-risk targets.",
        "Optimize kidney-protective therapy.",
        "Optimize glycemic therapy.",
        "Clarification testing should not delay treatment.",
    ]
    assert len(plan["recommendations"]) == 4
    assert "triglycerides" not in plan["domains"]
    assert "clarification" not in plan["domains"]


def test_build_action_plan_adds_testing_after_treatment_actions():
    patient = Patient(age=60, sex="male", a1c=7.0, ldl_c=160, apob=None)

    plan = build_action_plan(patient, RCCKMResult())

    assert plan["recommendations"] == [
        "Optimize glycemic therapy.",
        "Obtain ApoB to define atherogenic particle burden.",
        "Check Lp(a) once.",
        "Obtain UACR to complete kidney-risk assessment.",
    ]
    assert "cac_testing" not in plan["domains"]


def test_build_action_plan_adds_cac_for_borderline_risk_with_premature_family_history():
    patient = Patient(
        age=60,
        sex="male",
        lp_a_value=20,
        lp_a_unit="nmol/L",
        premature_fhx_ascvd=True,
    )

    plan = build_action_plan(patient, RCCKMResult(prevent_risk_category="BORDERLINE"))

    assert plan["dominant_action"] == "CAC reasonable for risk clarification if treatment decision remains uncertain."
    assert plan["domains"]["cac_testing"] == "CAC reasonable for risk clarification if treatment decision remains uncertain."


def test_build_action_plan_adds_uacr_for_diabetes_and_kidney_uncertainty():
    patient = Patient(
        age=60,
        sex="male",
        diabetes=True,
        uacr=None,
        lp_a_value=20,
        lp_a_unit="nmol/L",
    )

    plan = build_action_plan(patient, RCCKMResult())

    assert "Obtain UACR to complete kidney-risk assessment." in plan["recommendations"]
    assert plan["domains"]["uacr_testing"] == "Obtain UACR to complete kidney-risk assessment."


def test_build_action_plan_adds_hscrp_for_metabolic_or_family_history_context():
    patient = Patient(
        age=60,
        sex="male",
        bmi=32,
        lp_a_value=20,
        lp_a_unit="nmol/L",
    )

    plan = build_action_plan(patient, RCCKMResult())

    assert "Consider hsCRP to clarify inflammatory residual risk." in plan["recommendations"]
    assert (
        plan["domains"]["hscrp_testing"]
        == "Consider hsCRP to clarify inflammatory residual risk."
    )


def test_build_action_plan_adds_repeat_fasting_lipids_for_tg_uncertainty():
    patient = Patient(
        age=60,
        sex="male",
        triglycerides=420,
        lp_a_value=20,
        lp_a_unit="nmol/L",
    )

    plan = build_action_plan(patient, RCCKMResult())

    assert (
        "Repeat fasting lipid panel to confirm severe hypertriglyceridemia."
        in plan["recommendations"]
    )
