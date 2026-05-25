import json
from pathlib import Path

from ui.input_worksheet import build_patient_from_inputs


DEMO_CASES = (
    ("Low risk / complete data", "minimal_signal_cac_0"),
    ("Early metabolic risk", "level2_early_metabolic_risk"),
    ("High 30-year risk", "level3_low_10y_high_lifetime_burden"),
    ("ApoB / LDL atherogenic burden", "level3b_atherogenic_30y_ldl_apob"),
    ("Lp(a) + family history", "level2b_low_prevent_lpa_family_history"),
    ("Diabetes + albuminuria", "diabetes_plus_ckd_albuminuria"),
    ("CAC 350 / high plaque burden", "cac_350"),
    ("LDL >=190", "ldl_severe_hypercholesterolemia"),
    ("Clinical ASCVD", "clinical_ascvd"),
    ("Severe hypertriglyceridemia", "tg_1000_very_severe"),
)


def _golden_cases_path() -> Path:
    return Path(__file__).resolve().parents[1] / "tests" / "golden_cases" / "golden_cases.json"


def load_golden_case_patients(path: Path | None = None) -> dict[str, dict]:
    """Load patient payloads from the golden-case fixture file."""
    fixture_path = path or _golden_cases_path()
    with fixture_path.open(encoding="utf-8") as handle:
        cases = json.load(handle)
    return {
        str(case.get("name")): dict(case.get("patient") or {})
        for case in cases
        if case.get("name") and case.get("patient")
    }


def demo_case_options(patients_by_case: dict[str, dict] | None = None) -> list[tuple[str, str]]:
    """Return friendly demo labels paired with available golden-case names."""
    available = patients_by_case if patients_by_case is not None else load_golden_case_patients()
    return [(label, case_name) for label, case_name in DEMO_CASES if case_name in available]


def build_demo_patient(case_name: str, patients_by_case: dict[str, dict] | None = None):
    """Build a Patient object from a named golden-case patient payload."""
    available = patients_by_case if patients_by_case is not None else load_golden_case_patients()
    if case_name not in available:
        raise KeyError(f"Unknown demo case: {case_name}")
    return build_patient_from_inputs(available[case_name])
