from core.enums import RiskLevel
from core.patient import Patient
from core.results import RCCKMResult
from modules.actions.engine import build_action_plan
from modules.actions.scaffold import build_action_recommendation_lines
from modules.risk_enhancers.engine import identify_risk_enhancers
from modules.targets.engine import build_target_result
from smartphrase_ingest.parser import parse_smartphrase_report
from ui.report_layout import run_patient


def test_non_hdl_is_calculated_at_engine_entry():
    patient = Patient(age=55, sex="male", tc=205, hdl_c=48)

    run_patient(patient)

    assert patient.non_hdl_c == 157


def test_diabetes_specific_enhancers_upgrade_diabetes_target_pathway():
    patient = Patient(
        age=55,
        sex="female",
        diabetes=True,
        diabetes_duration_years=12,
        diabetic_retinopathy=True,
        abi=0.82,
    )

    target = build_target_result(patient)
    enhancers = identify_risk_enhancers(patient)

    assert target.ldl_c_target == 70
    assert target.non_hdl_c_target == 100
    assert any("diabetes duration >=10 years" in item for item in enhancers)
    assert any("retinopathy" in item and "ABI <0.9" in item for item in enhancers)


def test_parser_extracts_diabetes_specific_enhancers_and_abi():
    report = parse_smartphrase_report(
        "Diabetes: yes. Diabetes duration 12 years. Retinopathy: Yes. Neuropathy: No. ABI 0.82."
    )

    assert report.extracted["diabetes"] is True
    assert report.extracted["diabetes_duration_years"] == 12
    assert report.extracted["diabetic_retinopathy"] is True
    assert report.extracted["diabetic_neuropathy"] is False
    assert report.extracted["abi"] == 0.82
    assert report.extracted["abi_lt_0_9"] is True


def test_lipid_supplement_parser_warning_and_recommendation():
    report = parse_smartphrase_report("Taking red yeast rice for cholesterol lowering.")
    patient = Patient(
        age=55,
        sex="male",
        lp_a_value=20,
        lp_a_unit="nmol/L",
        lipid_supplements=report.extracted["lipid_supplements"],
    )

    plan = build_action_plan(patient, RCCKMResult())

    assert report.extracted["lipid_supplements"] is True
    assert any("Dietary supplement mentioned" in warning for warning in report.warnings)
    assert "Dietary supplements are not recommended as a substitute" in plan["dominant_action"]


def test_lipid_monitoring_line_added_when_lipid_therapy_considered():
    patient = Patient(age=48, sex="female", preeclampsia=True)
    result = RCCKMResult(prevent_risk_category=RiskLevel.BORDERLINE)
    plan = build_action_plan(patient, result)
    result.dominant_action = plan["dominant_action"]
    result.recommendations = plan["recommendations"]
    result.action_domains = plan["domains"]

    lines = build_action_recommendation_lines(patient, result)

    assert lines[0] == "Risk discussion reasonable; consider lipid-lowering therapy."
    assert any("4-12 weeks" in line and "6-12 months" in line for line in lines)
