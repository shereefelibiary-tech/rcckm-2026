from core.results import RCCKMResult, TargetResult, DiagnosisCandidate
from core.enums import RiskLevel, PlaqueCategory, DecisionStability
from modules.snapshot.engine import build_snapshot_lines


def test_build_snapshot_lines_includes_all_result_fields():
    target = TargetResult(ldl_c_target=70, non_hdl_c_target=100)
    diagnosis1 = DiagnosisCandidate(name="Diabetes mellitus")
    diagnosis2 = DiagnosisCandidate(name="Chronic kidney disease")

    result = RCCKMResult(
        risk_level=RiskLevel.HIGH,
        plaque_category=PlaqueCategory.EXTENSIVE,
        decision_stability=DecisionStability.HIGH,
        targets=[target],
        diagnosis_candidates=[diagnosis1, diagnosis2],
    )

    lines = build_snapshot_lines(result)

    assert any("Risk level" in line for line in lines)
    assert any("Plaque category" in line for line in lines)
    assert any("Decision stability" in line for line in lines)
    assert any("LDL-C target" in line for line in lines)
    assert any("Non-HDL-C target" in line for line in lines)
    assert any("Diagnosis candidates" in line for line in lines)
