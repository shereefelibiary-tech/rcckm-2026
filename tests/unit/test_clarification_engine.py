from core.enums import RiskLevel
from core.patient import Patient
from core.results import RCCKMResult
from modules.clarification.engine import build_clarification_ladder


def test_build_clarification_ladder_treatment_forward_for_clinical_ascvd():
    patient = Patient(age=60, sex="male", clinical_ascvd=True)
    result = RCCKMResult(prevent_risk_category=RiskLevel.INTERMEDIATE)

    ladder = build_clarification_ladder(patient, result)

    assert ladder["tier"] == 3
    assert ladder["summary"] == (
        "Very high-risk patient; clarification testing should not delay management."
    )


def test_build_clarification_ladder_treatment_forward_for_cac_300():
    patient = Patient(age=60, sex="male", cac=300)
    result = RCCKMResult(prevent_risk_category=RiskLevel.INTERMEDIATE)

    ladder = build_clarification_ladder(patient, result)

    assert ladder["tier"] == 3


def test_build_clarification_ladder_recommends_cac_for_borderline_prevent():
    patient = Patient(
        age=60,
        sex="male",
        cac=None,
        lp_a_value=20,
        family_history_premature_ascvd=True,
    )
    result = RCCKMResult(prevent_risk_category=RiskLevel.BORDERLINE)

    ladder = build_clarification_ladder(patient, result)

    assert ladder["tier"] == 2
    assert ladder["recommend_cac"] is True
    assert "CAC" in ladder["summary"]


def test_build_clarification_ladder_recommends_apob_when_ldl_present():
    patient = Patient(age=60, sex="male", ldl_c=130, apob=None, lp_a_value=20)
    result = RCCKMResult(prevent_risk_category=RiskLevel.LOW)

    ladder = build_clarification_ladder(patient, result)

    assert ladder["tier"] == 2
    assert ladder["recommend_apob"] is True


def test_build_clarification_ladder_suppresses_lpa_when_missing_but_not_decision_relevant():
    patient = Patient(age=60, sex="male")
    result = RCCKMResult(prevent_risk_category=RiskLevel.LOW)

    ladder = build_clarification_ladder(patient, result)

    assert ladder["tier"] == 0
    assert ladder["recommend_lpa"] is False


def test_build_clarification_ladder_recommends_lpa_for_premature_family_history():
    patient = Patient(
        age=60,
        sex="male",
        family_history_premature_ascvd=True,
        family_history_relationship="father",
        family_history_event_type="MI",
        family_history_age_at_event=49,
    )
    result = RCCKMResult(prevent_risk_category=RiskLevel.LOW)

    ladder = build_clarification_ladder(patient, result)

    assert ladder["tier"] >= 1
    assert ladder["recommend_lpa"] is True


def test_build_clarification_ladder_suppresses_apob_and_lpa_for_low_friction_cac_case():
    patient = Patient(
        age=55,
        sex="male",
        cac=12,
        ldl_c=69,
        triglycerides=80,
        a1c=4.9,
        apob=None,
        lp_a_value=None,
    )
    result = RCCKMResult(prevent_risk_category=RiskLevel.LOW, prevent_10y_ascvd=2.43)

    ladder = build_clarification_ladder(patient, result)

    assert ladder["recommend_apob"] is False
    assert ladder["recommend_lpa"] is False
    assert ladder["tier"] == 0


def test_build_clarification_ladder_recommends_apob_for_elevated_tg():
    patient = Patient(
        age=55,
        sex="male",
        ldl_c=90,
        triglycerides=250,
        apob=None,
        lp_a_value=20,
    )
    result = RCCKMResult(prevent_risk_category=RiskLevel.LOW)

    ladder = build_clarification_ladder(patient, result)

    assert ladder["recommend_apob"] is True


def test_build_clarification_ladder_recommends_uacr_in_diabetes_context():
    patient = Patient(age=60, sex="male", diabetes=True, uacr=None, lp_a_value=20)
    result = RCCKMResult(prevent_risk_category=RiskLevel.LOW)

    ladder = build_clarification_ladder(patient, result)

    assert ladder["tier"] == 2
    assert ladder["recommend_uacr"] is True


def test_build_clarification_ladder_combines_recommendations():
    patient = Patient(
        age=60,
        sex="male",
        cac=None,
        ldl_c=140,
        apob=None,
        lp_a_value=None,
        diabetes=True,
        uacr=None,
    )
    result = RCCKMResult(prevent_risk_category=RiskLevel.INTERMEDIATE)

    ladder = build_clarification_ladder(patient, result)

    assert ladder["tier"] == 2
    assert ladder["recommend_cac"] is False
    assert ladder["recommend_apob"] is True
    assert ladder["recommend_lpa"] is True
    assert ladder["recommend_uacr"] is True


def test_build_clarification_ladder_respects_cac_age_gate():
    result = RCCKMResult(prevent_risk_category=RiskLevel.INTERMEDIATE)

    below_gate = build_clarification_ladder(
        Patient(age=39, sex="male", cac=None, lp_a_value=20),
        result,
    )
    at_gate = build_clarification_ladder(
        Patient(age=40, sex="male", cac=None, lp_a_value=20),
        result,
    )

    assert below_gate["recommend_cac"] is False
    assert at_gate["recommend_cac"] is True


def test_build_clarification_ladder_does_not_use_cac_to_derisk_clear_treatment_paths():
    result = RCCKMResult(prevent_risk_category=RiskLevel.INTERMEDIATE, egfr_stage="G3a")

    assert build_clarification_ladder(
        Patient(age=55, sex="male", clinical_ascvd=True, cac=None),
        result,
    )["recommend_cac"] is False
    assert build_clarification_ladder(
        Patient(age=55, sex="male", ldl_c=190, cac=None, lp_a_value=20),
        result,
    )["recommend_cac"] is False
    assert build_clarification_ladder(
        Patient(age=55, sex="male", diabetes=True, cac=None, lp_a_value=20),
        result,
    )["recommend_cac"] is False
