from core.patient import Patient
from core.enums import DecisionStability, PlaqueCategory, RiskLevel
from core.engine import evaluate_patient


def test_evaluate_patient_returns_combined_results():
    patient = Patient(
        age=60,
        sex="male",
        cac=350,
        apob=110,
        lp_a_value=80,
        uacr=45,
        egfr=55,
        diabetes=True,
        clinical_ascvd=False,
        prevent_10y_ascvd=8.2,
        prevent_10y_total_cvd=12.4,
        prevent_30y_ascvd=24.5,
        prevent_30y_total_cvd=31.2,
    )

    result = evaluate_patient(patient)

    assert result.plaque_category == PlaqueCategory.SEVERE
    assert result.prevent_10y_ascvd == 8.2
    assert result.prevent_10y_total_cvd == 12.4
    assert result.prevent_30y_ascvd == 24.5
    assert result.prevent_30y_total_cvd == 31.2
    assert result.prevent_risk_category == RiskLevel.INTERMEDIATE
    assert result.cac_recommendation is None
    assert result.egfr_stage == "G3a"
    assert result.albuminuria_stage == "A2"
    assert result.kdigo_stage == "G3aA2"
    assert result.clarification["tier"] == 3
    assert result.discordance_insight["status"] == "discordant"
    assert result.discordance_insight["type"] == "plaque_exceeds_population_risk"
    assert result.ckm_stage["stage"] == 3
    assert result.top_drivers == [
        "CAC 350",
        "ApoB 110 mg/dL",
        "T2DM with CKD G3aA2",
    ]
    assert (
        result.dominant_action
        == "Lipid-lowering therapy is indicated; treat toward high-risk targets."
    )
    assert (
        "Lipid-lowering therapy is indicated; treat toward high-risk targets."
        in result.recommendations
    )
    assert (
        result.action_domains["lipids"]
        == "Lipid-lowering therapy is indicated; treat toward high-risk targets."
    )
    assert result.decision_stability == DecisionStability.HIGH
    assert len(result.targets) == 1
    assert any(c.name == "Chronic kidney disease" for c in result.diagnosis_candidates)
    assert any("albuminuria" in c.name.lower() for c in result.diagnosis_candidates)
    assert any(c.name == "Type 2 diabetes mellitus" for c in result.diagnosis_candidates)


def test_evaluate_patient_populates_prevent_availability_from_worksheet_fields():
    patient = Patient(
        age=60,
        sex="male",
        tc=210,
        hdl_c=45,
        sbp=140,
        bp_treated=True,
        smoker=True,
        diabetes=True,
        bmi=32,
        egfr=55,
        lipid_lowering=True,
        uacr=45,
        a1c=7.1,
    )

    result = evaluate_patient(patient)

    assert result.prevent_available is True
    assert result.prevent_missing_inputs == []
    assert result.prevent_10y_ascvd is not None
    assert result.prevent_10y_total_cvd is not None
    assert result.prevent_30y_ascvd is None
    assert result.prevent_unsupported_reason == (
        "30-year PREVENT is only available for ages 30-59."
    )


def test_evaluate_patient_reports_prevent_missing_inputs():
    patient = Patient(age=60, sex="male", tc=210, hdl_c=45)

    result = evaluate_patient(patient)

    assert result.prevent_available is False
    assert "systolic BP" in result.prevent_missing_inputs
    assert "smoking status" in result.prevent_missing_inputs


def test_evaluate_patient_uses_calculated_prevent_for_target_selection():
    patient = Patient(
        age=55,
        sex="female",
        tc=200,
        hdl_c=50,
        sbp=130,
        bp_treated=False,
        smoker=False,
        diabetes=False,
        bmi=30,
        egfr=90,
        lipid_lowering=False,
    )

    result = evaluate_patient(patient)

    assert result.prevent_10y_ascvd is not None
    assert result.prevent_10y_ascvd < 3
    assert result.prevent_30y_ascvd is not None
    assert result.prevent_30y_ascvd >= 10
    assert result.targets[0].ldl_c_target == 100
    assert result.targets[0].non_hdl_c_target == 130
