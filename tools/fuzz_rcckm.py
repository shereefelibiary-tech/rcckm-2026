from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.validation_helpers import (  # noqa: E402
    action_lines,
    assert_no_raw_html_visible,
    clinical_visible_text,
    diagnosis_names,
    evaluate_dict,
)
from renderers.emr_renderer import render_emr_note  # noqa: E402


NUMERIC_FIELDS = (
    "age",
    "sbp",
    "dbp",
    "tc",
    "ldl_c",
    "hdl_c",
    "triglycerides",
    "apob",
    "lp_a_value",
    "a1c",
    "bmi",
    "egfr",
    "uacr",
    "hscrp",
    "cac",
)


def _maybe(rng: random.Random, values: list[Any], missing_rate: float = 0.25):
    if rng.random() < missing_rate:
        return None
    return rng.choice(values)


def generate_patient(rng: random.Random) -> dict[str, Any]:
    age = rng.choice([30, 39, 40, 45, 50, 55, 59, 60, 69, 70, 79])
    sex = rng.choice(["male", "female"])
    cac_choice = _maybe(rng, [0, 1, 25, 99, 100, 120, 299, 300, 350, 999, 1000, 1200], 0.35)
    cac_not_done = None
    if cac_choice is None and rng.random() < 0.45:
        cac_not_done = True

    patient = {
        "age": age,
        "sex": sex,
        "sbp": _maybe(rng, [118, 129, 130, 132, 145, 160], 0.25),
        "dbp": _maybe(rng, [70, 79, 80, 82, 92], 0.35),
        "tc": _maybe(rng, [160, 189, 205, 240, 280], 0.35),
        "ldl_c": _maybe(rng, [69, 70, 99, 100, 129, 130, 159, 160, 189, 190, 220], 0.25),
        "hdl_c": _maybe(rng, [38, 48, 55, 65], 0.35),
        "triglycerides": _maybe(rng, [99, 149, 150, 180, 499, 500, 999, 1000], 0.35),
        "apob": _maybe(rng, [79, 80, 99, 100, 110, 119, 120], 0.45),
        "lp_a_value": _maybe(rng, [30, 49, 50, 75, 80, 124, 125, 180, 250, 430], 0.5),
        "lp_a_unit": rng.choice(["nmol/L", "mg/dL"]),
        "a1c": _maybe(rng, [5.6, 5.7, 6.4, 6.5, 7.1, 9.0], 0.35),
        "bmi": _maybe(rng, [22, 27, 31, 38], 0.45),
        "egfr": _maybe(rng, [90, 60, 59, 55, 45, 44, 30, 29], 0.35),
        "uacr": _maybe(rng, [0, 9, 10, 29, 30, 45, 299, 300], 0.45),
        "hscrp": _maybe(rng, [0, 1.9, 2.0, 2.5, 6.0], 0.55),
        "cac": cac_choice,
        "cac_not_done": cac_not_done,
        "prevent_10y_ascvd": _maybe(rng, [2.99, 3.0, 4.99, 5.0, 9.99, 10.0, 18.0], 0.55),
        "prevent_30y_ascvd": _maybe(rng, [9.9, 10.0, 24.5, 40.0], 0.75),
        "diabetes": rng.choice([None, False, True]),
        "smoker": rng.choice([None, False, True]),
        "clinical_ascvd": rng.choice([False, False, False, True]),
        "family_history_premature_ascvd": rng.choice([None, False, True]),
        "inflammatory_disease": rng.choice([None, False, True]),
        "osa": rng.choice([None, False, True]),
        "masld": rng.choice([None, False, True]),
        "bp_treated": rng.choice([None, False, True]),
        "lipid_lowering": rng.choice([None, False, True]),
        "sglt2": rng.choice([None, False, True]),
        "glp1": rng.choice([None, False, True]),
        "ace_arb": rng.choice([None, False, True]),
    }
    if patient["clinical_ascvd"]:
        patient["clinical_ascvd_context"] = rng.choice(["prior MI", "prior NSTEMI and PCI/stent", None])
    return {key: value for key, value in patient.items() if value is not None}


def validate_patient(patient: dict[str, Any]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    try:
        patient_obj, result = evaluate_dict(patient)
        text = clinical_visible_text(patient_obj, result)
        emr_note = render_emr_note(patient_obj, result)
    except Exception as exc:  # pragma: no cover - exercised by CLI failure output
        return [{"category": "exception", "message": str(exc), "patient": patient}]

    def fail(category: str, message: str):
        failures.append(
            {
                "category": category,
                "message": message,
                "patient": patient,
                "emr_note": text[:4000],
            }
        )

    try:
        assert_no_raw_html_visible(text)
    except AssertionError:
        fail("raw_html", "Rendered visible text contains raw HTML.")

    if patient.get("uacr") is None and "UACR 0" in emr_note:
        fail("uacr_missing", "Missing UACR appeared as UACR 0.")
    if patient.get("cac") is None and "Plaque: CAC 0" in emr_note:
        fail("cac_missing", "Missing CAC appeared as CAC 0.")

    names = diagnosis_names(result)
    actions = action_lines(result)
    action_text = "\n".join(actions)
    lower_text = text.lower()

    cac = patient.get("cac")
    clinical_ascvd = bool(patient.get("clinical_ascvd"))

    if clinical_ascvd:
        if any("Subclinical coronary atherosclerosis" in name for name in names):
            fail("diagnosis", "Clinical ASCVD generated a subclinical plaque diagnosis.")
        if "PREVENT 10-year ASCVD risk" in emr_note:
            fail("prevent", "Clinical ASCVD displayed PREVENT as treatment-driving risk.")
    if cac is None and not clinical_ascvd:
        if any("Subclinical coronary atherosclerosis" in name for name in names):
            fail("cac_missing", "CAC missing generated plaque diagnosis.")
    if cac is not None and "Coronary calcium reasonable for plaque clarification" in action_text:
        fail("cac_repeat", "CAC already measured but CAC clarification was recommended.")
    if cac == 0 and "plaque unmeasured" in lower_text:
        fail("cac_zero", "Measured CAC 0 was also described as unmeasured.")
    if patient.get("cac_not_done") and "Plaque: CAC 0" in emr_note:
        fail("cac_not_done", "CAC not done appeared as CAC 0.")
    if "Aspirin may be considered" in text:
        age = patient.get("age")
        prevent = patient.get("prevent_10y_ascvd")
        evaluated_prevent = getattr(result, "prevent_10y_ascvd", None)
        allowed = (
            clinical_ascvd
            or (
                age is not None
                and 40 <= float(age) <= 69
                and (
                    cac is not None
                    and cac >= 100
                    or prevent is not None
                    and prevent >= 10
                    or evaluated_prevent is not None
                    and evaluated_prevent >= 10
                )
            )
        )
        if not allowed:
            fail("aspirin", "Aspirin consideration appeared outside allowed logic.")

    if len([name for name in names if name]) != len(set(name for name in names if name)):
        fail("duplicate_diagnosis", "Duplicate diagnosis candidate names generated.")

    forbidden = (
        "phenotype",
        "inherited risk",
        "genetics",
        "Supporting actions:",
        "no kidney action",
        "no kidney-risk signal",
        "do not start routine aspirin",
        "not routine for primary prevention",
        "artery plaque",
        "current goals and values",
        "the main reasons your risk is higher",
        "included in the prevention plan",
        "interpreted with the overall risk picture",
    )
    for phrase in forbidden:
        if phrase.lower() in lower_text:
            fail("wording", f"Forbidden phrase visible: {phrase}")

    return failures


def run_fuzz(n: int, seed: int) -> dict[str, Any]:
    rng = random.Random(seed)
    failures: list[dict[str, Any]] = []
    category_counts: dict[str, int] = {}
    for _ in range(n):
        patient = generate_patient(rng)
        case_failures = validate_patient(patient)
        failures.extend(case_failures)
        for failure in case_failures:
            category = failure["category"]
            category_counts[category] = category_counts.get(category, 0) + 1

    return {
        "seed": seed,
        "total_cases": n,
        "pass_count": n - len({json.dumps(failure["patient"], sort_keys=True) for failure in failures}),
        "failure_count": len(failures),
        "failure_categories": category_counts,
        "first_failures": failures[:20],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run RCCKM deterministic fuzz validation.")
    parser.add_argument("--n", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args(argv)

    summary = run_fuzz(args.n, args.seed)
    print(json.dumps(summary, indent=2))
    return 1 if summary["failure_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
