from core.results import RCCKMResult
from modules.diagnoses.engine import build_diagnosis_candidates
from modules.plaque.engine import build_plaque_result
from modules.risk.engine import assign_risk_level
from modules.stability.engine import assess_decision_stability
from modules.targets.engine import build_target_result


def evaluate_patient(patient):
    plaque_result = build_plaque_result(patient)
    risk_level = assign_risk_level(patient)
    stability = assess_decision_stability(patient)
    target_result = build_target_result(patient)
    diagnosis_candidates = build_diagnosis_candidates(patient)

    return RCCKMResult(
        plaque_category=plaque_result.plaque_category,
        risk_level=risk_level,
        decision_stability=stability,
        targets=[target_result],
        diagnosis_candidates=diagnosis_candidates,
    )
