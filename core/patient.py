from dataclasses import dataclass
from typing import Optional


@dataclass
class Patient:
    age: Optional[int]
    sex: str
    tc: Optional[float] = None
    ldl_c: Optional[float] = None
    hdl_c: Optional[float] = None
    triglycerides: Optional[float] = None
    non_hdl_c: Optional[float] = None
    apob: Optional[float] = None
    lp_a_value: Optional[float] = None
    lp_a_unit: Optional[str] = None
    cac: Optional[float] = None
    cac_not_done: Optional[bool] = None
    egfr: Optional[float] = None
    uacr: Optional[float] = None
    a1c: Optional[float] = None
    bmi: Optional[float] = None
    diabetes: Optional[bool] = None
    hypertension: Optional[bool] = None
    sbp: Optional[float] = None
    dbp: Optional[float] = None
    bp_treated: Optional[bool] = None
    elevated_bp: Optional[bool] = None
    smoker: Optional[bool] = None
    smoking: Optional[bool] = None
    clinical_ascvd: Optional[bool] = None
    clinical_ascvd_context: Optional[str] = None
    hscrp: Optional[float] = None
    ckd: Optional[bool] = None
    inflammatory_disease: Optional[bool] = None
    rheumatoid_arthritis: Optional[bool] = None
    sle: Optional[bool] = None
    psoriasis: Optional[bool] = None
    ibd: Optional[bool] = None
    hiv: Optional[bool] = None
    osa: Optional[bool] = None
    masld: Optional[bool] = None
    family_history_premature_ascvd: Optional[bool] = None
    premature_fhx_ascvd: Optional[bool] = None
    family_history_relationship: Optional[str] = None
    family_history_event_type: Optional[str] = None
    family_history_age_at_event: Optional[float] = None
    family_history_summary: Optional[str] = None
    lipid_lowering: Optional[bool] = None
    sglt2: Optional[bool] = None
    glp1: Optional[bool] = None
    ace_arb: Optional[bool] = None
    prevent_10y_ascvd: Optional[float] = None
    prevent_10y_total_cvd: Optional[float] = None
    prevent_30y_ascvd: Optional[float] = None
    prevent_30y_total_cvd: Optional[float] = None
    prevent_age: Optional[float] = None
    prevent_percentile: Optional[float] = None
