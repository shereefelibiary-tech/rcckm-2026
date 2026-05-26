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

    assert plan["dominant_action"] == (
        "Confirm persistent albuminuria with repeat UACR if not already confirmed; optimize kidney-protective therapy."
    )
    assert plan["domains"]["kidney"] == (
        "Confirm persistent albuminuria with repeat UACR if not already confirmed; optimize kidney-protective therapy."
    )


def test_albuminuria_with_elevated_bp_uses_kidney_protective_action_not_passive_plan():
    patient = Patient(
        age=57,
        sex="male",
        sbp=142,
        dbp=86,
        bp_treated=True,
        egfr=64,
        uacr=48,
        a1c=6.0,
        triglycerides=150,
    )
    result = RCCKMResult(
        egfr_stage="G2",
        albuminuria_stage="A2",
        prevent_risk_category="INTERMEDIATE",
        level_classification={"level": "3B"},
    )

    plan = build_action_plan(patient, result)

    assert "No escalation indicated." not in plan["recommendations"]
    assert plan["domains"]["kidney"] == (
        "Confirm persistent albuminuria with repeat UACR if not already confirmed; optimize kidney-protective therapy."
    )
    assert plan["domains"]["blood_pressure"] == (
        "Treat BP toward goal <130/80 if tolerated."
    )
    assert "ACEi/ARB" in plan["domains"]["ace_arb"]


def test_albuminuria_with_intermediate_risk_adds_statin_prevention_language():
    patient = Patient(
        age=57,
        sex="male",
        sbp=142,
        dbp=86,
        bp_treated=True,
        egfr=64,
        uacr=48,
        a1c=6.0,
        triglycerides=150,
    )
    result = RCCKMResult(
        egfr_stage="G2",
        albuminuria_stage="A2",
        prevent_risk_category="INTERMEDIATE",
        prevent_30y_ascvd=26.0,
        level_classification={"level": "3B"},
    )

    plan = build_action_plan(patient, result)

    assert plan["domains"]["lipids"] == (
        "Moderate-intensity statin therapy is reasonable given borderline/intermediate ASCVD risk with albuminuria and metabolic risk-enhancing factors."
    )
    assert "No escalation indicated." not in plan["recommendations"]


def test_albuminuria_lipid_path_continues_existing_statin():
    patient = Patient(
        age=57,
        sex="male",
        egfr=64,
        uacr=48,
        lipid_lowering=True,
        statin_intensity="moderate",
    )
    result = RCCKMResult(
        egfr_stage="G2",
        albuminuria_stage="A2",
        prevent_risk_category="INTERMEDIATE",
        prevent_30y_ascvd=26.0,
        level_classification={"level": "3B"},
    )

    plan = build_action_plan(patient, result)

    assert plan["domains"]["lipids"] == (
        "Continue statin therapy; consider intensification if LDL-C/ApoB remain above target."
    )


def test_prevent_ascvd_bands_drive_lipid_decisions_without_total_cvd():
    low = build_action_plan(
        Patient(age=55, sex="male"),
        RCCKMResult(prevent_10y_ascvd=4.9, prevent_10y_total_cvd=22.0),
    )
    assert low["domains"]["lipids"] == (
        "Continue lifestyle-focused prevention; reassess risk as clinical data evolve."
    )

    borderline_with_enhancer = build_action_plan(
        Patient(age=55, sex="male", uacr=45, egfr=70),
        RCCKMResult(
            prevent_10y_ascvd=5.4,
            prevent_10y_total_cvd=22.0,
            albuminuria_stage="A2",
            egfr_stage="G2",
        ),
    )
    assert "Moderate-intensity statin therapy is reasonable" in borderline_with_enhancer["domains"]["lipids"]

    intermediate = build_action_plan(
        Patient(age=55, sex="male"),
        RCCKMResult(prevent_10y_ascvd=8.0),
    )
    assert intermediate["domains"]["lipids"] == (
        "Moderate-intensity statin therapy is generally favored for primary prevention."
    )

    high = build_action_plan(
        Patient(age=55, sex="male"),
        RCCKMResult(prevent_10y_ascvd=20.0),
    )
    assert high["domains"]["lipids"] == (
        "High-intensity statin therapy is generally recommended for primary prevention given high ASCVD risk."
    )


def test_sglt2_kidney_protection_branches():
    strong_albuminuria = build_action_plan(
        Patient(age=60, sex="male", egfr=45, uacr=220, ace_arb=True),
        RCCKMResult(egfr_stage="G3a", albuminuria_stage="A2"),
    )
    assert strong_albuminuria["domains"]["sglt2"].startswith("Add an SGLT2 inhibitor")

    diabetes_albuminuria = build_action_plan(
        Patient(age=60, sex="male", diabetes=True, egfr=55, uacr=80),
        RCCKMResult(egfr_stage="G3a", albuminuria_stage="A2"),
    )
    assert diabetes_albuminuria["domains"]["sglt2"].startswith("Consider an SGLT2 inhibitor")

    heart_failure = build_action_plan(
        Patient(age=60, sex="male", egfr=55, uacr=10, heart_failure=True),
        RCCKMResult(egfr_stage="G3a", albuminuria_stage="A1"),
    )
    assert heart_failure["domains"]["sglt2"].startswith("Add an SGLT2 inhibitor")

    low_egfr = build_action_plan(
        Patient(age=60, sex="male", egfr=18, uacr=220),
        RCCKMResult(egfr_stage="G4", albuminuria_stage="A2"),
    )
    assert "not routinely recommended at this eGFR" in low_egfr["domains"]["sglt2"]


def test_albuminuria_on_ace_arb_at_bp_goal_continues_kidney_protective_therapy():
    patient = Patient(
        age=57,
        sex="male",
        sbp=124,
        dbp=76,
        bp_treated=True,
        ace_arb=True,
        egfr=64,
        uacr=48,
    )
    result = RCCKMResult(egfr_stage="G2", albuminuria_stage="A2")

    plan = build_action_plan(patient, result)

    assert plan["domains"]["kidney"] == "Continue kidney-protective therapy and monitor UACR/eGFR."
    assert "ace_arb" not in plan["domains"]
    assert "blood_pressure" not in plan["domains"]


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
    plan = build_action_plan(Patient(age=55, sex="male", hiv=True, stable_art=True), RCCKMResult())

    assert plan["dominant_action"] == "Statin therapy recommended/reasonable in HIV; review ART-statin interactions."


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
        "Confirm persistent albuminuria with repeat UACR if not already confirmed; optimize kidney-protective therapy.",
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

    assert "Consider hsCRP to clarify inflammatory biomarker context." in plan["recommendations"]
    assert (
        plan["domains"]["hscrp_testing"]
        == "Consider hsCRP to clarify inflammatory biomarker context."
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
