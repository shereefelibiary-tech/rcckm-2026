from dataclasses import dataclass
from typing import Optional


@dataclass
class Patient:
    age: int
    sex: str
    ldl_c: Optional[float] = None
    hdl_c: Optional[float] = None
    triglycerides: Optional[float] = None
    non_hdl_c: Optional[float] = None
    apob: Optional[float] = None
    lp_a_value: Optional[float] = None
    lp_a_unit: Optional[str] = None
    cac: Optional[float] = None
    egfr: Optional[float] = None
    uacr: Optional[float] = None
    diabetes: Optional[bool] = None
    hypertension: Optional[bool] = None
    smoker: Optional[bool] = None
    clinical_ascvd: Optional[bool] = None
    hscrp: Optional[float] = None
    ckd: Optional[bool] = None
    family_history_premature_ascvd: Optional[bool] = None
