from dataclasses import dataclass, field
from typing import Any, Optional

from core.enums import DecisionStability, PlaqueCategory, RiskLevel


@dataclass
class TargetResult:
    ldl_c_target: Optional[float] = None
    non_hdl_c_target: Optional[float] = None
    apob_target: Optional[float] = None
    rationale: Optional[str] = None


@dataclass
class DiagnosisCandidate:
    name: Optional[str] = None
    icd10_code: Optional[str] = None
    status: Optional[str] = None
    source: Optional[str] = None
    hcc_relevant: Optional[bool] = None
    diagnosis: Optional[str] = None
    hcc_supported: bool = False
    hcc_label: Optional[str] = None
    confidence: Optional[str] = None
    review_status: Optional[str] = None


@dataclass
class RCCKMResult:
    plaque_category: Optional[PlaqueCategory] = None
    risk_level: Optional[RiskLevel] = None
    clinical_ascvd: bool = False
    prevention_context: Optional[str] = None
    prevention_context_primary_reason: Optional[str] = None
    prevention_context_supporting_findings: list[str] = field(default_factory=list)
    prevention_context_rule_id: Optional[str] = None
    severe_hypercholesterolemia: bool = False
    possible_fh_pathway: bool = False
    prevent_available: bool = False
    prevent_missing_inputs: list[str] = field(default_factory=list)
    prevent_unsupported_reason: Optional[str] = None
    prevent_10y_ascvd: Optional[float] = None
    prevent_10y_total_cvd: Optional[float] = None
    prevent_10y_hf: Optional[float] = None
    prevent_10y_chd: Optional[float] = None
    prevent_10y_stroke: Optional[float] = None
    prevent_30y_ascvd: Optional[float] = None
    prevent_30y_total_cvd: Optional[float] = None
    prevent_30y_hf: Optional[float] = None
    prevent_30y_chd: Optional[float] = None
    prevent_30y_stroke: Optional[float] = None
    prevent_5y_ascvd: Optional[float] = None
    prevent_5y_total_cvd: Optional[float] = None
    prevent_5y_hf: Optional[float] = None
    prevent_age: Optional[float] = None
    prevent_percentile: Optional[float] = None
    prevent_model_used: Optional[str] = None
    prevent_warnings: list[str] = field(default_factory=list)
    prevent_risk_category: Optional[RiskLevel] = None
    cac_recommendation: Optional[str] = None
    egfr_stage: Optional[str] = None
    albuminuria_stage: Optional[str] = None
    kdigo_stage: Optional[str] = None
    clarification: Optional[dict] = None
    discordance_insight: Optional[dict] = None
    ckm_stage: Optional[dict] = None
    top_drivers: list[str] = field(default_factory=list)
    rss_total: Optional[float] = None
    rss_category: Optional[str] = None
    level_classification: Optional[dict] = None
    family_history_summary: Optional[str] = None
    premature_fhx_ascvd: Optional[bool] = None
    decision_stability: Optional[DecisionStability] = None
    targets: list[TargetResult] = field(default_factory=list)
    dominant_action: Optional[str] = None
    recommendations: list[str] = field(default_factory=list)
    action_domains: dict = field(default_factory=dict)
    rule_traces: list[dict] = field(default_factory=list)
    snapshot_lines: list[str] = field(default_factory=list)
    emr_lines: list[str] = field(default_factory=list)
    diagnosis_candidates: list[DiagnosisCandidate] = field(default_factory=list)
    diagnosis_entries: list[dict[str, Any]] = field(default_factory=list)
