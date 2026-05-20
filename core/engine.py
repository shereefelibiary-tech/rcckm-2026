from core.results import RCCKMResult
from modules.diagnoses.engine import build_diagnosis_candidates
from modules.plaque.engine import build_plaque_result
from modules.stability.engine import assess_decision_stability
from modules.targets.engine import build_target_result


def evaluate_patient(patient):
    plaque_result = build_plaque_result(patient)
    stability = assess_decision_stability(patient)
    target_result = build_target_result(patient)
    diagnosis_candidates = build_diagnosis_candidates(patient)

    return RCCKMResult(
        plaque_category=plaque_result.plaque_category,
        decision_stability=stability,
        targets=[target_result],
        diagnosis_candidates=diagnosis_candidates,
    )
