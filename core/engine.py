from core.results import RCCKMResult
from modules.actions.engine import build_action_plan
from modules.cac_recommendation.engine import build_cac_recommendation
from modules.clarification.engine import build_clarification_ladder
from modules.ckm.engine import classify_ckm_stage
from modules.diagnoses.engine import build_diagnosis_candidates
from modules.discordance.engine import build_discordance_insight
from modules.drivers.engine import build_top_drivers
from modules.family_history.engine import build_family_history_payload
from modules.kdigo.engine import (
    build_kdigo_stage,
    classify_albuminuria_stage,
    classify_egfr_stage,
)
from modules.levels.level_classifier import classify_rcckm_level
from modules.plaque.engine import build_plaque_result
from modules.prevention_context.engine import classify_prevention_context
from modules.lipids.non_hdl import calculate_non_hdl
from modules.prevent.calculator import (
    calculate_prevent_summary,
)
from modules.prevent.engine import classify_prevent_ascvd_risk
from modules.risk.engine import assign_risk_level
from modules.snapshot.engine import build_snapshot_lines
from modules.stability.engine import assess_decision_stability
from modules.targets.engine import build_target_result
from rcckm.rule_trace import build_rule_traces


def evaluate_patient(patient):
    if patient.non_hdl_c is None:
        patient.non_hdl_c = calculate_non_hdl(patient.tc, patient.hdl_c)

    family_history = build_family_history_payload(patient)
    patient.family_history_summary = family_history["summary"]
    patient.premature_fhx_ascvd = family_history["premature_fhx_ascvd"]
    patient.family_history_premature_ascvd = family_history["premature_fhx_ascvd"]

    plaque_result = build_plaque_result(patient)
    risk_level = assign_risk_level(patient)
    stability = assess_decision_stability(patient)
    diagnosis_candidates = build_diagnosis_candidates(patient)
    prevent_summary = calculate_prevent_summary(patient)
    prevent_10y_ascvd = prevent_summary["prevent_10y_ascvd"]
    prevent_10y_total_cvd = prevent_summary["prevent_10y_total_cvd"]
    prevent_30y_ascvd = prevent_summary["prevent_30y_ascvd"]
    prevent_30y_total_cvd = prevent_summary["prevent_30y_total_cvd"]
    patient.prevent_10y_ascvd = prevent_10y_ascvd
    patient.prevent_10y_total_cvd = prevent_10y_total_cvd
    patient.prevent_30y_ascvd = prevent_30y_ascvd
    patient.prevent_30y_total_cvd = prevent_30y_total_cvd
    target_result = build_target_result(patient)
    prevent_risk_category = classify_prevent_ascvd_risk(prevent_10y_ascvd)
    egfr_stage = classify_egfr_stage(patient.egfr)
    albuminuria_stage = classify_albuminuria_stage(patient.uacr)
    kdigo_stage = build_kdigo_stage(patient)
    severe_hypercholesterolemia = patient.ldl_c is not None and patient.ldl_c >= 190
    possible_fh_pathway = bool(
        getattr(patient, "suspected_fh_hefh", False)
        or (
            severe_hypercholesterolemia
            and (
                family_history["premature_fhx_ascvd"]
                or (patient.apob is not None and patient.apob >= 140)
            )
        )
    )
    prevention_context = classify_prevention_context(
        patient,
        {"plaque_category": plaque_result.plaque_category},
    )

    rcckm_result = RCCKMResult(
        plaque_category=plaque_result.plaque_category,
        risk_level=risk_level,
        clinical_ascvd=bool(patient.clinical_ascvd),
        prevention_context=prevention_context["prevention_context"],
        prevention_context_primary_reason=prevention_context["primary_reason"],
        prevention_context_supporting_findings=list(
            prevention_context["supporting_findings"]
        ),
        prevention_context_rule_id=prevention_context["rule_id"],
        severe_hypercholesterolemia=severe_hypercholesterolemia,
        possible_fh_pathway=possible_fh_pathway,
        prevent_available=bool(prevent_summary["available"]),
        prevent_missing_inputs=list(prevent_summary["missing_inputs"]),
        prevent_unsupported_reason=prevent_summary.get("unsupported_reason") or prevent_summary.get("unavailable_reason"),
        prevent_model_used=prevent_summary.get("model_used"),
        prevent_warnings=list(prevent_summary.get("warnings") or []),
        prevent_10y_ascvd=prevent_10y_ascvd,
        prevent_10y_total_cvd=prevent_10y_total_cvd,
        prevent_10y_hf=prevent_summary.get("prevent_10y_hf"),
        prevent_10y_chd=prevent_summary.get("prevent_10y_chd"),
        prevent_10y_stroke=prevent_summary.get("prevent_10y_stroke"),
        prevent_30y_ascvd=prevent_30y_ascvd,
        prevent_30y_total_cvd=prevent_30y_total_cvd,
        prevent_30y_hf=prevent_summary.get("prevent_30y_hf"),
        prevent_30y_chd=prevent_summary.get("prevent_30y_chd"),
        prevent_30y_stroke=prevent_summary.get("prevent_30y_stroke"),
        prevent_5y_ascvd=prevent_summary.get("prevent_5y_ascvd"),
        prevent_5y_total_cvd=prevent_summary.get("prevent_5y_total_cvd"),
        prevent_5y_hf=prevent_summary.get("prevent_5y_hf"),
        prevent_age=prevent_summary.get("prevent_age"),
        prevent_percentile=prevent_summary.get("prevent_percentile"),
        prevent_risk_category=prevent_risk_category,
        decision_stability=stability,
        egfr_stage=egfr_stage,
        albuminuria_stage=albuminuria_stage,
        kdigo_stage=kdigo_stage,
        family_history_summary=family_history["summary"],
        premature_fhx_ascvd=family_history["premature_fhx_ascvd"],
        targets=[target_result],
        diagnosis_candidates=diagnosis_candidates,
    )

    rcckm_result.cac_recommendation = build_cac_recommendation(
        patient, rcckm_result
    )
    rcckm_result.clarification = build_clarification_ladder(
        patient, rcckm_result
    )
    rcckm_result.discordance_insight = build_discordance_insight(
        patient, rcckm_result
    )
    rcckm_result.ckm_stage = classify_ckm_stage(patient, rcckm_result)
    rcckm_result.level_classification = classify_rcckm_level(
        patient, rcckm_result
    ).to_dict()
    rcckm_result.top_drivers = build_top_drivers(patient, rcckm_result)
    action_plan = build_action_plan(patient, rcckm_result)
    rcckm_result.dominant_action = action_plan["dominant_action"]
    rcckm_result.recommendations = action_plan["recommendations"]
    rcckm_result.action_domains = action_plan["domains"]
    rcckm_result.rule_traces = [
        trace.to_dict() for trace in build_rule_traces(patient, rcckm_result)
    ]
    rcckm_result.snapshot_lines = build_snapshot_lines(rcckm_result)

    return rcckm_result
