from dataclasses import dataclass, field
from typing import Optional

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


@dataclass
class RCCKMResult:
    plaque_category: Optional[PlaqueCategory] = None
    risk_level: Optional[RiskLevel] = None
    decision_stability: Optional[DecisionStability] = None
    targets: list[TargetResult] = field(default_factory=list)
    dominant_action: Optional[str] = None
    snapshot_lines: list[str] = field(default_factory=list)
    emr_lines: list[str] = field(default_factory=list)
    diagnosis_candidates: list[DiagnosisCandidate] = field(default_factory=list)
